#!/usr/bin/env python3
"""Offline tests for anonymized portfolio x-ray review."""

from portfolio_xray import build_portfolio_xray, format_portfolio_xray


def _assert_contains(text, expected):
    if expected not in text:
        raise AssertionError(f"Expected text to contain: {expected}")


def _assert_not_contains(text, unexpected):
    if unexpected in text:
        raise AssertionError(f"Text should not contain: {unexpected}")


def run_portfolio_xray_test():
    portfolio = {
        "cash": {"amount": 500},
        "risk_rules": {"max_single_position_pct": 70},
        "holdings": [
            {
                "code": "PRIVATE_A",
                "name": "Private Growth Fund A",
                "cost_basis": 1000,
                "strategy_type": "dca",
                "market": "us_stock",
                "expense_ratio": 0.2,
                "factor_profile": {"type": "growth", "benchmark": "NASDAQ"},
                "underlying_holdings": [
                    {"code": "PRIVATE_ALPHA", "name": "Private Alpha", "weight_pct": 60}
                ],
            },
            {
                "code": "PRIVATE_B",
                "name": "Private Growth Fund B",
                "cost_basis": 500,
                "strategy_type": "trial",
                "market": "us_stock",
                "expense_ratio": 0.5,
                "factor_profile": {"type": "growth", "benchmark": "NASDAQ"},
                "underlying_holdings": [
                    {"code": "PRIVATE_ALPHA", "name": "Private Alpha", "weight_pct": 40}
                ],
            },
            {
                "code": "PRIVATE_C",
                "name": "Private Income Fund C",
                "cost_basis": 500,
                "strategy_type": "watch",
                "market": "bond",
                "factor_profile": {"type": "income", "benchmark": "BOND"},
            },
        ],
    }

    xray = build_portfolio_xray(portfolio)
    if xray["holding_count"] != 3:
        raise AssertionError(f"Unexpected holding_count: {xray}")
    if xray["allocation"]["cash_pct"] != 20.0:
        raise AssertionError(f"Unexpected allocation: {xray}")
    if xray["overlap_clusters"][0]["holding_refs"] != ["holding_1", "holding_2"]:
        raise AssertionError(f"Expected anonymized overlap cluster: {xray}")
    if xray["fee_review"]["weighted_expense_ratio_pct"] != 0.3:
        raise AssertionError(f"Unexpected weighted fee review: {xray}")
    if xray["fee_review"]["missing_fee_refs"] != ["holding_3"]:
        raise AssertionError(f"Expected missing fee ref: {xray}")
    if "fee_data_missing" not in [warning["type"] for warning in xray["warnings"]]:
        raise AssertionError(f"Expected fee-data warning: {xray}")
    if xray["stock_intersection"]["underlying_count"] != 1:
        raise AssertionError(f"Expected stock intersection: {xray}")
    if "underlying_overlap_review_required" not in [warning["type"] for warning in xray["warnings"]]:
        raise AssertionError(f"Expected underlying overlap warning: {xray}")

    rendered = format_portfolio_xray(xray)
    for expected in [
        "# Portfolio X-Ray",
        "## Allocation",
        "## Overlap Review",
        "## Fee Review",
        "## Stock Intersection",
        "underlying_count=1",
        "overlap cluster",
        "weighted_expense_ratio_pct=0.3",
        "fee_data_missing",
        "decision support only",
    ]:
        _assert_contains(rendered, expected)
    for unexpected in ["PRIVATE_A", "Private Growth", "买入", "卖出", "下单"]:
        _assert_not_contains(rendered, unexpected)


def main():
    run_portfolio_xray_test()
    print("Mock portfolio x-ray test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
