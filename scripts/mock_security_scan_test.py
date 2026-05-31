#!/usr/bin/env python3
"""Offline tests for tracked-file sensitive information scanning."""

import tempfile
from pathlib import Path

from security_scan import format_findings, scan_paths


def _assert_contains(text, expected):
    if expected not in text:
        raise AssertionError(f"Expected text to contain: {expected}")


def _assert_not_contains(text, unexpected):
    if unexpected in text:
        raise AssertionError(f"Text should not contain sensitive value: {unexpected}")


def run_security_scan_test():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        risky = root / "README.md"
        tavily_value = "tvly" + "-SECRET-123"
        tavily_env = "TAVILY" + "_API_KEY"
        risky.write_text(
            "\n".join(
                [
                    f"{tavily_env} = '{tavily_value}'",
                    "## Luke 当前持仓",
                    "- **123456** Example Fund（日定投5000，30万预算）",
                ]
            ),
            encoding="utf-8",
        )
        clean = root / "data" / "examples" / "portfolio.example.json"
        clean.parent.mkdir(parents=True)
        clean.write_text('{"code": "000000", "name": "Example Fund"}', encoding="utf-8")

        findings = scan_paths([risky, clean], root=root)
        risk_types = {finding["risk_type"] for finding in findings}
        if "api_key" not in risk_types:
            raise AssertionError(f"Expected api_key finding: {findings}")
        if "private_portfolio_detail" not in risk_types:
            raise AssertionError(f"Expected private portfolio finding: {findings}")

        output = format_findings(findings)
        _assert_contains(output, "README.md")
        _assert_contains(output, "api_key")
        _assert_contains(output, "private_portfolio_detail")
        _assert_not_contains(output, tavily_value)
        _assert_not_contains(output, "123456")
        _assert_not_contains(output, "5000")


def main():
    run_security_scan_test()
    print("Mock security scan test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
