#!/usr/bin/env python3
"""Offline tests for stricter local portfolio validation."""

from validate_portfolio import validate_portfolio


def _assert_has_error(errors, expected):
    if expected not in errors:
        raise AssertionError(f"Expected validation error {expected!r}, got {errors}")


def run_portfolio_validation_test():
    valid = {
        "user_profile": {},
        "risk_rules": {
            "single_loss_pct": 2,
            "daily_loss_pct": 6,
            "max_single_position_pct": 35,
            "max_underlying_position_pct": 45,
            "rebalance_tolerance_pct": 5,
        },
        "cash": {"amount": 1000, "target_weight_pct": 10},
        "holdings": [
            {
                "code": "EXAMPLE",
                "name": "Example Holding",
                "strategy_type": "dca",
                "cost_basis": 1000,
                "shares": 100,
                "expense_ratio": 0.2,
                "target_weight_pct": 90,
                "underlying_holdings": [
                    {"code": "EXAMPLE_UNDERLYING", "weight_pct": 35}
                ],
                "return_history": [
                    {"date": "2026-01-01", "return_pct": 1.5}
                ],
                "buy_records": [
                    {
                        "date": "2026-01-02",
                        "confirm_date": "2026-01-03",
                        "amount": 1000,
                        "nav": 10,
                        "shares": 100,
                    },
                    {
                        "date": "2026-02-02",
                        "status": "pending",
                        "amount": 500,
                    },
                ],
            }
        ],
        "watchlist": [],
    }
    valid_errors = validate_portfolio(valid)
    if valid_errors:
        raise AssertionError(f"Expected valid portfolio, got errors: {valid_errors}")

    invalid = {
        "user_profile": {},
        "risk_rules": {
            "single_loss_pct": -1,
            "daily_loss_pct": "6",
            "max_single_position_pct": 120,
            "max_underlying_position_pct": 0,
            "rebalance_tolerance_pct": 101,
        },
        "cash": {"amount": 1000, "target_weight_pct": "bad"},
        "holdings": [
            {
                "code": "BAD",
                "name": "Bad Holding",
                "strategy_type": "dca",
                "cost_basis": 0,
                "shares": -2,
                "expense_ratio": 120,
                "target_weight_pct": -1,
                "underlying_holdings": [
                    {"name": "", "weight_pct": 120},
                    "not-an-object",
                ],
                "return_history": [
                    {"date": "", "return_pct": "bad"},
                    "not-an-object",
                ],
                "buy_records": [
                    {"date": "2026-01-02", "amount": -100, "nav": 0, "shares": 0},
                    "not-an-object",
                ],
            }
        ],
        "watchlist": [],
    }
    errors = validate_portfolio(invalid)
    _assert_has_error(errors, "risk_rules.single_loss_pct must be positive")
    _assert_has_error(errors, "risk_rules.daily_loss_pct must be numeric")
    _assert_has_error(errors, "risk_rules.max_single_position_pct must be between 0 and 100")
    _assert_has_error(errors, "risk_rules.max_underlying_position_pct must be between 0 and 100")
    _assert_has_error(errors, "risk_rules.rebalance_tolerance_pct must be between 0 and 100")
    _assert_has_error(errors, "cash.target_weight_pct must be numeric")
    _assert_has_error(errors, "holding[0] cost_basis must be positive")
    _assert_has_error(errors, "holding[0] shares must be positive")
    _assert_has_error(errors, "holding[0] expense_ratio must be between 0 and 100")
    _assert_has_error(errors, "holding[0] target_weight_pct must be between 0 and 100")
    _assert_has_error(errors, "holding[0].underlying_holdings[0] code or name is required")
    _assert_has_error(errors, "holding[0].underlying_holdings[0].weight_pct must be between 0 and 100")
    _assert_has_error(errors, "holding[0].underlying_holdings[1] must be an object")
    _assert_has_error(errors, "holding[0].return_history[0] date is required")
    _assert_has_error(errors, "holding[0].return_history[0].return_pct must be numeric")
    _assert_has_error(errors, "holding[0].return_history[1] must be an object")
    _assert_has_error(errors, "holding[0].buy_records[0] confirm_date is required unless status=pending")
    _assert_has_error(errors, "holding[0].buy_records[0].amount must be positive")
    _assert_has_error(errors, "holding[0].buy_records[0].nav must be positive")
    _assert_has_error(errors, "holding[0].buy_records[0].shares must be positive")
    _assert_has_error(errors, "holding[0].buy_records[1] must be an object")


def main():
    run_portfolio_validation_test()
    print("Mock portfolio validation test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
