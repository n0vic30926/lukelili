#!/usr/bin/env python3
"""Offline tests for daily report data module status tracking."""

import pandas as pd

import daily_finance_brief as daily
from common.data_runtime import DataStatusTracker
from common.reporting import format_run_summary


class FakeAkShare:
    @staticmethod
    def fund_open_fund_info_em(symbol, indicator):
        return pd.DataFrame(
            [
                {"净值日期": "2026-05-29", "单位净值": 1.0, "日增长率": 0.1},
                {"净值日期": "2026-05-30", "单位净值": 1.1, "日增长率": 1.0},
            ]
        )

    @staticmethod
    def stock_hsgt_fund_flow_summary_em():
        raise RuntimeError("private upstream details")


def _assert_contains(text, expected):
    if expected not in text:
        raise AssertionError(f"Expected text to contain: {expected}")


def run_daily_data_status_test():
    original_ak = daily.ak
    daily.ak = FakeAkShare
    try:
        tracker = DataStatusTracker()
        nav = daily.get_fund_nav("000000", days=2, tracker=tracker)
        if nav is None or len(nav) != 2:
            raise AssertionError("Expected fake NAV data")

        north = daily.get_north_flow(tracker=tracker)
        if north is not None:
            raise AssertionError("Expected failed north flow fallback")

        etf = daily.get_etf_quote([], tracker=tracker)
        if etf != {}:
            raise AssertionError("Expected skipped ETF fallback")

        summary = daily.build_run_summary(tracker)
        rendered = format_run_summary(summary)
        _assert_contains(rendered, "- modules: success=1 failed=1 skipped=1 cache_hit=0")
        _assert_contains(rendered, "- data_module: fund_nav | status=success | source=AkShare")
        _assert_contains(rendered, "- data_module: north_flow | status=failed | source=AkShare | error_type=RuntimeError")
        _assert_contains(rendered, "- data_module: etf_quote | status=skipped | source=AkShare | reason=no_codes")
        if "private upstream details" in rendered:
            raise AssertionError("Runtime summary should not expose raw upstream error text")
    finally:
        daily.ak = original_ak


def main():
    run_daily_data_status_test()
    print("Mock daily status test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
