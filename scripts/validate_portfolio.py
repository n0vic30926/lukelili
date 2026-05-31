#!/usr/bin/env python3
"""Minimal portfolio validator using only the Python standard library."""

import json
import sys
from pathlib import Path


VALID_STRATEGIES = {"dca", "trial", "short_term", "watch", "long_term"}


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def validate_portfolio_data(data):
    errors = []
    for field in ["user_profile", "cash", "risk_rules", "holdings", "watchlist"]:
        if field not in data:
            errors.append(f"missing required field: {field}")

    if not isinstance(data.get("user_profile", {}), dict):
        errors.append("user_profile must be an object")
    if not isinstance(data.get("cash", {}), dict):
        errors.append("cash must be an object")
    if not isinstance(data.get("risk_rules", {}), dict):
        errors.append("risk_rules must be an object")
    if not isinstance(data.get("watchlist", []), list):
        errors.append("watchlist must be an array")

    cash = data.get("cash", {})
    if isinstance(cash, dict) and "amount" in cash and not _is_number(cash["amount"]):
        errors.append("cash.amount must be a number")

    holdings = data.get("holdings", [])
    if not isinstance(holdings, list):
        errors.append("holdings must be an array")
        return errors

    for idx, holding in enumerate(holdings):
        if not isinstance(holding, dict):
            errors.append(f"holdings[{idx}] must be an object")
            continue
        for field in ["code", "name", "strategy_type", "cost_basis", "shares"]:
            if field not in holding:
                errors.append(f"holdings[{idx}] missing required field: {field}")
        strategy = holding.get("strategy_type")
        if strategy is not None and strategy not in VALID_STRATEGIES:
            errors.append(f"holdings[{idx}].strategy_type is invalid: {strategy}")
        if "cost_basis" in holding and not _is_number(holding["cost_basis"]):
            errors.append(f"holdings[{idx}].cost_basis must be a number")
        if "shares" in holding and not _is_number(holding["shares"]):
            errors.append(f"holdings[{idx}].shares must be a number")
        if "target_allocation" in holding and not _is_number(holding["target_allocation"]):
            errors.append(f"holdings[{idx}].target_allocation must be a number")
        etf_profile = holding.get("etf_profile")
        if etf_profile is not None:
            if not isinstance(etf_profile, dict):
                errors.append(f"holdings[{idx}].etf_profile must be an object")
            else:
                for field in ["expense_ratio", "tracking_error"]:
                    if field in etf_profile and not _is_number(etf_profile[field]):
                        errors.append(f"holdings[{idx}].etf_profile.{field} must be a number")
                tracking_history = etf_profile.get("tracking_history", [])
                if not isinstance(tracking_history, list):
                    errors.append(f"holdings[{idx}].etf_profile.tracking_history must be an array")
                else:
                    for hist_idx, record in enumerate(tracking_history):
                        if not isinstance(record, dict):
                            errors.append(f"holdings[{idx}].etf_profile.tracking_history[{hist_idx}] must be an object")
                            continue
                        for field in ["etf_return_pct", "benchmark_return_pct"]:
                            if field in record and not _is_number(record[field]):
                                errors.append(
                                    f"holdings[{idx}].etf_profile.tracking_history[{hist_idx}].{field} must be a number"
                                )
                dividend_history = etf_profile.get("dividend_history", [])
                if not isinstance(dividend_history, list):
                    errors.append(f"holdings[{idx}].etf_profile.dividend_history must be an array")
                else:
                    for div_idx, record in enumerate(dividend_history):
                        if not isinstance(record, dict):
                            errors.append(f"holdings[{idx}].etf_profile.dividend_history[{div_idx}] must be an object")
                            continue
                        if "amount" in record and not _is_number(record["amount"]):
                            errors.append(
                                f"holdings[{idx}].etf_profile.dividend_history[{div_idx}].amount must be a number"
                            )
        buy_records = holding.get("buy_records", [])
        if not isinstance(buy_records, list):
            errors.append(f"holdings[{idx}].buy_records must be an array")
            continue
        for rec_idx, record in enumerate(buy_records):
            if not isinstance(record, dict):
                errors.append(f"holdings[{idx}].buy_records[{rec_idx}] must be an object")
                continue
            for field in ["date", "amount"]:
                if field not in record:
                    errors.append(f"holdings[{idx}].buy_records[{rec_idx}] missing required field: {field}")
            if "amount" in record and not _is_number(record["amount"]):
                errors.append(f"holdings[{idx}].buy_records[{rec_idx}].amount must be a number")

    return errors


def validate_portfolio_file(path):
    path = Path(path)
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    return validate_portfolio_data(data)


def main(argv=None):
    argv = argv or sys.argv[1:]
    if not argv:
        print("Usage: python3 scripts/validate_portfolio.py <portfolio.json>", file=sys.stderr)
        return 2
    path = Path(argv[0])
    errors = validate_portfolio_file(path)
    if errors:
        print(f"Portfolio validation failed for {path}:")
        for err in errors:
            print(f"- {err}")
        return 1
    print(f"Portfolio validation passed for {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
