#!/usr/bin/env python3
"""Scan tracked text files for sensitive local finance-agent data."""

import re
import subprocess
from pathlib import Path


TAVILY_PREFIX = "tvly" + "-"
TAVILY_ENV_NAME = "TAVILY" + "_API_KEY"
OPENCLAW_PATH = "~/.open" + "claw"

API_KEY_RE = re.compile(
    rf"({TAVILY_PREFIX}[A-Za-z0-9_-]+|{TAVILY_ENV_NAME}\s*=\s*['\"][^'\"]+)"
)
OPENCLAW_RE = re.compile(re.escape(OPENCLAW_PATH))
PRIVATE_PORTFOLIO_RE = re.compile(
    r"(Luke\s*当前持仓|当前持仓映射|"
    r"\b\d{6}\b.*(日定投|预算|成本|份额|持仓|试水仓)|"
    r"['\"]?(cost_basis|shares)['\"]?\s*[:=]\s*[1-9]\d+)"
)

DEFAULT_EXCLUDED_PARTS = {
    ".git",
    "data/examples",
    "schemas",
    "scripts",
}


def _relative(path, root):
    try:
        return str(Path(path).resolve().relative_to(Path(root).resolve()))
    except ValueError:
        return str(path)


def _is_text_file(path):
    return path.suffix.lower() in {
        "",
        ".env",
        ".json",
        ".md",
        ".py",
        ".txt",
        ".yaml",
        ".yml",
    }


def _is_excluded(relative_path):
    if relative_path == ".env.example":
        return False
    return any(relative_path == part or relative_path.startswith(f"{part}/") for part in DEFAULT_EXCLUDED_PARTS)


def tracked_paths(root):
    try:
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=root,
            text=True,
            capture_output=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return []
    return [Path(root) / line for line in result.stdout.splitlines() if line.strip()]


def scan_paths(paths, root=None):
    root = Path(root or Path.cwd())
    findings = []
    for path in paths:
        path = Path(path)
        relative_path = _relative(path, root)
        if _is_excluded(relative_path) or not _is_text_file(path):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        checks = [
            ("api_key", "TAVILY_API_KEY", API_KEY_RE),
            ("openclaw_path", "workspace_path", OPENCLAW_RE),
            ("private_portfolio_detail", "portfolio_detail", PRIVATE_PORTFOLIO_RE),
        ]
        for risk_type, field_name, pattern in checks:
            if pattern.search(text):
                findings.append(
                    {
                        "path": relative_path,
                        "field_name": field_name,
                        "risk_type": risk_type,
                    }
                )
    return findings


def format_findings(findings):
    if not findings:
        return "No sensitive tracked-file findings."
    lines = ["Sensitive tracked-file findings:"]
    for finding in findings:
        lines.append(
            "- "
            f"path={finding['path']} "
            f"field={finding['field_name']} "
            f"risk={finding['risk_type']}"
        )
    return "\n".join(lines)


def main():
    root = Path(__file__).resolve().parents[1]
    findings = scan_paths(tracked_paths(root), root=root)
    print(format_findings(findings))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
