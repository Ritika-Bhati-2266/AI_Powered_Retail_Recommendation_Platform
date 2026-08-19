"""Integration tests for the Retail Hyper-Personalisation Engine API.

All protected endpoints are exercised with and without a valid Bearer token
to verify the token-based auth model (owner-scoped, admin-role-scoped).
"""
import uuid

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app


def _create_and_login(client, name: str, consent: bool):
    """Create a fresh customer via the API and return (customer_id, token)."""
    email = f"auth.{uuid.uuid4().hex[:12]}@test.com"
    resp = client.post("/api/customers", json={
        "name": name,
        "email": email,
        "password": "TestPass@1234",
        "consent_given": consent,
        "currency": "USD",
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
