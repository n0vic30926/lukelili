#!/usr/bin/env python3
"""Runtime helpers for external data calls, status tracking, and cache."""

import hashlib
import importlib.util
import json
import pickle
import time
from datetime import datetime

from common.config_loader import get_report_dirs, load_settings


class DataStatusTracker:
    """Collect visible module status for reports and logs."""

    def __init__(self):
        self.records = []

    def record(self, module, status, source="", message="", cache_hit=False):
        entry = {
            "module": module,
            "status": status,
            "source": source,
            "message": str(message) if message else "",
            "cache_hit": bool(cache_hit),
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        }
        self.records.append(entry)
        return entry

    def ok(self, module, source="", message="", cache_hit=False):
        return self.record(module, "ok", source, message, cache_hit)

    def fail(self, module, source="", message=""):
        return self.record(module, "failed", source, message, False)

    def skip(self, module, source="", message=""):
        return self.record(module, "skipped", source, message, False)

    def counts(self):
        result = {"ok": 0, "failed": 0, "skipped": 0, "cache_hits": 0}
        for item in self.records:
            result[item["status"]] = result.get(item["status"], 0) + 1
            if item.get("cache_hit"):
                result["cache_hits"] += 1
        return result

    def summary_text(self):
        c = self.counts()
        return f"ok={c.get('ok', 0)}, failed={c.get('failed', 0)}, skipped={c.get('skipped', 0)}, cache_hits={c.get('cache_hits', 0)}"

    def markdown_lines(self):
        lines = ["## 运行摘要", ""]
        lines.append(f"- 数据模块: {self.summary_text()}")
        if self.records:
            lines.append("- 模块明细:")
            for item in self.records:
                parts = [item["module"], item["status"]]
                if item.get("source"):
                    parts.append(f"source={item['source']}")
                if item.get("cache_hit"):
                    parts.append("cache=hit")
                if item.get("message"):
                    parts.append(f"message={item['message']}")
                lines.append(f"  - {' | '.join(parts)}")
        lines.append("")
        return lines


def dependency_available(module_name):
    """Return whether a Python module is importable without importing it."""
    return importlib.util.find_spec(module_name) is not None


def missing_dependencies(module_names):
    """Return a list of missing module names."""
    return [name for name in module_names if not dependency_available(name)]


def safe_call(tracker, module, source, func, fallback=None):
    """Call a data function and record success/failure without raising."""
    try:
        value = func()
    except Exception as exc:
        if tracker:
            tracker.fail(module, source, exc)
        return fallback
    if tracker:
        tracker.ok(module, source)
    return value


def _cache_path(settings, key):
    dirs = get_report_dirs(settings)
    cache_dir = dirs["cache_dir"]
    cache_dir.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]
    return cache_dir / f"{digest}.pkl"


def cached_call(settings, tracker, module, source, cache_key, producer, fallback=None):
    """Best-effort pickle cache around external data calls."""
    use_cache = bool(settings.get("use_cache", True))
    ttl_seconds = float(settings.get("cache_ttl_hours", 6)) * 3600
    path = None
    if use_cache:
        try:
            path = _cache_path(settings, cache_key)
            if path.exists() and time.time() - path.stat().st_mtime <= ttl_seconds:
                with path.open("rb") as f:
                    value = pickle.load(f)
                if tracker:
                    tracker.ok(module, source, "cache hit", cache_hit=True)
                return value
        except Exception:
            path = None

    def produce():
        value = producer()
        if path is not None:
            try:
                with path.open("wb") as f:
                    pickle.dump(value, f)
            except Exception:
                pass
        return value

    return safe_call(tracker, module, source, produce, fallback)


def status_records_json(tracker):
    return json.dumps(tracker.records if tracker else [], ensure_ascii=False)
