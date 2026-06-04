"""Local configuration helpers for finance-agent scripts."""

import json
import os
import copy
from pathlib import Path


def get_repo_root():
    return Path(__file__).resolve().parents[2]


def resolve_path(path_value, base_dir=None):
    if path_value is None:
        return None
    path = Path(path_value).expanduser()
    if path.is_absolute():
        return path
    return (base_dir or get_repo_root()) / path


def load_settings():
    root = get_repo_root()
    configured = os.environ.get("FINANCE_AGENT_CONFIG")
    candidates = []
    if configured:
        candidates.append(resolve_path(configured))
    candidates.append(root / "config" / "settings.local.json")
    candidates.append(root / "config" / "settings.example.json")
    for path in candidates:
        if path.exists():
            with path.open(encoding="utf-8") as f:
                settings = json.load(f)
            settings["_settings_path"] = str(path)
            return settings
    raise FileNotFoundError("No finance-agent settings file found")


def get_portfolio_path(settings=None, prefer_example=False):
    settings = settings or load_settings()
    if prefer_example:
        return resolve_path(settings["example_portfolio_path"])
    private_path = resolve_path(settings["portfolio_path"])
    if private_path.exists():
        return private_path
    return resolve_path(settings["example_portfolio_path"])


def get_portfolio_path_with_flag(settings=None):
    settings = settings or load_settings()
    private_path = resolve_path(settings.get("portfolio_path"))
    if private_path and private_path.exists():
        return private_path, False
    return resolve_path(settings["example_portfolio_path"]), True


def get_portfolio_overlay_path(settings=None):
    settings = settings or load_settings()
    return resolve_path(settings.get("portfolio_overlay_path"))


def _read_json(path):
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _merge_dict(base, updates):
    merged = dict(base or {})
    for key, value in (updates or {}).items():
        if value is None:
            continue
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_dict(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def apply_portfolio_overlay(portfolio, overlay):
    """Apply a local private overlay without mutating the original portfolio."""
    result = copy.deepcopy(portfolio)
    if not isinstance(overlay, dict):
        return result
    if overlay.get("enabled") is not True:
        result.setdefault("data_status", {})["overlay_applied"] = False
        return result

    for key in ["user_profile", "cash", "risk_rules", "data_status"]:
        if isinstance(overlay.get(key), dict):
            result[key] = _merge_dict(result.get(key), overlay[key])

    holdings_by_code = overlay.get("holdings_by_code") or {}
    if holdings_by_code:
        for holding in result.get("holdings", []) or []:
            code = str(holding.get("code") or "")
            updates = holdings_by_code.get(code)
            if isinstance(updates, dict):
                holding.update(_merge_dict(holding, updates))

    appends = overlay.get("append_buy_records_by_code") or {}
    if appends:
        for holding in result.get("holdings", []) or []:
            code = str(holding.get("code") or "")
            records = appends.get(code)
            if isinstance(records, list):
                holding.setdefault("buy_records", [])
                holding["buy_records"].extend(copy.deepcopy(records))

    metadata = result.setdefault("data_status", {})
    metadata["overlay_applied"] = True
    return result


def load_portfolio(settings=None, prefer_example=False, apply_overlay=True):
    settings = settings or load_settings()
    path, using_example = (
        (resolve_path(settings["example_portfolio_path"]), True)
        if prefer_example
        else get_portfolio_path_with_flag(settings)
    )
    portfolio = _read_json(path)
    overlay_path = get_portfolio_overlay_path(settings)
    overlay_applied = False
    if apply_overlay and not using_example and overlay_path and overlay_path.exists():
        portfolio = apply_portfolio_overlay(portfolio, _read_json(overlay_path))
        overlay_applied = True
        portfolio.setdefault("data_status", {})["overlay_path"] = str(overlay_path)
    return portfolio, path, using_example, overlay_applied


def get_report_dirs(settings=None):
    settings = settings or load_settings()
    report_output_dir = resolve_path(settings.get("report_output_dir", "reports"))
    return {
        "report_output_dir": report_output_dir,
        "daily_report_dir": resolve_path(settings.get("daily_report_dir", "reports/daily")),
        "weekly_report_dir": resolve_path(settings.get("weekly_report_dir", "reports/weekly")),
        "cache_dir": resolve_path(settings.get("cache_dir", "cache")),
        "log_dir": resolve_path(settings.get("log_dir", "logs")),
    }


def get_decision_track_dir(settings=None):
    settings = settings or load_settings()
    return resolve_path(settings["decision_track_dir"])


def get_scenario_assumptions_path(settings=None, prefer_example=False):
    settings = settings or load_settings()
    if prefer_example:
        return resolve_path(settings["example_scenario_assumptions_path"])
    private_path = resolve_path(settings["scenario_assumptions_path"])
    if private_path.exists():
        return private_path
    return resolve_path(settings["example_scenario_assumptions_path"])


def get_tavily_api_key(settings=None):
    settings = settings or load_settings()
    env_name = settings.get("tavily_api_key_env", "TAVILY_API_KEY")
    return os.environ.get(env_name, "")


def news_enabled(settings=None):
    settings = settings or load_settings()
    return bool(settings.get("enable_news")) and bool(get_tavily_api_key(settings))
