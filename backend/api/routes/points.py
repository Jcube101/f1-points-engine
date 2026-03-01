"""API routes for fantasy points calculation and leaderboard."""

from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.data.models import Driver, Constructor, Race, RaceResult, FantasyPoints
from backend.core.scoring import (
    qualifying_position_points, qualifying_bonus_points,
    race_position_points, race_bonus_points,
    sprint_position_points, sprint_bonus_points,
)
from backend.core.expected_points import calculate_xp, xp_per_million

router = APIRouter(prefix="/api/points", tags=["points"])


class CalculateRequest(BaseModel):
    driver_ids: list[int]
    constructor_ids: list[int]
    race_id: int
    drs_boost_driver_id: Optional[int] = None
    no_negative: bool = False


@router.post("/calculate")
async def calculate_points(req: CalculateRequest, db: Session = Depends(get_db)):
    """
    Calculate fantasy points for a given team + race.

    Body: { driver_ids, constructor_ids, race_id, drs_boost_driver_id?, no_negative? }
    Response: { success, data: { total, breakdown } }
    """
    race = db.query(Race).get(req.race_id)
    if not race:
        return {"success": False, "error": "Race not found", "data": None}

    breakdown = []
    grand_total = 0.0

    for driver_id in req.driver_ids:
        result = db.query(RaceResult).filter_by(race_id=req.race_id, driver_id=driver_id).first()
        driver = db.query(Driver).get(driver_id)
        if not result or not driver:
            continue

        # Qualifying points
        q_pts = qualifying_position_points(result.qualifying_pos, result.dsq)
        q_bonus = qualifying_bonus_points(result.positions_gained_quali, 0)

        # Race points
        r_pts = race_position_points(result.race_pos, result.dnf, result.dsq)
        r_bonus = race_bonus_points(
            result.positions_gained_race,
            result.overtakes,
            result.fastest_lap,
            result.driver_of_day,
        )

        # Sprint points (if applicable)
        s_pts = 0
        if result.sprint_pos is not None:
            s_pts = sprint_position_points(result.sprint_pos)

        total = q_pts + q_bonus + r_pts + r_bonus + s_pts

        # Apply chips
        if req.no_negative:
            total = max(0.0, total)
        if req.drs_boost_driver_id == driver_id:
            total *= 2

        grand_total += total
        breakdown.append({
            "driver_id": driver_id,
            "driver_name": driver.name,
            "qualifying_pts": q_pts + q_bonus,
            "race_pts": r_pts + r_bonus,
            "sprint_pts": s_pts,
            "total": total,
        })

    return {
        "success": True,
        "data": {
            "total": grand_total,
            "breakdown": breakdown,
        },
    }


@router.get("/leaderboard")
async def get_leaderboard(db: Session = Depends(get_db)):
    """
    Return driver + constructor value rankings (xP per $M).

    Response: { success, data: { drivers, constructors } }
    """
    drivers = db.query(Driver).all()
    driver_data = []
    for d in drivers:
        fp_rows = (
            db.query(FantasyPoints)
            .filter_by(driver_id=d.id)
            .order_by(FantasyPoints.race_id.desc())
            .limit(3)
            .all()
        )
        recent_pts = [row.total_pts for row in reversed(fp_rows)]
        total_pts = sum(row.total_pts for row in fp_rows)
        xp = calculate_xp(recent_pts, d.code, "balanced")
        value = xp_per_million(xp, d.price)
        driver_data.append({
            "id": d.id,
            "name": d.name,
            "code": d.code,
            "team": d.constructor.name if d.constructor else "",
            "price": d.price,
            "total_fantasy_pts": total_pts,
            "xp": xp,
            "value_score": value,
            "price_trend": 0,  # Phase 2: price rise/fall tracking
        })

    driver_data.sort(key=lambda x: x["value_score"], reverse=True)

    return {"success": True, "data": {"drivers": driver_data, "constructors": []}}
