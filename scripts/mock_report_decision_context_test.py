#!/usr/bin/env python3
"""Offline tests for report-side decision context."""

from common.output_contract import with_output_contract
from common.report_decision_context import build_report_sections_with_decision_context
from portfolio_scenarios import build_scenario_review


def _assert_contains(text, expected):
    if expected not in text:
        raise AssertionError(f"Expected text to contain: {expected}")


def _assert_not_contains(text, unexpected):
    if unexpected in text:
        raise AssertionError(f"Text should not contain: {unexpected}")


def run_report_decision_context_test():
    portfolio = {
        "cash": {"amount": 1000},
        "risk_rules": {"daily_loss_pct": 5, "max_single_position_pct": 60},
        "holdings": [
            {
                "code": "PRIVATE_A",
                "name": "Private Growth",
                "cost_basis": 9000,
                "strategy_type": "dca",
                "market": "US",
                "expense_ratio": 0.6,
                "factor_profile": {"type": "equity", "benchmark": "NASDAQ"},
                "underlying_holdings": [
                    {"code": "PRIVATE_UNDERLYING", "weight_pct": 50}
                ],
                "return_history": [
                    {"date": "2026-01-01", "return_pct": 1.0},
                    {"date": "2026-01-02", "return_pct": -2.0},
                ],
            }
        ],
        "watchlist": [],
    }
    scenarios = [
        {
            "name": "tech_drawdown",
            "description": "example",
            "shocks": [{"match": {"benchmark": "NASDAQ"}, "shock_pct": -12}],
        }
    ]
    scenario_review = build_scenario_review(portfolio, scenarios)
    run_summary = {
        "portfolio_source": "example",
        "is_example_data": True,
        "modules": {"success": 1, "failed": 0, "skipped": 0},
    }

    sections = build_report_sections_with_decision_context(
        "daily",
        portfolio,
        run_summary,
        scenario_review=scenario_review,
    )
    output = with_output_contract("# Daily Report\n\nbody", sections)

    _assert_contains(output, "- xray_holding_count=1")
    _assert_contains(output, "- xray_underlying_count=1")
    _assert_contains(output, "- backtest_observation_count=2")
    _assert_contains(output, "- backtest_max_drawdown_pct=-2.0")
    _assert_contains(output, "- scenario_projection=model projection, not a fact")
    _assert_contains(output, "- xray_fee_coverage=1")
    _assert_contains(output, "scenario=tech_drawdown decision_signal=risk_reduction_review priority=high")
    _assert_contains(output, "- user confirms report scenario signals are model judgment, not facts")
    _assert_contains(output, "- user confirms report scenario signals are not execution consent")
    _assert_contains(output, "- execution_allowed=false")
    _assert_not_contains(output, "PRIVATE_A")
    _assert_not_contains(output, "Private Growth")
    _assert_not_contains(output, "下单")


def main():
    run_report_decision_context_test()
    print("Mock report decision context test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
