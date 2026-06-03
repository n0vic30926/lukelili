#!/usr/bin/env python3
"""Hypothetical portfolio scenario review.

Scenarios are explicit assumptions and model projections, not facts. The output
is anonymized, offline, read-only, and decision-support only.
"""

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PORTFOLIO = ROOT / "data/examples/portfolio.example.json"
DEFAULT_SCENARIOS = ROOT / "data/examples/scenario_assumptions.example.json"


def _number(value, default=0.0):
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    return default


def _pct(numerator, denominator):
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator * 100, 1)


def _holding_ref(index):
    return f"holding_{index + 1}"


def _holding_dimensions(holding):
    factor = holding.get("factor_profile") or {}
    return {
        "market": str(holding.get("market") or ""),
        "factor_type": str(factor.get("type") or ""),
        "benchmark": str(factor.get("benchmark") or ""),
        "strategy_type": str(holding.get("strategy_type") or ""),
    }


def _matches(holding, match):
    if not isinstance(match, dict) or not match:
        return False
    dimensions = _holding_dimensions(holding)
    for key, expected in match.items():
        if str(dimensions.get(key) or "") != str(expected):
            return False
    return True


def _scenario_shock_for_holding(holding, shocks):
    matched = []
    for shock in shocks:
        if not isinstance(shock, dict):
            continue
        if _matches(holding, shock.get("match")):
            matched.append(_number(shock.get("shock_pct")))
    if not matched:
        return 0.0
    return round(sum(matched), 1)


def _build_holding_impacts(holdings, shocks):
    impacts = []
    for index, holding in enumerate(holdings):
        value = _number(holding.get("cost_basis"))
        shock_pct = _scenario_shock_for_holding(holding, shocks)
        impact_amount = round(value * shock_pct / 100, 2)
        impacts.append(
            {
                "holding_ref": _holding_ref(index),
                "shock_pct": shock_pct,
                "impact_amount": impact_amount,
            }
        )
    return impacts


def _build_risk_flags(portfolio, portfolio_impact_pct):
    flags = []
    daily_loss_limit = _number((portfolio.get("risk_rules") or {}).get("daily_loss_pct"))
    if daily_loss_limit > 0 and portfolio_impact_pct < -daily_loss_limit:
        flags.append(
            {
                "type": "scenario_loss_exceeds_daily_loss_rule",
                "impact_pct": portfolio_impact_pct,
                "limit_pct": round(daily_loss_limit, 1),
            }
        )
    return flags


def _build_decision_signals(risk_flags, portfolio_impact_pct):
    if any(flag["type"] == "scenario_loss_exceeds_daily_loss_rule" for flag in risk_flags):
        return [
            {
                "signal": "risk_reduction_review",
                "reason": "scenario loss exceeds configured daily loss rule",
                "requires_user_confirmation": True,
            }
        ]
    if portfolio_impact_pct > 0:
        return [
            {
                "signal": "hold_or_add_review",
                "reason": "scenario impact is positive under explicit assumptions",
                "requires_user_confirmation": True,
            }
        ]
    return [
        {
            "signal": "hold_review",
            "reason": "scenario impact stays within configured hard-loss rule",
            "requires_user_confirmation": True,
        }
    ]


def build_scenario_review(portfolio, scenarios):
    holdings = [item for item in portfolio.get("holdings", []) if isinstance(item, dict)]
    invested = sum(_number(item.get("cost_basis")) for item in holdings)
    cash = _number((portfolio.get("cash") or {}).get("amount"))
    total_capital = invested + cash

    scenario_results = []
    for scenario in scenarios:
        shocks = scenario.get("shocks") or []
        holding_impacts = _build_holding_impacts(holdings, shocks)
        total_impact = round(sum(item["impact_amount"] for item in holding_impacts), 2)
        portfolio_impact_pct = _pct(total_impact, total_capital)
        risk_flags = _build_risk_flags(portfolio, portfolio_impact_pct)
        scenario_results.append(
            {
                "name": str(scenario.get("name") or "unnamed_scenario"),
                "description": str(scenario.get("description") or ""),
                "portfolio_impact_pct": portfolio_impact_pct,
                "impact_amount": total_impact,
                "holding_impacts": holding_impacts,
                "risk_flags": risk_flags,
                "decision_signals": _build_decision_signals(risk_flags, portfolio_impact_pct),
            }
        )

    return {
        "scenario_count": len(scenario_results),
        "capital_base": {
            "cash_pct": _pct(cash, total_capital),
            "invested_pct": _pct(invested, total_capital),
        },
        "scenarios": scenario_results,
        "boundary": {
            "projection": "model projection, not a fact",
            "decision": "decision support only",
            "requires_user_confirmation": True,
            "execution_allowed": False,
            "privacy": "anonymized holding refs only",
        },
    }


def format_scenario_review(review):
    lines = ["# Portfolio Scenario Review", ""]
    lines.append("## Capital Base")
    lines.append(f"- cash_pct={review['capital_base']['cash_pct']}")
    lines.append(f"- invested_pct={review['capital_base']['invested_pct']}")
    lines.append("")

    lines.append("## Scenarios")
    for scenario in review["scenarios"]:
        lines.append(f"- scenario={scenario['name']}")
        lines.append(f"  portfolio_impact_pct={scenario['portfolio_impact_pct']}")
        lines.append(f"  impact_amount={scenario['impact_amount']}")
        for impact in scenario["holding_impacts"]:
            lines.append(
                "  holding_impact="
                f"{impact['holding_ref']}:shock_pct={impact['shock_pct']}:"
                f"impact_amount={impact['impact_amount']}"
            )
        if scenario["risk_flags"]:
            for flag in scenario["risk_flags"]:
                lines.append(
                    "  risk_flag="
                    f"{flag['type']}:impact_pct={flag['impact_pct']}:"
                    f"limit_pct={flag['limit_pct']}"
                )
        else:
            lines.append("  risk_flag=none")
        for signal in scenario["decision_signals"]:
            lines.append(
                "  decision_signal="
                f"{signal['signal']}:requires_user_confirmation="
                f"{str(signal['requires_user_confirmation']).lower()}"
            )
    lines.append("")

    lines.append("## Boundary")
    lines.append("- projection: model projection, not a fact")
    lines.append("- decision: decision support only")
    lines.append("- requires_user_confirmation=true")
    lines.append("- execution_allowed=false")
    lines.append("- privacy: anonymized holding refs only")
    return "\n".join(lines)


def _load_json(path):
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def main(argv=None):
    argv = argv or sys.argv[1:]
    portfolio_path = Path(argv[0]) if argv else DEFAULT_PORTFOLIO
    scenarios_path = Path(argv[1]) if len(argv) > 1 else DEFAULT_SCENARIOS
    review = build_scenario_review(_load_json(portfolio_path), _load_json(scenarios_path))
    print(format_scenario_review(review))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
