"""Pytest configuration: run every test against an isolated throwaway SQLite DB.

This module MUST be imported before any ``app.*`` module so the async engine is
built against the temporary database rather than the live development database.
The isolated DB is deleted first, then rebuilt and seeded by the application
lifespan inside the ``TestClient`` fixture.
"""
import os
import tempfile

_TEST_DB_PATH = os.path.join(tempfile.gettempdir(), "personalshop_test.db")
if os.path.exists(_TEST_DB_PATH):
    os.remove(_TEST_DB_PATH)

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///" + _TEST_DB_PATH.replace(os.sep, "/")

# Keep the seed small so the suite runs fast while still exercising the real
# end-to-end flow (signup, events, segments, offers, stats).
os.environ.setdefault("CUSTOMER_COUNT", "50")
os.environ.setdefault("EVENT_COUNT", "500")
