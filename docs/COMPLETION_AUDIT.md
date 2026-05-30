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

## Not Completed Yet

- Real report-level tests with mocked AkShare fixtures for every branch of daily/weekly logic.
- Broader macro coverage such as CPI, PPI, PMI, M2,社融, GDP, Fed policy calendar, and US Treasury yields.
- Richer ETF analysis such as premium/discount, tracking error, fee comparison, liquidity, and dividend data.
- Full migration of real holdings into ignored `data/private/portfolio.local.json`.
- Historical report review workflow and decision-review dashboard.
- L4 multi-agent research system.
- L5 semi-automated decision support with explicit user confirmation workflow.

## Current Priority

Stay in L3 until report generation can be tested offline with realistic mocked data and real-data failures are clearly visible. Do not start L4 or L5 before this is true.

## Next Recommended Tasks

1. Add fixture-based daily and weekly report tests that cover success, partial data failure, skipped news, and example portfolio mode.
2. Add macro source adapters one at a time with source/freshness metadata.
3. Add ETF-specific analysis fields and report sections.
4. Add a decision review command that summarizes past reports and decision tracker records.
5. Migrate real portfolio data to `data/private/portfolio.local.json` manually and stop relying on tracked `memory/portfolio.json`.
