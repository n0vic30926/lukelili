"""Data-call status tracking and best-effort cache helpers."""

import hashlib
import importlib.util
import json
import time
from pathlib import Path

from common.data_quality import freshness_label, source_tier


class DataStatusTracker:
    def __init__(self, current_time=None, default_max_age_hours=24):
        self.records = []
        self.cache_hits = 0
        self.current_time = current_time
        self.default_max_age_hours = default_max_age_hours

    def _record(self, item, observed_at=None, max_age_hours=None):
        source = item.get("source", "")
        item["source_tier"] = source_tier(source)
        item["freshness"] = freshness_label(
            observed_at,
            self.current_time,
            max_age_hours=max_age_hours or self.default_max_age_hours,
        )
        if observed_at:
            item["observed_at"] = observed_at
        self.records.append(item)

    def success(self, module, source="", detail="", observed_at=None, max_age_hours=None):
        self._record(
            {
                "module": module,
                "status": "success",
                "source": source,
                "detail": detail,
            },
            observed_at=observed_at,
            max_age_hours=max_age_hours,
        )

    def ok(self, module, source="", message="", cache_hit=False):
        self.success(module, source=source, detail=message)
        if cache_hit:
            self.cache_hit(module)

    def failure(self, module, source="", error=None):
        self._record(
            {
                "module": module,
                "status": "failed",
                "source": source,
                "error_type": type(error).__name__ if error else "Error",
            }
        )

    def fail(self, module, source="", message=""):
        self.failure(module, source=source, error=RuntimeError(str(message) or "failed"))

    def skipped(self, module, source="", reason=""):
        self._record(
            {
                "module": module,
                "status": "skipped",
                "source": source,
                "reason": reason,
            }
        )

    def skip(self, module, source="", message=""):
        self.skipped(module, source=source, reason=message)

    def cache_hit(self, module):
        self.cache_hits += 1

    def counts(self):
        summary = self.to_run_summary()["modules"]
        return {
            "ok": summary.get("success", 0),
            "success": summary.get("success", 0),
            "failed": summary.get("failed", 0),
            "skipped": summary.get("skipped", 0),
            "cache_hits": summary.get("cache_hit", 0),
            "cache_hit": summary.get("cache_hit", 0),
        }

    def summary_text(self):
        counts = self.counts()
        return (
            f"ok={counts.get('ok', 0)}, "
            f"failed={counts.get('failed', 0)}, "
            f"skipped={counts.get('skipped', 0)}, "
            f"cache_hits={counts.get('cache_hits', 0)}"
        )

    def markdown_lines(self):
        lines = ["## 运行摘要", ""]
        lines.append(f"- 数据模块: {self.summary_text()}")
        if self.records:
            lines.append("- 模块明细:")
            for item in self.records:
                parts = [
                    str(item.get("module", "unknown")),
                    str(item.get("status", "unknown")),
                ]
                if item.get("source"):
                    parts.append(f"source={item['source']}")
                if item.get("freshness"):
                    parts.append(f"freshness={item['freshness']}")
                if item.get("detail"):
                    parts.append(f"message={item['detail']}")
                if item.get("reason"):
                    parts.append(f"message={item['reason']}")
                if item.get("error_type"):
                    parts.append(f"error_type={item['error_type']}")
                lines.append(f"  - {' | '.join(parts)}")
        lines.append("")
        return lines

    def quality_markdown_lines(self, max_age_hours=24, thresholds=None):
        summary = self.to_run_summary().get("data_quality", {})
        lines = ["## 数据质量", ""]
        lines.append(
            "- freshness: "
            f"fresh={summary.get('fresh', 0)} "
            f"stale={summary.get('stale', 0)} "
            f"unknown={summary.get('unknown', 0)}"
        )
        source_tiers = summary.get("source_tiers") or {}
        if source_tiers:
            rendered = " ".join(f"{key}={source_tiers[key]}" for key in sorted(source_tiers))
            lines.append(f"- source_tiers: {rendered}")
        lines.append("")
        return lines

    def to_run_summary(self):
        counts = {"success": 0, "failed": 0, "skipped": 0, "cache_hit": self.cache_hits}
        quality = {
            "fresh": 0,
            "stale": 0,
            "unknown": 0,
            "source_tiers": {},
        }
        for record in self.records:
            status = record.get("status")
            if status in counts:
                counts[status] += 1
            freshness = record.get("freshness", "unknown")
            if freshness in ("fresh", "stale"):
                quality[freshness] += 1
            else:
                quality["unknown"] += 1
            tier = record.get("source_tier", "unknown")
            quality["source_tiers"][tier] = quality["source_tiers"].get(tier, 0) + 1
        return {
            "modules": counts,
            "data_quality": quality,
            "data_modules": list(self.records),
        }


def safe_call(module, func, fallback=None, tracker=None, source=""):
    try:
        result = func()
        if tracker:
            tracker.success(module, source=source)
        return result
    except Exception as exc:
        if tracker:
            tracker.failure(module, source=source, error=exc)
        return fallback


def _cache_file(cache_dir, key):
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]
    return Path(cache_dir) / f"{digest}.json"


def _fresh(path, ttl_hours):
    if not path.exists():
        return False
    age_seconds = time.time() - path.stat().st_mtime
    return age_seconds <= ttl_hours * 3600


def dependency_available(module_name):
    return importlib.util.find_spec(module_name) is not None


def missing_dependencies(module_names):
    return [name for name in module_names if not dependency_available(name)]


def cached_call(*args, **kwargs):
    if args and isinstance(args[0], dict):
        settings, tracker, module, source, cache_key, producer = args[:6]
        fallback = args[6] if len(args) > 6 else kwargs.get("fallback")
        cache_dir = settings.get("cache_dir", "cache")
        ttl_hours = settings.get("cache_ttl_hours", 1)
        try:
            result = _cached_call_simple(
                module,
                producer,
                cache_dir,
                ttl_hours=ttl_hours,
                tracker=tracker,
                cache_key=cache_key,
            )
            if tracker:
                tracker.success(module, source=source)
            return result
        except Exception as exc:
            if tracker:
                tracker.failure(module, source=source, error=exc)
            return fallback
    return _cached_call_simple(*args, **kwargs)


def _cached_call_simple(module, func, cache_dir, ttl_hours=1, tracker=None, cache_key=None):
    cache_path = _cache_file(cache_dir, cache_key or module)
    try:
        if _fresh(cache_path, ttl_hours):
            with cache_path.open(encoding="utf-8") as f:
                if tracker:
                    tracker.cache_hit(module)
                return json.load(f)
    except Exception:
        pass

    result = func()
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with cache_path.open("w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2, default=str)
    except Exception:
        pass
    return result
