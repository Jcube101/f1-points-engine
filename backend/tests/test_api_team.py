"""
Integration tests for /api/team/optimize endpoint.
"""


class TestOptimizeTeam:
    def test_returns_200(self, client):
        r = client.post("/api/team/optimize", json={"budget": 100_000_000})
        assert r.status_code == 200

    def test_response_envelope(self, client):
        body = client.post("/api/team/optimize", json={"budget": 100_000_000}).json()
        assert body["success"] is True
        assert "data" in body

    def test_result_has_both_modes(self, client):
        data = client.post("/api/team/optimize", json={"budget": 100_000_000}).json()["data"]
        assert "max_points" in data
        assert "best_value" in data

    def test_max_points_has_drivers_and_constructors(self, client):
        data = client.post("/api/team/optimize", json={"budget": 100_000_000}).json()["data"]
        mp = data["max_points"]
        assert "drivers" in mp
        assert "constructors" in mp
        assert "total_xp" in mp
        assert "total_price" in mp

    def test_feasible_flag_present(self, client):
        data = client.post("/api/team/optimize", json={"budget": 100_000_000}).json()["data"]
        assert "feasible" in data["max_points"]

    def test_budget_constraint_respected(self, client):
        data = client.post("/api/team/optimize", json={"budget": 100_000_000}).json()["data"]
        mp = data["max_points"]
        if mp["feasible"]:
            assert mp["total_price"] <= 100_000_000

    def test_tight_budget_may_be_infeasible(self, client):
        # $1 budget — should return infeasible gracefully, not 500
        r = client.post("/api/team/optimize", json={"budget": 1})
        assert r.status_code == 200
        data = r.json()["data"]
        assert "max_points" in data
