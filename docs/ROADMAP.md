# Roadmap

## Current Status

The project has completed the L1-L2 foundation:

- project-level guardrails in `AGENTS.md`;
- local config example and env example;
- shared JSON config loader;
- portfolio schema and fictional example data;
- smoke test for local foundation;
- core scripts no longer default to old OpenClaw workspace paths.

L3 foundation is now stabilized: daily and weekly reports have dependency checks, best-effort cache support, structured logs, archive index, visible module status, local portfolio validation, source tiering, freshness summaries, offline adapter audits, opt-in macro adapter output schema audits, configurable macro observations with freshness, release-calendar checks, Fed policy calendar checks, and rule-based interpretation, ETF proxy observations with fee comparison/tracking risk/historical tracking error/dividend history/dividend status/premium risk/liquidity gaps, mocked report branch tests, and a command-line historical review summary with report continuity, repeated module failure detection, strategy scorecards, user-confirmation action tracking, confirmed-action outcome status, outcome quality, checklist evidence, later-report evidence, and report-content marker matching. The next step is running schema audits against the user's installed AkShare version and adding richer source-specific interpretation.

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

Status: data-quality foundation stabilized; mocked report tests cover success, partial data failure, skipped news, example portfolio mode, macro freshness, release-calendar checks, Fed policy calendar checks, rule-based macro interpretation, ETF risk metadata, ETF historical tracking/dividend summaries, offline adapter audits, opt-in macro output schema audits, report continuity, repeated module failures, user-confirmation action tracking, confirmed-action outcome status, outcome quality, checklist evidence, later-report evidence, and report-content marker matching.

Next steps:

- run configured macro adapter output schema audits against the user's installed AkShare and adjust column mappings when needed;
- keep official release calendars current in local config;
- expand ETF beyond local history and configured metadata into official premium/discount, tracking-error, and dividend adapters;
- expand historical review beyond report-content marker matching into semantic outcome attribution;
- add more realistic AkShare-shaped fixtures for each report branch.

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

Current foundation:

- user actions can be recorded in local ignored decision records;
- historical review aggregates report continuity, repeated module failures, confirmed, pending, and rejected actions plus confirmed-action outcome status, quality, checklist evidence, later-report evidence, and report-content marker matching without printing private details.
