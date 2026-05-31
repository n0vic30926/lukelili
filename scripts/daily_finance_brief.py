#!/usr/bin/env python3
"""
每日持仓简报 v2 — AkShare直连版
数据源统一为AkShare，去掉东方财富估值API和westock CLI
覆盖：场外基金净值、场内ETF、指数基准、持仓穿透、北向资金、汇率、风控
"""

import json, os, sys, traceback
from datetime import datetime, timedelta
from pathlib import Path

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
from common.dependencies import REPORT_DEPENDENCIES, exit_if_missing
from common.config_loader import get_portfolio_path, load_settings, resolve_path
from common.data_runtime import DataStatusTracker
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


# ── 数据获取函数 ──

def get_fund_nav(code, days=10, tracker=None):
    """场外基金历史净值（AkShare直连）"""
    try:
        df = ak.fund_open_fund_info_em(symbol=code, indicator='单位净值走势')
        df = df.tail(days).copy()
        df['净值日期'] = pd.to_datetime(df['净值日期'])
        if tracker:
            tracker.success("fund_nav", source="AkShare", detail=code)
        return df
    except Exception as e:
        if tracker:
            tracker.failure("fund_nav", source="AkShare", error=e)
        return None


def get_etf_quote(codes, tracker=None):
    """场内ETF实时行情"""
    if not codes:
        if tracker:
            tracker.skipped("etf_quote", source="AkShare", reason="no_codes")
        return {}
    try:
        df = ak.fund_etf_spot_em()
        result = {}
        for code in codes:
            code_clean = code.replace('sh', '').replace('sz', '')
            row = df[df['代码'] == code_clean]
            if not row.empty:
                r = row.iloc[0]
                result[code] = {
                    'name': str(r.get('名称', '')),
                    'price': float(r.get('最新价', 0)),
                    'change_pct': float(r.get('涨跌幅', 0)),
                    'volume': float(r.get('成交额', 0)),
                }
        if tracker:
            tracker.success("etf_quote", source="AkShare", detail=f"{len(result)}/{len(codes)}")
        return result
    except Exception as e:
        if tracker:
            tracker.failure("etf_quote", source="AkShare", error=e)
        return {}


def get_us_index(tracker=None):
    """美股纳斯达克指数"""
    try:
        df = ak.index_us_stock_sina(symbol=".IXIC")
        df = df.tail(5).copy()
        if tracker:
            tracker.success("us_index", source="AkShare", detail=".IXIC")
        return df
    except Exception as e:
        if tracker:
            tracker.failure("us_index", source="AkShare", error=e)
        return None


def get_fx_usdcny(tracker=None):
    """美元兑人民币实时汇率"""
    try:
        df = ak.fx_spot_quote()
        usd = df[df['货币对'] == 'USD/CNY']
        if not usd.empty:
            if tracker:
                tracker.success("fx_usdcny", source="AkShare", detail="USD/CNY")
            return {
                'rate': float(usd.iloc[0]['买报价']),
            }
    except Exception as e:
        if tracker:
            tracker.failure("fx_usdcny", source="AkShare", error=e)
    return None


def get_north_flow(tracker=None):
    """北向资金+大盘指数"""
    try:
        df = ak.stock_hsgt_fund_flow_summary_em()
        north = df[df['资金方向'] == '北向']
        result = []
        for _, row in north.iterrows():
            result.append({
                'board': str(row['板块']),
                'date': str(row['交易日']),
                'net_buy': float(row['成交净买额']) if pd.notna(row['成交净买额']) else None,
                'net_flow': float(row['资金净流入']) if pd.notna(row['资金净流入']) else None,
                'index_name': str(row['相关指数']),
                'index_chg': float(row['指数涨跌幅']),
            })
        if tracker:
            tracker.success("north_flow", source="AkShare", detail=f"{len(result)} rows")
        return result
    except Exception as e:
        if tracker:
            tracker.failure("north_flow", source="AkShare", error=e)
        return None


def get_fund_top_holdings(code, tracker=None):
    """基金前十大持仓穿透"""
    try:
        df = ak.fund_portfolio_hold_em(symbol=code, date='2025')
        top10 = df.head(10)[['股票代码', '股票名称', '占净值比例']].copy()
        if tracker:
            tracker.success("fund_top_holdings", source="AkShare", detail=code)
        return top10.to_dict('records')
    except Exception as e:
        if tracker:
            tracker.failure("fund_top_holdings", source="AkShare", error=e)
        return []


# ── 生成简报 ──

def main(tracker=None):
    from qdii_three_factor import qdii_attribution, portfolio_risk_scan, ai_fund_attribution
    tracker = tracker or DataStatusTracker()

    portfolio = load_portfolio()
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    weekday = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][now.weekday()]
    is_trading = now.weekday() < 5

    lines = []
    lines.append(f"# 📊 每日持仓简报 | {today} {weekday}")
    lines.append("")

    if not is_trading:
        lines.append("> ⚠️ 非交易日，展示最近交易日数据")
        lines.append("")

    # ── 1. 场外基金 ──
    lines.append("## 📈 持仓基金")
    lines.append("")

    fund_changes = []  # 收集涨跌幅用于风控

    for h in portfolio['holdings']:
        code = h['code']
        name = h['name']
        df_nav = get_fund_nav(code, days=5, tracker=tracker)

        if df_nav is None or df_nav.empty:
            lines.append(f"**{name}** ({code}): 数据获取失败")
            lines.append("")
            continue

        latest = df_nav.iloc[-1]
        prev = df_nav.iloc[-2] if len(df_nav) >= 2 else latest

        nav = float(latest['单位净值'])
        nav_date = str(latest['净值日期'].date()) if hasattr(latest['净值日期'], 'date') else str(latest['净值日期'])
        chg_pct = float(latest['日增长率'])
        emoji = "🔴" if chg_pct < 0 else "🟢"

        # 5日趋势
        if len(df_nav) >= 5:
            nav_5d_ago = float(df_nav.iloc[0]['单位净值'])
            chg_5d = (nav / nav_5d_ago - 1) * 100
        else:
            chg_5d = 0

        fund_changes.append({'name': name, 'code': code, 'chg': chg_pct})

        lines.append(f"**{name}** ({code})")
        lines.append(f"- {emoji} 净值 {nav:.4f} ({chg_pct:+.2f}%) | {nav_date}")
        lines.append(f"- 近5日: {chg_5d:+.2f}% | 策略: {h.get('strategy_label', h.get('strategy', ''))}")
        lines.append("")

    # ── 2. 场内ETF代理 ──
    lines.append("## 📊 场内参考ETF")
    lines.append("")

    etf_codes = [h['proxy_etf'] for h in portfolio['holdings'] if h.get('proxy_etf')]
    etf_map = {h.get('proxy_etf', ''): h['name'] for h in portfolio['holdings']}

    if etf_codes:
        etf_data = get_etf_quote(etf_codes, tracker=tracker)
        for code in etf_codes:
            info = etf_data.get(code, {})
            if info:
                emoji = "🔴" if info['change_pct'] < 0 else "🟢"
                lines.append(f"**{code}** ({etf_map.get(code, '')}场内代理)")
                lines.append(f"- {emoji} {info['price']:.3f} ({info['change_pct']:+.2f}%)")
                lines.append("")
            else:
                lines.append(f"**{code}**: 数据获取失败")
                lines.append("")

    # ── 3. 指数基准 ──
    lines.append("## 🌐 指数基准")
    lines.append("")

    # 美股纳指
    us_idx = get_us_index(tracker=tracker)
    if us_idx is not None and not us_idx.empty:
        latest_us = us_idx.iloc[-1]
        prev_us = us_idx.iloc[-2] if len(us_idx) >= 2 else latest_us
        us_close = float(latest_us['close'])
        us_prev = float(prev_us['close'])
        us_chg = (us_close / us_prev - 1) * 100
        emoji = "🔴" if us_chg < 0 else "🟢"
        us_date = str(latest_us['date']) if 'date' in latest_us else ''
        lines.append(f"- {emoji} **纳斯达克综合**: {us_close:.2f} ({us_chg:+.2f}%) | {us_date}")
    else:
        lines.append("- 纳斯达克: 数据获取失败")

    # ── 4. 汇率 ──
    fx = get_fx_usdcny(tracker=tracker)
    if fx:
        lines.append(f"- 💱 **美元/人民币**: {fx['rate']:.4f}")
    else:
        lines.append("- 汇率: 数据获取失败")

    # ── 5. 北向资金 ──
    north = get_north_flow(tracker=tracker)
    if north:
        for n in north:
            emoji = "🔴" if n['index_chg'] < 0 else "🟢"
            net_str = f"净买{n['net_buy']/1e8:.1f}亿" if n.get('net_buy') else ""
            lines.append(f"- {emoji} **{n['index_name']}** ({n['board']}): {n['index_chg']:+.2f}% {net_str}")
    else:
        lines.append("- 大盘指数: 数据获取失败")

    lines.append("")

    # ── 6. 持仓穿透（月度更新，每周一显示） ──
    if now.weekday() == 0:  # 周一
        lines.append("## 🔍 持仓穿透（周一更新）")
        lines.append("")

        for h in portfolio['holdings']:
            top = get_fund_top_holdings(h['code'], tracker=tracker)
            if top:
                lines.append(f"**{h['name']}** 前十大重仓:")
                for s in top:
                    lines.append(f"  - {s['股票名称']}({s['股票代码']}) {s['占净值比例']:.2f}%")
                lines.append("")
            else:
                lines.append(f"**{h['name']}**: 持仓数据暂无")
                lines.append("")

    # ── 6b. 估值锚 ──
    try:
        from valuation_anchor import nasdaq_valuation, ai_index_valuation
        lines.append("## \u2693 \u4f30\u503c\u951a\uff08\u98ce\u9669\u63d0\u793a\uff0c\u975e\u4ea4\u6613\u4fe1\u53f7\uff09")
        lines.append("")
        nsdq = nasdaq_valuation(tracker=tracker)
        if 'error' not in nsdq:
            lines.append(f"- \u7eb3\u6307{nsdq['level']}\uff1a\u70b9\u4f4d{nsdq['latest']}\uff0c1\u5e74\u767e\u5206\u4f4d{nsdq['pct_1y']}%")
        ai_v = ai_index_valuation(tracker=tracker)
        if 'error' not in ai_v:
            lines.append(f"- AI\u6307\u6570{ai_v['level']}\uff1aPE {ai_v['latest_pe']}\uff0c\u767e\u5206\u4f4d{ai_v['pe_pct']}%")
        lines.append("")
    except Exception as e:
        lines.append(f"\u4f30\u503c\u951a\u83b7\u53d6\u5931\u8d25: {e}")
        lines.append("")

    # ── 7. 风控检查 ──
    lines.append("## 🛡️ 风控检查")
    lines.append("")
    risk = portfolio.get('risk_rules', {})
    lines.append(f"- 单笔日跌上限: {risk.get('single_loss_pct', 2)}%")
    lines.append(f"- 组合日跌上限: {risk.get('daily_loss_pct', 6)}%")
    lines.append("")

    alerts = []
    for fc in fund_changes:
        if abs(fc['chg']) >= risk.get('daily_loss_pct', 6):
            alerts.append(f"🚨 **{fc['name']}** 单日 {fc['chg']:+.2f}% 触及{risk.get('daily_loss_pct', 6)}%警戒线")
        elif abs(fc['chg']) >= risk.get('single_loss_pct', 2):
            alerts.append(f"⚠️ **{fc['name']}** 单日 {fc['chg']:+.2f}% 超过{risk.get('single_loss_pct', 2)}%关注线")

    if alerts:
        lines.append("### 预警")
        for a in alerts:
            lines.append(a)
    else:
        lines.append("✅ 今日无风控预警")

    # ── 8. 持仓盈亏快照 ──
    lines.append("## 💰 持仓盈亏")
    lines.append("")
    total_cost = 0
    total_market = 0
    for h in portfolio['holdings']:
        cost = h.get('cost_basis')
        shares = h.get('shares')
        df_nav = get_fund_nav(h['code'], days=3, tracker=tracker)
        if cost and shares and df_nav is not None and not df_nav.empty:
            latest_nav = float(df_nav.iloc[-1]['单位净值'])
            market_val = shares * latest_nav
            pnl = market_val - cost
            pnl_pct = (pnl / cost) * 100
            total_cost += cost
            total_market += market_val
            emoji = "🔴" if pnl < 0 else "🟢"
            lines.append(f"- {emoji} **{h['name']}**: 成本{cost:.0f} → 市值{market_val:.0f} | {pnl_pct:+.1f}% ({pnl:+.0f}元)")
            # pending shares标注
            pending = [r for r in h.get('buy_records', []) if r.get('status') == 'pending']
            if pending:
                pending_amt = sum(r['amount'] for r in pending)
                lines.append(f"  ⏳ 待确认: {len(pending)}笔共{pending_amt:.0f}元")
        else:
            lines.append(f"- **{h['name']}**: 盈亏计算数据不完整")
    if total_cost > 0:
        total_pnl = total_market - total_cost
        total_pnl_pct = (total_pnl / total_cost) * 100
        emoji = "🔴" if total_pnl < 0 else "🟢"
        lines.append(f"- {emoji} **组合合计**: 成本{total_cost:.0f} → 市值{total_market:.0f} | {total_pnl_pct:+.1f}% ({total_pnl:+.0f}元)")
    lines.append("")

    # ── 9. QDII三因子归因 ──
    lines.append("## 🔬 QDII三因子归因（近30日）")
    lines.append("")
    try:
        attr = qdii_attribution(days=30, tracker=tracker)
        if 'error' not in attr:
            lines.append(f"- 基金收益: {attr['fund_ret']:+.2f}%")
            lines.append(f"- 纳指贡献: {attr['nasdaq_contrib']:+.2f}%")
            lines.append(f"- 汇率贡献: {attr['fx_contrib']:+.2f}%")
            lines.append(f"- 残差(超额/跟踪误差): {attr['residual']:+.2f}%")
            lines.append(f"- 解释度: {attr['explained_pct']:.1f}%")
            attr_data = attr  # 供决策模块用
        else:
            lines.append(f"- 归因计算失败: {attr['error']}")
            attr_data = None
    except Exception as e:
        lines.append(f"- 归因计算异常: {e}")
        attr_data = None
    lines.append("")

    # ── 9b. AI基金三因子归因 ──
    lines.append("## 🔬 AI基金三因子归因（近30日）")
    lines.append("")
    try:
        ai_attr = ai_fund_attribution(days=30, tracker=tracker)
        if 'error' not in ai_attr:
            lines.append(f"- 基金收益: {ai_attr['fund_ret']:+.2f}%")
            lines.append(f"- 中证AI指数贡献: {ai_attr['index_contrib']:+.2f}%")
            lines.append(f"- 行业轮动贡献: {ai_attr['rotation_contrib']:+.2f}%")
            lines.append(f"- 残差(alpha/跟踪误差): {ai_attr['residual']:+.2f}%")
            lines.append(f"- 解释度: {ai_attr['explained_pct']:.1f}%")
            ai_attr_data = ai_attr
        else:
            lines.append(f"- 归因计算失败: {ai_attr['error']}")
            ai_attr_data = None
    except Exception as e:
        lines.append(f"- 归因计算异常: {e}")
        ai_attr_data = None
    lines.append("")

    # ── 10. 组合风险扫描 ──
    lines.append("## 🛡️ 组合风险扫描")
    lines.append("")
    try:
        risk_scan = portfolio_risk_scan(tracker=tracker)
        if 'error' not in risk_scan:
            for h in portfolio['holdings']:
                code = h['code']
                if code in risk_scan:
                    r = risk_scan[code]
                    lines.append(f"- **{r['name']}**: 年化波动率{r['ann_vol']:.1f}% | 区间收益{r['period_ret']:+.2f}%")
            if 'correlation' in risk_scan:
                lines.append(f"- 组合相关性: {risk_scan['correlation']:.2f} ({risk_scan['concentration_risk']}集中度)")
                lines.append(f"  > {risk_scan['crisis_note']}")
            if 'factor_exposure' in risk_scan:
                lines.append("- 因子暴露:")
                for factor, level in risk_scan['factor_exposure'].items():
                    lines.append(f"  - {factor}: {level}")
            risk_data = risk_scan
        else:
            lines.append(f"- 风险扫描失败: {risk_scan['error']}")
            risk_data = None
    except Exception as e:
        lines.append(f"- 风险扫描异常: {e}")
        risk_data = None
    lines.append("")

    # ── 11. 决策建议 ──
    lines.append("## 💡 决策建议")
    lines.append("")
    advice = []
    for h in portfolio['holdings']:
        stype = h.get('strategy_type', 'dca')
        cost = h.get('cost_basis')
        shares = h.get('shares')
        df_nav_h = get_fund_nav(h['code'], days=3, tracker=tracker)
        if not (cost and shares and df_nav_h is not None and not df_nav_h.empty):
            continue
        nav_now = float(df_nav_h.iloc[-1]['单位净值'])
        pnl_pct = ((shares * nav_now - cost) / cost) * 100
        chg_today = float(df_nav_h.iloc[-1].get('日增长率', 0))

        if stype == 'dca':
            # 定投：纯状态描述，不带操作暗示
            advice.append(f"\u2705 **{h['name']}** [{h.get('strategy_label','定投')}] 浮盈亏{pnl_pct:+.1f}%，定投纪律执行中")
        elif stype == 'short_term':
            # 短线：止盈止损信号
            if pnl_pct > 30:
                advice.append(f"\U0001f7e2 **{h['name']}** [短线] 浮盈{pnl_pct:+.1f}%，已达高收益区间，可考虑分批止盈")
            elif pnl_pct > 20:
                advice.append(f"\U0001f7e1 **{h['name']}** [短线] 浮盈{pnl_pct:+.1f}%，接近止盈关注区")
            elif pnl_pct < -5:
                advice.append(f"\U0001f534 **{h['name']}** [短线] 浮亏{pnl_pct:+.1f}%，超过短线止损线")
            else:
                advice.append(f"\u2705 **{h['name']}** [短线] 浮盈亏{pnl_pct:+.1f}%，运行正常")
        else:
            advice.append(f"\u2705 **{h['name']}** 浮盈亏{pnl_pct:+.1f}%")

    # 纯状态提示（不带操作暗示）
    if attr_data and attr_data.get('explained_pct', 0) > 90:
        advice.append(f"\U0001f4ca QDII因子集中度：纳指解释{attr_data['explained_pct']:.0f}%")
    if attr_data and abs(attr_data.get('fx_contrib', 0)) > 0.5:
        direction = "走弱" if attr_data['fx_contrib'] < 0 else "走强"
        advice.append(f"\U0001f4b1 汇率{direction}{attr_data['fx_contrib']:+.2f}%")
    if risk_data and risk_data.get('correlation', 0) > 0.5:
        advice.append(f"\U0001f517 组合相关性{risk_data['correlation']:.2f}")

    # 纪律守护（不择时，只锚定纪律）
    try:
        from industry_intel import fetch_industry_intel
        intel = fetch_industry_intel(tracker=tracker)
        has_red = any(a["signal"] == "\U0001f534" for a in intel)
        has_yellow = any(a["signal"] == "\U0001f7e1" for a in intel)

        lines.append("")
        lines.append("## \U0001f6e1\ufe0f 纪律守护")
        lines.append("")
        lines.append("\u2705 **定投纪律**: 维持日定投节奏不变")

        if has_red:
            lines.append("\U0001f4e1 市场出现重大信号，但定投纪律的核心恰恰是穿越波动")
            lines.append("   历史上，恐慌期继续定投往往是长期收益最好的阶段")
        elif has_yellow:
            lines.append("\U0001f4e1 市场有趋势变化信号，持续观察中，不影响定投节奏")

        # 极端时刻纪律提醒
        for h in portfolio['holdings']:
            df_3d = get_fund_nav(h['code'], days=3, tracker=tracker)
            if df_3d is not None and len(df_3d) >= 2:
                chg = float(df_3d.iloc[-1].get('日增长率', 0))
                if abs(chg) >= 2:
                    direction = "大跌" if chg < 0 else "大涨"
                    lines.append(f"\u26a0\ufe0f {h['name']}今日{direction}{abs(chg):.1f}% — {direction}日正是定投纪律最重要的时刻")
        lines.append("")
    except Exception:
        pass  # 情报采集失败不影响核心建议

    for a in advice:
        lines.append(f"- {a}")
    lines.append("")

    lines.append("---")
    lines.append(f"_v3 集成版 | 生成时间: {now.strftime('%Y-%m-%d %H:%M')}_")

    # ── 12. 行业情报速递 ──
    lines.append("## \U0001f4e1 行业情报速递")
    lines.append("")
    try:
        from industry_intel import fetch_industry_intel
        intel = fetch_industry_intel(tracker=tracker)
        signals = [a for a in intel if a["signal"] in ("\U0001f534", "\U0001f7e1")]
        greens = [a for a in intel if a["signal"] == "\U0001f7e2"][:2]
        if signals:
            for a in signals[:5]:
                funds = a.get("impact_label") or a.get("impact", "组合")
                lines.append(f"- {a['signal']} [{funds}] {a['title'][:60]}")
        if greens:
            for a in greens:
                funds = a.get("impact_label") or a.get("impact", "组合")
                lines.append(f"- \U0001f7e2 [{funds}] {a['title'][:60]}")
        if not signals and not greens:
            lines.append("- 今日无重大行业信号")
    except Exception as e:
        lines.append(f"- 行业情报采集异常: {e}")
    lines.append("")

    return '\n'.join(lines)


if __name__ == "__main__":
    if exit_if_missing("daily_finance_brief.py", REPORT_DEPENDENCIES):
        raise SystemExit(1)

    # 生成简报
    tracker = DataStatusTracker()
    report = main(tracker=tracker)
    archived = write_report("daily", report, run_summary=build_run_summary(tracker))
    print(archived["content"])

    # 反事实追踪：记录今日决策状态
    try:
        from decision_tracker import save_daily_decisions
        save_daily_decisions(PORTFOLIO_PATH)
    except Exception:
        pass  # 追踪失败不影响简报输出
