#!/usr/bin/env python3
"""L5 decision-support packet builder.

Outputs candidate actions and confirmation checklists only. It never connects to
broker endpoints, places orders, or treats model judgment as user consent.
"""

import json
import sys

from common.config_loader import get_portfolio_path
from common.evidence import rank_evidence
from research_dispatch import build_research_plan, execute_research_plan


ACTION_BY_STRATEGY = {
    "dca": "observe",
    "long_term": "observe",
    "trial": "review_exit_rules",
    "short_term": "review_exit_rules",
    "watch": "research_only",
}


def _strategy_counts(portfolio):
    counts = {}
    for holding in portfolio.get("holdings", []):
        strategy = str(holding.get("strategy_type") or "unknown")
        counts[strategy] = counts.get(strategy, 0) + 1
    return dict(sorted(counts.items()))


def _research_observations(research_result):
    observations = []
    for role_result in research_result.get("role_results", []):
        role = role_result.get("role", "unknown")
        for observation in role_result.get("observations", [])[:2]:
            observations.append(f"{role}: {observation}")
    return observations[:8]


def _research_evidence(research_result):
    evidence = []
    for role_result in research_result.get("role_results", []):
        evidence.extend(role_result.get("evidence", []))
    return rank_evidence(evidence)[:8]


def _candidate_for_holding(index, holding, research_notes):
    strategy = str(holding.get("strategy_type") or "unknown")
    action = ACTION_BY_STRATEGY.get(strategy, "observe")
    rationale = [
        f"strategy_type={strategy}",
        "candidate action is decision support only",
    ]
    if research_notes:
        rationale.append("research observations available")
    risks = [
        "data may be stale or incomplete",
        "model judgment is not user consent",
    ]
    confirmations = [
        "user confirms strategy still applies",
        "user confirms latest data source freshness",
        "user confirms no broker action should be automated",
    ]
    return {
        "holding_ref": f"holding_{index + 1}",
        "strategy_type": strategy,
        "candidate_action": action,
        "rationale": rationale,
        "risks": risks,
        "required_confirmations": confirmations,
    }


def build_decision_packet(portfolio, research_result=None):
    research_result = research_result or {}
    research_notes = _research_observations(research_result)
    evidence = _research_evidence(research_result)
    candidates = [
        _candidate_for_holding(index, holding, research_notes)
        for index, holding in enumerate(portfolio.get("holdings", []))
    ]
    return {
        "mode": "decision_support_only",
        "execution_allowed": False,
        "requires_user_confirmation": True,
        "strategy_counts": _strategy_counts(portfolio),
        "research_observations": research_notes,
        "evidence": evidence,
        "candidates": candidates,
        "prohibited_actions": [
            "broker_connection",
            "order_placement",
            "automatic_trading",
            "treating_forecast_as_fact",
        ],
    }


def format_decision_packet(packet):
    lines = ["# Decision Support Packet", ""]
    lines.append(f"- Mode: {packet['mode']}")
    lines.append(f"- Execution allowed: {'yes' if packet['execution_allowed'] else 'no'}")
    lines.append(f"- Requires user confirmation: {'yes' if packet['requires_user_confirmation'] else 'no'}")
    if packet["strategy_counts"]:
        counts = " ".join(f"{key}={value}" for key, value in packet["strategy_counts"].items())
        lines.append(f"- Strategy counts: {counts}")
    lines.append("")

    if packet["research_observations"]:
        lines.append("## Research Observations")
        for observation in packet["research_observations"]:
            lines.append(f"- {observation}")
        lines.append("")

    if packet["evidence"]:
        lines.append("## Evidence Reliability")
        for item in packet["evidence"]:
            lines.append(
                "- "
                f"{item['label']} | source_tier={item['source_tier']} "
                f"| freshness={item['freshness']} | score={item['score']}"
            )
        lines.append("")

    lines.append("## Candidates")
    if not packet["candidates"]:
        lines.append("- No holdings found.")
    for candidate in packet["candidates"]:
        lines.append(
            "- "
            f"{candidate['holding_ref']} "
            f"strategy_type={candidate['strategy_type']} "
            f"candidate_action={candidate['candidate_action']}"
        )
        lines.append("  rationale=" + "; ".join(candidate["rationale"]))
        lines.append("  risks=" + "; ".join(candidate["risks"]))
        lines.append("  confirmations=" + "; ".join(candidate["required_confirmations"]))
    lines.append("")
    lines.append("## Prohibited Actions")
    for action in packet["prohibited_actions"]:
        lines.append(f"- {action}")
    return "\n".join(lines)


def _load_portfolio():
    with open(get_portfolio_path(), encoding="utf-8") as f:
        return json.load(f)


def main(argv=None):
    argv = argv or sys.argv[1:]
    query = " ".join(argv) if argv else "组合风险 复盘 决策辅助"
    portfolio = _load_portfolio()
    plan = build_research_plan(query, portfolio)
    research_result = execute_research_plan(plan, portfolio)
    print(format_decision_packet(build_decision_packet(portfolio, research_result)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
