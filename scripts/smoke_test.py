#!/usr/bin/env python3
"""Smoke test for the finance-agent local foundation."""

import json
import os
import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from common.config_loader import get_portfolio_path, get_report_dirs, load_settings
from common.data_runtime import missing_dependencies
from validate_portfolio import validate_portfolio_file


CORE_SCRIPTS = [
    REPO_ROOT / "scripts" / "daily_finance_brief.py",
    REPO_ROOT / "scripts" / "weekly_finance_review.py",
    REPO_ROOT / "scripts" / "qdii_three_factor.py",
    REPO_ROOT / "scripts" / "decision_tracker.py",
    REPO_ROOT / "scripts" / "industry_intel.py",
    REPO_ROOT / "scripts" / "industry_cycle.py",
]

OPENCLAW_WORKSPACE_PATTERN = "~/.open" + "claw/workspace"
TAVILY_KEY_PREFIX_PATTERN = "tvly" + "-"


def check(condition, message):
    if condition:
        print(f"PASS {message}")
        return True
    print(f"FAIL {message}")
    return False


def file_contains(path, pattern):
    text = path.read_text(encoding="utf-8")
    return re.search(pattern, text) is not None


def main():
    failures = 0

    required_files = [
        "AGENTS.md",
        ".env.example",
        "config/settings.example.json",
        "schemas/portfolio.schema.json",
        "data/examples/portfolio.example.json",
        "scripts/common/config_loader.py",
    ]
    for rel in required_files:
        failures += not check((REPO_ROOT / rel).exists(), f"{rel} exists")

    settings = load_settings()
    failures += not check(isinstance(settings, dict), "settings load as JSON object")

    missing = missing_dependencies(["akshare", "pandas", "numpy", "requests"])
    if missing:
        print(f"WARN missing optional runtime dependencies: {', '.join(missing)}")
        print("WARN install manually with: python3 -m pip install -r requirements.txt")
    failures += not check(True, "dependency check is non-fatal")

    portfolio_path, using_example = get_portfolio_path(settings)
    failures += not check(portfolio_path.exists(), "portfolio path resolves")
    with portfolio_path.open(encoding="utf-8") as f:
        portfolio = json.load(f)
    failures += not check("holdings" in portfolio, "portfolio JSON can be read")
    example_errors = validate_portfolio_file(REPO_ROOT / "data/examples/portfolio.example.json")
    failures += not check(not example_errors, "example portfolio validates")
    if not using_example:
        real_errors = validate_portfolio_file(portfolio_path)
        failures += not check(not real_errors, "configured portfolio validates without printing asset details")

    joined_core = "\n".join(p.read_text(encoding="utf-8") for p in CORE_SCRIPTS)
    failures += not check(OPENCLAW_WORKSPACE_PATTERN not in joined_core, "core scripts do not hardcode OpenClaw workspace")
    failures += not check(TAVILY_KEY_PREFIX_PATTERN not in joined_core, "core scripts do not hardcode Tavily key value")
    failures += not check(
        not any(file_contains(p, r"TAVILY_API_KEY\s*=\s*['\"]") for p in CORE_SCRIPTS),
        "core scripts do not hardcode TAVILY_API_KEY assignment",
    )

    dirs = get_report_dirs(settings)
    for name, path in dirs.items():
        failures += not check(path is not None and not str(path).startswith("/Users/luke/.openclaw"), f"{name} resolves outside OpenClaw")
        try:
            path.mkdir(parents=True, exist_ok=True)
            creatable = path.exists()
        except OSError:
            creatable = False
        failures += not check(creatable, f"{name} can be created")

    key_env = settings.get("tavily_api_key_env", "TAVILY_API_KEY")
    news_requires_missing_key = bool(settings.get("enable_news")) and not os.environ.get(key_env)
    failures += not check(not news_requires_missing_key, "runtime does not require real Tavily key")
    failures += not check(using_example or portfolio_path.exists(), "runtime can use local or example portfolio")
    failures += not check("openclaw" not in str(portfolio_path).lower(), "portfolio path does not touch OpenClaw")

    if failures:
        print(f"\nSmoke test failed: {failures} check(s).")
        return 1
    print("\nSmoke test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
