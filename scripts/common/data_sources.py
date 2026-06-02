"""Role-level data source requirements and availability summaries."""

import importlib.util
import os

from common.data_quality import source_tier


ROLE_DATA_REQUIREMENTS = {
    "macro": [
        {"name": "macro_rates", "source": "AkShare"},
        {"name": "fx_rates", "source": "AkShare"},
        {"name": "liquidity_indicators", "source": "AkShare"},
    ],
    "industry": [
        {"name": "portfolio_context", "source": "local"},
        {"name": "industry_rotation", "source": "AkShare"},
        {"name": "concept_rotation", "source": "AkShare"},
        {"name": "news_search", "source": "Tavily"},
    ],
    "security": [
        {"name": "portfolio_context", "source": "local"},
        {"name": "financial_statements", "source": "AkShare"},
        {"name": "announcements", "source": "AkShare"},
        {"name": "valuation_metrics", "source": "AkShare"},
        {"name": "security_market_quotes", "source": "AkShare"},
        {"name": "research_reports", "source": "AkShare"},
    ],
    "etf": [
        {"name": "portfolio_context", "source": "local"},
        {"name": "etf_quotes", "source": "AkShare"},
        {"name": "premium_discount", "source": "AkShare"},
        {"name": "liquidity_metrics", "source": "AkShare"},
        {"name": "etf_nav_history", "source": "AkShare"},
        {"name": "etf_holdings", "source": "AkShare"},
    ],
    "risk": [
        {"name": "portfolio_context", "source": "local"},
        {"name": "risk_rules", "source": "local"},
        {"name": "portfolio_exposure", "source": "local"},
        {"name": "market_quotes", "source": "AkShare"},
        {"name": "factor_exposure", "source": "local"},
    ],
    "review": [
        {"name": "report_index", "source": "local"},
        {"name": "report_continuity", "source": "local"},
        {"name": "decision_records", "source": "local"},
        {"name": "confirmation_records", "source": "local"},
    ],
}


def _normalized_source(source):
    return str(source or "").strip()


def _source_status(source, env=None):
    env = env if env is not None else os.environ
    normalized = _normalized_source(source).lower()
    if normalized == "local":
        return "available"
    if normalized == "akshare":
        return "available" if importlib.util.find_spec("akshare") else "missing_dependency"
    if normalized == "tavily":
        return "available" if env.get("TAVILY_API_KEY") else "missing_key"
    return "unknown"


def role_data_requirements(role):
    return [dict(item) for item in ROLE_DATA_REQUIREMENTS.get(str(role or ""), [])]


def summarize_role_data_requirements(role, env=None):
    summary = []
    for item in role_data_requirements(role):
        source = _normalized_source(item.get("source"))
        summary.append(
            {
                "name": item["name"],
                "source": source,
                "status": _source_status(source, env=env),
                "source_tier": source_tier(source),
            }
        )
    return summary
