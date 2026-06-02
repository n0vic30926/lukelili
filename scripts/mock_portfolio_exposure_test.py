#!/usr/bin/env python3
"""Offline tests for anonymized local portfolio exposure checks."""

from common.portfolio_exposure import summarize_portfolio_exposure


def _assert_contains(text, expected):
    if expected not in text:
        raise AssertionError(f"Expected text to contain: {expected}")


def _assert_not_contains(text, unexpected):
    if unexpected in text:
        raise AssertionError(f"Text should not contain: {unexpected}")


def run_portfolio_exposure_test():
    portfolio = {
        "cash": {"amount": 500},
        "risk_rules": {"max_single_position_pct": 50},
        "holdings": [
            {
                "code": "PRIVATE_A",
                "name": "Private Holding A",
                "cost_basis": 1400,
                "strategy_type": "dca",
                "market": "us_stock",
                "factor_profile": {"type": "qdii_us_equity"},
            },
            {
                "code": "PRIVATE_B",
                "name": "Private Holding B",
                "cost_basis": 100,
                "strategy_type": "trial",
                "market": "a_share",
                "factor_profile": {"type": "a_share_ai"},
            },
        ],
    }
    summary = summarize_portfolio_exposure(portfolio)
    if summary["holding_count"] != 2:
        raise AssertionError(f"Unexpected holding_count: {summary}")
    if summary["cash_pct"] != 25.0:
        raise AssertionError(f"Unexpected cash_pct: {summary}")
    if summary["invested_pct"] != 75.0:
        raise AssertionError(f"Unexpected invested_pct: {summary}")
    if summary["max_position_pct"] != 70.0:
        raise AssertionError(f"Unexpected max_position_pct: {summary}")
    if summary["strategy_counts"] != {"dca": 1, "trial": 1}:
        raise AssertionError(f"Unexpected strategy_counts: {summary}")
    if summary["factor_counts"] != {"a_share_ai": 1, "qdii_us_equity": 1}:
        raise AssertionError(f"Unexpected factor_counts: {summary}")
    if summary["market_counts"] != {"a_share": 1, "us_stock": 1}:
        raise AssertionError(f"Unexpected market_counts: {summary}")
    warnings = summary["warnings"]
    if warnings[0]["type"] != "single_position_exceeds_rule":
        raise AssertionError(f"Expected single position warning: {warnings}")
    if warnings[0]["holding_ref"] != "holding_1":
        raise AssertionError(f"Expected anonymized holding ref: {warnings}")

    rendered = str(summary)
    _assert_contains(rendered, "holding_1")
    _assert_not_contains(rendered, "PRIVATE_A")
    _assert_not_contains(rendered, "Private Holding")
    _assert_not_contains(rendered, "买入")
    _assert_not_contains(rendered, "卖出")
    _assert_not_contains(rendered, "自动交易")


def main():
    run_portfolio_exposure_test()
    print("Mock portfolio exposure test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
