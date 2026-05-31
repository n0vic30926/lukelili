#!/usr/bin/env python3
"""Offline tests for weekly report data module status tracking."""

import pandas as pd

import weekly_finance_review as weekly
from common.data_runtime import DataStatusTracker
from common.reporting import format_run_summary


class FakeAkShare:
    @staticmethod
    def fund_open_fund_info_em(symbol, indicator):
        return pd.DataFrame(
            [
                {"净值日期": "2026-05-25", "单位净值": 1.0},
                {"净值日期": "2026-05-29", "单位净值": 1.1},
            ]
        )

    @staticmethod
    def stock_fund_flow_industry():
        raise RuntimeError("private industry upstream detail")

    @staticmethod
    def stock_sector_fund_flow_hist(symbol):
        raise RuntimeError("private fallback detail")


def _assert_contains(text, expected):
    if expected not in text:
        raise AssertionError(f"Expected text to contain: {expected}")


def run_weekly_data_status_test():
    original_ak = weekly.ak
    weekly.ak = FakeAkShare
    try:
        tracker = DataStatusTracker()
        rets = weekly.weekly_returns(tracker=tracker)
        if not rets or rets[0]["week_ret"] != 10.0:
            raise AssertionError(f"Unexpected weekly returns: {rets}")

        industry = weekly.industry_rotation(tracker=tracker)
        if industry is not None:
            raise AssertionError("Expected failed industry fallback")

        dca = weekly.dca_curve(tracker=tracker)
        if not dca:
            raise AssertionError("Expected fake DCA curve")

        summary = weekly.build_run_summary(tracker)
        rendered = format_run_summary(summary)
        _assert_contains(rendered, "- modules: success=2 failed=1 skipped=0 cache_hit=0")
        _assert_contains(rendered, "- data_module: weekly_returns | status=success | source=AkShare")
        _assert_contains(rendered, "- data_module: industry_rotation | status=failed | source=AkShare | source_tier=community_data | freshness=unknown | error_type=RuntimeError")
        _assert_contains(rendered, "- data_module: dca_curve | status=success | source=AkShare")
        if "private industry upstream detail" in rendered or "private fallback detail" in rendered:
            raise AssertionError("Runtime summary should not expose raw upstream error text")
    finally:
        weekly.ak = original_ak


def main():
    run_weekly_data_status_test()
    print("Mock weekly status test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
