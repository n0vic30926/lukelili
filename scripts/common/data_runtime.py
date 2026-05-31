"""Data-call status tracking and best-effort cache helpers."""

import hashlib
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

    def failure(self, module, source="", error=None):
        self._record(
            {
                "module": module,
                "status": "failed",
                "source": source,
                "error_type": type(error).__name__ if error else "Error",
            }
        )

    def skipped(self, module, source="", reason=""):
        self._record(
            {
                "module": module,
                "status": "skipped",
                "source": source,
                "reason": reason,
            }
        )

    def cache_hit(self, module):
        self.cache_hits += 1

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


def cached_call(module, func, cache_dir, ttl_hours=1, tracker=None, cache_key=None):
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
