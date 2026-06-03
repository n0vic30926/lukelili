#!/usr/bin/env python3
"""Offline tests for hypothetical portfolio scenario review."""

from portfolio_scenarios import build_scenario_review, format_scenario_review


def _assert_contains(text, expected):
    if expected not in text:
        raise AssertionError(f"Expected text to contain: {expected}")


def _assert_not_contains(text, unexpected):
    if unexpected in text:
        raise AssertionError(f"Text should not contain: {unexpected}")


def run_portfolio_scenarios_test():
    portfolio = {
        "cash": {"amount": 500},
        "risk_rules": {"daily_loss_pct": 6, "max_single_position_pct": 70},
        "holdings": [
            {
                "code": "PRIVATE_A",
                "name": "Private Growth Fund A",
                "cost_basis": 1000,
                "strategy_type": "dca",
                "market": "us_stock",
                "factor_profile": {"type": "growth", "benchmark": "NASDAQ"},
            },
            {
                "code": "PRIVATE_B",
                "name": "Private Bond Fund B",
                "cost_basis": 500,
                "strategy_type": "watch",
                "market": "bond",
                "factor_profile": {"type": "income", "benchmark": "BOND"},
            },
        ],
    }
    scenarios = [
        {
            "name": "growth_drawdown",
            "description": "Hypothetical growth selloff",
            "shocks": [
                {"match": {"market": "us_stock"}, "shock_pct": -12},
                {"match": {"factor_type": "income"}, "shock_pct": -2},
            ],
        },
        {
            "name": "benchmark_rebound",
            "description": "Hypothetical benchmark rebound",
            "shocks": [
                {"match": {"benchmark": "NASDAQ"}, "shock_pct": 5},
            ],
        },
    ]

    review = build_scenario_review(portfolio, scenarios)
    if review["scenario_count"] != 2:
        raise AssertionError(f"Unexpected scenario count: {review}")
    first = review["scenarios"][0]
    if first["portfolio_impact_pct"] != -6.5:
        raise AssertionError(f"Unexpected first scenario impact: {first}")
    if first["holding_impacts"][0]["holding_ref"] != "holding_1":
        raise AssertionError(f"Expected anonymized holding ref: {first}")
    if first["holding_impacts"][0]["shock_pct"] != -12.0:
        raise AssertionError(f"Unexpected holding shock: {first}")
    if first["risk_flags"][0]["type"] != "scenario_loss_exceeds_daily_loss_rule":
        raise AssertionError(f"Expected risk rule flag: {first}")
    if review["boundary"]["projection"] != "model projection, not a fact":
        raise AssertionError(f"Expected projection boundary: {review}")
    if first["decision_signals"][0]["signal"] != "risk_reduction_review":
        raise AssertionError(f"Expected review signal: {first}")

    rendered = format_scenario_review(review)
    for expected in [
        "# Portfolio Scenario Review",
        "growth_drawdown",
        "portfolio_impact_pct=-6.5",
        "scenario_loss_exceeds_daily_loss_rule",
        "decision_signal=risk_reduction_review",
        "model projection, not a fact",
        "decision support only",
        "requires_user_confirmation=true",
        "execution_allowed=false",
    ]:
        _assert_contains(rendered, expected)
    for unexpected in ["PRIVATE_A", "Private Growth", "下单"]:
        _assert_not_contains(rendered, unexpected)


def main():
    run_portfolio_scenarios_test()
    print("Mock portfolio scenarios test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
