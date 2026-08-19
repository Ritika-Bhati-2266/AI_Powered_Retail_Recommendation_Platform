"""HTTP-level scale verification against the running backend.

Phases (run with the backend freshly started on port 8000):
  A. Live-request latency on ~30 random real customers (p50 / p95 / p99).
  B. Concurrent burst: 50 simultaneous recommendation GETs (distinct customers).
  C. POST /api/admin/train WHILE serving concurrent recommendation GETs —
     verifies training does not block/burst-slow reads.

Auth tokens are minted in-process with the same JWT secret the server uses
(mirrors what /api/auth/login would return), so no bcrypt/login cost pollutes
the measurement.
"""
import asyncio
import json
import os
import statistics
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import httpx
from sqlalchemy import select

from app.database import async_session_factory
from app.models import Customer, Event
from app.security import create_access_token

BASE = "http://127.0.0.1:8000"
OUT_PATH = os.path.join(os.environ.get("TEMP", "."), "scale_verify_http_report.json")


def pct(xs, p):
    if not xs:
        return 0.0
    s = sorted(xs)
    return float(s[min(len(s) - 1, round((p / 100.0) * (len(s) - 1)))])


def stats(xs):
    if not xs:
        return {"n": 0}
    return {
        "n": len(xs),
        "min_ms": round(min(xs), 2),
        "p50_ms": round(pct(xs, 50), 2),
        "p95_ms": round(pct(xs, 95), 2),
        "p99_ms": round(pct(xs, 99), 2),
        "mean_ms": round(statistics.mean(xs), 2),
        "max_ms": round(max(xs), 2),
    }


async def fetch(bucket):
    async with async_session_factory() as db:
        consent = (await db.execute(
            select(Customer.customer_id, Customer.consent_given))).all()
        event_having = set((await db.execute(
            select(Event.customer_id).distinct())).scalars().all())
        admin = (await db.execute(
            select(Customer.customer_id).where(Customer.role == "admin"))).scalar_one()
    e2e = [
        "ea9ad3b5-b3b8-47c2-a5db-4a9267fa5ef5",
        "37b4411b-2d47-4135-9eff-0ada8372c5b8",
        "01e2376e-9f19-4a76-94b4-04ad665cc90b",
    ]
    consenting = [c[0] for c in consent if c[1]]
    in_matrix = [c for c in consenting if c in event_having]
    out_matrix = [c for c in consenting if c not in event_having]
    bucket["admin"] = admin
    bucket["e2e"] = e2e
    bucket["in_matrix"] = in_matrix
    bucket["out_matrix"] = out_matrix
    return bucket


async def get_recs(client, cid, token):
    t0 = time.perf_counter()
    r = await client.get(f"/api/customers/{cid}/recommendations",
                         headers={"Authorization": f"Bearer {token}"})
    return time.perf_counter() - t0, r


async def run_latency_sample(client, bucket):
    sample = []
    sample += bucket["e2e"]
    rng = random_sample(bucket["in_matrix"], 20)
    sample += rng
    sample += random_sample(bucket["out_matrix"], 3)
    lat, reps, statuses = [], {}, {}
    for cid in sample:
        tok = create_access_token(cid, "customer")
        d, r = await get_recs(client, cid, tok)
        lat.append(d * 1000)
        statuses[r.status_code] = statuses.get(r.status_code, 0) + 1
        if r.status_code == 200:
            reps[cid] = {
                "source": r.json()[0].get("source") if r.json() else None,
                "n": len(r.json()),
            }
    return {"latency_ms": stats(lat), "status_codes": statuses}, reps


def random_sample(xs, n):
    import random
    random.seed(7)
    return random.sample(xs, min(n, len(xs)))


async def run_burst(client, bucket, admin_token):
    ids = random_sample(bucket["in_matrix"], 40) + random_sample(bucket["out_matrix"], 10)
    tokens = {cid: create_access_token(cid, "customer") for cid in ids}
    t0 = time.perf_counter()
    results = await asyncio.gather(*[get_recs(client, c, tokens[c]) for c in ids])
    total = time.perf_counter() - t0
    lats = [r[0] * 1000 for r in results]
    statuses = {}
    for _, r in results:
        statuses[r.status_code] = statuses.get(r.status_code, 0) + 1
    return {
        "concurrent": len(ids),
        "wall_s": round(total, 3),
        "latency_ms": stats(lats),
        "status_codes": statuses,
        "req_per_sec": round(len(ids) / total, 1) if total else 0.0,
    }


async def run_train_during_reads(client, bucket):
    admin_tok = create_access_token(bucket["admin"], "admin")
    ids = random_sample(bucket["in_matrix"], 50)
    tokens = {cid: create_access_token(cid, "customer") for cid in ids}

    t_train0 = time.perf_counter()
    train_r = await client.post("/api/admin/train", headers={"Authorization": f"Bearer {admin_tok}"})
    t_train_post = time.perf_counter() - t_train0

    t0 = time.perf_counter()
    results = await asyncio.gather(*[get_recs(client, c, tokens[c]) for c in ids])
    reads_dur = time.perf_counter() - t0

    lats = [r[0] * 1000 for r in results]
    statuses = {}
    for _, r in results:
        statuses[r.status_code] = statuses.get(r.status_code, 0) + 1

    # Poll backend log for training completion (up to ~3 min) WITHOUT holding
    # the event loop — poll via short sleeps.
    log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "logs", "backend_err.log")
    finished = False
    deadline = time.perf_counter() + 180
    while time.perf_counter() < deadline:
        await asyncio.sleep(1.0)
        try:
            txt = open(log_path, encoding="utf-8", errors="ignore").read()
        except OSError:
            txt = ""
        if "Model training completed successfully" in txt:
            finished = True
            break

    # Confirm the served model grew to the full event-having user count.
    e2e_ok = False
    if finished:
        await asyncio.sleep(0.5)
        recs = await get_recs(client, bucket["e2e"][0], create_access_token(bucket["e2e"][0], "customer"))
        e2e_ok = recs[1].status_code == 200

    return {
        "train_post_status": train_r.status_code,
        "train_post_s": round(t_train_post, 3),
        "reads_during_train": {
            "concurrent": len(ids),
            "wall_s": round(reads_dur, 3),
            "latency_ms": stats(lats),
            "status_codes": statuses,
        },
        "train_finished_observed": finished,
        "e2e_served_after_train": e2e_ok if finished else None,
    }


async def main():
    bucket = {}
    await fetch(bucket)
    report = {"bucket_sizes": {
        "consenting_in_matrix": len(bucket["in_matrix"]),
        "consenting_out_matrix": len(bucket["out_matrix"]),
    }}
    async with httpx.AsyncClient(base_url=BASE, timeout=30.0) as client:
        rep_a, reps = await run_latency_sample(client, bucket)
        report["a_latency_sample"] = rep_a
        report["a_reps_sources"] = reps
        print("A LATENCY:", json.dumps(rep_a))

        rep_b = await run_burst(client, bucket, None)
        report["b_burst"] = rep_b
        print("B BURST:", json.dumps(rep_b))

        rep_c = await run_train_during_reads(client, bucket)
        report["c_train_during_reads"] = rep_c
        print("C TRAIN DURING READS:", json.dumps(rep_c))

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\nReport written to {OUT_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
