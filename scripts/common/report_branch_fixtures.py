"""Sanitized report branch fixtures for offline report-path checks."""


def _portfolio(strategy_type="dca"):
    return {
        "holdings": [{"strategy_type": strategy_type, "factor_profile": {"type": "example_factor"}}],
        "watchlist": [{"reason": "example watch item"}],
    }


def report_branch_fixtures():
    """Return sanitized daily/weekly report branch fixtures."""
    return [
        {
            "name": "daily_all_available",
            "report_type": "daily",
            "portfolio": _portfolio("dca"),
            "run_summary": {
                "portfolio_source": "example",
                "is_example_data": True,
                "modules": {"success": 4, "failed": 0, "skipped": 0, "cache_hit": 1},
                "data_quality": {
                    "fresh": 3,
                    "stale": 0,
                    "unknown": 1,
                    "source_tiers": {"community_data": 3, "local_user_data": 1},
                },
                "data_modules": [
                    {"module": "fund_nav", "status": "success", "source": "AkShare", "freshness": "fresh"},
                    {"module": "north_flow", "status": "success", "source": "AkShare", "freshness": "unknown"},
                    {"module": "report_cache", "status": "success", "source": "local", "freshness": "fresh"},
                ],
            },
        },
        {
            "name": "daily_degraded_data",
            "report_type": "daily",
            "portfolio": _portfolio("trial"),
            "run_summary": {
                "portfolio_source": "example",
                "is_example_data": True,
                "modules": {"success": 1, "failed": 2, "skipped": 0, "cache_hit": 0},
                "data_quality": {
                    "fresh": 1,
                    "stale": 0,
                    "unknown": 2,
                    "source_tiers": {"community_data": 2, "local_user_data": 1},
                },
                "data_modules": [
                    {"module": "fund_nav", "status": "success", "source": "AkShare", "freshness": "fresh"},
                    {
                        "module": "north_flow",
                        "status": "failed",
                        "source": "AkShare",
                        "freshness": "unknown",
                        "error_type": "RuntimeError",
                    },
                    {
                        "module": "valuation_anchor",
                        "status": "failed",
                        "source": "AkShare",
                        "freshness": "unknown",
                        "error_type": "RuntimeError",
                    },
                ],
            },
        },
        {
            "name": "weekly_skipped_inputs",
            "report_type": "weekly",
            "portfolio": _portfolio("long_term"),
            "run_summary": {
                "portfolio_source": "example",
                "is_example_data": True,
                "modules": {"success": 2, "failed": 0, "skipped": 2, "cache_hit": 1},
                "data_quality": {
                    "fresh": 1,
                    "stale": 1,
                    "unknown": 2,
                    "source_tiers": {"community_data": 2, "news_search": 1, "local_user_data": 1},
                },
                "data_modules": [
                    {"module": "weekly_returns", "status": "success", "source": "AkShare", "freshness": "fresh"},
                    {
                        "module": "industry_rotation",
                        "status": "skipped",
                        "source": "AkShare",
                        "freshness": "unknown",
                        "reason": "missing_inputs",
                    },
                    {
                        "module": "industry_news",
                        "status": "skipped",
                        "source": "Tavily",
                        "freshness": "unknown",
                        "reason": "disabled",
                    },
                ],
            },
        },
    ]
