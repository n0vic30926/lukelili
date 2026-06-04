#!/usr/bin/env python3
"""Audit configured market data adapters without calling external data APIs."""

import argparse
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


def _fed_calendar_issues(settings):
    issues = []
    calendar = settings.get("fed_policy_calendar")
    if not isinstance(calendar, dict):
        return ["fed_policy_calendar"]
    if not calendar.get("source"):
        issues.append("source")
    if not calendar.get("source_tier"):
        issues.append("source_tier")
    events = calendar.get("events")
    if not isinstance(events, list):
        issues.append("events")
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


def _sample_columns(sample):
    if hasattr(sample, "columns"):
        return [str(column) for column in sample.columns]
    if isinstance(sample, list):
        if not sample:
            return []
        first_row = sample[0]
        if isinstance(first_row, dict):
            return [str(column) for column in first_row.keys()]
        return []
    if isinstance(sample, dict):
        return [str(column) for column in sample.keys()]
    return []


def _macro_schema_result(ak_module, indicator, available_functions):
    if ak_module is None:
        return {"status": "not_checked", "issues": [], "function": None}
    if not available_functions:
        return {"status": "not_checked", "issues": [], "function": None}

    function_name = available_functions[0]
    adapter = getattr(ak_module, function_name)
    try:
        columns = _sample_columns(adapter())
    except Exception as exc:
        return {
            "status": "schema_error",
            "issues": [type(exc).__name__],
            "function": function_name,
        }

    issues = []
    date_columns = _list_value(indicator.get("date_columns"))
    value_columns = _list_value(indicator.get("value_columns"))
    if not any(column in columns for column in date_columns):
        issues.append("missing_date_column")
    if not any(column in columns for column in value_columns):
        issues.append("missing_value_column")
    return {
        "status": "schema_issue" if issues else "ok",
        "issues": issues,
        "function": function_name,
    }


def audit_settings(settings, ak_module=None, dependency_status=None, check_output_schema=False):
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
        schema = {"status": "not_checked", "issues": [], "function": None}
        if check_output_schema and not issues and available:
            schema = _macro_schema_result(ak_module, indicator, available)
            if schema["status"] in ("schema_issue", "schema_error"):
                status = schema["status"]
        macro_results.append(
            {
                "id": indicator.get("id", "unknown"),
                "label": indicator.get("label", indicator.get("id", "unknown")),
                "status": status,
                "issues": issues,
                "schema": schema,
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
        "fed_policy_calendar": {
            "status": "config_issue" if _fed_calendar_issues(settings) else "ok",
            "issues": _fed_calendar_issues(settings),
        },
        "macro_adapters": macro_results,
        "etf_adapters": etf_results,
    }


def format_audit(audit):
    lines = ["# 数据 Adapter 离线审计", ""]
    lines.append(f"- AkShare dependency: {audit['akshare_dependency']}")
    lines.append("- 审计边界: 默认只检查本地配置和函数符号存在性；schema 检查必须显式开启。")
    fed = audit["fed_policy_calendar"]
    fed_line = f"- Fed policy calendar: status={fed['status']}"
    if fed["issues"]:
        fed_line += f" | issues={','.join(fed['issues'])}"
    lines.append(fed_line)
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
        schema = item.get("schema", {})
        if schema.get("status") and schema["status"] != "not_checked":
            parts.append(f"schema={schema['status']}")
        if schema.get("function"):
            parts.append(f"schema_function={schema['function']}")
        if schema.get("issues"):
            parts.append(f"schema_issues={','.join(schema['issues'])}")
        lines.append("- " + " | ".join(parts))
    lines.append("")
    lines.append("## ETF/市场 Adapter")
    for item in audit["etf_adapters"]:
        lines.append(f"- ETF adapter: {item['label']} | function={item['function']} | status={item['status']}")
    return lines


def main():
    parser = argparse.ArgumentParser(description="Audit configured finance-agent data adapters.")
    parser.add_argument(
        "--check-output-schema",
        action="store_true",
        help="Call available macro adapter functions and validate configured date/value columns.",
    )
    args = parser.parse_args()
    settings = load_settings()
    print("\n".join(format_audit(audit_settings(settings, check_output_schema=args.check_output_schema))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
