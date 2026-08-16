"""
Authentication endpoints.
POST /api/auth/login
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Customer
from app.schemas import AuthResponse, LoginRequest
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=AuthResponse)
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate a customer by email + password and return a signed token."""
    result = await db.execute(
        select(Customer).where(func.lower(Customer.email) == payload.email.strip().lower())
    )
    customer = result.scalar_one_or_none()

    # Deliberately fail the same way for unknown email and wrong password.
    if not customer or not verify_password(payload.password, customer.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(customer.customer_id, customer.role or "customer")

    # A hash must always be reachable once a real account logs in; if one was
    # created without a password (legacy/seed), backfill it so it can log in.
    if not customer.password_hash:
        customer.password_hash = hash_password(payload.password)

    await db.commit()

    return AuthResponse(
        access_token=token,
        token_type="bearer",
        customer_id=customer.customer_id,
        name=customer.name,
        email=customer.email,
        role=customer.role or "customer",
    )
