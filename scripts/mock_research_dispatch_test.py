#!/usr/bin/env python3
"""Offline tests for L4 research role dispatch contracts."""

from research_dispatch import build_research_plan, format_research_plan


def _assert_contains(text, expected):
    if expected not in text:
        raise AssertionError(f"Expected text to contain: {expected}")


def _assert_not_contains(text, unexpected):
    if unexpected in text:
        raise AssertionError(f"Text should not contain: {unexpected}")


def run_research_dispatch_test():
    portfolio = {
        "holdings": [
            {
                "code": "FUND_A",
                "name": "Example Global Tech Fund",
                "strategy_type": "dca",
                "factor_profile": {"type": "qdii_us_equity"},
            },
            {
                "code": "FUND_B",
                "name": "Example Robotics Fund",
                "strategy_type": "trial",
                "factor_profile": {"type": "a_share_ai"},
            },
            {
                "code": "STOCK_A",
                "name": "Example Security",
                "type": "stock",
                "strategy_type": "watch",
            },
        ],
        "watchlist": [
            {"code": "WATCH_A", "name": "Example ETF", "reason": "ETF candidate"}
        ],
    }

    plan = build_research_plan("帮我看宏观利率、个股财报、ETF、组合风险和历史复盘", portfolio)
    roles = [item["role"] for item in plan["tasks"]]
    if roles != ["macro", "security", "etf", "risk", "review"]:
        raise AssertionError(f"Unexpected roles: {roles}")
    if any(item["boundary"] != "decision_support_only" for item in plan["tasks"]):
        raise AssertionError(f"Unexpected boundaries: {plan}")
    if plan["requires_user_confirmation"] is not True:
        raise AssertionError(f"Plan must require user confirmation: {plan}")

    output = format_research_plan(plan)
    _assert_contains(output, "# Research Dispatch Plan")
    _assert_contains(output, "- macro: macro rates, FX, inflation, liquidity")
    _assert_contains(output, "- security: individual security fundamentals, valuation, filings")
    _assert_contains(output, "- etf: ETF structure, tracking, liquidity, fees")
    _assert_contains(output, "- risk: portfolio exposure, concentration, drawdown rules")
    _assert_contains(output, "- review: report continuity, repeated failures, discipline records")
    _assert_contains(output, "Requires user confirmation: yes")
    _assert_not_contains(output, "买入")
    _assert_not_contains(output, "卖出")
    _assert_not_contains(output, "自动交易")


def main():
    run_research_dispatch_test()
    print("Mock research dispatch test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
