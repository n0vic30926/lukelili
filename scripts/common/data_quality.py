"""Data source tiering and freshness labels."""

from datetime import datetime


SOURCE_TIERS = {
    "akshare": "community_data",
    "tavily": "news_search",
    "local": "local_user_data",
    "example": "example_data",
}


def source_tier(source):
    normalized = str(source or "").strip().lower()
    return SOURCE_TIERS.get(normalized, "unknown")


def _parse_time(value):
    if not value:
        return None
    text = str(value)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def freshness_label(observed_at, current_time, max_age_hours=24):
    observed = _parse_time(observed_at)
    current = _parse_time(current_time)
    if observed is None or current is None:
        return "unknown"
    age_seconds = (current - observed).total_seconds()
    if age_seconds < 0:
        return "unknown"
    return "fresh" if age_seconds <= max_age_hours * 3600 else "stale"

