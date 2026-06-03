#!/usr/bin/env python3
"""Anonymized direct and indirect portfolio stock intersection."""

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PORTFOLIO = ROOT / "data/examples/portfolio.example.json"


def _number(value, default=0.0):
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    return default


def _holding_ref(index):
    return f"holding_{index + 1}"


def _underlying_ref(index):
    return f"underlying_{index + 1}"


def _is_direct_security(holding):
    item_type = str(holding.get("type") or holding.get("asset_type") or "").lower()
    market = str(holding.get("market") or "").lower()
    if any(token in item_type for token in ["stock", "equity", "share"]):
        return True
    return market in {"a_share", "us_stock", "hk_stock"}


def _clean_code(code):
    return str(code or "").lower().replace("sh", "").replace("sz", "").strip()


def _underlying_key(item):
    code = str(item.get("code") or item.get("symbol") or "").strip().lower()
    if code:
        return "code:" + code
    name = str(item.get("name") or "").strip().lower()
    if name:
        return "name:" + name
    return ""


def _add_contribution(rows, key, holding_ref, amount):
    if not key or amount <= 0:
        return
    row = rows.setdefault(
        key,
        {
            "amount": 0.0,
            "source_holding_refs": [],
        },
    )
    row["amount"] += amount
    if holding_ref not in row["source_holding_refs"]:
        row["source_holding_refs"].append(holding_ref)


def _external_underlyings_for_holding(holding, external_underlying_holdings_by_code):
    if not external_underlying_holdings_by_code:
        return []
    code = _clean_code(holding.get("code") or holding.get("symbol"))
    if not code:
        return []
    return external_underlying_holdings_by_code.get(code) or []


def _build_rows(holdings, external_underlying_holdings_by_code=None):
    rows = {}
    covered_holding_refs = set()
    missing_underlying_refs = []

    for index, holding in enumerate(holdings):
        holding_ref = _holding_ref(index)
        value = _number(holding.get("cost_basis"))
        underlying_holdings = holding.get("underlying_holdings") or []
        if not underlying_holdings:
            underlying_holdings = _external_underlyings_for_holding(
                holding,
                external_underlying_holdings_by_code,
            )
        if isinstance(underlying_holdings, list) and underlying_holdings:
            covered_holding_refs.add(holding_ref)
            for item in underlying_holdings:
                if not isinstance(item, dict):
                    continue
                key = _underlying_key(item)
                weight_pct = _number(item.get("weight_pct"))
                _add_contribution(rows, key, holding_ref, value * weight_pct / 100)
            continue
        if _is_direct_security(holding):
            covered_holding_refs.add(holding_ref)
            _add_contribution(rows, _underlying_key(holding), holding_ref, value)
        else:
            missing_underlying_refs.append(holding_ref)

    return rows, covered_holding_refs, missing_underlying_refs


def build_stock_intersection(portfolio, external_underlying_holdings_by_code=None):
    holdings = [item for item in portfolio.get("holdings", []) if isinstance(item, dict)]
    invested = sum(_number(item.get("cost_basis")) for item in holdings)
    cash = _number((portfolio.get("cash") or {}).get("amount"))
    total_capital = invested + cash
    rows, covered_holding_refs, missing_underlying_refs = _build_rows(
        holdings,
        external_underlying_holdings_by_code=external_underlying_holdings_by_code,
    )

    sorted_items = sorted(
        rows.items(),
        key=lambda item: (-item[1]["amount"], item[0]),
    )
    top_underlyings = []
    for index, (_, row) in enumerate(sorted_items):
        top_underlyings.append(
            {
                "underlying_ref": _underlying_ref(index),
                "portfolio_pct": round(row["amount"] / total_capital * 100, 1)
                if total_capital > 0
                else 0.0,
                "source_holding_refs": sorted(row["source_holding_refs"]),
            }
        )

    warnings = []
    max_underlying_pct = _number(
        (portfolio.get("risk_rules") or {}).get("max_underlying_position_pct")
    )
    if max_underlying_pct > 0:
        for item in top_underlyings:
            if item["portfolio_pct"] > max_underlying_pct:
                warnings.append(
                    {
                        "type": "underlying_concentration_exceeds_rule",
                        "underlying_ref": item["underlying_ref"],
                        "actual_pct": item["portfolio_pct"],
                        "limit_pct": round(max_underlying_pct, 1),
                    }
                )
    overlap_count = sum(1 for item in top_underlyings if len(item["source_holding_refs"]) > 1)
    if overlap_count:
        warnings.append(
            {
                "type": "underlying_overlap_review_required",
                "overlap_count": overlap_count,
            }
        )
    if missing_underlying_refs:
        warnings.append(
            {
                "type": "underlying_data_missing",
                "holding_refs": missing_underlying_refs,
            }
        )

    return {
        "holding_count": len(holdings),
        "covered_holding_count": len(covered_holding_refs),
        "missing_underlying_refs": missing_underlying_refs,
        "underlying_count": len(top_underlyings),
        "top_underlyings": top_underlyings,
        "warnings": warnings,
        "boundary": {
            "privacy": "anonymized holding and underlying refs only",
            "decision": "decision support only",
            "execution_allowed": False,
        },
    }


def format_stock_intersection(matrix):
    lines = ["# Portfolio Stock Intersection", ""]
    lines.append("## Coverage")
    lines.append("- holding_count=" + str(matrix.get("holding_count", 0)))
    lines.append("- covered_holding_count=" + str(matrix.get("covered_holding_count", 0)))
    lines.append("- underlying_count=" + str(matrix.get("underlying_count", 0)))
    missing_refs = ",".join(matrix.get("missing_underlying_refs") or ["none"])
    lines.append("- missing_underlying_refs=" + missing_refs)
    lines.append("")

    lines.append("## Top Underlyings")
    if matrix.get("top_underlyings"):
        for item in matrix["top_underlyings"]:
            lines.append(
                "- "
                f"underlying_ref={item['underlying_ref']} "
                f"portfolio_pct={item['portfolio_pct']} "
                f"source_holding_refs={','.join(item['source_holding_refs'])}"
            )
    else:
        lines.append("- none")
    lines.append("")

    lines.append("## Warnings")
    if matrix.get("warnings"):
        for warning in matrix["warnings"]:
            lines.append("- " + str(warning.get("type") or "unknown"))
    else:
        lines.append("- none")
    lines.append("")

    lines.append("## Boundary")
    lines.append("- privacy: anonymized holding and underlying refs only")
    lines.append("- decision: decision support only")
    lines.append("- execution_allowed=false")
    return "\n".join(lines)


def _load_portfolio(path):
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def main(argv=None):
    argv = argv or sys.argv[1:]
    path = Path(argv[0]) if argv else DEFAULT_PORTFOLIO
    print(format_stock_intersection(build_stock_intersection(_load_portfolio(path))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
