"""Anonymized local portfolio exposure summaries."""


def _number(value, default=0):
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    return default


def _pct(numerator, denominator):
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator * 100, 1)


def _count_by(values):
    counts = {}
    for value in values:
        key = str(value or "unknown")
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def summarize_portfolio_exposure(portfolio):
    holdings = [item for item in portfolio.get("holdings", []) if isinstance(item, dict)]
    cash = _number((portfolio.get("cash") or {}).get("amount"))
    holding_values = [_number(item.get("cost_basis")) for item in holdings]
    invested = sum(holding_values)
    total_capital = invested + cash

    positions = []
    for index, value in enumerate(holding_values):
        positions.append(
            {
                "holding_ref": f"holding_{index + 1}",
                "position_pct": _pct(value, total_capital),
                "invested_pct": _pct(value, invested),
            }
        )

    max_position = max(positions, key=lambda item: item["position_pct"], default=None)
    max_position_pct = max_position["position_pct"] if max_position else 0.0
    max_position_ref = max_position["holding_ref"] if max_position else ""

    warnings = []
    limit = _number((portfolio.get("risk_rules") or {}).get("max_single_position_pct"))
    if limit > 0 and max_position_pct > limit:
        warnings.append(
            {
                "type": "single_position_exceeds_rule",
                "holding_ref": max_position_ref,
                "actual_pct": max_position_pct,
                "limit_pct": round(limit, 1),
            }
        )

    return {
        "holding_count": len(holdings),
        "cash_pct": _pct(cash, total_capital),
        "invested_pct": _pct(invested, total_capital),
        "max_position_pct": max_position_pct,
        "max_position_ref": max_position_ref,
        "strategy_counts": _count_by(item.get("strategy_type") for item in holdings),
        "factor_counts": _count_by((item.get("factor_profile") or {}).get("type") for item in holdings),
        "market_counts": _count_by(item.get("market") for item in holdings),
        "positions": positions,
        "warnings": warnings,
    }
