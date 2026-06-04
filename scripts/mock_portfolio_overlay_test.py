#!/usr/bin/env python3
"""Offline tests for private portfolio overlays and completion gaps."""

from common.config_loader import apply_portfolio_overlay
from portfolio_gap_review import build_gap_review, build_overlay_template


def _assert_contains(text, expected):
    if expected not in text:
        raise AssertionError(f"Expected {expected!r} in {text!r}")


def run_portfolio_overlay_test():
    portfolio = {
        "cash": {"amount": 0, "status": "not_provided"},
        "risk_rules": {
            "status": "draft_defaults_pending_user_confirmation",
            "single_loss_pct": 2,
            "daily_loss_pct": 6,
            "max_single_position_pct": 35,
        },
        "holdings": [
            {
                "code": "FUND_A",
                "name": "Example A",
                "strategy_type": "pending_user_declaration",
                "cost_basis": 100,
                "shares": 10,
                "buy_records": [{"date": "2026-01-01", "confirm_date": "2026-01-01", "amount": 100, "nav": 10, "shares": 10}],
            },
            {
                "code": "FUND_B",
                "name": "Example B",
                "strategy_type": "pending_user_declaration",
                "cost_basis": 300,
                "shares": 30,
                "pending_buy_notes": [{"note": "后续都是1500"}],
                "buy_records": [{"date": "2026-01-01", "confirm_date": "2026-01-01", "amount": 300, "nav": 10, "shares": 30}],
            },
        ],
        "watchlist": [],
    }
    overlay = {
        "enabled": True,
        "cash": {"amount": None, "target_weight_pct": 20},
        "risk_rules": {"status": "user_confirmed", "max_single_position_pct": 60},
        "holdings_by_code": {
            "FUND_A": {"strategy_type": "trial", "target_weight_pct": 20},
            "FUND_B": {"strategy_type": "dca", "target_weight_pct": 60},
        },
        "append_buy_records_by_code": {
            "FUND_B": [{"date": "2026-02-01", "amount": 1500, "status": "pending"}]
        },
    }

    disabled = apply_portfolio_overlay(portfolio, {**overlay, "enabled": False})
    if disabled["holdings"][0]["strategy_type"] != "pending_user_declaration":
        raise AssertionError(f"Disabled overlay should not apply: {disabled}")

    merged = apply_portfolio_overlay(portfolio, overlay)
    if merged["cash"]["amount"] != 0:
        raise AssertionError(f"None overlay should not overwrite cash amount: {merged['cash']}")
    if merged["cash"]["target_weight_pct"] != 20:
        raise AssertionError(f"Cash target not applied: {merged['cash']}")
    if merged["risk_rules"]["max_single_position_pct"] != 60:
        raise AssertionError(f"Risk rule not applied: {merged['risk_rules']}")
    if [h["strategy_type"] for h in merged["holdings"]] != ["trial", "dca"]:
        raise AssertionError(f"Strategies not applied: {merged['holdings']}")
    if len(merged["holdings"][1]["buy_records"]) != 2:
        raise AssertionError(f"Buy record append failed: {merged['holdings'][1]['buy_records']}")

    review = build_gap_review(portfolio)
    fields = "\n".join(item["field"] for item in review["gaps"])
    _assert_contains(fields, "holdings_by_code.FUND_A.strategy_type")
    _assert_contains(fields, "holdings_by_code.FUND_B.target_weight_pct")
    _assert_contains(fields, "append_buy_records_by_code.FUND_B")

    template = build_overlay_template(portfolio)
    if template["enabled"] is not False:
        raise AssertionError(f"Template overlay must default to disabled: {template}")
    if "FUND_A" not in template["holdings_by_code"]:
        raise AssertionError(f"Template missing holding code: {template}")
    if "FUND_B" not in template["append_buy_records_by_code"]:
        raise AssertionError(f"Template missing pending buy append: {template}")


def main():
    run_portfolio_overlay_test()
    print("Mock portfolio overlay test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
