#!/usr/bin/env python3
"""Offline tests for individual security research data adapter."""

from security_research import fetch_security_research


class FakeAkShare:
    @staticmethod
    def stock_financial_abstract(symbol):
        return [{"报告期": "2026Q1", "净利润": 123}]

    @staticmethod
    def stock_notice_report(symbol):
        return [{"公告标题": "Example filing"}]

    @staticmethod
    def stock_a_indicator_lg(symbol):
        return [{"pe": 18.5, "pb": 2.1}]

    @staticmethod
    def stock_zh_a_spot_em():
        return [{"代码": "000001", "最新价": 12.3, "成交额": 456789}]

    @staticmethod
    def stock_research_report_em(symbol):
        return [{"标题": "Example report"}]


def _assert_contains(text, expected):
    if expected not in text:
        raise AssertionError(f"Expected text to contain: {expected}")


def run_security_research_test():
    missing = fetch_security_research("000001", ak_client=None)
    if missing["status"] != "skipped":
        raise AssertionError(f"Expected skipped without AkShare: {missing}")
    _assert_contains(" ".join(missing["limitations"]), "missing_dependency")

    result = fetch_security_research("000001", ak_client=FakeAkShare)
    if result["status"] != "ok":
        raise AssertionError(f"Expected ok result: {result}")
    observations = "\n".join(result["observations"])
    _assert_contains(observations, "financial_statements_rows=1")
    _assert_contains(observations, "announcements_rows=1")
    _assert_contains(observations, "valuation_metrics_rows=1")
    _assert_contains(observations, "security_market_quotes_found=1")
    _assert_contains(observations, "research_reports_rows=1")
    evidence = "\n".join(item["label"] for item in result["evidence"])
    _assert_contains(evidence, "security.financial_statements")
    _assert_contains(evidence, "security.announcements")
    _assert_contains(evidence, "security.valuation_metrics")
    _assert_contains(evidence, "security.market_quotes")
    _assert_contains(evidence, "security.research_reports")
    data_sources = "\n".join(
        f"{item['name']} {item['status']}" for item in result["data_sources"]
    )
    _assert_contains(data_sources, "financial_statements available")
    _assert_contains(data_sources, "announcements available")
    _assert_contains(data_sources, "valuation_metrics available")
    _assert_contains(data_sources, "security_market_quotes available")
    _assert_contains(data_sources, "research_reports available")


def main():
    run_security_research_test()
    print("Mock security research test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
