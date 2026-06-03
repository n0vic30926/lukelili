#!/usr/bin/env python3
"""Offline tests for anonymized portfolio backtest metrics."""

from portfolio_backtest import build_portfolio_backtest, format_portfolio_backtest


def _assert_contains(text, expected):
    if expected not in text:
        raise AssertionError(f"Expected text to contain: {expected}")


def _assert_not_contains(text, unexpected):
    if unexpected in text:
        raise AssertionError(f"Text should not contain: {unexpected}")


def run_portfolio_backtest_test():
    portfolio = {
        "holdings": [
            {
                "code": "PRIVATE_A",
                "name": "Private Growth",
                "cost_basis": 600,
                "return_history": [
                    {"date": "2026-01-01", "return_pct": 10},
                    {"date": "2026-01-02", "return_pct": -20},
                    {"date": "2026-01-03", "return_pct": 5},
                ],
            },
            {
                "code": "PRIVATE_B",
                "name": "Private Hedge",
                "cost_basis": 400,
                "return_history": [
                    {"date": "2026-01-01", "return_pct": 0},
                    {"date": "2026-01-02", "return_pct": -10},
                    {"date": "2026-01-03", "return_pct": 0},
                ],
            },
            {
                "code": "PRIVATE_C",
                "name": "Private Missing",
                "cost_basis": 100,
            },
        ],
    }

    backtest = build_portfolio_backtest(portfolio)
    if backtest["covered_holding_count"] != 2:
        raise AssertionError(f"Expected two covered holdings: {backtest}")
    if backtest["missing_history_refs"] != ["holding_3"]:
        raise AssertionError(f"Expected missing history ref: {backtest}")
    if backtest["observation_count"] != 3:
        raise AssertionError(f"Expected three observations: {backtest}")
    if backtest["period_return_pct"] != -8.3:
        raise AssertionError(f"Unexpected period return: {backtest}")
    if backtest["max_drawdown_pct"] != -16.0:
        raise AssertionError(f"Unexpected max drawdown: {backtest}")
    if backtest["annualized_volatility_pct"] != 154.6:
        raise AssertionError(f"Unexpected volatility: {backtest}")
    if backtest["daily_returns"][1]["portfolio_return_pct"] != -16.0:
        raise AssertionError(f"Unexpected daily return series: {backtest}")
    if "historical_data_missing" not in [item["type"] for item in backtest["warnings"]]:
        raise AssertionError(f"Expected missing-history warning: {backtest}")

    output = format_portfolio_backtest(backtest)
    _assert_contains(output, "# Portfolio Backtest")
    _assert_contains(output, "- period_return_pct=-8.3")
    _assert_contains(output, "- max_drawdown_pct=-16.0")
    _assert_contains(output, "- annualized_volatility_pct=154.6")
    _assert_contains(output, "- missing_history_refs=holding_3")
    _assert_contains(output, "decision support only")
    for unexpected in ["PRIVATE_A", "Private Growth", "买入", "卖出", "下单"]:
        _assert_not_contains(output, unexpected)


def main():
    run_portfolio_backtest_test()
    print("Mock portfolio backtest test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
