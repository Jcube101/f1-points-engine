"""
Fantasy Scoring Engine — F1 Points Engine
==========================================
All fantasy scoring logic lives here. Never call scoring math directly in route handlers.
All functions are pure (no DB calls, no side effects).

Scoring rules source: F1 Fantasy official rules (2025 season).
"""

from backend.core.config import (
    QUALIFYING_POINTS, SPRINT_POINTS, RACE_POINTS
)


# ─── Qualifying ───────────────────────────────────────────────────────────────

def qualifying_position_points(position: int | None, dsq: bool = False, no_time: bool = False) -> int:
    """
    Return base fantasy points for a qualifying result.

    Args:
        position: Classified qualifying position (1–20), or None if not classified.
        dsq: Driver was disqualified.
        no_time: Driver failed to set a time.

    Returns:
        Fantasy points integer. Positions 11–20 score 0. No time / DSQ / NC = –5.
    """
    if dsq or no_time or position is None:
        return -5
    return QUALIFYING_POINTS.get(position, 0)


def qualifying_bonus_points(
    positions_gained: int,
    overtakes: int,
    fastest_lap: bool = False,
) -> int:
    """
    Return qualifying bonus points.

    Args:
        positions_gained: Net positions gained vs starting grid (positive = gained, negative = lost).
        overtakes: Number of overtakes made during qualifying.
        fastest_lap: Whether driver set fastest lap in qualifying session.

    Returns:
        Bonus points (can be negative if positions were lost).

    Rules:
        +1 per position gained vs grid
        –1 per position lost vs grid
        +1 per overtake
        +5 for fastest lap in qualifying
    """
    pts = positions_gained + overtakes
    if fastest_lap:
        pts += 5
    return pts


def constructor_qualifying_points(
    driver1_quali_pts: int,
    driver2_quali_pts: int,
    driver1_q2: bool,
    driver2_q2: bool,
    driver1_q3: bool,
    driver2_q3: bool,
) -> int:
    """
    Return total constructor fantasy points for qualifying.

    Args:
        driver1_quali_pts: Base + bonus qualifying points for first driver.
        driver2_quali_pts: Base + bonus qualifying points for second driver.
        driver1_q2: Whether first driver reached Q2.
        driver2_q2: Whether second driver reached Q2.
        driver1_q3: Whether first driver reached Q3.
        driver2_q3: Whether second driver reached Q3.

    Returns:
        Total constructor qualifying fantasy points.

    Rules:
        Sum of both driver points + Q2 bonus (+3 each) + Q3 bonus (+5 each).
    """
    pts = driver1_quali_pts + driver2_quali_pts
    for q2 in (driver1_q2, driver2_q2):
        if q2:
            pts += 3
    for q3 in (driver1_q3, driver2_q3):
        if q3:
            pts += 5
    return pts


# ─── Sprint ────────────────────────────────────────────────────────────────────

def sprint_position_points(position: int | None, dnf: bool = False, dsq: bool = False) -> int:
    """
    Return base fantasy points for a sprint race result.

    Args:
        position: Classified sprint finishing position (1–20), or None.
        dnf: Driver did not finish.
        dsq: Driver was disqualified.

    Returns:
        Fantasy points. Positions 9–20 score 0. DNF / DSQ / NC = –10.
    """
    if dnf or dsq or position is None:
        return -10
    return SPRINT_POINTS.get(position, 0)


def sprint_bonus_points(positions_gained: int, overtakes: int) -> int:
    """
    Return sprint race bonus points. No fastest lap bonus in sprint.

    Args:
        positions_gained: Net positions gained vs grid (positive = gained, negative = lost).
        overtakes: Number of overtakes made during sprint.

    Returns:
        Bonus points (can be negative).

    Rules:
        +1 per position gained
        –1 per position lost
        +1 per overtake
    """
    return positions_gained + overtakes


def sprint_total_points(
    position: int | None,
    positions_gained: int,
    overtakes: int,
    dnf: bool = False,
    dsq: bool = False,
) -> int:
    """
    Return total fantasy points for a sprint race (base + bonuses).

    Args:
        position: Classified sprint finishing position.
        positions_gained: Net positions gained vs grid.
        overtakes: Number of overtakes.
        dnf: Did not finish.
        dsq: Disqualified.

    Returns:
        Total sprint fantasy points.
    """
    base = sprint_position_points(position, dnf, dsq)
    bonus = sprint_bonus_points(positions_gained, overtakes)
    return base + bonus


# ─── Grand Prix Race ───────────────────────────────────────────────────────────

def race_position_points(position: int | None, dnf: bool = False, dsq: bool = False) -> int:
    """
    Return base fantasy points for a Grand Prix race result.

    Args:
        position: Classified finishing position (1–20), or None.
        dnf: Driver did not finish.
        dsq: Driver was disqualified.

    Returns:
        Fantasy points. Positions 11–20 score 0. DNF / DSQ / NC = –20.

    Rules based on F1 Fantasy 2025 scoring table:
        P1=25, P2=18, P3=15, P4=12, P5=10, P6=8, P7=6, P8=4, P9=2, P10=1
    """
    if dnf or dsq or position is None:
        return -20
    return RACE_POINTS.get(position, 0)


def race_bonus_points(
    positions_gained: int,
    overtakes: int,
    fastest_lap: bool = False,
    driver_of_day: bool = False,
) -> int:
    """
    Return Grand Prix race bonus points for a driver.

    Args:
        positions_gained: Net positions gained vs qualifying grid (positive = gained, negative = lost).
        overtakes: Number of overtakes made during the race.
        fastest_lap: Whether driver set the race fastest lap.
        driver_of_day: Whether driver won Driver of the Day vote.

    Returns:
        Bonus points (can be negative if positions were lost).

    Rules:
        +1 per position gained
        –1 per position lost
        +1 per overtake
        +10 fastest lap
        +10 Driver of the Day
    """
    pts = positions_gained + overtakes
    if fastest_lap:
        pts += 10
    if driver_of_day:
        pts += 10
    return pts


def race_total_points(
    position: int | None,
    positions_gained: int,
    overtakes: int,
    fastest_lap: bool = False,
    driver_of_day: bool = False,
    dnf: bool = False,
    dsq: bool = False,
) -> int:
    """
    Return total driver fantasy points for a Grand Prix race.

    Args:
        position: Classified finishing position.
        positions_gained: Net positions gained vs grid.
        overtakes: Number of overtakes.
        fastest_lap: Whether driver set fastest lap.
        driver_of_day: Whether driver won DOTD.
        dnf: Did not finish.
        dsq: Disqualified.

    Returns:
        Total race fantasy points.
    """
    base = race_position_points(position, dnf, dsq)
    bonus = race_bonus_points(positions_gained, overtakes, fastest_lap, driver_of_day)
    return base + bonus


def constructor_race_points(
    driver1_race_pts: int,
    driver2_race_pts: int,
    fastest_pit_stop: bool = False,
    sub_2s_pit: bool = False,
    new_pit_record: bool = False,
    driver1_dsq: bool = False,
    driver2_dsq: bool = False,
) -> int:
    """
    Return total constructor fantasy points for a Grand Prix race.

    Args:
        driver1_race_pts: Total race fantasy points for first driver.
        driver2_race_pts: Total race fantasy points for second driver.
        fastest_pit_stop: Constructor had the fastest pit stop of the race.
        sub_2s_pit: Constructor completed a pit stop under 2.0 seconds.
        new_pit_record: Constructor set a new pit stop record.
        driver1_dsq: First driver was disqualified.
        driver2_dsq: Second driver was disqualified.

    Returns:
        Total constructor race fantasy points.

    Rules:
        Sum of both drivers + fastest pit +5 + sub-2s pit +20 + new record +15 additional
        –20 per DSQ driver
    """
    pts = driver1_race_pts + driver2_race_pts
    if fastest_pit_stop:
        pts += 5
    if sub_2s_pit:
        pts += 20
    if new_pit_record:
        pts += 15
    if driver1_dsq:
        pts -= 20
    if driver2_dsq:
        pts -= 20
    return pts


# ─── Chip Effects ──────────────────────────────────────────────────────────────

def apply_drs_boost(total_points: int | float) -> float:
    """
    Apply Regular DRS Boost chip: selected driver total × 2.
    Doubles negatives as well.

    Args:
        total_points: Driver's total fantasy points for the race weekend.

    Returns:
        Points after DRS Boost (2× multiplier).
    """
    return total_points * 2


def apply_extra_drs_boost(total_points: int | float) -> float:
    """
    Apply Extra DRS Boost chip: selected driver total × 3.
    Triples negatives as well.

    Args:
        total_points: Driver's total fantasy points for the race weekend.

    Returns:
        Points after Extra DRS Boost (3× multiplier).
    """
    return total_points * 3


def apply_no_negative(total_points: int | float) -> float:
    """
    Apply No Negative chip: floor all driver/constructor totals to 0 if negative.

    Args:
        total_points: Driver or constructor total fantasy points.

    Returns:
        max(0, total_points) — negatives become 0.
    """
    return max(0.0, float(total_points))


def apply_autopilot(driver_points_list: list[int | float]) -> float:
    """
    Apply Autopilot chip: system applies 2× to the highest-scoring driver post-race.

    Args:
        driver_points_list: List of all five drivers' fantasy points totals.

    Returns:
        The total after 2× is applied to the highest scorer (replaces their raw points).
    """
    if not driver_points_list:
        return 0.0
    best = max(driver_points_list)
    total = sum(driver_points_list) - best + (best * 2)
    return float(total)
