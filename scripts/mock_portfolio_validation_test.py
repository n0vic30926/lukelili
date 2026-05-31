#!/usr/bin/env python3
"""Offline tests for local portfolio validation rules."""

from validate_portfolio import validate_portfolio_data


def _base_portfolio():
    return {
        "user_profile": {"investor_type": "example", "risk_tolerance": "moderate"},
        "cash": {"currency": "CNY", "amount": 1000},
        "risk_rules": {},
        "watchlist": [],
        "holdings": [
            {
                "code": "EXAMPLE",
                "name": "Example Holding",
                "type": "example",
                "strategy_type": "dca",
                "cost_basis": 100,
                "shares": 10,
                "etf_profile": {
                    "tracking_history": [
                        {"date": "2026-01-01", "etf_return_pct": 1.0, "benchmark_return_pct": 0.8}
                    ],
                    "dividend_history": [
                        {"ex_date": "2025-12-31", "amount": 0.02}
                    ],
                },
            }
        ],
    }


def run_valid_history_test():
    errors = validate_portfolio_data(_base_portfolio())
    if errors:
        raise AssertionError(f"Expected valid portfolio history fields, got: {errors}")


def run_invalid_history_test():
    portfolio = _base_portfolio()
    profile = portfolio["holdings"][0]["etf_profile"]
    profile["tracking_history"][0]["etf_return_pct"] = "bad"
    profile["dividend_history"][0]["amount"] = "bad"
    errors = validate_portfolio_data(portfolio)
    joined = "\n".join(errors)
    if "tracking_history[0].etf_return_pct must be a number" not in joined:
        raise AssertionError("Expected invalid tracking history value to be reported")
    if "dividend_history[0].amount must be a number" not in joined:
        raise AssertionError("Expected invalid dividend history value to be reported")


def main():
    run_valid_history_test()
    run_invalid_history_test()
    print("Mock portfolio validation test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
