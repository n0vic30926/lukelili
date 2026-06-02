#!/usr/bin/env python3
"""Offline tests for manual decision confirmation workflow state."""

from common.decision_confirmation import build_confirmation_state, format_confirmation_state


def _assert_contains(text, expected):
    if expected not in text:
        raise AssertionError(f"Expected text to contain: {expected}")


def _assert_not_contains(text, unexpected):
    if unexpected in text:
        raise AssertionError(f"Text should not contain: {unexpected}")


def run_decision_confirmation_test():
    packet = {
        "execution_allowed": False,
        "requires_user_confirmation": True,
        "risk_rule_checks": [
            {"rule": "single_loss_pct", "status": "present", "value": 2},
            {"rule": "max_single_position_pct", "status": "missing"},
        ],
        "exposure": {
            "warnings": [
                {
                    "type": "single_position_exceeds_rule",
                    "holding_ref": "holding_1",
                    "actual_pct": 70.0,
                    "limit_pct": 50.0,
                }
            ]
        },
        "candidates": [
            {
                "holding_ref": "holding_1",
                "candidate_action": "observe",
                "required_confirmations": [
                    "user confirms strategy still applies",
                    "user confirms no broker action should be automated",
                ],
            }
        ],
        "prohibited_actions": ["broker_connection", "order_placement", "automatic_trading"],
    }
    state = build_confirmation_state(packet)
    if state["confirmation_status"] != "pending_user_confirmation":
        raise AssertionError(f"Unexpected status: {state}")
    if state["execution_allowed"] is not False:
        raise AssertionError(f"Execution must stay disabled: {state}")
    if state["check_count"] != 2:
        raise AssertionError(f"Unexpected check count: {state}")
    if state["blocker_count"] != 2:
        raise AssertionError(f"Unexpected blocker count: {state}")
    if state["checks"][0]["check_ref"] != "confirmation_1":
        raise AssertionError(f"Expected anonymized check ref: {state}")

    output = format_confirmation_state(state)
    _assert_contains(output, "## Manual Confirmation Workflow")
    _assert_contains(output, "confirmation_status=pending_user_confirmation")
    _assert_contains(output, "execution_allowed=false")
    _assert_contains(output, "confirmation_1 status=pending")
    _assert_contains(output, "missing_risk_rule rule=max_single_position_pct")
    _assert_contains(output, "single_position_exceeds_rule holding_ref=holding_1")
    _assert_not_contains(output, "PRIVATE")
    _assert_not_contains(output, "买入")
    _assert_not_contains(output, "卖出")
    _assert_not_contains(output, "自动交易")


def main():
    run_decision_confirmation_test()
    print("Mock decision confirmation test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
