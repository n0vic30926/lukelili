#!/usr/bin/env python3
"""Offline tests for classified daily/weekly advice sections."""

import daily_finance_brief as daily
import weekly_finance_review as weekly


def _assert_contains(text, expected):
    if expected not in text:
        raise AssertionError(f"Expected text to contain: {expected}")


def run_report_advice_classification_test():
    daily_output = "\n".join(
        daily.format_advice_section(
            [
                "Example Holding [短线] 浮盈31.0%，已达高收益区间，可考虑分批止盈",
                "Example Fund [定投] 浮盈亏+1.0%，定投纪律执行中",
            ]
        )
    )
    weekly_output = "\n".join(
        weekly.format_weekly_advice_section(
            ["Example Holding [短线]: 浮亏-6.0%，超过短线止损线"]
        )
    )
    for output in [daily_output, weekly_output]:
        _assert_contains(output, "### Facts")
        _assert_contains(output, "execution_allowed=false")
        _assert_contains(output, "### Data-Derived Inferences")
        _assert_contains(output, "### Model Judgment")
        _assert_contains(output, "### User Confirmation Required")
        _assert_contains(output, "user confirms no broker action should be automated")


def main():
    run_report_advice_classification_test()
    print("Mock report advice classification test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
