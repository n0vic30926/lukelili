#!/usr/bin/env python3
"""Offline tests for market narrative radar and portfolio-fit mapping."""

from market_radar import build_market_radar, format_market_radar


def _assert_contains(text, expected):
    if expected not in text:
        raise AssertionError(f"missing expected text: {expected}")


def run_market_radar_test():
    portfolio = {
        "holdings": [
            {
                "name": "Example AI Theme Fund",
                "market": "CN",
                "cost_basis": 4000,
                "factor_profile": {"type": "cn_ai_theme_equity", "benchmark": "CSI_AI_THEME"},
            },
            {
                "name": "Example Nasdaq QDII",
                "market": "US_QDII",
                "cost_basis": 16000,
                "factor_profile": {"type": "qdii_us_equity", "benchmark": "NASDAQ100"},
            },
        ]
    }
    radar_config = {
        "themes": [
            {
                "theme_id": "memory_hbm",
                "name": "存储 / HBM",
                "thesis": "AI memory bottleneck",
                "exposure_tags": ["ai", "semiconductor", "memory"],
                "narratives": [
                    {
                        "claim": "HBM demand may benefit memory makers",
                        "evidence_level": "radar_only",
                        "source_note": "needs verification",
                    }
                ],
                "instruments": [
                    {"code": "MU", "name": "美光科技", "market": "US", "access": "美股 ticker"}
                ],
            },
            {
                "theme_id": "defensive_rotation",
                "name": "防守轮动",
                "thesis": "quality diversification",
                "exposure_tags": ["defensive", "financials", "quality"],
                "narratives": [
                    {
                        "claim": "quality stocks may diversify technology beta",
                        "evidence_level": "major_media",
                        "source_note": "example media source",
                    }
                ],
                "instruments": [
                    {"code": "BRK.B", "name": "伯克希尔 B", "market": "US", "access": "美股 ticker"}
                ],
            },
        ]
    }
    radar = build_market_radar(portfolio, radar_config)
    text = format_market_radar(radar)

    _assert_contains(text, "存储 / HBM")
    _assert_contains(text, "MU（美光科技，美股 ticker）")
    _assert_contains(text, "增厚原有风险")
    _assert_contains(text, "防守轮动")
    _assert_contains(text, "BRK.B（伯克希尔 B，美股 ticker）")
    _assert_contains(text, "分散候选")

    memory = next(item for item in radar["themes"] if item["theme_id"] == "memory_hbm")
    if memory["relation"] != "增厚原有风险":
        raise AssertionError("memory/HBM should overlap current AI/tech exposure")
    if memory["verification_status"] != "雷达观察，未核验":
        raise AssertionError("radar_only narrative should remain unverified")
    defensive = next(item for item in radar["themes"] if item["theme_id"] == "defensive_rotation")
    if defensive["relation"] != "分散候选":
        raise AssertionError("defensive rotation should be classified as diversification candidate")


def main():
    run_market_radar_test()
    print("Mock market radar test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
