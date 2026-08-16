"""
ConsentService: handles consent checking, logging, and GDPR/DPDP right-to-forget.
"""
import uuid

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ConsentLog, Customer, CustomerOffer, CustomerSegment, Event, Recommendation
from app.utils import utcnow


class ConsentService:
    """Manages customer consent and privacy rights."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_consent(self, customer_id: str) -> bool:
        """Check if a customer has given consent for personalisation."""
        result = await self.db.execute(
            select(Customer.consent_given).where(Customer.customer_id == customer_id)
        )
        row = result.scalar_one_or_none()
        return bool(row) if row is not None else False

    async def log_consent(self, customer_id: str, action: str, dp_act: str | None = None) -> None:
        """Record a consent action in the consent_log."""
        log_entry = ConsentLog(
            id=str(uuid.uuid4()),
            customer_id=customer_id,
            action=action,
            dp_act=dp_act,
            timestamp=utcnow(),
        )
        self.db.add(log_entry)

    async def right_to_forget(self, customer_id: str, regulator: str = "GDPR") -> None:
        """
        GDPR/DPDP Right to Forget:
        - Delete all events for the customer
        - Delete all recommendations
        - Delete all segment assignments
        - Delete all customer_offers
        - Set consent_given = False
        - Log the 'forgotten' action
        - The customer record itself stays (minimal record that right was exercised)
        - Prior consent_log history is preserved as an audit trail

        Raises:
            ValueError: if no customer with the given customer_id exists.
        """
        # 0. Confirm the customer actually exists before doing anything
        result = await self.db.execute(
            select(Customer).where(Customer.customer_id == customer_id)
        )
        customer = result.scalar_one_or_none()
        if customer is None:
            raise ValueError(f"Customer {customer_id} not found")

        now = utcnow()

        # 1. Delete all events for customer
        await self.db.execute(
            delete(Event).where(Event.customer_id == customer_id)
        )

        # 2. Delete all recommendations
        await self.db.execute(
            delete(Recommendation).where(Recommendation.customer_id == customer_id)
        )

        # 3. Delete all segment assignments
        await self.db.execute(
            delete(CustomerSegment).where(CustomerSegment.customer_id == customer_id)
        )

        # 4. Delete all customer_offers
        await self.db.execute(
            delete(CustomerOffer).where(CustomerOffer.customer_id == customer_id)
        )

        # Note: consent_log is intentionally NOT deleted here.
        # It contains no behavioural/personal data (just action + regulator +
        # timestamp) and controllers are generally expected to retain proof
        # that consent was given/withdrawn (e.g. GDPR Art. 7(1)).

        # 5. Set consent_given = False on the customer record
        await self.db.execute(
            update(Customer)
            .where(Customer.customer_id == customer_id)
            .values(consent_given=False, consent_timestamp=now)
        )

        # 6. Log the 'forgotten' action, tagged with the actual applicable regulator
        forgotten_log = ConsentLog(
            id=str(uuid.uuid4()),
            customer_id=customer_id,
            action="forgotten",
            dp_act=regulator,
            timestamp=now,
        )
        self.db.add(forgotten_log)
