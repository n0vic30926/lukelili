#!/usr/bin/env python3
"""Summarize report history and decision discipline without printing holdings."""

from collections import Counter
from datetime import date, timedelta
import json
from pathlib import Path

from common.config_loader import get_decision_track_dir, load_settings, resolve_path
from report_index import load_report_index


def _parse_date(value):
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _report_date(item):
    return _parse_date(item.get("report_date")) or _parse_date(item.get("created_at"))


def _count_current_daily_streak(items):
    daily_dates = {
        report_date
        for item in items
        if item.get("report_type") == "daily"
        for report_date in [_report_date(item)]
        if report_date is not None
    }
    if not daily_dates:
        return 0

    current = max(daily_dates)
    streak = 0
    while current in daily_dates:
        streak += 1
        current -= timedelta(days=1)
    return streak


def _count_missing_report_days(items):
    dates = sorted({_report_date(item) for item in items if _report_date(item)})
    if len(dates) < 2:
        return 0
    expected_days = (dates[-1] - dates[0]).days + 1
    return max(0, expected_days - len(dates))


def load_decision_records(decision_dir):
    """Load private decision files and retain only sanitized review fields."""
    root = Path(decision_dir)
    if not root.exists():
        return []

    records = []
    for path in sorted(root.glob("*.json")):
        try:
            item = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        strategies = []
        for holding in item.get("holdings", []):
            strategies.append(str(holding.get("strategy_type") or "unknown"))
        records.append(
            {
                "record_type": "daily_decision_snapshot",
                "date": str(item.get("date") or path.stem),
                "strategies": strategies,
            }
        )
    confirmation_path = root / "confirmations.jsonl"
    if confirmation_path.exists():
        for line in confirmation_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if item.get("event") != "confirmation_state_recorded":
                continue
            records.append(
                {
                    "record_type": "confirmation_state",
                    "date": str(item.get("created_at") or "")[:10],
                    "confirmation_status": str(item.get("confirmation_status") or "unknown"),
                    "check_count": int(item.get("check_count", 0) or 0),
                    "blocker_count": int(item.get("blocker_count", 0) or 0),
                    "blocker_types": [str(value) for value in item.get("blocker_types", [])],
                    "review_action_counts": {
                        str(key): int(value or 0)
                        for key, value in (item.get("review_action_counts") or {}).items()
                    },
                }
            )
    return records


def summarize_history(report_items, decision_records):
    failure_counts = Counter()
    quality = Counter({"fresh": 0, "stale": 0, "unknown": 0})
    strategy_counts = Counter()
    confirmation_records = Counter()
    confirmation_blockers = Counter()
    review_actions = Counter()

    for item in report_items:
        run_summary = item.get("run_summary", {})
        for module in run_summary.get("data_modules", []):
            if module.get("status") == "failed":
                failure_counts[str(module.get("module") or "unknown")] += 1

        data_quality = run_summary.get("data_quality", {})
        for key in ("fresh", "stale", "unknown"):
            quality[key] += int(data_quality.get(key, 0) or 0)

    for record in decision_records:
        if record.get("record_type") == "confirmation_state":
            confirmation_records[str(record.get("confirmation_status") or "unknown")] += 1
            confirmation_blockers.update(record.get("blocker_types", []))
            review_actions.update(record.get("review_action_counts", {}))
        else:
            strategy_counts.update(record.get("strategies", []))

    return {
        "report_count": len(report_items),
        "decision_record_count": len(decision_records),
        "report_continuity": {
            "current_streak_days": _count_current_daily_streak(report_items),
            "missing_days": _count_missing_report_days(report_items),
        },
        "repeated_failures": {
            name: count for name, count in sorted(failure_counts.items()) if count > 1
        },
        "data_quality": {
            "fresh": quality["fresh"],
            "stale": quality["stale"],
            "unknown": quality["unknown"],
        },
        "strategy_counts": dict(sorted(strategy_counts.items())),
        "confirmation_records": dict(sorted(confirmation_records.items())),
        "confirmation_blockers": dict(sorted(confirmation_blockers.items())),
        "review_actions": dict(sorted(review_actions.items())),
    }


def _format_counts(counts):
    if not counts:
        return "none"
    return " ".join(f"{key}={counts[key]}" for key in sorted(counts))


def format_history_review(summary):
    continuity = summary["report_continuity"]
    quality = summary["data_quality"]
    lines = ["# History Review Summary", ""]
    lines.append(f"- Reports: {summary['report_count']}")
    lines.append(f"- Current daily report streak: {continuity['current_streak_days']} day(s)")
    lines.append(f"- Missing report days: {continuity['missing_days']}")

    if summary["repeated_failures"]:
        for name, count in summary["repeated_failures"].items():
            lines.append(f"- Repeated failure: {name} x{count}")
    else:
        lines.append("- Repeated failures: none")

    lines.append(
        "- Data quality totals: "
        f"fresh={quality['fresh']} stale={quality['stale']} unknown={quality['unknown']}"
    )
    lines.append(f"- Decision records: {summary['decision_record_count']}")
    lines.append(f"- Strategy records: {_format_counts(summary['strategy_counts'])}")
    lines.append(f"- Confirmation records: {_format_counts(summary.get('confirmation_records', {}))}")
    lines.append(f"- Confirmation blockers: {_format_counts(summary.get('confirmation_blockers', {}))}")
    lines.append(f"- Review actions: {_format_counts(summary.get('review_actions', {}))}")
    return "\n".join(lines)


def main():
    settings = load_settings()
    index_path = resolve_path(settings.get("report_index_path", "reports/index.jsonl"))
    decision_dir = get_decision_track_dir(settings)
    report_items = load_report_index(index_path)
    decision_records = load_decision_records(decision_dir)
    print(format_history_review(summarize_history(report_items, decision_records)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
