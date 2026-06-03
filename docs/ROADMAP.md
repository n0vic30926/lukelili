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
- a competitive benchmark maps high-quality peer capabilities to local
  privacy-first, evidence-ranked, decision-support-only iteration gates.
- a signal policy now permits projections and trading-style signals as model
  judgment, while keeping confirmation and execution boundaries explicit.

## L1: Document Investment Assistant

Goal: Codex can read investment rules, safety boundaries, and output constraints.

Status: foundation in place. Decision-support, daily, and weekly outputs now
include an explicit Facts / Data-Derived Inferences / Model Judgment / User
Confirmation Required classification. Daily and weekly advice sections now also
classify their own content at the source, so older free-form advice language is
framed as decision-support judgment with explicit user confirmation.

## L2: Local Portfolio Analysis Assistant

Goal: read local holdings, cost basis, cash, strategy type, and risk rules.

Status: local path/config/schema foundation in place. Portfolio validation now
checks required risk rules, positive cost/share values, and buy-record fields
without printing private asset details. Local exposure checks now summarize
cash/invested percentages, max single-position percentage, and strategy/factor/
market distribution with anonymized holding refs. A local portfolio backtest
module now consumes optional `return_history` to calculate anonymized historical
period return, max drawdown, volatility, and coverage warnings. A local
stock-intersection module now consumes optional `underlying_holdings` to
calculate anonymized direct and indirect underlying concentration, overlap,
coverage, and warnings. A local portfolio x-ray now adds allocation, factor overlap clusters, stock
intersection, fee-coverage, and decision-support boundary review without
printing private holdings. A local scenario review now supports explicit stress
assumptions, model-projection labels, decision signals, and risk rule flags
without turning them into executable orders. Scenario assumptions now have a
local validator for allowed match keys, non-empty shocks, and bounded shock
percentages. Next step is moving real holdings into
`data/private/portfolio.local.json` manually.

## L3: Daily And Weekly Reports

Goal: stable daily and weekly reports with visible dependency/data status.

Status: original report scripts exist and now read local config for portfolio/news paths. Daily and weekly entrypoints check required runtime dependencies, avoid generating reports when `akshare` is missing, archive successful reports with structured index/log records, and have shared helpers for data status tracking plus best-effort cache. Daily and weekly report AkShare fetch helpers, QDII factor functions, portfolio risk scan, valuation anchors, and Tavily news helpers now record module success/failure/skipped states plus source-tier and freshness labels. A report index command summarizes recent reports, failed modules, and data quality trends. A history review command summarizes report continuity, repeated failed modules, and decision-discipline strategy counts without printing private holdings. Industry intelligence now builds search queries and impact labels from the configured portfolio instead of fixed exported holdings. Factor attribution now uses each holding's `factor_profile` to route supported QDII and A-share AI attribution jobs. Sanitized report branch fixtures now cover daily/weekly success, failed, skipped, and cache-hit output paths through the output contract and run-summary renderer. Run summaries now include per-source interpretation lines that map data-module status to report completeness and freshness impact without exposing raw upstream errors. Daily and weekly report contracts now also carry local portfolio x-ray facts, scenario model-projection labels, ranked scenario decision signals, and explicit confirmation requirements.

## L4: Multi-Agent Research

Goal: split macro, ETF, individual security, industry, risk, and review roles.

Status: a minimal local dispatcher now maps user intent to Macro, Industry,
Individual Security, ETF, Risk, and Review role contracts with explicit inputs,
outputs, and decision-support-only boundaries. It can also execute local
read-only role runners and merge observations into one research report. Evidence
is ranked and displayed with source tier, freshness, and reliability score. Role
reports now also show required data sources and availability status without
printing keys or private holdings. The Individual Security role has a first
read-only AkShare adapter for financial statements, announcements, valuation
metrics, market quotes/liquidity, and research reports with dependency-aware
fallback. The ETF role has a read-only adapter for ETF quotes, liquidity,
premium/discount checks, NAV history, holdings-through status, and normalized
holdings rows that can feed stock intersection. The Macro
role has a read-only adapter for rates, FX, liquidity, inflation, and PMI source
status with dependency-aware fallback. The Industry role has a read-only adapter for
portfolio-driven news query counts, news result/signal counts, and AkShare
industry/concept rotation source states. The Risk role has a read-only adapter for
anonymized portfolio exposure, local risk-rule/factor-profile state, cash buffer,
risk-limit breaches, AkShare market quote availability, and benchmark quote
context. The Review role has a first read-only adapter for report
continuity, repeated failures, data-quality totals, decision-record aggregates,
and manual-confirmation blocker summaries. Role data-source states are now also
interpreted into explicit impact paths and unconfirmed limitations, so execution
reports no longer stop at raw availability lists. Role reports now also generate
bounded per-role research questions from data-source states, keeping them as
manual decision-support prompts rather than trade instructions. Sanitized
research branch fixtures now cover ok/skipped/failed role paths, ranked
evidence, data sources, interpretations, and research questions. Cross-role
research synthesis now summarizes role status, data-source status, unavailable
sources, coverage percentage, prioritized data gaps, and ranked evidence for
downstream confirmation audit. Research execution reports now include a coverage
matrix before role details, so missing AkShare/Tavily/local-history inputs are
visible before model judgment. Real data depth can continue expanding by role,
while end-to-end readiness is now checked by the ideal-agent acceptance matrix
and the competitive benchmark gate.

## L5: Semi-Automated Decision Support

Goal: provide buy/sell/hold/watch decision support with explicit user confirmation.

Status: a local decision-support packet builder now converts portfolio strategy
types and research observations into candidate actions, rationale, risks, and
required confirmation checks. It also surfaces missing hard risk rules from the
local portfolio file, anonymized exposure checks, and a pending manual
confirmation state with blockers. Scenario decision signals now flow from the
configured scenario assumptions into the decision packet as ranked model
judgment with explicit user confirmation blockers. It sets
`execution_allowed=false` and does not connect to broker endpoints. Cross-role
research synthesis now feeds
unavailable role/data-source states into the manual confirmation blockers.
Manual confirmation now includes a bounded review queue that separates user
confirmation, data refresh, local-record updates, and risk-rule review. These
queue action counts and manual review resolutions can be recorded as sanitized
JSONL and summarized by history review without turning them into execution
consent. An end-to-end ideal-agent readiness matrix now checks L1-L5 and safety
capabilities against tracked example data without reading private holdings.

Explicitly out of scope:

- broker integration;
- automatic order placement;
- trade execution without user confirmation.
