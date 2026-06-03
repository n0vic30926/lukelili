"""Cross-role research synthesis for decision-support confirmation audit."""

from common.evidence import rank_evidence
from common.research_coverage import build_research_coverage_matrix


UNAVAILABLE_STATUSES = {
    "empty",
    "failed",
    "missing_dependency",
    "missing_file",
    "missing_key",
    "missing_method",
    "missing_nav",
    "skipped",
    "unknown",
}


def _count_by(values):
    counts = {}
    for value in values:
        key = str(value or "unknown")
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def _source_ref(role, source_name):
    return f"{role}.{source_name}"


def synthesize_research_result(research_result, evidence_limit=8, gap_limit=12):
    """Summarize multi-role research into a bounded confirmation-audit view."""
    role_results = list((research_result or {}).get("role_results") or [])
    role_status_counts = _count_by(item.get("status") for item in role_results)
    source_statuses = []
    unavailable_sources = []
    confirmation_audit_items = []
    evidence = []

    for role_result in role_results:
        role = str(role_result.get("role") or "unknown")
        if str(role_result.get("status") or "unknown") != "ok":
            confirmation_audit_items.append(
                {
                    "type": "role_status_unconfirmed",
                    "role": role,
                    "status": str(role_result.get("status") or "unknown"),
                }
            )
        evidence.extend(role_result.get("evidence") or [])
        for source in role_result.get("data_sources") or []:
            source_name = str(source.get("name") or "unknown")
            status = str(source.get("status") or "unknown")
            source_statuses.append(status)
            if status in UNAVAILABLE_STATUSES:
                item = {
                    "role": role,
                    "source": source_name,
                    "status": status,
                    "source_ref": _source_ref(role, source_name),
                }
                unavailable_sources.append(item)
                confirmation_audit_items.append(
                    {
                        "type": "data_source_unconfirmed",
                        "role": role,
                        "source": source_name,
                        "status": status,
                    }
                )

    return {
        "role_count": len(role_results),
        "role_status_counts": role_status_counts,
        "data_source_status_counts": _count_by(source_statuses),
        "coverage": build_research_coverage_matrix(research_result),
        "unavailable_sources": unavailable_sources[:gap_limit],
        "confirmation_audit_items": confirmation_audit_items[:gap_limit],
        "ranked_evidence": rank_evidence(evidence)[:evidence_limit],
    }
