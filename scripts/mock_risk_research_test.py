#!/usr/bin/env python3
"""Offline tests for portfolio risk research data adapter."""

from risk_research import fetch_risk_research


class FakeAkShare:
    @staticmethod
    def fund_etf_spot_em():
        return [{"代码": "513100", "最新价": 1.23, "成交额": 123456}]

    @staticmethod
    def stock_zh_a_spot_em():
        return [{"代码": "000001", "最新价": 12.3, "成交额": 456789}]

    @staticmethod
    def stock_zh_index_spot_em():
        return [{"代码": "000001", "名称": "Example Index", "最新价": 3000}]


def _assert_contains(text, expected):
    if expected not in text:
        raise AssertionError(f"Expected text to contain: {expected}")


def _assert_not_contains(text, unexpected):
    if unexpected in text:
        raise AssertionError(f"Text should not contain: {unexpected}")


def run_risk_research_test():
    portfolio = {
        "cash": {"amount": 500},
        "risk_rules": {"single_loss_pct": 2, "daily_loss_pct": 6, "max_single_position_pct": 50},
        "holdings": [
            {
                "code": "PRIVATE_A",
                "name": "Private Holding A",
                "type": "stock",
                "market": "a_share",
                "proxy_etf": "sh513100",
                "cost_basis": 1400,
                "strategy_type": "dca",
                "factor_profile": {"type": "qdii_us_equity"},
            },
            {
                "code": "PRIVATE_B",
                "name": "Private Holding B",
                "cost_basis": 100,
                "strategy_type": "trial",
                "factor_profile": {"type": "none"},
            },
        ],
    }

    missing = fetch_risk_research(portfolio, ak_client=None)
    if missing["status"] != "skipped":
        raise AssertionError(f"Expected skipped without AkShare: {missing}")
    _assert_contains(" ".join(missing["limitations"]), "missing_dependency")
    _assert_contains("\n".join(missing["observations"]), "market_quote_matches=0/2")

    result = fetch_risk_research(portfolio, ak_client=FakeAkShare)
    if result["status"] != "ok":
        raise AssertionError(f"Expected ok result: {result}")
    observations = "\n".join(result["observations"])
    _assert_contains(observations, "holding_count=2")
    _assert_contains(observations, "cash_pct=25.0")
    _assert_contains(observations, "max_position_pct=70.0")
    _assert_contains(observations, "exposure_warnings=1")
    _assert_contains(observations, "risk_limit_breaches=1")
    _assert_contains(observations, "cash_buffer_pct=25.0")
    _assert_contains(observations, "factor_profile_count=1")
    _assert_contains(observations, "market_quote_matches=1/2")
    _assert_contains(observations, "benchmark_quotes_rows=1")

    evidence = "\n".join(item["label"] for item in result["evidence"])
    _assert_contains(evidence, "portfolio.exposure")
    _assert_contains(evidence, "portfolio.risk_rules")
    _assert_contains(evidence, "portfolio.cash_buffer")
    _assert_contains(evidence, "portfolio.risk_limit_breaches")
    _assert_contains(evidence, "portfolio.factor_profile")
    _assert_contains(evidence, "risk.market_quotes")
    _assert_contains(evidence, "risk.benchmark_quotes")

    data_sources = "\n".join(
        f"{item['name']} {item['source']} {item['status']}" for item in result["data_sources"]
    )
    _assert_contains(data_sources, "risk_rules local available")
    _assert_contains(data_sources, "portfolio_exposure local available")
    _assert_contains(data_sources, "cash_buffer local available")
    _assert_contains(data_sources, "risk_limit_breaches local available")
    _assert_contains(data_sources, "factor_exposure local available")
    _assert_contains(data_sources, "market_quotes AkShare available")
    _assert_contains(data_sources, "benchmark_quotes AkShare available")

    all_text = observations + "\n" + evidence + "\n" + data_sources
    _assert_not_contains(all_text, "PRIVATE_A")
    _assert_not_contains(all_text, "PRIVATE_B")
    _assert_not_contains(all_text, "Private Holding")
    _assert_not_contains(all_text, "513100")
    _assert_not_contains(all_text, "000001")
    _assert_not_contains(all_text, "买入")
    _assert_not_contains(all_text, "卖出")
    _assert_not_contains(all_text, "自动交易")


def main():
    run_risk_research_test()
    print("Mock risk research test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
