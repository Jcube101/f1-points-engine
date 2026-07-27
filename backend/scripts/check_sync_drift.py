"""
Sync drift check — F1 Points Engine
====================================
Read-only health check: is any already-run round of the current season NOT
yet backed by real (Jolpica) results? Reuses the exact same "completed vs
synced" logic as sync_results.py so the two can never disagree.

Exists to catch a specific window: sync_results.py's per-round fetch falls
back to synthetic data (seed._generate_2026_round) whenever Jolpica returns
nothing for a round — which is correct for a round that hasn't been raced
yet, but also fires on a transient API hiccup for a round that already has
happened. That round then sits on data_source='generated' until the next
successful sync run replaces it (see store_2026_round's replace-on-upgrade
logic) — up to a week away on the weekly f1-sync.timer schedule. Run this
script on a tighter interval to shrink that window.

    .venv/bin/python backend/scripts/check_sync_drift.py            # detect only
    .venv/bin/python backend/scripts/check_sync_drift.py --fix      # detect + remediate now

Exit 0: no drift (or --fix resolved it all). Exit 1: drift found and unresolved.
"""

import argparse
import asyncio
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.db.database import SessionLocal, init_db
from backend.core.config import CURRENT_SEASON
from backend.data.models import SyncLog
from backend.scripts.sync_results import _completed_rounds, _synced_rounds, run_sync

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger("check_sync_drift")


async def _drifted_rounds(db) -> list[int]:
    """Rounds Jolpica reports as completed but that aren't backed by real data yet."""
    season = CURRENT_SEASON
    completed = await _completed_rounds(season)
    synced = _synced_rounds(db, season)
    return [r for r in completed if r not in synced]


def main() -> int:
    parser = argparse.ArgumentParser(description="Check for (and optionally fix) post-race sync drift.")
    parser.add_argument("--fix", action="store_true",
                         help="Run a full sync immediately if drift is found (default: report only).")
    args = parser.parse_args()

    init_db()
    db = SessionLocal()
    try:
        drifted = asyncio.run(_drifted_rounds(db))
        if not drifted:
            logger.info("No drift — every completed round is backed by real data.")
            return 0

        logger.warning("Drift detected: round(s) %s completed but not yet synced with real data.", drifted)
        if not args.fix:
            print(f"\nDRIFT: round(s) {drifted} completed but still on placeholder/missing data. "
                  f"Re-run with --fix to remediate now.")
            return 1

        logger.info("Attempting immediate remediation via run_sync()...")
        summary = asyncio.run(run_sync(db))
        db.add(SyncLog(rounds_synced=len(summary["synced_rounds"]), success=summary["success"]))
        db.commit()

        still_drifted = [r for r in drifted if r not in summary["synced_rounds"]]
        if still_drifted:
            logger.error("Remediation incomplete — still drifted: %s. Errors: %s",
                         still_drifted, summary["errors"])
            print(f"\nDRIFT: could not fully remediate round(s) {still_drifted}.")
            return 1

        print(f"\nDRIFT RESOLVED: round(s) {drifted} synced with real data.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
