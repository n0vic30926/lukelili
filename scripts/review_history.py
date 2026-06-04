#!/usr/bin/env python3
"""Review local report history and decision discipline without exposing asset details."""

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from common.config_loader import get_report_dirs, get_repo_root, load_settings, resolve_path


def _read_json(path):
    with Path(path).open(encoding="utf-8") as f:
        return json.load(f)


def load_report_index(limit=30):
    settings = load_settings()
    report_dirs = get_report_dirs(settings)
    index_path = report_dirs["report_output_dir"] / "index.jsonl"
    log_path = report_dirs["log_dir"] / "finance-agent.jsonl"
    events_by_path = {}
    if log_path.exists():
        with log_path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    item = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if item.get("path") and isinstance(item.get("events"), list):
                    events_by_path[item["path"]] = item["events"]
    records = []
    if index_path.exists():
        with index_path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    item = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if item.get("path") in events_by_path:
                    item["events"] = events_by_path[item["path"]]
                records.append(item)
    return index_path, records[-limit:]


def load_decision_records(limit=30, decision_dir=None):
    settings = load_settings()
    root = get_repo_root()
    return_records_only = False
    if decision_dir is None and not isinstance(limit, int):
        decision_dir = limit
        limit = 30
        return_records_only = True
    track_dir = resolve_path(decision_dir or settings.get("decision_track_dir", "data/private/decision_track"), root)
    records = []
    if track_dir.exists():
        for path in sorted(track_dir.glob("*.json"))[-limit:]:
            try:
                records.append(_read_json(path))
            except (OSError, json.JSONDecodeError):
                continue
        confirmation_path = track_dir / "confirmations.jsonl"
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
        resolution_path = track_dir / "review_resolutions.jsonl"
        if resolution_path.exists():
            for line in resolution_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    item = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if item.get("event") != "manual_review_resolution_recorded":
                    continue
                records.append(
                    {
                        "record_type": "manual_review_resolution",
                        "date": str(item.get("created_at") or "")[:10],
                        "action": str(item.get("action") or "unknown"),
                        "outcome": str(item.get("outcome") or "unknown"),
                        "reason_code": str(item.get("reason_code") or "unspecified"),
                        "execution_allowed": bool(item.get("execution_allowed")),
                    }
                )
    sample_paths = sorted((root / "memory").glob("decision_track_sample*.json"))
    if not records and sample_paths:
        for path in sample_paths[-limit:]:
            try:
                sample = _read_json(path)
                sample["_sample"] = True
                records.append(sample)
            except (OSError, json.JSONDecodeError):
                continue
    records = records[-limit:]
    if return_records_only:
        return records
    return track_dir, records


def summarize_reports(records):
    counts = Counter(item.get("type", "unknown") for item in records)
    status = Counter()
    for item in records:
        for key, value in item.get("status_counts", {}).items():
            status[key] += value
    return counts, status


def summarize_report_continuity(records):
    dates = sorted(
        {
            parsed.date()
            for parsed in (_parse_datetime(item.get("created_at")) for item in records)
            if parsed
        }
    )
    if not dates:
        return {
            "report_days": 0,
            "date_range": None,
            "max_gap_days": 0,
            "current_streak_days": 0,
        }
    gaps = [(dates[index] - dates[index - 1]).days for index in range(1, len(dates))]
    current_streak = 1
    for gap in reversed(gaps):
        if gap == 1:
            current_streak += 1
        else:
            break
    return {
        "report_days": len(dates),
        "date_range": f"{dates[0].isoformat()} → {dates[-1].isoformat()}",
        "max_gap_days": max(gaps) if gaps else 0,
        "current_streak_days": current_streak,
    }


def summarize_repeated_failures(records):
    failed_modules = Counter()
    skipped_modules = Counter()
    reports_with_events = 0
    reports_with_failures = 0
    aggregate_failed = 0
    for record in records:
        events = record.get("events")
        if isinstance(events, list) and events:
            reports_with_events += 1
            report_failed = False
            for event in events:
                module = event.get("module", "unknown")
                status = event.get("status")
                if status == "failed":
                    failed_modules[module] += 1
                    report_failed = True
                elif status == "skipped":
                    skipped_modules[module] += 1
            if report_failed:
                reports_with_failures += 1
        else:
            aggregate_failed += int(record.get("status_counts", {}).get("failed", 0) or 0)
    return {
        "reports_with_events": reports_with_events,
        "reports_with_failures": reports_with_failures,
        "failed_modules": failed_modules,
        "repeated_failed_modules": Counter({key: value for key, value in failed_modules.items() if value >= 2}),
        "skipped_modules": skipped_modules,
        "aggregate_failed_without_events": aggregate_failed,
    }


def _parse_datetime(value):
    if not value:
        return None
    text = str(value).strip()
    for candidate in (text, text.replace("Z", "+00:00")):
        try:
            parsed = datetime.fromisoformat(candidate)
            if parsed.tzinfo:
                return parsed.astimezone(timezone.utc).replace(tzinfo=None)
            return parsed
        except ValueError:
            continue
    try:
        return datetime.strptime(text[:10], "%Y-%m-%d")
    except ValueError:
        return None


def _iter_text_values(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, (list, tuple, set)):
        for item in value:
            if isinstance(item, str):
                yield item


def _action_content_terms(action):
    terms = set()
    for field in ("report_evidence_terms", "evidence_terms", "tags"):
        for value in _iter_text_values(action.get(field)):
            text = value.strip().lower()
            if 3 <= len(text) <= 80:
                terms.add(text)
    for field in ("action_id", "action_type"):
        value = action.get(field)
        if isinstance(value, str):
            text = value.strip().lower()
            if text and text != "unknown":
                terms.add(text)
    return terms


def _read_report_content(path_value):
    if not path_value:
        return None
    path = Path(path_value)
    if not path.is_absolute():
        path = get_repo_root() / path
    try:
        return path.read_text(encoding="utf-8").lower()
    except (OSError, UnicodeDecodeError):
        return None


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


def summarize_user_actions(records):
    status_counts = Counter()
    action_type_counts = Counter()
    strategy_counts = Counter()
    requires_confirmation = 0
    unresolved_confirmation = 0
    total = 0
    for record in records:
        for action in record.get("user_actions", []):
            total += 1
            status = action.get("status", "unknown")
            action_type = action.get("action_type", "unknown")
            strategy_type = action.get("strategy_type", "unknown")
            status_counts[status] += 1
            action_type_counts[action_type] += 1
            strategy_counts[strategy_type] += 1
            if action.get("requires_user_confirmation"):
                requires_confirmation += 1
                if status != "confirmed":
                    unresolved_confirmation += 1
    return {
        "total": total,
        "status_counts": status_counts,
        "action_type_counts": action_type_counts,
        "strategy_counts": strategy_counts,
        "requires_confirmation": requires_confirmation,
        "unresolved_confirmation": unresolved_confirmation,
    }


def summarize_action_outcomes(records):
    outcome_counts = Counter()
    quality_counts = Counter()
    checklist_counts = Counter()
    strategy_counts = Counter()
    action_type_counts = Counter()
    confirmed_total = 0
    pending_review = 0
    checklist_issues = 0
    for record in records:
        for action in record.get("user_actions", []):
            if action.get("status") != "confirmed":
                continue
            confirmed_total += 1
            outcome_status = action.get("outcome_status") or "pending_review"
            outcome_counts[outcome_status] += 1
            quality_counts[action.get("outcome_quality", "unrated")] += 1
            strategy_counts[action.get("strategy_type", "unknown")] += 1
            action_type_counts[action.get("action_type", "unknown")] += 1
            checklist = action.get("checklist", {}) or {}
            for status in checklist.values():
                checklist_counts[status] += 1
                if status != "pass":
                    checklist_issues += 1
            if outcome_status != "reviewed":
                pending_review += 1
    return {
        "confirmed_total": confirmed_total,
        "outcome_counts": outcome_counts,
        "quality_counts": quality_counts,
        "checklist_counts": checklist_counts,
        "strategy_counts": strategy_counts,
        "action_type_counts": action_type_counts,
        "pending_review": pending_review,
        "checklist_issues": checklist_issues,
    }


def summarize_cross_report_attribution(report_records, decision_records):
    report_points = []
    for record in report_records:
        created_at = _parse_datetime(record.get("created_at"))
        if created_at:
            report_points.append(
                {
                    "created_at": created_at,
                    "type": record.get("type", "unknown"),
                    "path": record.get("path"),
                }
            )
    report_points = sorted(report_points, key=lambda item: item["created_at"])

    with_evidence = 0
    without_evidence = 0
    later_type_counts = Counter()
    content_matched = 0
    content_unmatched = 0
    content_unreadable = 0
    content_missing_terms = 0
    content_type_counts = Counter()
    confirmed_total = 0
    for decision in decision_records:
        record_date = decision.get("date")
        for action in decision.get("user_actions", []):
            if action.get("status") != "confirmed":
                continue
            confirmed_total += 1
            action_time = (
                _parse_datetime(action.get("confirmed_at"))
                or _parse_datetime(action.get("created_at"))
                or _parse_datetime(record_date)
            )
            later_reports = [item for item in report_points if action_time and item["created_at"] > action_time]
            if later_reports:
                with_evidence += 1
                for report in later_reports[:3]:
                    later_type_counts[report["type"]] += 1
                terms = _action_content_terms(action)
                if not terms:
                    content_missing_terms += 1
                    continue
                readable = 0
                matched_report_type = None
                for report in later_reports[:3]:
                    content = _read_report_content(report.get("path"))
                    if content is None:
                        continue
                    readable += 1
                    if any(term in content for term in terms):
                        matched_report_type = report["type"]
                        break
                if matched_report_type:
                    content_matched += 1
                    content_type_counts[matched_report_type] += 1
                elif readable:
                    content_unmatched += 1
                else:
                    content_unreadable += 1
            else:
                without_evidence += 1
    return {
        "confirmed_total": confirmed_total,
        "with_evidence": with_evidence,
        "without_evidence": without_evidence,
        "later_type_counts": later_type_counts,
        "content_matched": content_matched,
        "content_unmatched": content_unmatched,
        "content_unreadable": content_unreadable,
        "content_missing_terms": content_missing_terms,
        "content_type_counts": content_type_counts,
    }


def _history_report_date(item):
    parsed = _parse_datetime(item.get("report_date")) or _parse_datetime(item.get("created_at"))
    return parsed.date() if parsed else None


def _count_current_daily_streak(items):
    daily_dates = {
        report_date
        for item in items
        if item.get("report_type") == "daily"
        for report_date in [_history_report_date(item)]
        if report_date is not None
    }
    if not daily_dates:
        return 0

    current = max(daily_dates)
    streak = 0
    while current in daily_dates:
        streak += 1
        current = current.fromordinal(current.toordinal() - 1)
    return streak


def _count_missing_report_days(items):
    dates = sorted({_history_report_date(item) for item in items if _history_report_date(item)})
    if len(dates) < 2:
        return 0
    expected_days = (dates[-1] - dates[0]).days + 1
    return max(0, expected_days - len(dates))


def summarize_history(report_items, decision_records):
    failure_counts = Counter()
    quality = Counter({"fresh": 0, "stale": 0, "unknown": 0})
    strategy_counts = Counter()
    confirmation_records = Counter()
    confirmation_blockers = Counter()
    review_actions = Counter()
    review_resolution_actions = Counter()
    review_resolution_outcomes = Counter()
    review_resolution_reasons = Counter()

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
        elif record.get("record_type") == "manual_review_resolution":
            review_resolution_actions[str(record.get("action") or "unknown")] += 1
            review_resolution_outcomes[str(record.get("outcome") or "unknown")] += 1
            review_resolution_reasons[str(record.get("reason_code") or "unspecified")] += 1
        else:
            for holding in record.get("holdings", []):
                strategy_counts[str(holding.get("strategy_type") or "unknown")] += 1

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
        "review_resolution_actions": dict(sorted(review_resolution_actions.items())),
        "review_resolution_outcomes": dict(sorted(review_resolution_outcomes.items())),
        "review_resolution_reasons": dict(sorted(review_resolution_reasons.items())),
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
    lines.append(f"- Review resolution actions: {_format_counts(summary.get('review_resolution_actions', {}))}")
    lines.append(f"- Review resolution outcomes: {_format_counts(summary.get('review_resolution_outcomes', {}))}")
    lines.append(f"- Review resolution reasons: {_format_counts(summary.get('review_resolution_reasons', {}))}")
    return "\n".join(lines)


def _has_short_term_rules(holding):
    rule_keys = (
        "take_profit",
        "take_profit_rule",
        "stop_loss",
        "stop_loss_rule",
        "exit_rule",
        "risk_rule",
    )
    return any(holding.get(key) for key in rule_keys)


def build_strategy_scorecards(records):
    grouped = {}
    for record in records:
        record_date = record.get("date") or "unknown"
        for holding in record.get("holdings", []):
            strategy_type = holding.get("strategy_type", "unknown")
            card = grouped.setdefault(
                strategy_type,
                {
                    "strategy_type": strategy_type,
                    "records": 0,
                    "assets": set(),
                    "dates": set(),
                    "short_term_rule_count": 0,
                },
            )
            card["records"] += 1
            if holding.get("code"):
                card["assets"].add(holding["code"])
            card["dates"].add(record_date)
            if strategy_type == "short_term" and _has_short_term_rules(holding):
                card["short_term_rule_count"] += 1

    cards = []
    for strategy_type in sorted(grouped):
        raw = grouped[strategy_type]
        assets = len(raw["assets"])
        dates = len(raw["dates"])
        records_count = raw["records"]
        if strategy_type == "dca":
            score = 7 if dates > 1 else 6
            status = "discipline_tracking"
            focus = "评估纪律是否持续执行，不按短期盈亏评价。"
            next_step = "继续记录执行日期；不要输出止损、择时暂停或波段化建议。"
        elif strategy_type == "trial":
            score = 5
            status = "needs_user_review"
            focus = "评估盈亏、回撤、学习结论，以及是否需要用户确认升级或退出。"
            next_step = "补充学习结论、退出条件和是否升级为信念仓的用户确认。"
        elif strategy_type == "short_term":
            rules = raw["short_term_rule_count"]
            score = 6 if rules == records_count else 3
            status = "rules_present" if rules == records_count else "missing_rules"
            focus = "评估止盈止损是否事先定义，而不是事后解释。"
            next_step = "为每条短线记录补齐止盈、止损或退出规则。"
        elif strategy_type == "watch":
            score = 6
            status = "research_only"
            focus = "只做研究和入场条件观察，不视为持仓操作。"
            next_step = "维护触发条件、否决条件和信息来源。"
        else:
            score = 2
            status = "unknown_strategy"
            focus = "策略类型无法映射到投资声明书。"
            next_step = "由用户显式声明 strategy_type 后再复盘。"
        cards.append(
            {
                "strategy_type": strategy_type,
                "score": score,
                "status": status,
                "records": records_count,
                "assets": assets,
                "dates": dates,
                "focus": focus,
                "next_step": next_step,
            }
        )
    return cards


def format_review(report_index_path, report_records, decision_dir, decision_records):
    report_counts, status_counts = summarize_reports(report_records)
    continuity_summary = summarize_report_continuity(report_records)
    failure_summary = summarize_repeated_failures(report_records)
    strategy_counts, decision_dates, sample_count = summarize_decisions(decision_records)
    strategy_cards = build_strategy_scorecards(decision_records)
    action_summary = summarize_user_actions(decision_records)
    outcome_summary = summarize_action_outcomes(decision_records)
    attribution_summary = summarize_cross_report_attribution(report_records, decision_records)
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

    lines.append("## 报告连续性")
    if not continuity_summary["report_days"]:
        lines.append("- 暂无可解析报告日期，无法评估连续性。")
    else:
        lines.append(f"- 报告日期范围: {continuity_summary['date_range']}")
        lines.append(f"- 有报告的自然日: {continuity_summary['report_days']}")
        lines.append(f"- 最大报告间隔: {continuity_summary['max_gap_days']} 天")
        lines.append(f"- 当前连续报告天数: {continuity_summary['current_streak_days']}")
        lines.append("- 连续性边界: 只按本地归档日期统计，不代表市场交易日完整覆盖。")
    lines.append("")

    lines.append("## 重复失败检测")
    if not report_records:
        lines.append("- 暂无报告记录，无法检测重复失败。")
    else:
        lines.append(f"- 有事件明细的报告: {failure_summary['reports_with_events']}")
        lines.append(f"- 含失败事件的报告: {failure_summary['reports_with_failures']}")
        if failure_summary["failed_modules"]:
            lines.append(f"- 失败模块分布: {dict(failure_summary['failed_modules'])}")
            lines.append(f"- 重复失败模块: {dict(failure_summary['repeated_failed_modules'])}")
        elif failure_summary["aggregate_failed_without_events"]:
            lines.append(f"- 仅有聚合失败次数: {failure_summary['aggregate_failed_without_events']}，缺少模块明细。")
        else:
            lines.append("- 暂无失败模块记录。")
        if failure_summary["skipped_modules"]:
            lines.append(f"- 跳过模块分布: {dict(failure_summary['skipped_modules'])}")
        lines.append("- 检测边界: 只输出模块级聚合，不输出错误消息、报告原文或私人数据。")
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

    lines.append("## 策略评分卡")
    if not strategy_cards:
        lines.append("- 暂无可评分策略记录。")
    for card in strategy_cards:
        lines.append(
            "- "
            f"{card['strategy_type']}: score={card['score']}/10, status={card['status']}, "
            f"records={card['records']}, assets={card['assets']}, dates={card['dates']}"
        )
        lines.append(f"  - 复盘重点: {card['focus']}")
        lines.append(f"  - 下一步: {card['next_step']}")
    lines.append("")

    lines.append("## 用户确认动作")
    if not action_summary["total"]:
        lines.append("- 暂无用户确认动作记录。")
    else:
        lines.append(f"- 动作数量: {action_summary['total']}")
        lines.append(f"- 状态分布: {dict(action_summary['status_counts'])}")
        lines.append(f"- 动作类型分布: {dict(action_summary['action_type_counts'])}")
        lines.append(f"- 策略分布: {dict(action_summary['strategy_counts'])}")
        lines.append(f"- 需要用户确认且未完成: {action_summary['unresolved_confirmation']}")
        lines.append("- 复盘边界: 只统计用户确认状态，不输出代码、金额或理由全文。")
    lines.append("")

    lines.append("## 确认后结果复盘")
    if not outcome_summary["confirmed_total"]:
        lines.append("- 暂无已确认动作，无法做结果复盘。")
    else:
        lines.append(f"- 已确认动作: {outcome_summary['confirmed_total']}")
        lines.append(f"- 结果状态分布: {dict(outcome_summary['outcome_counts'])}")
        lines.append(f"- 结果质量分布: {dict(outcome_summary['quality_counts'])}")
        lines.append(f"- 检查项状态分布: {dict(outcome_summary['checklist_counts'])}")
        lines.append(f"- 动作类型分布: {dict(outcome_summary['action_type_counts'])}")
        lines.append(f"- 策略分布: {dict(outcome_summary['strategy_counts'])}")
        lines.append(f"- 待结果复盘: {outcome_summary['pending_review']}")
        lines.append(f"- 失败或缺失检查项: {outcome_summary['checklist_issues']}")
        lines.append("- 复盘边界: 只统计结果状态，不输出收益、金额、代码或复盘说明全文。")
    lines.append("")

    lines.append("## 跨报告归因")
    if not attribution_summary["confirmed_total"]:
        lines.append("- 暂无已确认动作，无法连接后续报告。")
    else:
        lines.append(f"- 已确认动作: {attribution_summary['confirmed_total']}")
        lines.append(f"- 有后续报告证据: {attribution_summary['with_evidence']}")
        lines.append(f"- 缺少后续报告证据: {attribution_summary['without_evidence']}")
        lines.append(f"- 后续报告类型分布: {dict(attribution_summary['later_type_counts'])}")
        lines.append(f"- 后续报告内容命中: {attribution_summary['content_matched']}")
        lines.append(f"- 有后续报告但未命中内容: {attribution_summary['content_unmatched']}")
        lines.append(f"- 后续报告不可读取: {attribution_summary['content_unreadable']}")
        lines.append(f"- 缺少非敏感匹配标记: {attribution_summary['content_missing_terms']}")
        if attribution_summary["content_type_counts"]:
            lines.append(f"- 内容命中报告类型分布: {dict(attribution_summary['content_type_counts'])}")
        lines.append("- 归因边界: 只证明后续报告内容出现非敏感动作标记，不把市场结果归因为单次动作。")
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
