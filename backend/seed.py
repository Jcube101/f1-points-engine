"""
Seed Script — F1 Points Engine
================================
Run once to populate the database with:
1. 2025 race calendar (from Ergast/Jolpica API)
2. Driver + constructor list with realistic fantasy prices
3. 2025 historical race results → computed fantasy points
4. Initial xP scores for all drivers

Run with:
    cd backend && python seed.py
    OR from project root:
    python backend/seed.py
"""

import asyncio
import logging
import os
import sys

# Ensure the project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from backend.db.database import engine, init_db, SessionLocal
from backend.data.models import Driver, Constructor, Race, RaceResult, FantasyPoints
from backend.data.ergast_client import (
    get_race_calendar, get_drivers, get_constructors,
    get_season_results, get_season_qualifying,
)
from backend.core.scoring import (
    qualifying_position_points, qualifying_bonus_points,
    race_position_points, race_bonus_points,
)
from backend.core.expected_points import calculate_xp

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# ─── Driver pricing (realistic 2025 fantasy prices) ───────────────────────────
DRIVER_PRICES: dict[str, float] = {
    "max_verstappen": 30_000_000,
    "lando_norris": 28_000_000,
    "charles_leclerc": 26_000_000,
    "oscar_piastri": 25_000_000,
    "carlos_sainz": 24_000_000,
    "george_russell": 24_000_000,
    "lewis_hamilton": 23_000_000,
    "kimi_antonelli": 18_000_000,
    "fernando_alonso": 16_000_000,
    "lance_stroll": 10_000_000,
    "pierre_gasly": 13_000_000,
    "jack_doohan": 10_000_000,
    "esteban_ocon": 12_000_000,
    "oliver_bearman": 10_000_000,
    "yuki_tsunoda": 13_000_000,
    "liam_lawson": 12_000_000,
    "alexander_albon": 11_000_000,
    "franco_colapinto": 9_000_000,
    "nico_hulkenberg": 12_000_000,
    "gabriel_bortoleto": 9_000_000,
    "isack_hadjar": 10_000_000,
    "default": 10_000_000,
}

CONSTRUCTOR_PRICES: dict[str, float] = {
    "red_bull": 28_000_000,
    "mclaren": 28_000_000,
    "ferrari": 26_000_000,
    "mercedes": 24_000_000,
    "aston_martin": 16_000_000,
    "alpine": 12_000_000,
    "haas": 10_000_000,
    "rb": 12_000_000,
    "williams": 10_000_000,
    "sauber": 9_000_000,
    "default": 10_000_000,
}

CONSTRUCTOR_COLORS: dict[str, str] = {
    "red_bull": "#3671C6",
    "mclaren": "#FF8000",
    "ferrari": "#E8002D",
    "mercedes": "#27F4D2",
    "aston_martin": "#229971",
    "alpine": "#FF87BC",
    "haas": "#B6BABD",
    "rb": "#6692FF",
    "williams": "#64C4FF",
    "sauber": "#52E252",
}

CIRCUIT_TYPES: dict[str, str] = {
    "Australian Grand Prix": "balanced",
    "Chinese Grand Prix": "balanced",
    "Japanese Grand Prix": "balanced",
    "Bahrain Grand Prix": "balanced",
    "Saudi Arabian Grand Prix": "street",
    "Miami Grand Prix": "street",
    "Emilia Romagna Grand Prix": "balanced",
    "Monaco Grand Prix": "street",
    "Spanish Grand Prix": "balanced",
    "Canadian Grand Prix": "street",
    "Austrian Grand Prix": "balanced",
    "British Grand Prix": "balanced",
    "Hungarian Grand Prix": "balanced",
    "Belgian Grand Prix": "power",
    "Dutch Grand Prix": "balanced",
    "Italian Grand Prix": "power",
    "Azerbaijan Grand Prix": "street",
    "Singapore Grand Prix": "street",
    "United States Grand Prix": "balanced",
    "Mexico City Grand Prix": "power",
    "São Paulo Grand Prix": "balanced",
    "Las Vegas Grand Prix": "street",
    "Qatar Grand Prix": "balanced",
    "Abu Dhabi Grand Prix": "balanced",
}

SPRINT_RACES = {
    "Chinese Grand Prix",
    "Miami Grand Prix",
    "Austrian Grand Prix",
    "United States Grand Prix",
    "São Paulo Grand Prix",
    "Qatar Grand Prix",
}

# Fallback static data if API unavailable
FALLBACK_DRIVERS = [
    {"driverId": "max_verstappen", "code": "VER", "givenName": "Max", "familyName": "Verstappen", "nationality": "Dutch", "constructorId": "red_bull"},
    {"driverId": "lando_norris", "code": "NOR", "givenName": "Lando", "familyName": "Norris", "nationality": "British", "constructorId": "mclaren"},
    {"driverId": "charles_leclerc", "code": "LEC", "givenName": "Charles", "familyName": "Leclerc", "nationality": "Monegasque", "constructorId": "ferrari"},
    {"driverId": "oscar_piastri", "code": "PIA", "givenName": "Oscar", "familyName": "Piastri", "nationality": "Australian", "constructorId": "mclaren"},
    {"driverId": "carlos_sainz", "code": "SAI", "givenName": "Carlos", "familyName": "Sainz", "nationality": "Spanish", "constructorId": "williams"},
    {"driverId": "george_russell", "code": "RUS", "givenName": "George", "familyName": "Russell", "nationality": "British", "constructorId": "mercedes"},
    {"driverId": "lewis_hamilton", "code": "HAM", "givenName": "Lewis", "familyName": "Hamilton", "nationality": "British", "constructorId": "ferrari"},
    {"driverId": "kimi_antonelli", "code": "ANT", "givenName": "Kimi", "familyName": "Antonelli", "nationality": "Italian", "constructorId": "mercedes"},
    {"driverId": "fernando_alonso", "code": "ALO", "givenName": "Fernando", "familyName": "Alonso", "nationality": "Spanish", "constructorId": "aston_martin"},
    {"driverId": "lance_stroll", "code": "STR", "givenName": "Lance", "familyName": "Stroll", "nationality": "Canadian", "constructorId": "aston_martin"},
    {"driverId": "pierre_gasly", "code": "GAS", "givenName": "Pierre", "familyName": "Gasly", "nationality": "French", "constructorId": "alpine"},
    {"driverId": "jack_doohan", "code": "DOO", "givenName": "Jack", "familyName": "Doohan", "nationality": "Australian", "constructorId": "alpine"},
    {"driverId": "nico_hulkenberg", "code": "HUL", "givenName": "Nico", "familyName": "Hulkenberg", "nationality": "German", "constructorId": "sauber"},
    {"driverId": "gabriel_bortoleto", "code": "BOR", "givenName": "Gabriel", "familyName": "Bortoleto", "nationality": "Brazilian", "constructorId": "sauber"},
    {"driverId": "yuki_tsunoda", "code": "TSU", "givenName": "Yuki", "familyName": "Tsunoda", "nationality": "Japanese", "constructorId": "rb"},
    {"driverId": "liam_lawson", "code": "LAW", "givenName": "Liam", "familyName": "Lawson", "nationality": "New Zealander", "constructorId": "rb"},
    {"driverId": "alexander_albon", "code": "ALB", "givenName": "Alexander", "familyName": "Albon", "nationality": "Thai", "constructorId": "williams"},
    {"driverId": "franco_colapinto", "code": "COL", "givenName": "Franco", "familyName": "Colapinto", "nationality": "Argentine", "constructorId": "alpine"},
    {"driverId": "oliver_bearman", "code": "BEA", "givenName": "Oliver", "familyName": "Bearman", "nationality": "British", "constructorId": "haas"},
    {"driverId": "isack_hadjar", "code": "HAD", "givenName": "Isack", "familyName": "Hadjar", "nationality": "French", "constructorId": "rb"},
]

FALLBACK_CONSTRUCTORS = [
    {"constructorId": "red_bull", "name": "Red Bull Racing", "nationality": "Austrian"},
    {"constructorId": "mclaren", "name": "McLaren", "nationality": "British"},
    {"constructorId": "ferrari", "name": "Ferrari", "nationality": "Italian"},
    {"constructorId": "mercedes", "name": "Mercedes", "nationality": "German"},
    {"constructorId": "aston_martin", "name": "Aston Martin", "nationality": "British"},
    {"constructorId": "alpine", "name": "Alpine", "nationality": "French"},
    {"constructorId": "haas", "name": "Haas F1 Team", "nationality": "American"},
    {"constructorId": "rb", "name": "RB", "nationality": "Italian"},
    {"constructorId": "williams", "name": "Williams", "nationality": "British"},
    {"constructorId": "sauber", "name": "Sauber", "nationality": "Swiss"},
]

FALLBACK_CALENDAR = [
    {"round": "1", "raceName": "Australian Grand Prix", "Circuit": {"circuitName": "Albert Park"}, "date": "2025-03-16", "season": "2025"},
    {"round": "2", "raceName": "Chinese Grand Prix", "Circuit": {"circuitName": "Shanghai"}, "date": "2025-03-23", "season": "2025"},
    {"round": "3", "raceName": "Japanese Grand Prix", "Circuit": {"circuitName": "Suzuka"}, "date": "2025-04-06", "season": "2025"},
    {"round": "4", "raceName": "Bahrain Grand Prix", "Circuit": {"circuitName": "Bahrain"}, "date": "2025-04-13", "season": "2025"},
    {"round": "5", "raceName": "Saudi Arabian Grand Prix", "Circuit": {"circuitName": "Jeddah"}, "date": "2025-04-20", "season": "2025"},
    {"round": "6", "raceName": "Miami Grand Prix", "Circuit": {"circuitName": "Miami"}, "date": "2025-05-04", "season": "2025"},
    {"round": "7", "raceName": "Emilia Romagna Grand Prix", "Circuit": {"circuitName": "Imola"}, "date": "2025-05-18", "season": "2025"},
    {"round": "8", "raceName": "Monaco Grand Prix", "Circuit": {"circuitName": "Monaco"}, "date": "2025-05-25", "season": "2025"},
    {"round": "9", "raceName": "Spanish Grand Prix", "Circuit": {"circuitName": "Barcelona"}, "date": "2025-06-01", "season": "2025"},
    {"round": "10", "raceName": "Canadian Grand Prix", "Circuit": {"circuitName": "Montreal"}, "date": "2025-06-15", "season": "2025"},
    {"round": "11", "raceName": "Austrian Grand Prix", "Circuit": {"circuitName": "Red Bull Ring"}, "date": "2025-06-29", "season": "2025"},
    {"round": "12", "raceName": "British Grand Prix", "Circuit": {"circuitName": "Silverstone"}, "date": "2025-07-06", "season": "2025"},
    {"round": "13", "raceName": "Hungarian Grand Prix", "Circuit": {"circuitName": "Hungaroring"}, "date": "2025-07-20", "season": "2025"},
    {"round": "14", "raceName": "Belgian Grand Prix", "Circuit": {"circuitName": "Spa"}, "date": "2025-07-27", "season": "2025"},
    {"round": "15", "raceName": "Dutch Grand Prix", "Circuit": {"circuitName": "Zandvoort"}, "date": "2025-08-31", "season": "2025"},
    {"round": "16", "raceName": "Italian Grand Prix", "Circuit": {"circuitName": "Monza"}, "date": "2025-09-07", "season": "2025"},
    {"round": "17", "raceName": "Azerbaijan Grand Prix", "Circuit": {"circuitName": "Baku"}, "date": "2025-09-21", "season": "2025"},
    {"round": "18", "raceName": "Singapore Grand Prix", "Circuit": {"circuitName": "Marina Bay"}, "date": "2025-10-05", "season": "2025"},
    {"round": "19", "raceName": "United States Grand Prix", "Circuit": {"circuitName": "Austin"}, "date": "2025-10-19", "season": "2025"},
    {"round": "20", "raceName": "Mexico City Grand Prix", "Circuit": {"circuitName": "Mexico City"}, "date": "2025-10-26", "season": "2025"},
    {"round": "21", "raceName": "São Paulo Grand Prix", "Circuit": {"circuitName": "Sao Paulo"}, "date": "2025-11-09", "season": "2025"},
    {"round": "22", "raceName": "Las Vegas Grand Prix", "Circuit": {"circuitName": "Las Vegas"}, "date": "2025-11-22", "season": "2025"},
    {"round": "23", "raceName": "Qatar Grand Prix", "Circuit": {"circuitName": "Losail"}, "date": "2025-11-30", "season": "2025"},
    {"round": "24", "raceName": "Abu Dhabi Grand Prix", "Circuit": {"circuitName": "Yas Marina"}, "date": "2025-12-07", "season": "2025"},
]

# Realistic simulated race results for 2025 season (first 5 races as baseline)
SIMULATED_RESULTS = [
    # Race 1 - Australia: VER wins
    {"race_round": 1, "driver_id_code": "VER", "qualifying_pos": 1, "race_pos": 1, "dnf": False, "fastest_lap": False, "overtakes": 0, "positions_gained_race": 0},
    {"race_round": 1, "driver_id_code": "NOR", "qualifying_pos": 2, "race_pos": 2, "dnf": False, "fastest_lap": True, "overtakes": 0, "positions_gained_race": 0},
    {"race_round": 1, "driver_id_code": "LEC", "qualifying_pos": 3, "race_pos": 3, "dnf": False, "fastest_lap": False, "overtakes": 0, "positions_gained_race": 0},
    {"race_round": 1, "driver_id_code": "PIA", "qualifying_pos": 4, "race_pos": 4, "dnf": False, "fastest_lap": False, "overtakes": 0, "positions_gained_race": 0},
    {"race_round": 1, "driver_id_code": "RUS", "qualifying_pos": 6, "race_pos": 5, "dnf": False, "fastest_lap": False, "overtakes": 1, "positions_gained_race": 1},
    {"race_round": 1, "driver_id_code": "HAM", "qualifying_pos": 5, "race_pos": 6, "dnf": False, "fastest_lap": False, "overtakes": 0, "positions_gained_race": -1},
    {"race_round": 1, "driver_id_code": "SAI", "qualifying_pos": 7, "race_pos": 7, "dnf": False, "fastest_lap": False, "overtakes": 0, "positions_gained_race": 0},
    {"race_round": 1, "driver_id_code": "ANT", "qualifying_pos": 9, "race_pos": 8, "dnf": False, "fastest_lap": False, "overtakes": 1, "positions_gained_race": 1},
    {"race_round": 1, "driver_id_code": "ALO", "qualifying_pos": 8, "race_pos": 9, "dnf": False, "fastest_lap": False, "overtakes": 0, "positions_gained_race": -1},
    {"race_round": 1, "driver_id_code": "TSU", "qualifying_pos": 10, "race_pos": 10, "dnf": False, "fastest_lap": False, "overtakes": 0, "positions_gained_race": 0},
    {"race_round": 1, "driver_id_code": "HUL", "qualifying_pos": 11, "race_pos": 11, "dnf": False, "fastest_lap": False, "overtakes": 0, "positions_gained_race": 0},
    {"race_round": 1, "driver_id_code": "ALB", "qualifying_pos": 12, "race_pos": 12, "dnf": False, "fastest_lap": False, "overtakes": 0, "positions_gained_race": 0},
    {"race_round": 1, "driver_id_code": "GAS", "qualifying_pos": 13, "race_pos": 13, "dnf": False, "fastest_lap": False, "overtakes": 0, "positions_gained_race": 0},
    {"race_round": 1, "driver_id_code": "STR", "qualifying_pos": 14, "race_pos": 14, "dnf": False, "fastest_lap": False, "overtakes": 0, "positions_gained_race": 0},
    {"race_round": 1, "driver_id_code": "BEA", "qualifying_pos": 16, "race_pos": 15, "dnf": False, "fastest_lap": False, "overtakes": 1, "positions_gained_race": 1},
    {"race_round": 1, "driver_id_code": "DOO", "qualifying_pos": 15, "race_pos": 16, "dnf": False, "fastest_lap": False, "overtakes": 0, "positions_gained_race": -1},
    {"race_round": 1, "driver_id_code": "LAW", "qualifying_pos": 17, "race_pos": 17, "dnf": False, "fastest_lap": False, "overtakes": 0, "positions_gained_race": 0},
    {"race_round": 1, "driver_id_code": "BOR", "qualifying_pos": 18, "race_pos": 18, "dnf": False, "fastest_lap": False, "overtakes": 0, "positions_gained_race": 0},
    {"race_round": 1, "driver_id_code": "HAD", "qualifying_pos": 19, "race_pos": 19, "dnf": False, "fastest_lap": False, "overtakes": 0, "positions_gained_race": 0},
    {"race_round": 1, "driver_id_code": "COL", "qualifying_pos": 20, "race_pos": None, "dnf": True, "fastest_lap": False, "overtakes": 0, "positions_gained_race": 0},
    # Race 2 - China: NOR wins, sprint weekend
    {"race_round": 2, "driver_id_code": "NOR", "qualifying_pos": 1, "race_pos": 1, "dnf": False, "fastest_lap": True, "overtakes": 0, "positions_gained_race": 0},
    {"race_round": 2, "driver_id_code": "VER", "qualifying_pos": 3, "race_pos": 2, "dnf": False, "fastest_lap": False, "overtakes": 1, "positions_gained_race": 1},
    {"race_round": 2, "driver_id_code": "PIA", "qualifying_pos": 2, "race_pos": 3, "dnf": False, "fastest_lap": False, "overtakes": 0, "positions_gained_race": -1},
    {"race_round": 2, "driver_id_code": "LEC", "qualifying_pos": 4, "race_pos": 4, "dnf": False, "fastest_lap": False, "overtakes": 0, "positions_gained_race": 0},
    {"race_round": 2, "driver_id_code": "RUS", "qualifying_pos": 5, "race_pos": 5, "dnf": False, "fastest_lap": False, "overtakes": 0, "positions_gained_race": 0},
    {"race_round": 2, "driver_id_code": "HAM", "qualifying_pos": 6, "race_pos": 6, "dnf": False, "fastest_lap": False, "overtakes": 0, "positions_gained_race": 0},
    {"race_round": 2, "driver_id_code": "SAI", "qualifying_pos": 8, "race_pos": 7, "dnf": False, "fastest_lap": False, "overtakes": 1, "positions_gained_race": 1},
    {"race_round": 2, "driver_id_code": "ANT", "qualifying_pos": 7, "race_pos": 8, "dnf": False, "fastest_lap": False, "overtakes": 0, "positions_gained_race": -1},
    {"race_round": 2, "driver_id_code": "ALO", "qualifying_pos": 9, "race_pos": 9, "dnf": False, "fastest_lap": False, "overtakes": 0, "positions_gained_race": 0},
    {"race_round": 2, "driver_id_code": "TSU", "qualifying_pos": 10, "race_pos": 10, "dnf": False, "fastest_lap": False, "overtakes": 0, "positions_gained_race": 0},
    {"race_round": 2, "driver_id_code": "HUL", "qualifying_pos": 11, "race_pos": 11, "dnf": False, "fastest_lap": False, "overtakes": 0, "positions_gained_race": 0},
    {"race_round": 2, "driver_id_code": "ALB", "qualifying_pos": 12, "race_pos": 12, "dnf": False, "fastest_lap": False, "overtakes": 0, "positions_gained_race": 0},
    {"race_round": 2, "driver_id_code": "GAS", "qualifying_pos": 13, "race_pos": 13, "dnf": False, "fastest_lap": False, "overtakes": 0, "positions_gained_race": 0},
    {"race_round": 2, "driver_id_code": "STR", "qualifying_pos": 14, "race_pos": 14, "dnf": False, "fastest_lap": False, "overtakes": 0, "positions_gained_race": 0},
    {"race_round": 2, "driver_id_code": "BEA", "qualifying_pos": 15, "race_pos": 15, "dnf": False, "fastest_lap": False, "overtakes": 0, "positions_gained_race": 0},
    {"race_round": 2, "driver_id_code": "DOO", "qualifying_pos": 16, "race_pos": 16, "dnf": False, "fastest_lap": False, "overtakes": 0, "positions_gained_race": 0},
    {"race_round": 2, "driver_id_code": "LAW", "qualifying_pos": 17, "race_pos": 17, "dnf": False, "fastest_lap": False, "overtakes": 0, "positions_gained_race": 0},
    {"race_round": 2, "driver_id_code": "BOR", "qualifying_pos": 18, "race_pos": 18, "dnf": False, "fastest_lap": False, "overtakes": 0, "positions_gained_race": 0},
    {"race_round": 2, "driver_id_code": "HAD", "qualifying_pos": 20, "race_pos": 19, "dnf": False, "fastest_lap": False, "overtakes": 1, "positions_gained_race": 1},
    {"race_round": 2, "driver_id_code": "COL", "qualifying_pos": 19, "race_pos": 20, "dnf": False, "fastest_lap": False, "overtakes": 0, "positions_gained_race": -1},
    # Race 3 - Japan: LEC wins
    {"race_round": 3, "driver_id_code": "LEC", "qualifying_pos": 1, "race_pos": 1, "dnf": False, "fastest_lap": False, "overtakes": 0, "positions_gained_race": 0},
    {"race_round": 3, "driver_id_code": "VER", "qualifying_pos": 2, "race_pos": 2, "dnf": False, "fastest_lap": True, "overtakes": 0, "positions_gained_race": 0},
    {"race_round": 3, "driver_id_code": "NOR", "qualifying_pos": 3, "race_pos": 3, "dnf": False, "fastest_lap": False, "overtakes": 0, "positions_gained_race": 0},
    {"race_round": 3, "driver_id_code": "RUS", "qualifying_pos": 5, "race_pos": 4, "dnf": False, "fastest_lap": False, "overtakes": 1, "positions_gained_race": 1},
    {"race_round": 3, "driver_id_code": "PIA", "qualifying_pos": 4, "race_pos": 5, "dnf": False, "fastest_lap": False, "overtakes": 0, "positions_gained_race": -1},
    {"race_round": 3, "driver_id_code": "HAM", "qualifying_pos": 6, "race_pos": 6, "dnf": False, "fastest_lap": False, "overtakes": 0, "positions_gained_race": 0},
    {"race_round": 3, "driver_id_code": "SAI", "qualifying_pos": 7, "race_pos": 7, "dnf": False, "fastest_lap": False, "overtakes": 0, "positions_gained_race": 0},
    {"race_round": 3, "driver_id_code": "ANT", "qualifying_pos": 8, "race_pos": 8, "dnf": False, "fastest_lap": False, "overtakes": 0, "positions_gained_race": 0},
    {"race_round": 3, "driver_id_code": "ALO", "qualifying_pos": 9, "race_pos": 9, "dnf": False, "fastest_lap": False, "overtakes": 0, "positions_gained_race": 0},
    {"race_round": 3, "driver_id_code": "TSU", "qualifying_pos": 10, "race_pos": 10, "dnf": False, "fastest_lap": False, "overtakes": 0, "positions_gained_race": 0},
    {"race_round": 3, "driver_id_code": "HUL", "qualifying_pos": 11, "race_pos": 11, "dnf": False, "fastest_lap": False, "overtakes": 0, "positions_gained_race": 0},
    {"race_round": 3, "driver_id_code": "ALB", "qualifying_pos": 13, "race_pos": 12, "dnf": False, "fastest_lap": False, "overtakes": 1, "positions_gained_race": 1},
    {"race_round": 3, "driver_id_code": "GAS", "qualifying_pos": 12, "race_pos": 13, "dnf": False, "fastest_lap": False, "overtakes": 0, "positions_gained_race": -1},
    {"race_round": 3, "driver_id_code": "STR", "qualifying_pos": 14, "race_pos": 14, "dnf": False, "fastest_lap": False, "overtakes": 0, "positions_gained_race": 0},
    {"race_round": 3, "driver_id_code": "BEA", "qualifying_pos": 15, "race_pos": 15, "dnf": False, "fastest_lap": False, "overtakes": 0, "positions_gained_race": 0},
    {"race_round": 3, "driver_id_code": "DOO", "qualifying_pos": 16, "race_pos": 16, "dnf": False, "fastest_lap": False, "overtakes": 0, "positions_gained_race": 0},
    {"race_round": 3, "driver_id_code": "LAW", "qualifying_pos": 17, "race_pos": 17, "dnf": False, "fastest_lap": False, "overtakes": 0, "positions_gained_race": 0},
    {"race_round": 3, "driver_id_code": "BOR", "qualifying_pos": 18, "race_pos": 18, "dnf": False, "fastest_lap": False, "overtakes": 0, "positions_gained_race": 0},
    {"race_round": 3, "driver_id_code": "HAD", "qualifying_pos": 19, "race_pos": 19, "dnf": False, "fastest_lap": False, "overtakes": 0, "positions_gained_race": 0},
    {"race_round": 3, "driver_id_code": "COL", "qualifying_pos": 20, "race_pos": 20, "dnf": False, "fastest_lap": False, "overtakes": 0, "positions_gained_race": 0},
]


async def seed_constructors(db: Session) -> dict[str, int]:
    """Seed constructors. Returns constructorId → DB id mapping."""
    constructors_data = await get_constructors("2025")
    if not constructors_data:
        logger.warning("Ergast API unavailable, using fallback constructor data")
        constructors_data = FALLBACK_CONSTRUCTORS

    code_map: dict[str, int] = {}
    for c in constructors_data:
        cid = c.get("constructorId", "")
        name = c.get("name", cid)
        code = cid.upper()[:10]
        price = CONSTRUCTOR_PRICES.get(cid, CONSTRUCTOR_PRICES["default"])
        color = CONSTRUCTOR_COLORS.get(cid, "#888888")

        existing = db.query(Constructor).filter_by(code=code).first()
        if not existing:
            constructor = Constructor(name=name, code=code, price=price, color_hex=color)
            db.add(constructor)
            db.flush()
            code_map[cid] = constructor.id
            logger.info("  Constructor: %s ($%.0fM)", name, price / 1e6)
        else:
            code_map[cid] = existing.id

    db.commit()
    return code_map


async def seed_drivers(db: Session, constructor_id_map: dict[str, int]) -> dict[str, int]:
    """Seed drivers. Returns driver code → DB id mapping."""
    drivers_data = await get_drivers("2025")
    if not drivers_data:
        logger.warning("Ergast API unavailable, using fallback driver data")
        drivers_data = FALLBACK_DRIVERS

    code_map: dict[str, int] = {}
    for d in drivers_data:
        driver_id = d.get("driverId", "")
        code = d.get("code", driver_id[:3].upper())
        name = f"{d.get('givenName', '')} {d.get('familyName', '')}".strip()
        nationality = d.get("nationality", "")
        price = DRIVER_PRICES.get(driver_id, DRIVER_PRICES["default"])

        # Find constructor
        constructor_id_str = d.get("constructorId", "")
        team_id = constructor_id_map.get(constructor_id_str)
        if not team_id:
            # Try partial match
            for key, val in constructor_id_map.items():
                if key in constructor_id_str or constructor_id_str in key:
                    team_id = val
                    break
        if not team_id and constructor_id_map:
            team_id = list(constructor_id_map.values())[0]

        existing = db.query(Driver).filter_by(code=code).first()
        if not existing:
            driver = Driver(
                name=name, code=code, team_id=team_id,
                price=price, nationality=nationality,
            )
            db.add(driver)
            db.flush()
            code_map[code] = driver.id
            logger.info("  Driver: %s [%s] ($%.0fM)", name, code, price / 1e6)
        else:
            code_map[code] = existing.id

    db.commit()
    return code_map


async def seed_races(db: Session) -> dict[int, int]:
    """Seed race calendar. Returns round_number → DB id mapping."""
    calendar = await get_race_calendar("2025")
    if not calendar:
        logger.warning("Ergast API unavailable, using fallback calendar")
        calendar = FALLBACK_CALENDAR

    round_map: dict[int, int] = {}
    for race in calendar:
        round_num = int(race.get("round", 0))
        name = race.get("raceName", "")
        circuit_info = race.get("Circuit", {})
        circuit = circuit_info.get("circuitName", "")
        country = circuit_info.get("Location", {}).get("country", "") or race.get("country", "")
        date = race.get("date", "2025-01-01")
        season = int(race.get("season", 2025))
        circuit_type = CIRCUIT_TYPES.get(name, "balanced")
        session_type = "sprint_race" if name in SPRINT_RACES else "race"

        existing = db.query(Race).filter_by(round_number=round_num, season=season).first()
        if not existing:
            r = Race(
                name=name, circuit=circuit, country=country, date=date,
                session_type=session_type, round_number=round_num, season=season,
                circuit_type=circuit_type,
            )
            db.add(r)
            db.flush()
            round_map[round_num] = r.id
            logger.info("  Race %d: %s (%s)", round_num, name, circuit_type)
        else:
            round_map[round_num] = existing.id

    db.commit()
    return round_map


def seed_results(db: Session, race_round_map: dict, driver_code_map: dict, constructor_id_map: dict):
    """Seed race results and compute fantasy points from simulated data."""
    for res in SIMULATED_RESULTS:
        round_num = res["race_round"]
        race_id = race_round_map.get(round_num)
        driver_code = res["driver_id_code"]
        driver_id = driver_code_map.get(driver_code)

        if not race_id or not driver_id:
            continue

        driver = db.query(Driver).get(driver_id)
        constructor_id = driver.team_id if driver else None
        if not constructor_id:
            continue

        existing_result = db.query(RaceResult).filter_by(race_id=race_id, driver_id=driver_id).first()
        if existing_result:
            continue

        result = RaceResult(
            race_id=race_id,
            driver_id=driver_id,
            constructor_id=constructor_id,
            qualifying_pos=res["qualifying_pos"],
            race_pos=res["race_pos"],
            dnf=res["dnf"],
            dsq=False,
            fastest_lap=res["fastest_lap"],
            driver_of_day=False,
            positions_gained_quali=0,
            positions_gained_race=res["positions_gained_race"],
            overtakes=res["overtakes"],
            q2_reached=res["qualifying_pos"] <= 15,
            q3_reached=res["qualifying_pos"] <= 10,
        )
        db.add(result)
        db.flush()

        # Compute and store fantasy points
        q_pts = qualifying_position_points(res["qualifying_pos"], False)
        q_bonus = qualifying_bonus_points(0, 0)
        r_pts = race_position_points(res["race_pos"], res["dnf"], False)
        r_bonus = race_bonus_points(
            res["positions_gained_race"],
            res["overtakes"],
            res["fastest_lap"],
            False,
        )
        total = q_pts + q_bonus + r_pts + r_bonus

        existing_fp = db.query(FantasyPoints).filter_by(race_id=race_id, driver_id=driver_id).first()
        if not existing_fp:
            fp = FantasyPoints(
                race_id=race_id,
                driver_id=driver_id,
                qualifying_pts=float(q_pts + q_bonus),
                race_pts=float(r_pts + r_bonus),
                total_pts=float(total),
                xp_score=0.0,  # will be computed next
            )
            db.add(fp)

    db.commit()
    logger.info("  Seeded %d race results with fantasy points", len(SIMULATED_RESULTS))


def compute_xp_scores(db: Session):
    """Compute and store xP scores for all drivers based on their historical fantasy points."""
    drivers = db.query(Driver).all()
    for driver in drivers:
        fp_rows = (
            db.query(FantasyPoints)
            .filter_by(driver_id=driver.id)
            .order_by(FantasyPoints.race_id.asc())
            .all()
        )
        recent_pts = [row.total_pts for row in fp_rows[-3:]]
        xp = calculate_xp(recent_pts, driver.code, "balanced")

        # Update xp_score in the most recent FantasyPoints row
        if fp_rows:
            fp_rows[-1].xp_score = xp
    db.commit()
    logger.info("  Computed xP scores for %d drivers", len(drivers))


async def main():
    logger.info("=" * 60)
    logger.info("F1 Points Engine — Database Seed")
    logger.info("=" * 60)

    logger.info("\nInitialising database tables...")
    init_db()

    db: Session = SessionLocal()
    try:
        logger.info("\nSeeding constructors...")
        constructor_id_map = await seed_constructors(db)
        logger.info("  %d constructors seeded", len(constructor_id_map))

        logger.info("\nSeeding drivers...")
        driver_code_map = await seed_drivers(db, constructor_id_map)
        logger.info("  %d drivers seeded", len(driver_code_map))

        logger.info("\nSeeding 2025 race calendar...")
        race_round_map = await seed_races(db)
        logger.info("  %d races seeded", len(race_round_map))

        logger.info("\nSeeding race results and fantasy points...")
        seed_results(db, race_round_map, driver_code_map, constructor_id_map)

        logger.info("\nComputing xP scores...")
        compute_xp_scores(db)

        logger.info("\n" + "=" * 60)
        logger.info("Seed complete! App is ready to use.")
        logger.info("  Start backend: uvicorn backend.main:app --reload --port 8000")
        logger.info("  API docs:      http://localhost:8000/docs")
        logger.info("=" * 60)

    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
