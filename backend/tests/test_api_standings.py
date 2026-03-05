"""
Integration tests for /api/standings endpoints.

Note: WDC and WCC endpoints call the external Ergast API which is unavailable
in the test environment. We verify the response envelope and graceful fallback.
"""


class TestWDCStandings:
    def test_returns_200(self, client):
        r = client.get("/api/standings/wdc?season=2025")
        assert r.status_code == 200

    def test_response_has_envelope(self, client):
        body = client.get("/api/standings/wdc?season=2025").json()
        assert "success" in body
        assert "data" in body

    def test_data_is_list(self, client):
        data = client.get("/api/standings/wdc?season=2025").json()["data"]
        assert isinstance(data, list)

    def test_season_param_accepted(self, client):
        r = client.get("/api/standings/wdc?season=2026")
        assert r.status_code == 200


class TestWCCStandings:
    def test_returns_200(self, client):
        r = client.get("/api/standings/wcc?season=2025")
        assert r.status_code == 200

    def test_data_is_list(self, client):
        data = client.get("/api/standings/wcc?season=2025").json()["data"]
        assert isinstance(data, list)


class TestFantasyValueLeaderboard:
    def test_returns_200(self, client):
        r = client.get("/api/standings/value?season=2025")
        assert r.status_code == 200

    def test_returns_list(self, client):
        data = client.get("/api/standings/value?season=2025").json()["data"]
        assert isinstance(data, list)

    def test_entry_has_required_fields(self, client):
        data = client.get("/api/standings/value?season=2025").json()["data"]
        if data:
            entry = data[0]
            assert "code" in entry
            assert "xp" in entry
            assert "value_score" in entry

    def test_sorted_by_value_desc(self, client):
        data = client.get("/api/standings/value?season=2025").json()["data"]
        if len(data) >= 2:
            scores = [e["value_score"] for e in data]
            assert scores == sorted(scores, reverse=True)


class TestSeasonProgression:
    def test_returns_200(self, client):
        r = client.get("/api/standings/progression?season=2025")
        assert r.status_code == 200

    def test_returns_list(self, client):
        data = client.get("/api/standings/progression?season=2025").json()["data"]
        assert isinstance(data, list)

    def test_entry_has_round_fields(self, client):
        data = client.get("/api/standings/progression?season=2025").json()["data"]
        if data:
            entry = data[0]
            assert "round" in entry
            assert "round_name" in entry

    def test_cumulative_totals_increase(self, client):
        data = client.get("/api/standings/progression?season=2025").json()["data"]
        if len(data) >= 2:
            # VER should have non-decreasing cumulative points
            ver_pts = [e.get("VER", 0) for e in data]
            for i in range(1, len(ver_pts)):
                assert ver_pts[i] >= ver_pts[i - 1]
