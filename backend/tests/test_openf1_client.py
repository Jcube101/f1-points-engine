"""
Unit tests for backend.data.openf1_client.build_live_snapshot.

All network I/O is mocked: the module's async fetch helpers are monkeypatched
to return tiny fixture lists, so no real OpenF1 call is ever made.

Covers the live-pipeline behaviours flagged in the audit (C1/C3):
  - positions_gained is computed from grid vs current position (not hard-coded 0)
  - total_laps honours the explicit argument
  - constructors is a non-empty list when drivers share a team
"""

import asyncio
from datetime import datetime, timedelta, timezone

from backend.data import openf1_client


def _patch_fetchers(monkeypatch, *, positions, laps, pit_stops, drivers, grid):
    """Replace every async fetch helper with a stub returning fixed fixtures."""

    async def fake_positions(session_key):
        return positions

    async def fake_laps(session_key):
        return laps

    async def fake_pit(session_key):
        return pit_stops

    async def fake_drivers(session_key):
        return drivers

    async def fake_grid(session_key):
        return grid

    monkeypatch.setattr(openf1_client, "get_driver_positions", fake_positions)
    monkeypatch.setattr(openf1_client, "get_laps", fake_laps)
    monkeypatch.setattr(openf1_client, "get_pit_stops", fake_pit)
    monkeypatch.setattr(openf1_client, "get_drivers", fake_drivers)
    monkeypatch.setattr(openf1_client, "get_starting_grid", fake_grid)


class TestBuildLiveSnapshot:
    def _run(self, monkeypatch):
        # Two drivers on the same team (Red Bull) + one on Ferrari.
        positions = [
            {"driver_number": 1, "position": 1, "date": "2026-03-15T14:30:00+00:00"},
            {"driver_number": 11, "position": 4, "date": "2026-03-15T14:30:00+00:00"},
            {"driver_number": 16, "position": 2, "date": "2026-03-15T14:30:00+00:00"},
        ]
        # Grid: driver 1 started P3 (gained 2), driver 11 started P5 (gained 1),
        # driver 16 started P2 (gained 0).
        grid = [
            {"driver_number": 1, "position": 3},
            {"driver_number": 11, "position": 5},
            {"driver_number": 16, "position": 2},
        ]
        laps = [
            {"driver_number": 1, "lap_number": 58, "lap_duration": 91.5},
            {"driver_number": 11, "lap_number": 58, "lap_duration": 92.1},
            {"driver_number": 16, "lap_number": 58, "lap_duration": 91.2},
        ]
        drivers = [
            {"driver_number": 1, "name_acronym": "VER", "broadcast_name": "M VERSTAPPEN",
             "team_name": "Red Bull Racing"},
            {"driver_number": 11, "name_acronym": "PER", "broadcast_name": "S PEREZ",
             "team_name": "Red Bull Racing"},
            {"driver_number": 16, "name_acronym": "LEC", "broadcast_name": "C LECLERC",
             "team_name": "Ferrari"},
        ]
        _patch_fetchers(
            monkeypatch,
            positions=positions, laps=laps, pit_stops=[], drivers=drivers, grid=grid,
        )
        return asyncio.run(
            openf1_client.build_live_snapshot(1, "race", total_laps=58)
        )

    def test_total_laps_honours_argument(self, monkeypatch):
        snap = self._run(monkeypatch)
        assert snap["total_laps"] == 58

    def test_drivers_present(self, monkeypatch):
        snap = self._run(monkeypatch)
        assert isinstance(snap["drivers"], list)
        assert len(snap["drivers"]) == 3

    def test_positions_gained_is_computed(self, monkeypatch):
        snap = self._run(monkeypatch)
        by_id = {d["driver_id"]: d for d in snap["drivers"]}
        # VER: grid 3 -> current 1 = +2 gained (non-trivial, not hard-coded 0)
        assert by_id["VER"]["breakdown"]["positions_gained"] == 2
        # PER: grid 5 -> current 4 = +1 gained
        assert by_id["PER"]["breakdown"]["positions_gained"] == 1
        # At least one driver has a non-zero gain
        gains = [d["breakdown"]["positions_gained"] for d in snap["drivers"]]
        assert any(g != 0 for g in gains)

    def test_constructors_non_empty_when_team_shared(self, monkeypatch):
        snap = self._run(monkeypatch)
        assert isinstance(snap["constructors"], list)
        assert len(snap["constructors"]) >= 1
        # Red Bull should appear since two drivers share that team.
        teams = {c["constructor"] for c in snap["constructors"]}
        assert "Red Bull Racing" in teams

    def test_not_stale_when_fetches_succeed(self, monkeypatch):
        snap = self._run(monkeypatch)
        # All stubbed fetchers succeed (no cache fallback) -> not stale.
        assert snap["stale"] is False


class TestGetCurrentSession:
    """
    OpenF1's /sessions endpoint returns the whole season schedule (past + future),
    not just what's happening now. get_current_session() must pick the session
    whose [date_start, date_end] window actually contains the current time —
    not just the last item in the list (a real bug: the last item is often a
    future season-finale session, which made the site show "Live" months early).
    """

    def _patch_sessions(self, monkeypatch, sessions):
        async def fake_get(path, params=None):
            return sessions

        monkeypatch.setattr(openf1_client, "_get", fake_get)

    def test_returns_none_when_all_sessions_are_future(self, monkeypatch):
        sessions = [
            {"session_key": 1, "session_name": "Race",
             "date_start": "2026-12-06T13:00:00+00:00", "date_end": "2026-12-06T15:00:00+00:00"},
        ]
        self._patch_sessions(monkeypatch, sessions)
        assert asyncio.run(openf1_client.get_current_session()) is None

    def test_returns_none_when_all_sessions_are_past(self, monkeypatch):
        sessions = [
            {"session_key": 1, "session_name": "Race",
             "date_start": "2020-01-01T13:00:00+00:00", "date_end": "2020-01-01T15:00:00+00:00"},
        ]
        self._patch_sessions(monkeypatch, sessions)
        assert asyncio.run(openf1_client.get_current_session()) is None

    def test_returns_session_whose_window_contains_now(self, monkeypatch):
        now = datetime.now(timezone.utc)
        start = (now - timedelta(minutes=30)).isoformat()
        end = (now + timedelta(minutes=30)).isoformat()
        sessions = [
            {"session_key": 1, "session_name": "Practice 1",
             "date_start": "2020-01-01T13:00:00+00:00", "date_end": "2020-01-01T15:00:00+00:00"},
            {"session_key": 2, "session_name": "Race",
             "date_start": start, "date_end": end},
            {"session_key": 3, "session_name": "Race",
             "date_start": "2026-12-06T13:00:00+00:00", "date_end": "2026-12-06T15:00:00+00:00"},
        ]
        self._patch_sessions(monkeypatch, sessions)
        result = asyncio.run(openf1_client.get_current_session())
        assert result is not None
        assert result["session_key"] == 2
