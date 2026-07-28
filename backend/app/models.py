"""
SQLAlchemy ORM models for all database tables.
Uses String(36) for UUID fields for portability across database backends.
Datetimes are stored as timezone-naive UTC for compatibility with both SQLite and Postgres.
"""
import uuid
from sqlalchemy import (
    Column, String, Boolean, DateTime, Float, Integer, ForeignKey, JSON, Text,
    UniqueConstraint, Index,
)
from sqlalchemy.orm import relationship

from app.database import Base
from app.utils import utcnow


def _uuid() -> str:
    return str(uuid.uuid4())


class Customer(Base):
    __tablename__ = "customers"

    customer_id = Column(String(36), primary_key=True, default=_uuid)
    name = Column(String(255), nullable=False, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    consent_given = Column(Boolean, default=False, nullable=False)
    consent_timestamp = Column(DateTime, nullable=True)
    currency = Column(String(3), default="USD", nullable=False)
    role = Column(String(50), default="customer", nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)

    events = relationship("Event", back_populates="customer", cascade="all, delete-orphan")
    recommendations = relationship("Recommendation", back_populates="customer", cascade="all, delete-orphan")
    customer_segments = relationship("CustomerSegment", back_populates="customer", cascade="all, delete-orphan")
    customer_offers = relationship("CustomerOffer", back_populates="customer", cascade="all, delete-orphan")
    consent_logs = relationship("ConsentLog", back_populates="customer", cascade="all, delete-orphan")
    category_preferences = relationship("CustomerCategoryPreference", back_populates="customer", cascade="all, delete-orphan")


class Product(Base):
    __tablename__ = "products"

    product_id = Column(String(36), primary_key=True, default=_uuid)
    name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False, index=True)
    subcategory = Column(String(100), nullable=True)
    brand = Column(String(100), nullable=True)
    price = Column(Float, nullable=False, default=0.0)
    rating = Column(Float, nullable=True)
    discount_percent = Column(Float, nullable=True)
    original_price = Column(Float, nullable=True)
    image_url = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)

    events = relationship("Event", back_populates="product")
    recommendations = relationship("Recommendation", back_populates="product")


class Event(Base):
    __tablename__ = "events"

    event_id = Column(String(36), primary_key=True, default=_uuid)
    customer_id = Column(String(36), ForeignKey("customers.customer_id"), nullable=False, index=True)
    product_id = Column(String(36), ForeignKey("products.product_id"), nullable=True)
    event_type = Column(String(50), nullable=False, index=True)
    session_id = Column(String(100), nullable=True, index=True)
    event_metadata = Column("metadata", JSON, nullable=True)
    event_timestamp = Column(DateTime, default=utcnow, nullable=False, index=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)

    customer = relationship("Customer", back_populates="events")
    product = relationship("Product", back_populates="events")

    __table_args__ = (
        Index("ix_events_customer_type", "customer_id", "event_type"),
        Index("ix_events_timestamp_desc", event_timestamp.desc()),
    )


class ConsentLog(Base):
    __tablename__ = "consent_log"

    id = Column(String(36), primary_key=True, default=_uuid)
    customer_id = Column(String(36), ForeignKey("customers.customer_id"), nullable=False, index=True)
    action = Column(String(20), nullable=False)  # 'granted', 'revoked', 'forgotten'
    dp_act = Column(String(10), nullable=True)  # 'GDPR', 'DPDP'
    timestamp = Column(DateTime, default=utcnow, nullable=False)

    customer = relationship("Customer", back_populates="consent_logs")


class Recommendation(Base):
    __tablename__ = "recommendations"

    customer_id = Column(String(36), ForeignKey("customers.customer_id"), nullable=False, primary_key=True)
    product_id = Column(String(36), ForeignKey("products.product_id"), nullable=False, primary_key=True)
    score = Column(Float, nullable=False, default=0.0)
    reason_code = Column(String(50), nullable=True)
    reason_text = Column(Text, nullable=True)
    generated_at = Column(DateTime, default=utcnow, nullable=False)

    customer = relationship("Customer", back_populates="recommendations")
    product = relationship("Product", back_populates="recommendations")


class Offer(Base):
    __tablename__ = "offers"

    offer_id = Column(String(36), primary_key=True, default=_uuid)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    discount_type = Column(String(20), nullable=False)  # 'percentage', 'fixed'
    discount_value = Column(Float, nullable=False)
    segment = Column(String(50), nullable=False, index=True)
    min_purchase = Column(Float, nullable=True, default=0.0)
    valid_from = Column(DateTime, nullable=False)
    valid_until = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)

    customer_offers = relationship("CustomerOffer", back_populates="offer")


class CustomerOffer(Base):
    __tablename__ = "customer_offers"

    customer_id = Column(String(36), ForeignKey("customers.customer_id"), nullable=False, primary_key=True)
    offer_id = Column(String(36), ForeignKey("offers.offer_id"), nullable=False, primary_key=True)
    assigned_at = Column(DateTime, default=utcnow, nullable=False)

    customer = relationship("Customer", back_populates="customer_offers")
    offer = relationship("Offer", back_populates="customer_offers")


class CustomerSegment(Base):
    __tablename__ = "customer_segments"

    customer_id = Column(String(36), ForeignKey("customers.customer_id"), nullable=False, primary_key=True)
    segment = Column(String(50), nullable=False, primary_key=True)
    assigned_at = Column(DateTime, default=utcnow, nullable=False)

    customer = relationship("Customer", back_populates="customer_segments")


class CustomerCategoryPreference(Base):
    """Stores category preferences provided by a customer during signup (cold-start)."""
    __tablename__ = "customer_category_preferences"

    customer_id = Column(String(36), ForeignKey("customers.customer_id"), nullable=False, primary_key=True)
    category = Column(String(100), nullable=False, primary_key=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)

    customer = relationship("Customer", back_populates="category_preferences")


class User(Base):
    """OAuth-authenticated user for MCP access control."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sub = Column(String(255), unique=True, nullable=False)
    email = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
