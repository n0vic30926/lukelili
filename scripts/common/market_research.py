#!/usr/bin/env python3
"""Macro and ETF research helpers for daily reports."""

from common.data_runtime import cached_call


def _safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _format_pct(value):
    if value is None:
        return "N/A"
    return f"{value:+.2f}%"


def liquidity_tier(amount):
    """Classify ETF turnover/liquidity using RMB amount when available."""
    if amount is None:
        return "unknown"
    if amount >= 1_000_000_000:
        return "high"
    if amount >= 100_000_000:
        return "medium"
    return "low"


def macro_observation(ak, pd, settings, tracker):
    """Return markdown lines for macro conditions using best-effort AkShare data."""
    lines = ["## 🌏 宏观观察", ""]

    us_index = cached_call(
        settings,
        tracker,
        "macro_us_index",
        "AkShare index_us_stock_sina",
        "macro_us_index:.IXIC",
        lambda: ak.index_us_stock_sina(symbol=".IXIC"),
        None,
    )
    if us_index is not None and len(us_index) >= 2:
        us_index = us_index.tail(30).copy()
        latest = us_index.iloc[-1]
        first = us_index.iloc[0]
        latest_close = _safe_float(latest.get("close"))
        first_close = _safe_float(first.get("close"))
        ret_30d = (latest_close / first_close - 1) * 100 if latest_close and first_close else None
        lines.append(f"- 纳斯达克: {latest_close:.2f} | 近30日 {_format_pct(ret_30d)}")
    else:
        lines.append("- 纳斯达克: 数据不可用")

    fx_quote = cached_call(
        settings,
        tracker,
        "macro_fx_quote",
        "AkShare fx_spot_quote",
        "macro_fx_quote",
        lambda: ak.fx_spot_quote(),
        None,
    )
    if fx_quote is not None:
        try:
            usd = fx_quote[fx_quote["货币对"] == "USD/CNY"]
            rate = _safe_float(usd.iloc[0].get("买报价")) if not usd.empty else None
        except Exception:
            rate = None
        lines.append(f"- USD/CNY: {rate:.4f}" if rate else "- USD/CNY: 数据不可用")
    else:
        lines.append("- USD/CNY: 数据不可用")

    fx_history = cached_call(
        settings,
        tracker,
        "macro_fx_history",
        "AkShare currency_boc_safe",
        "macro_fx_history",
        lambda: ak.currency_boc_safe(),
        None,
    )
    if fx_history is not None and len(fx_history) >= 2:
        try:
            fx_col = [c for c in fx_history.columns if "美元" in str(c) or "USD" in str(c).upper()]
            fx_col = fx_col[0] if fx_col else fx_history.columns[1]
            fx_history = fx_history.tail(30).copy()
            start = _safe_float(str(fx_history.iloc[0][fx_col]).replace(",", ""))
            end = _safe_float(str(fx_history.iloc[-1][fx_col]).replace(",", ""))
            if start and end:
                fx_ret = (end / start - 1) * 100
                lines.append(f"- 人民币中间价近30日变化: {_format_pct(fx_ret)}")
            else:
                lines.append("- 人民币中间价近30日变化: 数据不可用")
        except Exception as exc:
            tracker.fail("macro_fx_history_parse", "AkShare currency_boc_safe", exc)
            lines.append("- 人民币中间价近30日变化: 数据不可用")
    else:
        lines.append("- 人民币中间价近30日变化: 数据不可用")

    lines.append("- 宏观结论: 仅描述环境，不构成买卖信号。")
    lines.append("")
    return lines


def etf_observation(ak, settings, tracker, holdings):
    """Return markdown lines for proxy ETF liquidity and price observations."""
    lines = ["## 🧾 ETF专项观察", ""]
    proxy_codes = [h.get("proxy_etf") for h in holdings if h.get("proxy_etf")]
    if not proxy_codes:
        lines.append("- 当前持仓未配置 proxy_etf，无法做 ETF 代理观察。")
        lines.append("")
        return lines

    quote = cached_call(
        settings,
        tracker,
        "etf_research_quote",
        "AkShare fund_etf_spot_em",
        "etf_research_quote",
        lambda: ak.fund_etf_spot_em(),
        None,
    )
    if quote is None:
        lines.append("- ETF行情: 数据不可用")
        lines.append("")
        return lines

    for holding in holdings:
        code = holding.get("proxy_etf")
        if not code:
            continue
        code_clean = code.replace("sh", "").replace("sz", "")
        try:
            row = quote[quote["代码"] == code_clean]
        except Exception:
            row = []
        if len(row) == 0:
            lines.append(f"- {holding.get('name', code)} / {code}: 行情不可用")
            continue
        item = row.iloc[0]
        price = _safe_float(item.get("最新价"))
        change_pct = _safe_float(item.get("涨跌幅"))
        amount = _safe_float(item.get("成交额"))
        tier = liquidity_tier(amount)
        amount_text = f"{amount / 100000000:.2f}亿" if amount is not None else "N/A"
        lines.append(
            f"- {holding.get('name', code)} / {code}: 价格 {price:.3f} | 涨跌 {_format_pct(change_pct)} | 成交额 {amount_text} | 流动性 {tier}"
        )
    lines.append("- ETF结论: 溢价/折价、跟踪误差和费率仍需后续专项数据源补齐。")
    lines.append("")
    return lines
