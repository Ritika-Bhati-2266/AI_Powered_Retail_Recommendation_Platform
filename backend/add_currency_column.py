"""Migration: add currency column to existing customers."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import select, text

from app.database import async_session_factory, engine
from app.models import Customer


async def main():
    # Add column if it doesn't exist (SQLite)
    async with engine.begin() as conn:
        # Check if column exists
        result = await conn.execute(text("PRAGMA table_info(customers)"))
        columns = [row[1] for row in result.fetchall()]
        if "currency" not in columns:
            await conn.execute(text("ALTER TABLE customers ADD COLUMN currency VARCHAR(3) DEFAULT 'USD' NOT NULL"))
            print("Added currency column to customers table.")
        else:
            print("Currency column already exists.")

    # Update any customers with NULL currency
    async with async_session_factory() as db:
        result = await db.execute(select(Customer).where(Customer.currency.is_(None)))
        null_customers = result.scalars().all()
        for c in null_customers:
            c.currency = "USD"
        await db.commit()
        print(f"Updated {len(null_customers)} customers with default currency.")

    print("Migration complete.")


if __name__ == "__main__":
    asyncio.run(main())
