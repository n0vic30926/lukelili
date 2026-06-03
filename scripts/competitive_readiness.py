#!/usr/bin/env python3
"""Offline competitive benchmark readiness checks."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BENCHMARK_PATH = ROOT / "docs/COMPETITIVE_BENCHMARK.md"


def _entry(requirement, ok, evidence):
    return {
        "requirement": requirement,
        "status": "pass" if ok else "fail",
        "evidence": evidence,
    }


def _read_benchmark():
    if not BENCHMARK_PATH.exists():
        return ""
    return BENCHMARK_PATH.read_text(encoding="utf-8")


def build_competitive_readiness():
    text = _read_benchmark()
    lower_text = text.lower()
    checks = []

    checks.append(
        _entry(
            "competitive benchmark document exists",
            bool(text),
            "docs/COMPETITIVE_BENCHMARK.md",
        )
    )

    required_sections = [
        "Competitor Capability Matrix",
        "Local Competitive Advantages",
        "Iteration Gate",
    ]
    missing_sections = [section for section in required_sections if section not in text]
    checks.append(
        _entry(
            "benchmark defines matrix, advantages, and iteration gate",
            not missing_sections,
            "missing=" + ",".join(missing_sections or ["none"]),
        )
    )

    competitors = [
        "Betterment",
        "Wealthfront",
        "Schwab Intelligent Portfolios",
        "Vanguard Digital Advisor",
        "Empower",
        "Morningstar",
        "Portfolio Visualizer",
        "Koyfin",
        "Magnifi",
        "FinChat",
        "Seeking Alpha",
        "Composer",
    ]
    missing_competitors = [name for name in competitors if name not in text]
    checks.append(
        _entry(
            "benchmark covers representative competitor set",
            not missing_competitors,
            "missing=" + ",".join(missing_competitors or ["none"]),
        )
    )

    capabilities = [
        "automated rebalancing",
        "tax-loss harvesting",
        "portfolio tracking",
        "portfolio x-ray",
        "backtesting",
        "factor analysis",
        "AI research",
        "explicit user confirmation",
        "local-first privacy",
        "evidence ranking",
        "data freshness",
    ]
    missing_capabilities = [
        capability for capability in capabilities if capability.lower() not in lower_text
    ]
    checks.append(
        _entry(
            "benchmark maps competitor capabilities to local differentiators",
            not missing_capabilities,
            "missing=" + ",".join(missing_capabilities or ["none"]),
        )
    )

    checks.append(
        _entry(
            "benchmark preserves investment-agent boundaries",
            "decision support only" in lower_text
            and "no broker execution" in lower_text
            and "execution_allowed=false" in lower_text,
            "decision support only; no broker execution; execution_allowed=false",
        )
    )

    return checks


def summarize_competitive_readiness(entries):
    counts = {"pass": 0, "fail": 0}
    for entry in entries:
        counts[entry["status"]] = counts.get(entry["status"], 0) + 1
    return counts


def format_competitive_readiness(entries):
    counts = summarize_competitive_readiness(entries)
    lines = ["# Competitive Readiness", ""]
    lines.append(f"- Summary: pass={counts.get('pass', 0)} fail={counts.get('fail', 0)}")
    lines.append("- Source: docs/COMPETITIVE_BENCHMARK.md")
    lines.append(
        "- Required Sections: Competitor Capability Matrix; "
        "Local Competitive Advantages; Iteration Gate"
    )
    lines.append("- Representative Benchmarks: Betterment; Portfolio Visualizer")
    lines.append(
        "- Local Boundaries: local-first privacy; explicit user confirmation; decision support only"
    )
    lines.append("")
    lines.append("| Status | Requirement | Evidence |")
    lines.append("|---|---|---|")
    for entry in entries:
        lines.append(f"| {entry['status']} | {entry['requirement']} | {entry['evidence']} |")
    return "\n".join(lines)


def main():
    entries = build_competitive_readiness()
    print(format_competitive_readiness(entries))
    return 0 if summarize_competitive_readiness(entries).get("fail", 0) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
