"""
Integration tests for /api/drivers endpoints.

Relies on the seeded test DB from conftest.py (4 drivers, 6 races, profiles).
"""


class TestGetDrivers:
    def test_returns_list(self, client):
        r = client.get("/api/drivers")
        assert r.status_code == 200
        data = r.json()["data"]
        assert isinstance(data, list)
        assert len(data) >= 4

    def test_driver_has_required_fields(self, client):
        data = client.get("/api/drivers").json()["data"]
        d = data[0]
        required = {"id", "name", "code", "team_name", "price", "xp", "value_score"}
        assert required.issubset(d.keys())

    def test_driver_has_phase2_fields(self, client):
        data = client.get("/api/drivers").json()["data"]
        d = data[0]
        # Phase 2 fields should be present (may be None)
        assert "form_status" in d
        assert "circuit_fit_score" in d
        assert "is_differential" in d

    def test_xp_is_non_negative(self, client):
        data = client.get("/api/drivers").json()["data"]
        for d in data:
            assert d["xp"] >= 0

    def test_price_is_positive(self, client):
        data = client.get("/api/drivers").json()["data"]
        for d in data:
            # Prices can be 0 for retired/inactive drivers
            assert d["price"] >= 0

    def test_value_score_is_numeric(self, client):
        data = client.get("/api/drivers").json()["data"]
        for d in data:
            assert isinstance(d["value_score"], (int, float))


class TestGetDriverById:
    def test_returns_known_driver(self, client):
        r = client.get("/api/drivers/1")
        assert r.status_code == 200
        body = r.json()
        assert body["success"] is True
        d = body["data"]
        assert d["id"] == 1
        assert d["code"] == "VER"

    def test_returns_error_for_unknown(self, client):
        # Route uses success:False envelope rather than HTTP 404
        r = client.get("/api/drivers/99999")
        assert r.status_code == 200
        assert r.json()["success"] is False

    def test_known_driver_has_name_and_code(self, client):
        d = client.get("/api/drivers/1").json()["data"]
        assert "name" in d
        assert "code" in d


class TestGetDriverForm:
    def test_returns_form_data(self, client):
        r = client.get("/api/drivers/1/form")
        assert r.status_code == 200
        data = r.json()["data"]
        assert "flag" in data
        assert "delta" in data
        assert "history" in data

    def test_flag_is_valid_value(self, client):
        data = client.get("/api/drivers/1/form").json()["data"]
        assert data["flag"] in {"overperforming", "underperforming", "on_form"}

    def test_history_has_required_keys(self, client):
        data = client.get("/api/drivers/1/form").json()["data"]
        if data["history"]:
            entry = data["history"][0]
            assert "round" in entry
            assert "actual" in entry
            assert "xp" in entry

    def test_returns_error_for_unknown_driver(self, client):
        r = client.get("/api/drivers/99999/form")
        assert r.status_code == 200
        assert r.json()["success"] is False

    def test_history_max_5_entries(self, client):
        data = client.get("/api/drivers/1/form").json()["data"]
        assert len(data["history"]) <= 5


class TestGetCircuitFit:
    def test_street_returns_list(self, client):
        r = client.get("/api/drivers/circuit-fit?circuit_type=street")
        assert r.status_code == 200
        data = r.json()["data"]
        assert isinstance(data, list)

    def test_power_returns_list(self, client):
        r = client.get("/api/drivers/circuit-fit?circuit_type=power")
        assert r.status_code == 200

    def test_balanced_returns_list(self, client):
        r = client.get("/api/drivers/circuit-fit?circuit_type=balanced")
        assert r.status_code == 200

    def test_fit_score_in_0_to_10(self, client):
        data = client.get("/api/drivers/circuit-fit?circuit_type=street").json()["data"]
        for entry in data:
            assert 0 <= entry["fit_score"] <= 10

    def test_sorted_by_fit_score_desc(self, client):
        data = client.get("/api/drivers/circuit-fit?circuit_type=balanced").json()["data"]
        scores = [e["fit_score"] for e in data]
        assert scores == sorted(scores, reverse=True)

    def test_entry_has_required_fields(self, client):
        data = client.get("/api/drivers/circuit-fit?circuit_type=street").json()["data"]
        if data:
            entry = data[0]
            required = {"driver_code", "driver_name", "fit_score", "avg_points"}
            assert required.issubset(entry.keys())

    def test_missing_circuit_type_is_handled(self, client):
        r = client.get("/api/drivers/circuit-fit")
        # Should either return 422 (missing required param) or an empty list
        assert r.status_code in {200, 422}


class TestGetVsTeammate:
    def test_returns_comparison(self, client):
        r = client.get("/api/drivers/1/vs-teammate")
        assert r.status_code == 200
        data = r.json()["data"]
        # Can be None if no teammate found
        if data is not None:
            assert "driver_1" in data or "constructor_id" in data

    def test_returns_error_for_unknown_driver(self, client):
        r = client.get("/api/drivers/99999/vs-teammate")
        assert r.status_code == 200
        assert r.json()["success"] is False
