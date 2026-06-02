#!/usr/bin/env python3
"""Offline tests for ETF research data adapter."""

from etf_research import fetch_etf_research


class FakeAkShare:
    @staticmethod
    def fund_etf_spot_em():
        return [
            {
                "代码": "513100",
                "名称": "Example ETF",
                "最新价": 1.23,
                "涨跌幅": 0.5,
                "成交额": 1234567,
            }
        ]

    @staticmethod
    def fund_etf_fund_info_em(symbol):
        return [{"净值日期": "2026-05-29", "单位净值": 1.20}]

    @staticmethod
    def fund_portfolio_hold_em(symbol, date):
        return [{"股票名称": "Example Holding", "持仓占比": "10.0%"}]


def _assert_contains(text, expected):
    if expected not in text:
        raise AssertionError(f"Expected text to contain: {expected}")


def run_etf_research_test():
    missing = fetch_etf_research(["sh513100"], ak_client=None)
    if missing["status"] != "skipped":
        raise AssertionError(f"Expected skipped without AkShare: {missing}")
    _assert_contains(" ".join(missing["limitations"]), "missing_dependency")

    result = fetch_etf_research(["sh513100"], ak_client=FakeAkShare)
    if result["status"] != "ok":
        raise AssertionError(f"Expected ok result: {result}")
    observations = "\n".join(result["observations"])
    _assert_contains(observations, "etf_quotes_found=1/1")
    _assert_contains(observations, "liquidity_amount_available=1")
    _assert_contains(observations, "premium_discount_available=1")
    _assert_contains(observations, "etf_nav_history_available=1")
    _assert_contains(observations, "etf_holdings_available=1")
    evidence = "\n".join(item["label"] for item in result["evidence"])
    _assert_contains(evidence, "etf.quotes")
    _assert_contains(evidence, "etf.premium_discount")
    _assert_contains(evidence, "etf.nav_history")
    _assert_contains(evidence, "etf.holdings")
    data_sources = "\n".join(
        f"{item['name']} {item['status']}" for item in result["data_sources"]
    )
    _assert_contains(data_sources, "etf_quotes available")
    _assert_contains(data_sources, "liquidity_metrics available")
    _assert_contains(data_sources, "premium_discount available")
    _assert_contains(data_sources, "etf_nav_history available")
    _assert_contains(data_sources, "etf_holdings available")


def main():
    run_etf_research_test()
    print("Mock ETF research test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
