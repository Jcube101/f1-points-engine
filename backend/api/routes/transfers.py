"""Transfer Planner — Phase 2 Feature 5.

Provides a 3-race rolling transfer plan for a user's current team.
For each upcoming race, identifies the weakest driver by projected xP on that
circuit type and suggests the best available in-budget replacement. Also flags
when a chip (Wildcard / Limitless) would deliver more value than individual moves.
"""

from datetime import date as date_type

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.data.models import Driver, FantasyPoints, Race, Constructor, DriverCircuitProfile
from backend.core.expected_points import calculate_xp
from backend.core.config import CURRENT_SEASON

router = APIRouter(prefix="/api/transfers", tags=["transfers"])

_CHIP_UNDERPERFORMERS_THRESHOLD = 2   # ≥ this many weak drivers → suggest chip
_UPGRADE_XP_MARGIN = 0.15              # replacement must be ≥15% better xP
_BUDGET_FLEX = 500_000                 # allow $0.5M overspend for a marginal upgrade


def _driver_xp(drv: Driver, circuit_type: str, db: Session) -> float:
    """Compute current xP for a driver at a given circuit type."""
    fp = (
        db.query(FantasyPoints)
        .filter_by(driver_id=drv.id)
        .order_by(FantasyPoints.race_id.desc())
        .limit(3)
        .all()
    )
    pts = [r.total_pts for r in reversed(fp)]
    return calculate_xp(pts, drv.code, circuit_type)


def _chip_suggestion(team_xps: list[float], total_xp: float) -> str | None:
    """Return a chip suggestion string if circumstances warrant it, else None."""
    weak_count = sum(1 for x in team_xps if x < 10)
    if weak_count >= _CHIP_UNDERPERFORMERS_THRESHOLD:
        return (
            f"Wildcard — {weak_count} of your drivers have low projected xP for this circuit. "
            "A full team reset could deliver significantly better returns."
        )
    return None


@router.get("/plan")
async def get_transfer_plan(
    drivers: str = Query(default="", description="Comma-separated driver codes, e.g. VER,NOR,PIA,HAD,GAS"),
    constructors: str = Query(default="", description="Comma-separated constructor codes, e.g. MCL,RBR"),
    season: int = Query(default=CURRENT_SEASON),
    db: Session = Depends(get_db),
):
    """
    Return a 3-race transfer plan for the given team.

    For each of the next 3 races:
    - Identifies the weakest driver (lowest xP for that circuit type)
    - Suggests the best available in-budget replacement with ≥15% higher xP
    - Flags if a chip would be more efficient than individual transfers

    Response shape: { success, data: [{ race, round, drop, add, budget_delta,
                                         chip_alternative, reasoning }] }
    """
    driver_codes = [c.strip().upper() for c in drivers.split(",") if c.strip()]
    if not driver_codes:
        return {"success": False, "error": "No drivers provided", "data": None}

    today = date_type.today().isoformat()
    upcoming_races = (
        db.query(Race)
        .filter(Race.season == season, Race.date >= today)
        .order_by(Race.round_number)
        .limit(3)
        .all()
    )
    if not upcoming_races:
        return {"success": True, "data": []}

    # Resolve team drivers from codes
    team_drivers: list[Driver] = []
    for code in driver_codes:
        drv = db.query(Driver).filter_by(code=code).first()
        if drv:
            team_drivers.append(drv)

    if not team_drivers:
        return {"success": False, "error": "No valid driver codes found", "data": None}

    total_team_price = sum(d.price for d in team_drivers)

    # All available active drivers that are NOT in the current team
    available = db.query(Driver).filter(
        Driver.price > 0,
        Driver.code.notin_(driver_codes),
    ).all()

    plan = []
    for race in upcoming_races:
        ct = race.circuit_type

        # Compute xP for every team driver at this circuit
        driver_xps = [(d, _driver_xp(d, ct, db)) for d in team_drivers]
        weakest_driver, weakest_xp = min(driver_xps, key=lambda x: x[1])

        freed_budget = weakest_driver.price
        # Budget available for the replacement (freed slot + any saved budget)
        budget_for_new = freed_budget + _BUDGET_FLEX

        # Find best available replacement
        best_rep: Driver | None = None
        best_rep_xp = 0.0
        for candidate in available:
            if candidate.price > budget_for_new:
                continue
            cand_xp = _driver_xp(candidate, ct, db)
            if cand_xp > weakest_xp * (1 + _UPGRADE_XP_MARGIN) and cand_xp > best_rep_xp:
                best_rep_xp = cand_xp
                best_rep = candidate

        # Chip suggestion
        team_xp_vals = [x for _, x in driver_xps]
        chip_alt = _chip_suggestion(team_xp_vals, sum(team_xp_vals))

        # Build reasoning string
        if best_rep:
            gain = round(best_rep_xp - weakest_xp, 1)
            reasoning = (
                f"{weakest_driver.name} projects {weakest_xp:.1f} xP on {ct} circuits. "
                f"{best_rep.name} projects {best_rep_xp:.1f} xP — a +{gain} gain. "
                f"Price delta: ${(best_rep.price - weakest_driver.price) / 1e6:+.1f}M."
            )
        else:
            reasoning = (
                f"{weakest_driver.name} is your weakest pick for {race.name.replace(' Grand Prix', ' GP')} "
                f"({weakest_xp:.1f} xP on {ct} circuits), but no clear in-budget upgrade was found."
            )

        plan.append({
            "race": race.name.replace(" Grand Prix", " GP"),
            "round": race.round_number,
            "date": race.date,
            "circuit_type": ct,
            "drop": {
                "id": weakest_driver.id,
                "code": weakest_driver.code,
                "name": weakest_driver.name,
                "xp": round(weakest_xp, 1),
                "price": weakest_driver.price,
            },
            "add": {
                "id": best_rep.id,
                "code": best_rep.code,
                "name": best_rep.name,
                "xp": round(best_rep_xp, 1),
                "price": best_rep.price,
            } if best_rep else None,
            "budget_delta": int(best_rep.price - weakest_driver.price) if best_rep else 0,
            "chip_alternative": chip_alt,
            "reasoning": reasoning,
        })

    return {"success": True, "data": plan}
