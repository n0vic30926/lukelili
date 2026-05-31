"""Data-call status tracking and best-effort cache helpers."""

import hashlib
import json
import time
from pathlib import Path


class DataStatusTracker:
    def __init__(self):
        self.records = []
        self.cache_hits = 0

    def success(self, module, source="", detail=""):
        self.records.append(
            {
                "module": module,
                "status": "success",
                "source": source,
                "detail": detail,
            }
        )

    def failure(self, module, source="", error=None):
        self.records.append(
            {
                "module": module,
                "status": "failed",
                "source": source,
                "error_type": type(error).__name__ if error else "Error",
            }
        )

    def skipped(self, module, source="", reason=""):
        self.records.append(
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
        for record in self.records:
            status = record.get("status")
            if status in counts:
                counts[status] += 1
        return {
            "modules": counts,
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

