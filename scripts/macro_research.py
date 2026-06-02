#!/usr/bin/env python3
"""Read-only macro research data adapter."""

try:
    import akshare as ak
except ImportError:
    ak = None


_DEFAULT_AK_CLIENT = object()


def _row_count(value):
    if value is None:
        return 0
    try:
        return len(value)
    except TypeError:
        return 1


def _data_source(name, status):
    return {
        "name": name,
        "source": "AkShare",
        "status": status,
        "source_tier": "community_data",
    }


def _call_rows(ak_client, method_name):
    method = getattr(ak_client, method_name, None)
    if not method:
        return None, "missing_method"
    try:
        return method(), "available"
    except Exception:
        return None, "failed"


def fetch_macro_research(ak_client=_DEFAULT_AK_CLIENT):
    ak_client = ak if ak_client is _DEFAULT_AK_CLIENT else ak_client
    if ak_client is None:
        return {
            "status": "skipped",
            "observations": [],
            "evidence": [],
            "data_sources": [
                _data_source("macro_rates", "missing_dependency"),
                _data_source("fx_rates", "missing_dependency"),
                _data_source("liquidity_indicators", "missing_dependency"),
            ],
            "limitations": ["missing_dependency: akshare"],
        }

    calls = [
        ("macro_rates", "bond_zh_us_rate", "macro.rates"),
        ("fx_rates", "fx_spot_quote", "macro.fx"),
        ("liquidity_indicators", "macro_china_money_supply", "macro.liquidity"),
    ]
    observations = []
    evidence = []
    data_sources = []
    for name, method_name, evidence_label in calls:
        value, status = _call_rows(ak_client, method_name)
        data_sources.append(_data_source(name, status))
        if status == "available":
            observations.append(f"{name}_rows={_row_count(value)}")
            evidence.append({"label": evidence_label, "source_tier": "community_data", "freshness": "unknown"})

    return {
        "status": "ok" if evidence else "skipped",
        "observations": observations,
        "evidence": evidence,
        "data_sources": data_sources,
        "limitations": [] if evidence else ["no macro data fetched"],
    }


def main():
    print(fetch_macro_research())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
