#!/usr/bin/env python3
"""L5 decision-support packet builder.

Outputs candidate actions and confirmation checklists only. It never connects to
broker endpoints, places orders, or treats model judgment as user consent.
"""

import json
import sys

from common.config_loader import get_portfolio_path, get_scenario_assumptions_path
from common.decision_confirmation import build_confirmation_state, format_confirmation_state
from common.evidence import rank_evidence
from common.output_contract import format_output_sections
from common.portfolio_exposure import summarize_portfolio_exposure
from common.research_synthesis import synthesize_research_result
from common.signal_ranking import rank_scenario_signals
from research_dispatch import build_research_plan, execute_research_plan
from portfolio_scenarios import build_scenario_review
from validate_scenarios import validate_scenarios


ACTION_BY_STRATEGY = {
    "dca": "observe",
    "long_term": "observe",
    "trial": "review_exit_rules",
    "short_term": "review_exit_rules",
    "watch": "research_only",
}

REQUIRED_RISK_RULES = (
    "single_loss_pct",
    "daily_loss_pct",
    "max_single_position_pct",
)


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


def _risk_rule_checks(portfolio):
    rules = portfolio.get("risk_rules") or {}
    checks = []
    for rule_name in REQUIRED_RISK_RULES:
        value = rules.get(rule_name)
        if value in (None, ""):
            checks.append({"rule": rule_name, "status": "missing"})
        else:
            checks.append({"rule": rule_name, "value": value, "status": "present"})
    return checks


def _missing_risk_rules(risk_rule_checks):
    return [item["rule"] for item in risk_rule_checks if item["status"] == "missing"]


def _candidate_for_holding(index, holding, research_notes, missing_risk_rules=None):
    missing_risk_rules = missing_risk_rules or []
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
    if missing_risk_rules:
        risks.append("missing hard risk rules: " + ",".join(missing_risk_rules))
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


def _scenario_signals(scenario_review):
    signals = []
    if not scenario_review:
        return signals
    for scenario in scenario_review.get("scenarios") or []:
        risk_flags = scenario.get("risk_flags") or []
        risk_flag_types = [str(item.get("type") or "unknown") for item in risk_flags]
        for signal in scenario.get("decision_signals") or []:
            signals.append(
                {
                    "scenario": str(scenario.get("name") or "unnamed_scenario"),
                    "signal": str(signal.get("signal") or "unknown"),
                    "portfolio_impact_pct": scenario.get("portfolio_impact_pct"),
                    "risk_flags": risk_flag_types,
                    "requires_user_confirmation": bool(
                        signal.get("requires_user_confirmation")
                    ),
                }
            )
    return signals


def _scenario_confirmation_texts(scenario_signals):
    confirmations = []
    if scenario_signals:
        confirmations.append("user confirms scenario signals are model judgment, not facts")
        confirmations.append("user confirms scenario signals are not execution consent")
    return confirmations


def build_decision_packet(portfolio, research_result=None, scenario_review=None):
    research_result = research_result or {}
    research_synthesis = synthesize_research_result(research_result)
    research_notes = _research_observations(research_result)
    evidence = research_synthesis["ranked_evidence"] or _research_evidence(research_result)
    risk_rule_checks = _risk_rule_checks(portfolio)
    missing_risk_rules = _missing_risk_rules(risk_rule_checks)
    exposure = summarize_portfolio_exposure(portfolio)
    candidates = [
        _candidate_for_holding(index, holding, research_notes, missing_risk_rules)
        for index, holding in enumerate(portfolio.get("holdings", []))
    ]
    scenario_signals = _scenario_signals(scenario_review)
    ranked_scenario_signals = rank_scenario_signals(scenario_signals)
    for candidate in candidates:
        for confirmation in _scenario_confirmation_texts(scenario_signals):
            if confirmation not in candidate["required_confirmations"]:
                candidate["required_confirmations"].append(confirmation)
    packet = {
        "mode": "decision_support_only",
        "execution_allowed": False,
        "requires_user_confirmation": True,
        "scenario_boundary": (scenario_review or {}).get("boundary") or {},
        "scenario_signals": scenario_signals,
        "ranked_scenario_signals": ranked_scenario_signals,
        "strategy_counts": _strategy_counts(portfolio),
        "research_observations": research_notes,
        "research_synthesis": research_synthesis,
        "evidence": evidence,
        "risk_rule_checks": risk_rule_checks,
        "exposure": exposure,
        "candidates": candidates,
        "prohibited_actions": [
            "broker_connection",
            "order_placement",
            "automatic_trading",
            "treating_forecast_as_fact",
        ],
    }
    packet["confirmation_state"] = build_confirmation_state(packet)
    return packet


def _output_sections(packet):
    facts = [
        f"execution_allowed={str(packet['execution_allowed']).lower()}",
        f"requires_user_confirmation={str(packet['requires_user_confirmation']).lower()}",
    ]
    if packet["strategy_counts"]:
        counts = " ".join(f"{key}={value}" for key, value in packet["strategy_counts"].items())
        facts.append(f"strategy_counts: {counts}")
    exposure = packet.get("exposure") or {}
    if exposure:
        facts.append(
            "exposure "
            f"cash_pct={exposure.get('cash_pct', 0)} "
            f"invested_pct={exposure.get('invested_pct', 0)} "
            f"max_position_pct={exposure.get('max_position_pct', 0)}"
        )
    for item in packet["risk_rule_checks"]:
        if item["status"] == "present":
            facts.append(f"risk_rule {item['rule']}={item['value']} status=present")
        else:
            facts.append(f"risk_rule {item['rule']} status=missing")
    if packet.get("scenario_signals"):
        projection = (packet.get("scenario_boundary") or {}).get("projection", "unknown")
        facts.append("scenario_projection=" + str(projection))

    inferences = list(packet["research_observations"])
    inferences.extend(
        f"evidence {item['label']} score={item['score']}"
        for item in packet["evidence"][:3]
    )

    judgments = [
        f"{candidate['holding_ref']} candidate_action={candidate['candidate_action']}"
        for candidate in packet["candidates"]
    ]
    judgments.extend(
        f"scenario={item['scenario']} decision_signal={item['signal']} priority={item['priority']}"
        for item in packet.get("ranked_scenario_signals") or []
    )

    confirmations = []
    for candidate in packet["candidates"]:
        for item in candidate["required_confirmations"]:
            if item not in confirmations:
                confirmations.append(item)

    return {
        "facts": facts,
        "inferences": inferences,
        "judgments": judgments,
        "confirmations": confirmations,
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
    lines.append(format_output_sections(_output_sections(packet)))
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

    if packet.get("research_synthesis"):
        synthesis = packet["research_synthesis"]
        lines.append("## Cross-Role Research Audit")
        lines.append(f"- role_count={synthesis.get('role_count', 0)}")
        if synthesis.get("role_status_counts"):
            counts = " ".join(
                f"{key}={value}" for key, value in synthesis["role_status_counts"].items()
            )
            lines.append(f"- role_status_counts: {counts}")
        if synthesis.get("data_source_status_counts"):
            counts = " ".join(
                f"{key}={value}" for key, value in synthesis["data_source_status_counts"].items()
            )
            lines.append(f"- data_source_status_counts: {counts}")
        for item in synthesis.get("unavailable_sources", []):
            lines.append(
                "- "
                f"unconfirmed_source role={item['role']} "
                f"source={item['source']} status={item['status']}"
            )
        if synthesis.get("coverage"):
            coverage = synthesis["coverage"]
            lines.append(
                "- "
                f"coverage_pct={coverage.get('coverage_pct', 0.0)} "
                f"available={coverage.get('available_count', 0)}/"
                f"{coverage.get('requirement_count', 0)}"
            )
            for item in (coverage.get("gaps") or [])[:3]:
                lines.append(
                    "- "
                    f"coverage_gap role={item.get('role')} "
                    f"source={item.get('source')} "
                    f"priority={item.get('priority')} "
                    f"status={item.get('status')}"
                )
        lines.append("")

    if packet["risk_rule_checks"]:
        lines.append("## Risk Rule Checks")
        for item in packet["risk_rule_checks"]:
            if item["status"] == "present":
                lines.append(f"- {item['rule']}={item['value']} status=present")
            else:
                lines.append(f"- {item['rule']} status=missing")
        lines.append("")

    if packet.get("exposure"):
        exposure = packet["exposure"]
        lines.append("## Exposure Checks")
        lines.append(
            "- "
            f"cash_pct={exposure['cash_pct']} "
            f"invested_pct={exposure['invested_pct']} "
            f"max_position_pct={exposure['max_position_pct']}"
        )
        if exposure.get("strategy_counts"):
            counts = " ".join(f"{key}={value}" for key, value in exposure["strategy_counts"].items())
            lines.append(f"- strategy_counts: {counts}")
        if exposure.get("factor_counts"):
            counts = " ".join(f"{key}={value}" for key, value in exposure["factor_counts"].items())
            lines.append(f"- factor_counts: {counts}")
        if exposure.get("market_counts"):
            counts = " ".join(f"{key}={value}" for key, value in exposure["market_counts"].items())
            lines.append(f"- market_counts: {counts}")
        for warning in exposure.get("warnings", []):
            lines.append(
                "- "
                f"{warning['type']} holding_ref={warning['holding_ref']} "
                f"actual_pct={warning['actual_pct']} limit_pct={warning['limit_pct']}"
            )
        lines.append("")

    if packet.get("scenario_signals"):
        lines.append("## Scenario Decision Signals")
        projection = (packet.get("scenario_boundary") or {}).get("projection", "unknown")
        lines.append(f"- projection={projection}")
        for item in packet.get("ranked_scenario_signals") or []:
            risk_flags = ",".join(item.get("risk_flags") or ["none"])
            lines.append(
                "- "
                f"scenario={item['scenario']} "
                f"decision_signal={item['signal']} "
                f"priority={item['priority']} "
                f"score={item['score']} "
                f"portfolio_impact_pct={item['portfolio_impact_pct']} "
                f"risk_flags={risk_flags} "
                f"requires_user_confirmation="
                f"{str(item['requires_user_confirmation']).lower()}"
            )
        lines.append("")

    if packet.get("confirmation_state"):
        lines.append(format_confirmation_state(packet["confirmation_state"]))
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


def load_scenario_review(portfolio, settings=None):
    path = get_scenario_assumptions_path(settings)
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as f:
        scenarios = json.load(f)
    if validate_scenarios(scenarios):
        return None
    return build_scenario_review(portfolio, scenarios)


def main(argv=None):
    argv = argv or sys.argv[1:]
    query = " ".join(argv) if argv else "组合风险 复盘 决策辅助"
    portfolio = _load_portfolio()
    plan = build_research_plan(query, portfolio)
    research_result = execute_research_plan(plan, portfolio)
    scenario_review = load_scenario_review(portfolio)
    packet = build_decision_packet(
        portfolio,
        research_result,
        scenario_review=scenario_review,
    )
    print(format_decision_packet(packet))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
