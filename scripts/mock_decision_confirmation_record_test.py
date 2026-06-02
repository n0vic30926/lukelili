#!/usr/bin/env python3
"""Offline tests for sanitized confirmation record persistence."""

import json
import tempfile
from pathlib import Path

from common.decision_confirmation import build_confirmation_state
from decision_tracker import load_confirmation_records, save_confirmation_record


def _assert_contains(text, expected):
    if expected not in text:
        raise AssertionError(f"Expected text to contain: {expected}")


def _assert_not_contains(text, unexpected):
    if unexpected in text:
        raise AssertionError(f"Text should not contain: {unexpected}")


def run_decision_confirmation_record_test():
    packet = {
        "execution_allowed": False,
        "requires_user_confirmation": True,
        "risk_rule_checks": [{"rule": "max_single_position_pct", "status": "missing"}],
        "exposure": {"warnings": [{"type": "single_position_exceeds_rule", "holding_ref": "holding_1"}]},
        "research_synthesis": {
            "confirmation_audit_items": [
                {
                    "type": "data_source_unconfirmed",
                    "role": "review",
                    "source": "report_index",
                    "status": "missing_file",
                }
            ]
        },
        "candidates": [
            {
                "holding_ref": "holding_1",
                "candidate_action": "observe",
                "code": "PRIVATE_A",
                "name": "Private Holding A",
                "required_confirmations": ["user confirms strategy still applies"],
            }
        ],
        "prohibited_actions": ["broker_connection", "order_placement", "automatic_trading"],
    }
    state = build_confirmation_state(packet)
    with tempfile.TemporaryDirectory() as tmp:
        record_path = Path(tmp) / "confirmations.jsonl"
        result = save_confirmation_record(
            state,
            record_path=record_path,
            created_at="2026-06-02T10:00:00+08:00",
            source="mock_decision_support",
        )
        if result["record_path"] != str(record_path):
            raise AssertionError(f"Unexpected record path: {result}")
        lines = record_path.read_text(encoding="utf-8").splitlines()
        if len(lines) != 1:
            raise AssertionError(f"Expected one JSONL record: {lines}")
        raw = lines[0]
        _assert_contains(raw, "pending_user_confirmation")
        _assert_contains(raw, "single_position_exceeds_rule")
        _assert_contains(raw, "review_action_counts")
        _assert_not_contains(raw, "PRIVATE_A")
        _assert_not_contains(raw, "Private Holding A")
        _assert_not_contains(raw, "买入")
        _assert_not_contains(raw, "卖出")

        records = load_confirmation_records(record_path)
        if records[0]["confirmation_status"] != "pending_user_confirmation":
            raise AssertionError(f"Unexpected loaded records: {records}")
        if records[0]["check_count"] != 1 or records[0]["blocker_count"] != 3:
            raise AssertionError(f"Unexpected counts: {records}")
        if records[0]["review_queue_count"] != 4:
            raise AssertionError(f"Unexpected review queue count: {records}")
        if records[0]["review_action_counts"] != {
            "update_local_records": 2,
            "user_confirm": 1,
            "review_risk_rule": 1,
        }:
            raise AssertionError(f"Unexpected review action counts: {records}")
        rendered = json.dumps(records, ensure_ascii=False)
        _assert_not_contains(rendered, "PRIVATE_A")
        _assert_not_contains(rendered, "Private Holding A")


def main():
    run_decision_confirmation_record_test()
    print("Mock decision confirmation record test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
