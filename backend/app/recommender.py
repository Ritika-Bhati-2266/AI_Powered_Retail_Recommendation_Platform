"""
RecommendationEngine: Hybrid collaborative + content-based filtering.
Uses TruncatedSVD (sklearn) for matrix factorization + cosine similarity
for content-based fallback, with interpretable reason codes.

Privacy-safe: all features are behavioural only — no demographics,
no age, no gender, no location. Consent-gated at the API layer.
"""
import logging
import os

import joblib
import numpy as np
import pandas as pd
from scipy.sparse import coo_matrix, csr_matrix
from sklearn.decomposition import TruncatedSVD
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import normalize

logger = logging.getLogger(__name__)

# Weight applied to each behavioural signal when building the user-item
# interaction matrix (purchases dominate, passive views weight least).
EVENT_WEIGHTS: dict[str, float] = {
    "purchase": 5.0,
    "add_to_cart": 3.0,
    "wishlist_add": 2.5,
    "email_click": 2.0,
    "page_view": 1.0,
    "email_open": 0.5,
    "remove_from_cart": -1.0,
}


class RecommendationEngine:
    """Hybrid recommender using TruncatedSVD + content-based similarity."""

    def __init__(self, settings):
        self.settings = settings
        self.svd: TruncatedSVD | None = None
        self._user_ids: list[str] = []
        self._item_ids: list[str] = []
        self._user_index: dict[str, int] = {}
        self._item_index: dict[str, int] = {}
        self._product_details: dict[str, dict] = {}
        self._interaction_matrix: csr_matrix | None = None
        self._user_factors: np.ndarray | None = None
        self._item_factors: np.ndarray | None = None
        self._item_content_vectors: np.ndarray | None = None
        self._is_trained: bool = False

    # ── Feature Building ───────────────────────────────────────────────

    def build_features(
        self,
        events_df: pd.DataFrame,
        products_df: pd.DataFrame,
    ) -> None:
        """Build user-item interaction matrix + item content features."""
        logger.info("Building user-item interaction matrix and features...")

        self._product_details = products_df.set_index("product_id").to_dict(orient="index")

        # Identify users and items.
        # NOTE: items are restricted to the current product catalog only.
        # We intentionally do NOT include product_ids that appear in events_df
        # but not in products_df — those are discontinued/invalid products and
        # including them let the model recommend items with no real details
        # (they'd fall back to "Unknown Product" / price 0.0 downstream).
        event_users = events_df["customer_id"].unique()
        all_product_ids = products_df["product_id"].unique()
        all_items = sorted(set(all_product_ids))
        all_users = sorted(event_users)

        self._user_ids = all_users
        self._item_ids = all_items
        self._user_index = {uid: i for i, uid in enumerate(all_users)}
        self._item_index = {pid: i for i, pid in enumerate(all_items)}

        n_users = len(all_users)
        n_items = len(all_items)
        logger.info(f"Building matrix: {n_users} users x {n_items} items")

        # ── Build interaction matrix with weighted events (vectorized) ──
        valid = (
            events_df["customer_id"].isin(self._user_index)
            & events_df["product_id"].isin(self._item_index)
        )
        sub = events_df.loc[valid, ["customer_id", "product_id", "event_type"]]

        if len(sub) > 0:
            rows = sub["customer_id"].map(self._user_index).to_numpy()
            cols = sub["product_id"].map(self._item_index).to_numpy()
            vals = sub["event_type"].map(EVENT_WEIGHTS).fillna(0.5).to_numpy(dtype=np.float32)

            mat = coo_matrix((vals, (rows, cols)), shape=(n_users, n_items), dtype=np.float32).tocsr()
        else:
            mat = csr_matrix((n_users, n_items), dtype=np.float32)

        # Log transform, preserving sign
        mat.data = np.log1p(np.abs(mat.data)) * np.sign(mat.data)
        self._interaction_matrix = mat

        # ── Build item content features (category, brand, price tier) ──
        cat_dummies = pd.get_dummies(products_df["category"], prefix="cat")
        brand_dummies = pd.get_dummies(products_df["brand"], prefix="brand")

        price_df = products_df[["product_id", "price"]].copy()
        price_df["price_tier"] = pd.cut(
            price_df["price"],
            bins=[0, 20, 50, 100, 200, 10000],
            labels=["budget", "economy", "mid", "premium", "luxury"],
        )
        price_dummies = pd.get_dummies(price_df["price_tier"], prefix="price")

        content_df = pd.concat([cat_dummies, brand_dummies, price_dummies], axis=1)
        content_df.index = products_df["product_id"]

        # Build vectors in item order (all_items == products_df["product_id"]
        # now, so every id is guaranteed present in content_df.index)
        content_vecs = []
        for pid in all_items:
            if pid in content_df.index:
                vec = content_df.loc[pid].values.astype(np.float32)
                content_vecs.append(vec)
            else:
                vec = np.zeros(content_df.shape[1], dtype=np.float32)
                content_vecs.append(vec)
        self._item_content_vectors = np.array(content_vecs)
        self._item_content_vectors = normalize(self._item_content_vectors, axis=1)

        logger.info(
            f"Features built: {self._interaction_matrix.shape[0]} users, "
            f"{self._interaction_matrix.shape[1]} items, "
            f"{self._item_content_vectors.shape[1]} content features"
        )

    # ── Training ──────────────────────────────────────────────────────

    def train(
        self,
        events_df: pd.DataFrame,
        products_df: pd.DataFrame,
        n_components: int = 50,
    ) -> None:
        """Train the SVD-based collaborative filtering model."""
        self.build_features(events_df, products_df)

        mat = self._interaction_matrix
        n_users, n_items = mat.shape

        if n_users < 3 or n_items < 3:
            logger.warning("Too few users or items to train SVD.")
            self._is_trained = False
            return

        k = min(n_components, n_users - 1, n_items - 1)
        if k < 2:
            k = 2

        logger.info(f"Training TruncatedSVD with {k} components...")
        self.svd = TruncatedSVD(n_components=k, random_state=42)
        self.svd.fit(mat)

        self._user_factors = self.svd.transform(mat)
        self._item_factors = self.svd.components_.T

        self._is_trained = True
        logger.info(
            f"SVD training complete. Explained variance: "
            f"{self.svd.explained_variance_ratio_.sum():.3f}"
        )
        self.save()

    # ── Recommendation ────────────────────────────────────────────────

    def recommend(
        self,
        customer_id: str,
        n: int = 10,
        events_df: pd.DataFrame | None = None,
        products_df: pd.DataFrame | None = None,
    ) -> list[dict]:
        """Generate top-N hybrid recommendations.

        Every returned dict carries a ``source`` flag so callers can tell the
        provenance of the recommendation at a glance / for debugging:
          - ``svd``       → drove by the trained factor matrices (either the
                            customer's precomputed row OR a live projection of
                            their own interaction vector into the SVD space).
          - ``cold_start``→ behavior-aware fallback: biased toward the
                            customer's own event categories (recent clicks).
          - ``popular``   → pure global popularity, last resort (no signal).

        Customers absent from the trained user matrix are NOT silently served
        the generic popular list: their live interaction vector is projected
        into the SVD latent space, so new/low-activity customers still get
        personalised collaborative + content signals from their own behaviour.
        """
        if not self._is_trained or self.svd is None:
            logger.warning("Model not trained, using behavior-aware fallback.")
            return self._fallback_recommendations(n, events_df, customer_id, products_df)

        # Resolve this customer's behavioural signal.
        if customer_id in self._user_index:
            user_idx = self._user_index[customer_id]
            interactions = self._interaction_matrix[user_idx].toarray().flatten()
            user_vec = self._user_factors[user_idx]
            signal_source = "model_matrix"
        else:
            interactions = self._build_user_interactions(customer_id, events_df)
            if interactions is not None:
                # Fold the customer's live behaviour into the trained latent
                # space without retraining the model.
                user_vec = self.svd.transform(interactions.reshape(1, -1)).flatten()
                signal_source = "live_projection"
            else:
                interactions = None
                signal_source = None

        if signal_source is None or interactions is None or not np.any(interactions != 0):
            # No usable behavioural signal (in matrix or live) → category-aware
            # cold start from the customer's own recent event categories, else
            # global popularity as the absolute last resort.
            logger.info(
                "Customer %s has no behavioural signal for SVD; using category-aware cold start.",
                customer_id,
            )
            return self._fallback_recommendations(n, events_df, customer_id, products_df)

        if signal_source == "live_projection":
            logger.info(
                "Customer %s not in trained user index (%d users); projecting live "
                "interaction vector for SVD personalisation.",
                customer_id,
                len(self._user_index),
            )

        # Collaborative scores
        collab_scores = self._item_factors @ user_vec

        # Content-based scores from the customer's own interactions
        interacted_items = np.where(interactions > 0)[0]

        if len(interacted_items) > 0:
            weights = interactions[interacted_items]
            user_content_profile = np.average(
                self._item_content_vectors[interacted_items],
                axis=0,
                weights=weights,
            ).reshape(1, -1)
            content_scores = cosine_similarity(
                user_content_profile, self._item_content_vectors
            ).flatten()
        else:
            content_scores = np.zeros(len(self._item_ids))

        # Normalize and hybridise
        c_min, c_max = collab_scores.min(), collab_scores.max()
        collab_scores = (collab_scores - c_min) / (c_max - c_min + 1e-10)
        t_min, t_max = content_scores.min(), content_scores.max()
        content_scores = (content_scores - t_min) / (t_max - t_min + 1e-10)
        hybrid_scores = 0.7 * collab_scores + 0.3 * content_scores

        # Exclude purchased
        purchased = set()
        if events_df is not None:
            purchased = set(
                events_df[
                    (events_df["customer_id"] == customer_id)
                    & (events_df["event_type"] == "purchase")
                ]["product_id"].unique()
            )

        scored = [
            (self._item_ids[i], float(hybrid_scores[i]))
            for i in range(len(self._item_ids))
            if self._item_ids[i] not in purchased
        ]
        scored.sort(key=lambda x: x[1], reverse=True)

        recommendations = []
        for product_id, hscore in scored[:n]:
            details = self._product_details.get(product_id, {})
            if events_df is not None and products_df is not None:
                rc, rt = self.get_reason_code(
                    customer_id, product_id, events_df, products_df
                )
            else:
                rc, rt = "svd_personalized", "Recommended based on your shopping history"

            recommendations.append({
                "product_id": product_id,
                "name": details.get("name", "Unknown Product"),
                "category": details.get("category", ""),
                "subcategory": details.get("subcategory", ""),
                "brand": details.get("brand", ""),
                "price": float(details.get("price", 0)),
                "rating": details.get("rating"),
                "discount_percent": details.get("discount_percent"),
                "original_price": details.get("original_price"),
                "image_url": details.get("image_url", ""),
                "score": round(hscore, 4),
                "reason_code": rc,
                "reason_text": rt,
                "source": "svd",
            })

        return recommendations

    def _build_user_interactions(
        self,
        customer_id: str,
        events_df: pd.DataFrame | None,
    ) -> np.ndarray | None:
        """Build a weighted log1p interaction vector (length = n_items) for a
        customer from their LIVE events, mapped onto the trained item index.

        Mirrors the preprocessing used in build_features so an SVD projection
        is directly comparable to the trained factor matrices. Returns None if
        the customer has no usable interactions (product in catalog).
        """
        if events_df is None or len(events_df) == 0:
            return None
        if not {"customer_id", "product_id", "event_type"}.issubset(events_df.columns):
            return None

        sub = events_df[
            (events_df["customer_id"] == customer_id)
            & (events_df["product_id"].notna())
        ]
        if len(sub) == 0:
            return None

        valid = sub["product_id"].isin(self._item_index)
        sub = sub.loc[valid]
        if len(sub) == 0:
            return None

        cols = sub["product_id"].map(self._item_index).to_numpy()
        vals = sub["event_type"].map(EVENT_WEIGHTS).fillna(0.5).to_numpy(dtype=np.float32)

        row = np.zeros(len(self._item_ids), dtype=np.float32)
        for c, v in zip(cols, vals, strict=False):
            row[c] += v
        row = np.log1p(np.abs(row)) * np.sign(row)
        return row

    def _customer_category_interests(
        self,
        customer_id: str | None,
        events_df: pd.DataFrame | None,
        products_df: pd.DataFrame | None,
    ) -> dict[str, float]:
        """Summarise a customer's own recent behaviour into an ordered set of
        category interests (weighted by event type). Empty dict when there is
        no behavioural signal."""
        if events_df is None or len(events_df) == 0 or customer_id is None:
            return {}
        sub = events_df[events_df["customer_id"] == customer_id]
        if len(sub) == 0:
            return {}

        if (
            products_df is not None
            and len(products_df) > 0
            and {"product_id", "category"}.issubset(products_df.columns)
        ):
            cat_map = products_df.set_index("product_id")["category"].to_dict()
        else:
            cat_map = {pid: info.get("category") for pid, info in self._product_details.items()}

        interests: dict[str, float] = {}
        for _, ev in sub.iterrows():
            pid = ev.get("product_id")
            if not pid:
                continue
            cat = cat_map.get(pid)
            if not cat:
                continue
            w = EVENT_WEIGHTS.get(ev.get("event_type"), 0.5)
            interests[cat] = interests.get(cat, 0.0) + max(w, 0.0)
        return interests

    def _fallback_recommendations(
        self,
        n: int = 10,
        events_df: pd.DataFrame | None = None,
        customer_id: str | None = None,
        products_df: pd.DataFrame | None = None,
    ) -> list[dict]:
        """
        Return recommendations when no model/matrix signal is available.

        Behavior-aware: when the customer has their own event history, the list
        is biased toward the categories they actually browse / buy from
        (reason_code ``cold_start_category_based``, source ``cold_start``),
        ranked by real interaction popularity within those categories. Only
        when there is NO behavioural signal at all does it degrade to pure
        global popularity (reason_code ``popular``) — and to price-descending
        order if no event data is passed in at all.
        """
        if not self._product_details:
            return []

        counts: dict = {}
        if events_df is not None and len(events_df) > 0:
            counts = (
                events_df["product_id"]
                .dropna()
                .value_counts()
                .to_dict()
            )

        interests = self._customer_category_interests(customer_id, events_df, products_df)
        use_cold_start = bool(interests)

        scored = []
        for pid, details in self._product_details.items():
            category = details.get("category", "")
            if use_cold_start and category not in interests:
                continue
            scored.append({
                "product_id": pid,
                **{k: details.get(k, "") for k in ["name", "category", "subcategory", "brand", "image_url"]},
                "price": float(details.get("price", 0)),
                "rating": details.get("rating"),
                "discount_percent": details.get("discount_percent"),
                "original_price": details.get("original_price"),
                "score": 0.0,
                "reason_code": "cold_start_category_based" if use_cold_start else "popular",
                "reason_text": (
                    f"Based on your browsing in {category}" if use_cold_start else "Popular item"
                ),
                "source": "cold_start" if use_cold_start else "popular",
            })

        if use_cold_start:
            scored.sort(
                key=lambda x: (interests.get(x["category"], 0.0), counts.get(x["product_id"], 0)),
                reverse=True,
            )
        elif counts:
            scored.sort(key=lambda x: counts.get(x["product_id"], 0), reverse=True)
        else:
            scored.sort(key=lambda x: x["price"], reverse=True)

        return scored[:n]

    def get_reason_code(
        self,
        customer_id: str,
        product_id: str,
        events_df: pd.DataFrame,
        products_df: pd.DataFrame,
    ) -> tuple[str, str]:
        """Interpretable reason code from interaction history."""
        customer_events = events_df[events_df["customer_id"] == customer_id]
        prod_info = products_df[products_df["product_id"] == product_id]
        if prod_info.empty:
            return ("popular", "Popular item")

        category = prod_info.iloc[0]["category"]

        # Purchased in same category?
        purchased_cats = customer_events[
            customer_events["event_type"] == "purchase"
        ].merge(
            products_df[["product_id", "category"]], on="product_id", how="left"
        )["category"].dropna().unique()
        if category in purchased_cats:
            return ("purchased_category", f"You previously purchased {category} items")

        # Viewed this product?
        viewed_pids = customer_events[
            customer_events["event_type"] == "page_view"
        ]["product_id"].dropna().unique()
        if product_id in viewed_pids:
            return ("viewed_product", "You viewed this item recently")

        # Viewed same category?
        viewed_cats = customer_events[
            customer_events["event_type"] == "page_view"
        ].merge(
            products_df[["product_id", "category"]], on="product_id", how="left"
        )["category"].dropna().unique()
        if category in viewed_cats:
            return ("viewed_category", f"You've been browsing {category}")

        # Cart recovery?
        cart_pids = customer_events[
            customer_events["event_type"] == "add_to_cart"
        ]["product_id"].dropna().unique()
        purchased_pids = customer_events[
            customer_events["event_type"] == "purchase"
        ]["product_id"].dropna().unique()
        if product_id in cart_pids and product_id not in purchased_pids:
            return ("cart_recovery", "This item was in your cart")

        # Wishlist?
        wishlist_pids = customer_events[
            customer_events["event_type"] == "wishlist_add"
        ]["product_id"].dropna().unique()
        if product_id in wishlist_pids:
            return ("wishlist_item", "This item is on your wishlist")

        return ("trending_in_segment", "Popular among similar customers")

    # ── Persistence ───────────────────────────────────────────────────

    def save(self) -> None:
        """Serialize the trained model to disk."""
        model_path = self.settings.MODEL_PATH
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        state = {
            "svd": self.svd,
            "user_ids": self._user_ids,
            "item_ids": self._item_ids,
            "user_index": self._user_index,
            "item_index": self._item_index,
            "product_details": self._product_details,
            "interaction_matrix": self._interaction_matrix,
            "user_factors": self._user_factors,
            "item_factors": self._item_factors,
            "item_content_vectors": self._item_content_vectors,
            "is_trained": self._is_trained,
        }
        joblib.dump(state, model_path)
        logger.info(f"Model saved to {model_path}")

    def load(self) -> bool:
        """Load a trained model from disk. Returns True if successful."""
        model_path = self.settings.MODEL_PATH
        if not os.path.exists(model_path):
            logger.info(f"No model found at {model_path}")
            return False
        try:
            state = joblib.load(model_path)
            self.svd = state["svd"]
            self._user_ids = state["user_ids"]
            self._item_ids = state["item_ids"]
            self._user_index = state["user_index"]
            self._item_index = state["item_index"]
            self._product_details = state["product_details"]
            self._interaction_matrix = state["interaction_matrix"]
            self._user_factors = state["user_factors"]
            self._item_factors = state["item_factors"]
            self._item_content_vectors = state["item_content_vectors"]
            self._is_trained = state["is_trained"]
            logger.info(f"Model loaded from {model_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False
