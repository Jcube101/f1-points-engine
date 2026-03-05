"""
Unit tests for backend/core/expected_points.py

All functions are pure — no DB, no fixtures needed.
"""

import pytest
from backend.core.expected_points import (
    weighted_average,
    circuit_type_multiplier,
    teammate_gap_factor,
    calculate_xp,
    xp_per_million,
)


class TestWeightedAverage:
    def test_empty_returns_zero(self):
        assert weighted_average([]) == 0.0

    def test_single_entry_returns_itself(self):
        assert weighted_average([30.0]) == 30.0

    def test_two_entries_weighted_40_60(self):
        # [20, 30] → 20*0.4 + 30*0.6 = 26.0
        result = weighted_average([20.0, 30.0])
        assert abs(result - 26.0) < 0.001

    def test_three_entries_weighted_20_30_50(self):
        # [10, 20, 30] → 10*0.2 + 20*0.3 + 30*0.5 = 23.0
        result = weighted_average([10.0, 20.0, 30.0])
        assert abs(result - 23.0) < 0.001

    def test_more_than_three_uses_last_three(self):
        # [5, 10, 20, 30] — only last 3 used: [10, 20, 30] → 23.0
        result = weighted_average([5.0, 10.0, 20.0, 30.0])
        assert abs(result - 23.0) < 0.001

    def test_most_recent_weighted_highest(self):
        # Recent spike should dominate: [5, 5, 50]
        # 5*0.2 + 5*0.3 + 50*0.5 = 1 + 1.5 + 25 = 27.5
        result = weighted_average([5.0, 5.0, 50.0])
        assert abs(result - 27.5) < 0.001

    def test_all_same(self):
        assert weighted_average([20.0, 20.0, 20.0]) == 20.0


class TestCircuitTypeMultiplier:
    def test_ver_power_boost(self):
        # VER has 1.10 on power circuits
        assert circuit_type_multiplier("VER", "power") == 1.10

    def test_lec_street_boost(self):
        # LEC has 1.15 on street circuits
        assert circuit_type_multiplier("LEC", "street") == 1.15

    def test_ver_street_slight_penalty(self):
        # VER has 0.95 on street circuits
        assert circuit_type_multiplier("VER", "street") == 0.95

    def test_unknown_driver_returns_one(self):
        assert circuit_type_multiplier("XXX", "power") == 1.0

    def test_unknown_circuit_returns_one(self):
        assert circuit_type_multiplier("VER", "unknown_type") == 1.0

    def test_known_neutral_driver(self):
        # PIA has 1.0 everywhere
        assert circuit_type_multiplier("PIA", "street") == 1.0


class TestTeammateGapFactor:
    def test_empty_lists_return_neutral(self):
        assert teammate_gap_factor([], []) == 1.0

    def test_driver_better_than_teammate_gets_boost(self):
        # driver qualifies P1, teammate P5 — driver is significantly better
        factor = teammate_gap_factor([1, 1, 1], [5, 5, 5])
        assert factor > 1.0

    def test_driver_worse_than_teammate_gets_penalty(self):
        # driver qualifies P10, teammate P5 — driver consistently behind
        factor = teammate_gap_factor([10, 10, 10], [5, 5, 5])
        assert factor < 1.0

    def test_equal_quali_returns_neutral(self):
        factor = teammate_gap_factor([3, 3, 3], [3, 3, 3])
        assert factor == 1.0

    def test_boost_capped_at_5_percent(self):
        # Even massive gap shouldn't exceed 1.05
        factor = teammate_gap_factor([1, 1, 1], [20, 20, 20])
        assert factor <= 1.05

    def test_penalty_capped_at_3_percent(self):
        # Even massive reverse gap shouldn't go below 0.97
        factor = teammate_gap_factor([20, 20, 20], [1, 1, 1])
        assert factor >= 0.97


class TestCalculateXp:
    def test_no_race_history_returns_zero(self):
        result = calculate_xp([], "VER", "power")
        assert result == 0.0

    def test_applies_circuit_multiplier(self):
        # VER, 3 equal races of 30pts, power circuit (1.10)
        # w_avg = 30, xP = 30 * 1.10 = 33.0
        result = calculate_xp([30.0, 30.0, 30.0], "VER", "power")
        assert abs(result - 33.0) < 0.1

    def test_neutral_driver_circuit(self):
        # PIA on balanced (1.0) — result equals weighted avg
        result = calculate_xp([20.0, 20.0, 20.0], "PIA", "balanced")
        assert abs(result - 20.0) < 0.1

    def test_lec_street_boost(self):
        # LEC street multiplier 1.15, 3 races of 20pts
        result = calculate_xp([20.0, 20.0, 20.0], "LEC", "street")
        assert abs(result - 23.0) < 0.1

    def test_with_teammate_gap(self):
        # provide quali positions — factor should shift result
        no_gap = calculate_xp([20.0] * 3, "PIA", "balanced")
        with_gap = calculate_xp(
            [20.0] * 3, "PIA", "balanced",
            driver_quali_positions=[1, 1, 1],
            teammate_quali_positions=[5, 5, 5],
        )
        assert with_gap > no_gap


class TestXpPerMillion:
    def test_zero_price_returns_zero(self):
        assert xp_per_million(30.0, 0) == 0.0

    def test_negative_price_returns_zero(self):
        assert xp_per_million(30.0, -1) == 0.0

    def test_standard_calculation(self):
        # 30 xP / (15_000_000 / 1_000_000) = 30 / 15 = 2.0
        result = xp_per_million(30.0, 15_000_000)
        assert abs(result - 2.0) < 0.001

    def test_higher_price_lower_value(self):
        cheap = xp_per_million(20.0, 8_000_000)
        expensive = xp_per_million(20.0, 30_000_000)
        assert cheap > expensive
