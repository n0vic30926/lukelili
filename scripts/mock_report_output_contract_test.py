#!/usr/bin/env python3
"""Offline tests for daily/weekly report output classification."""

from common.output_contract import build_report_output_sections, with_output_contract


def _assert_contains(text, expected):
    if expected not in text:
        raise AssertionError(f"Expected text to contain: {expected}")


def run_report_output_contract_test():
    portfolio = {
        "holdings": [{"strategy_type": "dca"}],
        "watchlist": [{"reason": "example"}],
    }
    run_summary = {
        "portfolio_source": "example",
        "is_example_data": True,
        "modules": {"success": 2, "failed": 1, "skipped": 0},
        "data_quality": {"fresh": 1, "stale": 0, "unknown": 2},
    }

    sections = build_report_output_sections("daily", portfolio, run_summary)
    output = with_output_contract("# Daily Report\n\nbody", sections)

    _assert_contains(output, "# Daily Report")
    _assert_contains(output, "## Facts")
    _assert_contains(output, "- report_type=daily")
    _assert_contains(output, "- execution_allowed=false")
    _assert_contains(output, "- holdings=1 watchlist=1")
    _assert_contains(output, "- modules success=2 failed=1 skipped=0")
    _assert_contains(output, "## Data-Derived Inferences")
    _assert_contains(output, "- data_quality fresh=1 stale=0 unknown=2")
    _assert_contains(output, "## Model Judgment")
    _assert_contains(output, "- report risk reminders are decision support only")
    _assert_contains(output, "## User Confirmation Required")
    _assert_contains(output, "- user verifies data freshness before any portfolio change")


def main():
    run_report_output_contract_test()
    print("Mock report output contract test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
