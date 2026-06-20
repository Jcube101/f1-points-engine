"""
Tests for backend.data.fantasy_validator.store_validation and run_validation.

Network is mocked: fetch_official_scores is monkeypatched to return a fixed dict,
so no real F1 Fantasy API call is made. Self-contained: builds its own in-memory
SQLite engine and a minimal seed (one constructor, one driver, one race, one
FantasyPoints row) so the test does not depend on the conftest plugin's DB
instance.
"""

import asyncio

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.db.database import Base
from backend.data import fantasy_validator
from backend.data.models import (
    Constructor, Driver, Race, FantasyPoints, ScoreValidation,
)


@pytest.fixture()
def db():
    """Fresh in-memory DB seeded with one constructor/driver/race/fantasy row."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    con = Constructor(id=1, name="Red Bull Racing", code="RBR", color_hex="#3671C6", price=30_000_000)
    session.add(con)
    session.flush()
    drv = Driver(id=1, name="Max Verstappen", code="VER", team_id=1, price=30_000_000)
    session.add(drv)
    race = Race(id=1, name="Test Grand Prix", circuit="Test", country="Test",
                date="2026-03-08", round_number=1, season=2026, circuit_type="balanced")
    session.add(race)
    session.flush()
    session.add(FantasyPoints(race_id=1, driver_id=1, total_pts=38.0))
    session.commit()
    try:
        yield session
    finally:
        session.close()


def _race_and_driver(db):
    return db.get(Race, 1), db.get(Driver, 1)


class TestStoreValidation:
    def test_writes_record(self, db):
        race, driver = _race_and_driver(db)
        rec = fantasy_validator.store_validation(db, race, driver, our_score=38.0, official_score=38.0)
        assert rec.id is not None
        assert rec.race_id == race.id
        assert rec.driver_id == driver.id
        assert rec.delta == 0.0

    def test_records_delta_on_discrepancy(self, db):
        race, driver = _race_and_driver(db)
        rec = fantasy_validator.store_validation(db, race, driver, our_score=40.0, official_score=38.0)
        assert rec.delta == 2.0

    def test_idempotent_update(self, db):
        race, driver = _race_and_driver(db)
        first = fantasy_validator.store_validation(db, race, driver, our_score=38.0, official_score=38.0)
        second = fantasy_validator.store_validation(db, race, driver, our_score=42.0, official_score=38.0)
        assert second.id == first.id
        assert second.our_score == 42.0


class TestRunValidation:
    def test_summary_shape_and_rows_written(self, db, monkeypatch):
        async def fake_fetch(race_id):
            return {"VER": 38.0}

        monkeypatch.setattr(fantasy_validator, "fetch_official_scores", fake_fetch)
        race = db.get(Race, 1)
        summary = asyncio.run(fantasy_validator.run_validation(db, race))

        expected_keys = {"total_drivers", "matched", "discrepancies", "max_delta", "official_scores_available"}
        assert expected_keys.issubset(summary.keys())
        assert summary["official_scores_available"] is True
        assert summary["total_drivers"] >= 1
        assert summary["matched"] == 1  # VER 38.0 == official 38.0
        rows = db.query(ScoreValidation).filter_by(race_id=race.id).all()
        assert len(rows) >= 1

    def test_no_official_scores_available_flag(self, db, monkeypatch):
        async def fake_fetch(race_id):
            return {}

        monkeypatch.setattr(fantasy_validator, "fetch_official_scores", fake_fetch)
        race = db.get(Race, 1)
        summary = asyncio.run(fantasy_validator.run_validation(db, race))
        assert summary["official_scores_available"] is False
        assert summary["matched"] == 0
        assert summary["discrepancies"] == 0
