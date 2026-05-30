#!/usr/bin/env python3
"""
估值锚模块 — 纯状态提示，不择时
- 纳指100：点位历史百分位（1年/2年）
- 中证AI指数：PE滚动市盈率百分位（2024至今）
- 定投仓位：只输出"贵不贵"，不输出"该不该买"
"""
import akshare as ak
import pandas as pd
import numpy as np


def nasdaq_valuation():
    """纳指100估值锚：点位历史百分位"""
    try:
        df = ak.index_us_stock_sina(symbol=".IXIC")
        df['close'] = pd.to_numeric(df['close'], errors='coerce')

        latest = float(df.iloc[-1]['close'])

        # 1年百分位
        df_1y = df.tail(252)
        pct_1y = round((df_1y['close'] < latest).sum() / len(df_1y) * 100, 1)

        # 2年百分位
        df_2y = df.tail(504)
        pct_2y = round((df_2y['close'] < latest).sum() / len(df_2y) * 100, 1)

        # 区间
        low_1y = float(df_1y['close'].min())
        high_1y = float(df_1y['close'].max())

        # 定性判断
        if pct_1y >= 95:
            level = "历史高位"
        elif pct_1y >= 80:
            level = "偏高"
        elif pct_1y >= 50:
            level = "中等偏上"
        elif pct_1y >= 20:
            level = "中等"
        else:
            level = "偏低"

        return {
            'index': '纳斯达克综合',
            'latest': round(latest, 1),
            'pct_1y': pct_1y,
            'pct_2y': pct_2y,
            'range_1y': f"{low_1y:.0f}~{high_1y:.0f}",
            'level': level,
            'metric': '点位百分位',
        }
    except Exception as e:
        return {'error': str(e)}


def ai_index_valuation():
    """中证AI指数估值锚：PE滚动市盈率百分位"""
    try:
        df = ak.stock_zh_index_hist_csindex(symbol='930713', start_date='20240101', end_date='20991231')
        pe_col = '滚动市盈率'
        df[pe_col] = pd.to_numeric(df[pe_col], errors='coerce')
        df = df.dropna(subset=[pe_col])

        latest_pe = float(df.iloc[-1][pe_col])
        pe_pct = round((df[pe_col] < latest_pe).sum() / len(df) * 100, 1)
        pe_min = round(float(df[pe_col].min()), 2)
        pe_max = round(float(df[pe_col].max()), 2)

        # 定性判断
        if pe_pct >= 95:
            level = "历史高位"
        elif pe_pct >= 80:
            level = "偏高"
        elif pe_pct >= 50:
            level = "中等偏上"
        elif pe_pct >= 20:
            level = "中等"
        else:
            level = "偏低"

        return {
            'index': '中证AI',
            'latest_pe': latest_pe,
            'pe_pct': pe_pct,
            'pe_range': f"{pe_min}~{pe_max}",
            'level': level,
            'metric': 'PE百分位(2024至今)',
        }
    except Exception as e:
        return {'error': str(e)}


def format_valuation():
    """格式化输出估值锚"""
    lines = []
    lines.append("## ⚓ 估值锚（风险提示，非交易信号）")
    lines.append("")

    # 纳指
    nsdq = nasdaq_valuation()
    if 'error' not in nsdq:
        lines.append(f"- **纳指100**: 点位{nsdq['latest']} | 1年百分位{nsdq['pct_1y']}% | {nsdq['level']}")
        lines.append(f"  区间: {nsdq['range_1y']} | 2年百分位: {nsdq['pct_2y']}%")
    else:
        lines.append(f"- 纳指估值: 获取失败")

    # AI指数
    ai = ai_index_valuation()
    if 'error' not in ai:
        lines.append(f"- **中证AI**: PE {ai['latest_pe']} | 百分位{ai['pe_pct']}% | {ai['level']}")
        lines.append(f"  PE区间: {ai['pe_range']}")
    else:
        lines.append(f"- AI估值: 获取失败")

    lines.append("")
    lines.append("> 估值锚是风险提示器，不构成交易建议。高估值≠马上跌，低估值≠马上涨。")
    lines.append("")
    return '\n'.join(lines)


if __name__ == "__main__":
    print(format_valuation())
