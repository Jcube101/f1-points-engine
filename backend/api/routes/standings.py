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


@router.get("/progression")
async def get_season_progression(
    season: int = Query(default=CURRENT_SEASON),
    db: Session = Depends(get_db),
):
    """
    Return cumulative fantasy points per driver per round for a given season.

    Computes progressive totals from the FantasyPoints table — does not rely on
    the Ergast API. Used to render the championship points progression chart.

    Response: { success, data: [{ round, round_name, <driver_code>: cumulative_pts, ... }] }
    """
    races = db.query(Race).filter_by(season=season).order_by(Race.round_number.asc()).all()
    if not races:
        return {"success": True, "data": []}

    race_ids = [r.id for r in races]
    fp_rows = db.query(FantasyPoints).filter(FantasyPoints.race_id.in_(race_ids)).all()

    race_info: dict[int, tuple[int, str]] = {
        r.id: (r.round_number, r.name) for r in races
    }

    all_driver_ids = list({fp.driver_id for fp in fp_rows})
    drivers_in_data = db.query(Driver).filter(Driver.id.in_(all_driver_ids)).all()
    driver_id_to_code: dict[int, str] = {d.id: d.code for d in drivers_in_data}

    # Aggregate points per round per driver
    per_round: dict[int, dict[str, float]] = {}
    for fp in fp_rows:
        if fp.race_id not in race_info:
            continue
        round_num, _ = race_info[fp.race_id]
        code = driver_id_to_code.get(fp.driver_id)
        if not code:
            continue
        per_round.setdefault(round_num, {})[code] = fp.total_pts

    # Build cumulative progression across rounds
    result = []
    cumulative: dict[str, float] = {}
    for race in races:
        rn = race.round_number
        for code, pts in per_round.get(rn, {}).items():
            cumulative[code] = round(cumulative.get(code, 0.0) + pts, 1)
        entry: dict[str, object] = {
            "round": rn,
            "round_name": race.name.replace(" Grand Prix", " GP"),
        }
        entry.update(cumulative)
        result.append(entry)

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
