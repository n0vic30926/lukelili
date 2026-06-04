#!/usr/bin/env python3
"""Offline test for historical review summaries."""

import json
import tempfile
from pathlib import Path

from review_history import format_review, load_decision_records


def _assert_contains(text, expected):
    if expected not in text:
        raise AssertionError(f"Expected review to contain: {expected}")


def run_format_review_test():
    tmp_reports = tempfile.TemporaryDirectory()
    report_dir = Path(tmp_reports.name)
    daily_path = report_dir / "daily-2026-01-01.md"
    weekly_path = report_dir / "weekly-2026-01-03.md"
    daily_path.write_text("# Daily\nNo action evidence yet.\n", encoding="utf-8")
    weekly_path.write_text("# Weekly\nReview marker: continue_dca discipline follow-up.\n", encoding="utf-8")
    report_records = [
        {
            "type": "daily",
            "path": str(daily_path),
            "created_at": "2026-01-01T15:30:00",
            "status_counts": {"ok": 3, "failed": 1, "skipped": 1},
            "events": [
                {"module": "north_flow", "status": "failed", "source": "AkShare"},
                {"module": "industry_cycle", "status": "skipped", "source": "Tavily"},
            ],
        },
        {
            "type": "weekly",
            "path": str(weekly_path),
            "created_at": "2026-01-03T11:00:00Z",
            "status_counts": {"ok": 2, "failed": 1, "skipped": 1},
            "events": [
                {"module": "north_flow", "status": "failed", "source": "AkShare"},
                {"module": "valuation_anchor", "status": "failed", "source": "AkShare"},
            ],
        },
    ]
    decision_records = [
        {
            "date": "2026-01-01",
            "holdings": [
                {"code": "EX1", "strategy_type": "dca", "cost_basis": 100, "shares": 10},
                {"code": "EX2", "strategy_type": "trial", "cost_basis": 50, "shares": 5},
                {"code": "EX3", "strategy_type": "short_term", "cost_basis": 20, "shares": 2},
                {"code": "EX4", "strategy_type": "watch"},
            ],
            "user_actions": [
                {
                    "action_type": "upgrade_strategy",
                    "status": "pending",
                    "strategy_type": "trial",
                    "requires_user_confirmation": True,
                    "code": "EX2",
                    "amount": 12345,
                    "rationale": "Synthetic private rationale that must not be printed.",
                },
                {
                    "action_type": "continue_dca",
                    "status": "confirmed",
                    "strategy_type": "dca",
                    "requires_user_confirmation": False,
                    "confirmed_at": "2026-01-02T09:00:00",
                    "outcome_quality": "aligned",
                    "checklist": {
                        "discipline": "pass",
                        "risk_boundary": "pass",
                        "source_evidence": "missing",
                    },
                    "code": "EX1",
                },
                {
                    "action_type": "exit_trial",
                    "status": "confirmed",
                    "strategy_type": "trial",
                    "requires_user_confirmation": True,
                    "confirmed_at": "2026-01-04T09:00:00",
                    "outcome_status": "reviewed",
                    "outcome_quality": "mixed",
                    "checklist": {
                        "discipline": "pass",
                        "risk_boundary": "fail",
                        "source_evidence": "pass",
                    },
                    "outcome_review": "Synthetic private outcome that must not be printed.",
                    "code": "EX2",
                },
            ],
        }
    ]
    review = format_review(Path("reports/index.jsonl"), report_records, Path("data/private/decision_track"), decision_records)
    _assert_contains(review, "历史复盘摘要")
    _assert_contains(review, "报告数量: 2")
    _assert_contains(review, "报告连续性")
    _assert_contains(review, "报告日期范围: 2026-01-01 → 2026-01-03")
    _assert_contains(review, "最大报告间隔: 2 天")
    _assert_contains(review, "当前连续报告天数: 1")
    _assert_contains(review, "重复失败检测")
    _assert_contains(review, "有事件明细的报告: 2")
    _assert_contains(review, "失败模块分布: {'north_flow': 2, 'valuation_anchor': 1}")
    _assert_contains(review, "重复失败模块: {'north_flow': 2}")
    _assert_contains(review, "跳过模块分布: {'industry_cycle': 1}")
    _assert_contains(review, "strategy_type 分布")
    _assert_contains(review, "DCA记录存在")
    _assert_contains(review, "策略评分卡")
    _assert_contains(review, "dca: score=")
    _assert_contains(review, "trial: score=")
    _assert_contains(review, "short_term: score=")
    _assert_contains(review, "status=missing_rules")
    _assert_contains(review, "watch: score=")
    _assert_contains(review, "用户确认动作")
    _assert_contains(review, "状态分布: {'pending': 1, 'confirmed': 2}")
    _assert_contains(review, "动作类型分布: {'upgrade_strategy': 1, 'continue_dca': 1, 'exit_trial': 1}")
    _assert_contains(review, "需要用户确认且未完成: 1")
    _assert_contains(review, "确认后结果复盘")
    _assert_contains(review, "已确认动作: 2")
    _assert_contains(review, "结果状态分布: {'pending_review': 1, 'reviewed': 1}")
    _assert_contains(review, "待结果复盘: 1")
    _assert_contains(review, "结果质量分布: {'aligned': 1, 'mixed': 1}")
    _assert_contains(review, "检查项状态分布: {'pass': 4, 'missing': 1, 'fail': 1}")
    _assert_contains(review, "失败或缺失检查项: 2")
    _assert_contains(review, "跨报告归因")
    _assert_contains(review, "有后续报告证据: 1")
    _assert_contains(review, "缺少后续报告证据: 1")
    _assert_contains(review, "后续报告类型分布: {'weekly': 1}")
    _assert_contains(review, "后续报告内容命中: 1")
    _assert_contains(review, "有后续报告但未命中内容: 0")
    _assert_contains(review, "后续报告不可读取: 0")
    tmp_reports.cleanup()
    if "cost_basis" in review or "shares" in review or "amount" in review:
        raise AssertionError("Review leaked raw asset field names")
    if "EX1" in review or "EX2" in review or "EX3" in review or "EX4" in review:
        raise AssertionError("Review leaked asset codes")
    if "Synthetic private rationale" in review:
        raise AssertionError("Review leaked private rationale")
    if "Synthetic private outcome" in review:
        raise AssertionError("Review leaked private outcome")


def run_load_private_records_test():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "2026-01-01.json"
        path.write_text(
            json.dumps({"date": "2026-01-01", "holdings": [{"code": "EX", "strategy_type": "dca"}]}),
            encoding="utf-8",
        )
        _, records = load_decision_records(decision_dir=tmp)
        if len(records) != 1:
            raise AssertionError("Expected one private decision record")


def main():
    run_format_review_test()
    run_load_private_records_test()
    print("Mock review test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
