#!/usr/bin/env python3
"""Offline tests for historical report and discipline review summaries."""

import json
import tempfile
from pathlib import Path

from review_history import format_history_review, load_decision_records, summarize_history


def _write_json(path, item):
    path.write_text(json.dumps(item, ensure_ascii=False), encoding="utf-8")


def _assert_contains(text, expected):
    if expected not in text:
        raise AssertionError(f"Expected text to contain: {expected}")


def _assert_not_contains(text, unexpected):
    if unexpected in text:
        raise AssertionError(f"Text should not contain: {unexpected}")


def run_history_review_test():
    reports = [
        {
            "event": "report_written",
            "report_type": "daily",
            "report_date": "2026-05-27",
            "created_at": "2026-05-27T15:30:00+08:00",
            "report_path": "/tmp/daily-2026-05-27.md",
            "run_summary": {
                "modules": {"success": 2, "failed": 1, "skipped": 0, "cache_hit": 0},
                "data_quality": {"fresh": 2, "stale": 0, "unknown": 1, "source_tiers": {"community_data": 3}},
                "data_modules": [{"module": "north_flow", "status": "failed"}],
            },
        },
        {
            "event": "report_written",
            "report_type": "daily",
            "report_date": "2026-05-28",
            "created_at": "2026-05-28T15:30:00+08:00",
            "report_path": "/tmp/daily-2026-05-28.md",
            "run_summary": {
                "modules": {"success": 1, "failed": 1, "skipped": 1, "cache_hit": 0},
                "data_quality": {"fresh": 1, "stale": 1, "unknown": 1, "source_tiers": {"community_data": 2, "news_search": 1}},
                "data_modules": [{"module": "north_flow", "status": "failed"}],
            },
        },
        {
            "event": "report_written",
            "report_type": "weekly",
            "report_date": "2026-05-30",
            "created_at": "2026-05-30T11:00:00+08:00",
            "report_path": "/tmp/weekly-2026-05-30.md",
            "run_summary": {
                "modules": {"success": 2, "failed": 0, "skipped": 1, "cache_hit": 1},
                "data_quality": {"fresh": 1, "stale": 0, "unknown": 2, "source_tiers": {"community_data": 2, "news_search": 1}},
                "data_modules": [],
            },
        },
    ]

    with tempfile.TemporaryDirectory() as tmp:
        decision_dir = Path(tmp) / "decision_track"
        decision_dir.mkdir()
        _write_json(
            decision_dir / "2026-05-28.json",
            {
                "date": "2026-05-28",
                "holdings": [
                    {"code": "SECRET1", "name": "Private Fund", "strategy_type": "dca", "cost_basis": 999999, "shares": 123},
                    {"code": "SECRET2", "name": "Private Trial", "strategy_type": "trial", "cost_basis": 888888, "shares": 456},
                ],
            },
        )
        _write_json(
            decision_dir / "confirmations.jsonl",
            {
                "event": "confirmation_state_recorded",
                "created_at": "2026-05-28T16:00:00+08:00",
                "confirmation_status": "pending_user_confirmation",
                "check_count": 2,
                "blocker_count": 1,
                "blocker_types": ["missing_risk_rule"],
            },
        )
        decisions = load_decision_records(decision_dir)
        summary = summarize_history(reports, decisions)
        if summary["report_continuity"]["current_streak_days"] != 2:
            raise AssertionError(f"Unexpected continuity: {summary['report_continuity']}")
        if summary["repeated_failures"] != {"north_flow": 2}:
            raise AssertionError(f"Unexpected failures: {summary['repeated_failures']}")
        if summary["strategy_counts"] != {"dca": 1, "trial": 1}:
            raise AssertionError(f"Unexpected strategy counts: {summary['strategy_counts']}")
        if summary["confirmation_records"]["pending_user_confirmation"] != 1:
            raise AssertionError(f"Unexpected confirmation records: {summary['confirmation_records']}")
        if summary["confirmation_blockers"]["missing_risk_rule"] != 1:
            raise AssertionError(f"Unexpected confirmation blockers: {summary['confirmation_blockers']}")

        output = format_history_review(summary)
        _assert_contains(output, "# History Review Summary")
        _assert_contains(output, "- Current daily report streak: 2 day(s)")
        _assert_contains(output, "- Repeated failure: north_flow x2")
        _assert_contains(output, "- Data quality totals: fresh=4 stale=1 unknown=4")
        _assert_contains(output, "- Strategy records: dca=1 trial=1")
        _assert_contains(output, "- Confirmation records: pending_user_confirmation=1")
        _assert_contains(output, "- Confirmation blockers: missing_risk_rule=1")
        _assert_not_contains(output, "SECRET")
        _assert_not_contains(output, "999999")
        _assert_not_contains(output, "Private Fund")


def main():
    run_history_review_test()
    print("Mock history review test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
