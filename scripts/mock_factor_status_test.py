#!/usr/bin/env python3
"""Offline tests for factor and valuation status tracking."""

import qdii_three_factor as qdii
import valuation_anchor as valuation
from common.data_runtime import DataStatusTracker
from common.reporting import format_run_summary


def _assert_contains(text, expected):
    if expected not in text:
        raise AssertionError(f"Expected text to contain: {expected}")


def run_missing_dependency_status_test():
    qdii_ak = qdii.ak
    valuation_ak = valuation.ak
    qdii.ak = None
    valuation.ak = None
    try:
        tracker = DataStatusTracker()
        qdii_result = qdii.qdii_attribution(tracker=tracker)
        risk_result = qdii.portfolio_risk_scan(tracker=tracker)
        ai_result = qdii.ai_fund_attribution(tracker=tracker)
        nasdaq_result = valuation.nasdaq_valuation(tracker=tracker)
        ai_value_result = valuation.ai_index_valuation(tracker=tracker)

        for result in [qdii_result, risk_result, ai_result, nasdaq_result, ai_value_result]:
            if result.get("error") != "missing_dependency: akshare":
                raise AssertionError(f"Unexpected error result: {result}")

        rendered = format_run_summary(tracker.to_run_summary())
        _assert_contains(rendered, "- modules: success=0 failed=5 skipped=0 cache_hit=0")
        _assert_contains(rendered, "- data_module: qdii_attribution | status=failed | source=AkShare | error_type=RuntimeError")
        _assert_contains(rendered, "- data_module: portfolio_risk_scan | status=failed | source=AkShare | error_type=RuntimeError")
        _assert_contains(rendered, "- data_module: ai_fund_attribution | status=failed | source=AkShare | error_type=RuntimeError")
        _assert_contains(rendered, "- data_module: nasdaq_valuation | status=failed | source=AkShare | error_type=RuntimeError")
        _assert_contains(rendered, "- data_module: ai_index_valuation | status=failed | source=AkShare | error_type=RuntimeError")
    finally:
        qdii.ak = qdii_ak
        valuation.ak = valuation_ak


def main():
    run_missing_dependency_status_test()
    print("Mock factor status test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
