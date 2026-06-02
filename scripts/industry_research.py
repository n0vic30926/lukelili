#!/usr/bin/env python3
"""Read-only industry research data adapter."""

try:
    import akshare as ak
except ImportError:
    ak = None

from industry_intel import build_search_queries, classify_signal, sanitize_external_text, search_tavily
from common.config_loader import get_tavily_api_key, load_settings


def _row_count(value):
    if value is None:
        return 0
    try:
        return len(value)
    except TypeError:
        return 1


def _data_source(name, source, status):
    source_tier = "news_search" if source == "Tavily" else "community_data"
    if source == "local":
        source_tier = "local_user_data"
    return {
        "name": name,
        "source": source,
        "status": status,
        "source_tier": source_tier,
    }


def _call_rows(ak_client, method_name):
    method = getattr(ak_client, method_name, None)
    if not method:
        return None, "missing_method"
    try:
        return method(), "available"
    except Exception:
        return None, "failed"


def _news_search_status():
    settings = load_settings()
    if not settings.get("enable_news"):
        return "skipped"
    return "available" if get_tavily_api_key(settings) else "missing_key"


def _news_result_state(queries, news_client, search_status):
    if news_client is None and search_status != "available":
        return {"status": search_status, "total": 0, "signals": {}}

    client = news_client or (lambda query: search_tavily(query, days=3, max_results=5))
    signals = {"red": 0, "yellow": 0, "green": 0, "neutral": 0}
    total = 0
    try:
        for query in queries:
            for result in client(query["query"]) or []:
                title = sanitize_external_text(result.get("title", ""), max_length=160)
                content = sanitize_external_text(result.get("content", ""), max_length=300)
                signal, _ = classify_signal(title, content, query.get("tags") or [])
                key = {"🔴": "red", "🟡": "yellow", "🟢": "green"}.get(signal, "neutral")
                signals[key] += 1
                total += 1
    except Exception:
        return {"status": "failed", "total": 0, "signals": signals}

    return {"status": "available" if total else "empty", "total": total, "signals": signals}


def fetch_industry_research(portfolio, ak_client=None, news_client=None):
    ak_client = ak_client if ak_client is not None else ak
    queries = build_search_queries(portfolio or {})
    observations = [f"portfolio_driven_news_queries={len(queries)}"]
    evidence = [
        {
            "label": "industry.news_queries",
            "source_tier": "local_user_data",
            "freshness": "fresh",
        }
    ]
    data_sources = [
        _data_source("portfolio_context", "local", "available"),
        _data_source("news_search", "Tavily", _news_search_status()),
    ]
    news_state = _news_result_state(queries, news_client, data_sources[1]["status"])
    data_sources.append(_data_source("news_results", "Tavily", news_state["status"]))
    observations.append(f"news_results_found={news_state['total']}")
    for name in ["red", "yellow", "green", "neutral"]:
        observations.append(f"news_signal_{name}={news_state['signals'].get(name, 0)}")
    if news_state["status"] == "available":
        evidence.append(
            {
                "label": "industry.news_results",
                "source_tier": "news_search",
                "freshness": "unknown",
            }
        )

    if ak_client is None:
        data_sources.extend(
            [
                _data_source("industry_rotation", "AkShare", "missing_dependency"),
                _data_source("concept_rotation", "AkShare", "missing_dependency"),
            ]
        )
        return {
            "status": "skipped",
            "observations": observations,
            "evidence": evidence,
            "data_sources": data_sources,
            "limitations": ["missing_dependency: akshare"],
        }

    calls = [
        ("industry_rotation", "stock_fund_flow_industry", "industry.rotation"),
        ("concept_rotation", "stock_fund_flow_concept", "industry.concept_rotation"),
    ]
    for name, method_name, evidence_label in calls:
        value, status = _call_rows(ak_client, method_name)
        data_sources.append(_data_source(name, "AkShare", status))
        if status == "available":
            observations.append(f"{name}_rows={_row_count(value)}")
            evidence.append(
                {
                    "label": evidence_label,
                    "source_tier": "community_data",
                    "freshness": "unknown",
                }
            )

    has_external_evidence = any(item["source_tier"] in {"community_data", "news_search"} for item in evidence)
    return {
        "status": "ok" if has_external_evidence else "skipped",
        "observations": observations,
        "evidence": evidence,
        "data_sources": data_sources,
        "limitations": [] if has_external_evidence else ["no industry rotation or news result data fetched"],
    }


def main():
    print(fetch_industry_research({}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
