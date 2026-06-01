#!/usr/bin/env python3
"""Offline tests for evidence reliability ranking and formatting."""

from common.evidence import format_evidence_list, rank_evidence


def _assert_contains(text, expected):
    if expected not in text:
        raise AssertionError(f"Expected text to contain: {expected}")


def run_evidence_ranking_test():
    items = [
        {"label": "external news", "source_tier": "news_search", "freshness": "unknown"},
        {"label": "local portfolio", "source_tier": "local_user_data", "freshness": "fresh"},
        {"label": "community quote", "source_tier": "community_data", "freshness": "stale"},
    ]
    ranked = rank_evidence(items)
    labels = [item["label"] for item in ranked]
    if labels != ["local portfolio", "community quote", "external news"]:
        raise AssertionError(f"Unexpected ranking: {ranked}")
    if ranked[0]["score"] <= ranked[-1]["score"]:
        raise AssertionError(f"Scores should be descending: {ranked}")

    output = format_evidence_list(ranked)
    _assert_contains(output, "local portfolio | source_tier=local_user_data | freshness=fresh | score=")
    _assert_contains(output, "community quote | source_tier=community_data | freshness=stale | score=")
    _assert_contains(output, "external news | source_tier=news_search | freshness=unknown | score=")


def main():
    run_evidence_ranking_test()
    print("Mock evidence ranking test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
