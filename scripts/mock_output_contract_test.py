#!/usr/bin/env python3
"""Offline tests for investment output classification."""

from common.output_contract import format_output_sections


def _assert_contains(text, expected):
    if expected not in text:
        raise AssertionError(f"Expected text to contain: {expected}")


def run_output_contract_test():
    output = format_output_sections(
        {
            "facts": ["execution_allowed=false"],
            "inferences": ["risk rules are present"],
            "judgments": ["candidate_action=observe"],
            "confirmations": ["user confirms no broker action"],
        }
    )
    _assert_contains(output, "## Facts")
    _assert_contains(output, "- execution_allowed=false")
    _assert_contains(output, "## Data-Derived Inferences")
    _assert_contains(output, "- risk rules are present")
    _assert_contains(output, "## Model Judgment")
    _assert_contains(output, "- candidate_action=observe")
    _assert_contains(output, "## User Confirmation Required")
    _assert_contains(output, "- user confirms no broker action")


def main():
    run_output_contract_test()
    print("Mock output contract test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
