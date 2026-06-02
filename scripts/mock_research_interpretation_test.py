#!/usr/bin/env python3
"""Offline tests for role data-state interpretation."""

from common.research_interpretation import interpret_role_data_state


def _assert_contains(text, expected):
    if expected not in text:
        raise AssertionError(f"Expected text to contain: {expected}")


def _assert_not_contains(text, unexpected):
    if unexpected in text:
        raise AssertionError(f"Text should not contain: {unexpected}")


def run_research_interpretation_test():
    macro_notes = interpret_role_data_state(
        "macro",
        [
            {"name": "macro_rates", "status": "missing_dependency"},
            {"name": "fx_rates", "status": "available"},
            {"name": "liquidity_indicators", "status": "failed"},
        ],
    )
    macro_text = "\n".join(macro_notes)
    _assert_contains(macro_text, "macro_rates unavailable")
    _assert_contains(macro_text, "fx_rates available")
    _assert_contains(macro_text, "liquidity_indicators unavailable")
    _assert_contains(macro_text, "unconfirmed")

    etf_notes = interpret_role_data_state(
        "etf",
        [
            {"name": "etf_quotes", "status": "available"},
            {"name": "premium_discount", "status": "empty"},
            {"name": "liquidity_metrics", "status": "available"},
        ],
    )
    etf_text = "\n".join(etf_notes)
    _assert_contains(etf_text, "etf_quotes available")
    _assert_contains(etf_text, "premium_discount unavailable")
    _assert_contains(etf_text, "liquidity_metrics available")

    industry_notes = interpret_role_data_state(
        "industry",
        [
            {"name": "industry_rotation", "status": "available"},
            {"name": "concept_rotation", "status": "failed"},
            {"name": "news_search", "status": "missing_key"},
        ],
    )
    industry_text = "\n".join(industry_notes)
    _assert_contains(industry_text, "industry_rotation available")
    _assert_contains(industry_text, "concept_rotation unavailable")
    _assert_contains(industry_text, "news_search unavailable")

    risk_notes = interpret_role_data_state(
        "risk",
        [
            {"name": "risk_rules", "status": "available"},
            {"name": "portfolio_exposure", "status": "available"},
            {"name": "market_quotes", "status": "missing_dependency"},
            {"name": "factor_exposure", "status": "available"},
        ],
    )
    risk_text = "\n".join(risk_notes)
    _assert_contains(risk_text, "risk_rules available")
    _assert_contains(risk_text, "portfolio_exposure available")
    _assert_contains(risk_text, "market_quotes unavailable")
    _assert_contains(risk_text, "factor_exposure available")

    review_notes = interpret_role_data_state(
        "review",
        [
            {"name": "report_index", "status": "available"},
            {"name": "report_continuity", "status": "empty"},
            {"name": "decision_records", "status": "available"},
            {"name": "confirmation_records", "status": "missing_file"},
        ],
    )
    review_text = "\n".join(review_notes)
    _assert_contains(review_text, "report_index available")
    _assert_contains(review_text, "report_continuity unavailable")
    _assert_contains(review_text, "decision_records available")
    _assert_contains(review_text, "confirmation_records unavailable")

    unknown_notes = interpret_role_data_state("unknown", [{"name": "x", "status": "available"}])
    if unknown_notes:
        raise AssertionError(f"Unexpected unknown-role notes: {unknown_notes}")

    all_text = "\n".join(macro_notes + etf_notes + industry_notes + risk_notes + review_notes + unknown_notes)
    _assert_not_contains(all_text, "买入")
    _assert_not_contains(all_text, "卖出")
    _assert_not_contains(all_text, "自动交易")


def main():
    run_research_interpretation_test()
    print("Mock research interpretation test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
