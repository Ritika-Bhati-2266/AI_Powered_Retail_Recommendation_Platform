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
    password: str = Field(..., min_length=8, max_length=128, description="Account password (min 8 characters)")
    consent_given: bool = True
    currency: str = "USD"
    category_preferences: list[str] = Field(default_factory=list, description="Categories the customer is interested in (cold-start)")


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=1, max_length=128)


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    customer_id: str
    name: str
    email: str
    role: str = "customer"


class CustomerUpdate(BaseModel):
    """Partial update for customer settings (e.g. currency, consent)."""
    currency: Optional[str] = None
    consent_given: Optional[bool] = None


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
    rating: Optional[float] = None
    discount_percent: Optional[float] = None
    original_price: Optional[float] = None
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
    rating: Optional[float] = None
    discount_percent: Optional[float] = None
    original_price: Optional[float] = None


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
    rating: Optional[float] = None
    discount_percent: Optional[float] = None
    original_price: Optional[float] = None
    class Config:
        from_attributes = True


# ── Order ────────────────────────────────────────────────────────────────────

class OrderItemCreate(BaseModel):
    product_id: str
    quantity: int = Field(default=1, ge=1)


class OrderCreate(BaseModel):
    items: list[OrderItemCreate] = Field(..., min_length=1)
    shipping_name: Optional[str] = None
    shipping_address: Optional[str] = None


class OrderItemOut(BaseModel):
    order_item_id: str
    product_id: Optional[str] = None
    product_name_snapshot: str
    quantity: int
    unit_price: float
    subtotal: float


class OrderOut(BaseModel):
    order_id: str
    customer_id: str
    total_amount: float
    currency: str = "USD"
    status: str = "placed"
    shipping_name: Optional[str] = None
    shipping_address: Optional[str] = None
    created_at: datetime
    items: list[OrderItemOut] = []


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
