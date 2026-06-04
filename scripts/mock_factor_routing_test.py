#!/usr/bin/env python3
"""Offline tests for portfolio-driven factor attribution routing."""

from qdii_three_factor import build_factor_jobs, format_factor_result


def _assert_contains(text, expected):
    if expected not in text:
        raise AssertionError(f"Expected text to contain: {expected}")


def _assert_not_contains(text, unexpected):
    if unexpected in text:
        raise AssertionError(f"Text should not contain: {unexpected}")


def run_factor_routing_test():
    portfolio = {
        "holdings": [
            {
                "code": "FUND_A",
                "name": "Example Global Tech Fund",
                "factor_profile": {"type": "qdii_us_equity", "benchmark": "NASDAQ"},
            },
            {
                "code": "FUND_B",
                "name": "Example AI Theme Fund",
                "factor_profile": {"type": "a_share_ai", "benchmark": "CSI_AI"},
            },
            {
                "code": "FUND_D",
                "name": "Example CN AI Theme Alias",
                "factor_profile": {"type": "cn_ai_theme_equity", "benchmark": "CSI_AI"},
            },
            {
                "code": "FUND_C",
                "name": "Example Cash Fund",
                "factor_profile": {"type": "none"},
            },
        ]
    }
    jobs = build_factor_jobs(portfolio)
    if [job["code"] for job in jobs] != ["FUND_A", "FUND_B", "FUND_D"]:
        raise AssertionError(f"Unexpected jobs: {jobs}")
    if [job["attribution_type"] for job in jobs] != ["qdii_us_equity", "a_share_ai", "a_share_ai"]:
        raise AssertionError(f"Unexpected job types: {jobs}")

    qdii_text = format_factor_result(
        jobs[0],
        {
            "fund_ret": 1.2,
            "nasdaq_contrib": 0.8,
            "fx_contrib": 0.1,
            "residual": 0.3,
            "explained_pct": 75,
        },
    )
    ai_text = format_factor_result(
        jobs[1],
        {
            "fund_ret": -2.1,
            "index_contrib": -1.4,
            "rotation_contrib": -0.2,
            "residual": -0.5,
            "explained_pct": 80,
        },
    )

    _assert_contains(qdii_text, "Example Global Tech Fund")
    _assert_contains(qdii_text, "纳指贡献")
    _assert_contains(ai_text, "Example AI Theme Fund")
    _assert_contains(ai_text, "指数贡献")
    _assert_not_contains(qdii_text + ai_text, "016452")
    _assert_not_contains(qdii_text + ai_text, "011840")


def main():
    run_factor_routing_test()
    print("Mock factor routing test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
