"""Ranking helpers for decision-support signals."""


SIGNAL_SCORE = {
    "risk_reduction_review": 40,
    "hold_or_add_review": 20,
    "hold_review": 10,
}


def _number(value, default=0.0):
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    return default


def _priority(score):
    if score >= 70:
        return "high"
    if score >= 35:
        return "medium"
    return "low"


def score_scenario_signal(signal):
    base = SIGNAL_SCORE.get(str(signal.get("signal") or "unknown"), 0)
    impact = abs(_number(signal.get("portfolio_impact_pct")))
    risk_flags = signal.get("risk_flags") or []
    risk_score = 30 if risk_flags else 0
    confirmation_score = 5 if signal.get("requires_user_confirmation") else 0
    return round(base + risk_score + impact + confirmation_score, 1)


def rank_scenario_signals(signals):
    ranked = []
    for signal in signals or []:
        item = dict(signal)
        item["score"] = score_scenario_signal(signal)
        item["priority"] = _priority(item["score"])
        ranked.append(item)
    return sorted(
        ranked,
        key=lambda item: (
            -item["score"],
            str(item.get("scenario") or ""),
            str(item.get("signal") or ""),
        ),
    )


def format_ranked_signals(signals):
    lines = []
    for item in signals or []:
        lines.append(
            "scenario="
            + str(item.get("scenario") or "unknown")
            + " signal="
            + str(item.get("signal") or "unknown")
            + " priority="
            + str(item.get("priority") or "unknown")
            + " score="
            + str(item.get("score"))
        )
    return "\n".join(lines)
