#!/usr/bin/env python3
"""Offline tests for data runtime status tracking and cache helpers."""

import tempfile
from pathlib import Path

from common.data_runtime import DataStatusTracker, cached_call, safe_call
from common.reporting import format_run_summary


def _assert_contains(text, expected):
    if expected not in text:
        raise AssertionError(f"Expected text to contain: {expected}")


def run_status_tracker_test():
    tracker = DataStatusTracker()
    tracker.success("fund_nav", source="AkShare", detail="2 rows")
    tracker.failure("north_flow", source="AkShare", error=RuntimeError("boom"))
    tracker.skipped("news", source="Tavily", reason="disabled")
    tracker.cache_hit("fund_nav")

    summary = tracker.to_run_summary()
    if summary["modules"] != {"success": 1, "failed": 1, "skipped": 1, "cache_hit": 1}:
        raise AssertionError(f"Unexpected module summary: {summary['modules']}")
    if summary["data_modules"][1]["status"] != "failed":
        raise AssertionError("Expected failed module entry")
    if summary["data_modules"][1]["error_type"] != "RuntimeError":
        raise AssertionError("Expected sanitized error type only")

    rendered = format_run_summary(summary)
    _assert_contains(rendered, "- modules: success=1 failed=1 skipped=1 cache_hit=1")
    _assert_contains(rendered, "- data_module: north_flow | status=failed | source=AkShare | error_type=RuntimeError")
    _assert_contains(rendered, "- data_module: news | status=skipped | source=Tavily | reason=disabled")


def run_safe_call_test():
    tracker = DataStatusTracker()

    result = safe_call("ok_module", lambda: {"value": 1}, fallback={}, tracker=tracker, source="fixture")
    if result != {"value": 1}:
        raise AssertionError("Expected safe_call result")

    result = safe_call(
        "bad_module",
        lambda: (_ for _ in ()).throw(ValueError("private details")),
        fallback={"fallback": True},
        tracker=tracker,
        source="fixture",
    )
    if result != {"fallback": True}:
        raise AssertionError("Expected safe_call fallback")

    summary = tracker.to_run_summary()
    if summary["modules"]["success"] != 1 or summary["modules"]["failed"] != 1:
        raise AssertionError("Expected one success and one failure")


def run_cached_call_test():
    with tempfile.TemporaryDirectory() as tmp:
        tracker = DataStatusTracker()
        calls = {"count": 0}

        def fetch_value():
            calls["count"] += 1
            return {"value": calls["count"]}

        first = cached_call("sample", fetch_value, cache_dir=Path(tmp), ttl_hours=24, tracker=tracker)
        second = cached_call("sample", fetch_value, cache_dir=Path(tmp), ttl_hours=24, tracker=tracker)

        if first != {"value": 1} or second != {"value": 1}:
            raise AssertionError("Expected cached value")
        if calls["count"] != 1:
            raise AssertionError("Expected fetch to be called once")
        if tracker.to_run_summary()["modules"]["cache_hit"] != 1:
            raise AssertionError("Expected one cache hit")


def main():
    run_status_tracker_test()
    run_safe_call_test()
    run_cached_call_test()
    print("Mock runtime test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
