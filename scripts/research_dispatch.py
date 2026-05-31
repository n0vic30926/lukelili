#!/usr/bin/env python3
"""L4 local research role dispatcher.

This module creates a small, explicit contract between user intent and research
roles. It does not call broker APIs, place trades, or produce final decisions.
"""

import json
import sys

from common.config_loader import get_portfolio_path


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


def _load_portfolio():
    with open(get_portfolio_path(), encoding="utf-8") as f:
        return json.load(f)


def main(argv=None):
    argv = argv or sys.argv[1:]
    query = " ".join(argv) if argv else "组合风险与复盘"
    plan = build_research_plan(query, _load_portfolio())
    print(format_research_plan(plan))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
