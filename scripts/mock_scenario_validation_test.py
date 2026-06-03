#!/usr/bin/env python3
"""Offline tests for scenario assumption validation."""

from validate_scenarios import validate_scenarios


def _assert_has_error(errors, expected):
    if expected not in errors:
        raise AssertionError(f"Expected validation error {expected!r}, got {errors}")


def run_scenario_validation_test():
    valid = [
        {
            "name": "valid_drawdown",
            "description": "Valid hypothetical drawdown",
            "shocks": [
                {"match": {"market": "us_stock"}, "shock_pct": -8},
                {"match": {"factor_type": "growth"}, "shock_pct": 3.5},
            ],
        }
    ]
    valid_errors = validate_scenarios(valid)
    if valid_errors:
        raise AssertionError(f"Expected valid scenarios, got errors: {valid_errors}")

    invalid = [
        {
            "name": "",
            "description": "",
            "shocks": [
                {"match": {"private_code": "SECRET"}, "shock_pct": -101},
                {"match": {}, "shock_pct": "bad"},
                "not-an-object",
            ],
        },
        {"name": "missing_shocks"},
    ]
    errors = validate_scenarios(invalid)
    _assert_has_error(errors, "scenario[0].name is required")
    _assert_has_error(errors, "scenario[0].shocks[0].match key private_code is not allowed")
    _assert_has_error(errors, "scenario[0].shocks[0].shock_pct must be between -100 and 100")
    _assert_has_error(errors, "scenario[0].shocks[1].match must include at least one allowed key")
    _assert_has_error(errors, "scenario[0].shocks[1].shock_pct must be numeric")
    _assert_has_error(errors, "scenario[0].shocks[2] must be an object")
    _assert_has_error(errors, "scenario[1].shocks must be a non-empty list")
    _assert_has_error(validate_scenarios({}), "scenarios must be a list")


def main():
    run_scenario_validation_test()
    print("Mock scenario validation test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
