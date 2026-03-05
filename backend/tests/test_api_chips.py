"""
Integration tests for /api/chips/recommend endpoint.
"""

SAMPLE_REQUEST = {
    "race_id": 1,
    "chips_remaining": ["drs_boost", "no_negative", "wildcard"],
    "team_value": 98_000_000,
    "transfers_banked": 2,
    "races_completed": 5,
    "wet_weather_forecast": False,
}


class TestChipRecommendation:
    def test_returns_200(self, client):
        r = client.post("/api/chips/recommend", json=SAMPLE_REQUEST)
        assert r.status_code == 200

    def test_response_envelope(self, client):
        body = client.post("/api/chips/recommend", json=SAMPLE_REQUEST).json()
        assert body["success"] is True
        assert "data" in body

    def test_data_has_chip_and_reason(self, client):
        data = client.post("/api/chips/recommend", json=SAMPLE_REQUEST).json()["data"]
        assert "chip" in data
        assert "reason" in data

    def test_confidence_is_valid(self, client):
        data = client.post("/api/chips/recommend", json=SAMPLE_REQUEST).json()["data"]
        confidence = data.get("confidence")
        assert confidence is None or confidence.lower() in {"low", "medium", "high"}

    def test_chip_is_string(self, client):
        data = client.post("/api/chips/recommend", json=SAMPLE_REQUEST).json()["data"]
        assert isinstance(data["chip"], str)

    def test_reason_is_string(self, client):
        data = client.post("/api/chips/recommend", json=SAMPLE_REQUEST).json()["data"]
        assert isinstance(data["reason"], str)

    def test_wet_weather_flag(self, client):
        wet_req = {**SAMPLE_REQUEST, "wet_weather_forecast": True}
        r = client.post("/api/chips/recommend", json=wet_req)
        assert r.status_code == 200

    def test_no_chips_remaining_handled(self, client):
        req = {**SAMPLE_REQUEST, "chips_remaining": []}
        r = client.post("/api/chips/recommend", json=req)
        assert r.status_code == 200
