# Local Setup

## 1. Create Local Environment File

```bash
cp .env.example .env
```

`.env` is ignored by git. Put local secrets there only.

Example:

```text
TAVILY_API_KEY=
FINANCE_AGENT_CONFIG=config/settings.local.json
```

## 2. Create Local Settings

```bash
cp config/settings.example.json config/settings.local.json
```

`config/settings.local.json` is ignored by git.

Important fields:

- `portfolio_path`: real local portfolio path.
- `example_portfolio_path`: fictional portfolio for smoke tests.
- `daily_report_dir`: daily report output directory.
- `weekly_report_dir`: weekly report output directory.
- `cache_dir`: cache directory.
- `log_dir`: log directory.
- `use_cache`: whether to use best-effort local cache.
- `cache_ttl_hours`: cache freshness window.
- `macro_indicators`: configurable macro radar using candidate AkShare functions, local release-calendar metadata, date columns, and value columns.
- `fed_policy_calendar`: local FOMC/Fed event calendar metadata.
- `enable_news`: whether to use Tavily news.
- `tavily_api_key_env`: environment variable name for the Tavily key.
- `timezone`: report timezone.

## 3. Create Private Portfolio

Create:

```text
data/private/portfolio.local.json
```

Use `data/examples/portfolio.example.json` only as a structural reference. Do not copy real values into example files.

The private portfolio should contain:

- user profile;
- cash;
- holdings;
- cost basis;
- shares;
- buy records;
- watchlist;
- risk rules;
- strategy type and notes.
- optional `etf_profile` for ETF-like holdings, including benchmark, expense ratio, tracking error, tracking history, dividend policy, and dividend history.

For each configured macro indicator, keep `release_calendar.next_release_date` updated in `config/settings.local.json` from an official source. Keep `fed_policy_calendar.events` updated from the FOMC/Fed calendar. The report shows missing release dates as a calendar gap instead of guessing.

## 4. Tavily News

News is disabled by default.

To enable:

1. Set `TAVILY_API_KEY` in `.env`.
2. Set `"enable_news": true` in `config/settings.local.json`.

If no key is present, the news module skips itself and the report should continue.

## 5. Run Checks and Reports

Install dependencies manually:

```bash
python3 -m pip install -r requirements.txt
```

Run local checks:

```bash
python3 scripts/smoke_test.py
python3 scripts/validate_portfolio.py data/examples/portfolio.example.json
python3 scripts/mock_runtime_test.py
python3 scripts/mock_report_test.py
python3 scripts/mock_portfolio_validation_test.py
python3 scripts/mock_decision_tracker_test.py
python3 scripts/mock_review_test.py
```

Run reports:

```bash
python3 scripts/daily_finance_brief.py
python3 scripts/weekly_finance_review.py
```

If `akshare` is missing, the report scripts print an install hint and exit without generating market analysis.

Report artifacts:

- `reports/daily/`: daily markdown reports.
- `reports/weekly/`: weekly markdown reports.
- `reports/index.jsonl`: report archive index.
- `logs/finance-agent.jsonl`: structured runtime log.
- `cache/`: best-effort external data cache.

Inspect report index:

```bash
python3 scripts/report_index.py
```

Review decision and report history:

```bash
python3 scripts/review_history.py
```

Audit configured data adapters without calling external data APIs:

```bash
python3 scripts/audit_data_adapters.py
```

Explicitly validate macro adapter output columns against the installed AkShare version:

```bash
python3 scripts/audit_data_adapters.py --check-output-schema
```

The default audit does not call market data functions. The schema mode is opt-in and checks whether returned columns match each macro indicator's configured `date_columns` and `value_columns`.

Decision records can include `user_actions` for user-confirmed, pending, or rejected actions. Confirmed actions can also include `outcome_status`, `outcome_quality`, a `checklist` such as `discipline`, `risk_boundary`, and `source_evidence`, plus non-sensitive `action_id` or `report_evidence_terms` markers for later report-content matching. Keep real records under ignored private paths such as `data/private/decision_track/`; the review command only prints aggregate report continuity, repeated module failures, confirmation, outcome, checklist, later-report evidence, and report-content match status.

## 6. Never Commit

Do not commit:

- `.env`
- `config/settings.local.json`
- `data/private/portfolio.local.json`
- `data/private/decision_track/`
- `reports/`
- `cache/`
- `logs/`
- real API keys, tokens, cookies, or passwords
- real asset details copied into examples or docs
