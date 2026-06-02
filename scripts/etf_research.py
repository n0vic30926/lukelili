#!/usr/bin/env python3
"""Read-only ETF research data adapter."""

from datetime import date

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


def _latest_completed_year(today=None):
    today = today or date.today()
    return str(today.year - 1)


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
        return None, [], "missing_method"
    try:
        rows = _records(method(symbol=_clean_code(code)))
    except Exception:
        return None, [], "failed"
    if not rows:
        return None, [], "empty"
    latest = rows[-1]
    nav = _float_or_none(latest.get("单位净值") or latest.get("净值") or latest.get("nav"))
    return nav, rows, "available" if nav is not None else "missing_nav"


def _holdings_rows_for_code(ak_client, code):
    method = getattr(ak_client, "fund_portfolio_hold_em", None)
    if not method:
        return [], "missing_method"
    try:
        rows = _records(method(symbol=_clean_code(code), date=_latest_completed_year()))
    except Exception:
        return [], "failed"
    return rows, "available" if rows else "empty"


def _aggregate_status(available_count, statuses):
    if available_count:
        return "available"
    if "available" in statuses or "missing_nav" in statuses:
        return "empty"
    if "failed" in statuses:
        return "failed"
    if "missing_method" in statuses:
        return "missing_method"
    return "empty"


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
                _data_source("etf_nav_history", "missing_dependency"),
                _data_source("etf_holdings", "missing_dependency"),
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
                _data_source("etf_nav_history", "skipped"),
                _data_source("etf_holdings", "skipped"),
            ],
            "limitations": ["no ETF codes to query"],
        }

    rows, quote_status = _spot_rows(ak_client)
    row_by_code = {str(row.get("代码") or ""): row for row in rows if isinstance(row, dict)}
    matched = [row_by_code[code] for code in cleaned_codes if code in row_by_code]
    liquidity_available = sum(1 for row in matched if _float_or_none(row.get("成交额")) is not None)

    premium_available = 0
    nav_history_available = 0
    nav_statuses = []
    holdings_available = 0
    holdings_statuses = []
    for code in cleaned_codes:
        row = row_by_code.get(code)
        price = _float_or_none((row or {}).get("最新价"))
        nav, nav_rows, nav_status = _nav_for_code(ak_client, code)
        nav_statuses.append(nav_status)
        if nav_rows:
            nav_history_available += 1
        if price and nav:
            premium_available += 1
        holding_rows, holdings_status = _holdings_rows_for_code(ak_client, code)
        holdings_statuses.append(holdings_status)
        if holding_rows:
            holdings_available += 1

    data_sources = [
        _data_source("etf_quotes", quote_status if matched else ("empty" if quote_status == "available" else quote_status)),
        _data_source("liquidity_metrics", "available" if liquidity_available else ("empty" if quote_status == "available" else quote_status)),
        _data_source("premium_discount", _aggregate_status(premium_available, nav_statuses)),
        _data_source("etf_nav_history", _aggregate_status(nav_history_available, nav_statuses)),
        _data_source("etf_holdings", _aggregate_status(holdings_available, holdings_statuses)),
    ]
    evidence = []
    if matched:
        evidence.append({"label": "etf.quotes", "source_tier": "community_data", "freshness": "unknown"})
    if premium_available:
        evidence.append({"label": "etf.premium_discount", "source_tier": "community_data", "freshness": "unknown"})
    if nav_history_available:
        evidence.append({"label": "etf.nav_history", "source_tier": "community_data", "freshness": "unknown"})
    if holdings_available:
        evidence.append({"label": "etf.holdings", "source_tier": "community_data", "freshness": "unknown"})

    return {
        "status": "ok" if evidence else "skipped",
        "observations": [
            f"etf_quotes_found={len(matched)}/{len(cleaned_codes)}",
            f"liquidity_amount_available={liquidity_available}",
            f"premium_discount_available={premium_available}",
            f"etf_nav_history_available={nav_history_available}",
            f"etf_holdings_available={holdings_available}",
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
