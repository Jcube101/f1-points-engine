"""Configuration constants for F1 Points Engine."""

OPENF1_BASE_URL = "https://api.openf1.org/v1"
ERGAST_BASE_URL = "https://ergast.com/api/f1"
F1_FANTASY_BASE_URL = "https://fantasy.formula1.com/feeds"

CURRENT_SEASON = 2025
BUDGET_CAP = 100_000_000  # $100M

# Scoring tables
QUALIFYING_POINTS = {1: 10, 2: 9, 3: 8, 4: 7, 5: 6, 6: 5, 7: 4, 8: 3, 9: 2, 10: 1}
SPRINT_POINTS = {1: 8, 2: 7, 3: 6, 4: 5, 5: 4, 6: 3, 7: 2, 8: 1}
RACE_POINTS = {1: 25, 2: 18, 3: 15, 4: 12, 5: 10, 6: 8, 7: 6, 8: 4, 9: 2, 10: 1}

# Circuit type multipliers per driver code (placeholder - seeded with sensible defaults)
CIRCUIT_MULTIPLIERS = {
    "street": 1.0,
    "power": 1.0,
    "balanced": 1.0,
}
