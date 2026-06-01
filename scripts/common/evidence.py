"""Evidence reliability scoring and formatting."""


SOURCE_TIER_SCORE = {
    "local_user_data": 40,
    "official_data": 35,
    "community_data": 25,
    "news_search": 15,
    "example_data": 5,
    "unknown": 0,
}

FRESHNESS_SCORE = {
    "fresh": 30,
    "stale": 10,
    "unknown": 0,
}


def evidence_score(item):
    source_tier = str(item.get("source_tier") or "unknown")
    freshness = str(item.get("freshness") or "unknown")
    return SOURCE_TIER_SCORE.get(source_tier, 0) + FRESHNESS_SCORE.get(freshness, 0)


def normalize_evidence(item):
    if isinstance(item, str):
        item = {"label": item}
    normalized = {
        "label": str(item.get("label") or item.get("source") or "unknown"),
        "source_tier": str(item.get("source_tier") or "unknown"),
        "freshness": str(item.get("freshness") or "unknown"),
    }
    if item.get("detail"):
        normalized["detail"] = str(item["detail"])
    normalized["score"] = evidence_score(normalized)
    return normalized


def rank_evidence(items):
    normalized = [normalize_evidence(item) for item in items or []]
    return sorted(normalized, key=lambda item: (-item["score"], item["label"]))


def format_evidence_list(items):
    lines = []
    for item in rank_evidence(items):
        line = (
            f"{item['label']} | source_tier={item['source_tier']} "
            f"| freshness={item['freshness']} | score={item['score']}"
        )
        if item.get("detail"):
            line += f" | detail={item['detail']}"
        lines.append(line)
    return "\n".join(lines)
