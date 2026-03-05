"""API routes for race calendar, results, and fixture difficulty."""

from datetime import date as date_type

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.data.models import Race, RaceResult, Driver, DriverCircuitProfile
from backend.core.config import CURRENT_SEASON

router = APIRouter(prefix="/api/races", tags=["races"])


@router.get("")
async def get_races(
    season: int = Query(default=CURRENT_SEASON),
    db: Session = Depends(get_db),
):
    """Return the race calendar for a given season (defaults to current season)."""
    races = (
        db.query(Race)
        .filter_by(season=season)
        .order_by(Race.round_number)
        .all()
    )
    return {
        "success": True,
        "data": [
            {
                "id": r.id,
                "name": r.name,
                "circuit": r.circuit,
                "country": r.country,
                "date": r.date,
                "round_number": r.round_number,
                "season": r.season,
                "session_type": r.session_type,
                "circuit_type": r.circuit_type,
            }
            for r in races
        ],
    }


@router.get("/{race_id}/results")
async def get_race_results(race_id: int, db: Session = Depends(get_db)):
    """Return all results for a specific race."""
    race = db.query(Race).get(race_id)
    if not race:
        return {"success": False, "error": "Race not found", "data": None}

    results = db.query(RaceResult).filter_by(race_id=race_id).all()
    data = []
    for r in results:
        driver = db.query(Driver).get(r.driver_id)
        data.append({
            "driver_id": r.driver_id,
            "driver_name": driver.name if driver else "",
            "driver_code": driver.code if driver else "",
            "qualifying_pos": r.qualifying_pos,
            "race_pos": r.race_pos,
            "sprint_pos": r.sprint_pos,
            "dnf": r.dnf,
            "dsq": r.dsq,
            "fastest_lap": r.fastest_lap,
            "driver_of_day": r.driver_of_day,
            "positions_gained_race": r.positions_gained_race,
            "overtakes": r.overtakes,
        })
    return {"success": True, "data": data}


@router.get("/upcoming-difficulty")
async def get_upcoming_difficulty(
    drivers: str = Query(default="", description="Comma-separated driver codes, e.g. VER,NOR,PIA"),
    season: int = Query(default=CURRENT_SEASON),
    db: Session = Depends(get_db),
):
    """
    Return the next 5 races with their circuit type and, for each driver code provided,
    their DriverCircuitProfile fit score (0–10) for that circuit type.

    Used to render the Fixture View tab on the Standings page.
    """
    today = date_type.today().isoformat()
    upcoming = (
        db.query(Race)
        .filter(Race.season == season, Race.date >= today)
        .order_by(Race.round_number)
        .limit(5)
        .all()
    )

    driver_codes = [c.strip().upper() for c in drivers.split(",") if c.strip()]

    # Pre-fetch all DriverCircuitProfile rows for the requested drivers
    driver_objs = {}
    profile_map: dict[str, dict[str, float]] = {}  # code -> {circuit_type -> avg_pts}
    max_by_type: dict[str, float] = {}

    for code in driver_codes:
        drv = db.query(Driver).filter_by(code=code).first()
        if not drv:
            continue
        driver_objs[code] = drv
        profiles = db.query(DriverCircuitProfile).filter_by(driver_id=drv.id).all()
        profile_map[code] = {p.circuit_type: p.avg_points for p in profiles}

    # Compute normalised max per circuit type across all profiles in DB
    for ct in ("street", "power", "balanced"):
        all_profiles = db.query(DriverCircuitProfile).filter_by(circuit_type=ct).all()
        max_by_type[ct] = max((p.avg_points for p in all_profiles), default=1) or 1

    result = []
    for race in upcoming:
        ct = race.circuit_type
        driver_fits = {}
        for code in driver_codes:
            avg = profile_map.get(code, {}).get(ct, 0.0)
            fit_score = round(avg / max_by_type.get(ct, 1) * 10, 1)
            driver_fits[code] = fit_score

        result.append({
            "round": race.round_number,
            "race_name": race.name.replace(" Grand Prix", " GP"),
            "circuit_type": ct,
            "date": race.date,
            "driver_fits": driver_fits,
        })

    return {"success": True, "data": result}
