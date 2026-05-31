#!/usr/bin/env python3
"""Minimal standard-library portfolio validation."""

import json
import sys
from pathlib import Path


REQUIRED_TOP_LEVEL = ["user_profile", "risk_rules", "holdings", "watchlist"]
REQUIRED_HOLDING = ["code", "name", "strategy_type", "cost_basis", "shares", "buy_records"]


def validate_portfolio(data):
    errors = []
    for field in REQUIRED_TOP_LEVEL:
        if field not in data:
            errors.append(f"missing top-level field: {field}")
    holdings = data.get("holdings")
    if not isinstance(holdings, list) or not holdings:
        errors.append("holdings must be a non-empty list")
        return errors
    for index, holding in enumerate(holdings):
        if not isinstance(holding, dict):
            errors.append(f"holding[{index}] must be an object")
            continue
        for field in REQUIRED_HOLDING:
            if field not in holding:
                errors.append(f"holding[{index}] missing field: {field}")
        if "cost_basis" in holding and not isinstance(holding["cost_basis"], (int, float)):
            errors.append(f"holding[{index}] cost_basis must be numeric")
        if "shares" in holding and not isinstance(holding["shares"], (int, float)):
            errors.append(f"holding[{index}] shares must be numeric")
        if "buy_records" in holding and not isinstance(holding["buy_records"], list):
            errors.append(f"holding[{index}] buy_records must be a list")
    return errors


def main(argv=None):
    argv = argv or sys.argv[1:]
    if len(argv) != 1:
        print("Usage: python3 scripts/validate_portfolio.py <portfolio.json>")
        return 2
    path = Path(argv[0])
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    errors = validate_portfolio(data)
    if errors:
        for error in errors:
            print(f"FAIL {error}")
        return 1
    print(f"Portfolio validation passed for {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
