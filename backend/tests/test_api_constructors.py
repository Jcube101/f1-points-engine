"""
Integration tests for /api/constructors endpoints.
"""


class TestGetConstructors:
    def test_returns_list(self, client):
        r = client.get("/api/constructors")
        assert r.status_code == 200
        data = r.json()["data"]
        assert isinstance(data, list)
        assert len(data) >= 2

    def test_constructor_has_required_fields(self, client):
        data = client.get("/api/constructors").json()["data"]
        c = data[0]
        required = {"id", "name", "price", "color_hex", "drivers"}
        assert required.issubset(c.keys())

    def test_drivers_is_list(self, client):
        data = client.get("/api/constructors").json()["data"]
        for c in data:
            assert isinstance(c["drivers"], list)

    def test_drivers_have_code(self, client):
        data = client.get("/api/constructors").json()["data"]
        for c in data:
            for d in c["drivers"]:
                assert "code" in d


class TestGetTeammateComparison:
    def test_returns_comparison_for_known_constructor(self, client):
        r = client.get("/api/constructors/1/teammates")
        assert r.status_code == 200
        body = r.json()
        assert body["success"] is True

    def test_data_is_none_or_has_drivers(self, client):
        data = client.get("/api/constructors/1/teammates").json()["data"]
        if data is not None:
            assert "driver_1" in data
            assert "driver_2" in data

    def test_teammate_stats_have_required_fields(self, client):
        data = client.get("/api/constructors/1/teammates").json()["data"]
        if data is not None and data.get("driver_1"):
            d1 = data["driver_1"]
            required = {"id", "name", "code", "price", "avg_fantasy_pts", "xp"}
            assert required.issubset(d1.keys())

    def test_returns_error_for_unknown_constructor(self, client):
        # Route uses success:False envelope rather than HTTP 404
        r = client.get("/api/constructors/99999/teammates")
        assert r.status_code == 200
        assert r.json()["success"] is False
