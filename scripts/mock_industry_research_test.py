#!/usr/bin/env python3
"""Offline tests for industry research data adapter."""

from industry_research import fetch_industry_research


class FakeAkShare:
    @staticmethod
    def stock_fund_flow_industry():
        return [{"行业": "Example Industry", "净流入": 123}]

    @staticmethod
    def stock_fund_flow_concept():
        return [{"概念": "Example Theme", "净流入": 456}]


def fake_news_client(query):
    return [
        {
            "title": "Example industry crash warning",
            "content": "Sector pressure and crash risk update.",
        },
        {
            "title": "Example industry rally update",
            "content": "Sector rally and optimism update.",
        },
    ]


def _assert_contains(text, expected):
    if expected not in text:
        raise AssertionError(f"Expected text to contain: {expected}")


def _assert_not_contains(text, unexpected):
    if unexpected in text:
        raise AssertionError(f"Text should not contain: {unexpected}")


def run_industry_research_test():
    portfolio = {
        "holdings": [
            {
                "code": "PRIVATE_A",
                "name": "Private Holding A",
                "type": "stock",
                "strategy_type": "dca",
            }
        ],
        "watchlist": [{"code": "PRIVATE_W", "name": "Private Watch"}],
    }

    missing = fetch_industry_research(portfolio, ak_client=None)
    if missing["status"] != "skipped":
        raise AssertionError(f"Expected skipped without AkShare: {missing}")
    _assert_contains(" ".join(missing["limitations"]), "missing_dependency")
    missing_sources = "\n".join(
        f"{item['name']} {item['status']}" for item in missing["data_sources"]
    )
    _assert_contains(missing_sources, "industry_rotation missing_dependency")
    _assert_contains(missing_sources, "concept_rotation missing_dependency")

    result = fetch_industry_research(portfolio, ak_client=FakeAkShare)
    if result["status"] != "ok":
        raise AssertionError(f"Expected ok result: {result}")
    observations = "\n".join(result["observations"])
    _assert_contains(observations, "portfolio_driven_news_queries=2")
    _assert_contains(observations, "industry_rotation_rows=1")
    _assert_contains(observations, "concept_rotation_rows=1")

    news_result = fetch_industry_research(portfolio, ak_client=FakeAkShare, news_client=fake_news_client)
    if news_result["status"] != "ok":
        raise AssertionError(f"Expected ok result with news: {news_result}")
    news_observations = "\n".join(news_result["observations"])
    _assert_contains(news_observations, "news_results_found=4")
    _assert_contains(news_observations, "news_signal_red=2")
    _assert_contains(news_observations, "news_signal_green=2")
    news_evidence = "\n".join(item["label"] for item in news_result["evidence"])
    _assert_contains(news_evidence, "industry.news_results")
    news_sources = "\n".join(
        f"{item['name']} {item['status']}" for item in news_result["data_sources"]
    )
    _assert_contains(news_sources, "news_results available")

    evidence = "\n".join(item["label"] for item in result["evidence"])
    _assert_contains(evidence, "industry.news_queries")
    _assert_contains(evidence, "industry.rotation")
    _assert_contains(evidence, "industry.concept_rotation")
    data_sources = "\n".join(
        f"{item['name']} {item['status']}" for item in result["data_sources"]
    )
    _assert_contains(data_sources, "portfolio_context available")
    _assert_contains(data_sources, "industry_rotation available")
    _assert_contains(data_sources, "concept_rotation available")

    all_text = observations + "\n" + evidence + "\n" + data_sources + "\n" + news_observations + "\n" + news_evidence
    _assert_not_contains(all_text, "PRIVATE_A")
    _assert_not_contains(all_text, "PRIVATE_W")
    _assert_not_contains(all_text, "Private Holding A")
    _assert_not_contains(all_text, "Private Watch")
    _assert_not_contains(all_text, "买入")
    _assert_not_contains(all_text, "卖出")
    _assert_not_contains(all_text, "自动交易")


def main():
    run_industry_research_test()
    print("Mock industry research test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
