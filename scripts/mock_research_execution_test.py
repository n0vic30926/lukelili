#!/usr/bin/env python3
"""Offline tests for L4 research role execution and report merging."""

from research_dispatch import build_research_plan, execute_research_plan, format_research_report


def _assert_contains(text, expected):
    if expected not in text:
        raise AssertionError(f"Expected text to contain: {expected}")


def _assert_not_contains(text, unexpected):
    if unexpected in text:
        raise AssertionError(f"Text should not contain: {unexpected}")


def run_research_execution_test():
    portfolio = {
        "holdings": [
            {
                "code": "PRIVATE_A",
                "name": "Private Holding A",
                "type": "stock",
                "proxy_etf": "PRIVATE_ETF",
                "strategy_type": "dca",
                "factor_profile": {"type": "qdii_us_equity"},
            }
        ],
        "watchlist": [{"code": "PRIVATE_W", "name": "Private Watch"}],
        "risk_rules": {"single_loss_pct": 2, "daily_loss_pct": 6},
    }
    plan = build_research_plan("宏观 利率 汇率 流动性 个股 财报 ETF 组合风险 历史复盘 行业", portfolio)

    def fake_risk(task, portfolio_data):
        return {
            "status": "ok",
            "observations": ["risk rules present", "one holding in portfolio"],
            "evidence": [
                {"label": "external rumor", "source_tier": "news_search", "freshness": "unknown"},
                {"label": "portfolio.risk_rules", "source_tier": "local_user_data", "freshness": "fresh"},
            ],
            "limitations": ["no live market data"],
        }

    def fake_review(task, portfolio_data):
        return {
            "status": "ok",
            "observations": ["report continuity checked"],
            "evidence": ["reports/index.jsonl"],
            "limitations": [],
        }

    def fake_industry(task, portfolio_data):
        return {
            "status": "skipped",
            "observations": ["news disabled"],
            "evidence": ["settings.enable_news=false"],
            "data_sources": [
                {"name": "industry_rotation", "source": "AkShare", "status": "missing_dependency", "source_tier": "community_data"},
                {"name": "concept_rotation", "source": "AkShare", "status": "missing_dependency", "source_tier": "community_data"},
                {"name": "news_search", "source": "Tavily", "status": "missing_key", "source_tier": "news_search"},
                {"name": "news_results", "source": "Tavily", "status": "missing_key", "source_tier": "news_search"},
            ],
            "limitations": ["no external news fetched"],
        }

    result = execute_research_plan(
        plan,
        portfolio,
        runners={"risk": fake_risk, "review": fake_review, "industry": fake_industry},
    )
    if [item["role"] for item in result["role_results"]] != ["macro", "industry", "security", "etf", "risk", "review"]:
        raise AssertionError(f"Unexpected role order: {result}")
    if result["requires_user_confirmation"] is not True:
        raise AssertionError(f"Research result must require user confirmation: {result}")

    output = format_research_report(result)
    _assert_contains(output, "# Research Execution Report")
    _assert_contains(output, "## Research Coverage Matrix")
    _assert_contains(output, "coverage_pct=")
    _assert_contains(output, "source=news_search status=missing_key priority=high")
    _assert_contains(output, "## macro")
    _assert_contains(output, "macro_data_status=")
    _assert_contains(output, "macro_rates | source=AkShare | status=")
    _assert_contains(output, "inflation_indicators | source=AkShare | status=")
    _assert_contains(output, "pmi_indicators | source=AkShare | status=")
    _assert_contains(output, "- interpretation:")
    _assert_contains(output, "macro_rates")
    _assert_contains(output, "impact path")
    _assert_contains(output, "- research questions:")
    _assert_contains(output, "rate-sensitive exposure")
    _assert_contains(output, "## industry")
    _assert_contains(output, "- status: skipped")
    _assert_contains(output, "industry_rotation | source=AkShare | status=missing_dependency")
    _assert_contains(output, "concept_rotation | source=AkShare | status=missing_dependency")
    _assert_contains(output, "news_search | source=Tavily | status=missing_key")
    _assert_contains(output, "news_results | source=Tavily | status=missing_key")
    _assert_contains(output, "## security")
    _assert_contains(output, "- data sources:")
    _assert_contains(output, "portfolio_context | source=local | status=available | source_tier=local_user_data")
    _assert_contains(output, "financial_statements | source=AkShare | status=")
    _assert_contains(output, "security_market_quotes | source=AkShare | status=")
    _assert_contains(output, "research_reports | source=AkShare | status=")
    _assert_contains(output, "direct_security_holdings=1")
    _assert_contains(output, "fundamentals, valuation, filings, liquidity require external data")
    _assert_contains(output, "portfolio.holdings | source_tier=local_user_data | freshness=fresh | score=")
    _assert_contains(output, "## etf")
    _assert_contains(output, "proxy_etf_codes=1")
    _assert_contains(output, "etf_quotes | source=AkShare | status=")
    _assert_contains(output, "etf_nav_history | source=AkShare | status=")
    _assert_contains(output, "etf_holdings | source=AkShare | status=")
    _assert_contains(output, "## risk")
    _assert_contains(output, "- risk rules present")
    _assert_contains(output, "portfolio_exposure | source=local | status=available | source_tier=local_user_data")
    _assert_contains(output, "cash_buffer | source=local | status=")
    _assert_contains(output, "risk_limit_breaches | source=local | status=")
    _assert_contains(output, "benchmark_quotes | source=AkShare | status=")
    _assert_contains(output, "portfolio.risk_rules | source_tier=local_user_data | freshness=fresh | score=")
    _assert_contains(output, "external rumor | source_tier=news_search | freshness=unknown | score=")
    _assert_contains(output, "## review")
    _assert_contains(output, "- report continuity checked")
    _assert_contains(output, "report_continuity | source=local | status=available | source_tier=local_user_data")
    _assert_contains(output, "confirmation_records | source=local | status=available | source_tier=local_user_data")
    _assert_contains(output, "- Requires user confirmation: yes")
    _assert_not_contains(output, "PRIVATE_A")
    _assert_not_contains(output, "PRIVATE_ETF")
    _assert_not_contains(output, "PRIVATE_W")
    _assert_not_contains(output, "Private Holding A")
    _assert_not_contains(output, "Private Watch")
    _assert_not_contains(output, "买入")
    _assert_not_contains(output, "卖出")
    _assert_not_contains(output, "自动交易")

    no_direct_portfolio = {
        "holdings": [{"code": "PRIVATE_F", "type": "fund", "strategy_type": "dca"}],
        "watchlist": [],
        "risk_rules": {"single_loss_pct": 2, "daily_loss_pct": 6},
    }
    no_direct_plan = build_research_plan("个股 财报", no_direct_portfolio)
    no_direct_output = format_research_report(execute_research_plan(no_direct_plan, no_direct_portfolio))
    _assert_contains(no_direct_output, "security_market_quotes | source=AkShare | status=skipped")
    _assert_contains(no_direct_output, "research_reports | source=AkShare | status=skipped")
    _assert_contains(no_direct_output, "no direct security holding to query")
    _assert_not_contains(no_direct_output, "PRIVATE_F")


def main():
    run_research_execution_test()
    print("Mock research execution test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
