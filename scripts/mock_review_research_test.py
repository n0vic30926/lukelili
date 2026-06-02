#!/usr/bin/env python3
"""Offline tests for Review role research data adapter."""

from review_research import fetch_review_research


def _assert_contains(text, expected):
    if expected not in text:
        raise AssertionError(f"Expected text to contain: {expected}")


def _assert_not_contains(text, unexpected):
    if unexpected in text:
        raise AssertionError(f"Text should not contain: {unexpected}")


def run_review_research_test():
    reports = [
        {
            "event": "report_written",
            "report_type": "daily",
            "report_date": "2026-05-27",
            "created_at": "2026-05-27T15:30:00+08:00",
            "run_summary": {
                "data_quality": {"fresh": 2, "stale": 0, "unknown": 1},
                "data_modules": [{"module": "north_flow", "status": "failed"}],
            },
        },
        {
            "event": "report_written",
            "report_type": "daily",
            "report_date": "2026-05-28",
            "created_at": "2026-05-28T15:30:00+08:00",
            "run_summary": {
                "data_quality": {"fresh": 1, "stale": 1, "unknown": 1},
                "data_modules": [{"module": "north_flow", "status": "failed"}],
            },
        },
    ]
    decisions = [
        {
            "record_type": "daily_decision_snapshot",
            "date": "2026-05-28",
            "strategies": ["dca", "trial"],
            "private_name": "Private Fund",
        },
        {
            "record_type": "confirmation_state",
            "date": "2026-05-28",
            "confirmation_status": "pending_user_confirmation",
            "check_count": 2,
            "blocker_count": 1,
            "blocker_types": ["missing_risk_rule"],
        },
    ]

    result = fetch_review_research(report_items=reports, decision_records=decisions)
    if result["status"] != "ok":
        raise AssertionError(f"Expected ok result: {result}")

    observations = "\n".join(result["observations"])
    _assert_contains(observations, "reports=2")
    _assert_contains(observations, "decision_records=2")
    _assert_contains(observations, "current_daily_streak=2")
    _assert_contains(observations, "repeated_failure_modules=1")
    _assert_contains(observations, "data_quality_fresh=3")
    _assert_contains(observations, "data_quality_stale=1")
    _assert_contains(observations, "data_quality_unknown=2")
    _assert_contains(observations, "confirmation_records=pending_user_confirmation:1")
    _assert_contains(observations, "confirmation_blockers=missing_risk_rule:1")

    evidence = "\n".join(item["label"] for item in result["evidence"])
    _assert_contains(evidence, "reports.index")
    _assert_contains(evidence, "review.report_continuity")
    _assert_contains(evidence, "review.decision_records")
    _assert_contains(evidence, "review.confirmation_records")

    data_sources = "\n".join(
        f"{item['name']} {item['source']} {item['status']}" for item in result["data_sources"]
    )
    _assert_contains(data_sources, "report_index local available")
    _assert_contains(data_sources, "report_continuity local available")
    _assert_contains(data_sources, "decision_records local available")
    _assert_contains(data_sources, "confirmation_records local available")

    all_text = observations + "\n" + evidence + "\n" + data_sources
    _assert_not_contains(all_text, "Private Fund")
    _assert_not_contains(all_text, "SECRET")
    _assert_not_contains(all_text, "买入")
    _assert_not_contains(all_text, "卖出")
    _assert_not_contains(all_text, "自动交易")

    empty = fetch_review_research(report_items=[], decision_records=[])
    if empty["status"] != "skipped":
        raise AssertionError(f"Expected skipped empty result: {empty}")
    _assert_contains(" ".join(empty["limitations"]), "no archived report index records")
    _assert_contains(" ".join(empty["limitations"]), "no private decision records")


def main():
    run_review_research_test()
    print("Mock review research test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
