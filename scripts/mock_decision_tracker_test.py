#!/usr/bin/env python3
"""Offline tests for local decision action tracking."""

import json
import tempfile
from pathlib import Path

import decision_tracker


def run_append_user_action_test():
    with tempfile.TemporaryDirectory() as tmp:
        decision_tracker.TRACK_DIR = Path(tmp)
        path = decision_tracker.append_user_action(
            {
                "action_type": "upgrade_strategy",
                "strategy_type": "trial",
                "status": "pending",
                "requires_user_confirmation": True,
                "code": "EXAMPLE",
                "amount": 100,
                "rationale": "Synthetic private rationale.",
                "outcome_status": "reviewed",
                "outcome_review": "Synthetic private outcome.",
            },
            record_date="2026-01-02",
        )
        record = json.loads(Path(path).read_text(encoding="utf-8"))
        actions = record.get("user_actions", [])
        if len(actions) != 1:
            raise AssertionError("Expected one user action")
        action = actions[0]
        if action.get("status") != "pending":
            raise AssertionError("Expected pending action status")
        if action.get("requires_user_confirmation") is not True:
            raise AssertionError("Expected explicit confirmation flag")
        if action.get("outcome_status") != "reviewed":
            raise AssertionError("Expected outcome status to be preserved")
        if record.get("date") != "2026-01-02":
            raise AssertionError("Expected record date to be preserved")


def run_save_preserves_user_actions_test():
    with tempfile.TemporaryDirectory() as tmp:
        decision_tracker.TRACK_DIR = Path(tmp)
        today = decision_tracker.datetime.now().strftime("%Y-%m-%d")
        decision_tracker.append_user_action(
            {
                "action_type": "continue_dca",
                "strategy_type": "dca",
                "status": "confirmed",
                "requires_user_confirmation": False,
                "code": "EXAMPLE",
            },
            record_date=today,
        )
        portfolio_path = Path(tmp) / "portfolio.json"
        portfolio_path.write_text(
            json.dumps(
                {
                    "holdings": [
                        {
                            "code": "EXAMPLE",
                            "name": "Example Fund",
                            "strategy_type": "dca",
                            "strategy_label": "example dca",
                            "cost_basis": 100,
                            "shares": 10,
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        saved_path = decision_tracker.save_daily_decisions(str(portfolio_path))
        record = json.loads(Path(saved_path).read_text(encoding="utf-8"))
        if len(record.get("user_actions", [])) != 1:
            raise AssertionError("Expected save_daily_decisions to preserve user actions")


def main():
    run_append_user_action_test()
    run_save_preserves_user_actions_test()
    print("Mock decision tracker test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
