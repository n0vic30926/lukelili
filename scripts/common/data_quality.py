#!/usr/bin/env python3
"""Data quality helpers for report sources and freshness checks."""

from datetime import datetime, timedelta


SOURCE_TIERS = {
    "official": {
        "rank": 1,
        "label": "official/regulatory",
        "description": "Exchange, regulator, central bank, fund company, or official filing.",
    },
    "market_data": {
        "rank": 2,
        "label": "market data",
        "description": "Structured market data provider or index data endpoint.",
    },
    "vendor": {
        "rank": 3,
        "label": "vendor",
        "description": "Established financial data or analytics vendor.",
    },
    "media": {
        "rank": 4,
        "label": "media",
        "description": "Mainstream financial media or curated news search.",
    },
    "social": {
        "rank": 5,
        "label": "social/sentiment",
        "description": "Social media, forum, search trend, or narrative signal.",
    },
    "unknown": {
        "rank": 9,
        "label": "unknown",
        "description": "Unclassified or unavailable source.",
    },
}


SOURCE_CLASSIFICATION = {
    "AkShare": "market_data",
    "Tavily": "media",
    "local portfolio": "official",
    "config": "official",
}


DEFAULT_FRESHNESS_THRESHOLDS = {
    "official": 168,
    "market_data": 24,
    "vendor": 24,
    "media": 12,
    "social": 6,
    "unknown": 24,
}


def classify_source(source):
    """Return a source tier key for a source string."""
    source_text = str(source or "")
    for token, tier in SOURCE_CLASSIFICATION.items():
        if token.lower() in source_text.lower():
            return tier
    return "unknown"


def assess_freshness(timestamp_text, max_age_hours=24):
    """Assess whether a timestamp is fresh, stale, unknown, or future-dated."""
    if not timestamp_text:
        return {"status": "unknown", "age_hours": None, "message": "timestamp unavailable"}
    try:
        timestamp = datetime.fromisoformat(str(timestamp_text).replace("Z", "+00:00"))
        if timestamp.tzinfo is not None:
            timestamp = timestamp.replace(tzinfo=None)
    except ValueError:
        return {"status": "unknown", "age_hours": None, "message": "timestamp parse failed"}

    now = datetime.now()
    if timestamp > now + timedelta(minutes=5):
        return {"status": "future", "age_hours": None, "message": "timestamp is in the future"}

    age_hours = (now - timestamp).total_seconds() / 3600
    if age_hours <= max_age_hours:
        return {"status": "fresh", "age_hours": round(age_hours, 2), "message": "fresh"}
    return {"status": "stale", "age_hours": round(age_hours, 2), "message": "stale"}


def freshness_threshold_for_tier(tier, thresholds=None, default_hours=24):
    """Return freshness threshold hours for a source tier."""
    thresholds = thresholds or {}
    if tier in thresholds:
        return thresholds[tier]
    if tier in DEFAULT_FRESHNESS_THRESHOLDS:
        return DEFAULT_FRESHNESS_THRESHOLDS[tier]
    return default_hours


def quality_for_record(record, max_age_hours=24, thresholds=None):
    """Build a compact quality assessment for a status tracker record."""
    tier = classify_source(record.get("source", ""))
    tier_max_age = freshness_threshold_for_tier(tier, thresholds=thresholds, default_hours=max_age_hours)
    freshness = assess_freshness(record.get("timestamp"), max_age_hours=tier_max_age)
    return {
        "module": record.get("module", ""),
        "status": record.get("status", ""),
        "source": record.get("source", ""),
        "tier": tier,
        "tier_label": SOURCE_TIERS[tier]["label"],
        "freshness": freshness["status"],
        "age_hours": freshness["age_hours"],
        "max_age_hours": tier_max_age,
        "cache_hit": bool(record.get("cache_hit")),
    }


def summarize_quality(records, max_age_hours=24, thresholds=None):
    """Summarize source tiers and freshness for report display."""
    assessments = [
        quality_for_record(record, max_age_hours=max_age_hours, thresholds=thresholds)
        for record in records
    ]
    summary = {
        "total": len(assessments),
        "by_tier": {},
        "by_freshness": {},
        "failed": 0,
        "skipped": 0,
        "cache_hits": 0,
    }
    for item in assessments:
        summary["by_tier"][item["tier_label"]] = summary["by_tier"].get(item["tier_label"], 0) + 1
        summary["by_freshness"][item["freshness"]] = summary["by_freshness"].get(item["freshness"], 0) + 1
        if item["status"] == "failed":
            summary["failed"] += 1
        if item["status"] == "skipped":
            summary["skipped"] += 1
        if item["cache_hit"]:
            summary["cache_hits"] += 1
    return summary, assessments


def markdown_quality_lines(records, max_age_hours=24, thresholds=None):
    """Return markdown lines for report data quality."""
    summary, assessments = summarize_quality(records, max_age_hours=max_age_hours, thresholds=thresholds)
    lines = ["## 数据质量", ""]
    lines.append(
        f"- 数据事件: {summary['total']} | 失败: {summary['failed']} | 跳过: {summary['skipped']} | 缓存命中: {summary['cache_hits']}"
    )
    if summary["by_tier"]:
        tiers = ", ".join(f"{tier}={count}" for tier, count in sorted(summary["by_tier"].items()))
        lines.append(f"- 来源层级: {tiers}")
    if summary["by_freshness"]:
        freshness = ", ".join(f"{key}={count}" for key, count in sorted(summary["by_freshness"].items()))
        lines.append(f"- 新鲜度: {freshness}")
    if assessments:
        lines.append("- 低质量/异常数据:")
        abnormal = [item for item in assessments if item["status"] != "ok" or item["freshness"] not in ("fresh", "unknown")]
        if abnormal:
            for item in abnormal[:8]:
                lines.append(
                    f"  - {item['module']} | status={item['status']} | tier={item['tier_label']} | freshness={item['freshness']} | max_age_h={item['max_age_hours']}"
                )
        else:
            lines.append("  - 无")
    lines.append("")
    return lines
