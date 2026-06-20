"""
Tests for the post-race sync logic (backend.scripts.sync_results.run_sync).

The Jolpica API is fully mocked: `get_latest_completed_round` (how many rounds
are done) and `_fetch_2026_round` (per-round normalised rows) are monkeypatched,
so no network call is made. A self-contained in-memory DB is seeded with a
calendar and a pre-existing round-1 result tagged data_source='jolpica' to prove
already-synced rounds are skipped and new ones are stored.
"""

import asyncio

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.db.database import Base
from backend.data.models import (
    Constructor, Driver, Race, RaceResult, FantasyPoints,
)
from backend.scripts import sync_results


def _row(code, constructor_cid, quali, race, grid, *, fastest_lap=False,
         dnf=False, sprint_pos=None):
    """Build one normalised result row in the shape _fetch_2026_round returns."""
    gained = (grid - race) if (race is not None and not dnf) else 0
    return {
        "code": code,
        "constructor_cid": constructor_cid,
        "quali_pos": quali,
        "q2_reached": quali <= 15,
        "q3_reached": quali <= 10,
        "race_pos": None if dnf else race,
        "dnf": dnf,
        "dsq": False,
        "grid": grid,
        "positions_gained_race": gained,
        "overtakes": max(0, gained // 2) if gained > 0 else 0,
        "fastest_lap": fastest_lap,
        "sprint_pos": sprint_pos,
        "sprint_dnf": False,
        "data_source": "jolpica",
    }


@pytest.fixture()
def db():
    """In-memory DB: 2 constructors, 3 drivers, 3x 2026 races, R1 already synced."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()

    session.add_all([
        Constructor(id=1, name="Red Bull Racing", code="RED_BULL", price=28_000_000),
        Constructor(id=2, name="McLaren", code="MCLAREN", price=28_000_000),
    ])
    session.flush()
    session.add_all([
        Driver(id=1, name="Max Verstappen", code="VER", team_id=1, price=27_000_000),
        Driver(id=2, name="Lando Norris", code="NOR", team_id=2, price=27_000_000),
        Driver(id=3, name="Oscar Piastri", code="PIA", team_id=2, price=25_000_000),
    ])
    session.add_all([
        Race(id=1, name="Australian Grand Prix", circuit="Albert Park", country="Australia",
             date="2026-03-08", round_number=1, season=2026, circuit_type="street"),
        Race(id=2, name="Chinese Grand Prix", circuit="Shanghai", country="China",
             date="2026-03-15", round_number=2, season=2026, circuit_type="balanced"),
        Race(id=3, name="Japanese Grand Prix", circuit="Suzuka", country="Japan",
             date="2026-03-29", round_number=3, season=2026, circuit_type="power"),
    ])
    session.flush()
    # R1 already synced from real data — must be skipped by the sync.
    session.add(RaceResult(race_id=1, driver_id=1, constructor_id=1, qualifying_pos=1,
                           race_pos=1, grid_pos=1, data_source="jolpica"))
    session.add(FantasyPoints(race_id=1, driver_id=1, total_pts=35.0))
    session.commit()
    try:
        yield session
    finally:
        session.close()


def _patch_jolpica(monkeypatch, latest_round, round_rows):
    async def fake_latest_round(season):
        return latest_round  # standings 'round' = latest completed round

    async def fake_fetch_round(round_num):
        return round_rows.get(round_num, [])

    monkeypatch.setattr(sync_results, "get_latest_completed_round", fake_latest_round)
    monkeypatch.setattr(sync_results, "_fetch_2026_round", fake_fetch_round)


class TestRunSync:
    def test_new_round_stored_existing_skipped(self, db, monkeypatch):
        # R1 & R2 completed; R1 already in DB, R2 is new; R3 not completed.
        round2_rows = [
            _row("VER", "red_bull", quali=2, race=2, grid=2),
            _row("NOR", "mclaren", quali=1, race=1, grid=1, fastest_lap=True),
        ]
        _patch_jolpica(monkeypatch, latest_round=2, round_rows={2: round2_rows})

        summary = asyncio.run(sync_results.run_sync(db, dry_run=False))

        assert summary["success"] is True
        assert summary["errors"] == []
        assert summary["already_synced"] == [1]
        assert summary["new_rounds"] == [2]          # R1 skipped, R3 not completed
        assert summary["synced_rounds"] == [2]
        assert summary["drivers_updated"] == 2

        # R2 now has both drivers stored as jolpica…
        r2 = db.query(RaceResult).filter_by(race_id=2).all()
        assert {r.driver_id for r in r2} == {1, 2}
        assert all(r.data_source == "jolpica" for r in r2)
        # …and R1 was not duplicated.
        assert db.query(RaceResult).filter_by(race_id=1).count() == 1
        # R3 (not completed) was not touched.
        assert db.query(RaceResult).filter_by(race_id=3).count() == 0

    def test_dry_run_writes_nothing(self, db, monkeypatch):
        round2_rows = [_row("VER", "red_bull", quali=2, race=2, grid=2)]
        _patch_jolpica(monkeypatch, latest_round=2, round_rows={2: round2_rows})

        before = db.query(RaceResult).count()
        summary = asyncio.run(sync_results.run_sync(db, dry_run=True))

        assert summary["new_rounds"] == [2]
        assert summary["synced_rounds"] == []        # dry run stores nothing
        assert db.query(RaceResult).count() == before

    def test_up_to_date_when_no_new_rounds(self, db, monkeypatch):
        # Only R1 completed, and R1 is already synced → nothing to do.
        _patch_jolpica(monkeypatch, latest_round=1, round_rows={})
        summary = asyncio.run(sync_results.run_sync(db, dry_run=False))
        assert summary["new_rounds"] == []
        assert summary["synced_rounds"] == []
        assert summary["success"] is True

    def test_api_unreachable_is_failure(self, db, monkeypatch):
        # Empty season results = API unreachable → must report failure for systemd.
        async def no_round(season):
            return None
        monkeypatch.setattr(sync_results, "get_latest_completed_round", no_round)

        summary = asyncio.run(sync_results.run_sync(db, dry_run=False))
        assert summary["success"] is False
        assert summary["errors"]
