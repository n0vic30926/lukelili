#!/usr/bin/env python3
"""Offline tests for data adapter audit helpers."""

from audit_data_adapters import audit_settings, format_audit


class FakeAkShare:
    @staticmethod
    def macro_china_cpi_monthly():
        raise AssertionError("audit must not call adapter functions")

    @staticmethod
    def fund_etf_spot_em():
        raise AssertionError("audit must not call adapter functions")


def _assert_contains(text, expected):
    if expected not in text:
        raise AssertionError(f"Expected audit to contain: {expected}")


def run_adapter_audit_test():
    settings = {
        "fed_policy_calendar": {
            "source": "FOMC fixture",
            "source_tier": "official",
            "events": [{"date": "2026-03-18", "event": "FOMC decision"}],
        },
        "macro_indicators": [
            {
                "id": "china_cpi",
                "label": "中国CPI",
                "candidate_functions": ["macro_china_cpi_monthly", "macro_missing_fixture"],
                "date_columns": ["月份"],
                "value_columns": ["今值"],
                "cadence": "monthly",
                "max_age_days": 75,
                "release_calendar": {
                    "source": "NBS fixture",
                    "source_tier": "official",
                    "next_release_date": "2026-03-09",
                },
            },
            {
                "id": "broken_macro",
                "label": "坏宏观指标",
                "candidate_functions": [],
                "date_columns": ["日期"],
                "value_columns": [],
            },
        ],
    }
    audit = audit_settings(settings, ak_module=FakeAkShare)
    report = "\n".join(format_audit(audit))
    _assert_contains(report, "AkShare dependency: injected")
    _assert_contains(report, "宏观 adapter: 中国CPI | status=ok")
    _assert_contains(report, "available=macro_china_cpi_monthly")
    _assert_contains(report, "missing=macro_missing_fixture")
    _assert_contains(report, "宏观 adapter: 坏宏观指标 | status=config_issue")
    _assert_contains(report, "candidate_functions")
    _assert_contains(report, "value_columns")
    _assert_contains(report, "release_calendar")
    _assert_contains(report, "Fed policy calendar: status=ok")
    _assert_contains(report, "ETF adapter: ETF行情 | function=fund_etf_spot_em | status=ok")


def main():
    run_adapter_audit_test()
    print("Mock adapter audit test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
