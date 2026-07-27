"""API routes for post-race sync status."""

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.data.models import Race, RaceResult, SyncLog
from backend.core.config import CURRENT_SEASON
from backend.seed import REAL_DATA_SOURCES

router = APIRouter(prefix="/api/sync", tags=["sync"])


@router.get("/status")
async def sync_status(db: Session = Depends(get_db)):
    """
    Report how up-to-date the stored results are vs the season calendar.

    Wrapped in the standard { success, data } envelope (per CLAUDE.md). The data
    payload contains: last_sync, last_round_synced, rounds_in_db, next_round,
    next_round_name, next_round_date, status.

    status:
      - "no_data"     — no real results stored yet
      - "behind"      — a round whose date has passed is not yet synced
      - "up_to_date"  — every already-run round is stored
    """
    season = CURRENT_SEASON
    today = date.today().isoformat()

    races = (
        db.query(Race)
        .filter(Race.season == season)
        .order_by(Race.round_number.asc())
        .all()
    )

    synced_rounds = {
        r[0] for r in (
            db.query(Race.round_number)
            .join(RaceResult, RaceResult.race_id == Race.id)
            .filter(Race.season == season)
            .filter(RaceResult.data_source.in_(REAL_DATA_SOURCES))
            .distinct()
            .all()
        )
    }
    rounds_in_db = len(synced_rounds)
    last_round_synced = max(synced_rounds) if synced_rounds else None

    # A round is "due" once its date has passed; if any due round is unsynced → behind.
    due_rounds = [r.round_number for r in races if r.date <= today]
    behind = any(rn not in synced_rounds for rn in due_rounds)

    if rounds_in_db == 0:
        status = "no_data"
    elif behind:
        status = "behind"
    else:
        status = "up_to_date"

    # Next race = first calendar round still in the future.
    next_race = next((r for r in races if r.date > today), None)

    last_log = (
        db.query(SyncLog)
        .filter(SyncLog.success.is_(True))
        .order_by(SyncLog.synced_at.desc())
        .first()
    )

    return {
        "success": True,
        "data": {
            "last_sync": last_log.synced_at.isoformat() if last_log and last_log.synced_at else None,
            "last_round_synced": last_round_synced,
            "rounds_in_db": rounds_in_db,
            "next_round": next_race.round_number if next_race else None,
            "next_round_name": next_race.name if next_race else None,
            "next_round_date": next_race.date if next_race else None,
            "status": status,
        },
    }
