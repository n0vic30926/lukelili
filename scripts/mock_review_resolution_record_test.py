#!/usr/bin/env python3
"""Offline tests for sanitized manual-review resolution records."""

import json
import tempfile
from pathlib import Path

from decision_tracker import load_review_resolution_records, save_review_resolution_record


def _assert_contains(text, expected):
    if expected not in text:
        raise AssertionError(f"Expected text to contain: {expected}")


def _assert_not_contains(text, unexpected):
    if unexpected in text:
        raise AssertionError(f"Text should not contain: {unexpected}")


def run_review_resolution_record_test():
    resolution = {
        "review_ref": "review_4",
        "action": "refresh_data",
        "outcome": "still_blocked",
        "reason_code": "missing_dependency",
        "private_note": "PRIVATE_A Private Holding A 999999 shares",
        "prohibited_actions": ["broker_connection", "order_placement", "automatic_trading"],
    }
    with tempfile.TemporaryDirectory() as tmp:
        record_path = Path(tmp) / "review_resolutions.jsonl"
        result = save_review_resolution_record(
            resolution,
            record_path=record_path,
            created_at="2026-06-03T10:00:00+08:00",
            source="mock_manual_review",
        )
        if result["record_path"] != str(record_path):
            raise AssertionError(f"Unexpected record path: {result}")
        raw = record_path.read_text(encoding="utf-8")
        _assert_contains(raw, "manual_review_resolution_recorded")
        _assert_contains(raw, "review_4")
        _assert_contains(raw, "still_blocked")
        _assert_contains(raw, "automatic_trading")
        _assert_not_contains(raw, "PRIVATE_A")
        _assert_not_contains(raw, "Private Holding A")
        _assert_not_contains(raw, "999999")
        _assert_not_contains(raw, "买入")
        _assert_not_contains(raw, "卖出")

        records = load_review_resolution_records(record_path)
        if records[0]["outcome"] != "still_blocked":
            raise AssertionError(f"Unexpected loaded record: {records}")
        if records[0]["execution_allowed"] is not False:
            raise AssertionError(f"Resolution must not allow execution: {records}")
        rendered = json.dumps(records, ensure_ascii=False)
        _assert_not_contains(rendered, "PRIVATE_A")
        _assert_not_contains(rendered, "Private Holding A")


def main():
    run_review_resolution_record_test()
    print("Mock review resolution record test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
