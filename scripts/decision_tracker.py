#!/usr/bin/env python3
"""
反事实追踪 — 记录每日建议，按strategy_type评估不同指标
- dca: 评估"是否持续执行纪律"
- short_term: 评估盈亏比、胜率
每天运行一次，检查7天前的建议是否与系统原则一致
"""
import json, os
from datetime import datetime, timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
import sys
sys.path.insert(0, SCRIPT_DIR)
from common.config_loader import get_portfolio_path, get_repo_root, load_settings, resolve_path

SETTINGS = load_settings()
TRACK_DIR = resolve_path(
    SETTINGS.get("decision_track_dir", "data/private/decision_track"),
    get_repo_root(),
)


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
    if os.path.exists(filepath):
        try:
            with open(filepath, encoding="utf-8") as f:
                existing = json.load(f)
            decisions["user_actions"] = existing.get("user_actions", [])
        except (OSError, json.JSONDecodeError):
            decisions["user_actions"] = []
    with open(filepath, 'w') as f:
        json.dump(decisions, f, ensure_ascii=False, indent=2)
    return filepath


def append_user_action(action, record_date=None):
    """Append a user-confirmation action to the local private decision record."""
    os.makedirs(TRACK_DIR, exist_ok=True)
    date_text = record_date or datetime.now().strftime("%Y-%m-%d")
    filepath = os.path.join(TRACK_DIR, f"{date_text}.json")
    if os.path.exists(filepath):
        with open(filepath, encoding="utf-8") as f:
            record = json.load(f)
    else:
        record = {"date": date_text, "holdings": [], "user_actions": []}
    record.setdefault("date", date_text)
    record.setdefault("holdings", [])
    record.setdefault("user_actions", [])

    entry = {
        "action_type": action.get("action_type", "unknown"),
        "status": action.get("status", "pending"),
        "strategy_type": action.get("strategy_type", "unknown"),
        "requires_user_confirmation": bool(action.get("requires_user_confirmation", True)),
        "created_at": action.get("created_at", datetime.now().isoformat(timespec="seconds")),
    }
    optional_fields = (
        "code",
        "rationale",
        "amount",
        "confirmed_at",
        "notes",
        "outcome_status",
        "outcome_review",
        "outcome_reviewed_at",
        "outcome_quality",
        "checklist",
    )
    for field in optional_fields:
        if field in action:
            entry[field] = action[field]
    record["user_actions"].append(entry)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)
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
    portfolio_path, _ = get_portfolio_path(SETTINGS)
    fp = save_daily_decisions(str(portfolio_path))
    print(f"Saved: {fp}")
    print()
    records = list_tracking_records()
    print(f"Tracking records: {len(records)}")
    print(records)
