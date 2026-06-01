#!/usr/bin/env python3
"""Read-only ETF research data adapter."""

try:
    import akshare as ak
except ImportError:
    ak = None


def _clean_code(code):
    return str(code or "").replace("sh", "").replace("sz", "").strip()


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


def _float_or_none(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _data_source(name, status):
    return {
        "name": name,
        "source": "AkShare",
        "status": status,
        "source_tier": "community_data",
    }


def _spot_rows(ak_client):
    method = getattr(ak_client, "fund_etf_spot_em", None)
    if not method:
        return [], "missing_method"
    try:
        return _records(method()), "available"
    except Exception:
        return [], "failed"


def _nav_for_code(ak_client, code):
    method = getattr(ak_client, "fund_etf_fund_info_em", None)
    if not method:
        return None, "missing_method"
    try:
        rows = _records(method(symbol=_clean_code(code)))
    except Exception:
        return None, "failed"
    if not rows:
        return None, "empty"
    latest = rows[-1]
    nav = _float_or_none(latest.get("单位净值") or latest.get("净值") or latest.get("nav"))
    return nav, "available" if nav is not None else "missing_nav"


def fetch_etf_research(codes, ak_client=None):
    ak_client = ak_client if ak_client is not None else ak
    cleaned_codes = [_clean_code(code) for code in codes or [] if _clean_code(code)]
    if ak_client is None:
        return {
            "status": "skipped",
            "observations": [],
            "evidence": [],
            "data_sources": [
                _data_source("etf_quotes", "missing_dependency"),
                _data_source("liquidity_metrics", "missing_dependency"),
                _data_source("premium_discount", "missing_dependency"),
            ],
            "limitations": ["missing_dependency: akshare"],
        }
    if not cleaned_codes:
        return {
            "status": "skipped",
            "observations": [],
            "evidence": [],
            "data_sources": [
                _data_source("etf_quotes", "skipped"),
                _data_source("liquidity_metrics", "skipped"),
                _data_source("premium_discount", "skipped"),
            ],
            "limitations": ["no ETF codes to query"],
        }

    rows, quote_status = _spot_rows(ak_client)
    row_by_code = {str(row.get("代码") or ""): row for row in rows if isinstance(row, dict)}
    matched = [row_by_code[code] for code in cleaned_codes if code in row_by_code]
    liquidity_available = sum(1 for row in matched if _float_or_none(row.get("成交额")) is not None)

    premium_available = 0
    for code in cleaned_codes:
        row = row_by_code.get(code)
        price = _float_or_none((row or {}).get("最新价"))
        nav, _ = _nav_for_code(ak_client, code)
        if price and nav:
            premium_available += 1

    data_sources = [
        _data_source("etf_quotes", quote_status if matched else ("empty" if quote_status == "available" else quote_status)),
        _data_source("liquidity_metrics", "available" if liquidity_available else "empty"),
        _data_source("premium_discount", "available" if premium_available else "empty"),
    ]
    evidence = []
    if matched:
        evidence.append({"label": "etf.quotes", "source_tier": "community_data", "freshness": "unknown"})
    if premium_available:
        evidence.append({"label": "etf.premium_discount", "source_tier": "community_data", "freshness": "unknown"})

    return {
        "status": "ok" if evidence else "skipped",
        "observations": [
            f"etf_quotes_found={len(matched)}/{len(cleaned_codes)}",
            f"liquidity_amount_available={liquidity_available}",
            f"premium_discount_available={premium_available}",
        ],
        "evidence": evidence,
        "data_sources": data_sources,
        "limitations": [] if evidence else ["no ETF data fetched"],
    }


def main():
    print(fetch_etf_research([]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
