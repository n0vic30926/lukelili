#!/usr/bin/env python3
"""Review real-portfolio completion gaps and emit a private overlay template."""

import argparse
import json
from pathlib import Path

from common.config_loader import (
    get_portfolio_overlay_path,
    load_portfolio,
    load_settings,
)


PENDING_STRATEGIES = {"", "pending_user_declaration", "user_defined_pending", "unknown"}


def _number(value, default=0.0):
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    return default


def _holding_ref(index):
    return f"holding_{index + 1}"


def _gap(severity, ref, field, issue, action):
    return {
        "severity": severity,
        "ref": ref,
        "field": field,
        "issue": issue,
        "action": action,
    }


def build_gap_review(portfolio):
    holdings = [item for item in portfolio.get("holdings", []) if isinstance(item, dict)]
    cash = portfolio.get("cash") if isinstance(portfolio.get("cash"), dict) else {}
    risk_rules = portfolio.get("risk_rules") if isinstance(portfolio.get("risk_rules"), dict) else {}
    data_status = portfolio.get("data_status") if isinstance(portfolio.get("data_status"), dict) else {}
    invested = sum(_number(item.get("cost_basis")) for item in holdings)
    cash_amount = _number(cash.get("amount"))
    total = invested + max(cash_amount, 0.0)
    gaps = []

    if cash.get("status") == "not_provided":
        gaps.append(
            _gap(
                "high",
                "cash",
                "amount",
                "cash balance is not provided",
                "Set cash.amount in the private overlay if cash should affect allocation and rebalance advice.",
            )
        )
    if "target_weight_pct" not in cash:
        gaps.append(
            _gap(
                "high",
                "cash",
                "target_weight_pct",
                "cash target weight is missing",
                "Set cash.target_weight_pct so rebalance review can include cash.",
            )
        )

    if str(risk_rules.get("status") or "").startswith("draft"):
        gaps.append(
            _gap(
                "high",
                "risk_rules",
                "status",
                "risk rules are draft defaults",
                "Confirm risk_rules in the private overlay before treating reduce-risk signals as your mandate.",
            )
        )

    target_sum = _number(cash.get("target_weight_pct"))
    for index, holding in enumerate(holdings):
        ref = _holding_ref(index)
        code = str(holding.get("code") or "")
        current_pct = _number(holding.get("cost_basis")) / total * 100 if total > 0 else 0.0
        strategy = str(holding.get("strategy_type") or "")
        if strategy in PENDING_STRATEGIES:
            gaps.append(
                _gap(
                    "critical",
                    ref,
                    f"holdings_by_code.{code}.strategy_type",
                    "strategy_type is pending user declaration",
                    "Choose one of dca, trial, short_term, or watch in the private overlay.",
                )
            )
        if "target_weight_pct" not in holding:
            gaps.append(
                _gap(
                    "high",
                    ref,
                    f"holdings_by_code.{code}.target_weight_pct",
                    f"target weight is missing; current known allocation is {current_pct:.1f}%",
                    "Set target_weight_pct so rebalance review can produce drift signals.",
                )
            )
        else:
            target_sum += _number(holding.get("target_weight_pct"))
        if "expense_ratio" not in holding:
            gaps.append(
                _gap(
                    "medium",
                    ref,
                    f"holdings_by_code.{code}.expense_ratio",
                    "expense ratio is missing",
                    "Set expense_ratio to improve fee review.",
                )
            )
        if not holding.get("underlying_holdings"):
            gaps.append(
                _gap(
                    "medium",
                    ref,
                    f"holdings_by_code.{code}.underlying_holdings",
                    "underlying holdings are missing",
                    "Add top holdings or an ETF/fund proxy to improve concentration review.",
                )
            )
        if not holding.get("return_history"):
            gaps.append(
                _gap(
                    "low",
                    ref,
                    f"holdings_by_code.{code}.return_history",
                    "local return history is missing",
                    "Add return_history only if you want local backtest metrics independent of AkShare.",
                )
            )
        for note in holding.get("pending_buy_notes") or []:
            gaps.append(
                _gap(
                    "critical",
                    ref,
                    f"append_buy_records_by_code.{code}",
                    str(note.get("note") or "pending buy note lacks dated records"),
                    "Append concrete buy records with date, amount, and status=pending or confirmed NAV/shares.",
                )
            )

    if target_sum and abs(target_sum - 100) > 0.01:
        gaps.append(
            _gap(
                "high",
                "portfolio",
                "target_weight_pct",
                f"configured target weights sum to {target_sum:.1f}%, not 100%",
                "Adjust cash and holding target weights to sum to 100.",
            )
        )

    severity_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    gaps.sort(key=lambda item: (severity_rank.get(item["severity"], 9), item["ref"], item["field"]))
    return {
        "mode": "portfolio_completion_review",
        "holding_count": len(holdings),
        "known_invested_amount": round(invested, 2),
        "known_cash_amount": round(cash_amount, 2),
        "overlay_applied": bool(data_status.get("overlay_applied")),
        "overlay_mode": data_status.get("overlay_mode"),
        "gap_count": len(gaps),
        "gaps": gaps,
    }


def build_overlay_template(portfolio):
    holdings = [item for item in portfolio.get("holdings", []) if isinstance(item, dict)]
    return {
        "enabled": False,
        "cash": {
            "amount": None,
            "target_weight_pct": None,
        },
        "risk_rules": {
            "status": None,
            "single_loss_pct": None,
            "daily_loss_pct": None,
            "max_single_position_pct": None,
            "max_underlying_position_pct": None,
            "rebalance_tolerance_pct": None,
        },
        "holdings_by_code": {
            str(holding.get("code") or ""): {
                "strategy_type": None,
                "target_weight_pct": None,
                "expense_ratio": None,
                "proxy_etf": None,
            }
            for holding in holdings
        },
        "append_buy_records_by_code": {
            str(holding.get("code") or ""): [
                {
                    "date": "YYYY-MM-DD",
                    "amount": 1500,
                    "status": "pending"
                }
            ]
            for holding in holdings
            if holding.get("pending_buy_notes")
        },
    }


def format_gap_review(review):
    lines = ["# Portfolio Completion Review", ""]
    lines.append(f"- holding_count={review['holding_count']}")
    lines.append(f"- known_invested_amount={review['known_invested_amount']}")
    lines.append(f"- known_cash_amount={review['known_cash_amount']}")
    lines.append(f"- overlay_applied={review.get('overlay_applied', False)}")
    if review.get("overlay_mode"):
        lines.append(f"- overlay_mode={review['overlay_mode']}")
    lines.append(f"- gap_count={review['gap_count']}")
    lines.append("")
    lines.append("## Gaps")
    if not review["gaps"]:
        lines.append("- none")
    for item in review["gaps"]:
        lines.append(
            "- "
            f"severity={item['severity']} ref={item['ref']} field={item['field']} "
            f"issue={item['issue']} action={item['action']}"
        )
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--template", action="store_true", help="Print overlay template JSON.")
    parser.add_argument("--write-template", action="store_true", help="Write overlay template to the private overlay path if absent.")
    parser.add_argument("--force", action="store_true", help="Overwrite an existing private overlay template.")
    parser.add_argument("--base", action="store_true", help="Review the raw portfolio before applying the private overlay.")
    args = parser.parse_args(argv)

    settings = load_settings()
    use_base = args.base or args.template or args.write_template
    portfolio, _, _, _ = load_portfolio(settings, apply_overlay=not use_base)
    if args.template:
        print(json.dumps(build_overlay_template(portfolio), ensure_ascii=False, indent=2))
        return 0
    if args.write_template:
        path = get_portfolio_overlay_path(settings)
        if path is None:
            raise SystemExit("portfolio_overlay_path is not configured")
        path = Path(path)
        if path.exists() and not args.force:
            raise SystemExit(f"Overlay template already exists: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(build_overlay_template(portfolio), f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"Wrote private overlay template to {path}")
        return 0
    print(format_gap_review(build_gap_review(portfolio)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
