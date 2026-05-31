# Completion Audit

## Completed

### L1: Document Investment Assistant

- Project guardrails are defined in `AGENTS.md`.
- Investment boundaries distinguish facts, inferences, model judgments, and user-confirmed actions.
- Safety docs define no automatic trading, no guaranteed returns, no broker integration, and no secret commits.

### L2: Local Portfolio Analysis Foundation

- Local settings and environment examples exist.
- Private portfolio path is separated from fictional example data.
- Portfolio schema and standard-library validation exist.
- OpenClaw default paths have been removed from core scripts.
- Hardcoded Tavily key has been removed from scripts.

### L3: Daily/Weekly Report Foundation

- Daily and weekly scripts have dependency checks and avoid generating fake reports when required dependencies are missing.
- Reports use local config, write to local report directories, and log structured JSONL events.
- Best-effort cache exists for external data calls.
- Data status tracking, source tiering, freshness summaries, and report index inspection exist.
- Offline data adapter audit checks macro configuration fields, release-calendar metadata, and AkShare function symbol availability without calling external APIs.
- Offline smoke, runtime, portfolio, and mocked report tests exist; report tests cover success, partial data failure, skipped news, and example portfolio mode.
- Historical review command aggregates report index, report continuity, repeated module failures, decision records, strategy scorecards, user-confirmation action status, confirmed-action outcome status, outcome quality, checklist pass/fail/missing evidence, later-report evidence, and later report-content marker matches without printing raw asset details.
- Daily report includes a macro observation section with Nasdaq/FX baseline plus configurable CPI/PPI/PMI/M2/GDP/social-financing/US-10Y candidate adapters, data freshness labels, local release-calendar checks, and rule-based interpretation text.
- Daily report includes an ETF proxy observation section with liquidity tiers, configured benchmark/fee/tracking-error/dividend metadata, local historical tracking-error calculation, local dividend-history yield summary, fee comparison, tracking-risk labels, dividend status, premium/discount risk labels, and explicit missing-data gaps.

## Not Completed Yet

- Realistic AkShare-shaped fixtures still do not cover every branch of daily/weekly logic.
- Macro coverage still needs real-source output verification, official release-date maintenance in local config, Fed policy calendar enrichment, and stronger per-indicator rules beyond the current configurable AkShare adapters.
- Richer ETF analysis still needs official tracking-error/dividend-history adapters and reliable premium/discount sources beyond the current quote/profile/local-history baseline.
- Full migration of real holdings into ignored `data/private/portfolio.local.json`.
- Historical report review workflow exists as a command-line summary with report streak/gap metrics, repeated module failure detection, strategy scorecards, user-confirmed action tracking, confirmed-action outcome status, outcome quality, checklist pass/fail evidence, later-report evidence, and report-content marker matching; dashboard and semantic outcome attribution remain incomplete.
- L4 multi-agent research system.
- L5 semi-automated decision support with explicit user confirmation workflow.

## Current Priority

Stay in L3 until report generation can be tested offline with realistic mocked data and real-data failures are clearly visible. Do not start L4 or L5 before this is true.

## Next Recommended Tasks

1. Verify macro adapter output schemas against the installed AkShare version and add Fed policy calendar coverage.
2. Add official ETF premium/discount, tracking-error, and dividend-history adapters.
3. Expand decision review into richer semantic outcome attribution once report text quality is stable.
4. Add more realistic AkShare-shaped fixtures for each report branch.
5. Migrate real portfolio data to `data/private/portfolio.local.json` manually and stop relying on tracked `memory/portfolio.json`.
