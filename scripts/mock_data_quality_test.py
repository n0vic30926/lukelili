#!/usr/bin/env python3
"""Offline tests for data source quality and freshness summaries."""

from common.data_quality import freshness_label, source_tier
from common.data_runtime import DataStatusTracker
from common.reporting import format_run_summary


def _assert_contains(text, expected):
    if expected not in text:
        raise AssertionError(f"Expected text to contain: {expected}")


def run_data_quality_test():
    if source_tier("AkShare") != "community_data":
        raise AssertionError("Expected AkShare community_data tier")
    if source_tier("Tavily") != "news_search":
        raise AssertionError("Expected Tavily news_search tier")
    if source_tier("local") != "local_user_data":
        raise AssertionError("Expected local_user_data tier")
    if source_tier("unknown") != "unknown":
        raise AssertionError("Expected unknown tier")

    if freshness_label("2026-05-31T09:00:00+08:00", "2026-05-31T10:00:00+08:00", max_age_hours=2) != "fresh":
        raise AssertionError("Expected fresh label")
    if freshness_label("2026-05-30T09:00:00+08:00", "2026-05-31T10:00:00+08:00", max_age_hours=2) != "stale":
        raise AssertionError("Expected stale label")
    if freshness_label(None, "2026-05-31T10:00:00+08:00") != "unknown":
        raise AssertionError("Expected unknown freshness")


def run_tracker_quality_summary_test():
    tracker = DataStatusTracker(current_time="2026-05-31T10:00:00+08:00", default_max_age_hours=2)
    tracker.success("fund_nav", source="AkShare", observed_at="2026-05-31T09:30:00+08:00")
    tracker.success("macro", source="AkShare", observed_at="2026-05-30T09:30:00+08:00")
    tracker.skipped("news", source="Tavily", reason="disabled")
    summary = tracker.to_run_summary()

    expected = {
        "fresh": 1,
        "stale": 1,
        "unknown": 1,
        "source_tiers": {"community_data": 2, "news_search": 1},
    }
    if summary["data_quality"] != expected:
        raise AssertionError(f"Unexpected data quality summary: {summary['data_quality']}")

    rendered = format_run_summary(summary)
    _assert_contains(rendered, "- data_quality: fresh=1 stale=1 unknown=1")
    _assert_contains(rendered, "- source_tiers: community_data=2 news_search=1")
    _assert_contains(rendered, "- data_module: fund_nav | status=success | source=AkShare | source_tier=community_data | freshness=fresh")
    _assert_contains(rendered, "- data_module: macro | status=success | source=AkShare | source_tier=community_data | freshness=stale")


def main():
    run_data_quality_test()
    run_tracker_quality_summary_test()
    print("Mock data quality test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
