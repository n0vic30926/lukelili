#!/usr/bin/env python3
"""Macro and ETF research helpers for daily reports."""

from datetime import datetime
from math import sqrt
import re
from statistics import median

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


def _format_ratio(value):
    if value is None:
        return "未配置"
    pct = value * 100 if abs(value) <= 1 else value
    return f"{pct:.2f}%"


def _first_value(row, names):
    for name in names:
        try:
            value = row.get(name)
        except AttributeError:
            value = None
        parsed = _safe_float(value)
        if parsed is not None and parsed > 0:
            return parsed, name
    return None, ""


def _last_numeric_value(row, preferred_columns):
    value, col = _first_value(row, preferred_columns)
    if value is not None:
        return value, col
    for col_name, raw in row.items():
        value = _safe_float(str(raw).replace(",", ""))
        if value is not None:
            return value, col_name
    return None, ""


def _first_text_value(row, preferred_columns):
    for name in preferred_columns:
        try:
            value = row.get(name)
        except AttributeError:
            value = None
        if value not in (None, ""):
            return str(value), name
    for col_name, raw in row.items():
        if raw not in (None, ""):
            return str(raw), col_name
    return "N/A", ""


def _parse_indicator_date(value):
    text = str(value).strip()
    if not text or text == "N/A":
        return None
    normalized = text.replace("/", "-")
    quarter = re.search(r"(\d{4})-?Q([1-4])", normalized, flags=re.IGNORECASE)
    if not quarter:
        quarter = re.search(r"(\d{4})年\s*第?([1-4])季度", normalized)
    if quarter:
        year = int(quarter.group(1))
        month = (int(quarter.group(2)) - 1) * 3 + 1
        return datetime(year, month, 1).date()
    year_month = re.search(r"(\d{4})年\s*(\d{1,2})月", normalized)
    if year_month:
        normalized = f"{year_month.group(1)}-{int(year_month.group(2)):02d}"
    for fmt, length in (("%Y-%m-%d", 10), ("%Y-%m", 7), ("%Y", 4)):
        try:
            return datetime.strptime(normalized[:length], fmt).date()
        except ValueError:
            continue
    return None


def _freshness_text(date_text, indicator):
    parsed = _parse_indicator_date(date_text)
    cadence = indicator.get("cadence", "unknown")
    max_age_days = _safe_float(indicator.get("max_age_days"))
    if parsed is None:
        return f"日期不可解析 | cadence={cadence}"
    age_days = (datetime.now().date() - parsed).days
    status = "unknown"
    if max_age_days is not None:
        status = "fresh" if age_days <= max_age_days else "stale"
    return f"{age_days}天 | status={status} | cadence={cadence}"


def _interpret_indicator(latest_value, delta, indicator):
    rules = indicator.get("interpretation", {}) or {}
    threshold = _safe_float(rules.get("threshold"))
    if threshold is not None and latest_value is not None:
        if latest_value >= threshold:
            return rules.get("above", f"高于阈值 {threshold:g}。")
        return rules.get("below", f"低于阈值 {threshold:g}。")
    if delta is not None:
        if delta > 0 and rules.get("trend_up"):
            return rules["trend_up"]
        if delta < 0 and rules.get("trend_down"):
            return rules["trend_down"]
        if delta == 0 and rules.get("flat"):
            return rules["flat"]
    return rules.get("default", "")


def macro_release_calendar_lines(indicators, today=None):
    """Return release-calendar lines from local indicator config."""
    lines = ["### 宏观发布日历", ""]
    missing = []
    today = today or datetime.now().date()
    for indicator in indicators:
        label = indicator.get("label", indicator.get("id", "macro"))
        calendar = indicator.get("release_calendar", {}) or {}
        release_date = calendar.get("next_release_date")
        if not release_date:
            missing.append(label)
            continue
        parsed = _parse_indicator_date(release_date)
        days_text = "日期不可解析"
        if parsed:
            days = (parsed - today).days
            if days >= 0:
                days_text = f"{days}天后"
            else:
                days_text = f"已过期{abs(days)}天"
        source = calendar.get("source", "未配置")
        source_tier = calendar.get("source_tier", "unknown")
        lines.append(
            f"- {label}: 下一发布日期 {release_date} | {days_text} | source={source} | tier={source_tier}"
        )
        if calendar.get("note"):
            lines.append(f"  - {calendar['note']}")
    if missing:
        lines.append(f"- 发布日历缺口: {', '.join(missing)}")
    lines.append("- 日历边界: 只读取本地配置，不自动联网确认官方发布日期。")
    lines.append("")
    return lines


def fed_policy_calendar_lines(settings, today=None):
    """Return Fed/FOMC calendar lines from local settings."""
    calendar = settings.get("fed_policy_calendar", {}) or {}
    lines = ["### Fed政策日历", ""]
    source = calendar.get("source", "未配置")
    source_tier = calendar.get("source_tier", "unknown")
    target_rate = calendar.get("current_target_rate", "未配置")
    events = calendar.get("events", []) or []
    today = today or datetime.now().date()
    lines.append(f"- source={source} | tier={source_tier}")
    lines.append(f"- 当前目标利率: {target_rate}")
    if not events:
        lines.append("- Fed日历缺口: 未配置 FOMC/Fed 事件。")
    for event in events:
        date_text = event.get("date", "")
        parsed = _parse_indicator_date(date_text)
        days_text = "日期不可解析"
        if parsed:
            days = (parsed - today).days
            days_text = f"{days}天后" if days >= 0 else f"已过期{abs(days)}天"
        event_name = event.get("event", "Fed event")
        lines.append(f"- {date_text} | {event_name} | {days_text}")
        if event.get("watch"):
            lines.append(f"  - 关注点: {event['watch']}")
    lines.append("- Fed日历边界: 只读取本地配置，不自动联网确认会议日期或政策结果。")
    lines.append("")
    return lines


def _call_first_available(ak, settings, tracker, indicator):
    candidates = indicator.get("candidate_functions", [])
    for fn_name in candidates:
        fn = getattr(ak, fn_name, None)
        if not callable(fn):
            continue
        return cached_call(
            settings,
            tracker,
            f"macro_indicator:{indicator.get('id', fn_name)}",
            f"AkShare {fn_name}",
            f"macro_indicator:{indicator.get('id', fn_name)}:{fn_name}",
            fn,
            None,
        ), fn_name
    tracker.skip(
        f"macro_indicator:{indicator.get('id', 'unknown')}",
        "AkShare",
        f"candidate functions unavailable: {', '.join(candidates)}",
    )
    return None, ""


def macro_indicator_lines(ak, settings, tracker):
    """Return configured macro indicator radar lines."""
    indicators = settings.get("macro_indicators", [])
    lines = ["### 宏观指标雷达", ""]
    if not indicators:
        lines.append("- 未配置 macro_indicators。")
        lines.append("")
        return lines

    unavailable = []
    for indicator in indicators:
        label = indicator.get("label", indicator.get("id", "macro"))
        df, source_fn = _call_first_available(ak, settings, tracker, indicator)
        if df is None or len(df) == 0:
            unavailable.append(label)
            lines.append(f"- {label}: 数据不可用")
            continue
        try:
            latest = df.iloc[-1]
            previous = df.iloc[-2] if len(df) >= 2 else latest
            date_text, _ = _first_text_value(latest, indicator.get("date_columns", []))
            latest_value, value_col = _last_numeric_value(latest, indicator.get("value_columns", []))
            prev_value, _ = _last_numeric_value(previous, [value_col] if value_col else indicator.get("value_columns", []))
            delta = latest_value - prev_value if latest_value is not None and prev_value is not None else None
            unit = indicator.get("unit", "")
            unit_text = unit if unit else ""
            value_text = f"{latest_value:.2f}{unit_text}" if latest_value is not None else "N/A"
            delta_text = f"{delta:+.2f}{unit_text}" if delta is not None else "N/A"
            note = indicator.get("risk_note", "")
            lines.append(
                f"- {label}: {value_text} | 日期 {date_text} | 较前值 {delta_text} | source={source_fn}"
            )
            if note:
                lines.append(f"  - {note}")
            lines.append(f"  - 数据时效: {_freshness_text(date_text, indicator)}")
            interpretation = _interpret_indicator(latest_value, delta, indicator)
            if interpretation:
                lines.append(f"  - 解读: {interpretation}")
        except Exception as exc:
            tracker.fail(f"macro_indicator_parse:{indicator.get('id', label)}", f"AkShare {source_fn}", exc)
            unavailable.append(label)
            lines.append(f"- {label}: 解析失败")

    if unavailable:
        lines.append(f"- 宏观数据缺口: {', '.join(unavailable)}")
    lines.extend(macro_release_calendar_lines(indicators))
    lines.extend(fed_policy_calendar_lines(settings))
    lines.append("")
    return lines


def liquidity_tier(amount):
    """Classify ETF turnover/liquidity using RMB amount when available."""
    if amount is None:
        return "unknown"
    if amount >= 1_000_000_000:
        return "high"
    if amount >= 100_000_000:
        return "medium"
    return "low"


def premium_discount(price, reference_nav):
    if price is None or reference_nav is None or reference_nav == 0:
        return None
    return (price / reference_nav - 1) * 100


def _risk_level(value, warn_threshold, high_threshold, use_abs=True):
    if value is None:
        return "unknown"
    score = abs(value) if use_abs else value
    if high_threshold is not None and score >= high_threshold:
        return "high"
    if warn_threshold is not None and score >= warn_threshold:
        return "elevated"
    return "normal"


def _expense_medians(holdings):
    grouped = {}
    for holding in holdings:
        profile = holding.get("etf_profile", {}) or {}
        benchmark = profile.get("benchmark")
        ratio = _safe_float(profile.get("expense_ratio"))
        if benchmark and benchmark != "未配置" and ratio is not None:
            grouped.setdefault(benchmark, []).append(ratio)
    return {benchmark: median(values) for benchmark, values in grouped.items() if values}


def _expense_comparison(expense_ratio, benchmark, medians):
    if expense_ratio is None or benchmark not in medians:
        return "费率比较: 数据不足"
    median_ratio = medians[benchmark]
    if expense_ratio < median_ratio:
        label = "低于同组中位数"
    elif expense_ratio > median_ratio:
        label = "高于同组中位数"
    else:
        label = "等于同组中位数"
    return f"费率比较: {label} {_format_ratio(median_ratio)}"


def _dividend_status(profile):
    last_date = profile.get("last_dividend_date")
    dividend_policy = profile.get("dividend_policy")
    if last_date:
        return f"最近分红 {last_date}"
    if dividend_policy and dividend_policy != "未配置":
        return "缺少最近分红日期"
    return "未配置"


def _historical_tracking_error(profile):
    active_returns = []
    for item in profile.get("tracking_history", []) or []:
        etf_return = _safe_float(item.get("etf_return_pct"))
        benchmark_return = _safe_float(item.get("benchmark_return_pct"))
        if etf_return is not None and benchmark_return is not None:
            active_returns.append(etf_return - benchmark_return)
    if not active_returns:
        return None
    return sqrt(sum(value * value for value in active_returns) / len(active_returns))


def _dividend_summary(profile, price):
    history = profile.get("dividend_history", []) or []
    amounts = []
    for item in history:
        amount = _safe_float(item.get("amount"))
        if amount is not None and amount >= 0:
            amounts.append(amount)
    total = sum(amounts)
    yield_pct = total / price * 100 if price and total else None
    return len(amounts), yield_pct


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

    lines.extend(macro_indicator_lines(ak, settings, tracker))
    lines.append("- 宏观结论: 仅描述环境，不构成买卖信号。")
    lines.append("")
    return lines


def etf_observation(ak, settings, tracker, holdings):
    """Return markdown lines for ETF liquidity, premium/discount, and metadata observations."""
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

    gaps = []
    etf_settings = settings.get("etf_analysis", {}) or {}
    premium_warn = _safe_float(etf_settings.get("premium_discount_warn_pct", 0.5))
    premium_high = _safe_float(etf_settings.get("premium_discount_high_pct", 1.0))
    tracking_warn = _safe_float(etf_settings.get("tracking_error_warn", 0.005))
    tracking_high = _safe_float(etf_settings.get("tracking_error_high", 0.01))
    expense_medians = _expense_medians(holdings)
    for holding in holdings:
        code = holding.get("proxy_etf")
        if not code:
            continue
        profile = holding.get("etf_profile", {}) or {}
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
        reference_nav, nav_col = _first_value(
            item,
            ["IOPV", "基金份额参考净值", "参考净值", "单位净值", "估算净值", "净值"],
        )
        pd_pct = premium_discount(price, reference_nav)
        tier = liquidity_tier(amount)
        amount_text = f"{amount / 100000000:.2f}亿" if amount is not None else "N/A"
        price_text = f"{price:.3f}" if price is not None else "N/A"
        benchmark = profile.get("benchmark", "未配置")
        expense_ratio = _safe_float(profile.get("expense_ratio"))
        tracking_error = _safe_float(profile.get("tracking_error"))
        dividend_policy = profile.get("dividend_policy", "未配置")
        dividend_status = _dividend_status(profile)
        historical_tracking_error = _historical_tracking_error(profile)
        dividend_count, dividend_yield = _dividend_summary(profile, price)
        premium_risk = _risk_level(pd_pct, premium_warn, premium_high)
        tracking_risk = _risk_level(tracking_error, tracking_warn, tracking_high, use_abs=False)
        fee_comparison = _expense_comparison(expense_ratio, benchmark, expense_medians)
        premium_text = _format_pct(pd_pct) if pd_pct is not None else "数据不可用"
        nav_text = f"{reference_nav:.4f}({nav_col})" if reference_nav is not None else "N/A"
        historical_tracking_text = f"{historical_tracking_error:.2f}%" if historical_tracking_error is not None else "数据不足"
        dividend_yield_text = f"{dividend_yield:.2f}%" if dividend_yield is not None else "数据不足"
        lines.append(
            f"- {holding.get('name', code)} / {code}: 价格 {price_text} | 涨跌 {_format_pct(change_pct)} | 成交额 {amount_text} | 流动性 {tier}"
        )
        lines.append(
            f"  - 基准: {benchmark} | 费率: {_format_ratio(expense_ratio)} | 跟踪误差: {_format_ratio(tracking_error)} | 分红: {dividend_policy}"
        )
        lines.append(f"  - 溢价/折价: {premium_text} | 参考净值: {nav_text}")
        lines.append(
            f"  - {fee_comparison} | 溢价风险: {premium_risk} | 跟踪风险: {tracking_risk} | 分红状态: {dividend_status}"
        )
        lines.append(
            f"  - 历史跟踪误差: {historical_tracking_text} | 分红记录: {dividend_count} | 分红率: {dividend_yield_text}"
        )

        if benchmark == "未配置":
            gaps.append(f"{code}: benchmark")
        if expense_ratio is None:
            gaps.append(f"{code}: expense_ratio")
        if tracking_error is None:
            gaps.append(f"{code}: tracking_error")
        if historical_tracking_error is None:
            gaps.append(f"{code}: tracking_history")
        if dividend_policy == "未配置":
            gaps.append(f"{code}: dividend_policy")
        if dividend_count == 0:
            gaps.append(f"{code}: dividend_history")
        if dividend_status == "缺少最近分红日期":
            gaps.append(f"{code}: last_dividend_date")
        if pd_pct is None:
            gaps.append(f"{code}: premium_discount_source")

    if gaps:
        lines.append(f"- 待补ETF数据: {', '.join(gaps[:10])}")
    else:
        lines.append("- ETF数据完整度: 当前基础字段齐全。")
    lines.append("- ETF结论: 以上为结构化观察，不构成买卖信号。")
    lines.append("")
    return lines
