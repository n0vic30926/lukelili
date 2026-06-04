#!/usr/bin/env python3
"""L4 local research role dispatcher.

This module creates a small, explicit contract between user intent and research
roles. It does not call broker APIs, place trades, or produce final decisions.
"""

import sys

from common.config_loader import load_portfolio
from common.data_sources import role_data_requirements, summarize_role_data_requirements
from common.evidence import rank_evidence
from common.research_coverage import build_research_coverage_matrix, format_research_coverage
from common.research_interpretation import interpret_role_data_state
from common.research_questions import build_role_research_questions


ROLE_DEFINITIONS = {
    "macro": {
        "keywords": ["宏观", "利率", "美联储", "通胀", "汇率", "pmi", "cpi", "m2"],
        "scope": "macro rates, FX, inflation, liquidity",
        "inputs": ["watchlist", "factor_profile"],
        "outputs": ["macro_state", "portfolio_impact_paths", "data_freshness"],
    },
    "industry": {
        "keywords": ["行业", "板块", "产业", "主题", "热点", "轮动", "半导体", "ai"],
        "scope": "industry rotation, themes, news signals",
        "inputs": ["holdings", "watchlist", "industry_intel"],
        "outputs": ["theme_signals", "holding_impacts", "source_quality"],
    },
    "security": {
        "keywords": ["个股", "股票", "公司", "财报", "基本面", "估值", "security", "stock", "earnings"],
        "scope": "individual security fundamentals, valuation, filings",
        "inputs": ["holdings", "watchlist", "financials", "announcements"],
        "outputs": ["security_context", "fundamental_questions", "missing_data"],
    },
    "etf": {
        "keywords": ["etf", "指数基金", "qdii", "跟踪", "溢价", "费率", "流动性"],
        "scope": "ETF structure, tracking, liquidity, fees",
        "inputs": ["holdings", "watchlist", "proxy_etf"],
        "outputs": ["tracking_notes", "liquidity_notes", "fee_questions"],
    },
    "risk": {
        "keywords": ["风险", "仓位", "回撤", "相关性", "集中", "组合", "止损"],
        "scope": "portfolio exposure, concentration, drawdown rules",
        "inputs": ["holdings", "risk_rules", "factor_profile"],
        "outputs": ["risk_flags", "rule_checks", "missing_controls"],
    },
    "review": {
        "keywords": ["复盘", "历史", "纪律", "记录", "报告", "连续", "失败"],
        "scope": "report continuity, repeated failures, discipline records",
        "inputs": ["reports/index.jsonl", "data/private/decision_track"],
        "outputs": ["continuity", "repeated_failures", "discipline_summary"],
    },
}

DEFAULT_ROLES = ["risk", "review"]


def _portfolio_summary(portfolio):
    holdings = portfolio.get("holdings", [])
    watchlist = portfolio.get("watchlist", [])
    return {
        "holding_count": len(holdings),
        "watchlist_count": len(watchlist),
        "strategy_types": sorted({str(h.get("strategy_type") or "unknown") for h in holdings}),
        "factor_profiles": sorted(
            {
                str((h.get("factor_profile") or {}).get("type") or "none")
                for h in holdings
            }
        ),
    }


def _is_direct_security(item):
    asset_type = str(item.get("type") or item.get("asset_type") or "").lower()
    market = str(item.get("market") or "").lower()
    if any(token in asset_type for token in ["stock", "equity", "share"]):
        return True
    return market in {"a_share", "us_stock", "hk_stock"}


def select_roles(query):
    text = str(query or "").lower()
    selected = []
    for role, definition in ROLE_DEFINITIONS.items():
        if any(keyword.lower() in text for keyword in definition["keywords"]):
            selected.append(role)
    if selected:
        return selected
    return list(DEFAULT_ROLES)


def build_research_plan(query, portfolio):
    tasks = []
    for role in select_roles(query):
        definition = ROLE_DEFINITIONS[role]
        tasks.append(
            {
                "role": role,
                "scope": definition["scope"],
                "inputs": definition["inputs"],
                "outputs": definition["outputs"],
                "data_requirements": [item["name"] for item in role_data_requirements(role)],
                "boundary": "decision_support_only",
            }
        )
    return {
        "query": str(query or ""),
        "portfolio_summary": _portfolio_summary(portfolio),
        "tasks": tasks,
        "requires_user_confirmation": True,
        "prohibited_actions": ["broker_connection", "order_placement", "automatic_trading"],
    }


def format_research_plan(plan):
    summary = plan["portfolio_summary"]
    lines = ["# Research Dispatch Plan", ""]
    lines.append(
        "- Portfolio: "
        f"holdings={summary['holding_count']} watchlist={summary['watchlist_count']} "
        f"strategies={','.join(summary['strategy_types']) or 'none'} "
        f"factors={','.join(summary['factor_profiles']) or 'none'}"
    )
    lines.append(f"- Requires user confirmation: {'yes' if plan['requires_user_confirmation'] else 'no'}")
    lines.append("- Boundary: decision support only")
    lines.append("")
    lines.append("## Tasks")
    for task in plan["tasks"]:
        lines.append(f"- {task['role']}: {task['scope']}")
        lines.append(f"  inputs={','.join(task['inputs'])}")
        lines.append(f"  outputs={','.join(task['outputs'])}")
        if task.get("data_requirements"):
            lines.append(f"  data_requirements={','.join(task['data_requirements'])}")
    return "\n".join(lines)


def _safe_list(values, limit=5):
    return [str(value) for value in list(values or [])[:limit]]


def _portfolio_runner(task, portfolio):
    summary = _portfolio_summary(portfolio)
    return {
        "status": "ok",
        "observations": [
            f"holdings={summary['holding_count']}",
            f"watchlist={summary['watchlist_count']}",
            f"strategies={','.join(summary['strategy_types']) or 'none'}",
            f"factor_profiles={','.join(summary['factor_profiles']) or 'none'}",
        ],
        "evidence": [
            {"label": "portfolio summary", "source_tier": "local_user_data", "freshness": "fresh"}
        ],
        "limitations": ["no live market data fetched"],
    }


def _risk_runner(task, portfolio):
    observations = []
    evidence = [
        {"label": "portfolio summary", "source_tier": "local_user_data", "freshness": "fresh"}
    ]
    data_sources = [
        {
            "name": "portfolio_context",
            "source": "local",
            "status": "available",
            "source_tier": "local_user_data",
        }
    ]
    limitations = []
    try:
        from risk_research import fetch_risk_research

        research = fetch_risk_research(portfolio)
        observations.extend(_safe_list(research.get("observations"), limit=8))
        evidence.extend(research.get("evidence") or [])
        data_sources = research.get("data_sources") or data_sources
        limitations.extend(_safe_list(research.get("limitations"), limit=5))
        observations.append(f"risk_data_status={research.get('status', 'unknown')}")
    except Exception as exc:
        limitations.append(type(exc).__name__)

    return {
        "status": "ok",
        "observations": observations,
        "evidence": evidence,
        "data_sources": data_sources,
        "limitations": limitations,
    }


def _macro_runner(task, portfolio):
    summary = _portfolio_summary(portfolio)
    observations = [
        f"macro review should map rates, FX, and liquidity to {summary['holding_count']} holding(s)",
        f"factor profiles: {','.join(summary['factor_profiles']) or 'none'}",
    ]
    evidence = [
        {"label": "portfolio.factor_profile", "source_tier": "local_user_data", "freshness": "fresh"},
        {"label": "portfolio.watchlist", "source_tier": "local_user_data", "freshness": "fresh"},
    ]
    data_sources = [
        {
            "name": "portfolio_context",
            "source": "local",
            "status": "available",
            "source_tier": "local_user_data",
        }
    ]
    limitations = []
    try:
        from macro_research import fetch_macro_research

        research = fetch_macro_research()
        observations.extend(_safe_list(research.get("observations"), limit=5))
        evidence.extend(research.get("evidence") or [])
        data_sources.extend(research.get("data_sources") or [])
        limitations.extend(_safe_list(research.get("limitations"), limit=5))
        observations.append(f"macro_data_status={research.get('status', 'unknown')}")
    except Exception as exc:
        limitations.append(type(exc).__name__)

    return {
        "status": "ok",
        "observations": observations,
        "evidence": evidence,
        "data_sources": data_sources,
        "limitations": limitations,
    }


def _industry_runner(task, portfolio):
    observations = []
    evidence = [
        {"label": "industry_intel.build_search_queries", "source_tier": "local_user_data", "freshness": "fresh"}
    ]
    data_sources = [
        {
            "name": "portfolio_context",
            "source": "local",
            "status": "available",
            "source_tier": "local_user_data",
        }
    ]
    limitations = []
    try:
        from industry_research import fetch_industry_research

        research = fetch_industry_research(portfolio)
        observations.extend(_safe_list(research.get("observations"), limit=5))
        evidence.extend(research.get("evidence") or [])
        data_sources = research.get("data_sources") or data_sources
        limitations.extend(_safe_list(research.get("limitations"), limit=5))
        observations.append(f"industry_data_status={research.get('status', 'unknown')}")
    except Exception as exc:
        limitations.append(type(exc).__name__)

    return {
        "status": "ok",
        "observations": observations,
        "evidence": evidence,
        "data_sources": data_sources,
        "limitations": limitations,
    }


def _security_runner(task, portfolio):
    holdings = portfolio.get("holdings", [])
    watchlist = portfolio.get("watchlist", [])
    direct_holdings = [holding for holding in holdings if _is_direct_security(holding)]
    direct_security_count = len(direct_holdings)
    watch_security_count = sum(1 for item in watchlist if _is_direct_security(item))
    observations = [
        f"direct_security_holdings={direct_security_count}",
        f"watchlist_security_items={watch_security_count}",
        "fundamentals, valuation, filings, liquidity require external data",
    ]
    evidence = [
        {"label": "portfolio.holdings", "source_tier": "local_user_data", "freshness": "fresh"},
        {"label": "portfolio.watchlist", "source_tier": "local_user_data", "freshness": "fresh"},
    ]
    data_sources = [
        {
            "name": "portfolio_context",
            "source": "local",
            "status": "available",
            "source_tier": "local_user_data",
        }
    ]
    limitations = []

    if direct_holdings:
        try:
            from security_research import fetch_security_research

            research = fetch_security_research(str(direct_holdings[0].get("code") or ""))
            observations.extend(_safe_list(research.get("observations"), limit=5))
            evidence.extend(research.get("evidence") or [])
            data_sources.extend(research.get("data_sources") or [])
            limitations.extend(_safe_list(research.get("limitations"), limit=5))
            observations.append(f"security_data_status={research.get('status', 'unknown')}")
        except Exception as exc:
            limitations.append(type(exc).__name__)
    else:
        for source in summarize_role_data_requirements("security"):
            if source["name"] != "portfolio_context":
                source["status"] = "skipped"
                data_sources.append(source)
        limitations.append("no direct security holding to query")

    return {
        "status": "ok",
        "observations": observations,
        "evidence": evidence,
        "data_sources": data_sources,
        "limitations": limitations,
    }


def _etf_runner(task, portfolio):
    summary = _portfolio_summary(portfolio)
    holdings = portfolio.get("holdings", [])
    watchlist = portfolio.get("watchlist", [])
    codes = []
    for holding in holdings:
        if holding.get("proxy_etf"):
            codes.append(holding["proxy_etf"])
    for item in watchlist:
        item_type = str(item.get("type") or item.get("asset_type") or "").lower()
        if "etf" in item_type and item.get("code"):
            codes.append(item["code"])

    observations = [
        f"holdings={summary['holding_count']}",
        f"watchlist={summary['watchlist_count']}",
        f"proxy_etf_codes={len(codes)}",
    ]
    evidence = [
        {"label": "portfolio proxy_etf", "source_tier": "local_user_data", "freshness": "fresh"}
    ]
    data_sources = [
        {
            "name": "portfolio_context",
            "source": "local",
            "status": "available",
            "source_tier": "local_user_data",
        }
    ]
    limitations = []
    try:
        from etf_research import fetch_etf_research

        research = fetch_etf_research(codes)
        observations.extend(_safe_list(research.get("observations"), limit=5))
        evidence.extend(research.get("evidence") or [])
        data_sources.extend(research.get("data_sources") or [])
        limitations.extend(_safe_list(research.get("limitations"), limit=5))
        observations.append(f"etf_data_status={research.get('status', 'unknown')}")
    except Exception as exc:
        limitations.append(type(exc).__name__)

    return {
        "status": "ok",
        "observations": observations,
        "evidence": evidence,
        "data_sources": data_sources,
        "limitations": limitations,
    }


def _review_runner(task, portfolio):
    observations = []
    evidence = [
        {"label": "reports.index", "source_tier": "local_user_data", "freshness": "unknown"},
        {"label": "review.decision_records", "source_tier": "local_user_data", "freshness": "unknown"},
    ]
    data_sources = summarize_role_data_requirements("review")
    limitations = []
    try:
        from review_research import fetch_review_research

        research = fetch_review_research()
        observations.extend(_safe_list(research.get("observations"), limit=8))
        evidence = research.get("evidence") or evidence
        data_sources = research.get("data_sources") or data_sources
        limitations.extend(_safe_list(research.get("limitations"), limit=5))
        observations.append(f"review_data_status={research.get('status', 'unknown')}")
    except Exception as exc:
        limitations.append(type(exc).__name__)

    return {
        "status": "ok",
        "observations": observations,
        "evidence": evidence,
        "data_sources": data_sources,
        "limitations": limitations,
    }


DEFAULT_RUNNERS = {
    "macro": _macro_runner,
    "industry": _industry_runner,
    "security": _security_runner,
    "etf": _etf_runner,
    "risk": _risk_runner,
    "review": _review_runner,
}


def execute_research_plan(plan, portfolio, runners=None):
    """Execute role contracts with read-only runners and collect role outputs."""
    runners = runners or {}
    role_results = []
    for task in plan.get("tasks", []):
        role = task["role"]
        runner = runners.get(role) or DEFAULT_RUNNERS.get(role) or _portfolio_runner
        try:
            result = runner(task, portfolio)
        except Exception as exc:
            result = {
                "status": "failed",
                "observations": [],
                "evidence": [{"label": role, "source_tier": "unknown", "freshness": "unknown"}],
                "limitations": [type(exc).__name__],
            }
        data_sources = result.get("data_sources") or summarize_role_data_requirements(role)
        role_results.append(
            {
                "role": role,
                "scope": task["scope"],
                "status": str(result.get("status") or "unknown"),
                "observations": _safe_list(result.get("observations"), limit=8),
                "evidence": rank_evidence(result.get("evidence")),
                "data_sources": data_sources,
                "interpretations": _safe_list(
                    result.get("interpretations") or interpret_role_data_state(role, data_sources)
                ),
                "research_questions": _safe_list(
                    result.get("research_questions") or build_role_research_questions(role, data_sources)
                ),
                "limitations": _safe_list(result.get("limitations")),
                "boundary": task.get("boundary", "decision_support_only"),
            }
        )
    return {
        "query": plan.get("query", ""),
        "portfolio_summary": plan.get("portfolio_summary", {}),
        "role_results": role_results,
        "requires_user_confirmation": True,
        "prohibited_actions": plan.get("prohibited_actions", []),
    }


def format_research_report(result):
    summary = result.get("portfolio_summary", {})
    lines = ["# Research Execution Report", ""]
    lines.append(
        "- Portfolio: "
        f"holdings={summary.get('holding_count', 0)} "
        f"watchlist={summary.get('watchlist_count', 0)}"
    )
    lines.append(f"- Requires user confirmation: {'yes' if result.get('requires_user_confirmation') else 'no'}")
    lines.append("- Boundary: decision support only")
    lines.append("")
    lines.append(format_research_coverage(build_research_coverage_matrix(result)))
    lines.append("")
    for role_result in result.get("role_results", []):
        lines.append(f"## {role_result['role']}")
        lines.append(f"- status: {role_result['status']}")
        lines.append(f"- scope: {role_result['scope']}")
        if role_result["observations"]:
            lines.append("- observations:")
            for item in role_result["observations"]:
                lines.append(f"  - {item}")
        if role_result["evidence"]:
            lines.append("- evidence:")
            for item in role_result["evidence"]:
                lines.append(
                    "  - "
                    f"{item['label']} | source_tier={item['source_tier']} "
                    f"| freshness={item['freshness']} | score={item['score']}"
                )
        if role_result.get("data_sources"):
            lines.append("- data sources:")
            for item in role_result["data_sources"]:
                lines.append(
                    "  - "
                    f"{item['name']} | source={item['source']} | status={item['status']} "
                    f"| source_tier={item['source_tier']}"
                )
        if role_result.get("interpretations"):
            lines.append("- interpretation:")
            for item in role_result["interpretations"]:
                lines.append(f"  - {item}")
        if role_result.get("research_questions"):
            lines.append("- research questions:")
            for item in role_result["research_questions"]:
                lines.append(f"  - {item}")
        if role_result["limitations"]:
            lines.append("- limitations:")
            for item in role_result["limitations"]:
                lines.append(f"  - {item}")
        lines.append("")
    return "\n".join(lines).strip()


def _load_portfolio():
    portfolio, _, _, _ = load_portfolio()
    return portfolio


def main(argv=None):
    argv = argv or sys.argv[1:]
    execute = False
    if "--execute" in argv:
        execute = True
        argv = [arg for arg in argv if arg != "--execute"]
    query = " ".join(argv) if argv else "组合风险与复盘"
    portfolio = _load_portfolio()
    plan = build_research_plan(query, portfolio)
    if execute:
        print(format_research_report(execute_research_plan(plan, portfolio)))
    else:
        print(format_research_plan(plan))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
