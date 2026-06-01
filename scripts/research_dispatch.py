#!/usr/bin/env python3
"""L4 local research role dispatcher.

This module creates a small, explicit contract between user intent and research
roles. It does not call broker APIs, place trades, or produce final decisions.
"""

import json
import sys

from common.config_loader import get_decision_track_dir, get_portfolio_path, load_settings, resolve_path
from common.evidence import rank_evidence


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


def _macro_runner(task, portfolio):
    summary = _portfolio_summary(portfolio)
    return {
        "status": "ok",
        "observations": [
            f"macro review should map rates, FX, and liquidity to {summary['holding_count']} holding(s)",
            f"factor profiles: {','.join(summary['factor_profiles']) or 'none'}",
        ],
        "evidence": [
            {"label": "portfolio.factor_profile", "source_tier": "local_user_data", "freshness": "fresh"},
            {"label": "portfolio.watchlist", "source_tier": "local_user_data", "freshness": "fresh"},
        ],
        "limitations": ["macro live data not fetched by dispatcher"],
    }


def _industry_runner(task, portfolio):
    try:
        from industry_intel import build_search_queries

        queries = build_search_queries(portfolio)
        return {
            "status": "ok",
            "observations": [f"portfolio-driven news queries={len(queries)}"],
            "evidence": [
                {"label": "industry_intel.build_search_queries", "source_tier": "local_user_data", "freshness": "fresh"}
            ],
            "limitations": ["news fetching is controlled by enable_news and Tavily key"],
        }
    except Exception as exc:
        return {
            "status": "failed",
            "observations": [],
            "evidence": [
                {"label": "industry_intel.build_search_queries", "source_tier": "local_user_data", "freshness": "unknown"}
            ],
            "limitations": [type(exc).__name__],
        }


def _security_runner(task, portfolio):
    holdings = portfolio.get("holdings", [])
    watchlist = portfolio.get("watchlist", [])
    direct_security_count = sum(1 for holding in holdings if _is_direct_security(holding))
    watch_security_count = sum(1 for item in watchlist if _is_direct_security(item))
    return {
        "status": "ok",
        "observations": [
            f"direct_security_holdings={direct_security_count}",
            f"watchlist_security_items={watch_security_count}",
            "fundamentals, valuation, filings, liquidity require external data",
        ],
        "evidence": [
            {"label": "portfolio.holdings", "source_tier": "local_user_data", "freshness": "fresh"},
            {"label": "portfolio.watchlist", "source_tier": "local_user_data", "freshness": "fresh"},
        ],
        "limitations": ["no live financial statements or announcements fetched by dispatcher"],
    }


def _review_runner(task, portfolio):
    try:
        from report_index import load_report_index
        from review_history import load_decision_records, summarize_history

        settings = load_settings()
        index_path = resolve_path(settings.get("report_index_path", "reports/index.jsonl"))
        reports = load_report_index(index_path)
        decisions = load_decision_records(get_decision_track_dir(settings))
        summary = summarize_history(reports, decisions)
        repeated = summary["repeated_failures"]
        observations = [
            f"reports={summary['report_count']}",
            f"decision_records={summary['decision_record_count']}",
            f"current_daily_streak={summary['report_continuity']['current_streak_days']}",
        ]
        if repeated:
            observations.append(
                "repeated_failures="
                + ",".join(f"{name}:{count}" for name, count in sorted(repeated.items()))
            )
        return {
            "status": "ok",
            "observations": observations,
            "evidence": [
                {"label": "reports/index.jsonl", "source_tier": "local_user_data", "freshness": "unknown"},
                {"label": "data/private/decision_track", "source_tier": "local_user_data", "freshness": "unknown"},
            ],
            "limitations": ["private decision details are summarized only"],
        }
    except Exception as exc:
        return {
            "status": "failed",
            "observations": [],
            "evidence": [
                {"label": "reports/index.jsonl", "source_tier": "local_user_data", "freshness": "unknown"},
                {"label": "data/private/decision_track", "source_tier": "local_user_data", "freshness": "unknown"},
            ],
            "limitations": [type(exc).__name__],
        }


DEFAULT_RUNNERS = {
    "macro": _macro_runner,
    "industry": _industry_runner,
    "security": _security_runner,
    "etf": _portfolio_runner,
    "risk": _portfolio_runner,
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
        role_results.append(
            {
                "role": role,
                "scope": task["scope"],
                "status": str(result.get("status") or "unknown"),
                "observations": _safe_list(result.get("observations")),
                "evidence": rank_evidence(result.get("evidence")),
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
        if role_result["limitations"]:
            lines.append("- limitations:")
            for item in role_result["limitations"]:
                lines.append(f"  - {item}")
        lines.append("")
    return "\n".join(lines).strip()


def _load_portfolio():
    with open(get_portfolio_path(), encoding="utf-8") as f:
        return json.load(f)


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
