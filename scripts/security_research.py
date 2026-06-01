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


def _call_rows(ak_client, method_name, symbol):
    method = getattr(ak_client, method_name, None)
    if not method:
        return None, "missing_method"
    try:
        value = method(symbol=symbol)
        return value, "available"
    except Exception:
        return None, "failed"


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
            ],
            "limitations": ["missing_dependency: akshare"],
        }

    calls = [
        ("financial_statements", "stock_financial_abstract", "security.financial_statements"),
        ("announcements", "stock_notice_report", "security.announcements"),
        ("valuation_metrics", "stock_a_indicator_lg", "security.valuation_metrics"),
    ]
    observations = []
    evidence = []
    data_sources = []
    for name, method_name, evidence_label in calls:
        value, status = _call_rows(ak_client, method_name, symbol)
        data_sources.append(_data_source(name, status))
        if status == "available":
            observations.append(f"{name}_rows={_row_count(value)}")
            evidence.append({"label": evidence_label, "source_tier": "community_data", "freshness": "unknown"})

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
