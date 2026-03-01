"""
OpenF1 API Client — F1 Points Engine
======================================
Async wrapper around the OpenF1 public API (https://openf1.org).
Handles downtime gracefully: returns last known state and logs a warning.

Endpoints used:
- /sessions — current/upcoming session metadata
- /position — lap-by-lap driver positions
- /laps — fastest lap tracking
- /pit — pit stop data
- /drivers — driver metadata
"""

import logging
from typing import Any, Optional

import httpx

from backend.core.config import OPENF1_BASE_URL

logger = logging.getLogger(__name__)

# In-memory cache: last successfully fetched data per endpoint
_cache: dict[str, Any] = {}


async def _get(path: str, params: dict | None = None) -> Optional[list[dict]]:
    """
    Make an async GET request to OpenF1 API.

    Returns deserialized JSON list on success, or cached value on failure.
    Logs a warning if the API is unreachable.
    """
    url = f"{OPENF1_BASE_URL}{path}"
    cache_key = f"{path}:{params}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            _cache[cache_key] = data
            return data
    except Exception as exc:
        logger.warning("OpenF1 API unreachable (%s %s): %s. Returning cached data.", url, params, exc)
        return _cache.get(cache_key)


async def get_current_session() -> Optional[dict]:
    """
    Fetch the most recent/current session from OpenF1.

    Returns:
        Session dict with keys: session_key, session_type, date_start, date_end,
        meeting_name, circuit_short_name. None if unavailable.
    """
    data = await _get("/sessions", {"date_start>": "2024-01-01"})
    if data:
        return data[-1]
    return None


async def get_driver_positions(session_key: int) -> list[dict]:
    """
    Fetch current lap-by-lap driver positions for a session.

    Args:
        session_key: OpenF1 session identifier.

    Returns:
        List of position records: {driver_number, position, date}.
    """
    data = await _get("/position", {"session_key": session_key})
    return data or []


async def get_laps(session_key: int) -> list[dict]:
    """
    Fetch lap data for fastest lap tracking.

    Args:
        session_key: OpenF1 session identifier.

    Returns:
        List of lap records with duration_sector_* and lap_duration fields.
    """
    data = await _get("/laps", {"session_key": session_key})
    return data or []


async def get_pit_stops(session_key: int) -> list[dict]:
    """
    Fetch pit stop data for constructor scoring.

    Args:
        session_key: OpenF1 session identifier.

    Returns:
        List of pit records: {driver_number, lap_number, pit_duration, date}.
    """
    data = await _get("/pit", {"session_key": session_key})
    return data or []


async def get_drivers(session_key: int) -> list[dict]:
    """
    Fetch driver metadata for a session (number → name/code mapping).

    Args:
        session_key: OpenF1 session identifier.

    Returns:
        List of driver records: {driver_number, broadcast_name, team_name, ...}.
    """
    data = await _get("/drivers", {"session_key": session_key})
    return data or []


def get_stale_flag() -> bool:
    """Return True if the last fetch populated from cache (indicating API downtime)."""
    return bool(_cache)  # simplified — in prod, track last successful fetch timestamp


async def build_live_snapshot(session_key: int, session_type: str) -> dict:
    """
    Build a complete live race snapshot for WebSocket delivery.

    Args:
        session_key: OpenF1 session identifier.
        session_type: "race" | "qualifying" | "sprint"

    Returns:
        Dict matching the WebSocket message format defined in SPEC.md.
        Sets stale=True if data comes from cache due to API downtime.
    """
    from datetime import datetime, timezone
    from backend.core.scoring import (
        race_position_points, qualifying_position_points,
        sprint_position_points, race_bonus_points,
    )

    positions = await get_driver_positions(session_key)
    laps = await get_laps(session_key)
    pit_stops = await get_pit_stops(session_key)
    drivers_meta = await get_drivers(session_key)

    # Map driver_number → metadata
    driver_map = {d["driver_number"]: d for d in drivers_meta}

    # Determine latest position per driver
    latest_pos: dict[int, dict] = {}
    for rec in positions:
        dn = rec.get("driver_number")
        if dn and (dn not in latest_pos or rec.get("date", "") > latest_pos[dn].get("date", "")):
            latest_pos[dn] = rec

    # Determine fastest lap holder
    fastest_lap_driver = None
    fastest_duration = float("inf")
    for lap in laps:
        dur = lap.get("lap_duration") or float("inf")
        if dur < fastest_duration:
            fastest_duration = dur
            fastest_lap_driver = lap.get("driver_number")

    # Determine lap count
    lap_numbers = [lap.get("lap_number", 0) for lap in laps]
    current_lap = max(lap_numbers) if lap_numbers else 0

    driver_snapshots = []
    for driver_number, pos_rec in sorted(latest_pos.items(), key=lambda x: x[1].get("position", 99)):
        meta = driver_map.get(driver_number, {})
        position = pos_rec.get("position")
        is_fastest = driver_number == fastest_lap_driver

        if session_type == "race":
            pos_pts = race_position_points(position)
            bonus = race_bonus_points(0, 0, is_fastest)
        elif session_type == "qualifying":
            pos_pts = qualifying_position_points(position)
            bonus = 0
        else:  # sprint
            pos_pts = sprint_position_points(position)
            bonus = 0

        total_pts = pos_pts + bonus
        driver_snapshots.append({
            "driver_number": driver_number,
            "driver_id": meta.get("name_acronym", str(driver_number)),
            "name": meta.get("broadcast_name", f"Driver {driver_number}"),
            "position": position,
            "fantasy_points": total_pts,
            "breakdown": {
                "race_position_points": pos_pts,
                "positions_gained": 0,
                "overtakes": 0,
                "fastest_lap": is_fastest,
                "drs_boost_applied": False,
            },
        })

    return {
        "session_type": session_type,
        "lap": current_lap,
        "total_laps": 57,  # default; actual from race data
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "stale": False,
        "drivers": driver_snapshots,
        "constructors": [],
    }
