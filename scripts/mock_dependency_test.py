#!/usr/bin/env python3
"""Offline dependency behavior tests for report entrypoints."""

import importlib.util
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _assert_contains(text, expected):
    if expected not in text:
        raise AssertionError(f"Expected output to contain: {expected}")


def _assert_not_contains(text, unexpected):
    if unexpected in text:
        raise AssertionError(f"Output should not contain: {unexpected}")


def run_missing_akshare_entrypoint_test():
    if importlib.util.find_spec("akshare") is not None:
        print("Skipping missing-akshare entrypoint test because akshare is installed")
        return

    for script in ["daily_finance_brief.py", "weekly_finance_review.py"]:
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / script)],
            cwd=str(ROOT),
            text=True,
            capture_output=True,
            timeout=10,
        )
        output = result.stdout + result.stderr
        if result.returncode == 0:
            raise AssertionError(f"{script} should exit non-zero when akshare is missing")
        _assert_contains(output, "Missing required runtime dependencies")
        _assert_contains(output, "akshare")
        _assert_contains(output, "python3 -m pip install -r requirements.txt")
        _assert_not_contains(output, "Traceback")


def main():
    run_missing_akshare_entrypoint_test()
    print("Mock dependency test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
