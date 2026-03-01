"""API routes for race calendar and results."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.data.models import Race, RaceResult, Driver

router = APIRouter(prefix="/api/races", tags=["races"])


@router.get("")
async def get_races(db: Session = Depends(get_db)):
    """Return the full race calendar for the current season."""
    races = db.query(Race).order_by(Race.round_number).all()
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
