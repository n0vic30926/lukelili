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
