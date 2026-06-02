#!/usr/bin/env python3
"""Offline tests for sanitized report branch fixtures."""

from common.output_contract import build_report_output_sections, with_output_contract
from common.report_branch_fixtures import report_branch_fixtures
from common.reporting import format_run_summary


def _assert_contains(text, expected):
    if expected not in text:
        raise AssertionError(f"Expected text to contain: {expected}")


def _assert_not_contains(text, unexpected):
    if unexpected in text:
        raise AssertionError(f"Text should not contain: {unexpected}")


def run_report_branch_fixtures_test():
    fixtures = report_branch_fixtures()
    names = {fixture["name"] for fixture in fixtures}
    for expected in ["daily_all_available", "daily_degraded_data", "weekly_skipped_inputs"]:
        if expected not in names:
            raise AssertionError(f"Missing fixture: {expected}")

    rendered_all = []
    for fixture in fixtures:
        report_type = fixture["report_type"]
        portfolio = fixture["portfolio"]
        run_summary = fixture["run_summary"]
        sections = build_report_output_sections(report_type, portfolio, run_summary)
        output = with_output_contract(f"# {report_type.title()} Fixture\n\nbody", sections)
        summary = format_run_summary(run_summary)
        rendered_all.append(output)
        rendered_all.append(summary)
        _assert_contains(output, "## Facts")
        _assert_contains(output, "## Data-Derived Inferences")
        _assert_contains(output, "## Model Judgment")
        _assert_contains(output, "## User Confirmation Required")
        _assert_contains(output, "execution_allowed=false")
        _assert_contains(summary, "## 运行摘要")
        _assert_contains(summary, "- modules:")

    rendered = "\n".join(rendered_all)
    _assert_contains(rendered, "some data modules failed; report may be incomplete")
    _assert_contains(rendered, "some data modules were skipped by configuration or missing inputs")
    _assert_contains(rendered, "cache_hit=1")
    _assert_not_contains(rendered, "PRIVATE")
    _assert_not_contains(rendered, "买入")
    _assert_not_contains(rendered, "卖出")
    _assert_not_contains(rendered, "自动交易")


def main():
    run_report_branch_fixtures_test()
    print("Mock report branch fixtures test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
