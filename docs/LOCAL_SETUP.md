# Local Setup

## 1. Local Environment

```bash
cp .env.example .env
cp config/settings.example.json config/settings.local.json
```

Both `.env` and `config/settings.local.json` are ignored by git.

Use `.env` for secrets:

```text
TAVILY_API_KEY=
FINANCE_AGENT_CONFIG=config/settings.local.json
```

## 2. Private Portfolio

Place real holdings in:

```text
data/private/portfolio.local.json
```

Use `data/examples/portfolio.example.json` only as a structural reference. Do not copy real costs, shares, account data, API keys, or transaction records into tracked files.

Validate a portfolio file:

```bash
python3 scripts/validate_portfolio.py data/examples/portfolio.example.json
```

## 3. Foundation Check

```bash
python3 scripts/smoke_test.py
python3 scripts/mock_dependency_test.py
```

The smoke test checks local guardrails, config examples, schema, fictional example data, OpenClaw path removal, and Tavily key isolation. It does not install dependencies or call market data APIs.

Install runtime dependencies manually before running daily or weekly reports:

```bash
python3 -m pip install -r requirements.txt
```

If a required dependency such as `akshare` is missing, report entrypoints should print the install command and exit without producing market analysis.

Successful report runs write Markdown reports and structured JSONL records:

- `reports/daily/`
- `reports/weekly/`
- `reports/index.jsonl`
- `logs/finance-agent.jsonl`

## 4. Optional News

News is disabled by default. To enable Tavily-backed news:

1. Put the key in `.env`.
2. Set `"enable_news": true` in `config/settings.local.json`.

If the key is missing or news is disabled, news functions return no articles and should not block the core report flow.
