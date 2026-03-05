"""
Integration tests for /api/races endpoints.
"""


class TestGetRaces:
    def test_returns_list_for_2025(self, client):
        r = client.get("/api/races?season=2025")
        assert r.status_code == 200
        data = r.json()["data"]
        assert isinstance(data, list)
        assert len(data) >= 6

    def test_race_has_required_fields(self, client):
        data = client.get("/api/races?season=2025").json()["data"]
        race = data[0]
        required = {"id", "season", "round_number", "name", "circuit_type", "date"}
        assert required.issubset(race.keys())

    def test_circuit_type_is_valid(self, client):
        data = client.get("/api/races?season=2025").json()["data"]
        valid_types = {"street", "power", "balanced"}
        for race in data:
            assert race["circuit_type"] in valid_types

    def test_season_filter_works(self, client):
        data_2025 = client.get("/api/races?season=2025").json()["data"]
        data_2026 = client.get("/api/races?season=2026").json()["data"]
        ids_2025 = {r["id"] for r in data_2025}
        ids_2026 = {r["id"] for r in data_2026}
        assert ids_2025.isdisjoint(ids_2026)

    def test_rounds_are_sorted(self, client):
        data = client.get("/api/races?season=2025").json()["data"]
        rounds = [r["round_number"] for r in data]
        assert rounds == sorted(rounds)


class TestGetRaceResults:
    def test_returns_results_for_known_race(self, client):
        r = client.get("/api/races/1/results")
        assert r.status_code == 200
        data = r.json()["data"]
        assert isinstance(data, list)
        assert len(data) >= 4

    def test_result_has_required_fields(self, client):
        data = client.get("/api/races/1/results").json()["data"]
        row = data[0]
        required = {"driver_id", "qualifying_pos", "race_pos"}
        assert required.issubset(row.keys())

    def test_unknown_race_returns_error(self, client):
        r = client.get("/api/races/99999/results")
        assert r.status_code == 200  # returns success:False envelope
        body = r.json()
        assert body["success"] is False


class TestUpcomingDifficulty:
    def test_returns_list(self, client):
        r = client.get("/api/races/upcoming-difficulty?season=2026")
        assert r.status_code == 200
        data = r.json()["data"]
        assert isinstance(data, list)

    def test_race_entry_has_required_fields(self, client):
        data = client.get("/api/races/upcoming-difficulty?season=2026").json()["data"]
        if data:
            entry = data[0]
            assert "race_name" in entry
            assert "circuit_type" in entry
            assert "driver_fits" in entry

    def test_fit_scores_in_range_when_drivers_specified(self, client):
        data = client.get(
            "/api/races/upcoming-difficulty?season=2026&drivers=VER,LEC"
        ).json()["data"]
        for race in data:
            for code, score in race.get("driver_fits", {}).items():
                assert 0 <= score <= 10

    def test_driver_filter_param(self, client):
        r = client.get("/api/races/upcoming-difficulty?season=2026&drivers=VER,LEC")
        assert r.status_code == 200
        data = r.json()["data"]
        if data:
            assert "VER" in data[0]["driver_fits"]
            assert "LEC" in data[0]["driver_fits"]

    def test_max_5_races_returned(self, client):
        data = client.get("/api/races/upcoming-difficulty?season=2026").json()["data"]
        assert len(data) <= 5
