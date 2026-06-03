#!/usr/bin/env python3
"""Offline tests for competitive benchmark readiness."""

from competitive_readiness import build_competitive_readiness, format_competitive_readiness


def _assert_contains(text, expected):
    if expected not in text:
        raise AssertionError(f"Expected text to contain: {expected}")


def run_competitive_readiness_test():
    entries = build_competitive_readiness()
    failures = [entry for entry in entries if entry["status"] == "fail"]
    if failures:
        raise AssertionError(f"Competitive readiness should have no failures: {failures}")

    output = format_competitive_readiness(entries)
    for expected in [
        "Competitor Capability Matrix",
        "Local Competitive Advantages",
        "Iteration Gate",
        "Betterment",
        "Portfolio Visualizer",
        "local-first privacy",
        "explicit user confirmation",
        "decision support only",
    ]:
        _assert_contains(output, expected)


def main():
    run_competitive_readiness_test()
    print("Mock competitive readiness test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
