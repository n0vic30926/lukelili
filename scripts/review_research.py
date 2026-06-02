#!/usr/bin/env python3
"""Read-only history and discipline review research adapter."""

from pathlib import Path

from common.config_loader import get_decision_track_dir, load_settings, resolve_path
from report_index import load_report_index
from review_history import load_decision_records, summarize_history


def _data_source(name, source, status):
    return {
        "name": name,
        "source": source,
        "status": status,
        "source_tier": "local_user_data",
    }


def _path_status(path):
    return "available" if Path(path).exists() else "missing_file"


def _count_repeated_failures(summary):
    return sum(1 for _ in summary.get("repeated_failures", {}))


def fetch_review_research(report_items=None, decision_records=None, index_path=None, decision_dir=None):
    settings = load_settings()
    if index_path is None:
        index_path = resolve_path(settings.get("report_index_path", "reports/index.jsonl"))
    if decision_dir is None:
        decision_dir = get_decision_track_dir(settings)

    reports = list(report_items) if report_items is not None else load_report_index(index_path)
    decisions = list(decision_records) if decision_records is not None else load_decision_records(decision_dir)
    summary = summarize_history(reports, decisions)
    continuity = summary["report_continuity"]
    quality = summary["data_quality"]
    confirmation_records = summary.get("confirmation_records", {})
    confirmation_blockers = summary.get("confirmation_blockers", {})

    observations = [
        f"reports={summary['report_count']}",
        f"decision_records={summary['decision_record_count']}",
        f"current_daily_streak={continuity['current_streak_days']}",
        f"missing_report_days={continuity['missing_days']}",
        f"repeated_failure_modules={_count_repeated_failures(summary)}",
        f"data_quality_fresh={quality['fresh']}",
        f"data_quality_stale={quality['stale']}",
        f"data_quality_unknown={quality['unknown']}",
    ]
    if confirmation_records:
        observations.append(
            "confirmation_records="
            + ",".join(f"{key}:{confirmation_records[key]}" for key in sorted(confirmation_records))
        )
    if confirmation_blockers:
        observations.append(
            "confirmation_blockers="
            + ",".join(f"{key}:{confirmation_blockers[key]}" for key in sorted(confirmation_blockers))
        )

    evidence = [
        {"label": "reports.index", "source_tier": "local_user_data", "freshness": "unknown"},
        {"label": "review.report_continuity", "source_tier": "local_user_data", "freshness": "unknown"},
        {"label": "review.decision_records", "source_tier": "local_user_data", "freshness": "unknown"},
    ]
    if confirmation_records or confirmation_blockers:
        evidence.append(
            {"label": "review.confirmation_records", "source_tier": "local_user_data", "freshness": "unknown"}
        )

    data_sources = [
        _data_source(
            "report_index",
            "local",
            "available" if report_items is not None else _path_status(index_path),
        ),
        _data_source("report_continuity", "local", "available" if reports else "empty"),
        _data_source(
            "decision_records",
            "local",
            "available" if decision_records is not None else _path_status(decision_dir),
        ),
        _data_source("confirmation_records", "local", "available" if confirmation_records else "empty"),
    ]

    limitations = ["private decision details are summarized only"]
    if not reports:
        limitations.append("no archived report index records")
    if not decisions:
        limitations.append("no private decision records")

    return {
        "status": "ok" if reports or decisions else "skipped",
        "observations": observations,
        "evidence": evidence,
        "data_sources": data_sources,
        "limitations": limitations,
    }


def main():
    print(fetch_review_research())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
