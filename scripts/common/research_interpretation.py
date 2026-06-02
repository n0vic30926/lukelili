"""Interpret role data-source states into decision-support impact paths."""


ROLE_SOURCE_NOTES = {
    "macro": {
        "macro_rates": "rate-sensitive impact path",
        "fx_rates": "FX translation impact path",
        "liquidity_indicators": "liquidity impact path",
    },
    "security": {
        "financial_statements": "fundamental quality impact path",
        "announcements": "event and filing impact path",
        "valuation_metrics": "valuation context impact path",
    },
    "etf": {
        "etf_quotes": "ETF price and tracking impact path",
        "premium_discount": "premium or discount impact path",
        "liquidity_metrics": "ETF liquidity impact path",
    },
    "risk": {
        "risk_rules": "hard risk-control impact path",
        "market_quotes": "market movement impact path",
        "factor_exposure": "factor concentration impact path",
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


def interpret_role_data_state(role, data_sources):
    """Return concise role-level notes derived only from source availability."""
    rules = ROLE_SOURCE_NOTES.get(str(role or ""))
    if not rules:
        return []

    statuses = _status_by_name(data_sources)
    notes = []
    for source_name, impact_path in rules.items():
        if source_name not in statuses:
            continue
        status = statuses[source_name]
        if status in AVAILABLE_STATUSES:
            notes.append(f"{source_name} available: {impact_path} can be reviewed with source freshness")
        else:
            notes.append(f"{source_name} unavailable: {impact_path} remains unconfirmed")
    return notes
