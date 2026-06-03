#!/usr/bin/env python3
"""Offline tests for decision signal ranking."""

from common.signal_ranking import format_ranked_signals, rank_scenario_signals


def _assert_contains(text, expected):
    if expected not in text:
        raise AssertionError(f"Expected text to contain: {expected}")


def run_signal_ranking_test():
    signals = [
        {
            "scenario": "rebound",
            "signal": "hold_or_add_review",
            "portfolio_impact_pct": 3.0,
            "risk_flags": [],
            "requires_user_confirmation": True,
        },
        {
            "scenario": "drawdown",
            "signal": "risk_reduction_review",
            "portfolio_impact_pct": -7.5,
            "risk_flags": ["scenario_loss_exceeds_daily_loss_rule"],
            "requires_user_confirmation": True,
        },
        {
            "scenario": "mild",
            "signal": "hold_review",
            "portfolio_impact_pct": -1.0,
            "risk_flags": [],
            "requires_user_confirmation": True,
        },
    ]

    ranked = rank_scenario_signals(signals)
    if [item["scenario"] for item in ranked] != ["drawdown", "rebound", "mild"]:
        raise AssertionError(f"Unexpected ranked order: {ranked}")
    if ranked[0]["priority"] != "high":
        raise AssertionError(f"Expected high priority risk signal: {ranked[0]}")
    if ranked[0]["score"] <= ranked[1]["score"]:
        raise AssertionError(f"Expected drawdown score to lead: {ranked}")

    output = format_ranked_signals(ranked)
    _assert_contains(output, "scenario=drawdown")
    _assert_contains(output, "priority=high")
    _assert_contains(output, "signal=risk_reduction_review")
    _assert_contains(output, "score=")


def main():
    run_signal_ranking_test()
    print("Mock signal ranking test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
