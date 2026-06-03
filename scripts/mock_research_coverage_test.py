#!/usr/bin/env python3
"""Offline tests for cross-role research coverage scoring."""

from common.research_coverage import build_research_coverage_matrix, format_research_coverage


def _assert_contains(text, expected):
    if expected not in text:
        raise AssertionError(f"Expected text to contain: {expected}")


def _assert_not_contains(text, unexpected):
    if unexpected in text:
        raise AssertionError(f"Text should not contain: {unexpected}")


def run_research_coverage_test():
    research_result = {
        "role_results": [
            {
                "role": "risk",
                "status": "ok",
                "data_sources": [
                    {"name": "portfolio_exposure", "source": "local", "status": "available", "source_tier": "local_user_data"},
                    {"name": "market_quotes", "source": "AkShare", "status": "missing_dependency", "source_tier": "community_data"},
                ],
            },
            {
                "role": "industry",
                "status": "skipped",
                "data_sources": [
                    {"name": "news_search", "source": "Tavily", "status": "missing_key", "source_tier": "news_search"},
                    {"name": "news_results", "source": "Tavily", "status": "missing_key", "source_tier": "news_search"},
                ],
            },
            {
                "role": "review",
                "status": "ok",
                "data_sources": [
                    {"name": "report_continuity", "source": "local", "status": "available", "source_tier": "local_user_data"},
                ],
            },
        ]
    }

    matrix = build_research_coverage_matrix(research_result)
    if matrix["role_count"] != 3:
        raise AssertionError(f"Unexpected role count: {matrix}")
    if matrix["requirement_count"] != 5:
        raise AssertionError(f"Unexpected requirement count: {matrix}")
    if matrix["available_count"] != 2:
        raise AssertionError(f"Unexpected available count: {matrix}")
    if matrix["coverage_pct"] != 40.0:
        raise AssertionError(f"Unexpected coverage pct: {matrix}")
    if matrix["gaps"][0]["role"] != "industry":
        raise AssertionError(f"Expected industry news gap first: {matrix}")
    if matrix["gaps"][0]["priority"] != "high":
        raise AssertionError(f"Expected high-priority gap: {matrix}")

    output = format_research_coverage(matrix)
    _assert_contains(output, "## Research Coverage Matrix")
    _assert_contains(output, "- coverage_pct=40.0")
    _assert_contains(output, "- role=industry source=news_search status=missing_key priority=high")
    _assert_contains(output, "- role=risk source=market_quotes status=missing_dependency priority=medium")
    _assert_not_contains(output, "PRIVATE")
    _assert_not_contains(output, "买入")
    _assert_not_contains(output, "卖出")
    _assert_not_contains(output, "自动交易")


def main():
    run_research_coverage_test()
    print("Mock research coverage test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
