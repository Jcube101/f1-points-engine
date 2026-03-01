"""API routes for team optimizer."""

from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.data.models import Driver, Constructor, FantasyPoints
from backend.core.optimizer import Asset, optimize_max_points, optimize_best_value
from backend.core.expected_points import calculate_xp, xp_per_million

router = APIRouter(prefix="/api/team", tags=["team"])


class OptimizeRequest(BaseModel):
    budget: Optional[float] = 100_000_000


def _build_assets(db: Session):
    """Build Asset objects for all drivers and constructors."""
    drivers = db.query(Driver).all()
    constructors = db.query(Constructor).all()

    driver_assets = []
    for d in drivers:
        fp_rows = (
            db.query(FantasyPoints)
            .filter_by(driver_id=d.id)
            .order_by(FantasyPoints.race_id.desc())
            .limit(3)
            .all()
        )
        recent_pts = [row.total_pts for row in reversed(fp_rows)]
        xp = calculate_xp(recent_pts, d.code, "balanced")
        value = xp_per_million(xp, d.price)
        driver_assets.append(
            Asset(
                id=d.id,
                name=d.name,
                code=d.code,
                price=d.price,
                xp=xp,
                xp_per_million=value,
                asset_type="driver",
                team_code=d.constructor.code if d.constructor else "",
            )
        )

    constructor_assets = []
    for c in constructors:
        # Estimate constructor xP as sum of driver xPs
        c_drivers = db.query(Driver).filter_by(team_id=c.id).all()
        total_xp = 0.0
        for cd in c_drivers:
            fp_rows = (
                db.query(FantasyPoints)
                .filter_by(driver_id=cd.id)
                .order_by(FantasyPoints.race_id.desc())
                .limit(3)
                .all()
            )
            recent_pts = [row.total_pts for row in reversed(fp_rows)]
            total_xp += calculate_xp(recent_pts, cd.code, "balanced")
        value = xp_per_million(total_xp, c.price)
        constructor_assets.append(
            Asset(
                id=c.id,
                name=c.name,
                code=c.code,
                price=c.price,
                xp=total_xp,
                xp_per_million=value,
                asset_type="constructor",
            )
        )

    return driver_assets, constructor_assets


def _asset_to_dict(a: Asset) -> dict:
    return {
        "id": a.id,
        "name": a.name,
        "code": a.code,
        "price": a.price,
        "xp": a.xp,
        "xp_per_million": a.xp_per_million,
        "type": a.asset_type,
        "team_code": a.team_code,
    }


@router.post("/optimize")
async def optimize_team(req: OptimizeRequest, db: Session = Depends(get_db)):
    """
    Return two optimized teams: max_points (PuLP) and best_value (greedy).

    Body: { budget?: float }
    Response: { success, data: { max_points: {...}, best_value: {...} } }
    """
    driver_assets, constructor_assets = _build_assets(db)
    budget = req.budget or 100_000_000

    max_pts = optimize_max_points(driver_assets, constructor_assets, budget)
    best_val = optimize_best_value(driver_assets, constructor_assets, budget)

    def fmt(result: dict) -> dict:
        return {
            "drivers": [_asset_to_dict(a) for a in result["drivers"]],
            "constructors": [_asset_to_dict(a) for a in result["constructors"]],
            "total_xp": result["total_xp"],
            "total_price": result["total_price"],
            "feasible": result["feasible"],
        }

    return {
        "success": True,
        "data": {
            "max_points": fmt(max_pts),
            "best_value": fmt(best_val),
        },
    }
