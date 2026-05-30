#!/usr/bin/env python3
"""Shared JSON settings loader for finance-agent scripts."""

import json
import os
from pathlib import Path


DEFAULT_LOCAL_CONFIG = "config/settings.local.json"
DEFAULT_EXAMPLE_CONFIG = "config/settings.example.json"


class SettingsError(RuntimeError):
    """Raised when settings exist but cannot be parsed."""


def get_repo_root():
    """Return the repository root as a Path."""
    return Path(__file__).resolve().parents[2]


def resolve_path(path_value, base_dir=None):
    """Resolve a settings path relative to the repo root."""
    if path_value is None:
        return None
    path = Path(os.path.expanduser(str(path_value)))
    if path.is_absolute():
        return path
    return (base_dir or get_repo_root()) / path


def _candidate_config_paths():
    root = get_repo_root()
    env_path = os.environ.get("FINANCE_AGENT_CONFIG")
    if env_path:
        yield resolve_path(env_path, root)
    yield root / DEFAULT_LOCAL_CONFIG
    yield root / DEFAULT_EXAMPLE_CONFIG


def load_settings():
    """Load settings from env-selected, local, or example JSON config."""
    tried = []
    for path in _candidate_config_paths():
        if path in tried:
            continue
        tried.append(path)
        if not path.exists():
            continue
        try:
            with path.open(encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as exc:
            raise SettingsError(
                f"Failed to parse settings file {path}: {exc}. "
                "Create a valid config/settings.local.json from config/settings.example.json."
            ) from exc
        if not isinstance(data, dict):
            raise SettingsError(
                f"Settings file {path} must contain a JSON object. "
                "Create config/settings.local.json from config/settings.example.json."
            )
        data["_settings_path"] = str(path)
        data["_using_example_settings"] = path.name == "settings.example.json"
        return data

    tried_text = ", ".join(str(p) for p in tried)
    raise SettingsError(
        "No settings file found. Copy config/settings.example.json to "
        f"config/settings.local.json or set FINANCE_AGENT_CONFIG. Tried: {tried_text}"
    )


def get_portfolio_path(settings=None):
    """Return the preferred portfolio path and whether it is example data."""
    settings = settings or load_settings()
    root = get_repo_root()
    portfolio_path = resolve_path(settings.get("portfolio_path"), root)
    if portfolio_path and portfolio_path.exists():
        return portfolio_path, False

    example_path = resolve_path(settings.get("example_portfolio_path"), root)
    if example_path and example_path.exists():
        return example_path, True

    fallback = root / "memory" / "portfolio.json"
    if fallback.exists():
        return fallback, False

    raise SettingsError(
        "No portfolio file found. Create data/private/portfolio.local.json "
        "or add data/examples/portfolio.example.json for smoke tests."
    )


def get_report_dirs(settings=None):
    """Return resolved report/cache/log directories from settings."""
    settings = settings or load_settings()
    root = get_repo_root()
    return {
        "report_output_dir": resolve_path(settings.get("report_output_dir", "reports"), root),
        "daily_report_dir": resolve_path(settings.get("daily_report_dir", "reports/daily"), root),
        "weekly_report_dir": resolve_path(settings.get("weekly_report_dir", "reports/weekly"), root),
        "cache_dir": resolve_path(settings.get("cache_dir", "cache"), root),
        "log_dir": resolve_path(settings.get("log_dir", "logs"), root),
    }


def get_tavily_api_key(settings=None):
    """Return Tavily API key from the configured environment variable."""
    settings = settings or load_settings()
    env_name = settings.get("tavily_api_key_env", "TAVILY_API_KEY")
    return os.environ.get(env_name, "")


def news_enabled(settings=None):
    """Return whether news collection is enabled and configured."""
    settings = settings or load_settings()
    return bool(settings.get("enable_news", False)) and bool(get_tavily_api_key(settings))
