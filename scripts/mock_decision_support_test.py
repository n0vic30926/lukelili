#!/usr/bin/env python3
"""Offline tests for L5 decision-support safety boundaries."""

from decision_support import build_decision_packet, format_decision_packet


def _assert_contains(text, expected):
    if expected not in text:
        raise AssertionError(f"Expected text to contain: {expected}")


def _assert_not_contains(text, unexpected):
    if unexpected in text:
        raise AssertionError(f"Text should not contain: {unexpected}")


def run_decision_support_test():
    portfolio = {
        "holdings": [
            {
                "code": "PRIVATE_A",
                "name": "Private Holding A",
                "strategy_type": "dca",
                "strategy_label": "long-term plan",
            },
            {
                "code": "PRIVATE_B",
                "name": "Private Holding B",
                "strategy_type": "short_term",
            },
            {
                "code": "PRIVATE_C",
                "name": "Private Holding C",
                "strategy_type": "watch",
            },
        ],
        "risk_rules": {"single_loss_pct": 2, "daily_loss_pct": 6},
    }
    research_result = {
        "role_results": [
            {
                "role": "risk",
                "status": "ok",
                "observations": ["drawdown rule present", "concentration needs review"],
                "evidence": [
                    {"label": "external rumor", "source_tier": "news_search", "freshness": "unknown", "score": 15},
                    {"label": "portfolio.risk_rules", "source_tier": "local_user_data", "freshness": "fresh", "score": 70},
                ],
                "limitations": ["no live market data"],
            }
        ],
        "requires_user_confirmation": True,
    }

    packet = build_decision_packet(portfolio, research_result)
    if packet["requires_user_confirmation"] is not True:
        raise AssertionError(f"Packet must require confirmation: {packet}")
    if packet["execution_allowed"] is not False:
        raise AssertionError(f"Execution must not be allowed: {packet}")
    actions = [item["candidate_action"] for item in packet["candidates"]]
    if actions != ["observe", "review_exit_rules", "research_only"]:
        raise AssertionError(f"Unexpected candidate actions: {actions}")
    if any("code" in item or "name" in item for item in packet["candidates"]):
        raise AssertionError(f"Candidates must avoid private holding identifiers: {packet}")

    output = format_decision_packet(packet)
    _assert_contains(output, "# Decision Support Packet")
    _assert_contains(output, "- Execution allowed: no")
    _assert_contains(output, "- Requires user confirmation: yes")
    _assert_contains(output, "## Facts")
    _assert_contains(output, "## Data-Derived Inferences")
    _assert_contains(output, "## Model Judgment")
    _assert_contains(output, "## User Confirmation Required")
    _assert_contains(output, "execution_allowed=false")
    _assert_contains(output, "candidate_action=observe")
    _assert_contains(output, "candidate_action=review_exit_rules")
    _assert_contains(output, "candidate_action=research_only")
    _assert_contains(output, "## Evidence Reliability")
    _assert_contains(output, "portfolio.risk_rules | source_tier=local_user_data | freshness=fresh | score=")
    _assert_contains(output, "external rumor | source_tier=news_search | freshness=unknown | score=")
    _assert_contains(output, "## Risk Rule Checks")
    _assert_contains(output, "single_loss_pct=2 status=present")
    _assert_contains(output, "daily_loss_pct=6 status=present")
    _assert_contains(output, "max_single_position_pct status=missing")
    _assert_contains(output, "missing hard risk rules: max_single_position_pct")
    _assert_not_contains(output, "PRIVATE_A")
    _assert_not_contains(output, "Private Holding")
    _assert_not_contains(output, "下单")
    _assert_not_contains(output, "自动交易")
    _assert_not_contains(output, "立即买入")
    _assert_not_contains(output, "立即卖出")


def main():
    run_decision_support_test()
    print("Mock decision support test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
