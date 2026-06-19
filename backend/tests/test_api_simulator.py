"""
Integration tests for POST /api/simulator/title-odds (Phase-3 Monte Carlo).

The championship-points baseline is mocked: backend.api.routes.simulator
._fetch_wdc_points is monkeypatched to return a fixed {code: points} dict, so
the test never depends on real Jolpica/WDC network calls. A small simulation
count keeps the test fast.
"""

from backend.api.routes import simulator


def _post(client, **body):
    base = {"season": 2026, "simulations": 200, "pace_multipliers": []}
    base.update(body)
    return client.post("/api/simulator/title-odds", json=base)


class TestTitleOdds:
    def _mock_wdc(self, monkeypatch):
        # raising=False: the helper may be supplied by a parallel agent; if it
        # is wired into the route, current_points will reflect these values.
        def fake_wdc(*args, **kwargs):
            return {"VER": 100.0, "LEC": 50.0}

        monkeypatch.setattr(simulator, "_fetch_wdc_points", fake_wdc, raising=False)

    def test_success_envelope(self, client, monkeypatch):
        self._mock_wdc(monkeypatch)
        r = _post(client)
        assert r.status_code == 200
        body = r.json()
        assert body["success"] is True
        assert "data" in body

    def test_odds_is_list(self, client, monkeypatch):
        self._mock_wdc(monkeypatch)
        data = _post(client).json()["data"]
        assert isinstance(data["odds"], list)
        assert len(data["odds"]) >= 1

    def test_entry_shape(self, client, monkeypatch):
        self._mock_wdc(monkeypatch)
        data = _post(client).json()["data"]
        entry = data["odds"][0]
        required = {
            "driver_code", "win_probability",
            "current_points", "simulated_avg_final",
        }
        assert required.issubset(entry.keys())

    def test_win_probability_in_range(self, client, monkeypatch):
        self._mock_wdc(monkeypatch)
        data = _post(client).json()["data"]
        for entry in data["odds"]:
            assert 0.0 <= entry["win_probability"] <= 1.0

    def test_win_probabilities_sum_to_about_one(self, client, monkeypatch):
        self._mock_wdc(monkeypatch)
        data = _post(client).json()["data"]
        total = sum(e["win_probability"] for e in data["odds"])
        # Exactly one champion per simulation, so probabilities sum to ~1.
        assert 0.95 <= total <= 1.05

    def test_current_points_numeric(self, client, monkeypatch):
        self._mock_wdc(monkeypatch)
        data = _post(client).json()["data"]
        for entry in data["odds"]:
            assert isinstance(entry["current_points"], (int, float))

    def test_ver_current_points_reflects_mock_if_wired(self, client, monkeypatch):
        # If the route uses _fetch_wdc_points as its baseline, VER's
        # current_points must reflect the mocked 100.0. If the helper is not
        # yet wired into the module, assert defensively that the value is still
        # numeric. (Check existence BEFORE patching, since monkeypatch with
        # raising=False would otherwise create the attribute.)
        helper_present = hasattr(simulator, "_fetch_wdc_points")
        self._mock_wdc(monkeypatch)
        data = _post(client).json()["data"]
        ver = next((e for e in data["odds"] if e["driver_code"] == "VER"), None)
        assert ver is not None
        if helper_present:
            # Helper exists and is mocked — baseline should be the mocked value.
            assert ver["current_points"] == 100.0
        else:
            assert isinstance(ver["current_points"], (int, float))
