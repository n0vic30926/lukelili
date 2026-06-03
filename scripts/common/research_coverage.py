"""Cross-role research data coverage scoring."""


AVAILABLE_STATUSES = {"available", "success"}

STATUS_GAP_SCORE = {
    "failed": 90,
    "missing_key": 85,
    "missing_file": 86,
    "missing_dependency": 65,
    "unknown": 60,
    "empty": 45,
    "missing_method": 45,
    "missing_nav": 45,
    "skipped": 35,
}

ROLE_GAP_SCORE = {
    "risk": 10,
    "security": 10,
    "industry": 8,
    "macro": 6,
    "etf": 6,
    "review": 4,
}

SOURCE_TIER_GAP_SCORE = {
    "local_user_data": 10,
    "community_data": 6,
    "news_search": 5,
    "official_data": 6,
    "unknown": 0,
}


def _status(value):
    return str(value or "unknown")


def _priority(score):
    if score >= 90:
        return "high"
    if score >= 70:
        return "medium"
    return "low"


def _gap_score(role, source):
    status = _status(source.get("status"))
    score = STATUS_GAP_SCORE.get(status, STATUS_GAP_SCORE["unknown"])
    score += ROLE_GAP_SCORE.get(str(role or "unknown"), 0)
    score += SOURCE_TIER_GAP_SCORE.get(str(source.get("source_tier") or "unknown"), 0)
    return score


def _gap_item(role, source):
    score = _gap_score(role, source)
    return {
        "role": str(role or "unknown"),
        "source": str(source.get("name") or "unknown"),
        "status": _status(source.get("status")),
        "source_tier": str(source.get("source_tier") or "unknown"),
        "score": score,
        "priority": _priority(score),
    }


def build_research_coverage_matrix(research_result):
    role_results = list((research_result or {}).get("role_results") or [])
    role_count = len(role_results)
    requirement_count = 0
    available_count = 0
    gaps = []
    role_summaries = []

    for role_result in role_results:
        role = str(role_result.get("role") or "unknown")
        sources = list(role_result.get("data_sources") or [])
        role_total = len(sources)
        role_available = 0
        for source in sources:
            requirement_count += 1
            if _status(source.get("status")) in AVAILABLE_STATUSES:
                available_count += 1
                role_available += 1
            else:
                gaps.append(_gap_item(role, source))
        role_coverage = round(role_available / role_total * 100, 1) if role_total else 0.0
        role_summaries.append(
            {
                "role": role,
                "requirement_count": role_total,
                "available_count": role_available,
                "coverage_pct": role_coverage,
            }
        )

    coverage_pct = (
        round(available_count / requirement_count * 100, 1)
        if requirement_count
        else 0.0
    )
    gaps.sort(key=lambda item: (-item["score"], item["role"], item["source"]))
    return {
        "role_count": role_count,
        "requirement_count": requirement_count,
        "available_count": available_count,
        "unavailable_count": requirement_count - available_count,
        "coverage_pct": coverage_pct,
        "roles": role_summaries,
        "gaps": gaps,
    }


def format_research_coverage(matrix, gap_limit=8):
    lines = ["## Research Coverage Matrix"]
    lines.append("- role_count=" + str(matrix.get("role_count", 0)))
    lines.append("- requirement_count=" + str(matrix.get("requirement_count", 0)))
    lines.append("- available_count=" + str(matrix.get("available_count", 0)))
    lines.append("- unavailable_count=" + str(matrix.get("unavailable_count", 0)))
    lines.append("- coverage_pct=" + str(matrix.get("coverage_pct", 0.0)))
    for role in matrix.get("roles") or []:
        lines.append(
            "- role="
            + str(role.get("role") or "unknown")
            + " coverage_pct="
            + str(role.get("coverage_pct", 0.0))
            + " available="
            + str(role.get("available_count", 0))
            + "/"
            + str(role.get("requirement_count", 0))
        )
    for gap in (matrix.get("gaps") or [])[:gap_limit]:
        lines.append(
            "- role="
            + str(gap.get("role") or "unknown")
            + " source="
            + str(gap.get("source") or "unknown")
            + " status="
            + str(gap.get("status") or "unknown")
            + " priority="
            + str(gap.get("priority") or "low")
        )
    return "\n".join(lines)
