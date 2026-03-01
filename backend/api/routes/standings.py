"""API routes for WDC and WCC standings."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.data.ergast_client import get_driver_standings, get_constructor_standings
from backend.data.models import Driver, FantasyPoints, Race
from backend.core.expected_points import calculate_xp, xp_per_million
from backend.core.config import CURRENT_SEASON

router = APIRouter(prefix="/api/standings", tags=["standings"])


@router.get("/wdc")
async def get_wdc(season: int = Query(default=CURRENT_SEASON)):
    """
    Return F1 Drivers Championship standings for a given season.

    Response: { success, data: [{ position, driver, points, wins, team }] }
    """
    standings = await get_driver_standings(str(season))
    result = []
    for s in standings:
        d = s.get("Driver", {})
        constructors = s.get("Constructors", [{}])
        result.append({
            "position": int(s.get("position", 0)),
            "driver_id": d.get("driverId", ""),
            "driver_code": d.get("code", ""),
            "driver_name": f"{d.get('givenName', '')} {d.get('familyName', '')}".strip(),
            "nationality": d.get("nationality", ""),
            "team": constructors[0].get("name", "") if constructors else "",
            "points": float(s.get("points", 0)),
            "wins": int(s.get("wins", 0)),
        })
    return {"success": True, "data": result}


@router.get("/wcc")
async def get_wcc(season: int = Query(default=CURRENT_SEASON)):
    """
    Return F1 Constructors Championship standings for a given season.

    Response: { success, data: [{ position, constructor, points, wins }] }
    """
    standings = await get_constructor_standings(str(season))
    result = []
    for s in standings:
        c = s.get("Constructor", {})
        result.append({
            "position": int(s.get("position", 0)),
            "constructor_id": c.get("constructorId", ""),
            "constructor_name": c.get("name", ""),
            "nationality": c.get("nationality", ""),
            "points": float(s.get("points", 0)),
            "wins": int(s.get("wins", 0)),
        })
    return {"success": True, "data": result}


@router.get("/value")
async def get_value_leaderboard(
    season: int = Query(default=CURRENT_SEASON),
    db: Session = Depends(get_db),
):
    """
    Return fantasy value leaderboard filtered by season: all drivers ranked by xP per $M.

    Response: { success, data: [driver value objects] }
    """
    season_race_ids = [
        r.id for r in db.query(Race).filter_by(season=season).all()
    ]

    drivers = db.query(Driver).filter(Driver.price > 0).all()
    result = []
    for d in drivers:
        fp_rows = (
            db.query(FantasyPoints)
            .filter(
                FantasyPoints.driver_id == d.id,
                FantasyPoints.race_id.in_(season_race_ids) if season_race_ids else False,
            )
            .order_by(FantasyPoints.race_id.desc())
            .limit(3)
            .all()
        ) if season_race_ids else []
        recent_pts = [row.total_pts for row in reversed(fp_rows)]
        total_pts = sum(row.total_pts for row in fp_rows)
        xp = calculate_xp(recent_pts, d.code, "balanced")
        value = xp_per_million(xp, d.price)
        result.append({
            "id": d.id,
            "name": d.name,
            "code": d.code,
            "team": d.constructor.name if d.constructor else "",
            "price": d.price,
            "total_fantasy_pts": total_pts,
            "xp": xp,
            "value_score": value,
            "price_trend": 0,
        })
    result.sort(key=lambda x: x["value_score"], reverse=True)
    return {"success": True, "data": result}
