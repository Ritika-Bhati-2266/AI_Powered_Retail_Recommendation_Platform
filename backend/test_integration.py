"""Integration tests for the Retail Hyper-Personalisation Engine API."""
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _get_consenting_customer_id():
    """Fetch a consenting customer ID directly from the seeded SQLite DB."""
    import sqlite3
    conn = sqlite3.connect("data/personalisation.db")
    c = conn.cursor()
    c.execute("SELECT customer_id FROM customers WHERE consent_given = 1 LIMIT 1")
    row = c.fetchone()
    conn.close()
    return row[0] if row else None


def _get_non_consenting_customer_id():
    """Fetch a non-consenting customer ID directly from the seeded SQLite DB."""
    import sqlite3
    conn = sqlite3.connect("data/personalisation.db")
    c = conn.cursor()
    c.execute("SELECT customer_id FROM customers WHERE consent_given = 0 LIMIT 1")
    row = c.fetchone()
    conn.close()
    return row[0] if row else None


@pytest.fixture(scope="module")
def consenting_customer_id():
    cid = _get_consenting_customer_id()
    assert cid is not None, "No consenting customer found in seeded DB"
    return cid


@pytest.fixture(scope="module")
def non_consenting_customer_id():
    cid = _get_non_consenting_customer_id()
    assert cid is not None, "No non-consenting customer found in seeded DB"
    return cid


class TestHealth:
    def test_health_endpoint(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "title" in data
        assert "version" in data


class TestCustomerProfile:
    def test_get_customer_profile_success(self, client, consenting_customer_id):
        resp = client.get(f"/api/customers/{consenting_customer_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["customer_id"] == consenting_customer_id
        assert "name" in data
        assert "email" in data
        assert "consent_status" in data
        assert "metrics" in data
        assert "segments" in data

    def test_get_customer_profile_not_found(self, client):
        resp = client.get("/api/customers/non-existent-id")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_search_customers(self, client):
        resp = client.get("/api/customers/search?q=olivia")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0
        for c in data:
            assert "customer_id" in c
            assert "name" in c
            assert "email" in c


class TestConsentGating:
    def test_recommendations_returns_403_without_consent(self, client, non_consenting_customer_id):
        resp = client.get(f"/api/customers/{non_consenting_customer_id}/recommendations")
        assert resp.status_code == 403
        assert "consent" in resp.json()["detail"].lower()

    def test_offers_returns_403_without_consent(self, client, non_consenting_customer_id):
        resp = client.get(f"/api/customers/{non_consenting_customer_id}/offers")
        assert resp.status_code == 403
        assert "consent" in resp.json()["detail"].lower()

    def test_recommendations_works_with_consent(self, client, consenting_customer_id):
        resp = client.get(f"/api/customers/{consenting_customer_id}/recommendations")
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
    def test_offers_returns_data_for_consenting_customer(self, client, consenting_customer_id):
        resp = client.get(f"/api/customers/{consenting_customer_id}/offers")
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
    def test_ingest_event_success(self, client, consenting_customer_id):
        resp = client.post("/api/events", json={
            "customer_id": consenting_customer_id,
            "event_type": "page_view",
            "product_id": None,
            "session_id": "test-session-123",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "event_id" in data

    def test_ingest_event_customer_not_found(self, client):
        resp = client.post("/api/events", json={
            "customer_id": "nonexistent-id",
            "event_type": "page_view",
        })
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
