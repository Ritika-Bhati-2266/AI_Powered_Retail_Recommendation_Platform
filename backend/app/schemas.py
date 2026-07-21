"""
Pydantic v2 models for all API request/response shapes.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ── Event ────────────────────────────────────────────────────────────────────

class EventCreate(BaseModel):
    customer_id: str
    event_type: str
    product_id: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Optional[dict] = None


class EventOut(BaseModel):
    status: str = "ok"
    event_id: str


# ── Customer ─────────────────────────────────────────────────────────────────

class CustomerMetrics(BaseModel):
    total_views: int = 0
    total_purchases: int = 0
    total_cart_events: int = 0
    total_email_engagement: int = 0
    avg_session_duration_minutes: float = 0.0
    days_since_last_activity: int = 0
    lifetime_value: float = 0.0
    preferred_category: str = ""
    preferred_price_tier: str = ""


class SegmentOut(BaseModel):
    segment: str
    assigned_at: datetime


class CustomerOut(BaseModel):
    customer_id: str
    name: str
    email: str
    consent_status: bool
    currency: str = "USD"
    role: str = "customer"
    segments: list[SegmentOut] = []
    metrics: CustomerMetrics = CustomerMetrics()
    category_preferences: list[str] = []

    class Config:
        from_attributes = True


class CustomerCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: str = Field(default="", max_length=255)
    consent_given: bool = True
    currency: str = "USD"
    category_preferences: list[str] = Field(default_factory=list, description="Categories the customer is interested in (cold-start)")


class CustomerUpdate(BaseModel):
    """Partial update for customer settings (e.g. currency)."""
    currency: Optional[str] = None


class CustomerSearchResult(BaseModel):
    customer_id: str
    name: str
    email: str
    currency: str = "USD"


# ── Recommendation ───────────────────────────────────────────────────────────

class RecommendationOut(BaseModel):
    product_id: str
    name: str
    category: str
    subcategory: Optional[str] = None
    brand: Optional[str] = None
    price: float
    currency: str = "USD"
    symbol: str = "$"
    image_url: Optional[str] = None
    score: float
    reason_code: str
    reason_text: str


# ── Offer ────────────────────────────────────────────────────────────────────

class OfferOut(BaseModel):
    offer_id: str
    title: str
    description: Optional[str] = None
    discount_type: str
    discount_value: float
    valid_until: datetime
    currency: str = "USD"
    symbol: str = "$"

    class Config:
        from_attributes = True


# ── Product ──────────────────────────────────────────────────────────────────

class ProductSearchResult(BaseModel):
    product_id: str
    name: str
    category: str = ""
    subcategory: str = ""
    brand: str = ""
    price: float
    currency: str = "USD"
    symbol: str = "$"
    image_url: str = ""


class ProductOut(BaseModel):
    product_id: str
    name: str
    category: str = ""
    subcategory: str = ""
    brand: str = ""
    price: float
    currency: str = "USD"
    symbol: str = "$"
    image_url: str = ""
    class Config:
        from_attributes = True


# ── Admin ────────────────────────────────────────────────────────────────────

class AdminActionOut(BaseModel):
    status: str
    message: Optional[str] = None


class TrainOut(BaseModel):
    status: str = "training_started"
    message: str = "Model training has been queued in the background."


class AssignOffersOut(BaseModel):
    status: str = "offers_assigned"
    assignments_count: int
    message: str = "Offers assigned to qualifying customers."


class SegmentCountOut(BaseModel):
    segment: str
    count: int


class SystemStatsOut(BaseModel):
    total_customers: int
    consent_rate: float
    total_events: int
    total_products: int
    total_offers: int
    active_offers: int
    total_assignments: int
    segment_distribution: list[SegmentCountOut]
