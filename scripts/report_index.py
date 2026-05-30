#!/usr/bin/env python3
"""Inspect the local report archive index."""

import json
import sys

from common.config_loader import get_report_dirs, load_settings


def load_index(limit=10):
    settings = load_settings()
    index_path = get_report_dirs(settings)["report_output_dir"] / "index.jsonl"
    if not index_path.exists():
        return index_path, []

    records = []
    with index_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return index_path, records[-limit:]


def main(argv=None):
    argv = argv or sys.argv[1:]
    limit = int(argv[0]) if argv else 10
    index_path, records = load_index(limit=limit)
    if not records:
        print(f"No report index records found at {index_path}")
        return 0
    print(f"Latest {len(records)} report index record(s) from {index_path}:")
    for item in records:
        counts = item.get("status_counts", {})
        print(
            f"- {item.get('created_at', '?')} | {item.get('type', '?')} | "
            f"ok={counts.get('ok', 0)} failed={counts.get('failed', 0)} skipped={counts.get('skipped', 0)} | "
            f"{item.get('path', '')}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
