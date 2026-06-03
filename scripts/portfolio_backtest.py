#!/usr/bin/env python3
"""Anonymized portfolio historical return and drawdown review."""

import json
import math
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


def _round_pct(value):
    return round(value, 1)


def _history_by_date(holding):
    history = {}
    for item in holding.get("return_history") or []:
        if not isinstance(item, dict):
            continue
        date_value = str(item.get("date") or "").strip()
        if not date_value:
            continue
        history[date_value] = _number(item.get("return_pct"))
    return history


def _portfolio_daily_returns(holdings):
    histories = []
    missing_refs = []
    total_weight = 0.0
    for index, holding in enumerate(holdings):
        weight = _number(holding.get("cost_basis"))
        history = _history_by_date(holding)
        if history and weight > 0:
            histories.append(
                {
                    "holding_ref": _holding_ref(index),
                    "weight": weight,
                    "history": history,
                }
            )
            total_weight += weight
        else:
            missing_refs.append(_holding_ref(index))

    dates = sorted({date for item in histories for date in item["history"]})
    daily_returns = []
    for date_value in dates:
        available = [
            item for item in histories if date_value in item["history"]
        ]
        available_weight = sum(item["weight"] for item in available)
        if available_weight <= 0:
            continue
        weighted_return = sum(
            item["history"][date_value] * item["weight"] / available_weight
            for item in available
        )
        daily_returns.append(
            {
                "date": date_value,
                "portfolio_return_pct": _round_pct(weighted_return),
                "coverage_pct": _round_pct(available_weight / total_weight * 100)
                if total_weight > 0
                else 0.0,
            }
        )
    return daily_returns, histories, missing_refs


def _period_return(daily_returns):
    value = 1.0
    for item in daily_returns:
        value *= 1 + item["portfolio_return_pct"] / 100
    return _round_pct((value - 1) * 100)


def _max_drawdown(daily_returns):
    value = 1.0
    peak = 1.0
    max_drawdown = 0.0
    for item in daily_returns:
        value *= 1 + item["portfolio_return_pct"] / 100
        peak = max(peak, value)
        if peak > 0:
            max_drawdown = min(max_drawdown, (value / peak - 1) * 100)
    return _round_pct(max_drawdown)


def _annualized_volatility(daily_returns):
    if not daily_returns:
        return 0.0
    values = [item["portfolio_return_pct"] for item in daily_returns]
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    return _round_pct(math.sqrt(variance) * math.sqrt(252))


def build_portfolio_backtest(portfolio):
    holdings = [item for item in portfolio.get("holdings", []) if isinstance(item, dict)]
    daily_returns, covered, missing_refs = _portfolio_daily_returns(holdings)
    warnings = []
    if missing_refs:
        warnings.append(
            {
                "type": "historical_data_missing",
                "holding_refs": missing_refs,
            }
        )
    if any(item["coverage_pct"] < 100 for item in daily_returns):
        warnings.append({"type": "partial_history_coverage"})

    return {
        "holding_count": len(holdings),
        "covered_holding_count": len(covered),
        "missing_history_refs": missing_refs,
        "observation_count": len(daily_returns),
        "period_return_pct": _period_return(daily_returns),
        "max_drawdown_pct": _max_drawdown(daily_returns),
        "annualized_volatility_pct": _annualized_volatility(daily_returns),
        "daily_returns": daily_returns,
        "warnings": warnings,
        "boundary": {
            "history": "historical local return inputs only",
            "decision": "decision support only",
            "execution_allowed": False,
        },
    }


def format_portfolio_backtest(backtest):
    lines = ["# Portfolio Backtest", ""]
    lines.append("## Summary")
    for key in [
        "holding_count",
        "covered_holding_count",
        "observation_count",
        "period_return_pct",
        "max_drawdown_pct",
        "annualized_volatility_pct",
    ]:
        lines.append("- " + key + "=" + str(backtest.get(key, 0)))
    lines.append(
        "- missing_history_refs="
        + ",".join(backtest.get("missing_history_refs") or ["none"])
    )
    lines.append("")

    lines.append("## Daily Returns")
    if backtest.get("daily_returns"):
        for item in backtest["daily_returns"]:
            lines.append(
                "- "
                f"date={item['date']} "
                f"portfolio_return_pct={item['portfolio_return_pct']} "
                f"coverage_pct={item['coverage_pct']}"
            )
    else:
        lines.append("- none")
    lines.append("")

    lines.append("## Warnings")
    if backtest.get("warnings"):
        for warning in backtest["warnings"]:
            lines.append("- " + str(warning.get("type") or "unknown"))
    else:
        lines.append("- none")
    lines.append("")

    lines.append("## Boundary")
    lines.append("- history: historical local return inputs only")
    lines.append("- decision: decision support only")
    lines.append("- execution_allowed=false")
    return "\n".join(lines)


def _load_portfolio(path):
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def main(argv=None):
    argv = argv or sys.argv[1:]
    path = Path(argv[0]) if argv else DEFAULT_PORTFOLIO
    print(format_portfolio_backtest(build_portfolio_backtest(_load_portfolio(path))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
