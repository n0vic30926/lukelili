"""Report archiving and structured runtime logging."""

import json
from datetime import datetime
from pathlib import Path

from common.config_loader import load_settings, resolve_path
from common.report_source_interpretation import interpret_data_module


def _now_iso():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _date_from_created_at(created_at):
    return created_at[:10]


def _json_default(value):
    return str(value)


def _write_jsonl(path, item):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(item, ensure_ascii=False, default=_json_default) + "\n")


def _report_dir(settings, report_type):
    if report_type == "daily":
        return resolve_path(settings["daily_report_dir"])
    if report_type == "weekly":
        return resolve_path(settings["weekly_report_dir"])
    raise ValueError(f"Unsupported report_type: {report_type}")


def _report_index_path(settings):
    return resolve_path(settings.get("report_index_path", "reports/index.jsonl"))


def _log_path(settings):
    return resolve_path(settings.get("log_dir", "logs")) / "finance-agent.jsonl"


def format_run_summary(run_summary):
    lines = ["## 运行摘要", ""]
    if not run_summary:
        lines.append("- status: generated")
        lines.append("")
        return "\n".join(lines)

    for key in sorted(run_summary):
        value = run_summary[key]
        if isinstance(value, bool):
            lines.append(f"- {key}: {str(value).lower()}")
        elif isinstance(value, dict) and key == "modules":
            lines.append(
                "- modules: "
                f"success={value.get('success', 0)} "
                f"failed={value.get('failed', 0)} "
                f"skipped={value.get('skipped', 0)} "
                f"cache_hit={value.get('cache_hit', 0)}"
            )
        elif isinstance(value, dict) and key == "data_quality":
            lines.append(
                "- data_quality: "
                f"fresh={value.get('fresh', 0)} "
                f"stale={value.get('stale', 0)} "
                f"unknown={value.get('unknown', 0)}"
            )
            tiers = value.get("source_tiers", {})
            if tiers:
                rendered = " ".join(f"{k}={tiers[k]}" for k in sorted(tiers))
                lines.append(f"- source_tiers: {rendered}")
        elif isinstance(value, list) and key == "data_modules":
            for item in value:
                parts = [
                    f"data_module: {item.get('module', 'unknown')}",
                    f"status={item.get('status', 'unknown')}",
                ]
                if item.get("source"):
                    parts.append(f"source={item['source']}")
                if item.get("source_tier"):
                    parts.append(f"source_tier={item['source_tier']}")
                if item.get("freshness"):
                    parts.append(f"freshness={item['freshness']}")
                if item.get("error_type"):
                    parts.append(f"error_type={item['error_type']}")
                if item.get("reason"):
                    parts.append(f"reason={item['reason']}")
                if item.get("detail"):
                    parts.append(f"detail={item['detail']}")
                lines.append("- " + " | ".join(parts))
                lines.append(f"- source_interpretation: {interpret_data_module(item)}")
        elif isinstance(value, dict):
            rendered = ", ".join(f"{k}={v}" for k, v in sorted(value.items()))
            lines.append(f"- {key}: {rendered}")
        else:
            lines.append(f"- {key}: {value}")
    lines.append("")
    return "\n".join(lines)


def with_run_summary(content, run_summary):
    return f"{format_run_summary(run_summary)}---\n\n{content}"


def write_report(report_type, content, settings=None, run_summary=None, created_at=None):
    settings = settings or load_settings()
    created_at = created_at or _now_iso()
    report_date = _date_from_created_at(created_at)
    report_dir = _report_dir(settings, report_type)
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"{report_type}-{report_date}.md"
    archived_content = with_run_summary(content, run_summary or {})
    report_path.write_text(archived_content, encoding="utf-8")

    item = {
        "event": "report_written",
        "report_type": report_type,
        "created_at": created_at,
        "report_date": report_date,
        "report_path": str(report_path),
        "run_summary": run_summary or {},
    }
    _write_jsonl(_report_index_path(settings), item)
    _write_jsonl(_log_path(settings), item)
    return {
        "report_path": str(report_path),
        "content": archived_content,
        "index_path": str(_report_index_path(settings)),
        "log_path": str(_log_path(settings)),
    }
