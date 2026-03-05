"""
Integration tests for /api/transfers/plan endpoint.
"""


class TestTransferPlan:
    def test_returns_200_with_drivers(self, client):
        r = client.get("/api/transfers/plan?drivers=VER,LEC")
        assert r.status_code == 200

    def test_response_envelope(self, client):
        body = client.get("/api/transfers/plan?drivers=VER,LEC").json()
        assert body["success"] is True
        assert "data" in body

    def test_returns_list(self, client):
        data = client.get("/api/transfers/plan?drivers=VER,LEC").json()["data"]
        assert isinstance(data, list)

    def test_max_3_moves(self, client):
        data = client.get("/api/transfers/plan?drivers=VER,LEC").json()["data"]
        assert len(data) <= 3

    def test_move_has_required_fields(self, client):
        data = client.get("/api/transfers/plan?drivers=VER,LEC").json()["data"]
        if data:
            move = data[0]
            required = {"race", "round", "drop", "budget_delta", "reasoning"}
            assert required.issubset(move.keys())

    def test_drop_has_code(self, client):
        data = client.get("/api/transfers/plan?drivers=VER,LEC").json()["data"]
        for move in data:
            assert "code" in move["drop"]

    def test_add_is_none_or_has_code(self, client):
        data = client.get("/api/transfers/plan?drivers=VER,LEC").json()["data"]
        for move in data:
            if move["add"] is not None:
                assert "code" in move["add"]

    def test_empty_drivers_returns_empty_plan(self, client):
        r = client.get("/api/transfers/plan")
        # Missing required param — either 422 or empty plan
        assert r.status_code in {200, 422}

    def test_single_driver(self, client):
        r = client.get("/api/transfers/plan?drivers=VER")
        assert r.status_code == 200

    def test_chip_alternative_is_string_or_none(self, client):
        data = client.get("/api/transfers/plan?drivers=VER,LEC,HAD,SAI").json()["data"]
        for move in data:
            assert move["chip_alternative"] is None or isinstance(move["chip_alternative"], str)
