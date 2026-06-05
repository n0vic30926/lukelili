#!/usr/bin/env python3
"""Offline tests for narrative evidence ingestion and thesis ledger records."""

from pathlib import Path
from tempfile import TemporaryDirectory

from market_radar import build_market_radar
from narrative_evidence import (
    apply_evidence_to_radar_config,
    build_narrative_evidence_review,
    format_narrative_evidence_review,
    load_thesis_ledger,
    save_thesis_ledger,
)


def _assert_contains(text, expected):
    if expected not in text:
        raise AssertionError(f"missing expected text: {expected}")


def run_narrative_evidence_test():
    radar_config = {
        "themes": [
            {
                "theme_id": "memory_hbm",
                "name": "存储 / HBM",
                "thesis": "AI memory cycle",
                "exposure_tags": ["ai", "semiconductor", "memory"],
                "narratives": [
                    {
                        "claim": "HBM remains a radar theme",
                        "evidence_level": "radar_only",
                    }
                ],
                "instruments": [
                    {"code": "MU", "name": "美光科技", "market": "US", "access": "美股 ticker"}
                ],
            },
            {
                "theme_id": "commercial_space",
                "name": "商业航天",
                "thesis": "commercial space launch and satellite theme",
                "exposure_tags": ["space"],
                "narratives": [
                    {
                        "claim": "Space remains a radar theme",
                        "evidence_level": "radar_only",
                    }
                ],
                "instruments": [
                    {"code": "RKLB", "name": "Rocket Lab", "market": "US", "access": "美股 ticker"}
                ],
            },
        ]
    }
    evidence_items = [
        {
            "title": "MU earnings call says HBM demand is strong",
            "content": "Micron discussed AI server HBM demand and memory pricing.",
            "url": "https://investors.example.com/mu-hbm",
            "source_type": "earnings",
        },
        {
            "title": "Space IPO rumor",
            "content": "A social account says a space company will IPO next month.",
            "url": "https://social.example.com/space-rumor",
            "source_type": "rumor",
        },
    ]
    review = build_narrative_evidence_review(evidence_items, radar_config)
    text = format_narrative_evidence_review(review)

    _assert_contains(text, "公司披露或财报证据")
    _assert_contains(text, "存储 / HBM")
    _assert_contains(text, "MU（美光科技，美股 ticker）")
    _assert_contains(text, "只记录为传闻或不可验证信息")

    updated = apply_evidence_to_radar_config(radar_config, review)
    portfolio = {
        "holdings": [
            {
                "name": "Example Nasdaq QDII",
                "market": "US_QDII",
                "cost_basis": 10000,
                "factor_profile": {"type": "qdii_us_equity", "benchmark": "NASDAQ100"},
            }
        ]
    }
    radar = build_market_radar(portfolio, updated)
    memory = radar["themes"][0]
    if memory["verification_status"] != "公司披露或财报证据":
        raise AssertionError(f"Expected evidence to upgrade theme confidence: {memory}")

    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "thesis_ledger.jsonl"
        save_thesis_ledger(review, record_path=path)
        records = load_thesis_ledger(path)
        if records[0]["matched_theme_ids"] != ["commercial_space", "memory_hbm"]:
            raise AssertionError(f"Unexpected ledger theme ids: {records}")


def main():
    run_narrative_evidence_test()
    print("Mock narrative evidence test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
