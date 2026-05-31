#!/usr/bin/env python3
"""Offline foundation checks for the local finance agent."""

import json
import pathlib
import re
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]


def _pass(message):
    print(f"PASS {message}")


def _fail(message):
    print(f"FAIL {message}")
    return message


def _read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def _json(path):
    return json.loads(_read(path))


def check_foundation_files():
    failures = []
    required = [
        "AGENTS.md",
        ".env.example",
        ".gitignore",
        "requirements.txt",
        "config/settings.example.json",
        "schemas/portfolio.schema.json",
        "data/examples/portfolio.example.json",
        "docs/LOCAL_SETUP.md",
        "docs/SECURITY_AND_BOUNDARIES.md",
        "docs/ROADMAP.md",
        "scripts/common/config_loader.py",
        "scripts/common/data_runtime.py",
        "scripts/common/dependencies.py",
        "scripts/common/reporting.py",
        "scripts/validate_portfolio.py",
        "scripts/mock_dependency_test.py",
        "scripts/mock_daily_status_test.py",
        "scripts/mock_reporting_test.py",
        "scripts/mock_runtime_test.py",
    ]
    for path in required:
        if (ROOT / path).exists():
            _pass(f"{path} exists")
        else:
            failures.append(_fail(f"{path} missing"))
    return failures


def check_json_files():
    failures = []
    for path in [
        "config/settings.example.json",
        "schemas/portfolio.schema.json",
        "data/examples/portfolio.example.json",
    ]:
        try:
            _json(path)
            _pass(f"{path} is valid JSON")
        except Exception as exc:
            failures.append(_fail(f"{path} invalid JSON: {type(exc).__name__}"))
    return failures


def check_sensitive_patterns():
    failures = []
    script_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (ROOT / "scripts").glob("*.py")
        if path.name != "smoke_test.py"
    )
    openclaw_pattern = "~/.open" + "claw"
    tavily_prefix = "tvly" + "-"
    if openclaw_pattern in script_text:
        failures.append(_fail("scripts must not hardcode OpenClaw workspace paths"))
    else:
        _pass("scripts do not hardcode OpenClaw workspace paths")
    if tavily_prefix in script_text:
        failures.append(_fail("scripts must not hardcode Tavily key values"))
    else:
        _pass("scripts do not hardcode Tavily key values")
    if re.search(r"TAVILY_API_KEY\s*=\s*['\"]", script_text):
        failures.append(_fail("scripts must not assign literal TAVILY_API_KEY values"))
    else:
        _pass("scripts do not assign literal TAVILY_API_KEY values")
    return failures


def main():
    failures = []
    failures.extend(check_foundation_files())
    failures.extend(check_json_files())
    failures.extend(check_sensitive_patterns())
    if failures:
        print("")
        print(f"Smoke test failed: {len(failures)} issue(s)")
        return 1
    print("")
    print("Smoke test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
