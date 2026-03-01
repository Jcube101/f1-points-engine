"""API routes for constructor (team) data."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.data.models import Constructor, Driver

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
