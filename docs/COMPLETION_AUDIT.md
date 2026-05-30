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
- Offline smoke, runtime, portfolio, and mocked report tests exist.
- Daily report includes a macro observation section with Nasdaq/FX baseline plus configurable CPI/PPI/PMI/M2/GDP/social-financing/US-10Y candidate adapters.
- Daily report includes an ETF proxy observation section with liquidity tiers, configured benchmark/fee/tracking-error/dividend metadata, premium/discount estimate when reference NAV is available, and explicit missing-data gaps.

## Not Completed Yet

- Real report-level tests with mocked AkShare fixtures for every branch of daily/weekly logic.
- Macro coverage still needs real-source verification and enrichment for Fed policy calendar, data release dates, and per-indicator interpretation rules beyond the current configurable AkShare adapters.
- Richer ETF analysis such as cross-fund fee comparison, historical tracking error calculation, official dividend history, and reliable premium/discount sources beyond the current quote/metadata baseline.
- Full migration of real holdings into ignored `data/private/portfolio.local.json`.
- Historical report review workflow and decision-review dashboard.
- L4 multi-agent research system.
- L5 semi-automated decision support with explicit user confirmation workflow.

## Current Priority

Stay in L3 until report generation can be tested offline with realistic mocked data and real-data failures are clearly visible. Do not start L4 or L5 before this is true.

## Next Recommended Tasks

1. Add fixture-based daily and weekly report tests that cover success, partial data failure, skipped news, and example portfolio mode.
2. Verify macro source adapters against the installed AkShare version and add release-date/freshness rules per indicator.
3. Add official ETF premium/discount, fee comparison, historical tracking error, and dividend adapters.
4. Add a decision review command that summarizes past reports and decision tracker records.
5. Migrate real portfolio data to `data/private/portfolio.local.json` manually and stop relying on tracked `memory/portfolio.json`.
