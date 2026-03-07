"""
Monte Carlo Championship Odds Simulator.

POST /api/simulator/title-odds
- Runs 10,000 simulations of the remaining 2026 season
- Uses each driver's last 5 race results weighted by recency (50/30/20% → oldest)
- Results cached in-memory for 1 hour
- Supports optional pace multipliers per driver (0.5x–1.5x)
"""

import random
import time
import logging
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.data.models import Driver, Race, FantasyPoints
from backend.core.config import CURRENT_SEASON

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/simulator", tags=["simulator"])

# In-memory cache: key → (timestamp, result)
_cache: dict[str, tuple[float, dict]] = {}
CACHE_TTL = 3600  # 1 hour


class PaceMultiplier(BaseModel):
    driver_code: str
    multiplier: float = Field(default=1.0, ge=0.5, le=1.5)


class TitleOddsRequest(BaseModel):
    season: int = CURRENT_SEASON
    simulations: int = Field(default=10_000, ge=100, le=50_000)
    pace_multipliers: list[PaceMultiplier] = []


def _get_driver_finish_distribution(
    driver_id: int,
    db: Session,
    num_drivers: int = 20,
) -> list[float]:
    """
    Return a list of finish-position weights for positions 1..num_drivers
    based on the driver's last 5 race results, weighted by recency (newest=50%).

    Returns a probability distribution (sums to 1.0).
    """
    recent = (
        db.query(FantasyPoints)
        .join(Race, Race.id == FantasyPoints.race_id)
        .filter(FantasyPoints.driver_id == driver_id)
        .order_by(Race.round_number.desc())
        .limit(5)
        .all()
    )

    # Recency weights: [0.50, 0.30, 0.20] for 3+ results; extend as needed
    recency_w = [0.50, 0.30, 0.20, 0.10, 0.05]

    if not recent:
        # No history → uniform distribution
        weight = 1.0 / num_drivers
        return [weight] * num_drivers

    # Map xp_score → approximate finish position (higher xp = better finish)
    # Normalise across all drivers by using position weights summing to 1
    weights = [0.0] * num_drivers
    total_rw = 0.0

    for i, fp in enumerate(recent):
        rw = recency_w[i] if i < len(recency_w) else 0.05
        total_rw += rw
        xp = fp.xp_score or fp.total_pts or 0.0
        # xp_score ranges ~0–25 for a race; map to finish position probability boost
        # Higher xp → concentrate probability on top positions
        boost_factor = max(0.1, xp / 20.0)  # normalise so ~20xp = 1.0
        for pos in range(num_drivers):
            # Exponential decay favouring top positions, scaled by boost_factor
            pos_weight = boost_factor * (0.85 ** pos)
            weights[pos] += rw * pos_weight

    if total_rw > 0:
        weights = [w / total_rw for w in weights]

    # Normalise to sum to 1
    total = sum(weights)
    if total <= 0:
        weight = 1.0 / num_drivers
        return [weight] * num_drivers
    return [w / total for w in weights]


def _simulate_race(
    driver_ids: list[int],
    distributions: dict[int, list[float]],
    pace_map: dict[str, float],
    driver_codes: dict[int, str],
    rng: random.Random,
) -> list[int]:
    """
    Simulate a single race. Returns list of driver_ids in finish order (index 0 = P1).

    Uses weighted sampling without replacement — draw a score for each driver
    from a position distribution, apply pace multiplier, sort descending.
    """
    n = len(driver_ids)
    scores: dict[int, float] = {}
    for did in driver_ids:
        dist = distributions.get(did, [1.0 / n] * n)
        # Sample a score: draw a position weight then add noise
        pos_weights = dist[:n]
        if len(pos_weights) < n:
            pos_weights += [0.01] * (n - len(pos_weights))
        # Pick random position weighted by distribution, invert so P1 = high score
        positions = list(range(1, n + 1))
        total = sum(pos_weights)
        norm = [w / total for w in pos_weights]
        chosen_pos = rng.choices(positions, weights=norm, k=1)[0]
        score = (n - chosen_pos) + rng.gauss(0, 1.5)
        # Apply pace multiplier
        mult = pace_map.get(driver_codes.get(did, ""), 1.0)
        score *= mult
        scores[did] = score

    return sorted(driver_ids, key=lambda d: scores[d], reverse=True)


@router.post("/title-odds")
def title_odds(req: TitleOddsRequest, db: Session = Depends(get_db)):
    """
    Run Monte Carlo simulation of remaining season title race.

    Returns win probability, current points, and simulated average final points
    for each driver, plus a plain-English scenario summary.
    """
    pace_map = {pm.driver_code: pm.multiplier for pm in req.pace_multipliers}
    cache_key = f"{req.season}:{req.simulations}:{sorted(pace_map.items())}"

    # Check cache (bypass if pace_multipliers are set — interactive)
    if not pace_map:
        cached = _cache.get(cache_key)
        if cached and (time.time() - cached[0]) < CACHE_TTL:
            logger.info("Returning cached title odds for %d", req.season)
            return {"success": True, "data": cached[1]}

    # Fetch all 2026 drivers (active only)
    drivers_db = db.query(Driver).filter(Driver.price > 0).all()
    if not drivers_db:
        return {"success": False, "data": None, "error": "No active drivers found"}

    driver_ids = [d.id for d in drivers_db]
    driver_codes: dict[int, str] = {d.id: d.code for d in drivers_db}
    driver_names: dict[int, str] = {d.id: d.name for d in drivers_db}

    # Fetch current championship standings approximation from FantasyPoints
    # Sum all fantasy points per driver as proxy for championship points
    current_pts: dict[int, float] = {}
    for d in drivers_db:
        total = sum(fp.total_pts for fp in d.fantasy_points)
        current_pts[d.id] = total

    # Count remaining 2026 races (date > today)
    from datetime import date
    today_str = date.today().isoformat()
    remaining_races_db = (
        db.query(Race)
        .filter(Race.season == req.season, Race.date > today_str)
        .order_by(Race.round_number)
        .all()
    )
    remaining = len(remaining_races_db)
    if remaining == 0:
        # Season over — use final standings
        remaining = 1

    # Build finish distributions for each driver
    distributions: dict[int, list[float]] = {}
    for did in driver_ids:
        distributions[did] = _get_driver_finish_distribution(did, db, len(driver_ids))

    # F1 race points: P1=25, P2=18, P3=15, ... P10=1, P11+=0
    F1_PTS = [25, 18, 15, 12, 10, 8, 6, 4, 2, 1]

    # Monte Carlo: simulate remaining_races × simulations
    win_count: dict[int, int] = {did: 0 for did in driver_ids}
    total_final_pts: dict[int, float] = {did: 0.0 for did in driver_ids}

    rng = random.Random()

    for _ in range(req.simulations):
        sim_pts: dict[int, float] = dict(current_pts)
        for _race in range(remaining):
            order = _simulate_race(driver_ids, distributions, pace_map, driver_codes, rng)
            for pos, did in enumerate(order):
                race_pts = F1_PTS[pos] if pos < len(F1_PTS) else 0
                sim_pts[did] = sim_pts.get(did, 0) + race_pts

        # Champion = highest simulated points
        champion = max(driver_ids, key=lambda d: sim_pts[d])
        win_count[champion] += 1

        for did in driver_ids:
            total_final_pts[did] += sim_pts[did]

    # Build result list sorted by win probability descending
    odds_list = []
    for d in drivers_db:
        did = d.id
        win_prob = win_count[did] / req.simulations
        avg_final = total_final_pts[did] / req.simulations
        odds_list.append({
            "driver_code": d.code,
            "driver_name": d.name,
            "win_probability": round(win_prob, 4),
            "current_points": round(current_pts.get(did, 0), 1),
            "simulated_avg_final": round(avg_final, 1),
        })

    odds_list.sort(key=lambda x: x["win_probability"], reverse=True)

    # Generate plain-English scenario summary
    top = odds_list[0] if odds_list else {}
    second = odds_list[1] if len(odds_list) > 1 else {}
    top_name = top.get("driver_name", "").split()[-1] if top else "Unknown"
    sec_name = second.get("driver_name", "").split()[-1] if second else ""
    top_pct = round(top.get("win_probability", 0) * 100, 1)
    sec_pct = round(second.get("win_probability", 0) * 100, 1)

    if top_pct >= 70:
        summary = (
            f"{top_name} is the overwhelming favourite with a {top_pct}% chance of winning the title. "
            f"Barring a catastrophic run of results, the championship looks settled."
        )
    elif top_pct >= 45:
        summary = (
            f"{top_name} leads the title race ({top_pct}%) with {remaining} races remaining, "
            f"but {sec_name} ({sec_pct}%) keeps the fight alive. Consistency will be key."
        )
    else:
        summary = (
            f"The title race is wide open — {top_name} leads at {top_pct}% but {sec_name} ({sec_pct}%) "
            f"and others remain in contention across the final {remaining} rounds."
        )

    result = {
        "season": req.season,
        "simulations": req.simulations,
        "remaining_races": remaining,
        "odds": odds_list,
        "scenario_summary": summary,
    }

    # Cache if no pace multipliers
    if not pace_map:
        _cache[cache_key] = (time.time(), result)

    return {"success": True, "data": result}
