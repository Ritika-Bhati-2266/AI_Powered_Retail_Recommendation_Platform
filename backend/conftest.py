"""Pytest configuration: run every test against an isolated throwaway SQLite DB.

This module MUST be imported before any ``app.*`` module so the async engine is
built against the temporary database rather than the live development database.
The isolated DB is deleted first, then rebuilt and seeded by the application
lifespan inside the ``TestClient`` fixture.
"""
import os
import tempfile

import pytest

_TEST_DB_PATH = os.path.join(tempfile.gettempdir(), "personalshop_test.db")
if os.path.exists(_TEST_DB_PATH):
    os.remove(_TEST_DB_PATH)

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///" + _TEST_DB_PATH.replace(os.sep, "/")

# Keep the seed small so the suite runs fast while still exercising the real
# end-to-end flow (signup, events, segments, offers, stats).
os.environ.setdefault("CUSTOMER_COUNT", "50")
os.environ.setdefault("EVENT_COUNT", "500")

# NOTE: the settings singleton MUST be constructed AFTER the env vars above,
# otherwise DATABASE_URL/MODEL_PATH freeze to the LIVE defaults and every test
# writes test data into the real development DB (as well as clobbering the
# live model, which _isolate_model_path guards against).
from app.config import settings  # noqa: E402 - ordering intentional


@pytest.fixture(autouse=True)
def _isolate_model_path(tmp_path, monkeypatch):
    """Isolate the ML model file from the live backend ``data/model.pkl``.

    Test-created engines call ``engine.train()``, which unconditionally
    ``save()``s to ``settings.MODEL_PATH`` (app/recommender.py:173) — the SAME
    path the running server loads from on startup. Without this isolation a
    pytest run silently replaces the real, live-serving model with the tiny
    4-user/24-item test-fixture model, and a backend restart after that serves
    garbage recommendations until ``/api/admin/train`` is manually re-run.

    Redirecting ``MODEL_PATH`` to a throwaway tmp file per test (mirroring the
    ``DATABASE_URL`` isolation above) keeps ``engine.train()`` -> ``save()``
    fully exercised without ever touching the live model. The real persistence
    path is unaffected: ``/api/admin/train``, ``train.py`` and ``scale_verify.py``
    run outside pytest and still write to ``backend/data/model.pkl``.
    """
    monkeypatch.setattr(settings, "MODEL_PATH", str(tmp_path / "test_model.pkl"))
