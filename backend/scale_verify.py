"""Scale verification for the recommendation + offer system.

Runs entirely in-process against the REAL database (no server needed):

  1. Full-dataset train timing (fresh engine, saved to the real MODEL_PATH).
  2. Full-dataset correctness distribution for ALL customers:
     source (svd / cold_start / popular), reason codes, and whether the top
     recommended category matches the customer's dominant browsing category.
  3. Per-request in-process recommend() latency (p50 / p95).
  4. Batch _store_recommendations() timing (real DB writes) + scoring-only split.
  5. Offer engine timing (assign_offers / seed_offers startup path).
  6. Model memory / size honesty numbers.

Read-only regarding data EXCEPT the standard training store cycle (which is
exactly what POST /api/admin/train performs).
"""
import os
import statistics
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import asyncio
import json

import pandas as pd
from sqlalchemy import func, select

from app.config import settings
from app.database import async_session_factory
from app.models import Customer, CustomerSegment, Event, Product, Recommendation
from app.offers import OfferEngine
from app.recommender import EVENT_WEIGHTS, RecommendationEngine
from app.routers.admin import _store_recommendations

OUT_PATH = os.path.join(os.environ.get("TEMP", "."), "scale_verify_report.json")


def pct(xs: list, p: float) -> float:
    if not xs:
        return 0.0
    s = sorted(xs)
    idx = min(len(s) - 1, round((p / 100.0) * (len(s) - 1)))
    return float(s[idx])


def lat_stats(xs: list[float]) -> dict:
    if not xs:
        return {"n": 0}
    return {
        "n": len(xs),
        "min_ms": round(min(xs) * 1000, 2),
        "p50_ms": round(pct(xs, 50) * 1000, 2),
        "p95_ms": round(pct(xs, 95) * 1000, 2),
        "p99_ms": round(pct(xs, 99) * 1000, 2),
        "mean_ms": round(statistics.mean(xs) * 1000, 2),
        "max_ms": round(max(xs) * 1000, 2),
    }


def dominant_category(customer_id: str, events_df: pd.DataFrame, cat_map: dict) -> str | None:
    sub = events_df[events_df["customer_id"] == customer_id]
    counts: dict[str, float] = {}
    for _, ev in sub.iterrows():
        pid = ev.get("product_id")
        if not pid or pid not in cat_map:
            continue
        cat = cat_map[pid]
        counts[cat] = counts.get(cat, 0.0) + max(EVENT_WEIGHTS.get(ev.get("event_type"), 0.5), 0.0)
    if not counts:
        return None
    return max(counts, key=counts.get)


async def load_data(db):
    eres = await db.execute(select(Event))
    events = eres.scalars().all()
    events_df = pd.DataFrame([{
        "event_id": e.event_id,
        "customer_id": e.customer_id,
        "product_id": e.product_id,
        "event_type": e.event_type,
        "event_timestamp": e.event_timestamp,
    } for e in events])

    pres = await db.execute(select(Product))
    products = pres.scalars().all()
    products_df = pd.DataFrame([{
        "product_id": p.product_id,
        "name": p.name,
        "category": p.category,
        "subcategory": p.subcategory,
        "brand": p.brand,
        "price": p.price,
        "image_url": p.image_url,
        "rating": p.rating,
        "discount_percent": p.discount_percent,
        "original_price": p.original_price,
    } for p in products])

    for col in ["customer_id", "product_id", "event_type"]:
        if col in events_df.columns:
            events_df[col] = events_df[col].astype(str)
    for col in ["product_id", "category", "brand"]:
        if col in products_df.columns:
            products_df[col] = products_df[col].astype(str)
    return events_df, products_df


def _pure_compute(engine, events_df, products_df, customer_ids) -> dict:
    computed = {}
    for cid in customer_ids:
        try:
            recs = engine.recommend(customer_id=cid, n=10,
                                    events_df=events_df, products_df=products_df)
            if recs:
                seen = {}
                for rec in recs:
                    pid = rec["product_id"]
                    if pid not in seen or rec["score"] > seen[pid]["score"]:
                        seen[pid] = rec
                computed[cid] = sorted(seen.values(), key=lambda r: r["score"], reverse=True)
        except Exception as e:
            print(f"  WARN: {cid[:12]} failed in pure compute: {e}")
            continue
    return computed


async def main() -> None:
    report: dict = {}

    async with async_session_factory() as db:
        # ── Real dataset sizes ─────────────────────────────────────────────
        cust_cnt = (await db.execute(select(func.count(Customer.customer_id)))).scalar()
        consent_cnt = (await db.execute(
            select(func.count(Customer.customer_id)).where(Customer.consent_given))).scalar()
        ev_cnt = (await db.execute(select(func.count(Event.event_id)))).scalar()
        prod_cnt = (await db.execute(select(func.count(Product.product_id)))).scalar()
        rec_cnt = (await db.execute(select(func.count(Recommendation.customer_id)))).scalar()
        cust_result = await db.execute(select(Customer.customer_id, Customer.consent_given))
        all_customers = cust_result.all()

        report["dataset"] = {
            "customers": cust_cnt,
            "consenting_customers": consent_cnt,
            "events": ev_cnt,
            "products": prod_cnt,
            "stored_recommendation_rows": rec_cnt,
        }
        print("DATASET:", json.dumps(report["dataset"]))

        events_df, products_df = await load_data(db)
        event_having = set(events_df["customer_id"].unique())
        report["dataset"]["event_having_customers"] = len(event_having)
        print("event-having customers:", len(event_having))

        # ── 1. Train timing on the full dataset ────────────────────────────
        t0 = time.perf_counter()
        engine = RecommendationEngine(settings)
        engine.train(events_df, products_df)
        t_train = time.perf_counter() - t0

        e2 = RecommendationEngine(settings)
        t0 = time.perf_counter()
        e2.build_features(events_df, products_df)
        t_build = time.perf_counter() - t0
        k = min(50, e2._interaction_matrix.shape[0] - 1, e2._interaction_matrix.shape[1] - 1)
        t0 = time.perf_counter()
        svd = __import__("sklearn.decomposition", fromlist=["TruncatedSVD"]).TruncatedSVD(
            n_components=k, random_state=42)
        svd.fit(e2._interaction_matrix)
        t_svd_fit = time.perf_counter() - t0

        train_timing = {
            "train_total_s": round(t_train, 3),
            "build_features_s": round(t_build, 3),
            "svd_fit_s": round(t_svd_fit, 3),
            "components": int(k),
            "matrix_users": int(e2._interaction_matrix.shape[0]),
            "matrix_items": int(e2._interaction_matrix.shape[1]),
            "model_file_bytes": os.path.getsize(settings.MODEL_PATH),
        }
        report["train_timing"] = train_timing
        print("TRAIN:", json.dumps(train_timing))

        # ── 2. Full-dataset correctness distribution ────────────────────────
        cat_map = products_df.set_index("product_id")["category"].to_dict()

        per_request: list[float] = []
        dist: dict[str, int] = {}
        reason_counts: dict[str, int] = {}
        match_top1 = 0
        match_top10 = 0
        event_having_match_denom = 0
        no_events = 0
        flags: list[dict] = []
        list_bucket: dict[str, dict[tuple, int]] = {"svd": {}, "cold_start": {}, "popular": {}}

        for cid, _consent in all_customers:
            dom = dominant_category(cid, events_df, cat_map) if cid in event_having else None

            t0 = time.perf_counter()
            recs = engine.recommend(customer_id=cid, n=10,
                                    events_df=events_df, products_df=products_df)
            per_request.append(time.perf_counter() - t0)

            if not recs:
                flags.append({"customer_id": cid, "issue": "no_recs"})
                continue

            src = recs[0]["source"]
            dist[src] = dist.get(src, 0) + 1
            for r in recs:
                reason_counts[r["reason_code"]] = reason_counts.get(r["reason_code"], 0) + 1

            top_cat = recs[0].get("category")
            top10_cats = {r.get("category") for r in recs}

            if dom is not None:
                event_having_match_denom += 1
                if top_cat == dom:
                    match_top1 += 1
                if dom in top10_cats:
                    match_top10 += 1
                if src in ("svd", "cold_start") and dom not in top10_cats:
                    flags.append({
                        "customer_id": cid,
                        "issue": "dominant_category_absent_from_top10",
                        "dominant": dom,
                        "top_cat": top_cat,
                        "source": src,
                    })
            else:
                no_events += 1

            list_bucket[src][tuple(r["product_id"] for r in recs)] = (
                list_bucket[src].get(tuple(r["product_id"] for r in recs), 0) + 1)

        consenting_dist = {s: 0 for s in ("svd", "cold_start", "popular")}
        for cid, consent in all_customers:
            if not consent:
                continue
            recs = engine.recommend(customer_id=cid, n=10,
                                    events_df=events_df, products_df=products_df)
            if recs:
                consenting_dist[recs[0]["source"]] = consenting_dist.get(recs[0]["source"], 0) + 1

        dup_report = {}
        for src, bucket in list_bucket.items():
            if not bucket:
                continue
            top_shared = max(bucket.values())
            dup_report[src] = {
                "customers": sum(bucket.values()),
                "distinct_lists": len(bucket),
                "max_customers_sharing_one_list": top_shared,
            }

        correctness = {
            "customers_scored": sum(dist.values()),
            "no_recs_customers": (len(flags) and sum(1 for f in flags if f["issue"] == "no_recs")) or 0,
            "source_distribution": dict(dist),
            "consenting_source_distribution": consenting_dist,
            "reason_code_distribution": dict(sorted(reason_counts.items(), key=lambda kv: -kv[1])),
            "event_having_customers": event_having_match_denom,
            "no_event_customers": no_events,
            "top1_category_match_among_event_having": round(match_top1 / event_having_match_denom * 100, 2)
            if event_having_match_denom else 0.0,
            "dominant_category_in_top10_among_event_having": round(match_top10 / event_having_match_denom * 100, 2)
            if event_having_match_denom else 0.0,
            "duplicate_lists_per_source": dup_report,
        }
        report["correctness"] = correctness
        report["request_latency_inprocess"] = lat_stats(per_request)
        report["flags"] = flags[:50]

        print("CORRECTNESS:", json.dumps(correctness))
        print("INPROC LATENCY:", json.dumps(report["request_latency_inprocess"]))
        print(f"FLAG count: {len(flags)}; shown {len(report['flags'])} of 50")

        # ── 3. Batch store timing (real _store_recommendations) ────────────
        consent_ids = [c[0] for c in all_customers if c[1]]
        t0 = time.perf_counter()
        computed = await asyncio.to_thread(_pure_compute, engine, events_df, products_df, consent_ids)
        t_scoring = time.perf_counter() - t0

        t0 = time.perf_counter()
        await _store_recommendations(db, engine, events_df, products_df)
        await db.commit()
        t_store_total = time.perf_counter() - t0

        rec_cnt_after = (await db.execute(
            select(func.count(Recommendation.customer_id)))).scalar()
        report["batch_store"] = {
            "consenting_customers_scored": len(computed),
            "scoring_only_s": round(t_scoring, 3),
            "store_total_incl_database_s": round(t_store_total, 3),
            "stored_rows_after": int(rec_cnt_after),
        }
        print("BATCH STORE:", json.dumps(report["batch_store"]))

        # ── 4. Offer engine (startup path) timing ───────────────────────────
        off = OfferEngine(db)
        t0 = time.perf_counter()
        n_assign = await off.assign_offers()
        t_offers = time.perf_counter() - t0
        await db.commit()
        seg_cnt = (await db.execute(select(func.count(CustomerSegment.customer_id)))).scalar()
        report["offers"] = {
            "assign_offers_s": round(t_offers, 3),
            "assignments": int(n_assign),
            "segment_rows": int(seg_cnt),
        }
        print("OFFERS:", json.dumps(report["offers"]))

        # ── 5. Model memory / size ──────────────────────────────────────────
        n_users, n_items = engine._interaction_matrix.shape
        item_fac = engine._item_factors
        user_fac = engine._user_factors
        content = engine._item_content_vectors
        report["model_size"] = {
            "matrix_shape": [n_users, n_items],
            "interaction_nnz": int(engine._interaction_matrix.nnz),
            "user_factors_shape": list(user_fac.shape),
            "item_factors_shape": list(item_fac.shape),
            "content_vectors_shape": list(content.shape),
            "model_file_mb": round(os.path.getsize(settings.MODEL_PATH) / 1e6, 2),
            "estimated_ram_mb": round(
                ((n_users * user_fac.shape[1]) + (n_items * item_fac.shape[1]) + content.size)
                * user_fac.dtype.itemsize / 1e6,
                3,
            ),
        }
        print("MODEL SIZE:", json.dumps(report["model_size"]))

        # e2e sanity on the 3 known fix customers
        e2e_ids = [c for c in ("ea9ad3b5-b3b8-47c2-a5db-4a9267fa5ef5",
                               "37b4411b-2d47-4135-9eff-0ada8372c5b8",
                               "01e2376e-9f19-4a76-94b4-04ad665cc90b")]
        e2e_report = {}
        for cid in e2e_ids:
            recs = engine.recommend(customer_id=cid, n=10,
                                    events_df=events_df, products_df=products_df)
            e2e_report[cid] = {
                "source": recs[0]["source"] if recs else None,
                "top_cats": [r.get("category") for r in recs][:5] if recs else [],
            }
        report["e2e_fix_customers"] = e2e_report
        print("E2E FIX CUSTOMERS:", json.dumps(e2e_report))

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\nReport written to {OUT_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
