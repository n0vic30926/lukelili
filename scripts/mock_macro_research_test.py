#!/usr/bin/env python3
"""Offline tests for macro research data adapter."""

from macro_research import fetch_macro_research


class FakeAkShare:
    @staticmethod
    def bond_zh_us_rate():
        return [{"date": "2026-06-01", "us10y": 4.5}]

    @staticmethod
    def fx_spot_quote():
        return [{"货币对": "USD/CNY", "买报价": 7.1}]

    @staticmethod
    def macro_china_money_supply():
        return [{"月份": "2026-05", "M2同比": 7.2}]


def _assert_contains(text, expected):
    if expected not in text:
        raise AssertionError(f"Expected text to contain: {expected}")


def run_macro_research_test():
    missing = fetch_macro_research(ak_client=None)
    if missing["status"] != "skipped":
        raise AssertionError(f"Expected skipped without AkShare: {missing}")
    _assert_contains(" ".join(missing["limitations"]), "missing_dependency")

    result = fetch_macro_research(ak_client=FakeAkShare)
    if result["status"] != "ok":
        raise AssertionError(f"Expected ok result: {result}")
    observations = "\n".join(result["observations"])
    _assert_contains(observations, "macro_rates_rows=1")
    _assert_contains(observations, "fx_rates_rows=1")
    _assert_contains(observations, "liquidity_indicators_rows=1")
    evidence = "\n".join(item["label"] for item in result["evidence"])
    _assert_contains(evidence, "macro.rates")
    _assert_contains(evidence, "macro.fx")
    _assert_contains(evidence, "macro.liquidity")
    data_sources = "\n".join(
        f"{item['name']} {item['status']}" for item in result["data_sources"]
    )
    _assert_contains(data_sources, "macro_rates available")
    _assert_contains(data_sources, "fx_rates available")
    _assert_contains(data_sources, "liquidity_indicators available")


def main():
    run_macro_research_test()
    print("Mock macro research test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
