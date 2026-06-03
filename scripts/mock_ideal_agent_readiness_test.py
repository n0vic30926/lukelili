#!/usr/bin/env python3
"""Offline tests for ideal-agent readiness matrix."""

from ideal_agent_readiness import build_readiness_matrix, format_readiness_matrix, summarize_readiness


def _assert_contains(text, expected):
    if expected not in text:
        raise AssertionError(f"Expected text to contain: {expected}")


def _assert_not_contains(text, unexpected):
    if unexpected in text:
        raise AssertionError(f"Text should not contain: {unexpected}")


def run_ideal_agent_readiness_test():
    entries = build_readiness_matrix()
    if len(entries) < 9:
        raise AssertionError(f"Expected broad readiness coverage: {entries}")
    counts = summarize_readiness(entries)
    if counts.get("fail", 0) != 0:
        raise AssertionError(f"Readiness matrix should have no failures: {entries}")
    layers = {entry["layer"] for entry in entries}
    for expected in ["L1", "L2", "L3", "L4", "L4/L5", "L5", "Safety", "Strategy"]:
        if expected not in layers:
            raise AssertionError(f"Missing readiness layer {expected}: {layers}")

    output = format_readiness_matrix(entries)
    _assert_contains(output, "# Ideal Agent Readiness Matrix")
    _assert_contains(output, "decision support only")
    _assert_contains(output, "execution_allowed=false")
    _assert_contains(output, "manual confirmation state includes blockers and a review queue")
    _assert_contains(output, "cross-role synthesis")
    _assert_contains(output, "research coverage")
    _assert_contains(output, "normalized ETF holdings")
    _assert_contains(output, "portfolio x-ray")
    _assert_contains(output, "portfolio backtest")
    _assert_contains(output, "stock intersection")
    _assert_contains(output, "portfolio scenarios")
    _assert_contains(output, "model projection")
    _assert_contains(output, "scenario signals")
    _assert_contains(output, "report decision context")
    _assert_contains(output, "ranked=")
    _assert_contains(output, "competitive benchmark")
    _assert_not_contains(output, "PRIVATE")
    _assert_not_contains(output, "买入")
    _assert_not_contains(output, "卖出")
    _assert_not_contains(output, "下单")


def main():
    run_ideal_agent_readiness_test()
    print("Mock ideal agent readiness test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
