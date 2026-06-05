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
  privacy-first, evidence-ranked, recommendation-first iteration gates.
- a signal policy now requires actionable recommendations when evidence is
  sufficient, while keeping execution authority explicit.
- an open-source agent benchmark maps OpenBB, Fincept, ai-hedge-fund,
  AutoHedge, Vibe-Trading, FinGPT, FinRL, Qlib, Backtrader, Pyfolio, and
  x2strategy into capability gaps and a reordered TODO.

## L1: Document Investment Assistant

Goal: Codex can read investment rules, safety boundaries, and output constraints.

Status: foundation in place. Recommendation, daily, and weekly outputs now
include an explicit Facts / Data-Derived Inferences / Model Judgment / User
Confirmation Required classification. Daily and weekly advice sections now also
classify their own content at the source. Decision support now also includes a
dedicated ranked Recommendation section before the lower-level audit details.

## L2: Local Portfolio Analysis Assistant

Goal: read local holdings, cost basis, cash, strategy type, and risk rules.

Status: local path/config/schema foundation in place. Portfolio validation now
checks required risk rules, positive cost/share values, and buy-record fields
without printing private asset details. Local exposure checks now summarize
cash/invested percentages, max single-position percentage, and strategy/factor/
market distribution with anonymized holding refs. A local portfolio backtest
module now consumes optional `return_history` to calculate anonymized historical
period return, max drawdown, volatility, and coverage warnings. A local
rebalance review module now consumes optional `target_weight_pct` values and
`rebalance_tolerance_pct` to calculate target-allocation drift and
manual-confirmation rebalance signals. A local stock-intersection module now
consumes optional `underlying_holdings` to
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

Reader-facing daily insight now includes a market narrative radar. The radar
maintains a stable theme matrix for AI compute, memory/HBM, semiconductor
equipment, AI power/nuclear, physical AI/robotics, commercial space, defensive
rotation, and A-share mapping. Each theme carries verification status, observable
tickers/ETFs, portfolio-overlap classification, and an execution stance before
external news is allowed to affect recommendations.

## L4: Multi-Agent Research

Goal: split macro, ETF, individual security, industry, risk, and review roles.

Status: a minimal local dispatcher now maps user intent to Macro, Industry,
Individual Security, ETF, Risk, and Review role contracts with explicit inputs,
outputs, and recommendation/execution-authority boundaries. It can also execute local
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
research prompts and recommendation inputs rather than passive caveats. Sanitized
research branch fixtures now cover ok/skipped/failed role paths, ranked
evidence, data sources, interpretations, and research questions. Cross-role
research synthesis now summarizes role status, data-source status, unavailable
sources, coverage percentage, prioritized data gaps, and ranked evidence for
downstream confirmation audit. Research execution reports now include a coverage
matrix before role details, so missing AkShare/Tavily/local-history inputs are
visible before model judgment. Real data depth can continue expanding by role,
while end-to-end readiness is now checked by the ideal-agent acceptance matrix
and the competitive benchmark gate.

## L5: Recommendation And Action Engine

Goal: provide ranked buy/sell/hold/rebalance/reduce-risk recommendations and
concrete next actions. Recommendation is allowed; real execution is a separate
mandate-gated capability.

Status: the current packet builder now emits a first-class ranked
recommendation section before the lower-level audit trail. It aggregates
portfolio strategy types, scenario signals, rebalance drift, local backtest
context, research-source gaps, and risk observations into recommendations with
action, instrument ref, direction, horizon, confidence, status, rationale,
risks, invalidators, position effect, and concrete next action. Candidate
actions and manual confirmation checks remain visible below the ranked layer for
auditability. `execution_allowed=false` remains only because no execution module
exists yet, not because the system should avoid recommendations.

New priority order:

1. P0 Product reset: remove blanket defensive phrasing and require actionable
   recommendation language.
2. P1 Market cognition layer: external evidence ingestion, fact/rumor
   verification, narrative-to-instrument mapping, portfolio-fit scoring, and
   visible thesis-change records.
3. P1 Harden recommendation scoring and add portfolio-manager aggregation over
   current portfolio, scenario, rebalance, backtest, and research signals.
4. P1 Investor-style voting agents: value, growth, macro, technical, sentiment,
   risk, and portfolio manager.
5. P2 Pyfolio-style performance analytics: Sharpe, Sortino, Calmar, beta,
   alpha, benchmark comparison, rolling stats, drawdown table.
6. P2 Strategy backtesting: strategy spec, signal series, trade ledger, sizing,
   slippage/fees, and out-of-sample split.
7. P3 Hypothesis registry and x2strategy-style strategy extraction from papers,
   news, and filings.
8. P4 Provider registry and tool catalog inspired by OpenBB/Fincept.
9. P5 Paper execution: mandate file, order proposal artifact, pre-trade risk
   checks, audit ledger, and kill switch.
10. P6 Live broker integration only after paper execution is reliable.

Still out of scope for the current codebase:

- silent broker integration;
- live order placement without a user mandate;
- promised returns or forecasts presented as facts.
