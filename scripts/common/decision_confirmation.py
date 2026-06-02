"""Manual confirmation state for decision-support packets."""


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


def build_confirmation_state(packet):
    checks = _unique_confirmations(packet.get("candidates") or [])
    blockers = _blockers(packet)
    return {
        "mode": "manual_confirmation_required",
        "confirmation_status": "pending_user_confirmation",
        "execution_allowed": False,
        "requires_user_confirmation": True,
        "check_count": len(checks),
        "blocker_count": len(blockers),
        "checks": checks,
        "blockers": blockers,
        "prohibited_actions": list(packet.get("prohibited_actions") or []),
    }


def format_confirmation_state(state):
    lines = ["## Manual Confirmation Workflow"]
    lines.append(f"- mode={state['mode']}")
    lines.append(f"- confirmation_status={state['confirmation_status']}")
    lines.append(f"- execution_allowed={str(state['execution_allowed']).lower()}")
    lines.append(f"- checks={state['check_count']} blockers={state['blocker_count']}")
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
    return "\n".join(lines)
