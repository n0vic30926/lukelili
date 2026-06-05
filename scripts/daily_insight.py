#!/usr/bin/env python3
"""Human-readable daily portfolio insight layer.

This script turns the existing finance-agent diagnostics into a reader-facing
decision-support report. Raw backend fields stay in the technical appendix; the
main body translates data into judgment, triggers, and next actions.
"""

from __future__ import annotations

import re
from pathlib import Path

from common.config_loader import load_portfolio, load_settings, resolve_path
from decision_support import build_decision_packet, load_scenario_review
from portfolio_backtest import build_portfolio_backtest
from portfolio_gap_review import build_gap_review
from portfolio_intersection import build_stock_intersection
from portfolio_xray import build_portfolio_xray
from report_index import load_report_index
from market_radar import build_market_radar
from narrative_evidence import load_thesis_ledger


def _number(value, default=0.0):
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    return default


def _fmt_pct(value):
    return f"{_number(value):.1f}%"


def _fmt_money(value):
    amount = _number(value)
    if abs(amount - int(amount)) < 0.01:
        return f"{int(amount)} 元"
    return f"{amount:.2f} 元"


def _holding_ref(index):
    return f"holding_{index + 1}"


def _holding_label(holding, index):
    name = str(holding.get("name") or "").strip()
    code = str(holding.get("code") or "").strip()
    if name and code:
        return f"{name}（{code}）"
    return name or code or _holding_ref(index)


def _strategy_label(strategy):
    labels = {
        "dca": "定投主仓",
        "trial": "试验仓",
        "short_term": "短线观察仓",
        "long_term": "长期仓",
        "watch": "观察标的",
    }
    return labels.get(str(strategy or "unknown"), "策略待确认")


def _position_label(ref, holdings):
    if ref == "portfolio":
        return "组合整体"
    if ref == "cash":
        return "现金仓位"
    match = re.match(r"holding_(\d+)$", str(ref or ""))
    if match:
        index = int(match.group(1)) - 1
        if 0 <= index < len(holdings):
            return _holding_label(holdings[index], index)
    return str(ref or "组合")


def _latest_report(items, report_type="daily"):
    candidates = [item for item in items if item.get("report_type") == report_type]
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: item.get("created_at", ""))[-1]


def _read_report_text(report_item):
    report_path = str((report_item or {}).get("report_path") or "").strip()
    if not report_path:
        return ""
    path = Path(report_path)
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _extract_daily_numbers(report_text):
    metrics = {"holdings": []}
    total_match = re.search(
        r"组合合计\*\*: 成本([0-9.]+) → 市值([0-9.]+) \| ([+-]?[0-9.]+)% \(([+-]?[0-9.]+)元\)",
        report_text,
    )
    if total_match:
        metrics["total"] = {
            "cost": _number(float(total_match.group(1))),
            "value": _number(float(total_match.group(2))),
            "return_pct": _number(float(total_match.group(3))),
            "profit": _number(float(total_match.group(4))),
        }
    for match in re.finditer(
        r"\*\*([^*\n]+)\*\*: 成本([0-9.]+) → 市值([0-9.]+) \| ([+-]?[0-9.]+)% \(([+-]?[0-9.]+)元\)",
        report_text,
    ):
        name = match.group(1)
        if name == "组合合计":
            continue
        metrics["holdings"].append(
            {
                "name": name,
                "cost": _number(float(match.group(2))),
                "value": _number(float(match.group(3))),
                "return_pct": _number(float(match.group(4))),
                "profit": _number(float(match.group(5))),
            }
        )
    qdii_match = re.search(
        r"QDII三因子归因（近30日）[\s\S]*?基金收益: ([+-]?[0-9.]+)%[\s\S]*?纳指贡献: ([+-]?[0-9.]+)%[\s\S]*?汇率贡献: ([+-]?[0-9.]+)%[\s\S]*?残差[^:]*: ([+-]?[0-9.]+)%",
        report_text,
    )
    if qdii_match:
        metrics["qdii_attribution"] = {
            "fund_return_pct": _number(float(qdii_match.group(1))),
            "index_contribution_pct": _number(float(qdii_match.group(2))),
            "fx_contribution_pct": _number(float(qdii_match.group(3))),
            "residual_pct": _number(float(qdii_match.group(4))),
        }
    ai_match = re.search(
        r"AI基金三因子归因（近30日）[\s\S]*?基金收益: ([+-]?[0-9.]+)%[\s\S]*?指数贡献: ([+-]?[0-9.]+)%[\s\S]*?行业轮动贡献: ([+-]?[0-9.]+)%[\s\S]*?残差[^:]*: ([+-]?[0-9.]+)%",
        report_text,
    )
    if ai_match:
        metrics["ai_attribution"] = {
            "fund_return_pct": _number(float(ai_match.group(1))),
            "index_contribution_pct": _number(float(ai_match.group(2))),
            "sector_contribution_pct": _number(float(ai_match.group(3))),
            "residual_pct": _number(float(ai_match.group(4))),
        }
    return metrics


def _pending_buys(holdings):
    count = 0
    amount = 0.0
    by_holding = []
    for index, holding in enumerate(holdings):
        local_count = 0
        local_amount = 0.0
        for record in holding.get("buy_records") or []:
            if str(record.get("status") or "").lower() == "pending":
                local_count += 1
                local_amount += _number(record.get("amount"))
        if local_count:
            by_holding.append(
                {
                    "label": _holding_label(holding, index),
                    "count": local_count,
                    "amount": local_amount,
                }
            )
            count += local_count
            amount += local_amount
    return {"count": count, "amount": amount, "by_holding": by_holding}


def _data_status_from_report(report_item):
    run_summary = (report_item or {}).get("run_summary") or {}
    modules = run_summary.get("modules") or {}
    quality = run_summary.get("data_quality") or {}
    skipped = [
        item for item in run_summary.get("data_modules", []) if item.get("status") == "skipped"
    ]
    return {
        "success": int(modules.get("success", 0) or 0),
        "failed": int(modules.get("failed", 0) or 0),
        "skipped": int(modules.get("skipped", 0) or 0),
        "cache_hit": int(modules.get("cache_hit", 0) or 0),
        "fresh": int(quality.get("fresh", 0) or 0),
        "stale": int(quality.get("stale", 0) or 0),
        "unknown": int(quality.get("unknown", 0) or 0),
        "skipped_reasons": [
            str(item.get("reason") or item.get("detail") or item.get("module") or "unknown")
            for item in skipped
        ],
    }


def build_daily_insight_context(portfolio=None, report_items=None):
    if portfolio is None:
        portfolio, portfolio_path, using_example, overlay_applied = load_portfolio()
    else:
        portfolio_path = None
        using_example = False
        overlay_applied = False

    settings = load_settings()
    if report_items is None:
        index_path = resolve_path(settings.get("report_index_path", "reports/index.jsonl"))
        report_items = load_report_index(index_path)
    latest_daily = _latest_report(report_items, "daily")
    daily_text = _read_report_text(latest_daily)
    report_metrics = _extract_daily_numbers(daily_text)

    holdings = [item for item in portfolio.get("holdings", []) if isinstance(item, dict)]
    gap_review = build_gap_review(portfolio)
    xray = build_portfolio_xray(portfolio)
    backtest = build_portfolio_backtest(portfolio)
    intersection = build_stock_intersection(portfolio)
    try:
        scenario_review = load_scenario_review(portfolio, settings=settings)
    except Exception:
        scenario_review = None
    decision_packet = build_decision_packet(portfolio, scenario_review=scenario_review)
    market_radar = build_market_radar(portfolio)
    thesis_ledger = load_thesis_ledger(limit=3)

    return {
        "portfolio": portfolio,
        "portfolio_path": str(portfolio_path) if portfolio_path else "",
        "using_example": using_example,
        "overlay_applied": overlay_applied,
        "holdings": holdings,
        "gap_review": gap_review,
        "xray": xray,
        "backtest": backtest,
        "intersection": intersection,
        "decision_packet": decision_packet,
        "market_radar": market_radar,
        "thesis_ledger": thesis_ledger,
        "latest_daily": latest_daily,
        "report_metrics": report_metrics,
        "data_status": _data_status_from_report(latest_daily),
        "pending_buys": _pending_buys(holdings),
    }


def _opening_line(ctx):
    allocation = ctx["xray"]["allocation"]
    recs = ctx["decision_packet"].get("recommendations") or []
    first_action = recs[0]["action"] if recs else "hold"
    if first_action == "reduce_risk":
        stance = "今天的核心不是追涨或补仓，而是先确认是否要降风险。"
    elif first_action in {"rebalance", "tighten_risk_controls"}:
        stance = "今天的核心是仓位校准，先把偏离目标的部分看清楚。"
    else:
        stance = "今天可以继续观察，但不要把没有触发硬风控理解成可以随意加风险。"
    return (
        f"{stance} 当前组合几乎全部投入市场，最大一只持仓已经是事实上的主仓，"
        f"占组合约 {_fmt_pct(allocation.get('max_position_pct'))}，现金缓冲不足。"
    )


def _important_items(ctx):
    allocation = ctx["xray"]["allocation"]
    pending = ctx["pending_buys"]
    data = ctx["data_status"]
    radar = ctx.get("market_radar") or {}
    items = []
    items.append(
        "组合结构比单日涨跌更重要：两只基金虽然分属 A 股 AI 和美股纳指，"
        "但底层都偏高估值科技成长，压力时相关性可能快速升高。"
    )
    if pending["count"]:
        items.append(
            f"先核对交易事实：仍有 {pending['count']} 笔、合计 "
            f"{_fmt_money(pending['amount'])}的买入记录待确认，仓位判断会被它直接影响。"
        )
    else:
        items.append("交易记录当前没有待确认买入，组合判断可以直接基于已知持仓推进。")
    if data["failed"]:
        items.append(
            f"数据链路有 {data['failed']} 个失败模块，今天的判断要先降级为保守复核。"
        )
    else:
        items.append(
            f"行情和组合链路本次跑通了 {data['success']} 个模块；但新闻自动抓取仍未进入判断链，"
            "所以外部事件需要你补链接或文本再综合。"
        )
    if allocation.get("cash_pct", 0) <= 1:
        items.append("没有现金缓冲，意味着任何新增买入都会继续放大科技成长暴露。")
    if radar.get("themes"):
        top = radar["themes"][0]
        items.append(
            f"市场雷达当前把“{top['name']}”排在前列，但证据状态是“{top['verification_status']}”，"
            "不能把主题热度直接等同于买入理由。"
        )
    return items[:5]


def _portfolio_portrait(ctx):
    holdings = ctx["holdings"]
    allocation = ctx["xray"]["allocation"]
    metrics = ctx["report_metrics"]
    lines = []
    total = metrics.get("total")
    if total:
        result = "盈利" if total["profit"] >= 0 else "亏损"
        lines.append(
            f"组合当前是{result}状态：投入约 {_fmt_money(total['cost'])}，"
            f"最新估算市值约 {_fmt_money(total['value'])}，累计"
            f" {_fmt_pct(total['return_pct'])}（{_fmt_money(total['profit'])}）。"
        )
    else:
        lines.append("组合当前可读取成本和仓位结构，但没有足够的日报净值结果来复述总盈亏。")

    for index, holding in enumerate(holdings):
        label = _holding_label(holding, index)
        strategy = _strategy_label(holding.get("strategy_type"))
        target = holding.get("target_weight_pct")
        current_pct = None
        exposure = ctx["decision_packet"].get("exposure") or {}
        for pos in exposure.get("positions") or []:
            if pos.get("holding_ref") == _holding_ref(index):
                current_pct = pos.get("position_pct")
        detail = f"{label}是{strategy}"
        if current_pct is not None:
            detail += f"，当前约占组合 {_fmt_pct(current_pct)}"
        if target is not None:
            detail += f"，目标约 {_fmt_pct(target)}"
        match = next(
            (item for item in metrics.get("holdings", []) if item["name"] in label),
            None,
        )
        if match:
            detail += f"，当前浮动结果约 {_fmt_pct(match['return_pct'])}"
        lines.append(detail + "。")
    return lines


def _risk_diagnosis(ctx):
    allocation = ctx["xray"]["allocation"]
    backtest = ctx["backtest"]
    fee = ctx["xray"]["fee_review"]
    intersection = ctx["intersection"]
    lines = []
    lines.append(
        f"仓位风险：现金约 {_fmt_pct(allocation.get('cash_pct'))}，"
        f"最大单仓约 {_fmt_pct(allocation.get('max_position_pct'))}。这不是分散组合，"
        "而是高 beta 科技主题组合。"
    )
    if backtest.get("observation_count", 0) > 0:
        lines.append(
            f"波动风险：本地历史样本里组合最大回撤约 {_fmt_pct(backtest.get('max_drawdown_pct'))}，"
            f"年化波动约 {_fmt_pct(backtest.get('annualized_volatility_pct'))}。样本仍短，"
            "只能作为压力感知，不能当成完整风险模型。"
        )
    else:
        lines.append("波动风险：本地历史样本不足，不能用回测结果支撑强判断。")
    if intersection.get("top_underlyings"):
        top = intersection["top_underlyings"][0]
        lines.append(
            f"穿透集中度：最大底层标的约占组合 {_fmt_pct(top.get('portfolio_pct'))}；"
            "这提示表面上的基金分散不等于真实底层分散。"
        )
    lines.append(
        f"成本风险：已覆盖费率的部分显示组合显性持有费率约 "
        f"{_fmt_pct(fee.get('weighted_expense_ratio_pct') or 0)}/年，"
        "它不会决定短期涨跌，但会长期消耗复利。"
    )
    return lines


def _instrument_line(instruments, limit=3):
    rendered = []
    for item in instruments[:limit]:
        code = str(item.get("code") or "")
        name = str(item.get("name") or "")
        access = str(item.get("access") or "")
        rendered.append(f"{code}（{name}，{access}）")
    return "；".join(rendered) if rendered else "暂无可执行代码"


def _market_radar_lines(ctx):
    radar = ctx.get("market_radar") or {}
    themes = radar.get("themes") or []
    lines = []
    if not themes:
        return ["市场雷达未生成，今天不把外部叙事纳入提案。"]
    for theme in themes[:5]:
        lines.append(
            f"{theme['name']}：{theme['verification_status']}，与组合关系是“{theme['relation']}”。"
            f"可观察代码：{_instrument_line(theme.get('instruments') or [])}。"
            f"执行口径：{theme['suggested_action']}"
        )
    return lines


def _cognition_iteration_lines(ctx):
    radar = ctx.get("market_radar") or {}
    themes = radar.get("themes") or []
    ledger = ctx.get("thesis_ledger") or []
    growth = [item["name"] for item in themes if item.get("relation") == "增厚原有风险"]
    diversifiers = [item["name"] for item in themes if item.get("relation") == "分散候选"]
    lines = [
        "昨日/历史判断：当前组合已经偏科技成长，首要任务是风险复核和仓位纪律。",
        "今日新增结构：日报不再只看持仓体检，新增市场雷达、叙事核验和组合适配检查。",
    ]
    if growth:
        lines.append(
            "需要修正的地方：AI 主线拆成更细的 "
            + "、".join(growth[:4])
            + "，但这些方向主要是在增厚现有风险。"
        )
    if diversifiers:
        lines.append(
            "维持不变的地方：分散候选仍优先看 "
            + "、".join(diversifiers[:3])
            + "，因为它们更可能降低对单一科技主线的依赖。"
        )
    if ledger:
        latest = ledger[-1]
        counts = latest.get("verification_counts") or {}
        count_text = "、".join(f"{key}:{counts[key]}" for key in sorted(counts)) or "无"
        lines.append(
            "最近一次证据摄取："
            f"{latest.get('created_at', 'unknown')}，"
            f"覆盖主题 {len(latest.get('matched_theme_ids') or [])} 个，"
            f"证据分布 {count_text}。"
        )
    lines.append("仍不确定：没有外部新闻证据时，雷达只给观察和核验优先级，不把传闻当事实。")
    return lines


ACTION_COPY = {
    "reduce_risk": "先做风险复核，不急着增加仓位；可选动作是停止额外加码、留现金垫，或把超目标仓位纳入减风险观察。",
    "rebalance": "检查目标权重和当前权重的偏离，只有在你确认目标仍有效后才考虑调整。",
    "review_upgrade_or_exit": "试验仓要写清楚升级或退出条件；没有条件前，不让它自然漂成长期主仓。",
    "continue_discipline": "定投仓维持纪律，但纪律不等于无限加码；触发集中度或亏损规则时要暂停复核。",
    "monitor_performance": "继续观察收益、回撤和波动，不因单日小涨小跌改变策略。",
    "tighten_risk_controls": "先收紧风险规则和现金缓冲，再讨论扩大风险敞口。",
    "improve_data": "先补数据，再提高建议强度。",
    "refresh_data": "刷新缺失或滞后的外部数据，尤其新闻、宏观和行业事件。",
    "hold": "暂不因为单日波动改变仓位，等待明确触发器。",
}


def _horizon_label(horizon):
    text = str(horizon or "").strip()
    replacements = {
        "now to 3 trading days": "现在到未来 3 个交易日",
        "1-5 trading days": "未来 1-5 个交易日",
        "next rebalance window": "下一次再平衡窗口",
        "before formal use": "正式使用前",
        "before acting on high-impact recommendations": "执行高影响动作前",
    }
    return replacements.get(text, text.replace("trading days", "个交易日"))


def _action_recommendations(ctx):
    holdings = ctx["holdings"]
    recs = ctx["decision_packet"].get("recommendations") or []
    lines = []
    seen = set()
    for rec in recs:
        action = rec.get("action")
        if action == "hold" and lines:
            continue
        if action in seen:
            continue
        seen.add(action)
        target = _position_label(rec.get("instrument_ref"), holdings)
        copy = ACTION_COPY.get(action, str(rec.get("next_action") or action))
        horizon = _horizon_label(rec.get("horizon"))
        suffix = f" 观察窗口：{horizon}。" if horizon else ""
        lines.append(f"{target}：{copy}{suffix}")
        if len(lines) >= 5:
            break
    if not lines:
        lines.append("今天没有生成高优先级动作；保持观察，并等待数据或风控触发器。")
    return lines


def _watch_triggers(ctx):
    rules = ctx["portfolio"].get("risk_rules") or {}
    allocation = ctx["xray"]["allocation"]
    triggers = []
    if rules.get("single_loss_pct") is not None:
        triggers.append(
            f"单只基金单日跌幅接近或超过 {_fmt_pct(rules.get('single_loss_pct'))}：不自动卖出，但必须复核原因和仓位。"
        )
    if rules.get("daily_loss_pct") is not None:
        triggers.append(
            f"组合单日回撤接近或超过 {_fmt_pct(rules.get('daily_loss_pct'))}：进入强制风险复盘。"
        )
    if rules.get("max_single_position_pct") is not None:
        triggers.append(
            f"最大单仓继续靠近 {_fmt_pct(rules.get('max_single_position_pct'))} 上限：停止扩大该方向暴露。"
        )
    if allocation.get("cash_pct", 0) <= 1:
        triggers.append("现金仍接近 0：新增买入前先回答“为什么现在必须继续满仓”。")
    triggers.append("出现与 AI、半导体、纳指、美元人民币、QDII 额度相关的重大新闻：把链接交给系统重新研判。")
    return triggers


def _confirmations(ctx):
    pending = ctx["pending_buys"]
    data_status = ctx["portfolio"].get("data_status") or {}
    lines = []
    if pending["count"]:
        lines.append(
            f"确认 {pending['count']} 笔待确认买入是否已经成交，以及成交净值、份额是否需要修正。"
        )
    if data_status.get("overlay_mode"):
        lines.append("确认当前临时假设层是否仍代表你的真实意图，尤其目标权重、现金和风控阈值。")
    if (ctx["gap_review"].get("gaps") or []):
        lines.append("仍有组合信息缺口；在扩大仓位前先处理 critical/high 项。")
    if not lines:
        lines.append("今天没有阻塞级确认项；后续主要确认外部新闻和个人风险偏好是否变化。")
    return lines


def _data_boundaries(ctx):
    data = ctx["data_status"]
    lines = []
    if data["failed"] == 0:
        lines.append(f"本次数据链路没有失败模块，{data['success']} 个模块成功返回。")
    else:
        lines.append(f"本次有 {data['failed']} 个数据模块失败，建议降低结论强度。")
    if data["unknown"]:
        lines.append(
            f"仍有 {data['unknown']} 个来源的新鲜度无法被系统自动确认；这些数据可用，但不能当成已验证实时数据。"
        )
    if data["skipped"]:
        lines.append("新闻或行业资金流中至少有一个模块被跳过；这不是利空或利多，只是信息面覆盖不足。")
    lines.append("所有买入、卖出、持有建议都是决策支持，不是自动交易指令。")
    return lines


def format_daily_insight(ctx):
    lines = ["# Finance Agent Daily Insight", ""]
    lines.append("## 一句话结论")
    lines.append(_opening_line(ctx))
    lines.append("")

    lines.append("## 今天最重要的事")
    for item in _important_items(ctx):
        lines.append(f"- {item}")
    lines.append("")

    lines.append("## 组合画像")
    for item in _portfolio_portrait(ctx):
        lines.append(f"- {item}")
    lines.append("")

    lines.append("## 风险诊断")
    for item in _risk_diagnosis(ctx):
        lines.append(f"- {item}")
    lines.append("")

    lines.append("## 市场雷达与叙事核验")
    for item in _market_radar_lines(ctx):
        lines.append(f"- {item}")
    lines.append("")

    lines.append("## 认知迭代记录")
    for item in _cognition_iteration_lines(ctx):
        lines.append(f"- {item}")
    lines.append("")

    lines.append("## 行动建议")
    for item in _action_recommendations(ctx):
        lines.append(f"- {item}")
    lines.append("")

    lines.append("## 观察触发器")
    for item in _watch_triggers(ctx):
        lines.append(f"- {item}")
    lines.append("")

    lines.append("## 需要你确认")
    for item in _confirmations(ctx):
        lines.append(f"- {item}")
    lines.append("")

    lines.append("## 数据可信度与盲区")
    for item in _data_boundaries(ctx):
        lines.append(f"- {item}")
    lines.append("")

    lines.append("## 技术附录")
    gap = ctx["gap_review"]
    allocation = ctx["xray"]["allocation"]
    backtest = ctx["backtest"]
    data = ctx["data_status"]
    latest = ctx.get("latest_daily") or {}
    radar = ctx.get("market_radar") or {}
    ledger = ctx.get("thesis_ledger") or []
    lines.append(f"- gap_count={gap.get('gap_count', 0)} overlay_mode={gap.get('overlay_mode')}")
    lines.append(
        "- allocation "
        f"cash_pct={allocation.get('cash_pct')} "
        f"max_position_pct={allocation.get('max_position_pct')} "
        f"max_position_ref={allocation.get('max_position_ref')}"
    )
    lines.append(
        "- backtest "
        f"observation_count={backtest.get('observation_count')} "
        f"max_drawdown_pct={backtest.get('max_drawdown_pct')} "
        f"annualized_volatility_pct={backtest.get('annualized_volatility_pct')}"
    )
    lines.append(
        "- daily_modules "
        f"success={data['success']} failed={data['failed']} skipped={data['skipped']} "
        f"cache_hit={data['cache_hit']} freshness_unknown={data['unknown']}"
    )
    lines.append(
        "- market_radar "
        f"theme_count={radar.get('theme_count', 0)} "
        "news_boundary=radar_matrix_only_unless_external_evidence_is_supplied"
    )
    lines.append(f"- thesis_ledger records_loaded={len(ledger)}")
    if latest.get("report_path"):
        lines.append(f"- source_report={latest.get('report_path')}")
    return "\n".join(lines)


def main():
    print(format_daily_insight(build_daily_insight_context()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
