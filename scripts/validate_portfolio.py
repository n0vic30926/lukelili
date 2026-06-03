#!/usr/bin/env python3
"""Minimal standard-library portfolio validation."""

import json
import sys
from pathlib import Path


REQUIRED_TOP_LEVEL = ["user_profile", "risk_rules", "holdings", "watchlist"]
REQUIRED_HOLDING = ["code", "name", "strategy_type", "cost_basis", "shares", "buy_records"]
REQUIRED_RISK_RULES = ["single_loss_pct", "daily_loss_pct", "max_single_position_pct"]


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _validate_positive(errors, label, value):
    if not _is_number(value):
        errors.append(f"{label} must be numeric")
    elif value <= 0:
        errors.append(f"{label} must be positive")


def _validate_percent(errors, label, value):
    if not _is_number(value):
        errors.append(f"{label} must be numeric")
    elif value <= 0 or value > 100:
        errors.append(f"{label} must be between 0 and 100")


def _validate_nonnegative_percent(errors, label, value):
    if not _is_number(value):
        errors.append(f"{label} must be numeric")
    elif value < 0 or value > 100:
        errors.append(f"{label} must be between 0 and 100")


def _validate_risk_rules(errors, data):
    rules = data.get("risk_rules")
    if not isinstance(rules, dict):
        errors.append("risk_rules must be an object")
        return
    for field in REQUIRED_RISK_RULES:
        if field not in rules:
            errors.append(f"risk_rules.{field} is required")
            continue
        if field == "max_single_position_pct":
            _validate_percent(errors, f"risk_rules.{field}", rules[field])
        else:
            _validate_positive(errors, f"risk_rules.{field}", rules[field])
    if "max_underlying_position_pct" in rules:
        _validate_percent(
            errors,
            "risk_rules.max_underlying_position_pct",
            rules["max_underlying_position_pct"],
        )


def _validate_buy_record(errors, holding_index, record_index, record):
    label = f"holding[{holding_index}].buy_records[{record_index}]"
    if not isinstance(record, dict):
        errors.append(f"{label} must be an object")
        return
    if not record.get("date"):
        errors.append(f"{label} date is required")
    status = str(record.get("status") or "")
    if status != "pending" and not record.get("confirm_date"):
        errors.append(f"{label} confirm_date is required unless status=pending")
    if "amount" not in record:
        errors.append(f"{label}.amount is required")
    else:
        _validate_positive(errors, f"{label}.amount", record["amount"])
    if status == "pending":
        for field in ["nav", "shares"]:
            if field in record:
                _validate_positive(errors, f"{label}.{field}", record[field])
        return
    for field in ["nav", "shares"]:
        if field not in record:
            errors.append(f"{label}.{field} is required unless status=pending")
        else:
            _validate_positive(errors, f"{label}.{field}", record[field])


def _validate_underlying_holding(errors, holding_index, underlying_index, item):
    label = f"holding[{holding_index}].underlying_holdings[{underlying_index}]"
    if not isinstance(item, dict):
        errors.append(f"{label} must be an object")
        return
    if not str(item.get("code") or item.get("symbol") or item.get("name") or "").strip():
        errors.append(f"{label} code or name is required")
    if "weight_pct" not in item:
        errors.append(f"{label}.weight_pct is required")
    else:
        _validate_nonnegative_percent(errors, f"{label}.weight_pct", item["weight_pct"])


def validate_portfolio(data):
    errors = []
    for field in REQUIRED_TOP_LEVEL:
        if field not in data:
            errors.append(f"missing top-level field: {field}")
    if "risk_rules" in data:
        _validate_risk_rules(errors, data)
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
        if "cost_basis" in holding:
            _validate_positive(errors, f"holding[{index}] cost_basis", holding["cost_basis"])
        if "shares" in holding:
            _validate_positive(errors, f"holding[{index}] shares", holding["shares"])
        if "expense_ratio" in holding:
            _validate_nonnegative_percent(
                errors, f"holding[{index}] expense_ratio", holding["expense_ratio"]
            )
        if "buy_records" in holding and not isinstance(holding["buy_records"], list):
            errors.append(f"holding[{index}] buy_records must be a list")
        elif "buy_records" in holding:
            for record_index, record in enumerate(holding["buy_records"]):
                _validate_buy_record(errors, index, record_index, record)
        if "underlying_holdings" in holding and not isinstance(holding["underlying_holdings"], list):
            errors.append(f"holding[{index}] underlying_holdings must be a list")
        elif "underlying_holdings" in holding:
            for underlying_index, item in enumerate(holding["underlying_holdings"]):
                _validate_underlying_holding(errors, index, underlying_index, item)
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
