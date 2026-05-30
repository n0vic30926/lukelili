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
- Offline smoke, runtime, portfolio, and mocked report tests exist; report tests cover success, partial data failure, skipped news, and example portfolio mode.
- Historical review command aggregates report index, decision records, strategy scorecards, user-confirmation action status, confirmed-action outcome status, outcome quality, checklist pass/fail/missing evidence, and later-report evidence without printing raw asset details.
- Daily report includes a macro observation section with Nasdaq/FX baseline plus configurable CPI/PPI/PMI/M2/GDP/social-financing/US-10Y candidate adapters, data freshness labels, and rule-based interpretation text.
- Daily report includes an ETF proxy observation section with liquidity tiers, configured benchmark/fee/tracking-error/dividend metadata, fee comparison, tracking-risk labels, dividend status, premium/discount risk labels, and explicit missing-data gaps.

## Not Completed Yet

- Realistic AkShare-shaped fixtures still do not cover every branch of daily/weekly logic.
- Macro coverage still needs real-source verification and enrichment for Fed policy calendar, official release calendars, and stronger per-indicator rules beyond the current configurable AkShare adapters.
- Richer ETF analysis still needs historical tracking error calculation, official dividend history adapters, and reliable premium/discount sources beyond the current quote/profile baseline.
- Full migration of real holdings into ignored `data/private/portfolio.local.json`.
- Historical report review workflow exists as a command-line summary with strategy scorecards, user-confirmed action tracking, confirmed-action outcome status, outcome quality, checklist pass/fail evidence, and later-report evidence; dashboard, report streak metrics, and report-content outcome attribution remain incomplete.
- L4 multi-agent research system.
- L5 semi-automated decision support with explicit user confirmation workflow.

## Current Priority

Stay in L3 until report generation can be tested offline with realistic mocked data and real-data failures are clearly visible. Do not start L4 or L5 before this is true.

## Next Recommended Tasks

1. Verify macro source adapters against the installed AkShare version and add official release-calendar checks per indicator.
2. Add official ETF premium/discount, historical tracking error, and dividend-history adapters.
3. Expand decision review into richer metrics: report streaks, repeated failures, and report-content outcome attribution.
4. Add more realistic AkShare-shaped fixtures for each report branch.
5. Migrate real portfolio data to `data/private/portfolio.local.json` manually and stop relying on tracked `memory/portfolio.json`.
