"""Report-side decision context helpers."""

import json

from common.config_loader import get_scenario_assumptions_path
from common.output_contract import build_report_output_sections
from common.signal_ranking import rank_scenario_signals
from portfolio_backtest import build_portfolio_backtest
from rebalance_review import build_rebalance_review
from portfolio_scenarios import build_scenario_review
from portfolio_xray import build_portfolio_xray
from validate_scenarios import validate_scenarios


def _scenario_signals(scenario_review):
    signals = []
    for scenario in (scenario_review or {}).get("scenarios") or []:
        risk_flags = [
            str(item.get("type") or "unknown")
            for item in scenario.get("risk_flags") or []
        ]
        for signal in scenario.get("decision_signals") or []:
            signals.append(
                {
                    "scenario": str(scenario.get("name") or "unnamed_scenario"),
                    "signal": str(signal.get("signal") or "unknown"),
                    "portfolio_impact_pct": scenario.get("portfolio_impact_pct"),
                    "risk_flags": risk_flags,
                    "requires_user_confirmation": bool(
                        signal.get("requires_user_confirmation")
                    ),
                }
            )
    return signals


def load_report_scenario_review(portfolio, settings=None):
    path = get_scenario_assumptions_path(settings)
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as f:
        scenarios = json.load(f)
    if validate_scenarios(scenarios):
        return None
    return build_scenario_review(portfolio, scenarios)


def build_report_decision_context(portfolio, scenario_review=None):
    xray = build_portfolio_xray(portfolio)
    backtest = build_portfolio_backtest(portfolio)
    rebalance = build_rebalance_review(portfolio)
    fee_review = xray.get("fee_review") or {}
    signals = _scenario_signals(scenario_review)
    ranked_signals = rank_scenario_signals(signals)
    scenario_boundary = (scenario_review or {}).get("boundary") or {}
    stock_intersection = xray.get("stock_intersection") or {}

    facts = [
        "report_decision_context=enabled",
        "xray_holding_count=" + str(xray.get("holding_count", 0)),
        "xray_underlying_count=" + str(stock_intersection.get("underlying_count", 0)),
        "backtest_observation_count=" + str(backtest.get("observation_count", 0)),
        "rebalance_reviewed_position_count="
        + str(rebalance.get("reviewed_position_count", 0)),
        "xray_execution_allowed="
        + str(bool((xray.get("boundary") or {}).get("execution_allowed"))).lower(),
    ]
    if scenario_review:
        facts.append(
            "scenario_projection="
            + str(scenario_boundary.get("projection", "model projection, not a fact"))
        )

    inferences = [
        "xray_fee_coverage=" + str(fee_review.get("fee_coverage_count", 0)),
        "xray_overlap_clusters=" + str(len(xray.get("overlap_clusters") or [])),
        "xray_warnings=" + str(len(xray.get("warnings") or [])),
        "backtest_max_drawdown_pct=" + str(backtest.get("max_drawdown_pct", 0.0)),
        "backtest_annualized_volatility_pct="
        + str(backtest.get("annualized_volatility_pct", 0.0)),
        "rebalance_max_abs_drift_pct="
        + str(rebalance.get("max_abs_drift_pct", 0.0)),
    ]

    judgments = [
        f"scenario={item['scenario']} decision_signal={item['signal']} priority={item['priority']}"
        for item in ranked_signals
    ]
    if rebalance.get("decision_signals"):
        judgments.append(
            "rebalance_signal_count="
            + str(len(rebalance.get("decision_signals") or []))
        )
    if not judgments:
        judgments.append("scenario_signals=none")

    confirmations = [
        "user confirms report x-ray is decision support, not execution",
    ]
    if rebalance.get("decision_signals"):
        confirmations.append(
            "user confirms report rebalance signals are model judgment, not execution"
        )
    if ranked_signals:
        confirmations.extend(
            [
                "user confirms report scenario signals are model judgment, not facts",
                "user confirms report scenario signals are not execution consent",
            ]
        )

    return {
        "facts": facts,
        "inferences": inferences,
        "judgments": judgments,
        "confirmations": confirmations,
    }


def build_report_sections_with_decision_context(
    report_type,
    portfolio,
    run_summary,
    scenario_review=None,
):
    context = build_report_decision_context(
        portfolio,
        scenario_review=scenario_review,
    )
    return build_report_output_sections(
        report_type,
        portfolio,
        run_summary,
        decision_context=context,
    )
