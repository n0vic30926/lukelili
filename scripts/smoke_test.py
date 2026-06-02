#!/usr/bin/env python3
"""Offline foundation checks for the local finance agent."""

import json
import pathlib
import re
import sys

from security_scan import format_findings, scan_paths, tracked_paths


ROOT = pathlib.Path(__file__).resolve().parents[1]


def _pass(message):
    print(f"PASS {message}")


def _fail(message):
    print(f"FAIL {message}")
    return message


def _read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def _json(path):
    return json.loads(_read(path))


def check_foundation_files():
    failures = []
    required = [
        "AGENTS.md",
        ".env.example",
        ".gitignore",
        "requirements.txt",
        "config/settings.example.json",
        "schemas/portfolio.schema.json",
        "data/examples/portfolio.example.json",
        "docs/LOCAL_SETUP.md",
        "docs/SECURITY_AND_BOUNDARIES.md",
        "docs/ROADMAP.md",
        "scripts/decision_support.py",
        "scripts/etf_research.py",
        "scripts/industry_research.py",
        "scripts/macro_research.py",
        "scripts/common/decision_confirmation.py",
        "scripts/common/config_loader.py",
        "scripts/common/data_quality.py",
        "scripts/common/data_runtime.py",
        "scripts/common/data_sources.py",
        "scripts/common/dependencies.py",
        "scripts/common/evidence.py",
        "scripts/common/output_contract.py",
        "scripts/common/portfolio_exposure.py",
        "scripts/common/report_branch_fixtures.py",
        "scripts/common/report_source_interpretation.py",
        "scripts/common/reporting.py",
        "scripts/common/research_branch_fixtures.py",
        "scripts/common/research_interpretation.py",
        "scripts/common/research_questions.py",
        "scripts/report_index.py",
        "scripts/research_dispatch.py",
        "scripts/risk_research.py",
        "scripts/review_history.py",
        "scripts/security_scan.py",
        "scripts/security_research.py",
        "scripts/validate_portfolio.py",
        "scripts/mock_data_quality_test.py",
        "scripts/mock_data_sources_test.py",
        "scripts/mock_decision_confirmation_test.py",
        "scripts/mock_decision_confirmation_record_test.py",
        "scripts/mock_decision_support_test.py",
        "scripts/mock_dependency_test.py",
        "scripts/mock_evidence_ranking_test.py",
        "scripts/mock_etf_research_test.py",
        "scripts/mock_macro_research_test.py",
        "scripts/mock_daily_status_test.py",
        "scripts/mock_factor_routing_test.py",
        "scripts/mock_factor_status_test.py",
        "scripts/mock_industry_intel_dynamic_test.py",
        "scripts/mock_industry_research_test.py",
        "scripts/mock_news_status_test.py",
        "scripts/mock_output_contract_test.py",
        "scripts/mock_portfolio_exposure_test.py",
        "scripts/mock_portfolio_validation_test.py",
        "scripts/mock_report_branch_fixtures_test.py",
        "scripts/mock_report_advice_classification_test.py",
        "scripts/mock_report_output_contract_test.py",
        "scripts/mock_report_source_interpretation_test.py",
        "scripts/mock_report_section_contract_test.py",
        "scripts/mock_research_branch_fixtures_test.py",
        "scripts/mock_research_execution_test.py",
        "scripts/mock_research_dispatch_test.py",
        "scripts/mock_research_interpretation_test.py",
        "scripts/mock_research_questions_test.py",
        "scripts/mock_risk_research_test.py",
        "scripts/mock_reporting_test.py",
        "scripts/mock_report_index_test.py",
        "scripts/mock_review_history_test.py",
        "scripts/mock_runtime_test.py",
        "scripts/mock_security_scan_test.py",
        "scripts/mock_security_research_test.py",
        "scripts/mock_weekly_status_test.py",
    ]
    for path in required:
        if (ROOT / path).exists():
            _pass(f"{path} exists")
        else:
            failures.append(_fail(f"{path} missing"))
    return failures


def check_json_files():
    failures = []
    for path in [
        "config/settings.example.json",
        "schemas/portfolio.schema.json",
        "data/examples/portfolio.example.json",
    ]:
        try:
            _json(path)
            _pass(f"{path} is valid JSON")
        except Exception as exc:
            failures.append(_fail(f"{path} invalid JSON: {type(exc).__name__}"))
    return failures


def check_sensitive_patterns():
    failures = []
    script_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (ROOT / "scripts").glob("*.py")
        if path.name != "smoke_test.py"
    )
    openclaw_pattern = "~/.open" + "claw"
    tavily_prefix = "tvly" + "-"
    if openclaw_pattern in script_text:
        failures.append(_fail("scripts must not hardcode OpenClaw workspace paths"))
    else:
        _pass("scripts do not hardcode OpenClaw workspace paths")
    if tavily_prefix in script_text:
        failures.append(_fail("scripts must not hardcode Tavily key values"))
    else:
        _pass("scripts do not hardcode Tavily key values")
    if re.search(r"TAVILY_API_KEY\s*=\s*['\"]", script_text):
        failures.append(_fail("scripts must not assign literal TAVILY_API_KEY values"))
    else:
        _pass("scripts do not assign literal TAVILY_API_KEY values")
    return failures


def check_tracked_sensitive_files():
    findings = scan_paths(tracked_paths(ROOT), root=ROOT)
    if findings:
        print(format_findings(findings))
        return [_fail("tracked files must not contain private portfolio details or secrets")]
    _pass("tracked files do not contain scanned private portfolio details or secrets")
    return []


def main():
    failures = []
    failures.extend(check_foundation_files())
    failures.extend(check_json_files())
    failures.extend(check_sensitive_patterns())
    failures.extend(check_tracked_sensitive_files())
    if failures:
        print("")
        print(f"Smoke test failed: {len(failures)} issue(s)")
        return 1
    print("")
    print("Smoke test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
