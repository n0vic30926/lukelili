#!/usr/bin/env python3
"""Offline tests for report archiving and structured logging."""

import json
import tempfile
from pathlib import Path

from common.reporting import write_report


def _read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _assert_contains(text, expected):
    if expected not in text:
        raise AssertionError(f"Expected text to contain: {expected}")


def run_report_archive_test():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        settings = {
            "daily_report_dir": str(root / "reports" / "daily"),
            "weekly_report_dir": str(root / "reports" / "weekly"),
            "report_index_path": str(root / "reports" / "index.jsonl"),
            "log_dir": str(root / "logs"),
        }
        result = write_report(
            "daily",
            "# Daily Body\n\nMarket content.",
            settings=settings,
            run_summary={
                "portfolio_source": "example",
                "is_example_data": True,
                "dependencies": {"akshare": "available"},
                "modules": {"success": 2, "failed": 1, "skipped": 0},
            },
            created_at="2026-05-31T09:30:00+08:00",
        )

        report_path = Path(result["report_path"])
        if not report_path.exists():
            raise AssertionError("Expected report file to be written")
        if report_path.name != "daily-2026-05-31.md":
            raise AssertionError(f"Unexpected report filename: {report_path.name}")

        report_text = report_path.read_text(encoding="utf-8")
        _assert_contains(report_text, "## 运行摘要")
        _assert_contains(report_text, "- portfolio_source: example")
        _assert_contains(report_text, "- is_example_data: true")
        _assert_contains(report_text, "- modules: success=2 failed=1 skipped=0")
        _assert_contains(report_text, "# Daily Body")

        index_items = _read_jsonl(root / "reports" / "index.jsonl")
        if index_items[0]["report_type"] != "daily":
            raise AssertionError("Expected index item report_type=daily")
        if index_items[0]["report_path"] != str(report_path):
            raise AssertionError("Expected index item to reference report path")

        log_items = _read_jsonl(root / "logs" / "finance-agent.jsonl")
        if log_items[0]["event"] != "report_written":
            raise AssertionError("Expected report_written log event")
        if log_items[0]["report_type"] != "daily":
            raise AssertionError("Expected log item report_type=daily")


def main():
    run_report_archive_test()
    print("Mock reporting test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
