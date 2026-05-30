#!/usr/bin/env python3
"""Offline checks for runtime status, cache, and quality helpers."""

import time

from common.config_loader import load_settings
from common.data_runtime import DataStatusTracker, cached_call
from common.data_quality import summarize_quality


def main():
    settings = load_settings()
    tracker = DataStatusTracker()
    calls = {"count": 0}

    def producer():
        calls["count"] += 1
        return {"value": 42, "created": time.time()}

    key = "mock_runtime_test:value"
    first = cached_call(settings, tracker, "mock_data", "local portfolio", key, producer, None)
    second = cached_call(settings, tracker, "mock_data", "local portfolio", key, producer, None)

    if first is None or second is None:
        print("FAIL cached_call returned None")
        return 1

    counts = tracker.counts()
    if counts.get("ok", 0) < 2:
        print(f"FAIL expected at least 2 ok records, got {counts}")
        return 1

    summary, _ = summarize_quality(tracker.records)
    if summary["total"] < 2:
        print(f"FAIL expected quality records, got {summary}")
        return 1

    print("Mock runtime test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
