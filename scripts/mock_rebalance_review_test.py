#!/usr/bin/env python3
"""Offline tests for anonymized target-allocation drift review."""

from rebalance_review import build_rebalance_review, format_rebalance_review


def _assert_contains(text, expected):
    if expected not in text:
        raise AssertionError(f"Expected text to contain: {expected}")


def _assert_not_contains(text, unexpected):
    if unexpected in text:
        raise AssertionError(f"Text should not contain: {unexpected}")


def run_rebalance_review_test():
    portfolio = {
        "cash": {"amount": 100, "target_weight_pct": 10},
        "risk_rules": {"rebalance_tolerance_pct": 5},
        "holdings": [
            {
                "code": "PRIVATE_A",
                "name": "Private Growth",
                "cost_basis": 700,
                "target_weight_pct": 60,
            },
            {
                "code": "PRIVATE_B",
                "name": "Private Income",
                "cost_basis": 200,
                "target_weight_pct": 30,
            },
            {
                "code": "PRIVATE_C",
                "name": "Private Missing Target",
                "cost_basis": 0,
            },
        ],
    }

    review = build_rebalance_review(portfolio)
    if review["reviewed_position_count"] != 3:
        raise AssertionError(f"Expected cash plus two target holdings: {review}")
    if review["missing_target_refs"] != ["holding_3"]:
        raise AssertionError(f"Expected missing target ref: {review}")
    if review["max_abs_drift_pct"] != 10.0:
        raise AssertionError(f"Unexpected max drift: {review}")
    if review["overweight_count"] != 1:
        raise AssertionError(f"Expected one overweight item: {review}")
    if review["underweight_count"] != 1:
        raise AssertionError(f"Expected one underweight item: {review}")
    if review["in_tolerance_count"] != 1:
        raise AssertionError(f"Expected one in-tolerance item: {review}")
    if review["decision_signals"][0]["signal"] != "rebalance_review":
        raise AssertionError(f"Expected rebalance review signal: {review}")
    if review["decision_signals"][0]["requires_user_confirmation"] is not True:
        raise AssertionError(f"Expected manual confirmation signal: {review}")
    if review["boundary"]["execution_allowed"] is not False:
        raise AssertionError(f"Rebalance review must not be executable: {review}")

    output = format_rebalance_review(review)
    _assert_contains(output, "# Rebalance Review")
    _assert_contains(output, "- tolerance_pct=5.0")
    _assert_contains(output, "- max_abs_drift_pct=10.0")
    _assert_contains(output, "- missing_target_refs=holding_3")
    _assert_contains(output, "position_ref=holding_1")
    _assert_contains(output, "position_ref=holding_2")
    _assert_contains(output, "signal=rebalance_review")
    _assert_contains(output, "requires_user_confirmation=true")
    _assert_contains(output, "- execution_allowed=false")
    for unexpected in ["PRIVATE_A", "Private Growth", "买入", "卖出", "下单"]:
        _assert_not_contains(output, unexpected)


def main():
    run_rebalance_review_test()
    print("Mock rebalance review test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
