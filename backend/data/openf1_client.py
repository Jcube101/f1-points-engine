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
- /starting_grid — grid positions for positions-gained calculation
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from backend.core.config import OPENF1_BASE_URL

logger = logging.getLogger(__name__)

# In-memory cache: last successfully fetched data per endpoint
_cache: dict[str, Any] = {}

# Tracks whether any fetch since the last reset was served from cache (API downtime).
# Reset at the start of build_live_snapshot and set True whenever _get falls back to cache.
_served_from_cache: bool = False


def _reset_cache_tracking() -> None:
    """Reset the served-from-cache flag before building a fresh snapshot."""
    global _served_from_cache
    _served_from_cache = False


def _any_served_from_cache() -> bool:
    """Return True if any fetch since the last reset fell back to cached data."""
    return _served_from_cache


async def _get(path: str, params: dict | None = None) -> Optional[list[dict]]:
    """
    Make an async GET request to OpenF1 API.

    Returns deserialized JSON list on success, or cached value on failure.
    Logs a warning if the API is unreachable and marks the snapshot as stale.
    """
    global _served_from_cache
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
        _served_from_cache = True
        return _cache.get(cache_key)


def _parse_iso(value: Optional[str]) -> Optional[datetime]:
    """Parse an OpenF1 ISO-8601 timestamp into an aware UTC datetime, or None."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


async def get_current_session() -> Optional[dict]:
    """
    Fetch the session that is currently live from OpenF1, if any.

    OpenF1's /sessions endpoint returns the full season schedule (past, live, and
    future), not just "the current one" — so the current session is whichever
    session's [date_start, date_end] window contains right now, not simply the
    last item in the response.

    Returns:
        Session dict with keys: session_key, session_type, date_start, date_end,
        meeting_name, circuit_short_name. None if no session is live right now.
    """
    data = await _get("/sessions", {"date_start>": "2024-01-01"})
    if not data:
        return None

    now = datetime.now(timezone.utc)
    for session in data:
        start = _parse_iso(session.get("date_start"))
        end = _parse_iso(session.get("date_end"))
        if start and end and start <= now <= end:
            return session
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


async def get_starting_grid(session_key: int) -> list[dict]:
    """
    Fetch the starting grid for a session (for positions-gained calculation).

    Args:
        session_key: OpenF1 session identifier.

    Returns:
        List of grid records: {driver_number, position, ...}. Empty list on failure.
    """
    data = await _get("/starting_grid", {"session_key": session_key})
    return data or []


async def build_live_snapshot(
    session_key: int, session_type: str, total_laps: int | None = None
) -> dict:
    """
    Build a complete live race snapshot for WebSocket delivery.

    Args:
        session_key: OpenF1 session identifier.
        session_type: "race" | "qualifying" | "sprint"
        total_laps: Scheduled total laps for the session. If None, falls back to the
            max observed lap_number (else 0).

    Returns:
        Dict matching the WebSocket message format defined in SPEC.md.
        Sets stale=True if any underlying fetch came from cache due to API downtime.
    """
    from backend.core.scoring import (
        race_position_points, qualifying_position_points,
        sprint_position_points, race_bonus_points, sprint_bonus_points,
    )

    # Reset stale tracking; any cache fallback during the fetches below flips it.
    _reset_cache_tracking()

    positions = await get_driver_positions(session_key)
    laps = await get_laps(session_key)
    pit_stops = await get_pit_stops(session_key)  # noqa: F841 — reserved for constructor pit bonuses
    drivers_meta = await get_drivers(session_key)
    grid = await get_starting_grid(session_key)

    # Map driver_number → metadata
    driver_map = {d["driver_number"]: d for d in drivers_meta}

    # Determine latest position per driver
    latest_pos: dict[int, dict] = {}
    for rec in positions:
        dn = rec.get("driver_number")
        if dn and (dn not in latest_pos or rec.get("date", "") > latest_pos[dn].get("date", "")):
            latest_pos[dn] = rec

    # Determine starting grid position per driver.
    # Prefer the /starting_grid endpoint; fall back to the earliest /position record.
    grid_pos: dict[int, int] = {}
    for rec in grid:
        dn = rec.get("driver_number")
        gp = rec.get("position")
        if dn is not None and gp is not None:
            grid_pos[dn] = gp
    if not grid_pos:
        earliest: dict[int, dict] = {}
        for rec in positions:
            dn = rec.get("driver_number")
            if dn and (dn not in earliest or rec.get("date", "") < earliest[dn].get("date", "")):
                earliest[dn] = rec
        for dn, rec in earliest.items():
            gp = rec.get("position")
            if gp is not None:
                grid_pos[dn] = gp

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

    # Resolve total laps: explicit arg → max observed lap → 0
    if total_laps is None:
        total_laps = max(lap_numbers) if lap_numbers else 0

    driver_snapshots = []
    for driver_number, pos_rec in sorted(latest_pos.items(), key=lambda x: x[1].get("position", 99)):
        meta = driver_map.get(driver_number, {})
        position = pos_rec.get("position")
        is_fastest = driver_number == fastest_lap_driver

        # positions_gained = grid - current (positive = gained). overtakes proxied as
        # net positions gained (OpenF1 has no overtake feed). Driver of the Day is not
        # exposed by OpenF1, so it stays False.
        start = grid_pos.get(driver_number)
        if start is not None and position is not None:
            positions_gained = start - position
        else:
            positions_gained = 0
        overtakes = max(0, positions_gained)
        driver_of_day = False  # not available from OpenF1

        if session_type == "race":
            pos_pts = race_position_points(position)
            bonus = race_bonus_points(positions_gained, overtakes, is_fastest, driver_of_day)
        elif session_type == "qualifying":
            pos_pts = qualifying_position_points(position)
            bonus = 0  # qualifying has no live position/overtake bonus
        else:  # sprint
            pos_pts = sprint_position_points(position)
            bonus = sprint_bonus_points(positions_gained, overtakes)

        total_pts = pos_pts + bonus
        driver_snapshots.append({
            "driver_number": driver_number,
            "driver_id": meta.get("name_acronym", str(driver_number)),
            "name": meta.get("broadcast_name", f"Driver {driver_number}"),
            "position": position,
            "team_name": meta.get("team_name"),
            "fantasy_points": total_pts,
            "breakdown": {
                "race_position_points": pos_pts,
                "positions_gained": positions_gained,
                "overtakes": overtakes,
                "fastest_lap": is_fastest,
                "drs_boost_applied": False,
            },
        })

    # Group drivers by constructor (team_name) and sum their fantasy points.
    constructor_map: dict[str, dict] = {}
    for ds in driver_snapshots:
        team = ds.get("team_name")
        if not team:
            continue
        entry = constructor_map.setdefault(
            team, {"constructor": team, "fantasy_points": 0, "drivers": []}
        )
        entry["fantasy_points"] += ds["fantasy_points"]
        entry["drivers"].append(ds["driver_id"])
    constructors = sorted(
        constructor_map.values(), key=lambda c: c["fantasy_points"], reverse=True
    )

    return {
        "session_type": session_type,
        "lap": current_lap,
        "total_laps": total_laps,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "stale": _any_served_from_cache(),
        "drivers": driver_snapshots,
        "constructors": constructors,
    }
