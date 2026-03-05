"""
Unit tests for backend/core/scoring.py

All functions are pure — no DB, no fixtures needed.
Tests mirror the exact scoring rules from the F1 Fantasy 2025 ruleset.
"""

import pytest
from backend.core.scoring import (
    qualifying_position_points,
    qualifying_bonus_points,
    constructor_qualifying_points,
    sprint_position_points,
    sprint_bonus_points,
    sprint_total_points,
    race_position_points,
    race_bonus_points,
    race_total_points,
    constructor_race_points,
    apply_drs_boost,
    apply_extra_drs_boost,
    apply_no_negative,
    apply_autopilot,
)


# ── Qualifying position points ─────────────────────────────────────────────────

class TestQualifyingPositionPoints:
    def test_pole_position(self):
        assert qualifying_position_points(1) == 10

    def test_p10(self):
        assert qualifying_position_points(10) == 1

    def test_p11_scores_zero(self):
        assert qualifying_position_points(11) == 0

    def test_p20_scores_zero(self):
        assert qualifying_position_points(20) == 0

    def test_none_position(self):
        assert qualifying_position_points(None) == -5

    def test_dsq(self):
        assert qualifying_position_points(1, dsq=True) == -5

    def test_no_time(self):
        assert qualifying_position_points(5, no_time=True) == -5

    def test_full_table(self):
        expected = {1: 10, 2: 9, 3: 8, 4: 7, 5: 6, 6: 5, 7: 4, 8: 3, 9: 2, 10: 1}
        for pos, pts in expected.items():
            assert qualifying_position_points(pos) == pts


class TestQualifyingBonusPoints:
    def test_positions_gained(self):
        assert qualifying_bonus_points(3, 0) == 3

    def test_positions_lost(self):
        assert qualifying_bonus_points(-2, 0) == -2

    def test_overtakes(self):
        assert qualifying_bonus_points(0, 4) == 4

    def test_fastest_lap_bonus(self):
        assert qualifying_bonus_points(0, 0, fastest_lap=True) == 5

    def test_combined(self):
        assert qualifying_bonus_points(2, 1, fastest_lap=True) == 8


class TestConstructorQualifyingPoints:
    def test_sums_both_drivers(self):
        pts = constructor_qualifying_points(10, 9, False, False, False, False)
        assert pts == 19

    def test_q2_bonus_per_driver(self):
        pts = constructor_qualifying_points(0, 0, True, True, False, False)
        assert pts == 6  # 2 × +3

    def test_q3_bonus_per_driver(self):
        pts = constructor_qualifying_points(0, 0, False, False, True, True)
        assert pts == 10  # 2 × +5

    def test_full_q3_weekend(self):
        # Both reach Q3: 10+9 base + 3+3 Q2 + 5+5 Q3 = 35
        pts = constructor_qualifying_points(10, 9, True, True, True, True)
        assert pts == 35


# ── Sprint scoring ─────────────────────────────────────────────────────────────

class TestSprintPositionPoints:
    def test_p1(self):
        assert sprint_position_points(1) == 8

    def test_p8(self):
        assert sprint_position_points(8) == 1

    def test_p9_scores_zero(self):
        assert sprint_position_points(9) == 0

    def test_dnf(self):
        assert sprint_position_points(1, dnf=True) == -10

    def test_dsq(self):
        assert sprint_position_points(3, dsq=True) == -10

    def test_none(self):
        assert sprint_position_points(None) == -10


class TestSprintBonusPoints:
    def test_gained(self):
        assert sprint_bonus_points(5, 0) == 5

    def test_lost(self):
        assert sprint_bonus_points(-3, 0) == -3

    def test_overtakes(self):
        assert sprint_bonus_points(0, 2) == 2


class TestSprintTotalPoints:
    def test_p1_with_bonus(self):
        # P1=8, +2 gained, +1 overtake = 11
        assert sprint_total_points(1, 2, 1) == 11

    def test_dnf_with_bonus(self):
        # DNF=-10, bonus not erased
        assert sprint_total_points(1, 5, 2, dnf=True) == -3


# ── Race scoring ───────────────────────────────────────────────────────────────

class TestRacePositionPoints:
    def test_p1(self):
        assert race_position_points(1) == 25

    def test_p2(self):
        assert race_position_points(2) == 18

    def test_p10(self):
        assert race_position_points(10) == 1

    def test_p11_scores_zero(self):
        assert race_position_points(11) == 0

    def test_dnf(self):
        assert race_position_points(1, dnf=True) == -20

    def test_dsq(self):
        assert race_position_points(5, dsq=True) == -20

    def test_none(self):
        assert race_position_points(None) == -20

    def test_full_table(self):
        expected = {1: 25, 2: 18, 3: 15, 4: 12, 5: 10, 6: 8, 7: 6, 8: 4, 9: 2, 10: 1}
        for pos, pts in expected.items():
            assert race_position_points(pos) == pts


class TestRaceBonusPoints:
    def test_fastest_lap(self):
        assert race_bonus_points(0, 0, fastest_lap=True) == 10

    def test_driver_of_day(self):
        assert race_bonus_points(0, 0, driver_of_day=True) == 10

    def test_both_bonuses(self):
        assert race_bonus_points(0, 0, fastest_lap=True, driver_of_day=True) == 20

    def test_positions_gained(self):
        assert race_bonus_points(5, 3) == 8

    def test_full_monster_race(self):
        # +5 gained, +3 overtakes, fastest lap, DOTD = 28
        assert race_bonus_points(5, 3, fastest_lap=True, driver_of_day=True) == 28


class TestRaceTotalPoints:
    def test_p1_winner(self):
        # P1=25, +1 gained, fastest_lap = 36
        assert race_total_points(1, 1, 0, fastest_lap=True) == 36

    def test_dnf_with_bonuses(self):
        # DNF=-20, +3 gained, +2 overtakes, DOTD = -5
        assert race_total_points(None, 3, 2, driver_of_day=True, dnf=True) == -5


class TestConstructorRacePoints:
    def test_sums_both_drivers(self):
        assert constructor_race_points(25, 18) == 43

    def test_fastest_pit(self):
        assert constructor_race_points(10, 10, fastest_pit_stop=True) == 25

    def test_sub_2s_pit(self):
        assert constructor_race_points(10, 10, sub_2s_pit=True) == 40

    def test_new_pit_record(self):
        # new record is +15 ON TOP of the sub-2s (or fastest) that triggered it
        assert constructor_race_points(10, 10, sub_2s_pit=True, new_pit_record=True) == 55

    def test_dsq_penalty(self):
        assert constructor_race_points(25, 18, driver1_dsq=True) == 23

    def test_both_dsq(self):
        assert constructor_race_points(25, 18, driver1_dsq=True, driver2_dsq=True) == 3


# ── Chip effects ───────────────────────────────────────────────────────────────

class TestChipEffects:
    def test_drs_boost_doubles(self):
        assert apply_drs_boost(30) == 60

    def test_drs_boost_doubles_negatives(self):
        assert apply_drs_boost(-10) == -20

    def test_extra_drs_triples(self):
        assert apply_extra_drs_boost(20) == 60

    def test_extra_drs_triples_negatives(self):
        assert apply_extra_drs_boost(-5) == -15

    def test_no_negative_floors_to_zero(self):
        assert apply_no_negative(-15) == 0

    def test_no_negative_preserves_positive(self):
        assert apply_no_negative(30) == 30

    def test_no_negative_zero(self):
        assert apply_no_negative(0) == 0

    def test_autopilot_doubles_highest(self):
        # [10, 20, 30, 5, 15] — highest=30 → sum - 30 + 60 = 110
        assert apply_autopilot([10, 20, 30, 5, 15]) == 110

    def test_autopilot_empty_list(self):
        assert apply_autopilot([]) == 0

    def test_autopilot_single_driver(self):
        assert apply_autopilot([25]) == 50

    def test_autopilot_with_negatives(self):
        # [-10, 20] — highest=20 → -10 + 20 + 20 = 30
        assert apply_autopilot([-10, 20]) == 30
