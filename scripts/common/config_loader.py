"""Local configuration helpers for finance-agent scripts."""

import json
import os
from pathlib import Path


def get_repo_root():
    return Path(__file__).resolve().parents[2]


def resolve_path(path_value):
    path = Path(path_value).expanduser()
    if path.is_absolute():
        return path
    return get_repo_root() / path


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
                return json.load(f)
    raise FileNotFoundError("No finance-agent settings file found")


def get_portfolio_path(settings=None, prefer_example=False):
    settings = settings or load_settings()
    if prefer_example:
        return resolve_path(settings["example_portfolio_path"])
    private_path = resolve_path(settings["portfolio_path"])
    if private_path.exists():
        return private_path
    return resolve_path(settings["example_portfolio_path"])


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
