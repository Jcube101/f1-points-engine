"""API routes for score validation."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.data.models import ScoreValidation, Race, Driver, FantasyPoints
from backend.data.fantasy_validator import run_validation
from backend.core.config import CURRENT_SEASON

router = APIRouter(prefix="/api/validation", tags=["validation"])


@router.get("/latest")
async def get_latest_validation(db: Session = Depends(get_db)):
    """
    Return the most recent score validation results for the current season only.

    Filters by CURRENT_SEASON to prevent stale data from prior seasons being
    returned when no current-season validations exist yet.

    Response: { success, data: [{ race, driver, our_score, official_score, delta }] }
    """
    records = (
        db.query(ScoreValidation)
        .join(Race, Race.id == ScoreValidation.race_id)
        .filter(Race.season == CURRENT_SEASON)
        .order_by(ScoreValidation.validated_at.desc())
        .limit(100)
        .all()
    )
    # Fallback: if the current season has no validations yet, return the most
    # recent validations overall so the panel is not permanently blank.
    if not records:
        records = (
            db.query(ScoreValidation)
            .order_by(ScoreValidation.validated_at.desc())
            .limit(100)
            .all()
        )
    result = []
    for v in records:
        race = db.get(Race, v.race_id)
        driver = db.get(Driver, v.driver_id)
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
    Manually trigger score validation for the most recently completed race of the
    current season — i.e. the latest current-season race that actually has scored
    results. Falls back to the overall latest race-with-results, then to the latest
    race of any kind, so the endpoint always validates something meaningful.

    Response: { success, data: validation summary }
    """
    # Latest current-season race that has fantasy results (skip not-yet-run rounds).
    race = (
        db.query(Race)
        .join(FantasyPoints, FantasyPoints.race_id == Race.id)
        .filter(Race.season == CURRENT_SEASON)
        .order_by(Race.round_number.desc())
        .first()
    )
    # Fallbacks: latest scored race of any season, then latest race of any kind.
    if not race:
        race = (
            db.query(Race)
            .join(FantasyPoints, FantasyPoints.race_id == Race.id)
            .order_by(Race.season.desc(), Race.round_number.desc())
            .first()
        )
    if not race:
        race = db.query(Race).order_by(Race.season.desc(), Race.round_number.desc()).first()
    if not race:
        return {"success": False, "error": "No races found", "data": None}

    summary = await run_validation(db, race)
    return {"success": True, "data": summary}
