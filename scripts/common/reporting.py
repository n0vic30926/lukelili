#!/usr/bin/env python3
"""Shared report archive and structured log helpers."""

import json
from datetime import datetime

from common.config_loader import get_report_dirs


def write_report(report_type, report, settings, tracker=None):
    """Write a markdown report, append index metadata, and write JSONL logs."""
    dirs = get_report_dirs(settings)
    out_key = "daily_report_dir" if report_type == "daily" else "weekly_report_dir"
    out_dir = dirs[out_key]
    log_dir = dirs["log_dir"]
    report_output_dir = dirs["report_output_dir"]
    out_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    report_output_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now()
    report_path = out_dir / f"{report_type}-{now.strftime('%Y-%m-%d')}.md"
    report_path.write_text(report, encoding="utf-8")

    meta = {
        "type": report_type,
        "path": str(report_path),
        "created_at": now.isoformat(timespec="seconds"),
        "status_counts": tracker.counts() if tracker else {},
    }

    with (report_output_dir / "index.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(meta, ensure_ascii=False) + "\n")

    with (log_dir / "finance-agent.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps({**meta, "events": tracker.records if tracker else []}, ensure_ascii=False) + "\n")

    return report_path
