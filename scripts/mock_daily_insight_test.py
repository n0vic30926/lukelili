#!/usr/bin/env python3
"""Offline contract test for the human-readable daily insight layer."""

from daily_insight import build_daily_insight_context, format_daily_insight


def _assert_contains(text, expected):
    if expected not in text:
        raise AssertionError(f"missing expected text: {expected}")


def _assert_not_contains(text, unexpected):
    if unexpected in text:
        raise AssertionError(f"unexpected raw field in main body: {unexpected}")


def run_daily_insight_test():
    portfolio = {
        "cash": {"amount": 0, "target_weight_pct": 0},
        "risk_rules": {
            "single_loss_pct": 2,
            "daily_loss_pct": 6,
            "max_single_position_pct": 85,
            "max_underlying_position_pct": 75,
            "rebalance_tolerance_pct": 5,
        },
        "data_status": {"overlay_mode": "dry_run_provisional"},
        "holdings": [
            {
                "code": "FUND_A",
                "name": "Example AI Fund",
                "market": "CN",
                "strategy_type": "trial",
                "target_weight_pct": 20,
                "cost_basis": 4500,
                "expense_ratio": 0.8,
                "factor_profile": {"type": "cn_ai_theme", "benchmark": "AI"},
                "underlying_holdings": [
                    {"name": "chip_a", "weight_pct": 30},
                    {"name": "cloud_a", "weight_pct": 20},
                ],
                "return_history": [
                    {"date": "2026-06-01", "return_pct": -2.0},
                    {"date": "2026-06-02", "return_pct": 3.0},
                ],
            },
            {
                "code": "FUND_B",
                "name": "Example Nasdaq Fund",
                "market": "US_QDII",
                "strategy_type": "dca",
                "target_weight_pct": 80,
                "cost_basis": 19000,
                "expense_ratio": 0.66,
                "factor_profile": {"type": "us_tech", "benchmark": "NASDAQ100"},
                "buy_records": [
                    {"date": "2026-06-01", "amount": 1500, "status": "pending"},
                    {"date": "2026-06-02", "amount": 1500, "status": "pending"},
                ],
                "underlying_holdings": [
                    {"name": "chip_a", "weight_pct": 10},
                    {"name": "platform_b", "weight_pct": 15},
                ],
                "return_history": [
                    {"date": "2026-06-01", "return_pct": 1.0},
                    {"date": "2026-06-02", "return_pct": 0.5},
                ],
            },
        ],
    }
    report_items = [
        {
            "event": "report_written",
            "report_type": "daily",
            "created_at": "2026-06-04T15:30:00+08:00",
            "report_path": "",
            "run_summary": {
                "modules": {"success": 19, "failed": 0, "skipped": 1, "cache_hit": 2},
                "data_quality": {"fresh": 0, "stale": 0, "unknown": 20},
                "data_modules": [
                    {
                        "module": "news",
                        "status": "skipped",
                        "reason": "enable_news=false",
                    }
                ],
            },
        }
    ]
    text = format_daily_insight(build_daily_insight_context(portfolio, report_items))

    for expected in [
        "一句话结论",
        "今天最重要的事",
        "组合画像",
        "风险诊断",
        "行动建议",
        "观察触发器",
        "技术附录",
        "市场雷达与叙事核验",
        "认知迭代记录",
        "没有现金缓冲",
        "事实上的主仓",
        "待确认",
        "增厚原有风险",
        "可观察代码",
    ]:
        _assert_contains(text, expected)

    main_body = text.split("## 技术附录", 1)[0]
    for raw_field in [
        "cash_pct",
        "max_position_pct",
        "workflow_exit_code",
        "commands_failed",
        "strategy_counts",
        "overlay_mode",
    ]:
        _assert_not_contains(main_body, raw_field)


def main():
    run_daily_insight_test()
    print("Mock daily insight test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
