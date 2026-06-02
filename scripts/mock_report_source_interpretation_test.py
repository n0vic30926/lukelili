#!/usr/bin/env python3
"""Offline tests for report data-source interpretation."""

from common.report_source_interpretation import interpret_data_module


def _assert_contains(text, expected):
    if expected not in text:
        raise AssertionError(f"Expected text to contain: {expected}")


def _assert_not_contains(text, unexpected):
    if unexpected in text:
        raise AssertionError(f"Text should not contain: {unexpected}")


def run_report_source_interpretation_test():
    success = interpret_data_module(
        {"module": "fund_nav", "status": "success", "source": "AkShare", "freshness": "fresh"}
    )
    _assert_contains(success, "fund_nav")
    _assert_contains(success, "available")
    _assert_contains(success, "fresh")

    failed = interpret_data_module(
        {
            "module": "north_flow",
            "status": "failed",
            "source": "AkShare",
            "freshness": "unknown",
            "error_type": "RuntimeError",
        }
    )
    _assert_contains(failed, "north_flow")
    _assert_contains(failed, "unavailable")
    _assert_contains(failed, "report section remains incomplete")
    _assert_not_contains(failed, "RuntimeError")

    skipped = interpret_data_module(
        {
            "module": "industry_news",
            "status": "skipped",
            "source": "Tavily",
            "freshness": "unknown",
            "reason": "disabled",
        }
    )
    _assert_contains(skipped, "industry_news")
    _assert_contains(skipped, "skipped")
    _assert_contains(skipped, "configuration or missing inputs")

    combined = "\n".join([success, failed, skipped])
    _assert_not_contains(combined, "PRIVATE")
    _assert_not_contains(combined, "买入")
    _assert_not_contains(combined, "卖出")
    _assert_not_contains(combined, "自动交易")


def main():
    run_report_source_interpretation_test()
    print("Mock report source interpretation test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
