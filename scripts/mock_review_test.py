#!/usr/bin/env python3
"""Offline test for historical review summaries."""

import json
import tempfile
from pathlib import Path

from review_history import format_review, load_decision_records


def _assert_contains(text, expected):
    if expected not in text:
        raise AssertionError(f"Expected review to contain: {expected}")


def run_format_review_test():
    report_records = [
        {
            "type": "daily",
            "path": "reports/daily/daily-2026-01-01.md",
            "created_at": "2026-01-01T15:30:00",
            "status_counts": {"ok": 3, "failed": 1, "skipped": 1},
        },
        {
            "type": "weekly",
            "path": "reports/weekly/weekly-2026-01-03.md",
            "created_at": "2026-01-03T11:00:00",
            "status_counts": {"ok": 2, "failed": 0, "skipped": 1},
        },
    ]
    decision_records = [
        {
            "date": "2026-01-01",
            "holdings": [
                {"code": "EX1", "strategy_type": "dca", "cost_basis": 100, "shares": 10},
                {"code": "EX2", "strategy_type": "trial", "cost_basis": 50, "shares": 5},
            ],
        }
    ]
    review = format_review(Path("reports/index.jsonl"), report_records, Path("data/private/decision_track"), decision_records)
    _assert_contains(review, "历史复盘摘要")
    _assert_contains(review, "报告数量: 2")
    _assert_contains(review, "strategy_type 分布")
    _assert_contains(review, "DCA记录存在")
    if "cost_basis" in review or "shares" in review:
        raise AssertionError("Review leaked raw asset field names")


def run_load_private_records_test():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "2026-01-01.json"
        path.write_text(
            json.dumps({"date": "2026-01-01", "holdings": [{"code": "EX", "strategy_type": "dca"}]}),
            encoding="utf-8",
        )
        _, records = load_decision_records(decision_dir=tmp)
        if len(records) != 1:
            raise AssertionError("Expected one private decision record")


def main():
    run_format_review_test()
    run_load_private_records_test()
    print("Mock review test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
