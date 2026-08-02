"""
Offers endpoint.
GET /api/customers/{customer_id}/offers
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Customer
from app.schemas import OfferOut
from app.offers import OfferEngine
from app.privacy import ConsentService
from app.currency import convert_price
from app.security import require_owner

router = APIRouter(tags=["offers"])


@router.get("/customers/{customer_id}/offers", response_model=list[OfferOut])
async def get_customer_offers(
    customer_id: str,
    auth: Customer = Depends(require_owner),
    db: AsyncSession = Depends(get_db),
):
    """Get active offers assigned to a customer. Consent-gated."""
    # 1. Check customer exists and get currency
    result = await db.execute(
        select(Customer).where(Customer.customer_id == customer_id)
    )
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    customer_currency = customer.currency or "USD"

    # 2. Check consent
    consent_service = ConsentService(db)
    has_consent = await consent_service.check_consent(customer_id)
    if not has_consent:
        raise HTTPException(
            status_code=403,
            detail="Customer has not given consent for personalisation. Offers are unavailable.",
        )

    # 3. Return offers with currency conversion
    offer_engine = OfferEngine(db)
    offers = await offer_engine.get_offers_for_customer(customer_id)

    result_list = []
    for offer in offers:
        # Convert discount value only for fixed amounts, not percentages
        converted_value = offer.discount_value
        if offer.discount_type in ("fixed", "fixed_amount", "free_shipping") and offer.discount_value > 0:
            converted_value, _, _ = convert_price(offer.discount_value, customer_currency)

        _, cur, sym = convert_price(0, customer_currency)  # Just get currency info

        result_list.append(OfferOut(
            offer_id=offer.offer_id,
            title=offer.title,
            description=offer.description,
            discount_type=offer.discount_type,
            discount_value=converted_value,
            valid_until=offer.valid_until,
            currency=cur,
            symbol=sym,
        ))

    return result_list
