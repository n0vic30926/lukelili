#!/usr/bin/env python3
"""Offline tests for portfolio-driven industry intelligence mapping."""

from industry_intel import build_search_queries, format_intel_report


def _assert_contains(text, expected):
    if expected not in text:
        raise AssertionError(f"Expected text to contain: {expected}")


def _assert_not_contains(text, unexpected):
    if unexpected in text:
        raise AssertionError(f"Text should not contain: {unexpected}")


def run_dynamic_industry_intel_test():
    portfolio = {
        "holdings": [
            {
                "code": "FUND_A",
                "name": "Example Global Tech Fund",
                "market": "US technology",
                "type": "global_equity",
                "strategy_type": "dca",
            },
            {
                "code": "FUND_B",
                "name": "Example Robotics Fund",
                "market": "A-share robotics",
                "type": "theme_fund",
                "strategy_type": "trial",
            },
        ],
        "watchlist": [
            {"code": "WATCH_A", "name": "Example Semiconductor Index", "reason": "industry benchmark"}
        ],
    }

    queries = build_search_queries(portfolio)
    impacts = {query["impact"] for query in queries}
    if impacts != {"FUND_A", "FUND_B", "WATCH_A"}:
        raise AssertionError(f"Unexpected impact mapping: {queries}")
    if not all(query.get("impact_label") for query in queries):
        raise AssertionError(f"Missing impact labels: {queries}")
    if not any("Example Global Tech Fund" in query["query"] for query in queries):
        raise AssertionError(f"Expected holding name in query text: {queries}")

    report = format_intel_report(
        [
            {
                "title": "Global tech rally continues",
                "content": "Technology shares rally as rates stabilize.",
                "url": "https://example.com/a",
                "tags": ["holding", "dca"],
                "impact": "FUND_A",
                "impact_label": "Example Global Tech Fund",
                "signal": "🟢",
                "signal_level": "利好信号",
            },
            {
                "title": "Robotics sector faces pressure",
                "content": "Robotics companies face correction pressure after a fast rise.",
                "url": "https://example.com/b",
                "tags": ["holding", "trial"],
                "impact": "FUND_B",
                "impact_label": "Example Robotics Fund",
                "signal": "🟡",
                "signal_level": "趋势变化",
            },
        ]
    )
    _assert_contains(report, "[Example Global Tech Fund]")
    _assert_contains(report, "[Example Robotics Fund]")
    _assert_contains(report, "**Example Global Tech Fund**")
    _assert_contains(report, "**Example Robotics Fund**")
    _assert_not_contains(report, "016452")
    _assert_not_contains(report, "011840")


def main():
    run_dynamic_industry_intel_test()
    print("Mock dynamic industry intel test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
