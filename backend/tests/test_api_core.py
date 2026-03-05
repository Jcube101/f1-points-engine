"""
Tests for the core API structure: health endpoint, response envelope, CORS.
"""


class TestHealth:
    def test_health_returns_ok(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


class TestResponseEnvelope:
    """Every /api/* endpoint must respond with { success, data } envelope."""

    def test_drivers_envelope(self, client):
        r = client.get("/api/drivers")
        assert r.status_code == 200
        body = r.json()
        assert "success" in body
        assert body["success"] is True
        assert "data" in body

    def test_constructors_envelope(self, client):
        r = client.get("/api/constructors")
        assert r.status_code == 200
        body = r.json()
        assert body["success"] is True
        assert isinstance(body["data"], list)

    def test_races_envelope(self, client):
        r = client.get("/api/races?season=2025")
        assert r.status_code == 200
        body = r.json()
        assert body["success"] is True
        assert isinstance(body["data"], list)
