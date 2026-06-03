#!/usr/bin/env python3
"""Validate local scenario assumptions with the standard library."""

import json
import sys
from pathlib import Path


ALLOWED_MATCH_KEYS = {"market", "factor_type", "benchmark", "strategy_type"}


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _validate_shock(errors, scenario_index, shock_index, shock):
    label = f"scenario[{scenario_index}].shocks[{shock_index}]"
    if not isinstance(shock, dict):
        errors.append(f"{label} must be an object")
        return

    match = shock.get("match")
    if not isinstance(match, dict) or not match:
        errors.append(f"{label}.match must include at least one allowed key")
    else:
        for key in match:
            if key not in ALLOWED_MATCH_KEYS:
                errors.append(f"{label}.match key {key} is not allowed")

    if "shock_pct" not in shock:
        errors.append(f"{label}.shock_pct is required")
        return
    shock_pct = shock["shock_pct"]
    if not _is_number(shock_pct):
        errors.append(f"{label}.shock_pct must be numeric")
    elif shock_pct < -100 or shock_pct > 100:
        errors.append(f"{label}.shock_pct must be between -100 and 100")


def _validate_scenario(errors, index, scenario):
    label = f"scenario[{index}]"
    if not isinstance(scenario, dict):
        errors.append(f"{label} must be an object")
        return
    if not str(scenario.get("name") or "").strip():
        errors.append(f"{label}.name is required")
    shocks = scenario.get("shocks")
    if not isinstance(shocks, list) or not shocks:
        errors.append(f"{label}.shocks must be a non-empty list")
        return
    for shock_index, shock in enumerate(shocks):
        _validate_shock(errors, index, shock_index, shock)


def validate_scenarios(data):
    errors = []
    if not isinstance(data, list):
        return ["scenarios must be a list"]
    for index, scenario in enumerate(data):
        _validate_scenario(errors, index, scenario)
    return errors


def main(argv=None):
    argv = argv or sys.argv[1:]
    if len(argv) != 1:
        print("Usage: python3 scripts/validate_scenarios.py <scenario_assumptions.json>")
        return 2
    path = Path(argv[0])
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    errors = validate_scenarios(data)
    if errors:
        for error in errors:
            print(f"FAIL {error}")
        return 1
    print(f"Scenario validation passed for {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
