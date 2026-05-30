#!/usr/bin/env python3
"""Review local report history and decision discipline without exposing asset details."""

import json
import sys
from collections import Counter
from pathlib import Path

from common.config_loader import get_report_dirs, get_repo_root, load_settings, resolve_path


def _read_json(path):
    with Path(path).open(encoding="utf-8") as f:
        return json.load(f)


def load_report_index(limit=30):
    settings = load_settings()
    index_path = get_report_dirs(settings)["report_output_dir"] / "index.jsonl"
    records = []
    if index_path.exists():
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


def load_decision_records(limit=30, decision_dir=None):
    settings = load_settings()
    root = get_repo_root()
    track_dir = resolve_path(decision_dir or settings.get("decision_track_dir", "data/private/decision_track"), root)
    records = []
    if track_dir.exists():
        for path in sorted(track_dir.glob("*.json"))[-limit:]:
            try:
                records.append(_read_json(path))
            except (OSError, json.JSONDecodeError):
                continue
    sample_paths = sorted((root / "memory").glob("decision_track_sample*.json"))
    if not records and sample_paths:
        for path in sample_paths[-limit:]:
            try:
                sample = _read_json(path)
                sample["_sample"] = True
                records.append(sample)
            except (OSError, json.JSONDecodeError):
                continue
    return track_dir, records[-limit:]


def summarize_reports(records):
    counts = Counter(item.get("type", "unknown") for item in records)
    status = Counter()
    for item in records:
        for key, value in item.get("status_counts", {}).items():
            status[key] += value
    return counts, status


def summarize_decisions(records):
    strategy_counts = Counter()
    dates = []
    sample_count = 0
    for record in records:
        if record.get("_sample"):
            sample_count += 1
        if record.get("date"):
            dates.append(record["date"])
        for holding in record.get("holdings", []):
            strategy_counts[holding.get("strategy_type", "unknown")] += 1
    return strategy_counts, dates, sample_count


def format_review(report_index_path, report_records, decision_dir, decision_records):
    report_counts, status_counts = summarize_reports(report_records)
    strategy_counts, decision_dates, sample_count = summarize_decisions(decision_records)
    lines = ["# 历史复盘摘要", ""]
    lines.append("## 报告归档")
    lines.append(f"- 索引路径: {report_index_path}")
    lines.append(f"- 报告数量: {len(report_records)}")
    if report_counts:
        lines.append(f"- 类型分布: {dict(report_counts)}")
    if status_counts:
        lines.append(f"- 数据状态累计: {dict(status_counts)}")
    if not report_records:
        lines.append("- 暂无报告索引记录。")
    lines.append("")

    lines.append("## 决策记录")
    lines.append(f"- 记录目录: {decision_dir}")
    lines.append(f"- 记录数量: {len(decision_records)}")
    if sample_count:
        lines.append(f"- 当前使用样例记录: {sample_count} 条")
    if decision_dates:
        lines.append(f"- 日期范围: {decision_dates[0]} → {decision_dates[-1]}")
    if strategy_counts:
        lines.append(f"- strategy_type 分布: {dict(strategy_counts)}")
    if not decision_records:
        lines.append("- 暂无决策记录。")
    lines.append("")

    lines.append("## 纪律检查")
    if not decision_records:
        lines.append("- 无法检查纪律：缺少决策记录。")
    else:
        dca_count = strategy_counts.get("dca", 0)
        if dca_count:
            lines.append(f"- DCA记录存在: {dca_count} 条。复盘重点是纪律是否持续，而不是短期盈亏。")
        trial_count = strategy_counts.get("trial", 0)
        if trial_count:
            lines.append(f"- Trial记录存在: {trial_count} 条。复盘重点是是否学到东西、是否需要用户确认升级/退出。")
        short_count = strategy_counts.get("short_term", 0)
        if short_count:
            lines.append(f"- Short-term记录存在: {short_count} 条。复盘重点是止盈止损规则是否事先定义。")
    lines.append("")

    lines.append("## 下一步")
    lines.append("- 若报告数量为0，先运行日报/周报以生成归档。")
    lines.append("- 若仍在使用样例记录，请迁移真实决策记录到 ignored private 目录。")
    lines.append("- 复盘输出只展示聚合信息，不打印成本、份额或交易明细。")
    return "\n".join(lines)


def build_review(limit=30, decision_dir=None):
    report_index_path, reports = load_report_index(limit=limit)
    track_dir, decisions = load_decision_records(limit=limit, decision_dir=decision_dir)
    return format_review(report_index_path, reports, track_dir, decisions)


def main(argv=None):
    argv = argv or sys.argv[1:]
    limit = int(argv[0]) if argv else 30
    print(build_review(limit=limit))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
