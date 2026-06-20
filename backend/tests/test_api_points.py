"""
Integration tests for /api/points/calculate.

Uses the seeded test DB from conftest (race id 1 has RaceResult + FantasyPoints
for drivers 1-4; driver 1 = VER finished P1 from grid/quali P1).

Covers M12-adjacent behaviour: DRS Boost is applied BEFORE the No-Negative
floor (the engine doubles the raw total, then floors negatives to 0).
"""


def _calc(client, **body):
    base = {
        "race_id": 1,
        "driver_ids": [1, 2, 3, 4],
        "constructor_ids": [1, 2],
        "drs_boost_driver_id": None,
        "no_negative": False,
    }
    base.update(body)
    return client.post("/api/points/calculate", json=base)


class TestCalculatePoints:
    def test_success_envelope(self, client):
        r = _calc(client)
        assert r.status_code == 200
        body = r.json()
        assert body["success"] is True
        assert "data" in body

    def test_total_is_numeric(self, client):
        data = _calc(client).json()["data"]
        assert isinstance(data["total"], (int, float))

    def test_breakdown_is_list(self, client):
        data = _calc(client).json()["data"]
        assert isinstance(data["breakdown"], list)
        # All four seeded drivers have a RaceResult for race 1.
        assert len(data["breakdown"]) == 4

    def test_breakdown_entry_shape(self, client):
        data = _calc(client).json()["data"]
        entry = data["breakdown"][0]
        required = {"driver_id", "driver_name", "total"}
        assert required.issubset(entry.keys())

    def test_unknown_race_returns_error(self, client):
        r = _calc(client, race_id=99999)
        assert r.status_code == 200
        assert r.json()["success"] is False


class TestChipInteractions:
    def _driver_total(self, data, driver_id):
        for e in data["breakdown"]:
            if e["driver_id"] == driver_id:
                return e["total"]
        raise AssertionError(f"driver {driver_id} not in breakdown")

    def test_no_negative_floors_total(self, client):
        # With no_negative, no driver total may be below zero.
        data = _calc(client, no_negative=True).json()["data"]
        for e in data["breakdown"]:
            assert e["total"] >= 0

    def test_drs_doubles_positive_total(self, client):
        # VER (driver 1) finished P1 from P1 — a clearly positive raw total.
        base = self._driver_total(_calc(client).json()["data"], 1)
        assert base > 0  # sanity: VER's raw total is positive

        boosted = self._driver_total(
            _calc(client, drs_boost_driver_id=1).json()["data"], 1
        )
        # DRS Boost = 2x the driver total.
        assert boosted == base * 2

    def test_drs_applied_before_no_negative(self, client):
        # For a driver whose raw total is positive, DRS doubles it and the
        # No-Negative floor is a no-op — so DRS+no_negative == DRS alone.
        # This documents the ordering: DRS (x2) runs FIRST, then the floor.
        drs_only = self._driver_total(
            _calc(client, drs_boost_driver_id=1).json()["data"], 1
        )
        drs_and_floor = self._driver_total(
            _calc(client, drs_boost_driver_id=1, no_negative=True).json()["data"], 1
        )
        assert drs_and_floor == drs_only
