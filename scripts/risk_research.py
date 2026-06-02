#!/usr/bin/env python3
"""Read-only portfolio risk research data adapter."""

try:
    import akshare as ak
except ImportError:
    ak = None

from common.portfolio_exposure import summarize_portfolio_exposure


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


def _data_source(name, source, status):
    source_tier = "local_user_data" if source == "local" else "community_data"
    return {
        "name": name,
        "source": source,
        "status": status,
        "source_tier": source_tier,
    }


def _codes_from_portfolio(portfolio):
    etf_codes = []
    stock_codes = []
    for collection_name in ("holdings", "watchlist"):
        for item in portfolio.get(collection_name, []) or []:
            if not isinstance(item, dict):
                continue
            if item.get("proxy_etf"):
                etf_codes.append(item["proxy_etf"])
            item_type = str(item.get("type") or item.get("asset_type") or "").lower()
            market = str(item.get("market") or "").lower()
            code = item.get("code")
            if code and ("etf" in item_type):
                etf_codes.append(code)
            elif code and (market == "a_share" or "stock" in item_type or "equity" in item_type):
                stock_codes.append(code)
    return sorted({_clean_code(code) for code in etf_codes if _clean_code(code)}), sorted(
        {_clean_code(code) for code in stock_codes if _clean_code(code)}
    )


def _spot_rows(ak_client, method_name):
    method = getattr(ak_client, method_name, None)
    if not method:
        return [], "missing_method"
    try:
        return _records(method()), "available"
    except Exception:
        return [], "failed"


def _match_count(rows, codes):
    row_codes = {str(row.get("代码") or "") for row in rows if isinstance(row, dict)}
    return sum(1 for code in codes if code in row_codes)


def _market_quote_state(ak_client, etf_codes, stock_codes):
    requested = len(etf_codes) + len(stock_codes)
    if requested == 0:
        return 0, 0, "skipped"

    matched = 0
    statuses = []
    if etf_codes:
        rows, status = _spot_rows(ak_client, "fund_etf_spot_em")
        statuses.append(status)
        if status == "available":
            matched += _match_count(rows, etf_codes)
    if stock_codes:
        rows, status = _spot_rows(ak_client, "stock_zh_a_spot_em")
        statuses.append(status)
        if status == "available":
            matched += _match_count(rows, stock_codes)

    if matched:
        return matched, requested, "available"
    if "available" in statuses:
        return matched, requested, "empty"
    if "failed" in statuses:
        return matched, requested, "failed"
    return matched, requested, "missing_method"


def _benchmark_quote_state(ak_client):
    rows, status = _spot_rows(ak_client, "stock_zh_index_spot_em")
    if status != "available":
        return 0, status
    return len(rows), "available" if rows else "empty"


def fetch_risk_research(portfolio, ak_client=None):
    ak_client = ak_client if ak_client is not None else ak
    portfolio = portfolio or {}
    exposure = summarize_portfolio_exposure(portfolio)
    rules = portfolio.get("risk_rules") or {}
    factor_counts = exposure.get("factor_counts") or {}
    factor_profile_count = sum(count for name, count in factor_counts.items() if name != "none")
    etf_codes, stock_codes = _codes_from_portfolio(portfolio)

    observations = [
        f"holding_count={exposure['holding_count']}",
        f"cash_pct={exposure['cash_pct']}",
        f"invested_pct={exposure['invested_pct']}",
        f"max_position_pct={exposure['max_position_pct']}",
        f"exposure_warnings={len(exposure.get('warnings') or [])}",
        f"risk_limit_breaches={len(exposure.get('warnings') or [])}",
        f"cash_buffer_pct={exposure['cash_pct']}",
        f"factor_profile_count={factor_profile_count}",
    ]
    evidence = [
        {"label": "portfolio.exposure", "source_tier": "local_user_data", "freshness": "fresh"},
        {"label": "portfolio.risk_rules", "source_tier": "local_user_data", "freshness": "fresh"},
        {"label": "portfolio.cash_buffer", "source_tier": "local_user_data", "freshness": "fresh"},
    ]
    data_sources = [
        _data_source("portfolio_context", "local", "available"),
        _data_source("risk_rules", "local", "available" if rules else "empty"),
        _data_source("portfolio_exposure", "local", "available"),
        _data_source("cash_buffer", "local", "available" if "cash" in portfolio else "empty"),
        _data_source("risk_limit_breaches", "local", "available"),
        _data_source("factor_exposure", "local", "available" if factor_profile_count else "empty"),
    ]
    if exposure.get("warnings"):
        evidence.append({"label": "portfolio.risk_limit_breaches", "source_tier": "local_user_data", "freshness": "fresh"})
    if factor_profile_count:
        evidence.append({"label": "portfolio.factor_profile", "source_tier": "local_user_data", "freshness": "fresh"})

    if ak_client is None:
        observations.append(f"market_quote_matches=0/{len(etf_codes) + len(stock_codes)}")
        data_sources.append(_data_source("market_quotes", "AkShare", "missing_dependency"))
        observations.append("benchmark_quotes_rows=0")
        data_sources.append(_data_source("benchmark_quotes", "AkShare", "missing_dependency"))
        return {
            "status": "skipped",
            "observations": observations,
            "evidence": evidence,
            "data_sources": data_sources,
            "limitations": ["missing_dependency: akshare"],
        }

    matched, requested, quote_status = _market_quote_state(ak_client, etf_codes, stock_codes)
    observations.append(f"market_quote_matches={matched}/{requested}")
    data_sources.append(_data_source("market_quotes", "AkShare", quote_status))
    if quote_status == "available":
        evidence.append({"label": "risk.market_quotes", "source_tier": "community_data", "freshness": "unknown"})

    benchmark_rows, benchmark_status = _benchmark_quote_state(ak_client)
    observations.append(f"benchmark_quotes_rows={benchmark_rows}")
    data_sources.append(_data_source("benchmark_quotes", "AkShare", benchmark_status))
    if benchmark_status == "available":
        evidence.append({"label": "risk.benchmark_quotes", "source_tier": "community_data", "freshness": "unknown"})

    return {
        "status": "ok" if "available" in {quote_status, benchmark_status} else "skipped",
        "observations": observations,
        "evidence": evidence,
        "data_sources": data_sources,
        "limitations": [] if "available" in {quote_status, benchmark_status} else ["no market quote data fetched"],
    }


def main():
    print(fetch_risk_research({}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
