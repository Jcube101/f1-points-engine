"""API routes for driver data — including Phase 2 intelligence features."""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.data.models import Driver, FantasyPoints, Race, RaceResult, DriverCircuitProfile
from backend.core.expected_points import calculate_xp, xp_per_million
from backend.core.config import CURRENT_SEASON

router = APIRouter(prefix="/api/drivers", tags=["drivers"])


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _form_flag(actual_avg: float, xp: float) -> str:
    """Classify a driver's recent form relative to their xP baseline."""
    if xp <= 0:
        return "on_form"
    ratio = actual_avg / xp
    if ratio > 1.2:
        return "overperforming"
    if ratio < 0.8:
        return "underperforming"
    return "on_form"


def _next_race_circuit_type(db: Session, season: int = CURRENT_SEASON) -> str:
    """Return the circuit_type of the next upcoming race in the given season."""
    today = date.today().isoformat()
    race = (
        db.query(Race)
        .filter(Race.season == season, Race.date >= today)
        .order_by(Race.round_number)
        .first()
    )
    return race.circuit_type if race else "balanced"


def _compute_teammate_stats(d1: Driver, d2: Driver, db: Session) -> dict:
    """
    Compute 2025 head-to-head stats between two teammates.
    Returns structured comparison data for use in multiple endpoints.
    """
    race_ids = [r.id for r in db.query(Race).filter_by(season=2025).all()]

    def _stats(drv: Driver) -> dict:
        results = db.query(RaceResult).filter(
            RaceResult.driver_id == drv.id,
            RaceResult.race_id.in_(race_ids),
        ).all()
        fp_rows = db.query(FantasyPoints).filter(
            FantasyPoints.driver_id == drv.id,
            FantasyPoints.race_id.in_(race_ids),
        ).all()
        quali_pos = [r.qualifying_pos for r in results if r.qualifying_pos]
        race_pos  = [r.race_pos for r in results if r.race_pos]
        avg_fp    = sum(f.total_pts for f in fp_rows) / max(len(fp_rows), 1)
        return {
            "quali_pos": quali_pos,
            "race_pos":  race_pos,
            "avg_fp":    round(avg_fp, 1),
            "total_fp":  round(sum(f.total_pts for f in fp_rows), 1),
            "avg_quali": round(sum(quali_pos) / max(len(quali_pos), 1), 1),
            "avg_race":  round(sum(race_pos)  / max(len(race_pos),  1), 1),
        }

    s1, s2 = _stats(d1), _stats(d2)

    # Head-to-head qualifying comparison across shared races
    q1_map = {r.race_id: r.qualifying_pos for r in db.query(RaceResult).filter(
        RaceResult.driver_id == d1.id,
        RaceResult.race_id.in_(race_ids),
        RaceResult.qualifying_pos.isnot(None),
    ).all()}
    q2_map = {r.race_id: r.qualifying_pos for r in db.query(RaceResult).filter(
        RaceResult.driver_id == d2.id,
        RaceResult.race_id.in_(race_ids),
        RaceResult.qualifying_pos.isnot(None),
    ).all()}
    shared = set(q1_map) & set(q2_map)
    d1_quali_wins = sum(1 for rid in shared if q1_map[rid] < q2_map[rid])
    d2_quali_wins = len(shared) - d1_quali_wins

    def _xp_current(drv: Driver) -> float:
        fp = (db.query(FantasyPoints).filter_by(driver_id=drv.id)
              .order_by(FantasyPoints.race_id.desc()).limit(3).all())
        pts = [r.total_pts for r in reversed(fp)]
        return round(calculate_xp(pts, drv.code, "balanced"), 1)

    def _pts_per_million(drv: Driver) -> float:
        fp = (db.query(FantasyPoints).filter_by(driver_id=drv.id)
              .order_by(FantasyPoints.race_id.desc()).limit(5).all())
        avg = sum(r.total_pts for r in fp) / max(len(fp), 1)
        return round(avg / (drv.price / 1_000_000), 2) if drv.price > 0 else 0.0

    return {
        "constructor_id": d1.team_id,
        "driver_1": {
            "id": d1.id, "name": d1.name, "code": d1.code, "price": d1.price,
            "avg_fantasy_pts": s1["avg_fp"], "total_fantasy_pts": s1["total_fp"],
            "avg_qualifying_pos": s1["avg_quali"], "avg_race_pos": s1["avg_race"],
            "quali_h2h_wins": d1_quali_wins,
            "xp": _xp_current(d1), "pts_per_million": _pts_per_million(d1),
        },
        "driver_2": {
            "id": d2.id, "name": d2.name, "code": d2.code, "price": d2.price,
            "avg_fantasy_pts": s2["avg_fp"], "total_fantasy_pts": s2["total_fp"],
            "avg_qualifying_pos": s2["avg_quali"], "avg_race_pos": s2["avg_race"],
            "quali_h2h_wins": d2_quali_wins,
            "xp": _xp_current(d2), "pts_per_million": _pts_per_million(d2),
        },
        "h2h_qualifying_races": len(shared),
    }


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.get("")
async def get_drivers(db: Session = Depends(get_db)):
    """
    Return all active 2026 drivers with price, xP, value score, form status,
    circuit fit score for the next race, and differential flag.
    """
    drivers = db.query(Driver).filter(Driver.price > 0).all()
    next_circuit = _next_race_circuit_type(db)

    # First pass: compute xP for all drivers (needed for differential threshold)
    raw = []
    for d in drivers:
        fp_rows = (
            db.query(FantasyPoints)
            .filter_by(driver_id=d.id)
            .order_by(FantasyPoints.race_id.desc())
            .limit(5)
            .all()
        )
        pts_rev = list(reversed(fp_rows))           # oldest first
        last3 = [r.total_pts for r in pts_rev[-3:]]
        last5 = [r.total_pts for r in pts_rev]
        xp = calculate_xp(last3, d.code, next_circuit)
        actual_avg5 = sum(last5) / max(len(last5), 1)

        profile = (
            db.query(DriverCircuitProfile)
            .filter_by(driver_id=d.id, circuit_type=next_circuit)
            .first()
        )
        raw.append({
            "driver": d,
            "xp": xp,
            "value": xp_per_million(xp, d.price),
            "actual_avg5": actual_avg5,
            "form_status": _form_flag(actual_avg5, xp),
            "form_delta": round(actual_avg5 - xp, 1),
            "circuit_fit_avg": profile.avg_points if profile else 0.0,
            "total_pts": sum(r.total_pts for r in fp_rows),
        })

    # Differential threshold: top-30% xP AND price < $12M
    sorted_xps = sorted(r["xp"] for r in raw)
    threshold_idx = max(0, len(sorted_xps) - len(sorted_xps) // 3 - 1)
    top30_threshold = sorted_xps[threshold_idx] if sorted_xps else 0

    # Normalise circuit fit to 0–10
    max_fit = max((r["circuit_fit_avg"] for r in raw), default=1) or 1

    result = []
    for r in raw:
        d = r["driver"]
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
            "xp": r["xp"],
            "value_score": r["value"],
            "total_fantasy_pts": r["total_pts"],
            "form_status": r["form_status"],
            "form_delta": r["form_delta"],
            "circuit_fit_score": round(r["circuit_fit_avg"] / max_fit * 10, 1),
            "circuit_fit_type": next_circuit,
            "is_differential": r["xp"] >= top30_threshold and d.price < 12_000_000,
        })

    return {"success": True, "data": result}


@router.get("/circuit-fit")
async def get_circuit_fit(
    circuit_type: str = Query(..., description="street | power | balanced"),
    db: Session = Depends(get_db),
):
    """
    Return all drivers ranked by their average fantasy points on the given circuit type,
    with a normalised fit score 0–10. Only active (price > 0) 2026 drivers are included.
    """
    profiles = db.query(DriverCircuitProfile).filter_by(circuit_type=circuit_type).all()
    if not profiles:
        return {"success": True, "data": []}

    max_avg = max((p.avg_points for p in profiles), default=1) or 1
    result = []
    for p in profiles:
        drv = db.query(Driver).get(p.driver_id)
        if not drv or drv.price <= 0:
            continue
        result.append({
            "driver_id": p.driver_id,
            "driver_code": drv.code,
            "driver_name": drv.name,
            "team_name": drv.constructor.name if drv.constructor else "",
            "circuit_type": circuit_type,
            "avg_points": round(p.avg_points, 1),
            "races_counted": p.races_counted,
            "fit_score": round(p.avg_points / max_avg * 10, 1),
        })
    result.sort(key=lambda x: x["fit_score"], reverse=True)
    return {"success": True, "data": result}


@router.get("/{driver_id}/form")
async def get_driver_form(driver_id: int, db: Session = Depends(get_db)):
    """
    Form vs Luck analysis: last 5 races actual points vs projected xP at the time of
    each race. Returns per-race sparkline data plus an overall flag:
    'overperforming', 'underperforming', or 'on_form'.
    """
    driver = db.query(Driver).get(driver_id)
    if not driver:
        return {"success": False, "error": "Driver not found", "data": None}

    all_fp = (
        db.query(FantasyPoints)
        .filter_by(driver_id=driver_id)
        .order_by(FantasyPoints.race_id.asc())
        .all()
    )
    if not all_fp:
        return {"success": True, "data": {
            "driver_id": driver_id, "driver_code": driver.code,
            "driver_name": driver.name, "actual_avg": 0.0, "xp_avg": 0.0,
            "delta": 0.0, "flag": "on_form", "history": [],
        }}

    last5_fp = all_fp[-5:]
    race_ids = [fp.race_id for fp in last5_fp]
    races_map = {r.id: r for r in db.query(Race).filter(Race.id.in_(race_ids)).all()}

    history = []
    for i, fp in enumerate(last5_fp):
        race = races_map.get(fp.race_id)
        circuit_type = race.circuit_type if race else "balanced"
        global_idx = len(all_fp) - len(last5_fp) + i
        prev_pts = [all_fp[j].total_pts for j in range(max(0, global_idx - 3), global_idx)]
        xp_at_race = calculate_xp(prev_pts, driver.code, circuit_type)
        history.append({
            "race_name": race.name.replace(" Grand Prix", " GP") if race else f"R{fp.race_id}",
            "round": race.round_number if race else 0,
            "circuit_type": circuit_type,
            "actual": round(fp.total_pts, 1),
            "xp": round(xp_at_race, 1),
        })

    actual_avg = sum(h["actual"] for h in history) / max(len(history), 1)
    xp_avg     = sum(h["xp"]     for h in history) / max(len(history), 1)

    return {"success": True, "data": {
        "driver_id": driver_id,
        "driver_code": driver.code,
        "driver_name": driver.name,
        "actual_avg": round(actual_avg, 1),
        "xp_avg":     round(xp_avg, 1),
        "delta":      round(actual_avg - xp_avg, 1),
        "flag":       _form_flag(actual_avg, xp_avg),
        "history":    history,
    }}


@router.get("/{driver_id}/vs-teammate")
async def get_vs_teammate(driver_id: int, db: Session = Depends(get_db)):
    """
    Return 2025 head-to-head comparison between a driver and their current
    constructor teammate (qualifying wins, avg race position, fantasy pts).
    """
    driver = db.query(Driver).get(driver_id)
    if not driver:
        return {"success": False, "error": "Driver not found", "data": None}

    teammate = (
        db.query(Driver)
        .filter(Driver.team_id == driver.team_id,
                Driver.id != driver.id,
                Driver.price > 0)
        .first()
    )
    if not teammate:
        return {"success": True, "data": None}

    return {"success": True, "data": _compute_teammate_stats(driver, teammate, db)}


@router.get("/{driver_id}")
async def get_driver(driver_id: int, db: Session = Depends(get_db)):
    """Return a single driver by ID with recent fantasy history."""
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

    return {"success": True, "data": {
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
    }}
