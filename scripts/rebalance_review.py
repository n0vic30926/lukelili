#!/usr/bin/env python3
"""Anonymized target-allocation drift review."""

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PORTFOLIO = ROOT / "data/examples/portfolio.example.json"
DEFAULT_TOLERANCE_PCT = 5.0


def _number(value, default=0.0):
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    return default


def _round_pct(value):
    return round(value, 1)


def _holding_ref(index):
    return f"holding_{index + 1}"


def _target_pct(item):
    if not isinstance(item, dict) or "target_weight_pct" not in item:
        return None
    return _number(item.get("target_weight_pct"))


def _position_rows(portfolio):
    cash = portfolio.get("cash") if isinstance(portfolio.get("cash"), dict) else {}
    holdings = [item for item in portfolio.get("holdings", []) if isinstance(item, dict)]
    cash_amount = max(_number(cash.get("amount")), 0.0)
    holding_values = [max(_number(item.get("cost_basis")), 0.0) for item in holdings]
    total_value = cash_amount + sum(holding_values)
    rows = []
    missing_target_refs = []

    cash_target = _target_pct(cash)
    if cash_target is not None:
        current_pct = cash_amount / total_value * 100 if total_value > 0 else 0.0
        rows.append(
            {
                "position_ref": "cash",
                "current_pct": _round_pct(current_pct),
                "target_pct": _round_pct(cash_target),
                "drift_pct": _round_pct(current_pct - cash_target),
            }
        )

    for index, holding in enumerate(holdings):
        target = _target_pct(holding)
        holding_ref = _holding_ref(index)
        if target is None:
            missing_target_refs.append(holding_ref)
            continue
        current_pct = holding_values[index] / total_value * 100 if total_value > 0 else 0.0
        rows.append(
            {
                "position_ref": holding_ref,
                "current_pct": _round_pct(current_pct),
                "target_pct": _round_pct(target),
                "drift_pct": _round_pct(current_pct - target),
            }
        )

    return rows, missing_target_refs


def _classify_rows(rows, tolerance_pct):
    for row in rows:
        drift = row["drift_pct"]
        if drift > tolerance_pct:
            row["status"] = "overweight"
        elif drift < -tolerance_pct:
            row["status"] = "underweight"
        else:
            row["status"] = "in_tolerance"
    return rows


def _decision_signals(rows, tolerance_pct):
    signals = []
    for row in rows:
        if row["status"] not in {"overweight", "underweight"}:
            continue
        signals.append(
            {
                "position_ref": row["position_ref"],
                "signal": "rebalance_review",
                "status": row["status"],
                "drift_pct": row["drift_pct"],
                "tolerance_pct": tolerance_pct,
                "requires_user_confirmation": True,
            }
        )
    return signals


def build_rebalance_review(portfolio):
    risk_rules = portfolio.get("risk_rules") if isinstance(portfolio.get("risk_rules"), dict) else {}
    tolerance_pct = _number(
        risk_rules.get("rebalance_tolerance_pct"),
        default=DEFAULT_TOLERANCE_PCT,
    )
    rows, missing_target_refs = _position_rows(portfolio)
    rows = _classify_rows(rows, tolerance_pct)
    decision_signals = _decision_signals(rows, tolerance_pct)
    warnings = []
    if missing_target_refs:
        warnings.append(
            {
                "type": "target_weight_missing",
                "position_refs": missing_target_refs,
            }
        )

    return {
        "reviewed_position_count": len(rows),
        "tolerance_pct": _round_pct(tolerance_pct),
        "max_abs_drift_pct": _round_pct(
            max([abs(row["drift_pct"]) for row in rows] or [0.0])
        ),
        "overweight_count": sum(1 for row in rows if row["status"] == "overweight"),
        "underweight_count": sum(1 for row in rows if row["status"] == "underweight"),
        "in_tolerance_count": sum(1 for row in rows if row["status"] == "in_tolerance"),
        "missing_target_refs": missing_target_refs,
        "positions": rows,
        "decision_signals": decision_signals,
        "warnings": warnings,
        "boundary": {
            "signal": "model judgment and decision support only",
            "execution_allowed": False,
        },
    }


def format_rebalance_review(review):
    lines = ["# Rebalance Review", ""]
    lines.append("## Summary")
    for key in [
        "reviewed_position_count",
        "tolerance_pct",
        "max_abs_drift_pct",
        "overweight_count",
        "underweight_count",
        "in_tolerance_count",
    ]:
        lines.append("- " + key + "=" + str(review.get(key, 0)))
    lines.append(
        "- missing_target_refs="
        + ",".join(review.get("missing_target_refs") or ["none"])
    )
    lines.append("")

    lines.append("## Positions")
    if review.get("positions"):
        for row in review["positions"]:
            lines.append(
                "- "
                f"position_ref={row['position_ref']} "
                f"current_pct={row['current_pct']} "
                f"target_pct={row['target_pct']} "
                f"drift_pct={row['drift_pct']} "
                f"status={row['status']}"
            )
    else:
        lines.append("- none")
    lines.append("")

    lines.append("## Decision Signals")
    if review.get("decision_signals"):
        for signal in review["decision_signals"]:
            lines.append(
                "- "
                f"position_ref={signal['position_ref']} "
                f"signal={signal['signal']} "
                f"status={signal['status']} "
                f"drift_pct={signal['drift_pct']} "
                "requires_user_confirmation="
                + str(signal["requires_user_confirmation"]).lower()
            )
    else:
        lines.append("- none")
    lines.append("")

    lines.append("## Warnings")
    if review.get("warnings"):
        for warning in review["warnings"]:
            lines.append("- " + str(warning.get("type") or "unknown"))
    else:
        lines.append("- none")
    lines.append("")

    lines.append("## Boundary")
    lines.append("- signal: model judgment and decision support only")
    lines.append("- execution_allowed=false")
    return "\n".join(lines)


def _load_portfolio(path):
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def main(argv=None):
    argv = argv or sys.argv[1:]
    path = Path(argv[0]) if argv else DEFAULT_PORTFOLIO
    print(format_rebalance_review(build_rebalance_review(_load_portfolio(path))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
