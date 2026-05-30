#!/usr/bin/env python3
"""QDII三因子归因：基金收益 = 纳指贡献 + 汇率贡献 + 残差(跟踪误差)
AI基金三因子归因：基金收益 = 指数贡献 + 行业轮动贡献 + 残差(alpha)"""
from datetime import datetime, timedelta
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
from common.config_loader import get_portfolio_path, load_settings
from common.data_runtime import DataStatusTracker, cached_call, missing_dependencies

try:
    import akshare as ak
    import pandas as pd
    import numpy as np
except ImportError:
    ak = None
    pd = None
    np = None

SETTINGS = load_settings()
TRACKER = DataStatusTracker()
MISSING_RUNTIME_DEPS = missing_dependencies(["akshare", "pandas", "numpy"])


def _missing_deps_error():
    if MISSING_RUNTIME_DEPS:
        return {"error": f"缺少必要依赖: {', '.join(MISSING_RUNTIME_DEPS)}"}
    return None

def qdii_attribution(fund_code="016452", days=30):
    """计算QDII基金的三因子归因"""
    missing = _missing_deps_error()
    if missing:
        return missing
    # 1. 基金净值序列
    df_fund = cached_call(
        SETTINGS,
        TRACKER,
        f"qdii_fund_nav:{fund_code}",
        "AkShare fund_open_fund_info_em",
        f"qdii_fund_nav:{fund_code}:{days}",
        lambda: ak.fund_open_fund_info_em(symbol=fund_code, indicator="单位净值走势"),
        None,
    )
    if df_fund is None:
        return {"error": "基金净值数据不可用"}
    df_fund['净值日期'] = pd.to_datetime(df_fund['净值日期'])
    df_fund = df_fund.tail(days + 5).drop_duplicates(subset='净值日期').tail(days)
    fund_start = float(df_fund.iloc[0]['单位净值'])
    fund_end = float(df_fund.iloc[-1]['单位净值'])
    fund_ret = (fund_end / fund_start - 1) * 100
    date_start = df_fund.iloc[0]['净值日期']
    date_end = df_fund.iloc[-1]['净值日期']

    # 2. 纳斯达克指数
    df_nasdaq = cached_call(
        SETTINGS,
        TRACKER,
        "qdii_nasdaq_index",
        "AkShare index_us_stock_sina",
        "qdii_nasdaq_index:.IXIC",
        lambda: ak.index_us_stock_sina(symbol=".IXIC"),
        None,
    )
    if df_nasdaq is None:
        return {"error": "纳指数据不可用"}
    df_nasdaq['date'] = pd.to_datetime(df_nasdaq['date'])
    df_nasdaq = df_nasdaq.sort_values('date')
    mask = (df_nasdaq['date'] >= date_start - timedelta(days=3)) & (df_nasdaq['date'] <= date_end + timedelta(days=1))
    df_nasdaq_period = df_nasdaq[mask].tail(days + 5).head(days)
    if len(df_nasdaq_period) < 2:
        return {"error": "纳指数据不足"}
    nasdaq_start = float(df_nasdaq_period.iloc[0]['close'])
    nasdaq_end = float(df_nasdaq_period.iloc[-1]['close'])
    nasdaq_ret = (nasdaq_end / nasdaq_start - 1) * 100

    # 3. 汇率变化
    df_fx = cached_call(
        SETTINGS,
        TRACKER,
        "qdii_fx_history",
        "AkShare currency_boc_safe",
        "qdii_fx_history",
        lambda: ak.currency_boc_safe(),
        None,
    )
    if df_fx is None:
        return {"error": "汇率历史数据不可用"}
    df_fx['日期'] = pd.to_datetime(df_fx['日期'])
    df_fx = df_fx.sort_values('日期')
    # USD/CNY列名检查
    fx_col = [c for c in df_fx.columns if '美元' in str(c) or 'USD' in str(c).upper()]
    if not fx_col:
        fx_col = [df_fx.columns[1]]  # fallback to second column
    fx_col = fx_col[0]
    df_fx['usdcny'] = pd.to_numeric(df_fx[fx_col].astype(str).str.replace(',', ''), errors='coerce') / 100  # 原始单位是人民币/百美元
    mask_fx = (df_fx['日期'] >= date_start - timedelta(days=5)) & (df_fx['日期'] <= date_end + timedelta(days=1))
    df_fx_period = df_fx[mask_fx].dropna(subset=['usdcny'])
    fx_start = float(df_fx_period.iloc[0]['usdcny'])
    fx_end = float(df_fx_period.iloc[-1]['usdcny'])
    fx_ret = (fx_end / fx_start - 1) * 100

    # 4. 三因子拆解
    # QDII收益 ≈ 纳指收益 + 汇率变化(美元涨=QDII涨) + 残差
    nasdaq_contrib = nasdaq_ret
    fx_contrib = fx_ret  # USD升值对QDII正贡献
    residual = fund_ret - nasdaq_contrib - fx_contrib
    total_explained = nasdaq_contrib + fx_contrib

    return {
        "period": f"{date_start.strftime('%m/%d')}→{date_end.strftime('%m/%d')}",
        "days": days,
        "fund_ret": round(fund_ret, 2),
        "nasdaq_ret": round(nasdaq_ret, 2),
        "fx_ret": round(fx_ret, 2),
        "nasdaq_contrib": round(nasdaq_contrib, 2),
        "fx_contrib": round(fx_contrib, 2),
        "residual": round(residual, 2),
        "explained_pct": round(abs(total_explained) / max(abs(fund_ret), 0.01) * 100, 1),
        "fx_start": round(fx_start, 4),
        "fx_end": round(fx_end, 4),
    }


def portfolio_risk_scan():
    """组合风险扫描：波动率+相关性+因子暴露"""
    missing = _missing_deps_error()
    if missing:
        return missing
    import json
    portfolio_path, _ = get_portfolio_path(SETTINGS)
    with open(portfolio_path, encoding="utf-8") as f:
        portfolio = json.load(f)

    holdings = portfolio['holdings']
    nav_series = {}
    for h in holdings:
        df = cached_call(
            SETTINGS,
            TRACKER,
            f"risk_fund_nav:{h['code']}",
            "AkShare fund_open_fund_info_em",
            f"risk_fund_nav:{h['code']}",
            lambda code=h['code']: ak.fund_open_fund_info_em(symbol=code, indicator="单位净值走势"),
            None,
        )
        if df is None:
            return {"error": f"{h['code']} 净值数据不可用"}
        df['净值日期'] = pd.to_datetime(df['净值日期'])
        df = df.tail(30).drop_duplicates(subset='净值日期')
        nav_series[h['code']] = df.set_index('净值日期')['单位净值'].astype(float)

    # 对齐日期
    common_dates = set(nav_series[holdings[0]['code']].index)
    for code in nav_series:
        common_dates &= set(nav_series[code].index)
    common_dates = sorted(common_dates)

    if len(common_dates) < 5:
        return {"error": "重叠交易日不足"}

    results = {}
    returns = {}
    for h in holdings:
        code = h['code']
        nav = nav_series[code][common_dates]
        ret = nav.pct_change().dropna()
        returns[code] = ret
        ann_vol = ret.std() * np.sqrt(252) * 100
        total_ret = (nav.iloc[-1] / nav.iloc[0] - 1) * 100
        results[code] = {
            "name": h['name'],
            "ann_vol": round(ann_vol, 1),
            "period_ret": round(total_ret, 2),
        }

    # 相关性
    if len(holdings) >= 2:
        codes = [h['code'] for h in holdings]
        ret_df = pd.DataFrame({c: returns[c] for c in codes})
        corr = ret_df.corr().iloc[0, 1]
        results['correlation'] = round(corr, 2)
        results['concentration_risk'] = "高" if corr > 0.7 else ("中" if corr > 0.4 else "低")
        results['crisis_note'] = "短期低相关但底层因子高度重合（全球科技Beta），危机时相关性会飙升"

    # 因子暴露定性
    results['factor_exposure'] = {
        "AI/科技成长": "高",
        "利率敏感": "高",
        "高估值": "高",
        "风险偏好": "高",
        "分散效果": "弱（表面A股+美股，底层高度同质）",
    }

    return results


def ai_fund_attribution(fund_code="011840", days=30):
    """AI基金三因子归因：指数贡献 + 行业轮动贡献 + 残差
    因子1: 中证AI指数(930713)贡献 — 基准beta
    因子2: 行业轮动 — 基金重仓行业vs整体AI行业的资金流差异
    因子3: 残差 — 个股选择alpha + 跟踪误差
    """
    missing = _missing_deps_error()
    if missing:
        return missing
    # 1. 基金净值序列
    df_fund = cached_call(
        SETTINGS,
        TRACKER,
        f"ai_fund_nav:{fund_code}",
        "AkShare fund_open_fund_info_em",
        f"ai_fund_nav:{fund_code}:{days}",
        lambda: ak.fund_open_fund_info_em(symbol=fund_code, indicator="单位净值走势"),
        None,
    )
    if df_fund is None:
        return {"error": "AI基金净值数据不可用"}
    df_fund['净值日期'] = pd.to_datetime(df_fund['净值日期'])
    df_fund = df_fund.tail(days + 5).drop_duplicates(subset='净值日期').tail(days)
    fund_start = float(df_fund.iloc[0]['单位净值'])
    fund_end = float(df_fund.iloc[-1]['单位净值'])
    fund_ret = (fund_end / fund_start - 1) * 100
    date_start = df_fund.iloc[0]['净值日期']
    date_end = df_fund.iloc[-1]['净值日期']

    # 2. 中证AI指数(930713) — 中证指数公司数据源，不受东方财富反爬影响
    start_str = (date_start - timedelta(days=5)).strftime('%Y%m%d')
    end_str = (date_end + timedelta(days=3)).strftime('%Y%m%d')
    df_index = cached_call(
        SETTINGS,
        TRACKER,
        "ai_index_history",
        "AkShare stock_zh_index_hist_csindex",
        f"ai_index_history:930713:{start_str}:{end_str}",
        lambda: ak.stock_zh_index_hist_csindex(symbol='930713', start_date=start_str, end_date=end_str),
        None,
    )
    if df_index is None:
        return {"error": "中证AI指数数据不可用"}
    df_index['日期'] = pd.to_datetime(df_index['日期'])
    df_index = df_index.sort_values('日期')
    if len(df_index) < 2:
        return {"error": "中证AI指数数据不足"}
    idx_start = float(df_index.iloc[0]['收盘'])
    idx_end = float(df_index.iloc[-1]['收盘'])
    index_ret = (idx_end / idx_start - 1) * 100

    # 3. 行业轮动因子 — AI基金重仓行业(半导体/软件开发/消费电子)的资金流 vs 整体市场
    # 用 sector_fund_flow_hist 查AI相关行业主力净流入，算加权平均净占比
    ai_industries = ['半导体', '软件开发', '消费电子', '通信设备', '计算机设备', '光学光电子']
    sector_results = []
    for ind in ai_industries:
        try:
            df_s = cached_call(
                SETTINGS,
                TRACKER,
                f"ai_sector_flow:{ind}",
                "AkShare stock_sector_fund_flow_hist",
                f"ai_sector_flow:{ind}:{date_start.date()}:{date_end.date()}",
                lambda ind=ind: ak.stock_sector_fund_flow_hist(symbol=ind),
                None,
            )
            if df_s is not None and len(df_s) > 0:
                df_s['日期'] = pd.to_datetime(df_s['日期'])
                mask = (df_s['日期'] >= date_start) & (df_s['日期'] <= date_end)
                df_s = df_s[mask]
                if len(df_s) > 0:
                    avg_net_pct = df_s['主力净流入-净占比'].mean()
                    sector_results.append(avg_net_pct)
        except Exception:
            continue

    if sector_results:
        rotation_contrib = round(np.mean(sector_results), 2)
    else:
        rotation_contrib = 0  # 数据不可用时置0，归入残差

    # 4. 三因子拆解
    index_contrib = index_ret  # 基准指数贡献
    residual = fund_ret - index_contrib - rotation_contrib
    total_explained = index_contrib + rotation_contrib

    return {
        "period": f"{date_start.strftime('%m/%d')}→{date_end.strftime('%m/%d')}",
        "days": days,
        "fund_ret": round(fund_ret, 2),
        "index_ret": round(index_ret, 2),
        "index_contrib": round(index_contrib, 2),
        "rotation_contrib": round(rotation_contrib, 2),
        "residual": round(residual, 2),
        "explained_pct": round(abs(total_explained) / max(abs(fund_ret), 0.01) * 100, 1),
        "sectors_queried": len(sector_results),
        "index_start": round(idx_start, 2),
        "index_end": round(idx_end, 2),
    }


if __name__ == "__main__":
    print("=== QDII三因子归因 ===")
    attr = qdii_attribution(days=30)
    for k, v in attr.items():
        print(f"  {k}: {v}")

    print("\n=== 组合风险扫描 ===")
    risk = portfolio_risk_scan()
    for k, v in risk.items():
        print(f"  {k}: {v}")
