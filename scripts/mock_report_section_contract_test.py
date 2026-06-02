#!/usr/bin/env python3
"""Offline tests for section-level report output classification."""

from common.output_contract import format_classified_report_section


def _assert_contains(text, expected):
    if expected not in text:
        raise AssertionError(f"Expected text to contain: {expected}")


def _assert_not_contains(text, unexpected):
    if unexpected in text:
        raise AssertionError(f"Text should not contain: {unexpected}")


def run_report_section_contract_test():
    output = format_classified_report_section(
        "Decision Notes",
        facts=["execution_allowed=false"],
        inferences=["short-term signal reached review zone"],
        judgments=["candidate action is decision support only"],
        confirmations=["user confirms no broker action should be automated"],
    )
    _assert_contains(output, "### Facts")
    _assert_contains(output, "- execution_allowed=false")
    _assert_contains(output, "### Data-Derived Inferences")
    _assert_contains(output, "- short-term signal reached review zone")
    _assert_contains(output, "### Model Judgment")
    _assert_contains(output, "- candidate action is decision support only")
    _assert_contains(output, "### User Confirmation Required")
    _assert_contains(output, "- user confirms no broker action should be automated")
    _assert_not_contains(output, "买入")
    _assert_not_contains(output, "卖出")
    _assert_not_contains(output, "自动交易")


def main():
    run_report_section_contract_test()
    print("Mock report section contract test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
