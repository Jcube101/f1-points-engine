"""API routes for score validation."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.data.models import ScoreValidation, Race, Driver
from backend.data.fantasy_validator import run_validation

router = APIRouter(prefix="/api/validation", tags=["validation"])


@router.get("/latest")
async def get_latest_validation(db: Session = Depends(get_db)):
    """
    Return the most recent score validation results.

    Response: { success, data: [{ race, driver, our_score, official_score, delta }] }
    """
    records = (
        db.query(ScoreValidation)
        .order_by(ScoreValidation.validated_at.desc())
        .limit(100)
        .all()
    )
    result = []
    for v in records:
        race = db.query(Race).get(v.race_id)
        driver = db.query(Driver).get(v.driver_id)
        result.append({
            "race_name": race.name if race else "",
            "driver_name": driver.name if driver else "",
            "driver_code": driver.code if driver else "",
            "our_score": v.our_score,
            "official_score": v.official_score,
            "delta": v.delta,
            "validated_at": v.validated_at.isoformat() if v.validated_at else None,
        })
    return {"success": True, "data": result}


@router.post("/run")
async def run_latest_validation(db: Session = Depends(get_db)):
    """
    Manually trigger score validation for the most recent race.

    Response: { success, data: validation summary }
    """
    race = db.query(Race).order_by(Race.round_number.desc()).first()
    if not race:
        return {"success": False, "error": "No races found", "data": None}

    summary = await run_validation(db, race)
    return {"success": True, "data": summary}
