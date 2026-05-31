# Roadmap

## Current Status

This worktree now has a local L1/L2 foundation:

- project guardrails in `AGENTS.md`;
- local config and env examples;
- ignored private portfolio path;
- fictional portfolio example;
- minimal portfolio schema and validator;
- smoke test for secret/path isolation;
- core scripts no longer hardcode OpenClaw portfolio paths or Tavily key values.

## L1: Document Investment Assistant

Goal: Codex can read investment rules, safety boundaries, and output constraints.

Status: foundation in place. Next step is tightening report templates so every output separates facts, inference, judgment, and user-confirmed action.

## L2: Local Portfolio Analysis Assistant

Goal: read local holdings, cost basis, cash, strategy type, and risk rules.

Status: local path/config/schema foundation in place. Next step is expanding validation and moving real holdings into `data/private/portfolio.local.json` manually.

## L3: Daily And Weekly Reports

Goal: stable daily and weekly reports with visible dependency/data status.

Status: original report scripts exist and now read local config for portfolio/news paths. Remaining work includes dependency checks, structured logs, report archive paths, cache, and visible module success/failure summaries.

## L4: Multi-Agent Research

Goal: split macro, ETF, individual security, industry, risk, and review roles.

Do not start until L3 report reliability is stable.

## L5: Semi-Automated Decision Support

Goal: provide buy/sell/hold/watch decision support with explicit user confirmation.

Explicitly out of scope:

- broker integration;
- automatic order placement;
- trade execution without user confirmation.

