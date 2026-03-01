"""
Chip Advisor — F1 Points Engine
=================================
Rule-based chip recommendation engine. Returns a prioritized recommendation
with confidence rating and plain-English explanation.

Chips available: DRS Boost, Extra DRS, No Negative, Wildcard, Limitless, Autopilot, Final Fix
"""

from dataclasses import dataclass


@dataclass
class ChipRecommendation:
    chip: str
    confidence: str  # "High" | "Medium" | "Low"
    reason: str
    alternatives: list[dict]


def recommend_chip(
    race_id: int,
    circuit_type: str,
    chips_remaining: list[str],
    team_value: float,
    transfers_banked: int,
    races_completed: int,
    wet_weather_forecast: bool = False,
    circuit_dnf_rate: float = 0.0,
    is_home_gp_for_top_driver: bool = False,
    total_races: int = 24,
) -> ChipRecommendation:
    """
    Return the highest-priority chip recommendation given the current situation.

    Args:
        race_id: The ID of the upcoming race.
        circuit_type: "street" | "power" | "balanced"
        chips_remaining: List of chip names the user still has available.
        team_value: Current team value in dollars.
        transfers_banked: Number of free transfers banked.
        races_completed: How many races have been completed this season.
        wet_weather_forecast: Whether wet weather is forecast for the race.
        circuit_dnf_rate: Historical DNF rate at this circuit (0.0–1.0).
        is_home_gp_for_top_driver: Whether this is a top driver's home GP.
        total_races: Total races in the season (default 24).

    Returns:
        ChipRecommendation with chip name, confidence, reason, and alternatives.

    Priority order (highest → lowest):
        1. Street circuit + DNF rate > 20% → No Negative (High)
        2. Wet weather forecast → No Negative (High)
        3. 3+ banked transfers → Wildcard (Medium)
        4. >4 races in + team value < $98M → Wildcard (Medium)
        5. High-value race (home GP) → Extra DRS Boost (Medium)
        6. >8 races in + Limitless unused → Limitless (Low)
        7. None of the above → Hold chips
    """
    alternatives: list[dict] = []

    # Rule 1: Street circuit with high DNF rate
    if "No Negative" in chips_remaining and circuit_type == "street" and circuit_dnf_rate > 0.20:
        _add_alternatives(alternatives, chips_remaining, exclude="No Negative")
        return ChipRecommendation(
            chip="No Negative",
            confidence="High",
            reason=(
                f"Street circuits have historically high DNF rates "
                f"({circuit_dnf_rate:.0%} at this venue). No Negative protects your score "
                "by flooring any negative points to zero."
            ),
            alternatives=alternatives,
        )

    # Rule 2: Wet weather forecast
    if "No Negative" in chips_remaining and wet_weather_forecast:
        _add_alternatives(alternatives, chips_remaining, exclude="No Negative")
        return ChipRecommendation(
            chip="No Negative",
            confidence="High",
            reason=(
                "Wet conditions dramatically increase the risk of crashes and DNFs. "
                "No Negative ensures a bad result for one driver won't tank your score."
            ),
            alternatives=alternatives,
        )

    # Rule 3: 3+ banked transfers
    if "Wildcard" in chips_remaining and transfers_banked >= 3:
        _add_alternatives(alternatives, chips_remaining, exclude="Wildcard")
        return ChipRecommendation(
            chip="Wildcard",
            confidence="Medium",
            reason=(
                f"You have {transfers_banked} transfers banked. A Wildcard lets you "
                "completely reset your team for free — ideal when you've been saving up for a major overhaul."
            ),
            alternatives=alternatives,
        )

    # Rule 4: >4 races in + team value < $98M
    if "Wildcard" in chips_remaining and races_completed > 4 and team_value < 98_000_000:
        _add_alternatives(alternatives, chips_remaining, exclude="Wildcard")
        return ChipRecommendation(
            chip="Wildcard",
            confidence="Medium",
            reason=(
                f"Your team is worth ${team_value/1e6:.1f}M after {races_completed} races — "
                "below the competitive threshold. A Wildcard now lets you rebuild with better value assets."
            ),
            alternatives=alternatives,
        )

    # Rule 5: Home GP for top driver (high-value race)
    if "Extra DRS" in chips_remaining and is_home_gp_for_top_driver:
        _add_alternatives(alternatives, chips_remaining, exclude="Extra DRS")
        return ChipRecommendation(
            chip="Extra DRS",
            confidence="Medium",
            reason=(
                "This is a home Grand Prix for a top driver who typically overperforms at this race. "
                "Extra DRS (3×) maximises points from a likely standout performance."
            ),
            alternatives=alternatives,
        )

    # Rule 6: >8 races in + Limitless unused
    if "Limitless" in chips_remaining and races_completed > 8:
        _add_alternatives(alternatives, chips_remaining, exclude="Limitless")
        return ChipRecommendation(
            chip="Limitless",
            confidence="Low",
            reason=(
                f"You're {races_completed} races in and still haven't used Limitless. "
                "Pick a high-scoring weekend (strong track + form) and use it before the season ends."
            ),
            alternatives=alternatives,
        )

    # Default: Hold chips
    _add_alternatives(alternatives, chips_remaining, exclude=None)
    return ChipRecommendation(
        chip="Hold",
        confidence="Low",
        reason=(
            "No standout opportunity this weekend. Save your chips for a circuit where "
            "conditions or value align for maximum impact."
        ),
        alternatives=alternatives,
    )


def _add_alternatives(
    alternatives: list[dict],
    chips_remaining: list[str],
    exclude: str | None,
) -> None:
    """Populate alternatives list with remaining chips and brief descriptions."""
    descriptions = {
        "No Negative": "Floors all negative scores to 0 — great for risky weekends.",
        "Wildcard": "Reset your entire team for free.",
        "Extra DRS": "Triple points (3×) for your selected driver.",
        "DRS Boost": "Double points (2×) for your selected driver.",
        "Limitless": "Pick any team regardless of budget for one race.",
        "Autopilot": "System auto-applies 2× to your highest scorer.",
        "Final Fix": "Make unlimited free transfers in the final race.",
    }
    for chip in chips_remaining:
        if chip != exclude:
            alternatives.append({
                "chip": chip,
                "reason": descriptions.get(chip, ""),
            })
