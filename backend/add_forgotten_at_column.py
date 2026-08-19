"""Migration: add forgotten_at column to existing customers table."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import text

from app.database import engine


async def main():
    async with engine.begin() as conn:
        result = await conn.execute(text("PRAGMA table_info(customers)"))
        columns = [row[1] for row in result.fetchall()]
        if "forgotten_at" not in columns:
            await conn.execute(text("ALTER TABLE customers ADD COLUMN forgotten_at DATETIME"))
            print("Added forgotten_at column to customers table.")
        else:
            print("Forgotten_at column already exists.")

    await engine.dispose()
    print("Migration complete.")


if __name__ == "__main__":
    asyncio.run(main())
