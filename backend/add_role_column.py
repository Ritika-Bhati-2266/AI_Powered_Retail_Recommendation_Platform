"""Migration: add role column to existing customers and seed admin user."""
import asyncio
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import select, text

from app.database import async_session_factory, engine
from app.models import Customer
from app.utils import utcnow


async def main():
    # 1. Add column if it doesn't exist (SQLite)
    async with engine.begin() as conn:
        # Check if column exists
        result = await conn.execute(text("PRAGMA table_info(customers)"))
        columns = [row[1] for row in result.fetchall()]
        if "role" not in columns:
            await conn.execute(text("ALTER TABLE customers ADD COLUMN role VARCHAR(50) DEFAULT 'customer' NOT NULL"))
            print("Added role column to customers table.")
        else:
            print("Role column already exists.")

    # 2. Check/Seed Admin User
    async with async_session_factory() as db:
        # Update existing to have default role if needed
        result = await db.execute(select(Customer).where(Customer.role.is_(None)))
        null_role_customers = result.scalars().all()
        for c in null_role_customers:
            c.role = "customer"

        # Check if admin user exists
        result_admin = await db.execute(select(Customer).where(Customer.email == "admin@personalshop.com"))
        admin = result_admin.scalar_one_or_none()

        now = utcnow()
        if not admin:
            admin = Customer(
                customer_id=str(uuid.uuid4()),
                name="Admin User",
                email="admin@personalshop.com",
                consent_given=True,
                consent_timestamp=now,
                role="admin",
                created_at=now,
            )
            db.add(admin)
            print("Seeded admin@personalshop.com user.")
        else:
            admin.role = "admin"
            print("Updated existing admin@personalshop.com user to have 'admin' role.")

        await db.commit()

    print("Migration complete.")

if __name__ == "__main__":
    asyncio.run(main())
