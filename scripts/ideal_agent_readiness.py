#!/usr/bin/env python3
"""Offline ideal-agent readiness matrix.

This check uses only tracked example data and sanitized fixtures. It does not
fetch market data, read private holdings, connect to brokers, or place orders.
"""

import json
from pathlib import Path
import warnings

warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL.*")

from common.output_contract import build_report_output_sections, format_output_sections
from common.portfolio_exposure import summarize_portfolio_exposure
from common.report_branch_fixtures import report_branch_fixtures
from common.data_sources import role_data_requirements
from common.research_synthesis import synthesize_research_result
from competitive_readiness import build_competitive_readiness
from decision_support import build_decision_packet
from portfolio_scenarios import build_scenario_review
from portfolio_xray import build_portfolio_xray
from research_dispatch import build_research_plan, execute_research_plan
from validate_scenarios import validate_scenarios
from validate_portfolio import validate_portfolio


ROOT = Path(__file__).resolve().parents[1]


def _load_example_portfolio():
    with (ROOT / "data/examples/portfolio.example.json").open(encoding="utf-8") as f:
        return json.load(f)


def _load_example_scenarios():
    with (ROOT / "data/examples/scenario_assumptions.example.json").open(encoding="utf-8") as f:
        return json.load(f)


def _entry(layer, requirement, ok, evidence, status_if_false="fail"):
    return {
        "layer": layer,
        "requirement": requirement,
        "status": "pass" if ok else status_if_false,
        "evidence": evidence,
    }


def _has_sections(text):
    return all(
        marker in text
        for marker in [
            "## Facts",
            "## Data-Derived Inferences",
            "## Model Judgment",
            "## User Confirmation Required",
        ]
    )


def build_readiness_matrix():
    portfolio = _load_example_portfolio()
    entries = []

    errors = validate_portfolio(portfolio)
    entries.append(
        _entry(
            "L2",
            "example portfolio validates with required risk rules and buy records",
            not errors,
            "validate_portfolio(data/examples/portfolio.example.json)",
        )
    )

    exposure = summarize_portfolio_exposure(portfolio)
    entries.append(
        _entry(
            "L2",
            "portfolio exposure summary is anonymized and includes allocation checks",
            bool(exposure.get("holding_count")) and "positions" in exposure,
            f"holding_count={exposure.get('holding_count')} max_position_pct={exposure.get('max_position_pct')}",
        )
    )

    xray = build_portfolio_xray(portfolio)
    entries.append(
        _entry(
            "L2",
            "portfolio x-ray exposes allocation, overlap, fee review, and boundaries",
            bool(xray.get("allocation"))
            and "overlap_clusters" in xray
            and xray.get("fee_review", {}).get("weighted_expense_ratio_pct") is not None
            and xray.get("boundary", {}).get("execution_allowed") is False,
            "portfolio_xray fee_coverage_count="
            + str(xray.get("fee_review", {}).get("fee_coverage_count")),
        )
    )

    scenario_review = build_scenario_review(portfolio, _load_example_scenarios())
    scenario_errors = validate_scenarios(_load_example_scenarios())
    entries.append(
        _entry(
            "L2",
            "portfolio scenarios validate and expose projections, decision signals, and risk flags",
            scenario_review.get("scenario_count", 0) > 0
            and not scenario_errors
            and scenario_review.get("boundary", {}).get("projection") == "model projection, not a fact"
            and scenario_review.get("boundary", {}).get("requires_user_confirmation") is True
            and scenario_review.get("boundary", {}).get("execution_allowed") is False
            and all(item.get("decision_signals") for item in scenario_review.get("scenarios", [])),
            "portfolio_scenarios scenario_count="
            + str(scenario_review.get("scenario_count", 0))
            + " validation_errors="
            + str(len(scenario_errors))
            + " boundary=model projection, not a fact",
        )
    )

    output = format_output_sections(
        {
            "facts": ["execution_allowed=false"],
            "inferences": ["data source status is visible"],
            "judgments": ["decision support only"],
            "confirmations": ["user confirmation required"],
        }
    )
    entries.append(
        _entry(
            "L1",
            "outputs separate facts, inferences, model judgment, and confirmation",
            _has_sections(output) and "execution_allowed=false" in output,
            "common.output_contract.format_output_sections",
        )
    )

    report_fixtures = report_branch_fixtures()
    report_sections = [
        build_report_output_sections(item["report_type"], item["portfolio"], item["run_summary"])
        for item in report_fixtures
    ]
    has_degraded_report = any(
        (item["run_summary"].get("modules") or {}).get("failed", 0) > 0
        or (item["run_summary"].get("modules") or {}).get("skipped", 0) > 0
        for item in report_fixtures
    )
    entries.append(
        _entry(
            "L3",
            "daily/weekly report branches expose success, degraded, and skipped paths",
            len(report_fixtures) >= 3 and has_degraded_report and all(section.get("facts") for section in report_sections),
            f"report_branch_fixtures={len(report_fixtures)}",
        )
    )

    research_query = "宏观 利率 行业 个股 财报 ETF 组合风险 复盘"
    plan = build_research_plan(research_query, portfolio)
    role_names = [task["role"] for task in plan["tasks"]]
    required_roles = {"macro", "industry", "security", "etf", "risk", "review"}
    entries.append(
        _entry(
            "L4",
            "dispatcher covers macro, industry, security, ETF, risk, and review roles",
            required_roles.issubset(set(role_names)),
            "roles=" + ",".join(role_names),
        )
    )

    security_requirements = {item["name"] for item in role_data_requirements("security")}
    entries.append(
        _entry(
            "L4",
            "security role covers fundamentals, filings, valuation, market quotes, and research reports",
            {
                "financial_statements",
                "announcements",
                "valuation_metrics",
                "security_market_quotes",
                "research_reports",
            }.issubset(security_requirements),
            "security_data_requirements=" + ",".join(sorted(security_requirements)),
        )
    )

    etf_requirements = {item["name"] for item in role_data_requirements("etf")}
    entries.append(
        _entry(
            "L4",
            "ETF role covers quotes, liquidity, premium/discount, NAV history, and holdings",
            {
                "etf_quotes",
                "liquidity_metrics",
                "premium_discount",
                "etf_nav_history",
                "etf_holdings",
            }.issubset(etf_requirements),
            "etf_data_requirements=" + ",".join(sorted(etf_requirements)),
        )
    )

    macro_requirements = {item["name"] for item in role_data_requirements("macro")}
    entries.append(
        _entry(
            "L4",
            "macro role covers rates, FX, liquidity, inflation, and PMI context",
            {
                "macro_rates",
                "fx_rates",
                "liquidity_indicators",
                "inflation_indicators",
                "pmi_indicators",
            }.issubset(macro_requirements),
            "macro_data_requirements=" + ",".join(sorted(macro_requirements)),
        )
    )

    industry_requirements = {item["name"] for item in role_data_requirements("industry")}
    entries.append(
        _entry(
            "L4",
            "industry role covers rotation, concept, news search, and news result evidence",
            {
                "industry_rotation",
                "concept_rotation",
                "news_search",
                "news_results",
            }.issubset(industry_requirements),
            "industry_data_requirements=" + ",".join(sorted(industry_requirements)),
        )
    )

    risk_requirements = {item["name"] for item in role_data_requirements("risk")}
    entries.append(
        _entry(
            "L4",
            "risk role covers exposure, cash buffer, rule breaches, market quotes, and benchmarks",
            {
                "portfolio_exposure",
                "cash_buffer",
                "risk_limit_breaches",
                "market_quotes",
                "benchmark_quotes",
                "factor_exposure",
            }.issubset(risk_requirements),
            "risk_data_requirements=" + ",".join(sorted(risk_requirements)),
        )
    )

    research_result = execute_research_plan(plan, portfolio)
    role_results = research_result.get("role_results", [])
    entries.append(
        _entry(
            "L4",
            "role execution returns evidence, data sources, interpretations, and research questions",
            all(
                item.get("evidence") is not None
                and item.get("data_sources")
                and item.get("interpretations") is not None
                and item.get("research_questions") is not None
                for item in role_results
            ),
            f"role_results={len(role_results)}",
        )
    )

    synthesis = synthesize_research_result(research_result)
    entries.append(
        _entry(
            "L4/L5",
            "cross-role synthesis summarizes status, gaps, and ranked evidence",
            synthesis["role_count"] == len(role_results)
            and bool(synthesis["data_source_status_counts"])
            and bool(synthesis["ranked_evidence"]),
            f"role_count={synthesis['role_count']} unavailable_sources={len(synthesis['unavailable_sources'])}",
        )
    )

    packet = build_decision_packet(portfolio, research_result, scenario_review=scenario_review)
    confirmation = packet["confirmation_state"]
    entries.append(
        _entry(
            "L5",
            "decision packet is decision-support only and never executable",
            packet["execution_allowed"] is False
            and packet["requires_user_confirmation"] is True
            and "broker_connection" in packet["prohibited_actions"],
            "execution_allowed=false prohibited_actions present",
        )
    )
    entries.append(
        _entry(
            "L5",
            "manual confirmation state includes blockers and a review queue",
            confirmation["execution_allowed"] is False
            and confirmation["review_queue_count"] >= confirmation["check_count"]
            and bool(confirmation["review_action_counts"]),
            "review_queue_count="
            + str(confirmation["review_queue_count"])
            + " review_actions="
            + ",".join(sorted(confirmation["review_action_counts"])),
        )
    )
    entries.append(
        _entry(
            "L5",
            "decision packet carries scenario signals into manual confirmation",
            bool(packet.get("scenario_signals"))
            and bool(packet.get("ranked_scenario_signals"))
            and all(item.get("requires_user_confirmation") for item in packet["scenario_signals"])
            and all(item.get("priority") for item in packet["ranked_scenario_signals"])
            and any(
                item.get("type") == "scenario_signal_requires_confirmation"
                for item in confirmation.get("blockers", [])
            ),
            "scenario_signals="
            + str(len(packet.get("scenario_signals") or []))
            + " ranked="
            + str(len(packet.get("ranked_scenario_signals") or [])),
        )
    )

    docs_ok = all(
        (ROOT / path).exists()
        for path in [
            "AGENTS.md",
            "docs/SIGNAL_POLICY.md",
            "docs/SECURITY_AND_BOUNDARIES.md",
            "docs/ROADMAP.md",
            "docs/LOCAL_SETUP.md",
        ]
    )
    entries.append(
        _entry(
            "Safety",
            "local guardrails and setup documentation are present",
            docs_ok,
            "AGENTS.md docs/SIGNAL_POLICY.md docs/SECURITY_AND_BOUNDARIES.md docs/ROADMAP.md docs/LOCAL_SETUP.md",
        )
    )

    competitive_entries = build_competitive_readiness()
    competitive_failures = [
        entry for entry in competitive_entries if entry["status"] == "fail"
    ]
    entries.append(
        _entry(
            "Strategy",
            "competitive benchmark exists and gates future roadmap iterations",
            not competitive_failures,
            "competitive_readiness failures=" + str(len(competitive_failures)),
        )
    )
    return entries


def summarize_readiness(entries):
    counts = {"pass": 0, "warn": 0, "fail": 0}
    for entry in entries:
        counts[entry["status"]] = counts.get(entry["status"], 0) + 1
    return counts


def format_readiness_matrix(entries):
    counts = summarize_readiness(entries)
    lines = ["# Ideal Agent Readiness Matrix", ""]
    lines.append(
        "- Summary: "
        f"pass={counts.get('pass', 0)} warn={counts.get('warn', 0)} fail={counts.get('fail', 0)}"
    )
    lines.append("- Boundary: decision support only; no broker connection or order placement")
    lines.append("")
    lines.append("| Layer | Status | Requirement | Evidence |")
    lines.append("|---|---|---|---|")
    for entry in entries:
        lines.append(
            f"| {entry['layer']} | {entry['status']} | {entry['requirement']} | {entry['evidence']} |"
        )
    return "\n".join(lines)


def main():
    entries = build_readiness_matrix()
    print(format_readiness_matrix(entries))
    return 0 if summarize_readiness(entries).get("fail", 0) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
