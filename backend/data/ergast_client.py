"""
Ergast API Client — F1 Points Engine
======================================
Async wrapper around the Ergast MRD API (http://ergast.com/mrd/).
Used for: race calendar, driver/constructor lists, historical results, standings.

Note: Ergast was officially retired in 2024. We use the community mirror at
jolpica-f1.vercel.app which provides the same JSON API format.
"""

import logging
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

# Use Jolpica F1 mirror (same API format as Ergast, actively maintained)
ERGAST_BASE = "https://ergast.com/api/f1"
JOLPICA_BASE = "https://api.jolpi.ca/ergast/f1"


async def _get(path: str, params: dict | None = None) -> Optional[dict]:
    """Make an async GET request to the Ergast-compatible API."""
    for base in (JOLPICA_BASE, ERGAST_BASE):
        url = f"{base}{path}.json"
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url, params={**(params or {}), "limit": 1000})
                resp.raise_for_status()
                return resp.json()
        except Exception as exc:
            logger.warning("Ergast API failed (%s): %s", url, exc)
    return None


async def get_race_calendar(season: int | str = "current") -> list[dict]:
    """
    Fetch the full race calendar for a season.

    Args:
        season: Year (int) or "current".

    Returns:
        List of race dicts with: raceName, Circuit, date, round, etc.
    """
    data = await _get(f"/{season}")
    if not data:
        return []
    try:
        return data["MRData"]["RaceTable"]["Races"]
    except (KeyError, TypeError):
        return []


async def get_drivers(season: int | str = "current") -> list[dict]:
    """
    Fetch the driver list for a season.

    Args:
        season: Year or "current".

    Returns:
        List of driver dicts: driverId, code, givenName, familyName, nationality.
    """
    data = await _get(f"/{season}/drivers")
    if not data:
        return []
    try:
        return data["MRData"]["DriverTable"]["Drivers"]
    except (KeyError, TypeError):
        return []


async def get_constructors(season: int | str = "current") -> list[dict]:
    """
    Fetch the constructor list for a season.

    Args:
        season: Year or "current".

    Returns:
        List of constructor dicts: constructorId, name, nationality.
    """
    data = await _get(f"/{season}/constructors")
    if not data:
        return []
    try:
        return data["MRData"]["ConstructorTable"]["Constructors"]
    except (KeyError, TypeError):
        return []


async def get_race_results(season: int | str, round_num: int | str) -> list[dict]:
    """
    Fetch race results for a specific round.

    Args:
        season: Year.
        round_num: Round number or "last".

    Returns:
        List of result dicts per driver.
    """
    data = await _get(f"/{season}/{round_num}/results")
    if not data:
        return []
    try:
        races = data["MRData"]["RaceTable"]["Races"]
        return races[0]["Results"] if races else []
    except (KeyError, TypeError, IndexError):
        return []


async def get_qualifying_results(season: int | str, round_num: int | str) -> list[dict]:
    """
    Fetch qualifying results for a specific round.

    Args:
        season: Year.
        round_num: Round number.

    Returns:
        List of qualifying result dicts.
    """
    data = await _get(f"/{season}/{round_num}/qualifying")
    if not data:
        return []
    try:
        races = data["MRData"]["RaceTable"]["Races"]
        return races[0]["QualifyingResults"] if races else []
    except (KeyError, TypeError, IndexError):
        return []


async def get_driver_standings(season: int | str = "current") -> list[dict]:
    """
    Fetch current WDC standings.

    Args:
        season: Year or "current".

    Returns:
        List of standing dicts: position, points, wins, Driver, Constructors.
    """
    data = await _get(f"/{season}/driverStandings")
    if not data:
        return []
    try:
        lists = data["MRData"]["StandingsTable"]["StandingsLists"]
        return lists[0]["DriverStandings"] if lists else []
    except (KeyError, TypeError, IndexError):
        return []


async def get_constructor_standings(season: int | str = "current") -> list[dict]:
    """
    Fetch current WCC standings.

    Args:
        season: Year or "current".

    Returns:
        List of standing dicts: position, points, wins, Constructor.
    """
    data = await _get(f"/{season}/constructorStandings")
    if not data:
        return []
    try:
        lists = data["MRData"]["StandingsTable"]["StandingsLists"]
        return lists[0]["ConstructorStandings"] if lists else []
    except (KeyError, TypeError, IndexError):
        return []


async def get_season_results(season: int | str) -> list[dict]:
    """
    Fetch all race results for an entire season (for seeding).

    Args:
        season: Year.

    Returns:
        List of race result blocks, each containing Results list.
    """
    data = await _get(f"/{season}/results")
    if not data:
        return []
    try:
        return data["MRData"]["RaceTable"]["Races"]
    except (KeyError, TypeError):
        return []


async def get_season_qualifying(season: int | str) -> list[dict]:
    """
    Fetch all qualifying results for an entire season.

    Args:
        season: Year.

    Returns:
        List of qualifying result blocks.
    """
    data = await _get(f"/{season}/qualifying")
    if not data:
        return []
    try:
        return data["MRData"]["RaceTable"]["Races"]
    except (KeyError, TypeError):
        return []
