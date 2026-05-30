# Roadmap

## Current Status

The project has completed the L1-L2 foundation:

- project-level guardrails in `AGENTS.md`;
- local config example and env example;
- shared JSON config loader;
- portfolio schema and fictional example data;
- smoke test for local foundation;
- core scripts no longer default to old OpenClaw workspace paths.

L3 is partially complete: daily and weekly reports exist, but still need stronger output persistence, cache behavior, logging detail, and data quality reporting.

## L1: Document Investment Assistant

Goal: Codex can read the investment policy, risk boundaries, and output rules.

Inputs:

- `AGENTS.md`
- `memory/investment_policy.md`
- report templates

Outputs:

- disciplined investment explanations;
- separated facts, inferences, judgments, and user-confirmed actions.

Status: complete for the local foundation.

## L2: Local Portfolio Analysis Assistant

Goal: Read local holdings, cost basis, cash, strategy type, and risk rules.

Inputs:

- `data/private/portfolio.local.json`
- `schemas/portfolio.schema.json`
- `config/settings.local.json`

Outputs:

- portfolio snapshot;
- risk reminders;
- strategy-specific analysis.

Status: foundation complete; next step is fuller schema validation and private portfolio migration.

## L3: Daily Market Brief Assistant

Goal: Generate stable daily and weekly reports with visible data status.

Inputs:

- local portfolio;
- AkShare market data;
- optional Tavily news;
- cache/log/report directories.

Outputs:

- daily report;
- weekly report;
- visible module success/failure status;
- archived report files.

Status: in progress.

Next steps:

- write report files to `reports/daily/` and `reports/weekly/`;
- add lightweight logs;
- add cache wrappers around external data calls;
- add module status summaries.

## L4: Multi-Agent Investment Research System

Goal: Split analysis into macro, industry, ETF, individual stock, risk, and review roles.

Do not start this until L3 is stable.

Preferred future approach:

- keep roles small and auditable;
- require source citations;
- add human confirmation gates;
- avoid theatrical agent debates that do not improve decisions.

## L5: Semi-Automated Decision Support

Goal: Provide buy/sell/hold/watch decision support that always requires user confirmation.

Explicitly out of scope:

- broker integration;
- automatic order placement;
- trade execution without user confirmation.

Required before L5:

- audit logs;
- decision records;
- source-backed evidence;
- rule-based risk gates;
- clear user confirmation workflow.
