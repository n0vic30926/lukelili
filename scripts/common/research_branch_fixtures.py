"""Sanitized research report branch fixtures."""

from common.evidence import rank_evidence
from common.research_interpretation import interpret_role_data_state
from common.research_questions import build_role_research_questions


def _role_result(role, status, scope, observations, evidence, data_sources, limitations=None):
    return {
        "role": role,
        "scope": scope,
        "status": status,
        "observations": list(observations or []),
        "evidence": rank_evidence(evidence),
        "data_sources": list(data_sources or []),
        "interpretations": interpret_role_data_state(role, data_sources),
        "research_questions": build_role_research_questions(role, data_sources),
        "limitations": list(limitations or []),
        "boundary": "decision_support_only",
    }


def _result(name, role_results):
    return {
        "name": name,
        "result": {
            "query": "sanitized research branch fixture",
            "portfolio_summary": {"holding_count": 2, "watchlist_count": 1},
            "role_results": role_results,
            "requires_user_confirmation": True,
            "prohibited_actions": ["broker_connection", "order_placement", "automatic_trading"],
        },
    }


def research_branch_fixtures():
    """Return sanitized branch fixtures for L4 research report rendering."""
    macro_sources = [
        {"name": "portfolio_context", "source": "local", "status": "available", "source_tier": "local_user_data"},
        {"name": "macro_rates", "source": "AkShare", "status": "missing_dependency", "source_tier": "community_data"},
        {"name": "fx_rates", "source": "AkShare", "status": "available", "source_tier": "community_data"},
        {"name": "liquidity_indicators", "source": "AkShare", "status": "failed", "source_tier": "community_data"},
    ]
    etf_sources = [
        {"name": "portfolio_context", "source": "local", "status": "available", "source_tier": "local_user_data"},
        {"name": "etf_quotes", "source": "AkShare", "status": "available", "source_tier": "community_data"},
        {"name": "premium_discount", "source": "AkShare", "status": "empty", "source_tier": "community_data"},
        {"name": "liquidity_metrics", "source": "AkShare", "status": "available", "source_tier": "community_data"},
    ]
    security_sources = [
        {"name": "portfolio_context", "source": "local", "status": "available", "source_tier": "local_user_data"},
        {"name": "financial_statements", "source": "AkShare", "status": "missing_dependency", "source_tier": "community_data"},
        {"name": "announcements", "source": "AkShare", "status": "missing_dependency", "source_tier": "community_data"},
        {"name": "valuation_metrics", "source": "AkShare", "status": "missing_dependency", "source_tier": "community_data"},
        {"name": "security_market_quotes", "source": "AkShare", "status": "missing_dependency", "source_tier": "community_data"},
        {"name": "research_reports", "source": "AkShare", "status": "missing_dependency", "source_tier": "community_data"},
    ]
    failed_industry_sources = [
        {"name": "portfolio_context", "source": "local", "status": "available", "source_tier": "local_user_data"},
        {"name": "industry_rotation", "source": "AkShare", "status": "failed", "source_tier": "community_data"},
        {"name": "news_search", "source": "Tavily", "status": "missing_key", "source_tier": "news_search"},
    ]

    return [
        _result(
            "all_roles_degraded",
            [
                _role_result(
                    "macro",
                    "ok",
                    "macro rates, FX, inflation, liquidity",
                    ["macro_data_status=skipped"],
                    [
                        {"label": "portfolio.factor_profile", "source_tier": "local_user_data", "freshness": "fresh"},
                        {"label": "macro.fx", "source_tier": "community_data", "freshness": "unknown"},
                    ],
                    macro_sources,
                    ["missing_dependency: akshare"],
                ),
                _role_result(
                    "security",
                    "skipped",
                    "individual security fundamentals, valuation, filings",
                    ["security_data_status=skipped"],
                    [{"label": "portfolio.holdings", "source_tier": "local_user_data", "freshness": "fresh"}],
                    security_sources,
                    ["no security data fetched"],
                ),
                _role_result(
                    "etf",
                    "ok",
                    "ETF structure, tracking, liquidity, fees",
                    ["etf_data_status=ok"],
                    [
                        {"label": "portfolio proxy_etf", "source_tier": "local_user_data", "freshness": "fresh"},
                        {"label": "etf.quotes", "source_tier": "community_data", "freshness": "unknown"},
                    ],
                    etf_sources,
                    [],
                ),
            ],
        ),
        _result(
            "runner_failure_path",
            [
                _role_result(
                    "industry",
                    "failed",
                    "industry rotation, themes, news signals",
                    [],
                    [{"label": "industry_intel.build_search_queries", "source_tier": "local_user_data", "freshness": "unknown"}],
                    failed_industry_sources,
                    ["RuntimeError"],
                ),
                _role_result(
                    "risk",
                    "ok",
                    "portfolio exposure, concentration, drawdown rules",
                    ["holdings=2", "factor_profiles=example_factor"],
                    [{"label": "portfolio summary", "source_tier": "local_user_data", "freshness": "fresh"}],
                    [
                        {"name": "portfolio_context", "source": "local", "status": "available", "source_tier": "local_user_data"},
                        {"name": "risk_rules", "source": "local", "status": "available", "source_tier": "local_user_data"},
                        {"name": "market_quotes", "source": "AkShare", "status": "missing_dependency", "source_tier": "community_data"},
                        {"name": "factor_exposure", "source": "AkShare", "status": "missing_dependency", "source_tier": "community_data"},
                    ],
                    ["no live market data fetched"],
                ),
            ],
        ),
    ]
