#!/usr/bin/env python3
"""Offline tests for role data source requirement summaries."""

from common.data_sources import role_data_requirements, summarize_role_data_requirements


def _assert_contains(text, expected):
    if expected not in text:
        raise AssertionError(f"Expected text to contain: {expected}")


def run_data_sources_test():
    security = role_data_requirements("security")
    names = [item["name"] for item in security]
    for expected in [
        "portfolio_context",
        "financial_statements",
        "announcements",
        "valuation_metrics",
        "security_market_quotes",
        "research_reports",
    ]:
        if expected not in names:
            raise AssertionError(f"Missing security data requirement {expected}: {security}")

    summary = summarize_role_data_requirements("security", env={})
    rendered = "\n".join(
        f"{item['name']} source={item['source']} status={item['status']} tier={item['source_tier']}"
        for item in summary
    )
    _assert_contains(rendered, "portfolio_context source=local status=available tier=local_user_data")
    _assert_contains(rendered, "financial_statements source=AkShare status=")
    _assert_contains(rendered, "announcements source=AkShare status=")
    _assert_contains(rendered, "valuation_metrics source=AkShare status=")
    _assert_contains(rendered, "security_market_quotes source=AkShare status=")
    _assert_contains(rendered, "research_reports source=AkShare status=")

    industry = summarize_role_data_requirements("industry", env={})
    industry_rendered = "\n".join(
        f"{item['name']} source={item['source']} status={item['status']} tier={item['source_tier']}"
        for item in industry
    )
    _assert_contains(industry_rendered, "news_search source=Tavily status=missing_key tier=news_search")
    _assert_contains(industry_rendered, "industry_rotation source=AkShare status=")
    _assert_contains(industry_rendered, "concept_rotation source=AkShare status=")
    if "tvly" + "-" in industry_rendered:
        raise AssertionError("Data source summaries must not expose API key values")

    risk = summarize_role_data_requirements("risk", env={})
    risk_rendered = "\n".join(
        f"{item['name']} source={item['source']} status={item['status']} tier={item['source_tier']}"
        for item in risk
    )
    _assert_contains(risk_rendered, "risk_rules source=local status=available tier=local_user_data")
    _assert_contains(risk_rendered, "portfolio_exposure source=local status=available tier=local_user_data")
    _assert_contains(risk_rendered, "market_quotes source=AkShare status=")
    _assert_contains(risk_rendered, "factor_exposure source=local status=available tier=local_user_data")

    review = summarize_role_data_requirements("review", env={})
    review_rendered = "\n".join(
        f"{item['name']} source={item['source']} status={item['status']} tier={item['source_tier']}"
        for item in review
    )
    _assert_contains(review_rendered, "report_index source=local status=available tier=local_user_data")
    _assert_contains(review_rendered, "report_continuity source=local status=available tier=local_user_data")
    _assert_contains(review_rendered, "decision_records source=local status=available tier=local_user_data")
    _assert_contains(review_rendered, "confirmation_records source=local status=available tier=local_user_data")


def main():
    run_data_sources_test()
    print("Mock data sources test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
