#!/usr/bin/env python3
"""Offline tests for sanitized research branch fixtures."""

from common.research_branch_fixtures import research_branch_fixtures
from research_dispatch import format_research_report


def _assert_contains(text, expected):
    if expected not in text:
        raise AssertionError(f"Expected text to contain: {expected}")


def _assert_not_contains(text, unexpected):
    if unexpected in text:
        raise AssertionError(f"Text should not contain: {unexpected}")


def run_research_branch_fixtures_test():
    fixtures = research_branch_fixtures()
    names = {fixture["name"] for fixture in fixtures}
    for expected in ["all_roles_degraded", "runner_failure_path"]:
        if expected not in names:
            raise AssertionError(f"Missing fixture: {expected}")

    rendered = []
    for fixture in fixtures:
        output = format_research_report(fixture["result"])
        rendered.append(output)
        _assert_contains(output, "# Research Execution Report")
        _assert_contains(output, "- Boundary: decision support only")
        _assert_contains(output, "- data sources:")
        _assert_contains(output, "- interpretation:")
        _assert_contains(output, "- research questions:")

    combined = "\n".join(rendered)
    _assert_contains(combined, "- status: ok")
    _assert_contains(combined, "- status: skipped")
    _assert_contains(combined, "- status: failed")
    _assert_contains(combined, "source_tier=local_user_data")
    _assert_contains(combined, "source_tier=community_data")
    _assert_contains(combined, "news_results")
    _assert_contains(combined, "inflation_indicators")
    _assert_contains(combined, "pmi_indicators")
    _assert_contains(combined, "security_market_quotes")
    _assert_contains(combined, "research_reports")
    _assert_contains(combined, "etf_nav_history")
    _assert_contains(combined, "etf_holdings")
    _assert_contains(combined, "cash_buffer")
    _assert_contains(combined, "risk_limit_breaches")
    _assert_contains(combined, "benchmark_quotes")
    _assert_contains(combined, "score=")
    _assert_contains(combined, "remains unconfirmed")
    _assert_contains(combined, "refresh before judgment")
    _assert_not_contains(combined, "PRIVATE")
    _assert_not_contains(combined, "买入")
    _assert_not_contains(combined, "卖出")
    _assert_not_contains(combined, "自动交易")


def main():
    run_research_branch_fixtures_test()
    print("Mock research branch fixtures test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
