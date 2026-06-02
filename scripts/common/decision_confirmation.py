"""Manual confirmation state for decision-support packets."""


LOCAL_RECORD_SOURCES = {"report_index", "decision_records", "confirmation_records"}
REFRESH_STATUSES = {
    "failed",
    "missing_dependency",
    "missing_key",
    "missing_method",
    "missing_nav",
    "skipped",
    "unknown",
}


def _unique_confirmations(candidates):
    checks = []
    seen = set()
    for candidate in candidates or []:
        candidate_ref = str(candidate.get("holding_ref") or "holding_unknown")
        for text in candidate.get("required_confirmations") or []:
            text = str(text)
            key = (candidate_ref, text)
            if key in seen:
                continue
            seen.add(key)
            checks.append(
                {
                    "check_ref": f"confirmation_{len(checks) + 1}",
                    "candidate_ref": candidate_ref,
                    "status": "pending",
                    "text": text,
                }
            )
    return checks


def _blockers(packet):
    blockers = []
    for item in packet.get("risk_rule_checks") or []:
        if item.get("status") == "missing":
            blockers.append({"type": "missing_risk_rule", "rule": item.get("rule")})
    for item in (packet.get("exposure") or {}).get("warnings") or []:
        blockers.append(
            {
                "type": item.get("type", "exposure_warning"),
                "holding_ref": item.get("holding_ref", ""),
                "actual_pct": item.get("actual_pct"),
                "limit_pct": item.get("limit_pct"),
            }
        )
    for item in (packet.get("research_synthesis") or {}).get("confirmation_audit_items") or []:
        if item.get("type") == "data_source_unconfirmed":
            blockers.append(
                {
                    "type": "research_data_source_unconfirmed",
                    "role": item.get("role", "unknown"),
                    "source": item.get("source", "unknown"),
                    "status": item.get("status", "unknown"),
                }
            )
        elif item.get("type") == "role_status_unconfirmed":
            blockers.append(
                {
                    "type": "research_role_status_unconfirmed",
                    "role": item.get("role", "unknown"),
                    "status": item.get("status", "unknown"),
                }
            )
    return blockers


def _review_queue(checks, blockers):
    queue = []
    for check in checks:
        queue.append(
            {
                "review_ref": f"review_{len(queue) + 1}",
                "source_ref": check.get("check_ref", ""),
                "action": "user_confirm",
                "status": "pending",
                "reason": "manual confirmation check",
            }
        )
    for blocker in blockers:
        blocker_type = blocker.get("type", "unknown")
        action = "user_confirm"
        reason = blocker_type
        if blocker_type == "missing_risk_rule":
            action = "update_local_records"
            reason = f"missing risk rule {blocker.get('rule')}"
        elif blocker_type == "research_data_source_unconfirmed":
            source = str(blocker.get("source") or "")
            status = str(blocker.get("status") or "unknown")
            if source in LOCAL_RECORD_SOURCES or status in {"empty", "missing_file"}:
                action = "update_local_records"
            elif status in REFRESH_STATUSES:
                action = "refresh_data"
            else:
                action = "user_confirm"
            reason = f"{blocker.get('role')}.{source} status={status}"
        elif blocker_type == "research_role_status_unconfirmed":
            action = "refresh_data"
            reason = f"{blocker.get('role')} status={blocker.get('status')}"
        elif blocker_type.endswith("_exceeds_rule") or blocker_type.endswith("_warning"):
            action = "review_risk_rule"

        queue.append(
            {
                "review_ref": f"review_{len(queue) + 1}",
                "source_ref": blocker_type,
                "action": action,
                "status": "pending",
                "reason": str(reason),
            }
        )
    return queue


def _count_actions(queue):
    counts = {}
    for item in queue or []:
        action = str(item.get("action") or "unknown")
        counts[action] = counts.get(action, 0) + 1
    return dict(sorted(counts.items()))


def build_confirmation_state(packet):
    checks = _unique_confirmations(packet.get("candidates") or [])
    blockers = _blockers(packet)
    review_queue = _review_queue(checks, blockers)
    return {
        "mode": "manual_confirmation_required",
        "confirmation_status": "pending_user_confirmation",
        "execution_allowed": False,
        "requires_user_confirmation": True,
        "check_count": len(checks),
        "blocker_count": len(blockers),
        "review_queue_count": len(review_queue),
        "review_action_counts": _count_actions(review_queue),
        "checks": checks,
        "blockers": blockers,
        "review_queue": review_queue,
        "prohibited_actions": list(packet.get("prohibited_actions") or []),
    }


def format_confirmation_state(state):
    lines = ["## Manual Confirmation Workflow"]
    lines.append(f"- mode={state['mode']}")
    lines.append(f"- confirmation_status={state['confirmation_status']}")
    lines.append(f"- execution_allowed={str(state['execution_allowed']).lower()}")
    lines.append(f"- checks={state['check_count']} blockers={state['blocker_count']}")
    lines.append(f"- review_queue={state.get('review_queue_count', 0)}")
    if state.get("review_action_counts"):
        counts = " ".join(
            f"{key}={state['review_action_counts'][key]}" for key in sorted(state["review_action_counts"])
        )
        lines.append(f"- review_actions: {counts}")
    for item in state.get("checks") or []:
        lines.append(
            "- "
            f"{item['check_ref']} status={item['status']} "
            f"candidate_ref={item['candidate_ref']} text={item['text']}"
        )
    for item in state.get("blockers") or []:
        if item.get("type") == "missing_risk_rule":
            lines.append(f"- missing_risk_rule rule={item.get('rule')}")
        elif item.get("type") == "research_data_source_unconfirmed":
            lines.append(
                "- "
                f"research_data_source_unconfirmed role={item.get('role')} "
                f"source={item.get('source')} status={item.get('status')}"
            )
        elif item.get("type") == "research_role_status_unconfirmed":
            lines.append(
                "- "
                f"research_role_status_unconfirmed role={item.get('role')} "
                f"status={item.get('status')}"
            )
        else:
            lines.append(
                "- "
                f"{item.get('type')} holding_ref={item.get('holding_ref')} "
                f"actual_pct={item.get('actual_pct')} limit_pct={item.get('limit_pct')}"
            )
    for item in state.get("review_queue") or []:
        lines.append(
            "- "
            f"{item.get('review_ref')} action={item.get('action')} "
            f"status={item.get('status')} source_ref={item.get('source_ref')} "
            f"reason={item.get('reason')}"
        )
    return "\n".join(lines)
