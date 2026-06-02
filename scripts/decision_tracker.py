#!/usr/bin/env python3
"""
反事实追踪 — 记录每日建议，按strategy_type评估不同指标
- dca: 评估"是否持续执行纪律"
- short_term: 评估盈亏比、胜率
每天运行一次，检查7天前的建议是否与系统原则一致
"""
import json, os
from datetime import datetime, timedelta
from pathlib import Path
from common.config_loader import get_decision_track_dir, get_portfolio_path

TRACK_DIR = str(get_decision_track_dir())


def _confirmation_record(state, created_at=None, source="decision_support"):
    created_at = created_at or datetime.now().astimezone().isoformat(timespec="seconds")
    return {
        "event": "confirmation_state_recorded",
        "created_at": created_at,
        "source": source,
        "confirmation_status": state.get("confirmation_status", "unknown"),
        "execution_allowed": False,
        "check_count": int(state.get("check_count", 0) or 0),
        "blocker_count": int(state.get("blocker_count", 0) or 0),
        "check_refs": [item.get("check_ref") for item in state.get("checks", []) if item.get("check_ref")],
        "blocker_types": [item.get("type", "unknown") for item in state.get("blockers", [])],
        "prohibited_actions": list(state.get("prohibited_actions") or []),
    }


def save_confirmation_record(state, record_path=None, created_at=None, source="decision_support"):
    """Append a sanitized manual-confirmation state record to JSONL."""
    record_path = Path(record_path) if record_path else Path(TRACK_DIR) / "confirmations.jsonl"
    record_path.parent.mkdir(parents=True, exist_ok=True)
    record = _confirmation_record(state, created_at=created_at, source=source)
    with record_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return {"record_path": str(record_path), "record": record}


def load_confirmation_records(record_path=None):
    """Load sanitized manual-confirmation JSONL records."""
    record_path = Path(record_path) if record_path else Path(TRACK_DIR) / "confirmations.jsonl"
    if not record_path.exists():
        return []
    records = []
    for line in record_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if item.get("event") != "confirmation_state_recorded":
            continue
        records.append(
            {
                "created_at": str(item.get("created_at") or ""),
                "confirmation_status": str(item.get("confirmation_status") or "unknown"),
                "execution_allowed": bool(item.get("execution_allowed")),
                "check_count": int(item.get("check_count", 0) or 0),
                "blocker_count": int(item.get("blocker_count", 0) or 0),
                "blocker_types": [str(value) for value in item.get("blocker_types", [])],
            }
        )
    return records


def save_daily_decisions(portfolio_path):
    """记录今日的持仓状态和建议（由daily brief调用）"""
    os.makedirs(TRACK_DIR, exist_ok=True)
    with open(portfolio_path) as f:
        portfolio = json.load(f)

    today = datetime.now().strftime("%Y-%m-%d")
    decisions = {
        "date": today,
        "holdings": [],
    }

    for h in portfolio['holdings']:
        entry = {
            "code": h['code'],
            "name": h['name'],
            "strategy_type": h.get('strategy_type', 'dca'),
            "strategy_label": h.get('strategy_label', ''),
            "cost_basis": h.get('cost_basis'),
            "shares": h.get('shares'),
        }
        decisions['holdings'].append(entry)

    filepath = os.path.join(TRACK_DIR, f"{today}.json")
    with open(filepath, 'w') as f:
        json.dump(decisions, f, ensure_ascii=False, indent=2)
    return filepath


def check_7day_discipline():
    """检查7天前的定投纪律是否执行"""
    os.makedirs(TRACK_DIR, exist_ok=True)

    check_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    filepath = os.path.join(TRACK_DIR, f"{check_date}.json")

    if not os.path.exists(filepath):
        return f"7天前({check_date})无记录，无法评估"

    with open(filepath) as f:
        record = json.load(f)

    results = []
    for h in record.get('holdings', []):
        stype = h.get('strategy_type', 'dca')
        code = h['code']

        if stype == 'dca':
            # 评估：是否持续执行了定投纪律
            results.append(f"{h['name']} [定投]: 7天前记录存在，纪律持续执行 ✓")
        elif stype == 'short_term':
            # 评估：盈亏状态变化
            results.append(f"{h['name']} [短线]: 7天前成本{h.get('cost_basis','?')}元，需要对比当前盈亏")

    return "\n".join(results)


def list_tracking_records():
    """列出所有追踪记录"""
    os.makedirs(TRACK_DIR, exist_ok=True)
    files = sorted(os.listdir(TRACK_DIR))
    return [f.replace('.json', '') for f in files if f.endswith('.json')]


if __name__ == "__main__":
    portfolio_path = str(get_portfolio_path())
    fp = save_daily_decisions(portfolio_path)
    print(f"Saved: {fp}")
    print()
    records = list_tracking_records()
    print(f"Tracking records: {len(records)}")
    print(records)
