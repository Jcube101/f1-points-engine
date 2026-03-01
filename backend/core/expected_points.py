"""
Expected Points (xP) — F1 Points Engine
=========================================
xP is the F1 equivalent of xG in FPL. It smooths out lucky/unlucky results to
give a truer picture of a driver's expected fantasy points per race weekend.

Formula:
    xP = weighted_avg(last_3_race_points) × circuit_type_multiplier × teammate_gap_factor

- weighted_avg: most recent race 50%, previous 30%, oldest 20%
- circuit_type_multiplier: per-driver historical performance on street/power/balanced
- teammate_gap_factor: if driver consistently outqualifies teammate, slight boost
"""

from typing import Optional

# Default circuit multipliers per driver code per circuit type.
# Values > 1.0 mean the driver historically performs better on that type.
DEFAULT_CIRCUIT_MULTIPLIERS: dict[str, dict[str, float]] = {
    # Format: driver_code -> {circuit_type -> multiplier}
    "VER": {"street": 0.95, "power": 1.10, "balanced": 1.05},
    "NOR": {"street": 1.05, "power": 1.0, "balanced": 1.0},
    "LEC": {"street": 1.15, "power": 0.95, "balanced": 1.0},
    "PIA": {"street": 1.0, "power": 1.0, "balanced": 1.0},
    "SAI": {"street": 1.05, "power": 1.0, "balanced": 1.0},
    "RUS": {"street": 1.0, "power": 1.05, "balanced": 1.0},
    "HAM": {"street": 1.0, "power": 1.05, "balanced": 1.0},
    "ANT": {"street": 1.0, "power": 1.0, "balanced": 1.0},
    "ALO": {"street": 1.10, "power": 0.95, "balanced": 1.0},
    "STR": {"street": 1.0, "power": 1.0, "balanced": 1.0},
    "GAS": {"street": 1.0, "power": 1.0, "balanced": 1.0},
    "OCO": {"street": 1.0, "power": 1.0, "balanced": 1.0},
    "HUL": {"street": 1.0, "power": 1.0, "balanced": 1.0},
    "BOR": {"street": 1.0, "power": 1.0, "balanced": 1.0},
    "TSU": {"street": 1.05, "power": 1.0, "balanced": 1.0},
    "LAW": {"street": 1.0, "power": 1.0, "balanced": 1.0},
    "ALB": {"street": 1.0, "power": 1.0, "balanced": 1.0},
    "SAR": {"street": 1.0, "power": 1.0, "balanced": 1.0},
    "BEA": {"street": 1.0, "power": 1.0, "balanced": 1.0},
    "DOO": {"street": 1.0, "power": 1.0, "balanced": 1.0},
    "HAD": {"street": 1.0, "power": 1.0, "balanced": 1.0},
}


def weighted_average(points: list[float]) -> float:
    """
    Compute a weighted rolling average of the last 3 race points.

    Args:
        points: List of fantasy points from recent races, most recent LAST.
                Can have 0–3 entries; fewer races = lower confidence.

    Returns:
        Weighted average. Weights: [oldest=0.2, middle=0.3, most_recent=0.5].
        If fewer than 3 races, weights are redistributed proportionally.
    """
    weights = [0.2, 0.3, 0.5]

    if not points:
        return 0.0
    if len(points) == 1:
        return float(points[-1])
    if len(points) == 2:
        w = [0.4, 0.6]
        return sum(p * w for p, w in zip(points[-2:], w))

    last3 = points[-3:]
    return sum(p * w for p, w in zip(last3, weights))


def circuit_type_multiplier(driver_code: str, circuit_type: str) -> float:
    """
    Return the circuit-type performance multiplier for a given driver.

    Args:
        driver_code: Short driver code (e.g. "VER", "NOR").
        circuit_type: One of "street", "power", "balanced".

    Returns:
        Float multiplier (e.g. 1.15 = 15% boost). Defaults to 1.0 if unknown.
    """
    driver_mults = DEFAULT_CIRCUIT_MULTIPLIERS.get(driver_code, {})
    return driver_mults.get(circuit_type, 1.0)


def teammate_gap_factor(
    driver_quali_positions: list[int],
    teammate_quali_positions: list[int],
) -> float:
    """
    Compute a slight qualifying xP boost if driver consistently outqualifies teammate.

    Args:
        driver_quali_positions: List of driver's qualifying positions over recent races.
        teammate_quali_positions: List of teammate's qualifying positions over same races.

    Returns:
        Float factor. 1.0 = neutral, up to 1.05 = 5% boost, down to 0.97 = 3% penalty.
        Only applies to qualifying xP, not race xP.
    """
    if not driver_quali_positions or not teammate_quali_positions:
        return 1.0

    n = min(len(driver_quali_positions), len(teammate_quali_positions))
    driver_avg = sum(driver_quali_positions[:n]) / n
    teammate_avg = sum(teammate_quali_positions[:n]) / n

    gap = teammate_avg - driver_avg  # positive means driver qualifies better (lower pos)
    # Cap the boost at ±5%
    factor = 1.0 + min(0.05, max(-0.03, gap * 0.01))
    return round(factor, 4)


def calculate_xp(
    recent_race_points: list[float],
    driver_code: str,
    circuit_type: str,
    driver_quali_positions: Optional[list[int]] = None,
    teammate_quali_positions: Optional[list[int]] = None,
) -> float:
    """
    Calculate expected points (xP) for a driver ahead of a race weekend.

    Args:
        recent_race_points: Driver's total fantasy points from up to last 3 races (oldest first).
        driver_code: Short driver code (e.g. "VER").
        circuit_type: Type of upcoming circuit ("street" | "power" | "balanced").
        driver_quali_positions: Optional list of driver's recent qualifying positions.
        teammate_quali_positions: Optional list of teammate's recent qualifying positions.

    Returns:
        xP score as a float. Represents expected fantasy points for the weekend.

    Formula:
        xP = weighted_avg(last_3_race_points) × circuit_type_multiplier × teammate_gap_factor
    """
    w_avg = weighted_average(recent_race_points)
    circ_mult = circuit_type_multiplier(driver_code, circuit_type)
    tm_factor = teammate_gap_factor(
        driver_quali_positions or [],
        teammate_quali_positions or [],
    )
    return round(w_avg * circ_mult * tm_factor, 2)


def xp_per_million(xp: float, price: float) -> float:
    """
    Compute value score: expected points per million dollars.

    Args:
        xp: Expected points (xP) for the driver.
        price: Driver price in dollars.

    Returns:
        xP / (price / 1_000_000). Higher = better value.
    """
    if price <= 0:
        return 0.0
    return round(xp / (price / 1_000_000), 4)
