#!/usr/bin/env python3
"""周度复盘报告 — 每周六运行，推送至微信
模块1: 周度收益汇总
"""
import json, os, sys
from datetime import datetime, timedelta
from pathlib import Path

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
from common.dependencies import REPORT_DEPENDENCIES, exit_if_missing
from common.config_loader import get_portfolio_path, load_settings, resolve_path
from common.data_runtime import DataStatusTracker
from common.output_contract import build_report_output_sections, format_classified_report_section, with_output_contract
from common.reporting import write_report

try:
    import akshare as ak
except ImportError:
    ak = None

try:
    import pandas as pd
except ImportError:
    pd = None

try:
    import numpy as np
except ImportError:
    np = None

PORTFOLIO_PATH = str(get_portfolio_path())


def build_run_summary(tracker=None):
    settings = load_settings()
    portfolio_path = Path(PORTFOLIO_PATH)
    example_path = resolve_path(settings["example_portfolio_path"])
    is_example = portfolio_path == example_path
    summary = {
        "portfolio_source": "example" if is_example else "private",
        "is_example_data": is_example,
        "dependencies": {"akshare": "available", "pandas": "available", "numpy": "available"},
        "modules": {"success": 1, "failed": 0, "skipped": 0},
    }
    if tracker:
        summary.update(tracker.to_run_summary())
    return summary

def load_portfolio():
    with open(PORTFOLIO_PATH) as f:
        return json.load(f)

def weekly_returns(tracker=None):
    """模块1: 每只持仓的本周收益"""
    portfolio = load_portfolio()
    results = []
    try:
        for h in portfolio['holdings']:
            df = ak.fund_open_fund_info_em(symbol=h['code'], indicator="单位净值走势")
            df['净值日期'] = pd.to_datetime(df['净值日期'])
            df = df.drop_duplicates(subset='净值日期').sort_values('净值日期')
            # Use the latest available NAV date, not wall-clock week boundaries.
            latest_date = df['净值日期'].max()
            window_start = latest_date - timedelta(days=7)
            mask = df['净值日期'] >= window_start
            df_week = df[mask].tail(10)
            if len(df_week) < 2:
                continue
            nav_start = float(df_week.iloc[0]['单位净值'])
            nav_end = float(df_week.iloc[-1]['单位净值'])
            week_ret = (nav_end / nav_start - 1) * 100
            date_start = df_week.iloc[0]['净值日期'].strftime('%m/%d')
            date_end = df_week.iloc[-1]['净值日期'].strftime('%m/%d')

            # 持仓盈亏
            cost = h.get('cost_basis')
            shares = h.get('shares')
            pnl = None
            pnl_pct = None
            if cost and shares:
                market_value = shares * nav_end
                pnl = market_value - cost
                pnl_pct = (pnl / cost) * 100

            results.append({
                'code': h['code'],
                'name': h['name'],
                'nav_start': nav_start,
                'nav_end': nav_end,
                'week_ret': round(week_ret, 2),
                'period': f"{date_start}→{date_end}",
                'pnl': round(pnl, 2) if pnl else None,
                'pnl_pct': round(pnl_pct, 2) if pnl_pct else None,
                'strategy': h.get('strategy', ''),
            })
        if tracker:
            tracker.success("weekly_returns", source="AkShare", detail=f"{len(results)} holdings")
    except Exception as e:
        if tracker:
            tracker.failure("weekly_returns", source="AkShare", error=e)
    return results


KEY_INDUSTRIES = ['半导体', '白酒', '新能源车', '人工智能', '软件开发', '通信设备', '消费电子', '银行', '医药商业', '光伏设备', '证券', '汽车整车', '电力设备', '计算机设备', '光学光电子']


def industry_rotation(tracker=None):
    """模块2: 本周行业资金流TOP3流入+TOP3流出
    主接口: stock_fund_flow_industry (全行业排名)
    备用接口: stock_sector_fund_flow_hist (逐行业查历史)
    """
    # 主接口
    primary_error = None
    try:
        df = ak.stock_fund_flow_industry()
        df = df.sort_values('净额', ascending=True)
        df = df.drop_duplicates(subset='行业', keep='first')
        top_outflow = df.head(3)[['行业', '净额', '行业-涨跌幅']].to_dict('records')
        top_inflow = df.tail(3)[['行业', '净额', '行业-涨跌幅']].to_dict('records')
        top_inflow.reverse()
        if tracker:
            tracker.success("industry_rotation", source="AkShare", detail="primary")
        return {'inflow': top_inflow, 'outflow': top_outflow, 'source': 'primary'}
    except Exception as e:
        primary_error = e

    # 备用接口：逐行业查最近1天主力净流入
    try:
        results = []
        for ind in KEY_INDUSTRIES:
            try:
                df = ak.stock_sector_fund_flow_hist(symbol=ind)
                if df is not None and len(df) > 0:
                    latest = df.iloc[-1]
                    results.append({
                        '行业': ind,
                        '净额': float(latest['主力净流入-净额']),
                        '净占比': float(latest['主力净流入-净占比']),
                    })
            except Exception:
                continue
        if not results:
            if tracker:
                tracker.failure("industry_rotation", source="AkShare", error=primary_error)
            return None
        rdf = pd.DataFrame(results).sort_values('净额', ascending=True)
        top_outflow = rdf.head(3).to_dict('records')
        top_inflow = rdf.tail(3).to_dict('records')
        top_inflow.reverse()
        # 补涨跌幅字段（备用接口没有，置0）
        for item in top_inflow + top_outflow:
            item['行业-涨跌幅'] = 0
        if tracker:
            tracker.success("industry_rotation", source="AkShare", detail="fallback")
        return {'inflow': top_inflow, 'outflow': top_outflow, 'source': 'fallback'}
    except Exception as e:
        if tracker:
            tracker.failure("industry_rotation", source="AkShare", error=e)
        return None


def factor_weekly(portfolio, tracker=None):
    """模块3: 按 portfolio factor_profile 生成本周因子归因"""
    sys.path.insert(0, os.path.dirname(__file__))
    from qdii_three_factor import run_factor_jobs
    return run_factor_jobs(portfolio, days=7, tracker=tracker)


def decision_template(weekly_rets, industry_data, factor_results):
    """模块4: 决策建议（按strategy_type隔离逻辑）"""
    portfolio = load_portfolio()
    strategy_map = {h['code']: h.get('strategy_type', 'dca') for h in portfolio['holdings']}
    label_map = {h['code']: h.get('strategy_label', '') for h in portfolio['holdings']}
    advice = []
    for item in weekly_rets:
        stype = strategy_map.get(item['code'], 'dca')
        label = label_map.get(item['code'], '定投')
        if stype == 'dca':
            # 定投：纯状态描述
            advice.append(f"{item['name']} [{label}]: 本周{item['week_ret']:+.2f}%，定投纪律执行中")
        elif stype == 'short_term':
            # 短线：止盈止损信号
            if item['pnl_pct'] is not None and item['pnl_pct'] > 30:
                advice.append(f"{item['name']} [短线]: 浮盈{item['pnl_pct']:+.1f}%，已达高收益区间，可考虑分批止盈")
            elif item['pnl_pct'] is not None and item['pnl_pct'] > 20:
                advice.append(f"{item['name']} [短线]: 浮盈{item['pnl_pct']:+.1f}%，接近止盈关注区")
            elif item['pnl_pct'] is not None and item['pnl_pct'] < -5:
                advice.append(f"{item['name']} [短线]: 浮亏{item['pnl_pct']:+.1f}%，超过短线止损线")
            else:
                advice.append(f"{item['name']} [短线]: 本周{item['week_ret']:+.2f}%，运行正常")
        else:
            advice.append(f"{item['name']}: 本周{item['week_ret']:+.2f}%")

    # 因子建议
    for job, result in factor_results:
        if not result or 'error' in result:
            continue
        fx = result.get('fx_contrib')
        if fx is not None and fx < -0.5:
            advice.append(f"{job['label']}汇率因子: 美元走弱{fx:+.2f}%拖累收益，汇率波动属常态")
        elif fx is not None and fx > 0.5:
            advice.append(f"{job['label']}汇率因子: 美元走强{fx:+.2f}%增厚收益")

        rotation = result.get('rotation_contrib')
        residual = result.get('residual', 0)
        if job.get('attribution_type') == 'a_share_ai':
            if residual < -2:
                advice.append(f"{job['label']}: 本周alpha为{residual:+.1f}%，跑输指数，基金经理选股拖累")
            elif residual > 2:
                advice.append(f"{job['label']}: 本周alpha为{residual:+.1f}%，跑赢指数，选股能力突出")
            if rotation is not None and rotation < -1:
                advice.append(f"{job['label']}: 行业轮动拖累{rotation:+.1f}%，重仓行业资金流出")

    # 行业轮动提示
    if industry_data:
        top_in = [x['行业'] for x in industry_data['inflow'][:3]]
        advice.append(f"本周资金流入前三: {', '.join(top_in)}")

    return advice


def format_weekly_advice_section(advice):
    section = format_classified_report_section(
        facts=["execution_allowed=false", "report_section=decision_support_only"],
        inferences=["weekly return, factor, and industry signals require user review"],
        judgments=list(advice or []),
        confirmations=[
            "user verifies data freshness before any portfolio change",
            "user confirms strategy still applies",
            "user confirms no broker action should be automated",
        ],
    )
    return section.splitlines()


def dca_curve(tracker=None):
    """模块5: 定投收益曲线——每笔确认日的累计成本 vs 累计市值"""
    portfolio = load_portfolio()
    results = []
    try:
        for h in portfolio['holdings']:
            records = [r for r in h.get('buy_records', []) if r.get('status') != 'pending' and r.get('nav') and r.get('shares')]
            if not records:
                continue
            records.sort(key=lambda x: x['confirm_date'])

            # 获取当前净值
            df = ak.fund_open_fund_info_em(symbol=h['code'], indicator="单位净值走势")
            df['净值日期'] = pd.to_datetime(df['净值日期'])
            current_nav = float(df.iloc[-1]['单位净值'])

            cumulative_cost = 0
            cumulative_shares = 0
            entries = []
            for r in records:
                cumulative_cost += r['amount']
                cumulative_shares += r['shares']
                market_val = cumulative_shares * current_nav
                pnl = market_val - cumulative_cost
                pnl_pct = (pnl / cumulative_cost) * 100 if cumulative_cost else 0
                avg_cost = cumulative_cost / cumulative_shares if cumulative_shares else 0
                entries.append({
                    'date': r['confirm_date'],
                    'amount': r['amount'],
                    'nav': r['nav'],
                    'cum_cost': cumulative_cost,
                    'cum_shares': round(cumulative_shares, 2),
                    'avg_cost_nav': round(avg_cost, 4),
                    'current_nav': current_nav,
                    'market_val': round(market_val, 2),
                    'pnl': round(pnl, 2),
                    'pnl_pct': round(pnl_pct, 2),
                })

            # 汇总
            final = entries[-1] if entries else {}
            results.append({
                'code': h['code'],
                'name': h['name'],
                'strategy': h.get('strategy', ''),
                'entries': entries,
                'summary': {
                    'total_cost': final.get('cum_cost', 0),
                    'total_shares': final.get('cum_shares', 0),
                    'avg_cost': final.get('avg_cost_nav', 0),
                    'current_nav': current_nav,
                    'market_val': final.get('market_val', 0),
                    'pnl': final.get('pnl', 0),
                    'pnl_pct': final.get('pnl_pct', 0),
                }
            })
        if tracker:
            tracker.success("dca_curve", source="AkShare", detail=f"{len(results)} holdings")
    except Exception as e:
        if tracker:
            tracker.failure("dca_curve", source="AkShare", error=e)
    return results


def format_report(tracker=None):
    """生成完整周报"""
    tracker = tracker or DataStatusTracker()
    portfolio = load_portfolio()
    now = datetime.now()
    lines = []
    lines.append(f"# 📋 周度复盘 | {now.strftime('%Y-%m-%d')}")
    lines.append("")

    # 模块1: 收益
    rets = weekly_returns(tracker=tracker)
    lines.append("## 📈 本周收益")
    lines.append("")
    total_cost = 0
    total_pnl = 0
    for r in rets:
        emoji = "🔴" if r['week_ret'] < 0 else "🟢"
        pnl_str = f"总盈亏{r['pnl_pct']:+.1f}%({r['pnl']:+.0f}元)" if r['pnl'] else ""
        lines.append(f"- {emoji} **{r['name']}**: 本周{r['week_ret']:+.2f}% | {pnl_str}")
        if r['pnl'] and r.get('cost_basis'):
            pass  # cost not in rets, skip total
    lines.append("")

    # 模块2: 行业轮动
    ind = industry_rotation(tracker=tracker)
    if ind:
        lines.append("## 🔄 行业资金流")
        lines.append("")
        lines.append("流入TOP3:")
        for x in ind['inflow'][:3]:
            lines.append(f"  - {x['行业']}: 净流入{x['净额']:.1f}亿 ({x['行业-涨跌幅']:+.2f}%)")
        lines.append("流出TOP3:")
        for x in ind['outflow'][:3]:
            lines.append(f"  - {x['行业']}: 净流出{abs(x['净额']):.1f}亿 ({x['行业-涨跌幅']:+.2f}%)")
        lines.append("")

    # 模块3: 因子归因
    factors = factor_weekly(portfolio, tracker=tracker)
    lines.append("## 🔬 因子周变化")
    lines.append("")
    if factors:
        from qdii_three_factor import format_factor_result
        for job, result in factors:
            lines.append(format_factor_result(job, result))
            lines.append("")
    else:
        lines.append("- 未配置可用 factor_profile，跳过归因")
        lines.append("")

    # 模块4: 决策建议
    advice = decision_template(rets, ind, factors)
    lines.append("## 💡 下周建议")
    lines.append("")
    lines.extend(format_weekly_advice_section(advice))
    lines.append("")

    # 模块5: 定投收益曲线
    dca = dca_curve(tracker=tracker)
    if dca:
        lines.append("## 📊 定投收益曲线")
        lines.append("")
        for d in dca:
            s = d['summary']
            lines.append(f"**{d['name']}** ({d.get('strategy_label', d.get('strategy', ''))})")
            lines.append(f"  - 累计投入: {s['total_cost']:.0f}元 | 累计份额: {s['total_shares']:.2f}")
            lines.append(f"  - 平均成本NAV: {s['avg_cost']:.4f} | 当前NAV: {s['current_nav']:.4f}")
            emoji = "🔴" if s['pnl'] < 0 else "🟢"
            lines.append(f"  - {emoji} 当前市值: {s['market_val']:.0f}元 | {s['pnl_pct']:+.2f}% ({s['pnl']:+.0f}元)")
            # 每笔明细
            lines.append(f"  逐笔:")
            for e in d['entries']:
                lines.append(f"    {e['date']}: 投{e['amount']:.0f}元@{e['nav']:.4f} → 份额{e['cum_shares']:.2f}")
            lines.append("")

    # 模块6: 产业周期量化信号(块1, 秒级)
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from industry_cycle import generate_block1_report
        cycle_quant = generate_block1_report()
        if cycle_quant:
            lines.append("## 🗺️ 产业周期量化信号")
            lines.append("")
            for line in cycle_quant.split('\n'):
                lines.append(line)
            lines.append("")
    except Exception as e:
        lines.append(f"## 🗺️ 产业周期量化信号")
        lines.append(f"  ⚠️ 获取失败: {e}")
        lines.append("")

    lines.append(f"---")
    lines.append(f"_生成时间: {now.strftime('%Y-%m-%d %H:%M')}_")
    return '\n'.join(lines)


if __name__ == "__main__":
    if exit_if_missing("weekly_finance_review.py", REPORT_DEPENDENCIES):
        raise SystemExit(1)

    tracker = DataStatusTracker()
    report = format_report(tracker=tracker)
    run_summary = build_run_summary(tracker)
    report = with_output_contract(
        report,
        build_report_output_sections("weekly", load_portfolio(), run_summary),
    )
    archived = write_report("weekly", report, run_summary=run_summary)
    print(archived["content"])
