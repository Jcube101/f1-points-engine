"""
conftest.py — shared pytest fixtures for F1 Points Engine backend tests.

Uses an in-memory SQLite database created fresh for every test session.
All models are registered before create_all() so every table exists.
The FastAPI dependency get_db is overridden to use the test DB.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# ── In-memory test DB ─────────────────────────────────────────────────────────
# StaticPool ensures all sessions share the SAME underlying SQLite connection,
# which is required for in-memory DBs — each new connection would see an empty DB.
SQLALCHEMY_TEST_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_TEST_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _create_tables():
    """Import every model so SQLAlchemy registers them before create_all()."""
    from backend.db.database import Base
    from backend.data.models import (  # noqa: F401
        Constructor, Driver, Race, RaceResult,
        FantasyPoints, ScoreValidation, DriverCircuitProfile,
    )
    Base.metadata.create_all(bind=engine)


_create_tables()


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── App + TestClient ──────────────────────────────────────────────────────────
@pytest.fixture(scope="session")
def client():
    from backend.db.database import get_db
    from backend.main import app
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()


# ── Minimal seeded DB ─────────────────────────────────────────────────────────
@pytest.fixture(scope="session", autouse=True)
def seed_test_db():
    """
    Seeds a minimal but complete dataset covering all tested endpoints:
      - 2 constructors (Red Bull, Ferrari)
      - 4 drivers (VER + HAD at RBR, LEC + SAI at Ferrari)
      - 6 races in 2025 (past) + 5 races in 2026 (upcoming)
      - RaceResult + FantasyPoints for all drivers x 2025 races
      - DriverCircuitProfile for all drivers x 3 circuit types
    """
    from backend.data.models import (
        Constructor, Driver, Race, RaceResult, FantasyPoints, DriverCircuitProfile,
    )

    db = TestingSessionLocal()
    try:
        # ── Constructors ──────────────────────────────────────────────────────
        rbr = Constructor(id=1, name="Red Bull Racing", code="RBR",
                          color_hex="#3671C6", price=34_500_000)
        fer = Constructor(id=2, name="Ferrari", code="FER",
                          color_hex="#E8002D", price=32_000_000)
        db.add_all([rbr, fer])
        db.flush()

        # ── Drivers ───────────────────────────────────────────────────────────
        ver = Driver(id=1, name="Max Verstappen", code="VER", team_id=1,
                     nationality="Dutch", price=30_000_000, image_url="")
        had = Driver(id=2, name="Isack Hadjar", code="HAD", team_id=1,
                     nationality="French", price=7_500_000, image_url="")
        lec = Driver(id=3, name="Charles Leclerc", code="LEC", team_id=2,
                     nationality="Monegasque", price=26_000_000, image_url="")
        sai = Driver(id=4, name="Carlos Sainz", code="SAI", team_id=2,
                     nationality="Spanish", price=20_000_000, image_url="")
        db.add_all([ver, had, lec, sai])
        db.flush()

        # ── 2025 races (past — for history / form / standings) ────────────────
        races_2025 = [
            Race(id=1, name="Bahrain Grand Prix",       circuit="Bahrain",   country="Bahrain",
                 date="2025-03-02", round_number=1, season=2025, circuit_type="balanced"),
            Race(id=2, name="Saudi Arabian Grand Prix", circuit="Jeddah",    country="Saudi Arabia",
                 date="2025-03-09", round_number=2, season=2025, circuit_type="street"),
            Race(id=3, name="Australian Grand Prix",    circuit="Melbourne", country="Australia",
                 date="2025-03-16", round_number=3, season=2025, circuit_type="balanced"),
            Race(id=4, name="Japanese Grand Prix",      circuit="Suzuka",    country="Japan",
                 date="2025-04-06", round_number=4, season=2025, circuit_type="power"),
            Race(id=5, name="Chinese Grand Prix",       circuit="Shanghai",  country="China",
                 date="2025-04-20", round_number=5, season=2025, circuit_type="balanced"),
            Race(id=6, name="Monaco Grand Prix",        circuit="Monaco",    country="Monaco",
                 date="2025-05-25", round_number=6, season=2025, circuit_type="street"),
        ]
        # ── 2026 races (upcoming — for transfer planner + fixture difficulty) ─
        races_2026 = [
            Race(id=10, name="Bahrain Grand Prix",       circuit="Bahrain",   country="Bahrain",
                 date="2026-03-15", round_number=1, season=2026, circuit_type="balanced"),
            Race(id=11, name="Saudi Arabian Grand Prix", circuit="Jeddah",    country="Saudi Arabia",
                 date="2026-03-22", round_number=2, season=2026, circuit_type="street"),
            Race(id=12, name="Australian Grand Prix",    circuit="Melbourne", country="Australia",
                 date="2026-04-05", round_number=3, season=2026, circuit_type="balanced"),
            Race(id=13, name="Japanese Grand Prix",      circuit="Suzuka",    country="Japan",
                 date="2026-04-19", round_number=4, season=2026, circuit_type="power"),
            Race(id=14, name="Chinese Grand Prix",       circuit="Shanghai",  country="China",
                 date="2026-05-03", round_number=5, season=2026, circuit_type="balanced"),
        ]
        db.add_all(races_2025 + races_2026)
        db.flush()

        # ── Race results + fantasy points ─────────────────────────────────────
        # (driver_id, race_id, q_pos, r_pos, total_pts)
        results_data = [
            # Round 1 — balanced
            (1, 1, 1, 1, 38.0), (2, 1, 5, 6, 12.0), (3, 1, 2, 2, 26.0), (4, 1, 3, 3, 20.0),
            # Round 2 — street
            (1, 2, 2, 1, 36.0), (2, 2, 6, 5, 14.0), (3, 2, 1, 2, 28.0), (4, 2, 3, 4, 18.0),
            # Round 3 — balanced
            (1, 3, 1, 1, 40.0), (2, 3, 7, 8,  8.0), (3, 3, 3, 2, 24.0), (4, 3, 4, 3, 19.0),
            # Round 4 — power
            (1, 4, 1, 1, 42.0), (2, 4, 8, 9,  6.0), (3, 4, 3, 3, 22.0), (4, 4, 2, 2, 30.0),
            # Round 5 — balanced
            (1, 5, 2, 1, 37.0), (2, 5, 6, 7, 10.0), (3, 5, 1, 2, 27.0), (4, 5, 4, 3, 21.0),
            # Round 6 — street
            (1, 6, 1, 2, 30.0), (2, 6, 9, 10,  5.0), (3, 6, 2, 1, 35.0), (4, 6, 3, 4, 18.0),
        ]

        constructor_map = {1: 1, 2: 1, 3: 2, 4: 2}  # driver_id -> constructor_id

        for driver_id, race_id, q_pos, r_pos, total_pts in results_data:
            db.add(RaceResult(
                race_id=race_id,
                driver_id=driver_id,
                constructor_id=constructor_map[driver_id],
                qualifying_pos=q_pos,
                race_pos=r_pos,
                positions_gained_race=0,
                overtakes=0,
            ))
            db.add(FantasyPoints(
                race_id=race_id,
                driver_id=driver_id,
                qualifying_pts=float(q_pos),
                sprint_pts=0.0,
                race_pts=float(r_pos),
                total_pts=total_pts,
                xp_score=0.0,
            ))

        db.flush()

        # ── DriverCircuitProfile ──────────────────────────────────────────────
        profiles = [
            DriverCircuitProfile(driver_id=1, circuit_type="balanced", avg_points=38.3, races_counted=3),
            DriverCircuitProfile(driver_id=1, circuit_type="street",   avg_points=33.0, races_counted=2),
            DriverCircuitProfile(driver_id=1, circuit_type="power",    avg_points=42.0, races_counted=1),
            DriverCircuitProfile(driver_id=2, circuit_type="balanced", avg_points=10.0, races_counted=3),
            DriverCircuitProfile(driver_id=2, circuit_type="street",   avg_points=9.5,  races_counted=2),
            DriverCircuitProfile(driver_id=2, circuit_type="power",    avg_points=6.0,  races_counted=1),
            DriverCircuitProfile(driver_id=3, circuit_type="balanced", avg_points=25.7, races_counted=3),
            DriverCircuitProfile(driver_id=3, circuit_type="street",   avg_points=31.5, races_counted=2),
            DriverCircuitProfile(driver_id=3, circuit_type="power",    avg_points=22.0, races_counted=1),
            DriverCircuitProfile(driver_id=4, circuit_type="balanced", avg_points=20.0, races_counted=3),
            DriverCircuitProfile(driver_id=4, circuit_type="street",   avg_points=18.0, races_counted=2),
            DriverCircuitProfile(driver_id=4, circuit_type="power",    avg_points=30.0, races_counted=1),
        ]
        db.add_all(profiles)
        db.commit()

    finally:
        db.close()
