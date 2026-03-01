"""
Team Optimizer — F1 Points Engine
===================================
Uses PuLP linear programming to solve two objectives:
1. Max Points Team: Maximize projected fantasy points within $100M budget.
2. Best Value Team: Rank assets by xP_per_million, greedily select within budget.

Team rules:
- Exactly 5 drivers + 2 constructors
- Total price ≤ $100,000,000
- Minimum price per asset: $3,000,000
- No duplicates
"""

import logging
from dataclasses import dataclass
from typing import Any

try:
    import pulp
    PULP_AVAILABLE = True
except ImportError:
    PULP_AVAILABLE = False

from backend.core.config import BUDGET_CAP

logger = logging.getLogger(__name__)


@dataclass
class Asset:
    id: int
    name: str
    code: str
    price: float
    xp: float
    xp_per_million: float
    asset_type: str  # "driver" | "constructor"
    team_code: str = ""


def optimize_max_points(
    drivers: list[Asset],
    constructors: list[Asset],
    budget: float = BUDGET_CAP,
) -> dict[str, Any]:
    """
    Use PuLP integer linear programming to find the team maximising projected xP.

    Args:
        drivers: List of all available driver assets with price and xP.
        constructors: List of all available constructor assets.
        budget: Total budget cap in dollars (default $100M).

    Returns:
        Dict with keys: drivers (list of Asset), constructors (list of Asset),
        total_xp, total_price, feasible (bool).

    Constraints:
        - Exactly 5 drivers selected
        - Exactly 2 constructors selected
        - Total price ≤ budget
    """
    if not PULP_AVAILABLE:
        logger.warning("PuLP not installed, falling back to greedy optimizer")
        return _greedy_max_points(drivers, constructors, budget)

    prob = pulp.LpProblem("MaxF1FantasyPoints", pulp.LpMaximize)

    d_vars = {d.id: pulp.LpVariable(f"d_{d.id}", cat="Binary") for d in drivers}
    c_vars = {c.id: pulp.LpVariable(f"c_{c.id}", cat="Binary") for c in constructors}

    # Objective: maximise total xP
    prob += (
        pulp.lpSum(d.xp * d_vars[d.id] for d in drivers)
        + pulp.lpSum(c.xp * c_vars[c.id] for c in constructors)
    )

    # Constraints
    prob += pulp.lpSum(d_vars[d.id] for d in drivers) == 5, "exactly_5_drivers"
    prob += pulp.lpSum(c_vars[c.id] for c in constructors) == 2, "exactly_2_constructors"
    prob += (
        pulp.lpSum(d.price * d_vars[d.id] for d in drivers)
        + pulp.lpSum(c.price * c_vars[c.id] for c in constructors)
        <= budget
    ), "budget_cap"

    prob.solve(pulp.PULP_CBC_CMD(msg=0))

    if pulp.LpStatus[prob.status] != "Optimal":
        logger.warning("PuLP did not find optimal solution, falling back to greedy")
        return _greedy_max_points(drivers, constructors, budget)

    selected_drivers = [d for d in drivers if d_vars[d.id].value() == 1]
    selected_constructors = [c for c in constructors if c_vars[c.id].value() == 1]

    return {
        "drivers": selected_drivers,
        "constructors": selected_constructors,
        "total_xp": sum(d.xp for d in selected_drivers) + sum(c.xp for c in selected_constructors),
        "total_price": sum(d.price for d in selected_drivers) + sum(c.price for c in selected_constructors),
        "feasible": True,
    }


def optimize_best_value(
    drivers: list[Asset],
    constructors: list[Asset],
    budget: float = BUDGET_CAP,
) -> dict[str, Any]:
    """
    Greedy best-value team: rank all assets by xP_per_million and select within budget.

    Args:
        drivers: List of all available driver assets.
        constructors: List of all available constructor assets.
        budget: Total budget cap in dollars.

    Returns:
        Dict with keys: drivers, constructors, total_xp, total_price, feasible.

    Strategy:
        Sort all assets by xP_per_million descending, greedily pick 5 drivers
        and 2 constructors while staying under budget.
    """
    sorted_drivers = sorted(drivers, key=lambda d: d.xp_per_million, reverse=True)
    sorted_constructors = sorted(constructors, key=lambda c: c.xp_per_million, reverse=True)

    selected_drivers: list[Asset] = []
    selected_constructors: list[Asset] = []
    remaining = budget

    for c in sorted_constructors:
        if len(selected_constructors) < 2 and c.price <= remaining:
            selected_constructors.append(c)
            remaining -= c.price

    for d in sorted_drivers:
        if len(selected_drivers) < 5 and d.price <= remaining:
            selected_drivers.append(d)
            remaining -= d.price

    feasible = len(selected_drivers) == 5 and len(selected_constructors) == 2
    return {
        "drivers": selected_drivers,
        "constructors": selected_constructors,
        "total_xp": sum(d.xp for d in selected_drivers) + sum(c.xp for c in selected_constructors),
        "total_price": sum(d.price for d in selected_drivers) + sum(c.price for c in selected_constructors),
        "feasible": feasible,
    }


def _greedy_max_points(
    drivers: list[Asset],
    constructors: list[Asset],
    budget: float,
) -> dict[str, Any]:
    """Fallback greedy approach: pick top-xP assets within budget."""
    sorted_drivers = sorted(drivers, key=lambda d: d.xp, reverse=True)
    sorted_constructors = sorted(constructors, key=lambda c: c.xp, reverse=True)

    selected_drivers: list[Asset] = []
    selected_constructors: list[Asset] = []
    remaining = budget

    for c in sorted_constructors:
        if len(selected_constructors) < 2 and c.price <= remaining:
            selected_constructors.append(c)
            remaining -= c.price

    for d in sorted_drivers:
        if len(selected_drivers) < 5 and d.price <= remaining:
            selected_drivers.append(d)
            remaining -= d.price

    return {
        "drivers": selected_drivers,
        "constructors": selected_constructors,
        "total_xp": sum(d.xp for d in selected_drivers) + sum(c.xp for c in selected_constructors),
        "total_price": sum(d.price for d in selected_drivers) + sum(c.price for c in selected_constructors),
        "feasible": len(selected_drivers) == 5 and len(selected_constructors) == 2,
    }
