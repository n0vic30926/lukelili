#!/usr/bin/env python3
"""Offline tests for anonymized portfolio stock intersection."""

from portfolio_intersection import build_stock_intersection, format_stock_intersection


def _assert_contains(text, expected):
    if expected not in text:
        raise AssertionError(f"Expected text to contain: {expected}")


def _assert_not_contains(text, unexpected):
    if unexpected in text:
        raise AssertionError(f"Text should not contain: {unexpected}")


def run_portfolio_intersection_test():
    portfolio = {
        "cash": {"amount": 1000},
        "risk_rules": {"max_underlying_position_pct": 25},
        "holdings": [
            {
                "code": "PRIVATE_FUND_A",
                "name": "Private Fund A",
                "type": "mutual_fund",
                "cost_basis": 6000,
                "underlying_holdings": [
                    {"code": "PRIVATE_ALPHA", "name": "Private Alpha", "weight_pct": 50},
                    {"code": "PRIVATE_BETA", "name": "Private Beta", "weight_pct": 20},
                ],
            },
            {
                "code": "PRIVATE_FUND_B",
                "name": "Private Fund B",
                "type": "etf",
                "cost_basis": 3000,
                "underlying_holdings": [
                    {"code": "PRIVATE_ALPHA", "name": "Private Alpha", "weight_pct": 40},
                    {"code": "PRIVATE_GAMMA", "name": "Private Gamma", "weight_pct": 30},
                ],
            },
            {
                "code": "PRIVATE_ALPHA",
                "name": "Private Alpha Direct",
                "type": "stock",
                "cost_basis": 1000,
            },
        ],
    }

    matrix = build_stock_intersection(portfolio)
    if matrix["underlying_count"] != 3:
        raise AssertionError(f"Unexpected underlying count: {matrix}")
    if matrix["covered_holding_count"] != 3:
        raise AssertionError(f"Unexpected coverage count: {matrix}")
    if matrix["top_underlyings"][0]["underlying_ref"] != "underlying_1":
        raise AssertionError(f"Unexpected top underlying ref: {matrix}")
    if matrix["top_underlyings"][0]["portfolio_pct"] != 47.3:
        raise AssertionError(f"Unexpected top concentration: {matrix}")
    if matrix["top_underlyings"][0]["source_holding_refs"] != ["holding_1", "holding_2", "holding_3"]:
        raise AssertionError(f"Expected direct and indirect sources: {matrix}")
    if "underlying_concentration_exceeds_rule" not in [item["type"] for item in matrix["warnings"]]:
        raise AssertionError(f"Expected concentration warning: {matrix}")

    output = format_stock_intersection(matrix)
    _assert_contains(output, "# Portfolio Stock Intersection")
    _assert_contains(output, "- underlying_count=3")
    _assert_contains(output, "underlying_ref=underlying_1 portfolio_pct=47.3")
    _assert_contains(output, "source_holding_refs=holding_1,holding_2,holding_3")
    _assert_contains(output, "underlying_concentration_exceeds_rule")
    _assert_contains(output, "decision support only")
    for unexpected in [
        "PRIVATE_FUND_A",
        "PRIVATE_ALPHA",
        "Private Alpha",
        "Private Fund",
        "买入",
        "卖出",
        "下单",
    ]:
        _assert_not_contains(output, unexpected)

    researched_portfolio = {
        "cash": {"amount": 0},
        "holdings": [
            {
                "code": "sh513100",
                "name": "Private ETF",
                "type": "etf",
                "cost_basis": 1000,
            }
        ],
    }
    researched = build_stock_intersection(
        researched_portfolio,
        external_underlying_holdings_by_code={
            "513100": [
                {"code": "PRIVATE_RESEARCHED_A", "weight_pct": 60},
                {"code": "PRIVATE_RESEARCHED_B", "weight_pct": 25},
            ]
        },
    )
    if researched["underlying_count"] != 2:
        raise AssertionError(f"Expected researched holdings to feed intersection: {researched}")
    researched_output = format_stock_intersection(researched)
    _assert_contains(researched_output, "underlying_ref=underlying_1 portfolio_pct=60.0")
    _assert_not_contains(researched_output, "PRIVATE_RESEARCHED")
    _assert_not_contains(researched_output, "Private ETF")


def main():
    run_portfolio_intersection_test()
    print("Mock portfolio intersection test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
