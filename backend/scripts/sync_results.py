"""
Post-race result sync — F1 Points Engine
=========================================
Standalone script (NOT run through FastAPI) that ingests newly completed race
results from Jolpica into the same SQLite database the app uses. Designed to be
driven by a systemd timer on the Raspberry Pi (see systemd/f1-sync.timer), but
can also be run by hand:

    .venv/bin/python backend/scripts/sync_results.py
    .venv/bin/python backend/scripts/sync_results.py --dry-run

Behaviour:
- Connects to the app DB (backend.db.database.SessionLocal).
- Asks Jolpica which rounds of the current season are completed.
- Skips any round already stored with data_source in ('jolpica', 'real').
- For each NEW completed round: fetches quali + race (+ sprint) from Jolpica and
  stores RaceResult + FantasyPoints via the SAME pipeline as seed.py
  (backend.seed.store_2026_round → backend.core.scoring).
- Recomputes xP scores and rebuilds DriverCircuitProfile (idempotent, per L-010).
- Records a SyncLog row and exits 0 on success, 1 on any failure (so systemd can
  detect failures via the unit's exit status).
"""

import argparse
import asyncio
import logging
import os
import sys

# Make `backend.*` importable when run directly as a script from the repo root.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy.orm import Session

from backend.db.database import SessionLocal, init_db
from backend.core.config import CURRENT_SEASON
from backend.data.ergast_client import get_latest_completed_round
from backend.data.models import Race, RaceResult, Driver, SyncLog
from backend.seed import (
    _fetch_2026_round, store_2026_round, compute_xp_scores,
    seed_circuit_profiles, _ROUND_NAME_2026,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger("sync_results")

# Result rows already produced from real data are never re-synced.
REAL_DATA_SOURCES = ("jolpica", "real")


async def _completed_rounds(season: int) -> list[int]:
    """Return the round numbers Jolpica reports as completed (1..latest).

    Uses the standings 'round' (latest scored race) rather than the season-wide
    /results endpoint, which is paginated and can omit later rounds.
    """
    latest = await get_latest_completed_round(season)
    if not latest or latest < 1:
        return []
    return list(range(1, latest + 1))


def _synced_rounds(db: Session, season: int) -> set[int]:
    """Rounds of `season` already stored from real data (data_source jolpica/real)."""
    rows = (
        db.query(Race.round_number)
        .join(RaceResult, RaceResult.race_id == Race.id)
        .filter(Race.season == season)
        .filter(RaceResult.data_source.in_(REAL_DATA_SOURCES))
        .distinct()
        .all()
    )
    return {r[0] for r in rows}


async def run_sync(db: Session, dry_run: bool = False) -> dict:
    """Core sync routine. Returns a summary dict; never calls sys.exit / never writes SyncLog.

    summary = {
        season, completed_rounds, already_synced, new_rounds,
        synced_rounds, drivers_updated, errors, success
    }
    """
    season = CURRENT_SEASON
    errors: list[str] = []

    completed = await _completed_rounds(season)
    if not completed:
        # Reaching Jolpica but getting zero rounds with results means the API is
        # unreachable or returned nothing — treat as a failure so systemd alerts.
        errors.append(f"No completed rounds returned by Jolpica for {season} (API unreachable?)")
        return {
            "season": season, "completed_rounds": [], "already_synced": [],
            "new_rounds": [], "synced_rounds": [], "drivers_updated": 0,
            "errors": errors, "success": False,
        }

    already = _synced_rounds(db, season)
    new_rounds = [r for r in completed if r not in already]

    if dry_run:
        return {
            "season": season, "completed_rounds": completed,
            "already_synced": sorted(already), "new_rounds": new_rounds,
            "synced_rounds": [], "drivers_updated": 0, "errors": errors, "success": True,
        }

    driver_code_map = {d.code: d.id for d in db.query(Driver).all()}
    race_round_map = {
        r.round_number: r.id for r in db.query(Race).filter(Race.season == season).all()
    }

    synced: list[int] = []
    drivers_updated = 0
    for rnd in new_rounds:
        race_id = race_round_map.get(rnd)
        if not race_id:
            errors.append(f"R{rnd}: no race row in DB (calendar out of date?) — skipped")
            continue
        try:
            rows = await _fetch_2026_round(rnd)
            if not rows:
                errors.append(f"R{rnd}: no result rows fetched — skipped")
                continue
            inserted = store_2026_round(db, race_id, rows, driver_code_map)
            db.commit()
            synced.append(rnd)
            drivers_updated += inserted
            logger.info("Synced R%d (%s): %d driver rows [%s]", rnd,
                        _ROUND_NAME_2026.get(rnd, "?"), inserted, rows[0]["data_source"])
        except Exception as exc:  # noqa: BLE001 — one bad round shouldn't abort the rest
            db.rollback()
            errors.append(f"R{rnd}: {exc}")
            logger.exception("Failed to sync R%d", rnd)

    # Recompute derived data only if something changed (L-010: profiles depend on
    # FantasyPoints, so rebuild after results are committed).
    if synced:
        compute_xp_scores(db)
        seed_circuit_profiles(db)

    return {
        "season": season, "completed_rounds": completed,
        "already_synced": sorted(already), "new_rounds": new_rounds,
        "synced_rounds": synced, "drivers_updated": drivers_updated,
        "errors": errors, "success": not errors,
    }


def _print_summary(summary: dict, dry_run: bool) -> None:
    print("\n" + "=" * 56)
    print(f"  F1 result sync — season {summary['season']}" + ("  [DRY RUN]" if dry_run else ""))
    print("=" * 56)
    print(f"  Completed rounds (Jolpica): {summary['completed_rounds']}")
    print(f"  Already in DB:              {summary['already_synced']}")
    if dry_run:
        print(f"  Would sync:                {summary['new_rounds'] or '(nothing — up to date)'}")
    else:
        print(f"  Newly synced rounds:       {summary['synced_rounds'] or '(none)'}")
        print(f"  Driver rows updated:       {summary['drivers_updated']}")
    if summary["errors"]:
        print(f"  ERRORS ({len(summary['errors'])}):")
        for e in summary["errors"]:
            print(f"    - {e}")
    print(f"  Result: {'OK' if summary['success'] else 'FAILED'}")
    print("=" * 56)


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync completed F1 race results into the app DB.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be synced without writing to the DB.")
    args = parser.parse_args()

    init_db()  # ensure tables exist (incl. sync_logs) — no-op if already present
    db = SessionLocal()
    try:
        summary = asyncio.run(run_sync(db, dry_run=args.dry_run))
        if not args.dry_run:
            db.add(SyncLog(rounds_synced=len(summary["synced_rounds"]), success=summary["success"]))
            db.commit()
        _print_summary(summary, args.dry_run)
        return 0 if summary["success"] else 1
    except Exception as exc:  # noqa: BLE001 — top-level guard so systemd sees exit 1
        logger.exception("Sync failed with an unexpected error")
        if not args.dry_run:
            try:
                db.rollback()
                db.add(SyncLog(rounds_synced=0, success=False))
                db.commit()
            except Exception:  # noqa: BLE001
                pass
        print(f"\nSync FAILED: {exc}")
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
