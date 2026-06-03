# Finance Agent Guardrails

This repository is a local personal investment-analysis assistant. It supports
research, portfolio review, risk reminders, daily/weekly reports, and discipline
review. It must not place trades, connect to broker execution endpoints, promise
returns, or present forecasts as facts. It may output projections and
trading-style signals when they are framed as model judgment and decision
support.

## Output Boundaries

- Separate facts, data-derived inference, model judgment, and user-confirmed actions.
- Every buy/sell/hold style output must be framed as decision support, not execution.
- Forecasts and projections are allowed only as model judgment, not facts.
- Mention data source and data freshness whenever external data is used.
- If required data is missing or stale, say so plainly.
- Do not copy real holdings, costs, shares, API keys, cookies, or account IDs into tracked examples or docs.

## Engineering Rules

- Keep local secrets in `.env` or ignored local config only.
- Keep real portfolio files under `data/private/`.
- Do not hardcode OpenClaw paths.
- Do not hardcode API keys.
- Prefer small, testable helpers over broad rewrites.
- Run `python3 scripts/smoke_test.py` before claiming foundation changes are complete.
