"""
Regression tests for personalized recommendations.

Confirmed bug (pre-fix): every customer — regardless of behaviour — was served
the same global "popular" Electronics list because customers absent from the
trained SVD user matrix silently fell back to generic popularity.

These tests lock in the three behaviours required of the fix:
  1. SVD-based personalized recs differ across behavioral profiles.
  2. A customer NOT in the trained user matrix (stale snapshot / new signup)
     is still served personalized recs via live SVD projection of their own
     interaction vector (source == "svd"), biased to their categories.
  3. The no-model fallback is behavior-aware (category-biased cold start)
     rather than a pure global "popular" list.
  4. Re-training from all events (including a previously-unknown customer)
     folds that customer into the user matrix.
"""
import uuid

import pandas as pd
import pytest

from app.config import settings
from app.recommender import RecommendationEngine


def _product_df(items: list[tuple[str, str]]) -> pd.DataFrame:
    """Build a tiny catalog: (product_id, category)."""
    rows = []
    for pid, cat in items:
        rows.append({
            "product_id": pid,
            "name": f"{cat} item {pid}",
            "category": cat,
            "subcategory": "",
            "brand": "TestBrand",
            "price": 50.0,
            "image_url": "",
            "rating": 4.0,
            "discount_percent": None,
            "original_price": None,
        })
    return pd.DataFrame(rows)


def _events_df(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    for c in ["customer_id", "product_id", "event_type"]:
        df[c] = df[c].astype(str)
    return df


CATALOG = [
    ("p-el-1", "Electronics"), ("p-el-2", "Electronics"), ("p-el-3", "Electronics"),
    ("p-el-4", "Electronics"), ("p-el-5", "Electronics"), ("p-el-6", "Electronics"),
    ("p-el-7", "Electronics"), ("p-el-8", "Electronics"),
    ("p-au-1", "Automotive"), ("p-au-2", "Automotive"), ("p-au-3", "Automotive"),
    ("p-au-4", "Automotive"), ("p-au-5", "Automotive"), ("p-au-6", "Automotive"),
    ("p-au-7", "Automotive"), ("p-au-8", "Automotive"),
    ("p-be-1", "Beauty & Personal Care"), ("p-be-2", "Beauty & Personal Care"),
    ("p-be-3", "Beauty & Personal Care"), ("p-be-4", "Beauty & Personal Care"),
    ("p-be-5", "Beauty & Personal Care"), ("p-be-6", "Beauty & Personal Care"),
    ("p-be-7", "Beauty & Personal Care"), ("p-be-8", "Beauty & Personal Care"),
]


def _events_for(customer_id: str, products: list[str], n: int) -> list[dict]:
    """Mix stronger signals (cart/wishlist) with views, mirroring real behaviour."""
    kinds = ["page_view", "page_view", "add_to_cart", "wishlist_add", "add_to_cart"]
    return [
        {
            "event_id": f"{customer_id}-ev-{i}",
            "customer_id": customer_id,
            "product_id": products[i % len(products)],
            "event_type": kinds[i % len(kinds)],
        }
        for i in range(n)
    ]


@pytest.fixture()
def catalogs():
    products_df = _product_df(CATALOG)
    return products_df


def _trained_engine(events_df: pd.DataFrame, products_df: pd.DataFrame) -> RecommendationEngine:
    engine = RecommendationEngine(settings)
    engine.train(events_df.copy(), products_df.copy())
    return engine


def test_different_profiles_get_different_recs(catalogs):
    """Two customers with opposite behavioral profiles must NOT get the same list."""
    beauty_cid, automotive_cid = f"c-{uuid.uuid4().hex[:8]}", f"c-{uuid.uuid4().hex[:8]}"
    beauty_ids = [p for p, c in CATALOG if c == "Beauty & Personal Care"]
    auto_ids = [p for p, c in CATALOG if c == "Automotive"]

    # ≥3 training users so SVD can actually fit.
    base_events = _base_training_events()

    events_df = _events_df(
        base_events
        + _events_for(beauty_cid, beauty_ids, 20)
        + _events_for(automotive_cid, auto_ids, 20)
    )
    engine = _trained_engine(events_df, catalogs)

    beauty_recs = engine.recommend(beauty_cid, n=6, events_df=events_df, products_df=catalogs)
    auto_recs = engine.recommend(automotive_cid, n=6, events_df=events_df, products_df=catalogs)

    assert beauty_recs and auto_recs
    assert {r["product_id"] for r in beauty_recs} != {r["product_id"] for r in auto_recs}, \
        "FAIL: distinct behavioral profiles produced identical recommendation lists"
    assert all(r["source"] == "svd" for r in beauty_recs + auto_recs)
    assert sum(1 for r in beauty_recs if r["category"] == "Beauty & Personal Care") >= 4
    assert sum(1 for r in auto_recs if r["category"] == "Automotive") >= 4


def test_new_customer_not_in_matrix_gets_svd_projection(catalogs):
    """A customer created AFTER training (not in user matrix) must still be
    served personalized SVD recs from a live projection, not the popular list."""
    base_events = _base_training_events()
    engine = _trained_engine(_events_df(base_events), catalogs)

    new_cid = "brand-new-after-training"
    new_events = _events_df(
        _events_for(new_cid, ["p-be-1", "p-be-2", "p-be-3", "p-be-4"], 26)
    )
    # The model was trained BEFORE this customer existed → stale snapshot.
    assert new_cid not in engine._user_index

    recs = engine.recommend(
        new_cid, n=6,
        events_df=pd.concat([_events_df(base_events), new_events], ignore_index=True),
        products_df=catalogs,
    )

    assert recs, "no recommendations generated for out-of-matrix customer"
    assert all(r["source"] == "svd" for r in recs), \
        "FAIL: out-of-matrix customer fell back to non-SVD (popular/cold_start)"
    assert sum(1 for r in recs if r["category"] == "Beauty & Personal Care") >= 4, \
        "FAIL: new customer's recs did not reflect their own browsing category"


def _base_training_events() -> list[dict]:
    """Three distinct training customers so SVD can fit (needs ≥3 users)."""
    return (
        _events_for("base-el", ["p-el-1", "p-el-2", "p-el-3"], 30)
        + _events_for("base-au", ["p-au-1", "p-au-2", "p-au-3"], 30)
        + _events_for("base-be", ["p-be-1", "p-be-2", "p-be-3"], 30)
    )


def test_no_model_fallback_is_category_based(catalogs):
    """With no trained model, the fallback biases toward the customer's own
    browsing categories instead of a pure global popularity list."""
    engine = RecommendationEngine(settings)
    engine._product_details = catalogs.set_index("product_id").to_dict(orient="index")

    cid = "no-model-customer"
    events_df = _events_df(_events_for(cid, ["p-au-1", "p-au-2", "p-au-3", "p-au-4", "p-au-5"], 15))

    recs = engine._fallback_recommendations(
        n=6, events_df=events_df, customer_id=cid, products_df=catalogs
    )

    assert recs
    assert all(r["reason_code"] == "cold_start_category_based" for r in recs), \
        "FAIL: no-model fallback was not behavior-aware"
    assert all(r["source"] == "cold_start" for r in recs)
    assert sum(1 for r in recs if r["category"] == "Automotive") >= 5


def test_no_model_global_fallback_is_popular(catalogs):
    """A customer with NO history and no model → the last resort is global
    popularity, and it must be flagged as such."""
    engine = RecommendationEngine(settings)
    engine._product_details = catalogs.set_index("product_id").to_dict(orient="index")

    recs = engine._fallback_recommendations(n=6, events_df=None, customer_id="ghost")

    assert recs
    assert all(r["reason_code"] == "popular" for r in recs)
    assert all(r["source"] == "popular" for r in recs)


def test_retrain_folds_new_customer_into_matrix(catalogs):
    """Re-running training over ALL events (including a previously unknown
    customer) must add that customer to the user matrix so their SVD row is
    precomputed directly."""
    base_events = _base_training_events()
    events_df = _events_df(base_events)
    engine = _trained_engine(events_df, catalogs)

    new_cid = "new-customer-folds-in"
    full_events = pd.concat(
        [events_df, _events_df(_events_for(new_cid, ["p-be-1", "p-be-2"], 22))],
        ignore_index=True,
    )

    assert new_cid not in engine._user_index
    retrained = _trained_engine(full_events, catalogs)
    assert new_cid in retrained._user_index, "FAIL: retrained model did not index the new customer"
    recs = retrained.recommend(new_cid, n=6, events_df=full_events, products_df=catalogs)
    assert all(r["source"] == "svd" for r in recs)
    assert sum(1 for r in recs if r["category"] == "Beauty & Personal Care") >= 4
