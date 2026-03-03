"""
Seed Script — F1 Points Engine
================================
Run once to populate the database with:
1. 2025 race calendar + generated historical race results (24 rounds)
2. 2026 race calendar (upcoming)
3. Driver + constructor list with real 2026 fantasy prices (11 constructors, 22 drivers)
4. 2025 fantasy points computed for each driver/race using scoring engine
5. Initial xP scores for all 2026 drivers

Run with:
    cd backend && python seed.py
    OR from project root:
    python backend/seed.py
"""

import asyncio
import logging
import os
import random
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
    sprint_position_points, sprint_bonus_points,
)
from backend.core.expected_points import calculate_xp

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# ─── 2026 Driver pricing (real F1 Fantasy opening prices) ─────────────────────
DRIVER_PRICES: dict[str, float] = {
    "max_verstappen":     27_700_000,
    "george_russell":     27_400_000,
    "lando_norris":       27_200_000,
    "oscar_piastri":      25_500_000,
    "kimi_antonelli":     23_200_000,
    "charles_leclerc":    22_800_000,
    "lewis_hamilton":     22_500_000,
    "isack_hadjar":       15_100_000,
    "pierre_gasly":       12_000_000,
    "carlos_sainz":       11_800_000,
    "alexander_albon":    11_600_000,
    "fernando_alonso":    10_000_000,
    "lance_stroll":        8_000_000,
    "oliver_bearman":      7_400_000,
    "esteban_ocon":        7_300_000,
    "nico_hulkenberg":     6_800_000,
    "gabriel_bortoleto":   6_500_000,
    "liam_lawson":         6_400_000,
    "arvid_lindblad":      6_200_000,
    "franco_colapinto":    6_200_000,
    "sergio_perez":        6_000_000,
    "valtteri_bottas":     5_800_000,
    # 2025-only drivers — seeded for historical results, not on 2026 grid
    "yuki_tsunoda":        0,
    "jack_doohan":         0,
    "default":            10_000_000,
}

# ─── 2026 Constructor pricing (real F1 Fantasy opening prices) ─────────────────
CONSTRUCTOR_PRICES: dict[str, float] = {
    "mercedes":       29_300_000,
    "mclaren":        28_900_000,
    "red_bull":       28_200_000,
    "ferrari":        23_300_000,
    "alpine":         12_500_000,
    "williams":       12_000_000,
    "aston_martin":   10_300_000,
    "haas":            7_400_000,
    "audi":            6_600_000,
    "rb":              6_300_000,
    "cadillac":        6_000_000,
    "default":        10_000_000,
}

CONSTRUCTOR_COLORS: dict[str, str] = {
    "red_bull":     "#3671C6",
    "mclaren":      "#FF8000",
    "ferrari":      "#E8002D",
    "mercedes":     "#27F4D2",
    "aston_martin": "#229971",
    "alpine":       "#FF87BC",
    "haas":         "#B6BABD",
    "rb":           "#6692FF",
    "williams":     "#64C4FF",
    "audi":         "#52E252",
    "cadillac":     "#CC0033",
}

CIRCUIT_TYPES: dict[str, str] = {
    "Australian Grand Prix":     "balanced",
    "Chinese Grand Prix":        "balanced",
    "Japanese Grand Prix":       "balanced",
    "Bahrain Grand Prix":        "balanced",
    "Saudi Arabian Grand Prix":  "street",
    "Miami Grand Prix":          "street",
    "Emilia Romagna Grand Prix": "balanced",
    "Monaco Grand Prix":         "street",
    "Spanish Grand Prix":        "balanced",
    "Canadian Grand Prix":       "street",
    "Austrian Grand Prix":       "balanced",
    "British Grand Prix":        "balanced",
    "Hungarian Grand Prix":      "balanced",
    "Belgian Grand Prix":        "power",
    "Dutch Grand Prix":          "balanced",
    "Italian Grand Prix":        "power",
    "Azerbaijan Grand Prix":     "street",
    "Singapore Grand Prix":      "street",
    "United States Grand Prix":  "balanced",
    "Mexico City Grand Prix":    "power",
    "São Paulo Grand Prix":      "balanced",
    "Las Vegas Grand Prix":      "street",
    "Qatar Grand Prix":          "balanced",
    "Abu Dhabi Grand Prix":      "balanced",
}

SPRINT_RACES = {
    "Chinese Grand Prix",
    "Miami Grand Prix",
    "Austrian Grand Prix",
    "United States Grand Prix",
    "São Paulo Grand Prix",
    "Qatar Grand Prix",
}

# ─── 2025 drivers on the grid (full season, 20 drivers) ───────────────────────
# These are NOT in the 2026 roster but raced the full 2025 season
DRIVERS_2025_ONLY = {"DOO", "TSU"}  # Doohan and Tsunoda not on 2026 grid

# 2025 driver codes (full grid)
DRIVERS_2025 = [
    "VER", "NOR", "LEC", "PIA", "RUS", "HAM", "SAI", "ANT",
    "ALO", "TSU", "HUL", "ALB", "GAS", "STR", "BEA", "DOO",
    "LAW", "BOR", "HAD", "COL",
]

# Strength profiles for 2025 simulation (0.0–1.0): reflects McLaren dominance
DRIVER_STRENGTH_2025: dict[str, float] = {
    "VER": 0.95,
    "NOR": 0.90,
    "PIA": 0.85,
    "LEC": 0.84,
    "RUS": 0.82,
    "HAM": 0.80,
    "SAI": 0.76,
    "ANT": 0.72,
    "ALO": 0.70,
    "TSU": 0.62,
    "HUL": 0.60,
    "ALB": 0.60,
    "GAS": 0.58,
    "STR": 0.55,
    "BEA": 0.53,
    "LAW": 0.52,
    "DOO": 0.50,
    "BOR": 0.48,
    "HAD": 0.47,
    "COL": 0.45,
}

# 2025 team memberships for race_results (Sauber → stored as 'audi' after rename)
DRIVER_CONSTRUCTOR_2025: dict[str, str] = {
    "VER": "red_bull",    "LAW": "red_bull",
    "NOR": "mclaren",     "PIA": "mclaren",
    "LEC": "ferrari",     "HAM": "ferrari",
    "RUS": "mercedes",    "ANT": "mercedes",
    "SAI": "williams",    "ALB": "williams",
    "ALO": "aston_martin","STR": "aston_martin",
    "GAS": "alpine",      "DOO": "alpine",
    "HUL": "audi",        "BOR": "audi",    # Sauber in 2025, renamed to Audi in DB
    "TSU": "rb",          "HAD": "rb",
    "BEA": "haas",        "COL": "alpine",  # Colapinto replaced Doohan; simplified to full season
}

# ─── 2026 roster (22 drivers) ─────────────────────────────────────────────────
FALLBACK_DRIVERS = [
    {"driverId": "max_verstappen",    "code": "VER", "givenName": "Max",       "familyName": "Verstappen",  "nationality": "Dutch",         "constructorId": "red_bull"},
    {"driverId": "isack_hadjar",      "code": "HAD", "givenName": "Isack",     "familyName": "Hadjar",      "nationality": "French",        "constructorId": "red_bull"},
    {"driverId": "lando_norris",      "code": "NOR", "givenName": "Lando",     "familyName": "Norris",      "nationality": "British",       "constructorId": "mclaren"},
    {"driverId": "oscar_piastri",     "code": "PIA", "givenName": "Oscar",     "familyName": "Piastri",     "nationality": "Australian",    "constructorId": "mclaren"},
    {"driverId": "charles_leclerc",   "code": "LEC", "givenName": "Charles",   "familyName": "Leclerc",     "nationality": "Monegasque",    "constructorId": "ferrari"},
    {"driverId": "lewis_hamilton",    "code": "HAM", "givenName": "Lewis",     "familyName": "Hamilton",    "nationality": "British",       "constructorId": "ferrari"},
    {"driverId": "george_russell",    "code": "RUS", "givenName": "George",    "familyName": "Russell",     "nationality": "British",       "constructorId": "mercedes"},
    {"driverId": "kimi_antonelli",    "code": "ANT", "givenName": "Kimi",      "familyName": "Antonelli",   "nationality": "Italian",       "constructorId": "mercedes"},
    {"driverId": "pierre_gasly",      "code": "GAS", "givenName": "Pierre",    "familyName": "Gasly",       "nationality": "French",        "constructorId": "alpine"},
    {"driverId": "franco_colapinto",  "code": "COL", "givenName": "Franco",    "familyName": "Colapinto",   "nationality": "Argentine",     "constructorId": "alpine"},
    {"driverId": "carlos_sainz",      "code": "SAI", "givenName": "Carlos",    "familyName": "Sainz",       "nationality": "Spanish",       "constructorId": "williams"},
    {"driverId": "alexander_albon",   "code": "ALB", "givenName": "Alexander", "familyName": "Albon",       "nationality": "Thai",          "constructorId": "williams"},
    {"driverId": "fernando_alonso",   "code": "ALO", "givenName": "Fernando",  "familyName": "Alonso",      "nationality": "Spanish",       "constructorId": "aston_martin"},
    {"driverId": "lance_stroll",      "code": "STR", "givenName": "Lance",     "familyName": "Stroll",      "nationality": "Canadian",      "constructorId": "aston_martin"},
    {"driverId": "oliver_bearman",    "code": "BEA", "givenName": "Oliver",    "familyName": "Bearman",     "nationality": "British",       "constructorId": "haas"},
    {"driverId": "esteban_ocon",      "code": "OCO", "givenName": "Esteban",   "familyName": "Ocon",        "nationality": "French",        "constructorId": "haas"},
    {"driverId": "nico_hulkenberg",   "code": "HUL", "givenName": "Nico",      "familyName": "Hulkenberg",  "nationality": "German",        "constructorId": "audi"},
    {"driverId": "gabriel_bortoleto", "code": "BOR", "givenName": "Gabriel",   "familyName": "Bortoleto",   "nationality": "Brazilian",     "constructorId": "audi"},
    {"driverId": "liam_lawson",       "code": "LAW", "givenName": "Liam",      "familyName": "Lawson",      "nationality": "New Zealander", "constructorId": "rb"},
    {"driverId": "arvid_lindblad",    "code": "LIN", "givenName": "Arvid",     "familyName": "Lindblad",    "nationality": "Swedish",       "constructorId": "rb"},
    {"driverId": "sergio_perez",      "code": "PER", "givenName": "Sergio",    "familyName": "Perez",       "nationality": "Mexican",       "constructorId": "cadillac"},
    {"driverId": "valtteri_bottas",   "code": "BOT", "givenName": "Valtteri",  "familyName": "Bottas",      "nationality": "Finnish",       "constructorId": "cadillac"},
    # 2025-only drivers — needed in DB to hold historical race results
    {"driverId": "yuki_tsunoda",      "code": "TSU", "givenName": "Yuki",      "familyName": "Tsunoda",     "nationality": "Japanese",      "constructorId": "rb"},
    {"driverId": "jack_doohan",       "code": "DOO", "givenName": "Jack",      "familyName": "Doohan",      "nationality": "Australian",    "constructorId": "alpine"},
]

# ─── 2026 constructors (11 teams) ─────────────────────────────────────────────
FALLBACK_CONSTRUCTORS = [
    {"constructorId": "red_bull",     "name": "Red Bull Racing", "nationality": "Austrian"},
    {"constructorId": "mclaren",      "name": "McLaren",         "nationality": "British"},
    {"constructorId": "ferrari",      "name": "Ferrari",         "nationality": "Italian"},
    {"constructorId": "mercedes",     "name": "Mercedes",        "nationality": "German"},
    {"constructorId": "alpine",       "name": "Alpine",          "nationality": "French"},
    {"constructorId": "williams",     "name": "Williams",        "nationality": "British"},
    {"constructorId": "aston_martin", "name": "Aston Martin",    "nationality": "British"},
    {"constructorId": "haas",         "name": "Haas F1 Team",    "nationality": "American"},
    {"constructorId": "audi",         "name": "Audi",            "nationality": "German"},
    {"constructorId": "rb",           "name": "Racing Bulls",    "nationality": "Italian"},
    {"constructorId": "cadillac",     "name": "Cadillac",        "nationality": "American"},
]

# ─── Race calendars ────────────────────────────────────────────────────────────
FALLBACK_CALENDAR = [
    {"round": "1",  "raceName": "Australian Grand Prix",    "Circuit": {"circuitName": "Albert Park"},   "date": "2025-03-16", "season": "2025"},
    {"round": "2",  "raceName": "Chinese Grand Prix",        "Circuit": {"circuitName": "Shanghai"},      "date": "2025-03-23", "season": "2025"},
    {"round": "3",  "raceName": "Japanese Grand Prix",       "Circuit": {"circuitName": "Suzuka"},        "date": "2025-04-06", "season": "2025"},
    {"round": "4",  "raceName": "Bahrain Grand Prix",        "Circuit": {"circuitName": "Bahrain"},       "date": "2025-04-13", "season": "2025"},
    {"round": "5",  "raceName": "Saudi Arabian Grand Prix",  "Circuit": {"circuitName": "Jeddah"},        "date": "2025-04-20", "season": "2025"},
    {"round": "6",  "raceName": "Miami Grand Prix",          "Circuit": {"circuitName": "Miami"},         "date": "2025-05-04", "season": "2025"},
    {"round": "7",  "raceName": "Emilia Romagna Grand Prix", "Circuit": {"circuitName": "Imola"},         "date": "2025-05-18", "season": "2025"},
    {"round": "8",  "raceName": "Monaco Grand Prix",         "Circuit": {"circuitName": "Monaco"},        "date": "2025-05-25", "season": "2025"},
    {"round": "9",  "raceName": "Spanish Grand Prix",        "Circuit": {"circuitName": "Barcelona"},     "date": "2025-06-01", "season": "2025"},
    {"round": "10", "raceName": "Canadian Grand Prix",       "Circuit": {"circuitName": "Montreal"},      "date": "2025-06-15", "season": "2025"},
    {"round": "11", "raceName": "Austrian Grand Prix",       "Circuit": {"circuitName": "Red Bull Ring"}, "date": "2025-06-29", "season": "2025"},
    {"round": "12", "raceName": "British Grand Prix",        "Circuit": {"circuitName": "Silverstone"},   "date": "2025-07-06", "season": "2025"},
    {"round": "13", "raceName": "Hungarian Grand Prix",      "Circuit": {"circuitName": "Hungaroring"},   "date": "2025-07-20", "season": "2025"},
    {"round": "14", "raceName": "Belgian Grand Prix",        "Circuit": {"circuitName": "Spa"},           "date": "2025-07-27", "season": "2025"},
    {"round": "15", "raceName": "Dutch Grand Prix",          "Circuit": {"circuitName": "Zandvoort"},     "date": "2025-08-31", "season": "2025"},
    {"round": "16", "raceName": "Italian Grand Prix",        "Circuit": {"circuitName": "Monza"},         "date": "2025-09-07", "season": "2025"},
    {"round": "17", "raceName": "Azerbaijan Grand Prix",     "Circuit": {"circuitName": "Baku"},          "date": "2025-09-21", "season": "2025"},
    {"round": "18", "raceName": "Singapore Grand Prix",      "Circuit": {"circuitName": "Marina Bay"},    "date": "2025-10-05", "season": "2025"},
    {"round": "19", "raceName": "United States Grand Prix",  "Circuit": {"circuitName": "Austin"},        "date": "2025-10-19", "season": "2025"},
    {"round": "20", "raceName": "Mexico City Grand Prix",    "Circuit": {"circuitName": "Mexico City"},   "date": "2025-10-26", "season": "2025"},
    {"round": "21", "raceName": "São Paulo Grand Prix",      "Circuit": {"circuitName": "Sao Paulo"},     "date": "2025-11-09", "season": "2025"},
    {"round": "22", "raceName": "Las Vegas Grand Prix",      "Circuit": {"circuitName": "Las Vegas"},     "date": "2025-11-22", "season": "2025"},
    {"round": "23", "raceName": "Qatar Grand Prix",          "Circuit": {"circuitName": "Losail"},        "date": "2025-11-30", "season": "2025"},
    {"round": "24", "raceName": "Abu Dhabi Grand Prix",      "Circuit": {"circuitName": "Yas Marina"},    "date": "2025-12-07", "season": "2025"},
]

FALLBACK_CALENDAR_2026 = [
    {"round": "1",  "raceName": "Australian Grand Prix",    "Circuit": {"circuitName": "Albert Park"},   "date": "2026-03-15", "season": "2026"},
    {"round": "2",  "raceName": "Chinese Grand Prix",        "Circuit": {"circuitName": "Shanghai"},      "date": "2026-03-22", "season": "2026"},
    {"round": "3",  "raceName": "Japanese Grand Prix",       "Circuit": {"circuitName": "Suzuka"},        "date": "2026-04-05", "season": "2026"},
    {"round": "4",  "raceName": "Bahrain Grand Prix",        "Circuit": {"circuitName": "Bahrain"},       "date": "2026-04-19", "season": "2026"},
    {"round": "5",  "raceName": "Saudi Arabian Grand Prix",  "Circuit": {"circuitName": "Jeddah"},        "date": "2026-04-26", "season": "2026"},
    {"round": "6",  "raceName": "Miami Grand Prix",          "Circuit": {"circuitName": "Miami"},         "date": "2026-05-10", "season": "2026"},
    {"round": "7",  "raceName": "Emilia Romagna Grand Prix", "Circuit": {"circuitName": "Imola"},         "date": "2026-05-24", "season": "2026"},
    {"round": "8",  "raceName": "Monaco Grand Prix",         "Circuit": {"circuitName": "Monaco"},        "date": "2026-05-31", "season": "2026"},
    {"round": "9",  "raceName": "Spanish Grand Prix",        "Circuit": {"circuitName": "Barcelona"},     "date": "2026-06-07", "season": "2026"},
    {"round": "10", "raceName": "Canadian Grand Prix",       "Circuit": {"circuitName": "Montreal"},      "date": "2026-06-14", "season": "2026"},
    {"round": "11", "raceName": "Austrian Grand Prix",       "Circuit": {"circuitName": "Red Bull Ring"}, "date": "2026-06-28", "season": "2026"},
    {"round": "12", "raceName": "British Grand Prix",        "Circuit": {"circuitName": "Silverstone"},   "date": "2026-07-05", "season": "2026"},
    {"round": "13", "raceName": "Hungarian Grand Prix",      "Circuit": {"circuitName": "Hungaroring"},   "date": "2026-07-19", "season": "2026"},
    {"round": "14", "raceName": "Belgian Grand Prix",        "Circuit": {"circuitName": "Spa"},           "date": "2026-07-26", "season": "2026"},
    {"round": "15", "raceName": "Dutch Grand Prix",          "Circuit": {"circuitName": "Zandvoort"},     "date": "2026-08-30", "season": "2026"},
    {"round": "16", "raceName": "Italian Grand Prix",        "Circuit": {"circuitName": "Monza"},         "date": "2026-09-06", "season": "2026"},
    {"round": "17", "raceName": "Azerbaijan Grand Prix",     "Circuit": {"circuitName": "Baku"},          "date": "2026-09-20", "season": "2026"},
    {"round": "18", "raceName": "Singapore Grand Prix",      "Circuit": {"circuitName": "Marina Bay"},    "date": "2026-10-04", "season": "2026"},
    {"round": "19", "raceName": "United States Grand Prix",  "Circuit": {"circuitName": "Austin"},        "date": "2026-10-18", "season": "2026"},
    {"round": "20", "raceName": "Mexico City Grand Prix",    "Circuit": {"circuitName": "Mexico City"},   "date": "2026-10-25", "season": "2026"},
    {"round": "21", "raceName": "São Paulo Grand Prix",      "Circuit": {"circuitName": "Sao Paulo"},     "date": "2026-11-08", "season": "2026"},
    {"round": "22", "raceName": "Las Vegas Grand Prix",      "Circuit": {"circuitName": "Las Vegas"},     "date": "2026-11-21", "season": "2026"},
    {"round": "23", "raceName": "Qatar Grand Prix",          "Circuit": {"circuitName": "Losail"},        "date": "2026-11-29", "season": "2026"},
    {"round": "24", "raceName": "Abu Dhabi Grand Prix",      "Circuit": {"circuitName": "Yas Marina"},    "date": "2026-12-06", "season": "2026"},
]


def get_2025_constructor(driver_code: str, round_num: int) -> str:
    """
    Return the 2025 constructor key for a driver, handling mid-season swaps.

    Lawson/Tsunoda swap: Lawson drove Red Bull for rounds 1–2, then returned to Racing
    Bulls from round 3. Tsunoda replaced him at Red Bull from round 3 onwards.
    """
    if driver_code == "LAW":
        return "red_bull" if round_num <= 2 else "rb"
    if driver_code == "TSU":
        return "rb" if round_num <= 2 else "red_bull"
    return DRIVER_CONSTRUCTOR_2025.get(driver_code, "")


def generate_2025_season_results() -> list[dict]:
    """
    Generate deterministic simulated results for all 24 rounds of 2025.
    Uses seeded RNG (seed=42) for reproducibility across runs.
    Reflects McLaren dominance with Norris/Piastri as title contenders.
    """
    rng = random.Random(42)
    results = []

    for round_num in range(1, 25):
        race_name = FALLBACK_CALENDAR[round_num - 1]["raceName"]
        is_sprint = race_name in SPRINT_RACES

        # Qualifying: strength + gaussian noise, rank descending
        quali_scores = {
            code: DRIVER_STRENGTH_2025.get(code, 0.5) + rng.gauss(0, 0.12)
            for code in DRIVERS_2025
        }
        quali_order = sorted(DRIVERS_2025, key=lambda c: quali_scores[c], reverse=True)

        # Race: additional noise layer
        race_scores = {
            code: DRIVER_STRENGTH_2025.get(code, 0.5) + rng.gauss(0, 0.15)
            for code in DRIVERS_2025
        }

        # DNFs: ~6–14% chance per driver (higher for backmarkers)
        dnf_set: set[str] = set()
        for code in DRIVERS_2025:
            base_strength = DRIVER_STRENGTH_2025.get(code, 0.5)
            dnf_prob = 0.06 + (1.0 - base_strength) * 0.08
            if rng.random() < dnf_prob:
                dnf_set.add(code)

        finishers = [c for c in DRIVERS_2025 if c not in dnf_set]
        dnfers = [c for c in DRIVERS_2025 if c in dnf_set]
        race_order = sorted(finishers, key=lambda c: race_scores[c], reverse=True) + dnfers

        # Fastest lap: top-6 finisher, random choice
        fl_candidates = race_order[:min(6, len(finishers))]
        fl_winner = rng.choice(fl_candidates) if fl_candidates else None

        # Driver of Day: midfield hero (P6–P15 in race)
        dotd_pool = race_order[5:15]
        dotd_winner = rng.choice(dotd_pool) if dotd_pool else None

        # Sprint weekend
        sprint_order: list[str] | None = None
        sprint_dnf_set: set[str] = set()
        if is_sprint:
            sprint_scores = {
                code: DRIVER_STRENGTH_2025.get(code, 0.5) + rng.gauss(0, 0.10)
                for code in DRIVERS_2025
            }
            for code in DRIVERS_2025:
                if rng.random() < 0.04:
                    sprint_dnf_set.add(code)
            sprint_finishers = [c for c in DRIVERS_2025 if c not in sprint_dnf_set]
            sprint_dnfers = [c for c in DRIVERS_2025 if c in sprint_dnf_set]
            sprint_order = (
                sorted(sprint_finishers, key=lambda c: sprint_scores[c], reverse=True)
                + sprint_dnfers
            )

        for code in DRIVERS_2025:
            quali_pos = quali_order.index(code) + 1
            dnf = code in dnf_set
            race_pos = None if dnf else race_order.index(code) + 1
            positions_gained = 0 if race_pos is None else (quali_pos - race_pos)
            overtakes = max(0, positions_gained // 2) if positions_gained > 0 else 0

            sprint_pos: int | None = None
            sprint_dnf = False
            if is_sprint and sprint_order is not None:
                sprint_dnf = code in sprint_dnf_set
                sprint_pos = None if sprint_dnf else sprint_order.index(code) + 1

            results.append({
                "race_round": round_num,
                "driver_id_code": code,
                "qualifying_pos": quali_pos,
                "race_pos": race_pos,
                "sprint_pos": sprint_pos,
                "dnf": dnf,
                "sprint_dnf": sprint_dnf,
                "fastest_lap": code == fl_winner,
                "driver_of_day": code == dotd_winner,
                "overtakes": overtakes,
                "positions_gained_race": positions_gained,
                "q2_reached": quali_pos <= 15,
                "q3_reached": quali_pos <= 10,
            })

    return results


async def seed_constructors(db: Session) -> dict[str, int]:
    """Seed/update constructors for 2026 (Sauber→Audi rename + Cadillac). Returns constructorId→DB id."""
    # Rename Sauber → Audi if old record exists
    sauber = db.query(Constructor).filter_by(code="SAUBER").first()
    if sauber:
        sauber.name = "Audi"
        sauber.code = "AUDI"
        sauber.price = CONSTRUCTOR_PRICES["audi"]
        sauber.color_hex = CONSTRUCTOR_COLORS.get("audi", "#52E252")
        db.flush()
        logger.info("  Renamed Sauber → Audi")

    code_map: dict[str, int] = {}
    for c in FALLBACK_CONSTRUCTORS:
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
            logger.info("  New constructor: %s ($%.1fM)", name, price / 1e6)
        else:
            existing.price = price
            existing.color_hex = color
            code_map[cid] = existing.id

    db.commit()
    return code_map


async def seed_drivers(db: Session, constructor_id_map: dict[str, int]) -> dict[str, int]:
    """Seed/update drivers for 2026 roster. Returns driver code → DB id mapping."""
    code_map: dict[str, int] = {}
    for d in FALLBACK_DRIVERS:
        driver_id = d.get("driverId", "")
        code = d.get("code", driver_id[:3].upper())
        name = f"{d.get('givenName', '')} {d.get('familyName', '')}".strip()
        nationality = d.get("nationality", "")
        price = DRIVER_PRICES.get(driver_id, DRIVER_PRICES["default"])

        constructor_id_str = d.get("constructorId", "")
        team_id = constructor_id_map.get(constructor_id_str)
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
            logger.info("  New driver: %s [%s] ($%.1fM)", name, code, price / 1e6)
        else:
            existing.price = price
            existing.team_id = team_id
            existing.name = name
            code_map[code] = existing.id
            logger.info("  Updated: %s [%s] ($%.1fM)", name, code, price / 1e6)

    # Mark 2025-only drivers as retired (price=0 preserves historical data)
    for retired_code in DRIVERS_2025_ONLY:
        retired = db.query(Driver).filter_by(code=retired_code).first()
        if retired:
            retired.price = 0.0
            code_map[retired_code] = retired.id  # still needed for 2025 results lookup
            logger.info("  Marked %s as 2025-only (price=0)", retired_code)

    db.commit()
    return code_map


async def seed_races(db: Session, calendar: list[dict], season_year: int) -> dict[int, int]:
    """Seed race calendar for a given season. Returns round_number → DB id mapping."""
    round_map: dict[int, int] = {}
    for race in calendar:
        round_num = int(race.get("round", 0))
        name = race.get("raceName", "")
        circuit_info = race.get("Circuit", {})
        circuit = circuit_info.get("circuitName", "")
        country = circuit_info.get("Location", {}).get("country", "") or race.get("country", "")
        date = race.get("date", f"{season_year}-01-01")
        circuit_type = CIRCUIT_TYPES.get(name, "balanced")
        session_type = "sprint_race" if name in SPRINT_RACES else "race"

        existing = db.query(Race).filter_by(round_number=round_num, season=season_year).first()
        if not existing:
            r = Race(
                name=name, circuit=circuit, country=country, date=date,
                session_type=session_type, round_number=round_num, season=season_year,
                circuit_type=circuit_type,
            )
            db.add(r)
            db.flush()
            round_map[round_num] = r.id
            logger.info("  Race %d [%d]: %s (%s)", round_num, season_year, name, circuit_type)
        else:
            round_map[round_num] = existing.id

    db.commit()
    return round_map


def seed_results(
    db: Session,
    race_round_map: dict[int, int],
    driver_code_map: dict[str, int],
    constructor_id_map: dict[str, int],
) -> int:
    """Seed 2025 race results and compute fantasy points from generated data."""
    generated = generate_2025_season_results()
    inserted = 0

    for res in generated:
        round_num = res["race_round"]
        race_id = race_round_map.get(round_num)
        driver_code = res["driver_id_code"]
        driver_id = driver_code_map.get(driver_code)

        if not race_id or not driver_id:
            logger.debug("  Skipping %s round %d: no race/driver id", driver_code, round_num)
            continue

        # Use 2025 team membership, not current 2026 assignment (handles LAW/TSU swap)
        constructor_key_2025 = get_2025_constructor(driver_code, round_num)
        constructor_id = constructor_id_map.get(constructor_key_2025)
        if not constructor_id:
            logger.warning("  No constructor for %s (%s)", driver_code, constructor_key_2025)
            continue

        existing_result = db.query(RaceResult).filter_by(
            race_id=race_id, driver_id=driver_id
        ).first()
        if existing_result:
            continue

        result = RaceResult(
            race_id=race_id,
            driver_id=driver_id,
            constructor_id=constructor_id,
            qualifying_pos=res["qualifying_pos"],
            race_pos=res["race_pos"],
            sprint_pos=res.get("sprint_pos"),
            dnf=res["dnf"],
            dsq=False,
            fastest_lap=res["fastest_lap"],
            driver_of_day=res.get("driver_of_day", False),
            positions_gained_quali=0,
            positions_gained_race=res["positions_gained_race"],
            overtakes=res["overtakes"],
            q2_reached=res["q2_reached"],
            q3_reached=res["q3_reached"],
        )
        db.add(result)
        db.flush()

        # Compute fantasy points
        q_pts = qualifying_position_points(res["qualifying_pos"], False)
        q_bonus = qualifying_bonus_points(0, 0)
        r_pts = race_position_points(res["race_pos"], res["dnf"], False)
        r_bonus = race_bonus_points(
            res["positions_gained_race"],
            res["overtakes"],
            res["fastest_lap"],
            res.get("driver_of_day", False),
        )

        # Sprint points for sprint weekends
        s_pts = 0.0
        if res.get("sprint_pos") is not None or res.get("sprint_dnf"):
            s_pts = float(sprint_position_points(res.get("sprint_pos"), res.get("sprint_dnf", False)))
            s_pts += float(sprint_bonus_points(0, 0))

        total = q_pts + q_bonus + r_pts + r_bonus + s_pts

        existing_fp = db.query(FantasyPoints).filter_by(
            race_id=race_id, driver_id=driver_id
        ).first()
        if not existing_fp:
            fp = FantasyPoints(
                race_id=race_id,
                driver_id=driver_id,
                qualifying_pts=float(q_pts + q_bonus),
                sprint_pts=float(s_pts),
                race_pts=float(r_pts + r_bonus),
                total_pts=float(total),
                xp_score=0.0,
            )
            db.add(fp)
            inserted += 1

    db.commit()
    return inserted


def compute_xp_scores(db: Session):
    """Compute and store xP scores for all drivers based on their recent fantasy points."""
    drivers = db.query(Driver).filter(Driver.price > 0).all()
    for driver in drivers:
        fp_rows = (
            db.query(FantasyPoints)
            .filter_by(driver_id=driver.id)
            .order_by(FantasyPoints.race_id.asc())
            .all()
        )
        recent_pts = [row.total_pts for row in fp_rows[-3:]]
        xp = calculate_xp(recent_pts, driver.code, "balanced")
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
        logger.info("\nSeeding 2026 constructors (11 teams)...")
        constructor_id_map = await seed_constructors(db)
        logger.info("  %d constructors seeded", len(constructor_id_map))

        logger.info("\nSeeding 2026 drivers (22 drivers)...")
        driver_code_map = await seed_drivers(db, constructor_id_map)
        logger.info("  %d drivers seeded/updated", len(driver_code_map))

        logger.info("\nSeeding 2025 race calendar (24 rounds)...")
        race_round_map_2025 = await seed_races(db, FALLBACK_CALENDAR, 2025)
        logger.info("  %d races seeded for 2025", len(race_round_map_2025))

        logger.info("\nSeeding 2026 race calendar (24 rounds)...")
        race_round_map_2026 = await seed_races(db, FALLBACK_CALENDAR_2026, 2026)
        logger.info("  %d races seeded for 2026", len(race_round_map_2026))

        logger.info("\nGenerating 2025 season results (24 rounds × 20 drivers)...")
        n_inserted = seed_results(db, race_round_map_2025, driver_code_map, constructor_id_map)
        logger.info("  %d fantasy point records inserted", n_inserted)

        logger.info("\nComputing xP scores from 2025 history...")
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
