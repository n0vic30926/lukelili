#!/usr/bin/env python3
"""周度复盘报告 — 每周六运行，推送至微信
模块1: 周度收益汇总
"""
import json, os, sys
from datetime import datetime, timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
from common.config_loader import get_portfolio_path_with_flag, get_report_dirs, load_settings
from common.data_runtime import DataStatusTracker, missing_dependencies
from common.output_contract import format_classified_report_section
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

SETTINGS = load_settings()
PORTFOLIO_PATH, USING_EXAMPLE_PORTFOLIO = get_portfolio_path_with_flag(SETTINGS)
REPORT_DIRS = get_report_dirs(SETTINGS)
TRACKER = DataStatusTracker()
MISSING_RUNTIME_DEPS = missing_dependencies(["akshare", "pandas", "numpy"])


def _is_frame(value):
    return hasattr(value, "empty") and hasattr(value, "iloc") and not value.empty


def _call_dataframe(tracker, module, source, producer):
    try:
        result = producer()
        tracker.success(module, source=source)
        return result
    except Exception as exc:
        tracker.failure(module, source=source, error=exc)
        return None


def load_portfolio():
    with open(PORTFOLIO_PATH, encoding="utf-8") as f:
        return json.load(f)


def build_run_summary(tracker=None):
    return (tracker or TRACKER).to_run_summary()


def module_status_lines():
    key_env = SETTINGS.get("tavily_api_key_env", "TAVILY_API_KEY")
    news_ready = bool(SETTINGS.get("enable_news", False)) and bool(os.environ.get(key_env))
    return [
        "portfolio=ok",
        f"portfolio_mode={'example' if USING_EXAMPLE_PORTFOLIO else 'private'}",
        f"runtime_deps={'missing:' + ','.join(MISSING_RUNTIME_DEPS) if MISSING_RUNTIME_DEPS else 'ok'}",
        f"data_status={TRACKER.summary_text()}",
        f"news={'enabled' if news_ready else 'skipped'}",
        "industry_cycle=best_effort",
    ]


def write_report_file(report):
    return write_report("weekly", report, SETTINGS, TRACKER)


def dependency_error_report():
    now = datetime.now()
    lines = [
        f"# 📋 周度复盘 | {now.strftime('%Y-%m-%d')}",
        "",
        "> Missing required runtime dependencies.",
        "> 运行失败: 缺少必要 Python 依赖。",
        f"> 缺失依赖: {', '.join(MISSING_RUNTIME_DEPS)}",
        "> 请手动执行: python3 -m pip install -r requirements.txt",
        "",
        "未生成市场分析，避免产生不完整或误导性报告。",
    ]
    return "\n".join(lines)

def weekly_returns(tracker=None):
    """模块1: 每只持仓的本周收益"""
    active_tracker = tracker or TRACKER
    portfolio = load_portfolio()
    today = datetime.now()
    # 本周一
    monday = today - timedelta(days=today.weekday())
    results = []
    for h in portfolio['holdings']:
        df = _call_dataframe(
            active_tracker,
            f"weekly_fund_nav:{h['code']}",
            "AkShare fund_open_fund_info_em",
            lambda code=h['code']: ak.fund_open_fund_info_em(symbol=code, indicator="单位净值走势"),
        )
        if not _is_frame(df):
            continue
        df['净值日期'] = pd.to_datetime(df['净值日期'])
        df = df.drop_duplicates(subset='净值日期').sort_values('净值日期')
        # 找上周五和本周五(或最新)
        last_friday = monday - timedelta(days=3)
        mask = df['净值日期'] >= last_friday
        df_week = df[mask].tail(10)
        if tracker and len(df_week) < 2:
            df_week = df.tail(10)
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
    return results


KEY_INDUSTRIES = ['半导体', '白酒', '新能源车', '人工智能', '软件开发', '通信设备', '消费电子', '银行', '医药商业', '光伏设备', '证券', '汽车整车', '电力设备', '计算机设备', '光学光电子']


def industry_rotation(tracker=None):
    """模块2: 本周行业资金流TOP3流入+TOP3流出
    主接口: stock_fund_flow_industry (全行业排名)
    备用接口: stock_sector_fund_flow_hist (逐行业查历史)
    """
    active_tracker = tracker or TRACKER
    # 主接口
    try:
        df = _call_dataframe(
            active_tracker,
            "weekly_industry_flow",
            "AkShare stock_fund_flow_industry",
            lambda: ak.stock_fund_flow_industry(),
        )
        if not _is_frame(df):
            raise RuntimeError("stock_fund_flow_industry unavailable")
        df = df.sort_values('净额', ascending=True)
        df = df.drop_duplicates(subset='行业', keep='first')
        top_outflow = df.head(3)[['行业', '净额', '行业-涨跌幅']].to_dict('records')
        top_inflow = df.tail(3)[['行业', '净额', '行业-涨跌幅']].to_dict('records')
        top_inflow.reverse()
        return {'inflow': top_inflow, 'outflow': top_outflow, 'source': 'primary'}
    except Exception:
        if tracker:
            tracker.failure("industry_rotation", source="AkShare", error=RuntimeError("stock_fund_flow_industry unavailable"))
            return None
        pass

    # 备用接口：逐行业查最近1天主力净流入
    try:
        results = []
        for ind in KEY_INDUSTRIES:
            try:
                df = _call_dataframe(
                    active_tracker,
                    f"weekly_sector_flow:{ind}",
                    "AkShare stock_sector_fund_flow_hist",
                    lambda ind=ind: ak.stock_sector_fund_flow_hist(symbol=ind),
                )
                if _is_frame(df) and len(df) > 0:
                    latest = df.iloc[-1]
                    results.append({
                        '行业': ind,
                        '净额': float(latest['主力净流入-净额']),
                        '净占比': float(latest['主力净流入-净占比']),
                    })
            except Exception:
                continue
        if not results:
            return None
        rdf = pd.DataFrame(results).sort_values('净额', ascending=True)
        top_outflow = rdf.head(3).to_dict('records')
        top_inflow = rdf.tail(3).to_dict('records')
        top_inflow.reverse()
        # 补涨跌幅字段（备用接口没有，置0）
        for item in top_inflow + top_outflow:
            item['行业-涨跌幅'] = 0
        return {'inflow': top_inflow, 'outflow': top_outflow, 'source': 'fallback'}
    except Exception:
        return None


def qdii_factor_weekly():
    """模块3: 本周QDII因子变化"""
    sys.path.insert(0, os.path.dirname(__file__))
    from qdii_three_factor import qdii_attribution
    return qdii_attribution(days=7)


def ai_fund_factor_weekly():
    """模块3b: 本周AI基金因子变化"""
    sys.path.insert(0, os.path.dirname(__file__))
    from qdii_three_factor import ai_fund_attribution
    return ai_fund_attribution(days=7)


def decision_template(weekly_rets, industry_data, qdii_factor, ai_factor):
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
    if qdii_factor and 'nasdaq_contrib' in qdii_factor:
        fx = qdii_factor.get('fx_contrib', 0)
        if fx < -0.5:
            advice.append(f"QDII汇率因子: 美元走弱{fx:+.2f}%拖累收益，短期不必调整，汇率波动属常态")
        elif fx > 0.5:
            advice.append(f"QDII汇率因子: 美元走强{fx:+.2f}%增厚收益")

    # 行业轮动提示
    if industry_data:
        top_in = [x['行业'] for x in industry_data['inflow'][:3]]
        advice.append(f"本周资金流入前三: {', '.join(top_in)}")

    # AI因子建议
    if ai_factor and 'error' not in ai_factor:
        rotation = ai_factor.get('rotation_contrib', 0)
        residual = ai_factor.get('residual', 0)
        if residual < -2:
            advice.append(f"AI基金: 本周alpha为{residual:+.1f}%，跑输指数，基金经理选股拖累")
        elif residual > 2:
            advice.append(f"AI基金: 本周alpha为{residual:+.1f}%，跑赢指数，选股能力突出")
        if rotation < -1:
            advice.append(f"AI基金: 行业轮动拖累{rotation:+.1f}%，重仓行业资金流出")

    return advice


def format_weekly_advice_section(advice):
    section = format_classified_report_section(
        facts=["execution_allowed=false", "report_section=decision_support_only"],
        inferences=["weekly return, factor, and industry signals require user review"],
        judgments=list(advice or []),
        confirmations=[
            "User must review facts, inferred signals, and model judgment before any action.",
            "user confirms no broker action should be automated",
        ],
    )
    return section.splitlines()


def dca_curve(tracker=None):
    """模块5: 定投收益曲线——每笔确认日的累计成本 vs 累计市值"""
    active_tracker = tracker or TRACKER
    portfolio = load_portfolio()
    results = []
    for h in portfolio['holdings']:
        records = [r for r in h.get('buy_records', []) if r.get('status') != 'pending' and r.get('nav') and r.get('shares')]
        if not records:
            continue
        records.sort(key=lambda x: x['confirm_date'])

        # 获取当前净值
        df = _call_dataframe(
            active_tracker,
            f"dca_fund_nav:{h['code']}",
            "AkShare fund_open_fund_info_em",
            lambda code=h['code']: ak.fund_open_fund_info_em(symbol=code, indicator="单位净值走势"),
        )
        if not _is_frame(df):
            continue
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
    return results


def format_report():
    """生成完整周报"""
    now = datetime.now()
    lines = []
    lines.append(f"# 📋 周度复盘 | {now.strftime('%Y-%m-%d')}")
    lines.append("")
    lines.append(f"> 数据来源: AkShare + local portfolio | 配置: {SETTINGS.get('_settings_path')} | 生成时间: {now.strftime('%Y-%m-%d %H:%M')}")
    status_line_at = len(lines)
    lines.append(f"> 模块状态: {', '.join(module_status_lines())}")
    if USING_EXAMPLE_PORTFOLIO:
        lines.append("> ⚠️ 当前使用示例持仓数据，仅用于 smoke test，不代表真实资产。")
    lines.append("")
    summary_insert_at = len(lines)
    lines.append("__RUN_SUMMARY_PLACEHOLDER__")
    lines.append("")

    # 模块1: 收益
    rets = weekly_returns()
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
    ind = industry_rotation()
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

    # 模块3: QDII因子
    qf = qdii_factor_weekly()
    if qf and 'error' not in qf:
        lines.append("## 🔬 QDII因子周变化")
        lines.append("")
        lines.append(f"- 基金周收益: {qf['fund_ret']:+.2f}%")
        lines.append(f"- 纳指贡献: {qf['nasdaq_contrib']:+.2f}%")
        lines.append(f"- 汇率贡献: {qf['fx_contrib']:+.2f}%")
        lines.append(f"- 残差(超额/跟踪误差): {qf['residual']:+.2f}%")
        lines.append("")

    # 模块3b: AI基金因子
    af = ai_fund_factor_weekly()
    if af and 'error' not in af:
        lines.append("## 🔬 AI基金因子周变化")
        lines.append("")
        lines.append(f"- 基金周收益: {af['fund_ret']:+.2f}%")
        lines.append(f"- 中证AI指数贡献: {af['index_contrib']:+.2f}%")
        lines.append(f"- 行业轮动贡献: {af['rotation_contrib']:+.2f}%")
        lines.append(f"- 残差(alpha/跟踪误差): {af['residual']:+.2f}%")
        lines.append("")

    # 模块4: 决策建议
    advice = decision_template(rets, ind, qf, af)
    lines.append("## 💡 下周建议")
    lines.append("")
    for a in advice:
        lines.append(f"- {a}")
    lines.append("")

    # 模块5: 定投收益曲线
    dca = dca_curve()
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
    lines[status_line_at] = f"> 模块状态: {', '.join(module_status_lines())}"
    lines[summary_insert_at:summary_insert_at + 1] = TRACKER.markdown_lines() + TRACKER.quality_markdown_lines(
        max_age_hours=SETTINGS.get("freshness_max_age_hours", 24),
        thresholds=SETTINGS.get("freshness_thresholds", {}),
    )
    return '\n'.join(lines)


if __name__ == "__main__":
    if MISSING_RUNTIME_DEPS:
        print(dependency_error_report())
        raise SystemExit(2)
    report = format_report()
    print(report)
    report_path = write_report_file(report)
    print(f"\n[report saved] {report_path}")
