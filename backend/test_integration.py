"""Integration tests for the Retail Hyper-Personalisation Engine API.

All protected endpoints are exercised with and without a valid Bearer token
to verify the token-based auth model (owner-scoped, admin-role-scoped).
"""
import asyncio
import uuid

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.database import async_session_factory
from app.main import app
from app.models import CustomerOffer, CustomerSegment


def _create_and_login(client, name: str, consent: bool, currency: str = "USD"):
    """Create a fresh customer via the API and return (customer_id, token)."""
    email = f"auth.{uuid.uuid4().hex[:12]}@test.com"
    resp = client.post("/api/customers", json={
        "name": name,
        "email": email,
        "password": "TestPass@1234",
        "consent_given": consent,
        "currency": currency,
        "category_preferences": [],
    })
    assert resp.status_code == 201, resp.text
    customer_id = resp.json()["customer_id"]
    login = client.post("/api/auth/login", json={
        "email": email,
        "password": "TestPass@1234",
    })
    assert login.status_code == 200, login.text
    return customer_id, login.json()["access_token"]


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def admin_token(client):
    resp = client.post("/api/auth/login", json={
        "email": "admin@personalshop.com",
        "password": settings.DEMO_PASSWORD,
    })
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest.fixture(scope="module")
def customer(client):
    return _create_and_login(client, "Auth Test User", consent=True)


@pytest.fixture(scope="module")
def other_customer(client):
    return _create_and_login(client, "Other Auth User", consent=True)


@pytest.fixture(scope="module")
def non_consenting_customer(client):
    return _create_and_login(client, "No Consent User", consent=False)


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _count_customer_rows(model, customer_id: str) -> int:
    """Count a customer-scoped ORM model's rows in the isolated test DB."""
    from sqlalchemy import func, select

    async def _count():
        async with async_session_factory() as session:
            result = await session.execute(
                select(func.count()).select_from(model).where(model.customer_id == customer_id)
            )
            return result.scalar()

    return asyncio.run(_count())


def _delete_customer_rows(model, customer_id: str) -> None:
    """Delete a customer-scoped ORM model's rows in the isolated test DB."""
    from sqlalchemy import delete

    async def _delete():
        async with async_session_factory() as session:
            await session.execute(delete(model).where(model.customer_id == customer_id))
            await session.commit()

    asyncio.run(_delete())


def _first_product(client) -> dict:
    resp = client.get("/api/products/search?q=&limit=5")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data, "expected at least one seeded product"
    return data[0]


def _discounted_product(client) -> dict:
    def find(url: str) -> dict | None:
        resp = client.get(url)
        assert resp.status_code == 200, resp.text
        for p in resp.json():
            if p.get("discount_percent") and p.get("original_price"):
                return p
        return None

    for q in ("", "pro", "smart", "classic", "premium"):
        found = find(f"/api/products/search?q={q}&limit=100")
        if found:
            return found
    cats = client.get("/api/products/categories").json()
    for cat in cats:
        found = find(f"/api/products/search?q=&category={cat}&limit=50")
        if found:
            return found
    pytest.fail("no discounted product found in the seeded catalog")


def _place_order(client, customer_id: str, token: str, product_ids: list[str]):
    return client.post(
        f"/api/customers/{customer_id}/orders",
        headers=_auth(token),
        json={
            "items": [{"product_id": pid, "quantity": 1} for pid in product_ids],
            "shipping_name": None,
            "shipping_address": None,
        },
    )


class TestHealth:
    def test_health_endpoint(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "title" in data
        assert "version" in data


class TestAuth:
    def test_login_wrong_password_rejected(self, client):
        resp = client.post("/api/auth/login", json={
            "email": "admin@personalshop.com",
            "password": "WrongPass@9999",
        })
        assert resp.status_code == 401

    def test_login_unknown_email_rejected(self, client):
        resp = client.post("/api/auth/login", json={
            "email": "nobody@nowhere.test",
            "password": "Whatever@123",
        })
        assert resp.status_code == 401

    def test_login_with_none_client_does_not_crash(self, client, monkeypatch):
        # Regression: request.client can be None when the ASGI scope omits
        # client info (proxy/lb stripping it, some test harnesses). The login
        # endpoint must degrade to an "unknown" rate-limit key instead of
        # crashing on request.client.host.
        from starlette.requests import Request

        def _client_returns_none(self):
            return None

        monkeypatch.setattr(Request, "client", property(_client_returns_none))

        resp = client.post("/api/auth/login", json={
            "email": "admin@personalshop.com",
            "password": settings.DEMO_PASSWORD,
        })
        assert resp.status_code == 200, resp.text
        assert "access_token" in resp.json()


class TestCustomerProfile:
    def test_get_customer_profile_success(self, client, customer):
        cid, token = customer
        resp = client.get(f"/api/customers/{cid}", headers=_auth(token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["customer_id"] == cid
        assert "name" in data
        assert "email" in data
        assert "consent_status" in data
        assert "metrics" in data
        assert "segments" in data

    def test_get_customer_profile_no_token_rejected(self, client, customer):
        cid, _ = customer
        resp = client.get(f"/api/customers/{cid}")
        assert resp.status_code == 401

    def test_get_customer_profile_cross_user_rejected(self, client, customer, other_customer):
        cid, _ = customer
        _, other_token = other_customer
        resp = client.get(f"/api/customers/{cid}", headers=_auth(other_token))
        assert resp.status_code == 403

    def test_get_customer_profile_not_found(self, client, customer):
        _, token = customer
        resp = client.get("/api/customers/non-existent-id", headers=_auth(token))
        assert resp.status_code == 404


class TestCustomerSearch:
    def test_search_no_token_rejected(self, client):
        resp = client.get("/api/customers/search?q=olivia")
        assert resp.status_code == 401

    def test_search_non_admin_rejected(self, client, customer):
        _, token = customer
        resp = client.get("/api/customers/search?q=olivia", headers=_auth(token))
        assert resp.status_code == 403

    def test_search_admin_allowed(self, client, admin_token):
        resp = client.get("/api/customers/search?q=olivia", headers=_auth(admin_token))
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        for c in data:
            assert "customer_id" in c
            assert "name" in c
            assert "email" in c


class TestConsentGating:
    def test_recommendations_requires_token(self, client, customer):
        cid, _ = customer
        resp = client.get(f"/api/customers/{cid}/recommendations")
        assert resp.status_code == 401

    def test_recommendations_returns_403_without_consent(self, client, non_consenting_customer):
        cid, token = non_consenting_customer
        resp = client.get(f"/api/customers/{cid}/recommendations", headers=_auth(token))
        assert resp.status_code == 403
        assert "consent" in resp.json()["detail"].lower()

    def test_offers_returns_403_without_consent(self, client, non_consenting_customer):
        cid, token = non_consenting_customer
        resp = client.get(f"/api/customers/{cid}/offers", headers=_auth(token))
        assert resp.status_code == 403
        assert "consent" in resp.json()["detail"].lower()

    def test_recommendations_works_with_consent(self, client, customer):
        cid, token = customer
        resp = client.get(f"/api/customers/{cid}/recommendations", headers=_auth(token))
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        if data:
            rec = data[0]
            assert "product_id" in rec
            assert "name" in rec
            assert "reason_code" in rec
            assert "reason_text" in rec
            assert "score" in rec


class TestOffers:
    def test_offers_returns_data_for_consenting_customer(self, client, customer):
        cid, token = customer
        resp = client.get(f"/api/customers/{cid}/offers", headers=_auth(token))
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        if data:
            offer = data[0]
            assert "offer_id" in offer
            assert "title" in offer
            assert "discount_type" in offer
            assert "discount_value" in offer
            assert "valid_until" in offer


class TestEvents:
    def test_ingest_event_no_token_rejected(self, client, customer):
        cid, _ = customer
        resp = client.post("/api/events", json={
            "customer_id": cid,
            "event_type": "page_view",
        })
        assert resp.status_code == 401

    def test_ingest_event_cross_user_rejected(self, client, customer, other_customer):
        cid, _ = customer
        _, other_token = other_customer
        resp = client.post("/api/events", json={
            "customer_id": cid,
            "event_type": "page_view",
        }, headers=_auth(other_token))
        assert resp.status_code == 403

    def test_ingest_event_own_account_allowed(self, client, customer):
        cid, token = customer
        resp = client.post("/api/events", json={
            "customer_id": cid,
            "event_type": "page_view",
            "product_id": None,
            "session_id": "test-session-123",
        }, headers=_auth(token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "event_id" in data

    def test_ingest_event_admin_for_other_allowed(self, client, customer, admin_token):
        cid, _ = customer
        resp = client.post("/api/events", json={
            "customer_id": cid,
            "event_type": "page_view",
        }, headers=_auth(admin_token))
        assert resp.status_code == 200

    def test_ingest_event_customer_not_found(self, client, admin_token):
        resp = client.post("/api/events", json={
            "customer_id": "nonexistent-id",
            "event_type": "page_view",
        }, headers=_auth(admin_token))
        assert resp.status_code == 404


class TestProducts:
    def test_search_products(self, client):
        resp = client.get("/api/products/search?q=laptop")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        if data:
            p = data[0]
            assert "product_id" in p
            assert "name" in p
            assert "price" in p

    def test_get_categories(self, client):
        resp = client.get("/api/products/categories")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0


class TestAdminStats:
    def test_admin_stats_requires_auth(self, client):
        resp = client.get("/api/admin/stats")
        assert resp.status_code == 401

    def test_admin_stats_non_admin_rejected(self, client, customer):
        _, token = customer
        resp = client.get("/api/admin/stats", headers=_auth(token))
        assert resp.status_code == 403

    def test_admin_stats_admin_allowed(self, client, admin_token):
        resp = client.get("/api/admin/stats", headers=_auth(admin_token))
        assert resp.status_code == 200
        data = resp.json()
        assert "total_customers" in data
        assert "consent_rate" in data


class TestBusinessLogicFixes:
    """Regression tests for the 14fc0b6 / 2ac7b01 business-logic fixes that were
    only verified with throwaway scripts before. Each test exercises the fix end
    to end through the public API against the isolated test DB."""

    def test_lifetime_value_is_net_of_discount(self, client):
        # A fresh consenting customer gets the Welcome offer auto-assigned, so a
        # discount applies at checkout; LTV must be the NET total (gross minus
        # discount), not the pre-discount subtotal.
        cid, token = _create_and_login(client, "LTV User", consent=True)
        pid = _first_product(client)["product_id"]
        order = _place_order(client, cid, token, [pid])
        assert order.status_code == 201, order.text
        order_data = order.json()
        assert order_data["discount_amount"] > 0, "expected checkout discount to apply"
        prof = client.get(f"/api/customers/{cid}", headers=_auth(token))
        assert prof.status_code == 200
        ltv = prof.json()["metrics"]["lifetime_value"]
        # USD customer: stored total is already USD; LTV must equal the NET order total.
        assert ltv == pytest.approx(order_data["total_amount"])

    def test_consent_revoke_purges_segments_and_offers(self, client):
        cid, token = _create_and_login(client, "Revoke User", consent=True)
        pid = _first_product(client)["product_id"]
        assert _place_order(client, cid, token, [pid]).status_code == 201
        # Personalisation state must exist before the revocation.
        assert _count_customer_rows(CustomerOffer, cid) >= 1
        assert _count_customer_rows(CustomerSegment, cid) >= 1
        assert client.get(f"/api/customers/{cid}/offers", headers=_auth(token)).status_code == 200

        up = client.patch(f"/api/customers/{cid}", headers=_auth(token), json={"consent_given": False})
        assert up.status_code == 200

        # Revocation purges all personalisation rows from the DB...
        assert _count_customer_rows(CustomerOffer, cid) == 0
        assert _count_customer_rows(CustomerSegment, cid) == 0
        # ...and the offers endpoint re-gates with 403.
        assert client.get(f"/api/customers/{cid}/offers", headers=_auth(token)).status_code == 403

    def test_inr_discounted_prices_are_converted(self, client):
        # original_price and price must render on the converted (INR, ~83x) scale.
        prod = _discounted_product(client)
        usd_price = prod["price"]
        usd_original = prod["original_price"]
        assert usd_original > usd_price

        cid, token = _create_and_login(client, "INR User", consent=True, currency="INR")
        resp = client.get(
            f"/api/products/search?q=&limit=100&customer_id={cid}",
            headers=_auth(token),
        )
        assert resp.status_code == 200
        inr = next(p for p in resp.json() if p["product_id"] == prod["product_id"])
        assert inr["currency"] == "INR"
        # INR rounds to whole numbers: converted price/original are ~83x USD.
        assert inr["price"] == round(usd_price * 83)
        assert inr["original_price"] == round(usd_original * 83)
        assert inr["original_price"] > inr["price"]

    def test_total_purchases_counts_orders_not_line_items(self, client):
        cid, token = _create_and_login(client, "Count User", consent=True)
        prods = client.get("/api/products/search?q=&limit=5").json()[:3]
        pids = [p["product_id"] for p in prods]
        order = _place_order(client, cid, token, pids)
        assert order.status_code == 201, order.text
        assert len(order.json()["items"]) == 3
        prof = client.get(f"/api/customers/{cid}", headers=_auth(token))
        assert prof.status_code == 200
        # One order with three line items -> purchase count must be 1 (order count).
        assert prof.json()["metrics"]["total_purchases"] == 1

    def test_offer_is_one_time_use(self, client):
        cid, token = _create_and_login(client, "Offer User", consent=True)
        pid = _first_product(client)["product_id"]

        o1 = _place_order(client, cid, token, [pid])
        assert o1.status_code == 201, o1.text
        d1 = o1.json()
        assert d1["applied_offer_id"] is not None
        assert d1["discount_amount"] > 0
        applied_id = d1["applied_offer_id"]

        # Second order: the welcome offer was consumed at checkout.
        o2 = _place_order(client, cid, token, [pid])
        assert o2.status_code == 201, o2.text
        d2 = o2.json()
        assert d2["applied_offer_id"] is None
        assert d2["discount_amount"] == 0

        # Consumed offer no longer appears in the (only_unused) offers panel.
        offers = client.get(f"/api/customers/{cid}/offers", headers=_auth(token))
        assert offers.status_code == 200
        assert all(o["offer_id"] != applied_id for o in offers.json())

    def test_event_ingest_recomputes_segments_via_background_task(self, client):
        # Prove the background recompute actually runs after ingest: wipe the
        # customer's segments, ingest one event, and confirm they are restored.
        cid, token = _create_and_login(client, "BG Seg User", consent=True)
        _delete_customer_rows(CustomerSegment, cid)
        assert _count_customer_rows(CustomerSegment, cid) == 0

        resp = client.post("/api/events", headers=_auth(token), json={
            "customer_id": cid,
            "event_type": "page_view",
        })
        assert resp.status_code == 200
        assert "event_id" in resp.json()
        # Segment recompute (FastAPI BackgroundTask) has completed by the time
        # the ingest response returns in the test client.
        assert _count_customer_rows(CustomerSegment, cid) >= 1
