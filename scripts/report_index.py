#!/usr/bin/env python3
"""Inspect archived finance-agent report index without printing private report bodies."""

import json
from pathlib import Path

from common.config_loader import load_settings, resolve_path


def load_report_index(index_path):
    path = Path(index_path)
    if not path.exists():
        return []
    items = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if item.get("event") == "report_written":
                items.append(item)
    return items


def load_index(limit=10):
    settings = load_settings()
    index_path = resolve_path(settings.get("report_index_path", "reports/index.jsonl"))
    return index_path, load_report_index(index_path)[-limit:]


def _empty_quality():
    return {
        "fresh": 0,
        "stale": 0,
        "unknown": 0,
        "source_tiers": {},
    }


def summarize_reports(items):
    summary = {
        "report_count": len(items),
        "by_type": {},
        "module_counts": {"success": 0, "failed": 0, "skipped": 0, "cache_hit": 0},
        "failed_modules": {},
        "data_quality": _empty_quality(),
    }
    for item in items:
        report_type = item.get("report_type", "unknown")
        summary["by_type"][report_type] = summary["by_type"].get(report_type, 0) + 1
        run_summary = item.get("run_summary", {})
        modules = run_summary.get("modules", {})
        for key in summary["module_counts"]:
            summary["module_counts"][key] += int(modules.get(key, 0) or 0)

        quality = run_summary.get("data_quality", {})
        for key in ("fresh", "stale", "unknown"):
            summary["data_quality"][key] += int(quality.get(key, 0) or 0)
        for tier, count in quality.get("source_tiers", {}).items():
            tiers = summary["data_quality"]["source_tiers"]
            tiers[tier] = tiers.get(tier, 0) + int(count or 0)

        for module in run_summary.get("data_modules", []):
            if module.get("status") == "failed":
                name = module.get("module", "unknown")
                summary["failed_modules"][name] = summary["failed_modules"].get(name, 0) + 1
    return summary


def _format_counts(counts):
    return " ".join(f"{key}={counts[key]}" for key in sorted(counts))


def format_report_index(items, limit=5):
    summary = summarize_reports(items)
    lines = ["# Report Index Summary", ""]
    lines.append(f"- Reports: {summary['report_count']}")
    if summary["by_type"]:
        lines.append(f"- By type: {_format_counts(summary['by_type'])}")
    modules = summary["module_counts"]
    lines.append(
        "- Modules: "
        f"success={modules['success']} failed={modules['failed']} "
        f"skipped={modules['skipped']} cache_hit={modules['cache_hit']}"
    )
    quality = summary["data_quality"]
    lines.append(
        "- Data quality: "
        f"fresh={quality['fresh']} stale={quality['stale']} unknown={quality['unknown']}"
    )
    if quality["source_tiers"]:
        lines.append(f"- Source tiers: {_format_counts(quality['source_tiers'])}")
    if summary["failed_modules"]:
        for name, count in sorted(summary["failed_modules"].items()):
            lines.append(f"- Failed module: {name} x{count}")
    else:
        lines.append("- Failed modules: none")

    lines.append("")
    lines.append("## Recent Reports")
    recent = sorted(items, key=lambda item: item.get("created_at", ""), reverse=True)[:limit]
    if not recent:
        lines.append("- No archived reports found.")
    for item in recent:
        modules = item.get("run_summary", {}).get("modules", {})
        lines.append(
            f"- {item.get('created_at', 'unknown')} | {item.get('report_type', 'unknown')} "
            f"| failed={modules.get('failed', 0)} | skipped={modules.get('skipped', 0)} "
            f"| {item.get('report_path', '')}"
        )
    return "\n".join(lines)


def main():
    settings = load_settings()
    index_path = resolve_path(settings.get("report_index_path", "reports/index.jsonl"))
    print(format_report_index(load_report_index(index_path)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
