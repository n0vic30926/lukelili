#!/usr/bin/env python3
"""Read-only individual security research data adapter."""

try:
    import akshare as ak
except ImportError:
    ak = None


def _row_count(value):
    if value is None:
        return 0
    try:
        return len(value)
    except TypeError:
        return 1


def _records(value):
    if value is None:
        return []
    if hasattr(value, "to_dict"):
        try:
            return value.to_dict("records")
        except TypeError:
            return value.to_dict()
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return [value]
    return []


def _clean_code(symbol):
    return str(symbol or "").replace("sh", "").replace("sz", "").strip()


def _call_rows(ak_client, method_name, symbol):
    method = getattr(ak_client, method_name, None)
    if not method:
        return None, "missing_method"
    try:
        value = method(symbol=symbol)
        return value, "available"
    except Exception:
        return None, "failed"


def _call_noarg_rows(ak_client, method_name):
    method = getattr(ak_client, method_name, None)
    if not method:
        return None, "missing_method"
    try:
        return method(), "available"
    except Exception:
        return None, "failed"


def _quote_match_count(value, symbol):
    cleaned = _clean_code(symbol)
    if not cleaned:
        return 0
    rows = _records(value)
    return sum(1 for row in rows if isinstance(row, dict) and str(row.get("代码") or "") == cleaned)


def _data_source(name, status):
    return {
        "name": name,
        "source": "AkShare",
        "status": status,
        "source_tier": "community_data",
    }


def fetch_security_research(symbol, ak_client=None):
    ak_client = ak_client if ak_client is not None else ak
    if ak_client is None:
        return {
            "status": "skipped",
            "observations": [],
            "evidence": [],
            "data_sources": [
                _data_source("financial_statements", "missing_dependency"),
                _data_source("announcements", "missing_dependency"),
                _data_source("valuation_metrics", "missing_dependency"),
                _data_source("security_market_quotes", "missing_dependency"),
                _data_source("research_reports", "missing_dependency"),
            ],
            "limitations": ["missing_dependency: akshare"],
        }

    symbol_calls = [
        ("financial_statements", "stock_financial_abstract", "security.financial_statements"),
        ("announcements", "stock_notice_report", "security.announcements"),
        ("valuation_metrics", "stock_a_indicator_lg", "security.valuation_metrics"),
        ("research_reports", "stock_research_report_em", "security.research_reports"),
    ]
    observations = []
    evidence = []
    data_sources = []
    for name, method_name, evidence_label in symbol_calls:
        value, status = _call_rows(ak_client, method_name, symbol)
        data_sources.append(_data_source(name, status))
        if status == "available":
            observations.append(f"{name}_rows={_row_count(value)}")
            evidence.append({"label": evidence_label, "source_tier": "community_data", "freshness": "unknown"})

    quote_value, quote_status = _call_noarg_rows(ak_client, "stock_zh_a_spot_em")
    quote_matches = _quote_match_count(quote_value, symbol) if quote_status == "available" else 0
    data_sources.append(
        _data_source(
            "security_market_quotes",
            "available" if quote_matches else ("empty" if quote_status == "available" else quote_status),
        )
    )
    observations.append(f"security_market_quotes_found={quote_matches}")
    if quote_matches:
        evidence.append({"label": "security.market_quotes", "source_tier": "community_data", "freshness": "unknown"})

    return {
        "status": "ok" if evidence else "skipped",
        "observations": observations,
        "evidence": evidence,
        "data_sources": data_sources,
        "limitations": [] if evidence else ["no security data fetched"],
    }


def main():
    print(fetch_security_research(""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
