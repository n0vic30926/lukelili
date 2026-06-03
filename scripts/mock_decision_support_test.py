#!/usr/bin/env python3
"""Offline tests for L5 decision-support safety boundaries."""

import json
import tempfile
from pathlib import Path

from decision_support import build_decision_packet, format_decision_packet, load_scenario_review
from portfolio_scenarios import build_scenario_review


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
                "cost_basis": 1400,
                "market": "us_stock",
                "factor_profile": {"type": "qdii_us_equity"},
            },
            {
                "code": "PRIVATE_B",
                "name": "Private Holding B",
                "strategy_type": "short_term",
                "cost_basis": 100,
                "market": "a_share",
                "factor_profile": {"type": "a_share_ai"},
            },
            {
                "code": "PRIVATE_C",
                "name": "Private Holding C",
                "strategy_type": "watch",
                "cost_basis": 0,
            },
        ],
        "cash": {"amount": 500},
        "risk_rules": {"single_loss_pct": 2, "daily_loss_pct": 6, "max_single_position_pct": 50},
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
                "data_sources": [
                    {"name": "risk_rules", "status": "available"},
                    {"name": "market_quotes", "status": "missing_dependency"},
                ],
                "limitations": ["no live market data"],
            }
        ],
        "requires_user_confirmation": True,
    }

    scenario_review = build_scenario_review(
        portfolio,
        [
            {
                "name": "risk_drawdown",
                "description": "Hypothetical risk drawdown",
                "shocks": [{"match": {"market": "us_stock"}, "shock_pct": -20}],
            }
        ],
    )
    packet = build_decision_packet(portfolio, research_result, scenario_review=scenario_review)
    if packet["requires_user_confirmation"] is not True:
        raise AssertionError(f"Packet must require confirmation: {packet}")
    if packet["execution_allowed"] is not False:
        raise AssertionError(f"Execution must not be allowed: {packet}")
    actions = [item["candidate_action"] for item in packet["candidates"]]
    if actions != ["observe", "review_exit_rules", "research_only"]:
        raise AssertionError(f"Unexpected candidate actions: {actions}")
    if any("code" in item or "name" in item for item in packet["candidates"]):
        raise AssertionError(f"Candidates must avoid private holding identifiers: {packet}")
    if packet["scenario_signals"][0]["signal"] != "risk_reduction_review":
        raise AssertionError(f"Expected scenario signal in decision packet: {packet}")
    if packet["scenario_boundary"]["projection"] != "model projection, not a fact":
        raise AssertionError(f"Expected scenario projection boundary: {packet}")

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
    _assert_contains(output, "## Cross-Role Research Audit")
    _assert_contains(output, "role_status_counts: ok=1")
    _assert_contains(output, "data_source_status_counts: available=1 missing_dependency=1")
    _assert_contains(output, "unconfirmed_source role=risk source=market_quotes status=missing_dependency")
    _assert_contains(output, "## Risk Rule Checks")
    _assert_contains(output, "single_loss_pct=2 status=present")
    _assert_contains(output, "daily_loss_pct=6 status=present")
    _assert_contains(output, "max_single_position_pct=50 status=present")
    _assert_contains(output, "## Exposure Checks")
    _assert_contains(output, "cash_pct=25.0")
    _assert_contains(output, "max_position_pct=70.0")
    _assert_contains(output, "single_position_exceeds_rule holding_ref=holding_1")
    _assert_contains(output, "## Scenario Decision Signals")
    _assert_contains(output, "scenario=risk_drawdown")
    _assert_contains(output, "decision_signal=risk_reduction_review")
    _assert_contains(output, "projection=model projection, not a fact")
    _assert_contains(output, "scenario_loss_exceeds_daily_loss_rule")
    _assert_contains(output, "user confirms scenario signals are model judgment, not facts")
    _assert_contains(output, "## Manual Confirmation Workflow")
    _assert_contains(output, "confirmation_status=pending_user_confirmation")
    _assert_contains(output, "review_queue=")
    _assert_contains(output, "review_actions:")
    _assert_contains(output, "confirmation_1 status=pending")
    _assert_contains(output, "research_data_source_unconfirmed role=risk source=market_quotes status=missing_dependency")
    _assert_contains(output, "scenario_signal_requires_confirmation scenario=risk_drawdown signal=risk_reduction_review")
    _assert_contains(output, "action=refresh_data status=pending source_ref=research_data_source_unconfirmed")
    _assert_not_contains(output, "PRIVATE_A")
    _assert_not_contains(output, "Private Holding")
    _assert_not_contains(output, "下单")
    _assert_not_contains(output, "自动交易")
    _assert_not_contains(output, "立即买入")
    _assert_not_contains(output, "立即卖出")


def run_scenario_loader_test():
    portfolio = {
        "holdings": [
            {
                "cost_basis": 1000,
                "market": "us_stock",
                "strategy_type": "dca",
                "factor_profile": {"type": "growth"},
            }
        ],
        "cash": {"amount": 0},
        "risk_rules": {"daily_loss_pct": 5},
    }
    scenarios = [
        {
            "name": "configured_drawdown",
            "description": "Configured local drawdown",
            "shocks": [{"match": {"market": "us_stock"}, "shock_pct": -8}],
        }
    ]

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        local_path = tmp_path / "scenario.local.json"
        example_path = tmp_path / "scenario.example.json"
        local_path.write_text(json.dumps(scenarios), encoding="utf-8")
        example_path.write_text(json.dumps([]), encoding="utf-8")

        settings = {
            "scenario_assumptions_path": str(local_path),
            "example_scenario_assumptions_path": str(example_path),
        }
        review = load_scenario_review(portfolio, settings=settings)
        if review["scenario_count"] != 1:
            raise AssertionError(f"Expected configured scenario review: {review}")
        if review["scenarios"][0]["name"] != "configured_drawdown":
            raise AssertionError(f"Expected local scenario assumptions first: {review}")

        local_path.unlink()
        review = load_scenario_review(portfolio, settings=settings)
        if review["scenario_count"] != 0:
            raise AssertionError(f"Expected example scenario fallback: {review}")

        local_path.write_text(json.dumps([{"name": "", "shocks": []}]), encoding="utf-8")
        review = load_scenario_review(portfolio, settings=settings)
        if review is not None:
            raise AssertionError(f"Invalid local scenarios should not build signals: {review}")

        local_path.unlink()
        example_path.unlink()
        review = load_scenario_review(portfolio, settings=settings)
        if review is not None:
            raise AssertionError(f"Missing scenarios should not block decisions: {review}")


def main():
    run_decision_support_test()
    run_scenario_loader_test()
    print("Mock decision support test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
