#!/usr/bin/env python3
"""Anonymized portfolio x-ray review.

This module is offline and read-only. It can inspect tracked example data or a
user-provided local portfolio file, but it only renders anonymized holding refs.
"""

import json
import sys
from pathlib import Path

from common.portfolio_exposure import summarize_portfolio_exposure


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PORTFOLIO = ROOT / "data/examples/portfolio.example.json"


def _number(value, default=0.0):
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    return default


def _round(value):
    return round(value, 1)


def _round_fee(value):
    return round(value, 2)


def _holding_ref(index):
    return f"holding_{index + 1}"


def _overlap_key(holding):
    factor = holding.get("factor_profile") or {}
    return (
        str(holding.get("market") or "unknown"),
        str(factor.get("type") or "unknown"),
        str(factor.get("benchmark") or "unknown"),
    )


def _build_overlap_clusters(holdings, holding_values, invested):
    groups = {}
    for index, holding in enumerate(holdings):
        groups.setdefault(_overlap_key(holding), []).append(
            {
                "holding_ref": _holding_ref(index),
                "value": holding_values[index],
            }
        )

    clusters = []
    for key, members in sorted(groups.items()):
        if len(members) < 2:
            continue
        value = sum(member["value"] for member in members)
        clusters.append(
            {
                "type": "overlap cluster",
                "market": key[0],
                "factor_type": key[1],
                "benchmark": key[2],
                "holding_refs": [member["holding_ref"] for member in members],
                "invested_pct": _round(value / invested * 100) if invested > 0 else 0.0,
            }
        )
    return clusters


def _build_fee_review(holdings, holding_values):
    fee_weight = 0.0
    fee_value = 0.0
    missing_fee_refs = []

    for index, holding in enumerate(holdings):
        expense_ratio = holding.get("expense_ratio")
        if expense_ratio is None:
            missing_fee_refs.append(_holding_ref(index))
            continue
        fee = _number(expense_ratio, default=-1)
        if fee < 0:
            missing_fee_refs.append(_holding_ref(index))
            continue
        value = holding_values[index]
        fee_weight += value
        fee_value += value * fee

    weighted_expense_ratio = None
    if fee_weight > 0:
        weighted_expense_ratio = _round_fee(fee_value / fee_weight)

    return {
        "weighted_expense_ratio_pct": weighted_expense_ratio,
        "fee_coverage_count": len(holdings) - len(missing_fee_refs),
        "missing_fee_refs": missing_fee_refs,
    }


def build_portfolio_xray(portfolio):
    holdings = [item for item in portfolio.get("holdings", []) if isinstance(item, dict)]
    holding_values = [_number(item.get("cost_basis")) for item in holdings]
    invested = sum(holding_values)
    exposure = summarize_portfolio_exposure(portfolio)
    overlap_clusters = _build_overlap_clusters(holdings, holding_values, invested)
    fee_review = _build_fee_review(holdings, holding_values)

    warnings = list(exposure.get("warnings") or [])
    if fee_review["missing_fee_refs"]:
        warnings.append(
            {
                "type": "fee_data_missing",
                "holding_refs": fee_review["missing_fee_refs"],
            }
        )
    if overlap_clusters:
        warnings.append(
            {
                "type": "overlap_review_required",
                "cluster_count": len(overlap_clusters),
            }
        )

    return {
        "holding_count": len(holdings),
        "allocation": {
            "cash_pct": exposure["cash_pct"],
            "invested_pct": exposure["invested_pct"],
            "max_position_pct": exposure["max_position_pct"],
            "max_position_ref": exposure["max_position_ref"],
            "strategy_counts": exposure["strategy_counts"],
            "factor_counts": exposure["factor_counts"],
            "market_counts": exposure["market_counts"],
        },
        "overlap_clusters": overlap_clusters,
        "fee_review": fee_review,
        "warnings": warnings,
        "boundary": {
            "privacy": "anonymized holding refs only",
            "decision": "decision support only",
            "execution_allowed": False,
        },
    }


def _format_counts(counts):
    if not counts:
        return "none"
    return ", ".join(f"{key}={value}" for key, value in sorted(counts.items()))


def format_portfolio_xray(xray):
    allocation = xray["allocation"]
    fee_review = xray["fee_review"]
    lines = ["# Portfolio X-Ray", ""]
    lines.append("## Allocation")
    lines.append(f"- holding_count={xray['holding_count']}")
    lines.append(f"- cash_pct={allocation['cash_pct']}")
    lines.append(f"- invested_pct={allocation['invested_pct']}")
    lines.append(
        "- max_position="
        f"{allocation['max_position_ref']}:{allocation['max_position_pct']}"
    )
    lines.append("- strategy_counts: " + _format_counts(allocation["strategy_counts"]))
    lines.append("- factor_counts: " + _format_counts(allocation["factor_counts"]))
    lines.append("- market_counts: " + _format_counts(allocation["market_counts"]))
    lines.append("")

    lines.append("## Overlap Review")
    if xray["overlap_clusters"]:
        for cluster in xray["overlap_clusters"]:
            lines.append(
                "- overlap cluster: "
                f"market={cluster['market']} "
                f"factor={cluster['factor_type']} "
                f"benchmark={cluster['benchmark']} "
                f"holding_refs={','.join(cluster['holding_refs'])} "
                f"invested_pct={cluster['invested_pct']}"
            )
    else:
        lines.append("- overlap cluster: none")
    lines.append("")

    lines.append("## Fee Review")
    lines.append(
        "- weighted_expense_ratio_pct="
        + str(fee_review["weighted_expense_ratio_pct"])
    )
    lines.append("- fee_coverage_count=" + str(fee_review["fee_coverage_count"]))
    missing_fee_refs = ",".join(fee_review["missing_fee_refs"] or ["none"])
    lines.append("- missing_fee_refs=" + missing_fee_refs)
    lines.append("")

    lines.append("## Warnings")
    if xray["warnings"]:
        for warning in xray["warnings"]:
            lines.append("- " + warning["type"])
    else:
        lines.append("- none")
    lines.append("")

    lines.append("## Boundary")
    lines.append("- privacy: anonymized holding refs only")
    lines.append("- decision: decision support only")
    lines.append("- execution_allowed=false")
    return "\n".join(lines)


def _load_portfolio(path):
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def main(argv=None):
    argv = argv or sys.argv[1:]
    path = Path(argv[0]) if argv else DEFAULT_PORTFOLIO
    portfolio = _load_portfolio(path)
    print(format_portfolio_xray(build_portfolio_xray(portfolio)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
