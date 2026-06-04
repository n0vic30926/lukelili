"""Ranked recommendation packet builder.

The functions in this module turn existing local signals into explicit
recommendations. They never use private holding names/codes in rendered output
and never allow broker execution.
"""

from common.signal_ranking import rank_scenario_signals


def _number(value, default=0.0):
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    return default


def _confidence(score):
    return max(1, min(95, int(round(score))))


def _status(score):
    return "recommended" if score >= 50 else "informational"


def _holding_ref(index):
    return f"holding_{index + 1}"


def _base_rec(action, instrument_ref, direction, score, rationale, risks, invalidators, next_action, horizon="1-5 trading days", position_effect="review only"):
    return {
        "action": action,
        "instrument_ref": instrument_ref,
        "direction": direction,
        "horizon": horizon,
        "confidence": _confidence(score),
        "status": _status(score),
        "rationale": list(rationale),
        "risks": list(risks),
        "invalidators": list(invalidators),
        "position_effect": position_effect,
        "next_action": next_action,
        "execution_allowed": False,
        "_score": score,
    }


def _scenario_recommendations(scenario_review):
    recommendations = []
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
                    "requires_user_confirmation": bool(signal.get("requires_user_confirmation")),
                }
            )

    for signal in rank_scenario_signals(signals):
        signal_name = signal.get("signal")
        impact = _number(signal.get("portfolio_impact_pct"))
        risk_flags = signal.get("risk_flags") or []
        if signal_name == "risk_reduction_review":
            recommendations.append(
                _base_rec(
                    "reduce_risk",
                    "portfolio",
                    "reduce",
                    78 + min(abs(impact), 12),
                    [
                        "stress scenario breaches configured loss tolerance",
                        "scenario signal ranks as risk_reduction_review",
                    ],
                    [
                        "scenario is a model projection, not a fact",
                        "market data may be stale or incomplete",
                    ],
                    [
                        "scenario assumptions are revised below risk-rule threshold",
                        "fresh market data invalidates the drawdown path",
                    ],
                    "Review risk-reduction choices before any order: trim exposure, raise cash, or add hedge candidate.",
                    horizon="now to 3 trading days",
                    position_effect="lower portfolio risk exposure if user confirms",
                )
            )
        elif signal_name == "hold_or_add_review":
            recommendations.append(
                _base_rec(
                    "review_add",
                    "portfolio",
                    "increase",
                    52 + min(abs(impact), 10),
                    [
                        "scenario impact is positive under explicit assumptions",
                        "add decision still requires portfolio and risk-rule review",
                    ],
                    ["positive scenario may not persist", "cash deployment can increase drawdown"],
                    ["scenario edge disappears", "portfolio concentration exceeds risk limit"],
                    "Compare add size against target weights and cash buffer before acting.",
                    position_effect="possible increase in selected exposure after confirmation",
                )
            )
        elif signal_name == "hold_review":
            recommendations.append(
                _base_rec(
                    "hold",
                    "portfolio",
                    "hold",
                    35 + min(abs(impact), 10),
                    ["scenario remains inside configured hard-loss rule"],
                    ["holding can still be wrong if source data is stale"],
                    ["loss threshold is breached", "research coverage deteriorates"],
                    "Keep position under review and refresh data before changing exposure.",
                    position_effect="no position change",
                )
            )
    return recommendations


def _rebalance_recommendations(rebalance_review):
    recommendations = []
    for signal in (rebalance_review or {}).get("decision_signals") or []:
        position_ref = str(signal.get("position_ref") or "position_unknown")
        status = str(signal.get("status") or "unknown")
        drift = _number(signal.get("drift_pct"))
        if status == "overweight":
            direction = "reduce"
            next_action = f"Review reducing {position_ref} toward target weight."
        elif status == "underweight":
            direction = "increase"
            next_action = f"Review increasing {position_ref} toward target weight."
        else:
            direction = "hold"
            next_action = f"Keep {position_ref} within tolerance."
        recommendations.append(
            _base_rec(
                "rebalance",
                position_ref,
                direction,
                45 + min(abs(drift), 25),
                [
                    f"allocation drift status={status}",
                    f"drift_pct={round(drift, 1)}",
                ],
                ["target weights may be stale", "rebalancing can conflict with tax or liquidity constraints"],
                ["user updates target allocation", "fresh portfolio value brings drift back within tolerance"],
                next_action,
                horizon="next rebalance window",
                position_effect="move allocation closer to target if user confirms",
            )
        )
    return recommendations


def _backtest_recommendation(backtest):
    if not backtest:
        return []
    drawdown = _number(backtest.get("max_drawdown_pct"))
    observations = int(_number(backtest.get("observation_count")))
    if observations <= 0:
        return [
            _base_rec(
                "improve_data",
                "portfolio",
                "hold",
                30,
                ["local return history is missing"],
                ["recommendation confidence is limited without historical context"],
                ["return_history is added for current holdings"],
                "Add local return_history or benchmark history before relying on performance claims.",
                horizon="before formal use",
                position_effect="no position change",
            )
        ]
    if drawdown <= -10:
        return [
            _base_rec(
                "tighten_risk_controls",
                "portfolio",
                "reduce",
                55 + min(abs(drawdown), 20),
                [f"historical max_drawdown_pct={round(drawdown, 1)}"],
                ["history is local and may have partial coverage"],
                ["drawdown improves under updated history", "risk rules are revised by user"],
                "Review stop/risk rules and cash buffer before increasing exposure.",
                position_effect="lower future drawdown sensitivity if user confirms",
            )
        ]
    return [
        _base_rec(
            "monitor_performance",
            "portfolio",
            "hold",
            34,
            [f"historical max_drawdown_pct={round(drawdown, 1)} remains below high-risk trigger"],
            ["short history can understate tail risk"],
            ["drawdown worsens beyond threshold", "volatility rises materially"],
            "Keep monitoring backtest metrics during daily/weekly review.",
            position_effect="no position change",
        )
    ]


def _holding_recommendations(portfolio):
    recommendations = []
    for index, holding in enumerate(portfolio.get("holdings", []) or []):
        strategy = str(holding.get("strategy_type") or "unknown")
        ref = _holding_ref(index)
        if strategy == "short_term":
            recommendations.append(
                _base_rec(
                    "review_exit_rules",
                    ref,
                    "hold",
                    48,
                    ["short_term strategy requires explicit exit discipline"],
                    ["exit rules may be absent or stale"],
                    ["user confirms stop/take-profit rules are current"],
                    "Confirm stop-loss, take-profit, and invalidation levels before the next session.",
                    position_effect="no position change until rules are confirmed",
                )
            )
        elif strategy == "dca":
            recommendations.append(
                _base_rec(
                    "continue_discipline",
                    ref,
                    "hold",
                    38,
                    ["dca strategy emphasizes discipline over short-term timing"],
                    ["DCA can keep adding into deteriorating fundamentals"],
                    ["strategy_type changes by user", "hard risk rule is breached"],
                    "Continue scheduled review; do not change cadence without a risk-rule trigger.",
                    position_effect="maintain planned exposure path",
                )
            )
        elif strategy == "trial":
            recommendations.append(
                _base_rec(
                    "review_upgrade_or_exit",
                    ref,
                    "hold",
                    42,
                    ["trial strategy should produce a learning decision"],
                    ["trial positions can become accidental long-term holdings"],
                    ["user confirms upgrade criteria or exit criteria"],
                    "Write the upgrade/exit condition before adding capital.",
                    position_effect="no new capital until trial criteria are reviewed",
                )
            )
        elif strategy == "watch":
            recommendations.append(
                _base_rec(
                    "research_only",
                    ref,
                    "hold",
                    25,
                    ["watch item is not a position action"],
                    ["research can be mistaken for execution intent"],
                    ["user promotes watch item to an explicit strategy_type"],
                    "Keep this in research mode until user defines an entry rule.",
                    position_effect="no position change",
                )
            )
    return recommendations


def _research_gap_recommendation(research_result):
    unavailable = 0
    for role in (research_result or {}).get("role_results", []) or []:
        for source in role.get("data_sources") or []:
            if source.get("status") not in ("available", "ok"):
                unavailable += 1
    if unavailable <= 0:
        return []
    return [
        _base_rec(
            "refresh_data",
            "research_sources",
            "hold",
            min(60, 30 + unavailable),
            [f"unavailable_data_sources={unavailable}"],
            ["recommendation confidence is capped until data gaps close"],
            ["required market/news/local sources refresh successfully"],
            "Refresh missing dependencies and rerun research before increasing action size.",
            horizon="before acting on high-impact recommendations",
            position_effect="no position change",
        )
    ]


def build_recommendations(portfolio, research_result=None, scenario_review=None, rebalance_review=None, backtest=None, limit=7):
    items = []
    items.extend(_scenario_recommendations(scenario_review))
    items.extend(_rebalance_recommendations(rebalance_review))
    items.extend(_backtest_recommendation(backtest))
    items.extend(_holding_recommendations(portfolio))
    items.extend(_research_gap_recommendation(research_result))

    deduped = {}
    for item in items:
        key = (item["action"], item["instrument_ref"], item["direction"])
        current = deduped.get(key)
        if current is None or item["_score"] > current["_score"]:
            deduped[key] = item

    ranked = sorted(
        deduped.values(),
        key=lambda item: (-item["_score"], item["action"], item["instrument_ref"]),
    )[:limit]
    for index, item in enumerate(ranked, start=1):
        item.pop("_score", None)
        item["rank"] = index
        item["recommendation_id"] = f"rec_{index}"
    return ranked


def format_recommendations(recommendations):
    lines = ["## Ranked Recommendations"]
    if not recommendations:
        lines.append("- none")
        return "\n".join(lines)
    for item in recommendations:
        lines.append(
            "- "
            f"rank={item['rank']} "
            f"id={item['recommendation_id']} "
            f"action={item['action']} "
            f"instrument_ref={item['instrument_ref']} "
            f"direction={item['direction']} "
            f"status={item['status']} "
            f"confidence={item['confidence']} "
            f"horizon={item['horizon']} "
            f"execution_allowed={str(item['execution_allowed']).lower()}"
        )
        lines.append("  rationale=" + "; ".join(item["rationale"]))
        lines.append("  risks=" + "; ".join(item["risks"]))
        lines.append("  invalidators=" + "; ".join(item["invalidators"]))
        lines.append("  position_effect=" + item["position_effect"])
        lines.append("  next_action=" + item["next_action"])
    return "\n".join(lines)
