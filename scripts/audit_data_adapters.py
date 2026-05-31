#!/usr/bin/env python3
"""Audit configured market data adapters without calling external data APIs."""

import importlib

from common.config_loader import load_settings


ETF_ADAPTERS = [
    ("ETF行情", "fund_etf_spot_em"),
    ("美股指数", "index_us_stock_sina"),
    ("即期汇率", "fx_spot_quote"),
    ("人民币中间价", "currency_boc_safe"),
    ("北向资金", "stock_hsgt_fund_flow_summary_em"),
    ("基金持仓", "fund_portfolio_hold_em"),
    ("中美国债利率", "bond_zh_us_rate"),
]


def _load_akshare():
    try:
        return importlib.import_module("akshare"), "available"
    except ImportError:
        return None, "missing"


def _list_value(value):
    return value if isinstance(value, list) else []


def _macro_config_issues(indicator):
    issues = []
    if not indicator.get("id"):
        issues.append("id")
    if not indicator.get("label"):
        issues.append("label")
    if not _list_value(indicator.get("candidate_functions")):
        issues.append("candidate_functions")
    if not _list_value(indicator.get("date_columns")):
        issues.append("date_columns")
    if not _list_value(indicator.get("value_columns")):
        issues.append("value_columns")
    if not indicator.get("cadence"):
        issues.append("cadence")
    if indicator.get("max_age_days") is None:
        issues.append("max_age_days")
    calendar = indicator.get("release_calendar")
    if not isinstance(calendar, dict):
        issues.append("release_calendar")
    else:
        if not calendar.get("source"):
            issues.append("release_calendar.source")
        if not calendar.get("source_tier"):
            issues.append("release_calendar.source_tier")
    return issues


def _available_functions(ak_module, function_names):
    if ak_module is None:
        return [], list(function_names)
    available = []
    missing = []
    for name in function_names:
        if callable(getattr(ak_module, name, None)):
            available.append(name)
        else:
            missing.append(name)
    return available, missing


def audit_settings(settings, ak_module=None, dependency_status=None):
    """Return adapter audit data using only local settings and symbol inspection."""
    if ak_module is None and dependency_status is None:
        ak_module, dependency_status = _load_akshare()
    elif dependency_status is None:
        dependency_status = "injected"

    macro_results = []
    for indicator in settings.get("macro_indicators", []):
        candidates = _list_value(indicator.get("candidate_functions"))
        issues = _macro_config_issues(indicator)
        available, missing = _available_functions(ak_module, candidates)
        if issues:
            status = "config_issue"
        elif ak_module is None:
            status = "dependency_missing"
        elif available:
            status = "ok"
        else:
            status = "function_missing"
        macro_results.append(
            {
                "id": indicator.get("id", "unknown"),
                "label": indicator.get("label", indicator.get("id", "unknown")),
                "status": status,
                "issues": issues,
                "available_functions": available,
                "missing_functions": missing,
                "candidate_functions": candidates,
            }
        )

    etf_results = []
    for label, function_name in ETF_ADAPTERS:
        available, _ = _available_functions(ak_module, [function_name])
        if ak_module is None:
            status = "dependency_missing"
        elif available:
            status = "ok"
        else:
            status = "function_missing"
        etf_results.append({"label": label, "function": function_name, "status": status})

    return {
        "akshare_dependency": dependency_status,
        "macro_adapters": macro_results,
        "etf_adapters": etf_results,
    }


def format_audit(audit):
    lines = ["# 数据 Adapter 离线审计", ""]
    lines.append(f"- AkShare dependency: {audit['akshare_dependency']}")
    lines.append("- 审计边界: 只检查本地配置和函数符号存在性，不联网、不调用行情接口。")
    lines.append("")
    lines.append("## 宏观 Adapter")
    if not audit["macro_adapters"]:
        lines.append("- 未配置 macro_indicators。")
    for item in audit["macro_adapters"]:
        parts = [f"宏观 adapter: {item['label']}", f"status={item['status']}"]
        if item["available_functions"]:
            parts.append(f"available={','.join(item['available_functions'])}")
        if item["missing_functions"]:
            parts.append(f"missing={','.join(item['missing_functions'])}")
        if item["issues"]:
            parts.append(f"issues={','.join(item['issues'])}")
        lines.append("- " + " | ".join(parts))
    lines.append("")
    lines.append("## ETF/市场 Adapter")
    for item in audit["etf_adapters"]:
        lines.append(f"- ETF adapter: {item['label']} | function={item['function']} | status={item['status']}")
    return lines


def main():
    settings = load_settings()
    print("\n".join(format_audit(audit_settings(settings))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
