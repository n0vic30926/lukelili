# Autopilot Baseline

Generated during Phase 0 of the L1-L3 foundation work.

## Repository State

- Working directory: `/Users/luke/finance-agent`
- Branch: `main`
- Initial status: clean
- Existing top-level modules: `cron-config/`, `docs/`, `memory/`, `scripts/`, `skills/`, `README.md`

## OpenClaw Coupling

| Path | Field or Pattern | Risk Type |
|---|---|---|
| `scripts/daily_finance_brief.py` | `PORTFOLIO_PATH` | Reads portfolio from old OpenClaw workspace |
| `scripts/weekly_finance_review.py` | `PORTFOLIO_PATH` | Reads portfolio from old OpenClaw workspace |
| `scripts/qdii_three_factor.py` | `portfolio_path` | Reads portfolio from old OpenClaw workspace |
| `scripts/decision_tracker.py` | `TRACK_DIR` | Writes tracking records to old OpenClaw workspace |
| `scripts/decision_tracker.py` | `portfolio_path` | Reads portfolio from old OpenClaw workspace |
| `scripts/industry_intel.py` | `PORTFOLIO_PATH` | Reads portfolio from old OpenClaw workspace |
| `README.md` | `openclaw-weixin` delivery example | OpenClaw-specific deployment instructions |

## Sensitive Configuration Risks

| Path | Field | Risk Type |
|---|---|---|
| `scripts/industry_intel.py` | `TAVILY_API_KEY` | Hardcoded API key |
| `scripts/industry_cycle.py` | `TAVILY_API_KEY` | Hardcoded API key |

The key values are intentionally not reproduced here. The exposed key should be rotated before relying on it again.

## User Asset Data

| Path | Fields | Risk Type |
|---|---|---|
| `memory/portfolio.json` | `user_profile`, `holdings`, `cost_basis`, `shares`, `buy_records` | Real personal asset data stored in a tracked file |

This file should not be copied into examples, test fixtures, docs, or generated reports.

## Missing Local Foundation

- No project-level `AGENTS.md`.
- No `.env.example`.
- No local settings file example under `config/`.
- No shared configuration loader.
- No portfolio JSON schema.
- No fictional example portfolio.
- No ignored private data directory.
- No smoke test.
- No committed local setup, roadmap, or security boundary docs.
- No durable report, log, or cache directory contract.

## Safety Constraints for Follow-up Phases

- Do not delete or overwrite `memory/portfolio.json`.
- Do not copy real asset details into example files.
- Do not print or preserve hardcoded API key values.
- Do not write to `~/.openclaw`.
- Do not connect to broker or trading interfaces.
- Do not add third-party dependencies for this foundation pass.
