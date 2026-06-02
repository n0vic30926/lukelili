"""Build role-specific research questions from data-source states."""


ROLE_SOURCE_QUESTIONS = {
    "macro": {
        "macro_rates": {
            "available": "How does confirmed macro_rates freshness affect rate-sensitive exposure?",
            "unavailable": "Which macro_rates source must refresh before judgment on rate-sensitive exposure?",
        },
        "fx_rates": {
            "available": "How does confirmed fx_rates freshness affect FX translation exposure?",
            "unavailable": "Which fx_rates source must refresh before judgment on FX translation exposure?",
        },
        "liquidity_indicators": {
            "available": "How does confirmed liquidity_indicators freshness affect liquidity-sensitive exposure?",
            "unavailable": "Which liquidity_indicators source must refresh before judgment on liquidity-sensitive exposure?",
        },
    },
    "security": {
        "financial_statements": {
            "available": "What fundamental quality questions are supported by current financial_statements?",
            "unavailable": "Which financial_statements source must refresh before judgment on fundamental quality?",
        },
        "announcements": {
            "available": "What announcements need review for event or filing context?",
            "unavailable": "Which announcements source must refresh before judgment on event or filing context?",
        },
        "valuation_metrics": {
            "available": "What valuation context questions are supported by current valuation_metrics?",
            "unavailable": "Which valuation_metrics source must refresh before judgment on valuation context?",
        },
    },
    "etf": {
        "etf_quotes": {
            "available": "What ETF quote freshness is needed before reviewing tracking context?",
            "unavailable": "Which etf_quotes source must refresh before judgment on tracking context?",
        },
        "premium_discount": {
            "available": "What premium or discount context needs comparison with ETF quotes?",
            "unavailable": "Which premium_discount source must refresh before judgment on premium or discount context?",
        },
        "liquidity_metrics": {
            "available": "What ETF liquidity questions are supported by current liquidity_metrics?",
            "unavailable": "Which liquidity_metrics source must refresh before judgment on ETF liquidity?",
        },
    },
    "risk": {
        "risk_rules": {
            "available": "Which hard risk controls should be checked against current portfolio exposure?",
            "unavailable": "Which risk_rules source must refresh before judgment on hard risk controls?",
        },
        "market_quotes": {
            "available": "What market movement context should be checked before risk judgment?",
            "unavailable": "Which market_quotes source must refresh before judgment on market movement context?",
        },
        "factor_exposure": {
            "available": "What factor concentration questions are supported by current factor_exposure?",
            "unavailable": "Which factor_exposure source must refresh before judgment on factor concentration?",
        },
    },
}

AVAILABLE_STATUSES = {"available"}


def _status_by_name(data_sources):
    statuses = {}
    for item in data_sources or []:
        name = str(item.get("name") or "")
        if name:
            statuses[name] = str(item.get("status") or "unknown")
    return statuses


def build_role_research_questions(role, data_sources, limit=4):
    """Return bounded role questions derived from source state, not forecasts."""
    rules = ROLE_SOURCE_QUESTIONS.get(str(role or ""))
    if not rules:
        return []

    statuses = _status_by_name(data_sources)
    questions = []
    for source_name, templates in rules.items():
        if source_name not in statuses:
            continue
        state = "available" if statuses[source_name] in AVAILABLE_STATUSES else "unavailable"
        questions.append(templates[state])
    return questions[:limit]
