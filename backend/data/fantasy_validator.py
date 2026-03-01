"""
Fantasy Score Validator — F1 Points Engine
============================================
Post-race validation: fetches official scores from the F1 Fantasy API and
compares them to our computed scores. Stores diffs in ScoreValidation table.

IMPORTANT: The F1 Fantasy API is unofficial and undocumented.
Used only as a post-race validation layer. Never used as a primary data source.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

import httpx
from sqlalchemy.orm import Session

from backend.core.config import F1_FANTASY_BASE_URL
from backend.data.models import ScoreValidation, Race, Driver

logger = logging.getLogger(__name__)


async def fetch_official_scores(race_id: int) -> dict[str, float]:
    """
    Attempt to fetch official fantasy scores from the F1 Fantasy API.

    Args:
        race_id: Internal race ID.

    Returns:
        Dict mapping driver_code → official_score. Empty dict on failure.

    Note: This API is unofficial and may be unavailable. Failure is non-fatal.
    """
    # The F1 Fantasy API is undocumented; we attempt a known endpoint pattern
    url = f"{F1_FANTASY_BASE_URL}/drivers_scores.json"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            # Try to parse whatever shape the response has
            scores: dict[str, float] = {}
            if isinstance(data, list):
                for item in data:
                    code = item.get("code") or item.get("abbreviation", "")
                    pts = item.get("total_points") or item.get("score", 0)
                    if code:
                        scores[code] = float(pts)
            elif isinstance(data, dict):
                for code, pts in data.items():
                    scores[code] = float(pts)
            return scores
    except Exception as exc:
        logger.warning("F1 Fantasy API unavailable: %s. Skipping validation.", exc)
        return {}


def store_validation(
    db: Session,
    race: Race,
    driver: Driver,
    our_score: float,
    official_score: Optional[float],
) -> ScoreValidation:
    """
    Store or update a score validation record.

    Args:
        db: SQLAlchemy session.
        race: Race ORM object.
        driver: Driver ORM object.
        our_score: Score computed by our scoring engine.
        official_score: Official score from F1 Fantasy API, or None if unavailable.

    Returns:
        The saved ScoreValidation record.
    """
    delta = (our_score - official_score) if official_score is not None else None
    if delta and abs(delta) > 0:
        logger.warning(
            "Score discrepancy: Driver=%s Race=%s Our=%.1f Official=%.1f Delta=%.1f",
            driver.code, race.name, our_score, official_score, delta,
        )

    existing = (
        db.query(ScoreValidation)
        .filter_by(race_id=race.id, driver_id=driver.id)
        .first()
    )
    if existing:
        existing.our_score = our_score
        existing.official_score = official_score
        existing.delta = delta
        existing.validated_at = datetime.now(timezone.utc)
        db.commit()
        return existing

    record = ScoreValidation(
        race_id=race.id,
        driver_id=driver.id,
        our_score=our_score,
        official_score=official_score,
        delta=delta,
        validated_at=datetime.now(timezone.utc),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


async def run_validation(db: Session, race: Race) -> dict:
    """
    Run full validation for a race: fetch official scores and compare to ours.

    Args:
        db: SQLAlchemy session.
        race: Race ORM object to validate.

    Returns:
        Summary dict: total_drivers, matched, discrepancies, max_delta.
    """
    from backend.data.models import FantasyPoints

    official = await fetch_official_scores(race.id)

    fantasy_rows = db.query(FantasyPoints).filter_by(race_id=race.id).all()
    matched = 0
    discrepancies = 0
    max_delta = 0.0

    for fp in fantasy_rows:
        driver = db.query(Driver).get(fp.driver_id)
        if not driver:
            continue
        official_score = official.get(driver.code)
        store_validation(db, race, driver, fp.total_pts, official_score)
        if official_score is not None:
            delta = abs(fp.total_pts - official_score)
            max_delta = max(max_delta, delta)
            if delta == 0:
                matched += 1
            else:
                discrepancies += 1

    return {
        "total_drivers": len(fantasy_rows),
        "matched": matched,
        "discrepancies": discrepancies,
        "max_delta": max_delta,
        "official_scores_available": bool(official),
    }
