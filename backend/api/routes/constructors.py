"""API routes for constructor (team) data — includes Phase 2 teammate comparison."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.data.models import Constructor, Driver
from backend.api.routes.drivers import _compute_teammate_stats

router = APIRouter(prefix="/api/constructors", tags=["constructors"])


@router.get("")
async def get_constructors(db: Session = Depends(get_db)):
    """Return all constructors with price and driver list."""
    constructors = db.query(Constructor).all()
    result = []
    for c in constructors:
        drivers = db.query(Driver).filter_by(team_id=c.id).all()
        result.append({
            "id": c.id,
            "name": c.name,
            "code": c.code,
            "color_hex": c.color_hex,
            "price": c.price,
            "drivers": [{"id": d.id, "name": d.name, "code": d.code} for d in drivers],
        })
    return {"success": True, "data": result}


@router.get("/{constructor_id}/teammates")
async def get_teammate_comparison(constructor_id: int, db: Session = Depends(get_db)):
    """
    Return 2025 head-to-head stats for both drivers in a constructor:
    qualifying H2H record, average race position, average fantasy points,
    and average points per million. Used to power the Teammate Comparison modal.
    """
    constructor = db.query(Constructor).get(constructor_id)
    if not constructor:
        return {"success": False, "error": "Constructor not found", "data": None}

    # Only active 2026-grid drivers (price > 0), ordered by id for consistency
    drivers = (
        db.query(Driver)
        .filter_by(team_id=constructor_id)
        .filter(Driver.price > 0)
        .order_by(Driver.id)
        .all()
    )
    if len(drivers) < 2:
        return {"success": True, "data": None}

    data = _compute_teammate_stats(drivers[0], drivers[1], db)
    return {"success": True, "data": data}
