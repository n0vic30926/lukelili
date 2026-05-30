#!/usr/bin/env python3
"""Offline report-level checks with mocked market data."""

from datetime import datetime

import pandas as pd


def _fund_nav_frame():
    return pd.DataFrame(
        [
            {"净值日期": pd.Timestamp("2026-01-01"), "单位净值": 1.0, "日增长率": 0.1},
            {"净值日期": pd.Timestamp("2026-01-02"), "单位净值": 1.01, "日增长率": 1.0},
            {"净值日期": pd.Timestamp("2026-01-05"), "单位净值": 1.02, "日增长率": 0.99},
            {"净值日期": pd.Timestamp("2026-01-06"), "单位净值": 1.03, "日增长率": 0.98},
            {"净值日期": pd.Timestamp("2026-01-07"), "单位净值": 1.04, "日增长率": 0.97},
        ]
    )


def _assert_contains(text, expected):
    if expected not in text:
        raise AssertionError(f"Expected report to contain: {expected}")


def run_daily_mock():
    import daily_finance_brief as daily

    daily.TRACKER.records.clear()
    daily.MISSING_RUNTIME_DEPS.clear()
    daily.USING_EXAMPLE_PORTFOLIO = True
    daily.get_fund_nav = lambda code, days=10: _fund_nav_frame().tail(days)
    daily.get_etf_quote = lambda codes: {
        code: {"name": f"Mock ETF {code}", "price": 1.23, "change_pct": 0.5, "volume": 1000000}
        for code in codes
    }
    daily.get_us_index = lambda: pd.DataFrame(
        [
            {"date": "2026-01-06", "close": 100.0},
            {"date": "2026-01-07", "close": 101.0},
        ]
    )
    daily.get_fx_usdcny = lambda: {"rate": 7.1}
    daily.get_north_flow = lambda: [
        {
            "board": "mock",
            "date": "2026-01-07",
            "net_buy": 100000000,
            "net_flow": 100000000,
            "index_name": "Mock Index",
            "index_chg": 0.3,
        }
    ]
    daily.get_fund_top_holdings = lambda code: []
    daily.macro_observation = lambda ak, pd, settings, tracker: ["## 🌏 宏观观察", "", "- Mock macro ok", ""]
    daily.etf_observation = lambda ak, settings, tracker, holdings: ["## 🧾 ETF专项观察", "", "- Mock ETF ok", ""]

    report = daily.main()
    _assert_contains(report, "## 运行摘要")
    _assert_contains(report, "## 数据质量")
    _assert_contains(report, "当前使用示例持仓数据")
    _assert_contains(report, "## 📈 持仓基金")
    _assert_contains(report, "## 🌏 宏观观察")
    _assert_contains(report, "## 🧾 ETF专项观察")
    return report


def run_weekly_mock():
    import weekly_finance_review as weekly

    weekly.TRACKER.records.clear()
    weekly.MISSING_RUNTIME_DEPS.clear()
    weekly.USING_EXAMPLE_PORTFOLIO = True
    weekly.weekly_returns = lambda: [
        {
            "code": "000001",
            "name": "Mock Fund",
            "week_ret": 1.23,
            "pnl": 100,
            "pnl_pct": 1.0,
        }
    ]
    weekly.industry_rotation = lambda: {
        "inflow": [{"行业": "Mock Industry", "净额": 1.0, "行业-涨跌幅": 0.5}],
        "outflow": [{"行业": "Other Industry", "净额": -1.0, "行业-涨跌幅": -0.5}],
        "source": "mock",
    }
    weekly.qdii_factor_weekly = lambda: {"fund_ret": 1.0, "nasdaq_contrib": 0.8, "fx_contrib": 0.1, "residual": 0.1}
    weekly.ai_fund_factor_weekly = lambda: {"fund_ret": 1.0, "index_contrib": 0.8, "rotation_contrib": 0.1, "residual": 0.1}
    weekly.dca_curve = lambda: []

    report = weekly.format_report()
    _assert_contains(report, "## 运行摘要")
    _assert_contains(report, "## 数据质量")
    _assert_contains(report, "当前使用示例持仓数据")
    _assert_contains(report, "## 📈 本周收益")
    return report


def main():
    run_daily_mock()
    run_weekly_mock()
    print("Mock report test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
