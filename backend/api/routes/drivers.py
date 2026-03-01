"""API routes for driver data."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.data.models import Driver, FantasyPoints
from backend.core.expected_points import calculate_xp, xp_per_million

router = APIRouter(prefix="/api/drivers", tags=["drivers"])


@router.get("")
async def get_drivers(db: Session = Depends(get_db)):
    """
    Return all drivers with price, xP, and value score.

    Response: { success, data: [driver objects] }
    """
    drivers = db.query(Driver).filter(Driver.price > 0).all()
    result = []
    for d in drivers:
        # Compute xP from last 3 race fantasy points
        fp_rows = (
            db.query(FantasyPoints)
            .filter_by(driver_id=d.id)
            .order_by(FantasyPoints.race_id.desc())
            .limit(3)
            .all()
        )
        recent_pts = [row.total_pts for row in reversed(fp_rows)]
        circuit_type = "balanced"  # default; ideally from next race
        xp = calculate_xp(recent_pts, d.code, circuit_type)
        value = xp_per_million(xp, d.price)

        result.append({
            "id": d.id,
            "name": d.name,
            "code": d.code,
            "team_id": d.team_id,
            "team_name": d.constructor.name if d.constructor else "",
            "team_color": d.constructor.color_hex if d.constructor else "#888888",
            "price": d.price,
            "nationality": d.nationality,
            "image_url": d.image_url,
            "xp": xp,
            "value_score": value,
            "total_fantasy_pts": sum(row.total_pts for row in fp_rows),
        })

    return {"success": True, "data": result}


@router.get("/{driver_id}")
async def get_driver(driver_id: int, db: Session = Depends(get_db)):
    """Return a single driver by ID."""
    driver = db.query(Driver).get(driver_id)
    if not driver:
        return {"success": False, "error": "Driver not found", "data": None}

    fp_rows = (
        db.query(FantasyPoints)
        .filter_by(driver_id=driver_id)
        .order_by(FantasyPoints.race_id.desc())
        .limit(3)
        .all()
    )
    recent_pts = [row.total_pts for row in reversed(fp_rows)]
    xp = calculate_xp(recent_pts, driver.code, "balanced")
    value = xp_per_million(xp, driver.price)

    return {
        "success": True,
        "data": {
            "id": driver.id,
            "name": driver.name,
            "code": driver.code,
            "team_name": driver.constructor.name if driver.constructor else "",
            "price": driver.price,
            "nationality": driver.nationality,
            "xp": xp,
            "value_score": value,
            "fantasy_history": [
                {"race_id": row.race_id, "total_pts": row.total_pts, "xp_score": row.xp_score}
                for row in fp_rows
            ],
        },
    }
