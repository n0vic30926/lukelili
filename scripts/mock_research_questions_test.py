#!/usr/bin/env python3
"""Offline tests for per-role research question generation."""

from common.research_questions import build_role_research_questions


def _assert_contains(text, expected):
    if expected not in text:
        raise AssertionError(f"Expected text to contain: {expected}")


def _assert_not_contains(text, unexpected):
    if unexpected in text:
        raise AssertionError(f"Text should not contain: {unexpected}")


def run_research_questions_test():
    macro_questions = build_role_research_questions(
        "macro",
        [
            {"name": "macro_rates", "status": "missing_dependency"},
            {"name": "fx_rates", "status": "available"},
            {"name": "liquidity_indicators", "status": "failed"},
        ],
    )
    macro_text = "\n".join(macro_questions)
    _assert_contains(macro_text, "rate-sensitive exposure")
    _assert_contains(macro_text, "FX translation")
    _assert_contains(macro_text, "refresh before judgment")

    security_questions = build_role_research_questions(
        "security",
        [
            {"name": "financial_statements", "status": "available"},
            {"name": "announcements", "status": "missing_dependency"},
            {"name": "valuation_metrics", "status": "empty"},
        ],
    )
    security_text = "\n".join(security_questions)
    _assert_contains(security_text, "fundamental quality")
    _assert_contains(security_text, "announcements")
    _assert_contains(security_text, "valuation context")

    industry_questions = build_role_research_questions(
        "industry",
        [
            {"name": "industry_rotation", "status": "available"},
            {"name": "concept_rotation", "status": "empty"},
            {"name": "news_search", "status": "missing_key"},
        ],
    )
    industry_text = "\n".join(industry_questions)
    _assert_contains(industry_text, "industry fund-flow")
    _assert_contains(industry_text, "theme rotation")
    _assert_contains(industry_text, "external news")

    risk_questions = build_role_research_questions(
        "risk",
        [
            {"name": "risk_rules", "status": "available"},
            {"name": "portfolio_exposure", "status": "available"},
            {"name": "market_quotes", "status": "missing_dependency"},
            {"name": "factor_exposure", "status": "available"},
        ],
    )
    risk_text = "\n".join(risk_questions)
    _assert_contains(risk_text, "hard risk controls")
    _assert_contains(risk_text, "portfolio concentration")
    _assert_contains(risk_text, "market movement")
    _assert_contains(risk_text, "factor concentration")

    unknown_questions = build_role_research_questions("unknown", [{"name": "x", "status": "available"}])
    if unknown_questions:
        raise AssertionError(f"Unexpected unknown-role questions: {unknown_questions}")

    all_text = "\n".join(macro_questions + security_questions + industry_questions + risk_questions + unknown_questions)
    _assert_not_contains(all_text, "买入")
    _assert_not_contains(all_text, "卖出")
    _assert_not_contains(all_text, "自动交易")


def main():
    run_research_questions_test()
    print("Mock research questions test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
