#!/usr/bin/env python3
"""Offline tests for cross-role research synthesis."""

from common.research_synthesis import synthesize_research_result


def _assert_contains(text, expected):
    if expected not in text:
        raise AssertionError(f"Expected text to contain: {expected}")


def _assert_not_contains(text, unexpected):
    if unexpected in text:
        raise AssertionError(f"Text should not contain: {unexpected}")


def run_research_synthesis_test():
    research_result = {
        "role_results": [
            {
                "role": "risk",
                "status": "ok",
                "evidence": [
                    {"label": "portfolio.risk_rules", "source_tier": "local_user_data", "freshness": "fresh"},
                    {"label": "external rumor", "source_tier": "news_search", "freshness": "unknown"},
                ],
                "data_sources": [
                    {"name": "portfolio_exposure", "status": "available"},
                    {"name": "market_quotes", "status": "missing_dependency"},
                ],
            },
            {
                "role": "review",
                "status": "skipped",
                "evidence": [{"label": "reports.index", "source_tier": "local_user_data", "freshness": "unknown"}],
                "data_sources": [
                    {"name": "report_index", "status": "missing_file"},
                    {"name": "confirmation_records", "status": "empty"},
                ],
            },
        ]
    }
    summary = synthesize_research_result(research_result)
    if summary["role_count"] != 2:
        raise AssertionError(f"Unexpected role count: {summary}")
    if summary["role_status_counts"] != {"ok": 1, "skipped": 1}:
        raise AssertionError(f"Unexpected role status counts: {summary}")
    if summary["data_source_status_counts"] != {"available": 1, "empty": 1, "missing_dependency": 1, "missing_file": 1}:
        raise AssertionError(f"Unexpected source status counts: {summary}")

    gaps = "\n".join(item["source_ref"] + " " + item["status"] for item in summary["unavailable_sources"])
    _assert_contains(gaps, "risk.market_quotes missing_dependency")
    _assert_contains(gaps, "review.report_index missing_file")
    _assert_contains(gaps, "review.confirmation_records empty")

    audit = "\n".join(
        f"{item['type']} {item.get('role')} {item.get('source', '')} {item.get('status')}"
        for item in summary["confirmation_audit_items"]
    )
    _assert_contains(audit, "data_source_unconfirmed risk market_quotes missing_dependency")
    _assert_contains(audit, "role_status_unconfirmed review  skipped")

    evidence = "\n".join(item["label"] for item in summary["ranked_evidence"])
    _assert_contains(evidence, "portfolio.risk_rules")
    _assert_contains(evidence, "reports.index")
    _assert_not_contains(evidence + gaps + audit, "PRIVATE")
    _assert_not_contains(evidence + gaps + audit, "买入")
    _assert_not_contains(evidence + gaps + audit, "卖出")
    _assert_not_contains(evidence + gaps + audit, "自动交易")


def main():
    run_research_synthesis_test()
    print("Mock research synthesis test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
