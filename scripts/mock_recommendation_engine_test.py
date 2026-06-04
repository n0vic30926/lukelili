#!/usr/bin/env python3
"""Offline tests for first-class ranked recommendation packets."""

from common.recommendations import build_recommendations, format_recommendations


def _assert_contains(text, expected):
    if expected not in text:
        raise AssertionError(f"Expected text to contain: {expected}")


def _assert_not_contains(text, unexpected):
    if unexpected in text:
        raise AssertionError(f"Text should not contain: {unexpected}")


def run_ranked_recommendation_test():
    portfolio = {
        "holdings": [
            {
                "code": "PRIVATE_A",
                "name": "Private Holding A",
                "strategy_type": "dca",
                "cost_basis": 1000,
                "target_weight_pct": 50,
                "factor_profile": {"type": "qdii_us_equity"},
            },
            {
                "code": "PRIVATE_B",
                "name": "Private Holding B",
                "strategy_type": "short_term",
                "cost_basis": 400,
                "target_weight_pct": 20,
                "factor_profile": {"type": "a_share_ai"},
            },
        ],
        "cash": {"amount": 1600, "target_weight_pct": 30},
        "risk_rules": {
            "single_loss_pct": 2,
            "daily_loss_pct": 6,
            "max_single_position_pct": 60,
            "rebalance_tolerance_pct": 5,
        },
    }
    research_result = {
        "role_results": [
            {
                "role": "risk",
                "status": "ok",
                "observations": ["cash buffer high", "market quotes unavailable"],
                "evidence": [
                    {
                        "label": "portfolio.risk_rules",
                        "source_tier": "local_user_data",
                        "freshness": "fresh",
                        "score": 70,
                    }
                ],
                "data_sources": [
                    {"name": "risk_rules", "status": "available"},
                    {"name": "market_quotes", "status": "missing_dependency"},
                ],
            }
        ]
    }
    scenario_review = {
        "boundary": {"projection": "model projection, not a fact"},
        "scenarios": [
            {
                "name": "stress_drawdown",
                "portfolio_impact_pct": -9.0,
                "risk_flags": [{"type": "scenario_loss_exceeds_daily_loss_rule"}],
                "decision_signals": [
                    {
                        "signal": "risk_reduction_review",
                        "reason": "scenario loss exceeds configured daily loss rule",
                        "requires_user_confirmation": True,
                    }
                ],
            }
        ],
    }
    rebalance_review = {
        "max_abs_drift_pct": 23.3,
        "decision_signals": [
            {
                "position_ref": "cash",
                "signal": "rebalance_review",
                "status": "overweight",
                "drift_pct": 23.3,
                "requires_user_confirmation": True,
            },
            {
                "position_ref": "holding_1",
                "signal": "rebalance_review",
                "status": "underweight",
                "drift_pct": -16.7,
                "requires_user_confirmation": True,
            },
        ],
    }
    backtest = {
        "observation_count": 5,
        "period_return_pct": 3.2,
        "max_drawdown_pct": -8.5,
        "annualized_volatility_pct": 18.0,
        "warnings": [],
    }

    recommendations = build_recommendations(
        portfolio,
        research_result=research_result,
        scenario_review=scenario_review,
        rebalance_review=rebalance_review,
        backtest=backtest,
    )
    if len(recommendations) < 3:
        raise AssertionError(f"Expected at least three recommendations: {recommendations}")
    if recommendations[0]["rank"] != 1:
        raise AssertionError(f"Expected rank to start at one: {recommendations}")
    if recommendations[0]["action"] != "reduce_risk":
        raise AssertionError(f"Expected risk reduction to rank first: {recommendations}")
    if recommendations[0]["status"] != "recommended":
        raise AssertionError(f"Expected recommendation status: {recommendations[0]}")
    if recommendations[0]["confidence"] < recommendations[-1]["confidence"]:
        raise AssertionError(f"Expected descending confidence: {recommendations}")
    for item in recommendations:
        for field in [
            "recommendation_id",
            "action",
            "instrument_ref",
            "direction",
            "horizon",
            "confidence",
            "status",
            "rationale",
            "risks",
            "invalidators",
            "position_effect",
            "next_action",
            "execution_allowed",
        ]:
            if field not in item:
                raise AssertionError(f"Missing {field}: {item}")
        if item["execution_allowed"] is not False:
            raise AssertionError(f"Execution must stay false: {item}")
        if "PRIVATE" in str(item) or "Private Holding" in str(item):
            raise AssertionError(f"Recommendation leaked private identifiers: {item}")

    output = format_recommendations(recommendations)
    _assert_contains(output, "## Ranked Recommendations")
    _assert_contains(output, "rank=1")
    _assert_contains(output, "action=reduce_risk")
    _assert_contains(output, "direction=reduce")
    _assert_contains(output, "confidence=")
    _assert_contains(output, "invalidators=")
    _assert_contains(output, "next_action=")
    _assert_contains(output, "execution_allowed=false")
    _assert_not_contains(output, "PRIVATE_A")
    _assert_not_contains(output, "Private Holding")


def main():
    run_ranked_recommendation_test()
    print("Mock recommendation engine test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
