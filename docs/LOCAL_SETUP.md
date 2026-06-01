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

Optional `factor_profile` values route attribution modules:

- `qdii_us_equity`: fund return, US tech benchmark, and USD/CNY contribution.
- `a_share_ai`: fund return, CSI AI benchmark, and industry-rotation contribution.
- omit the field or set `"type": "none"` to skip attribution for that holding.

## 3. Foundation Check

```bash
python3 scripts/smoke_test.py
python3 scripts/mock_data_quality_test.py
python3 scripts/mock_decision_support_test.py
python3 scripts/mock_dependency_test.py
python3 scripts/mock_evidence_ranking_test.py
python3 scripts/mock_daily_status_test.py
python3 scripts/mock_factor_routing_test.py
python3 scripts/mock_factor_status_test.py
python3 scripts/mock_industry_intel_dynamic_test.py
python3 scripts/mock_news_status_test.py
python3 scripts/mock_research_execution_test.py
python3 scripts/mock_research_dispatch_test.py
python3 scripts/mock_report_index_test.py
python3 scripts/mock_review_history_test.py
python3 scripts/mock_runtime_test.py
python3 scripts/mock_reporting_test.py
python3 scripts/mock_security_scan_test.py
python3 scripts/mock_weekly_status_test.py
python3 scripts/security_scan.py
```

Create a local L4 research dispatch plan:

```bash
python3 scripts/research_dispatch.py "宏观 利率 ETF 组合风险 复盘"
```

Execute local read-only role runners and merge the observations:

```bash
python3 scripts/research_dispatch.py --execute "宏观 利率 ETF 组合风险 复盘"
```

The dispatch command only creates a role/task contract or a merged research
report. It does not run broker actions or convert research into
user-confirmed trades.

Create a decision-support packet:

```bash
python3 scripts/decision_support.py "组合风险 复盘 决策辅助"
```

The decision-support packet contains candidate actions, evidence, risks, and
confirmation checks. It is not executable and must not be treated as user
consent.

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
- `cache/`

Cache behavior is configured through `use_cache`, `cache_ttl_hours`, and `cache_dir` in local settings. Cache writes are best-effort and should not block report generation.

Run summaries include data quality labels:

- `source_tier`: local user data, community data, news/search data, example data, or unknown.
- `freshness`: fresh, stale, or unknown.

Inspect archived report history without printing report bodies:

```bash
python3 scripts/report_index.py
```

Review report continuity and decision-discipline aggregates without printing
private holdings:

```bash
python3 scripts/review_history.py
```

Scan tracked files for common secret and private-portfolio leakage patterns:

```bash
python3 scripts/security_scan.py
```

## 4. Optional News

News is disabled by default. To enable Tavily-backed news:

1. Put the key in `.env`.
2. Set `"enable_news": true` in `config/settings.local.json`.

If the key is missing or news is disabled, news functions return no articles and should not block the core report flow.
