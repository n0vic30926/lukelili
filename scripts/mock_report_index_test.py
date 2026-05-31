#!/usr/bin/env python3
"""Offline tests for report index summaries."""

import json
import tempfile
from pathlib import Path

from report_index import format_report_index, load_report_index, summarize_reports


def _write_jsonl(path, items):
    with path.open("w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


def _assert_contains(text, expected):
    if expected not in text:
        raise AssertionError(f"Expected text to contain: {expected}")


def run_report_index_test():
    items = [
        {
            "event": "report_written",
            "report_type": "daily",
            "created_at": "2026-05-29T15:30:00+08:00",
            "report_path": "/tmp/daily-2026-05-29.md",
            "run_summary": {
                "modules": {"success": 3, "failed": 1, "skipped": 0, "cache_hit": 0},
                "data_quality": {
                    "fresh": 2,
                    "stale": 1,
                    "unknown": 1,
                    "source_tiers": {"community_data": 3, "news_search": 1},
                },
                "data_modules": [
                    {"module": "fund_nav", "status": "success", "source": "AkShare"},
                    {"module": "north_flow", "status": "failed", "source": "AkShare"},
                ],
            },
        },
        {
            "event": "report_written",
            "report_type": "weekly",
            "created_at": "2026-05-30T11:00:00+08:00",
            "report_path": "/tmp/weekly-2026-05-30.md",
            "run_summary": {
                "modules": {"success": 2, "failed": 0, "skipped": 1, "cache_hit": 1},
                "data_quality": {
                    "fresh": 1,
                    "stale": 0,
                    "unknown": 2,
                    "source_tiers": {"community_data": 2, "news_search": 1},
                },
                "data_modules": [
                    {"module": "industry_intel", "status": "skipped", "source": "Tavily"},
                ],
            },
        },
    ]

    with tempfile.TemporaryDirectory() as tmp:
        index_path = Path(tmp) / "index.jsonl"
        _write_jsonl(index_path, items)
        loaded = load_report_index(index_path)
        summary = summarize_reports(loaded)
        if summary["report_count"] != 2:
            raise AssertionError(f"Unexpected report count: {summary}")
        if summary["failed_modules"] != {"north_flow": 1}:
            raise AssertionError(f"Unexpected failed modules: {summary['failed_modules']}")
        if summary["data_quality"]["fresh"] != 3 or summary["data_quality"]["unknown"] != 3:
            raise AssertionError(f"Unexpected data quality: {summary['data_quality']}")

        output = format_report_index(loaded, limit=2)
        _assert_contains(output, "# Report Index Summary")
        _assert_contains(output, "- Reports: 2")
        _assert_contains(output, "- Data quality: fresh=3 stale=1 unknown=3")
        _assert_contains(output, "- Failed module: north_flow x1")
        _assert_contains(output, "- 2026-05-30T11:00:00+08:00 | weekly | failed=0 | skipped=1")


def main():
    run_report_index_test()
    print("Mock report index test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
