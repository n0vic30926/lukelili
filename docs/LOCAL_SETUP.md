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

Optional private portfolio overrides can be placed in:

```text
data/private/portfolio.overlay.json
```

Use the overlay for user-confirmed strategy types, target weights, cash balance,
risk-rule confirmations, and dated follow-up buy records. It is ignored by git
and is applied by daily/weekly reports, decision support, research dispatch,
industry intelligence, and portfolio risk scan only after `enabled` is set to
`true`.

Review missing portfolio inputs:

```bash
python3 scripts/portfolio_gap_review.py
python3 scripts/portfolio_gap_review.py --base
python3 scripts/portfolio_gap_review.py --template
python3 scripts/portfolio_gap_review.py --write-template
```

By default the gap review applies an enabled private overlay, matching the
portfolio seen by daily/weekly reports and decision support. Use `--base` to
review the raw portfolio before local overrides.

Optional local scenario assumptions can be placed in:

```text
data/private/scenario_assumptions.local.json
```

Use `data/examples/portfolio.example.json` only as a structural reference. Do not copy real costs, shares, account data, API keys, or transaction records into tracked files.
Use `data/examples/scenario_assumptions.example.json` only as a scenario
structure reference. Scenario assumptions are model inputs, not facts.

`enable_ai_sector_flow` defaults to `false` because AkShare
`stock_sector_fund_flow_hist` can hang or fail behind proxies. Daily AI factor
attribution still uses fund NAV and the CSI AI index; sector-flow rotation is
set to zero unless this optional source is explicitly enabled.

Validate a portfolio file:

```bash
python3 scripts/validate_portfolio.py data/examples/portfolio.example.json
```

Review anonymized local historical return and drawdown metrics:

```bash
python3 scripts/portfolio_backtest.py data/examples/portfolio.example.json
```

`portfolio_backtest.py` consumes optional `return_history` fields and reports
historical period return, max drawdown, volatility, and coverage warnings. It
does not forecast future returns by itself or create executable trade
instructions; downstream reports may use it as decision-support context.

Review anonymized target-allocation drift:

```bash
python3 scripts/rebalance_review.py data/examples/portfolio.example.json
```

`rebalance_review.py` consumes optional `target_weight_pct` fields on `cash`
and holdings, plus optional `risk_rules.rebalance_tolerance_pct`. It reports
allocation drift and rebalance-style decision signals for manual review only;
it does not place trades or create executable order instructions.

Inspect anonymized direct and indirect underlying concentration:

```bash
python3 scripts/portfolio_intersection.py data/examples/portfolio.example.json
```

`portfolio_intersection.py` consumes optional `underlying_holdings` fields and
renders only `holding_N` and `underlying_N` references. It is a local
decision-support view, not a trade instruction.

Validate scenario assumptions:

```bash
python3 scripts/validate_scenarios.py data/examples/scenario_assumptions.example.json
```

The validator checks required risk rules, positive cost/share values, and
buy-record fields. Pending buy records may omit confirmed NAV and shares.
The scenario validator checks explicit scenario names, match keys, non-empty
shock lists, and `shock_pct` values between -100 and 100.

Optional `factor_profile` values route attribution modules:

- `qdii_us_equity`: fund return, US tech benchmark, and USD/CNY contribution.
- `a_share_ai`: fund return, CSI AI benchmark, and industry-rotation contribution.
- omit the field or set `"type": "none"` to skip attribution for that holding.

## 3. Foundation Check

```bash
python3 scripts/smoke_test.py
python3 scripts/ideal_agent_readiness.py
python3 scripts/mock_data_quality_test.py
python3 scripts/mock_data_sources_test.py
python3 scripts/mock_decision_confirmation_test.py
python3 scripts/mock_decision_confirmation_record_test.py
python3 scripts/mock_decision_support_test.py
python3 scripts/mock_dependency_test.py
python3 scripts/mock_evidence_ranking_test.py
python3 scripts/mock_etf_research_test.py
python3 scripts/mock_macro_research_test.py
python3 scripts/mock_output_contract_test.py
python3 scripts/mock_portfolio_exposure_test.py
python3 scripts/mock_portfolio_intersection_test.py
python3 scripts/mock_portfolio_validation_test.py
python3 scripts/mock_report_branch_fixtures_test.py
python3 scripts/mock_report_advice_classification_test.py
python3 scripts/mock_report_output_contract_test.py
python3 scripts/mock_report_source_interpretation_test.py
python3 scripts/mock_report_section_contract_test.py
python3 scripts/mock_daily_status_test.py
python3 scripts/mock_factor_routing_test.py
python3 scripts/mock_factor_status_test.py
python3 scripts/mock_ideal_agent_readiness_test.py
python3 scripts/mock_industry_intel_dynamic_test.py
python3 scripts/mock_industry_research_test.py
python3 scripts/mock_news_status_test.py
python3 scripts/mock_research_branch_fixtures_test.py
python3 scripts/mock_research_execution_test.py
python3 scripts/mock_research_dispatch_test.py
python3 scripts/mock_research_interpretation_test.py
python3 scripts/mock_research_questions_test.py
python3 scripts/mock_research_synthesis_test.py
python3 scripts/mock_risk_research_test.py
python3 scripts/mock_review_research_test.py
python3 scripts/mock_security_research_test.py
python3 scripts/mock_report_index_test.py
python3 scripts/mock_review_history_test.py
python3 scripts/mock_review_resolution_record_test.py
python3 scripts/mock_runtime_test.py
python3 scripts/mock_reporting_test.py
python3 scripts/mock_security_scan_test.py
python3 scripts/mock_weekly_status_test.py
python3 scripts/security_scan.py
```

Create a local L4 research dispatch plan:

```bash
python3 scripts/research_dispatch.py "宏观 利率 个股 财报 ETF 组合风险 复盘"
```

Execute local read-only role runners and merge the observations:

```bash
python3 scripts/research_dispatch.py --execute "宏观 利率 个股 财报 ETF 组合风险 复盘"
```

The dispatch command only creates a role/task contract or a merged research
report. It does not run broker actions or convert research into
user-confirmed trades.

Executed research reports include a cross-role coverage matrix. The matrix
shows total data requirements, available sources, coverage percentage, and the
highest-priority missing data gaps before role-level observations.
When ETF holdings are available, the ETF adapter normalizes provider rows into
`underlying_holdings`-compatible records for stock-intersection analysis.

Create a decision-support packet:

```bash
python3 scripts/decision_support.py "组合风险 复盘 决策辅助"
```

The decision-support packet contains candidate actions, ranked evidence, hard
risk rule checks, exposure checks, risks, and a pending manual-confirmation
state. If scenario assumptions are configured, it also includes model-projection
scenario signals as decision-support judgments. The confirmation state also
includes a review queue that separates user confirmation, data refresh,
local-record updates, and risk-rule review. It is not executable and must not be
treated as user consent.

Daily and weekly report output contracts also include local portfolio x-ray
context and scenario signal summaries when scenario assumptions are configured.
These report-side signals are model judgment for manual review, not execution
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

Generate the reader-facing daily insight report:

```bash
python3 scripts/daily_insight.py
```

Review report continuity and decision-discipline aggregates without printing
private holdings:

```bash
python3 scripts/review_history.py
```

Manual confirmation state can be recorded as sanitized JSONL under the private
decision-track directory. Manual review resolutions can also be recorded as
sanitized JSONL. Review summaries aggregate confirmation status,
blocker/action types, and resolution outcomes only; they must not print
holdings, costs, shares, or account details.

Scan tracked files for common secret and private-portfolio leakage patterns:

```bash
python3 scripts/security_scan.py
```

## 4. Optional News

News is disabled by default. To enable Tavily-backed news:

1. Put the key in `.env`.
2. Set `"enable_news": true` in `config/settings.local.json`.

If the key is missing or news is disabled, news functions return no articles and should not block the core report flow.
