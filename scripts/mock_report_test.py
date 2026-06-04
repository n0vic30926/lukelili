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


def _assert_not_contains(text, unexpected):
    if unexpected in text:
        raise AssertionError(f"Expected report to omit: {unexpected}")


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


def run_daily_partial_failure_mock():
    import daily_finance_brief as daily

    daily.TRACKER.records.clear()
    daily.MISSING_RUNTIME_DEPS.clear()
    daily.USING_EXAMPLE_PORTFOLIO = True

    def fund_nav(code, days=10):
        if code == "000000":
            daily.TRACKER.fail(f"fund_nav:{code}", "fixture", "simulated fund nav failure")
            return None
        daily.TRACKER.ok(f"fund_nav:{code}", "fixture")
        return _fund_nav_frame().tail(days)

    daily.get_fund_nav = fund_nav
    daily.get_etf_quote = lambda codes: {}
    daily.get_us_index = lambda: None
    daily.get_fx_usdcny = lambda: None
    daily.get_north_flow = lambda: None
    daily.get_fund_top_holdings = lambda code: []
    daily.macro_observation = lambda ak, pd, settings, tracker: [
        "## 🌏 宏观观察",
        "",
        "- 宏观数据缺口: fixture simulated macro skip",
        "",
    ]
    daily.etf_observation = lambda ak, settings, tracker, holdings: [
        "## 🧾 ETF专项观察",
        "",
        "- 待补ETF数据: fixture simulated ETF gap",
        "",
    ]

    report = daily.main()
    _assert_contains(report, "当前使用示例持仓数据")
    _assert_contains(report, "数据获取失败")
    _assert_contains(report, "fund_nav:000000 | failed")
    _assert_contains(report, "新闻模块跳过")
    _assert_contains(report, "待补ETF数据")
    return report


def run_weekly_mock():
    import weekly_finance_review as weekly

    weekly.TRACKER.records.clear()
    weekly.MISSING_RUNTIME_DEPS.clear()
    weekly.USING_EXAMPLE_PORTFOLIO = True
    weekly.weekly_returns = lambda: [
        {
            "code": "000000",
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


def run_weekly_partial_failure_mock():
    import weekly_finance_review as weekly

    weekly.TRACKER.records.clear()
    weekly.MISSING_RUNTIME_DEPS.clear()
    weekly.USING_EXAMPLE_PORTFOLIO = True
    weekly.weekly_returns = lambda: []
    weekly.industry_rotation = lambda: None
    weekly.qdii_factor_weekly = lambda: {"error": "fixture qdii failure"}
    weekly.ai_fund_factor_weekly = lambda: {"error": "fixture ai failure"}
    weekly.decision_template = lambda rets, industry, qdii, ai: [
        "Fixture: 数据不足，仅保留用户确认前的观察。"
    ]

    def dca_curve_failure():
        weekly.TRACKER.fail("dca_curve", "fixture", "simulated dca curve failure")
        return []

    weekly.dca_curve = dca_curve_failure

    report = weekly.format_report()
    _assert_contains(report, "当前使用示例持仓数据")
    _assert_contains(report, "dca_curve | failed")
    _assert_contains(report, "Fixture: 数据不足")
    _assert_contains(report, "## 数据质量")
    return report


def run_etf_research_mock():
    from common.data_runtime import DataStatusTracker
    from common.market_research import etf_observation

    class FakeAk:
        @staticmethod
        def fund_etf_spot_em():
            return pd.DataFrame(
                [
                    {
                        "代码": "510000",
                        "最新价": 1.02,
                        "涨跌幅": 0.5,
                        "成交额": 250000000,
                        "IOPV": 1.0,
                    },
                    {
                        "代码": "159999",
                        "最新价": 1.5,
                        "涨跌幅": -0.2,
                        "成交额": 50000000,
                        "IOPV": 1.49,
                    }
                ]
            )

    settings = {
        "use_cache": False,
        "cache_ttl_hours": 0,
        "etf_analysis": {
            "premium_discount_warn_pct": 0.5,
            "premium_discount_high_pct": 1.0,
            "tracking_error_warn": 0.005,
            "tracking_error_high": 0.01,
        },
    }
    tracker = DataStatusTracker()
    holdings = [
        {
            "name": "Mock ETF Holding",
            "proxy_etf": "sh510000",
            "etf_profile": {
                "benchmark": "Mock Benchmark",
                "expense_ratio": 0.0015,
                "tracking_error": 0.002,
                "dividend_policy": "mock annual",
                "last_dividend_date": "2025-12-31",
                "tracking_history": [
                    {"date": "2026-01-01", "etf_return_pct": 1.0, "benchmark_return_pct": 0.8},
                    {"date": "2026-01-02", "etf_return_pct": -0.5, "benchmark_return_pct": -0.4},
                ],
                "dividend_history": [
                    {"ex_date": "2025-12-31", "amount": 0.02},
                    {"ex_date": "2025-06-30", "amount": 0.01},
                ],
            },
        },
        {
            "name": "High Fee ETF Holding",
            "proxy_etf": "sz159999",
            "etf_profile": {
                "benchmark": "Mock Benchmark",
                "expense_ratio": 0.005,
                "tracking_error": 0.015,
                "dividend_policy": "mock quarterly",
            },
        },
    ]

    report = "\n".join(etf_observation(FakeAk, settings, tracker, holdings))
    _assert_contains(report, "Mock Benchmark")
    _assert_contains(report, "费率: 0.15%")
    _assert_contains(report, "跟踪误差: 0.20%")
    _assert_contains(report, "分红: mock annual")
    _assert_contains(report, "溢价/折价: +2.00%")
    _assert_contains(report, "费率比较")
    _assert_contains(report, "低于同组中位数")
    _assert_contains(report, "高于同组中位数")
    _assert_contains(report, "溢价风险: high")
    _assert_contains(report, "跟踪风险: high")
    _assert_contains(report, "分红状态: 最近分红 2025-12-31")
    _assert_contains(report, "历史跟踪误差: 0.16%")
    _assert_contains(report, "分红记录: 2")
    _assert_contains(report, "分红率: 2.94%")
    _assert_contains(report, "分红状态: 缺少最近分红日期")
    return report


def run_macro_radar_mock():
    from common.data_runtime import DataStatusTracker
    from common.market_research import _parse_indicator_date, macro_indicator_lines

    if _parse_indicator_date("2026Q2").isoformat() != "2026-04-01":
        raise AssertionError("Quarter date parsing should map 2026Q2 to 2026-04-01")

    class FakeAk:
        @staticmethod
        def macro_china_cpi_monthly():
            return pd.DataFrame(
                [
                    {"月份": "2026-01", "今值": 1.0},
                    {"月份": "2026-02", "今值": 1.3},
                ]
            )

        @staticmethod
        def macro_china_pmi_yearly():
            return pd.DataFrame(
                [
                    {"月份": "2026-01", "制造业PMI": 49.8},
                    {"月份": "2026-02", "制造业PMI": 50.5},
                ]
            )

        @staticmethod
        def macro_china_money_supply():
            return pd.DataFrame(
                [
                    {"月份": "2026-01", "M2-同比增长": 8.0},
                    {"月份": "2026-02", "M2-同比增长": 8.4},
                ]
            )

        @staticmethod
        def macro_china_gdp_yearly():
            return pd.DataFrame(
                [
                    {"季度": "2026Q1", "今值": 4.8},
                    {"季度": "2026Q2", "今值": 5.1},
                ]
            )

        @staticmethod
        def bond_zh_us_rate():
            return pd.DataFrame(
                [
                    {"日期": "2026-01-01", "美国:国债收益率:10年": 4.1},
                    {"日期": "2026-01-02", "美国:国债收益率:10年": 4.2},
                ]
            )

    settings = {
        "use_cache": False,
        "cache_ttl_hours": 0,
        "fed_policy_calendar": {
            "source": "FOMC fixture",
            "source_tier": "official",
            "current_target_rate": "5.25%-5.50%",
            "events": [
                {
                    "date": "2026-03-18",
                    "event": "FOMC decision",
                    "watch": "dot plot and press conference",
                }
            ],
        },
        "macro_indicators": [
            {
                "id": "china_cpi",
                "label": "中国CPI",
                "candidate_functions": ["macro_china_cpi_monthly"],
                "date_columns": ["月份"],
                "value_columns": ["今值"],
                "unit": "%",
                "release_calendar": {
                    "next_release_date": "2026-03-09",
                    "source": "NBS fixture",
                    "source_tier": "official",
                    "note": "fixture calendar",
                },
                "interpretation": {
                    "trend_up": "通胀上行，利率和估值压力需要观察。",
                    "trend_down": "通胀回落，估值压力可能边际缓和。",
                },
            },
            {
                "id": "china_pmi",
                "label": "中国PMI",
                "candidate_functions": ["macro_china_pmi_yearly"],
                "date_columns": ["月份"],
                "value_columns": ["制造业PMI"],
                "unit": "",
                "interpretation": {
                    "threshold": 50,
                    "above": "制造业处于扩张区间。",
                    "below": "制造业处于收缩区间。",
                },
            },
            {
                "id": "china_money_supply",
                "label": "中国M2",
                "candidate_functions": ["macro_china_money_supply"],
                "date_columns": ["月份"],
                "value_columns": ["M2-同比增长"],
                "unit": "%",
            },
            {
                "id": "china_gdp",
                "label": "中国GDP",
                "candidate_functions": ["macro_china_gdp_yearly"],
                "date_columns": ["季度"],
                "value_columns": ["今值"],
                "unit": "%",
                "cadence": "quarterly",
                "interpretation": {
                    "trend_up": "增长动能边际改善。",
                    "trend_down": "增长动能边际走弱。",
                },
            },
            {
                "id": "us_treasury_10y",
                "label": "美国10Y国债收益率",
                "candidate_functions": ["bond_zh_us_rate"],
                "date_columns": ["日期"],
                "value_columns": ["美国:国债收益率:10年"],
                "unit": "%",
            },
            {
                "id": "missing_macro",
                "label": "缺失宏观指标",
                "candidate_functions": ["macro_missing_fixture"],
                "date_columns": ["日期"],
                "value_columns": ["今值"],
                "unit": "%",
            },
        ],
    }
    tracker = DataStatusTracker()
    report = "\n".join(macro_indicator_lines(FakeAk, settings, tracker))
    _assert_contains(report, "中国CPI")
    _assert_contains(report, "中国PMI")
    _assert_contains(report, "中国M2")
    _assert_contains(report, "中国GDP")
    _assert_contains(report, "美国10Y国债收益率")
    _assert_contains(report, "数据时效")
    _assert_contains(report, "通胀上行")
    _assert_contains(report, "制造业处于扩张区间")
    _assert_contains(report, "增长动能边际改善")
    _assert_not_contains(report, "日期不可解析 | cadence=quarterly")
    _assert_contains(report, "宏观发布日历")
    _assert_contains(report, "中国CPI: 下一发布日期 2026-03-09")
    _assert_contains(report, "source=NBS fixture")
    _assert_contains(report, "发布日历缺口")
    _assert_contains(report, "缺失宏观指标")
    _assert_contains(report, "Fed政策日历")
    _assert_contains(report, "当前目标利率: 5.25%-5.50%")
    _assert_contains(report, "2026-03-18 | FOMC decision")
    _assert_contains(report, "关注点: dot plot and press conference")
    _assert_contains(report, "宏观数据缺口")
    return report


def main():
    run_daily_mock()
    run_daily_partial_failure_mock()
    run_weekly_mock()
    run_weekly_partial_failure_mock()
    run_etf_research_mock()
    run_macro_radar_mock()
    print("Mock report test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
