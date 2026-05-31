# Roadmap

## Current Status

This worktree now has a local L1/L2 foundation:

- project guardrails in `AGENTS.md`;
- local config and env examples;
- ignored private portfolio path;
- fictional portfolio example;
- minimal portfolio schema and validator;
- smoke test for secret/path isolation;
- core scripts no longer hardcode OpenClaw portfolio paths or Tavily key values;
- tracked `memory/` and Skill files use sanitized templates instead of real holdings;
- a tracked-file security scanner guards against common secret and private-portfolio leakage.

## L1: Document Investment Assistant

Goal: Codex can read investment rules, safety boundaries, and output constraints.

Status: foundation in place. Next step is tightening report templates so every output separates facts, inference, judgment, and user-confirmed action.

## L2: Local Portfolio Analysis Assistant

Goal: read local holdings, cost basis, cash, strategy type, and risk rules.

Status: local path/config/schema foundation in place. Next step is expanding validation and moving real holdings into `data/private/portfolio.local.json` manually.

## L3: Daily And Weekly Reports

Goal: stable daily and weekly reports with visible dependency/data status.

Status: original report scripts exist and now read local config for portfolio/news paths. Daily and weekly entrypoints check required runtime dependencies, avoid generating reports when `akshare` is missing, archive successful reports with structured index/log records, and have shared helpers for data status tracking plus best-effort cache. Daily and weekly report AkShare fetch helpers, QDII factor functions, portfolio risk scan, valuation anchors, and Tavily news helpers now record module success/failure/skipped states plus source-tier and freshness labels. A report index command summarizes recent reports, failed modules, and data quality trends. A history review command summarizes report continuity, repeated failed modules, and decision-discipline strategy counts without printing private holdings. Industry intelligence now builds search queries and impact labels from the configured portfolio instead of fixed exported holdings. Factor attribution now uses each holding's `factor_profile` to route supported QDII and A-share AI attribution jobs. Remaining work includes broader report branch fixtures and richer per-source interpretation.

## L4: Multi-Agent Research

Goal: split macro, ETF, individual security, industry, risk, and review roles.

Do not start until L3 report reliability is stable.

## L5: Semi-Automated Decision Support

Goal: provide buy/sell/hold/watch decision support with explicit user confirmation.

Explicitly out of scope:

- broker integration;
- automatic order placement;
- trade execution without user confirmation.
