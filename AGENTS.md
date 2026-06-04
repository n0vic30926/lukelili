# Finance Agent Guardrails

This repository is a local personal investment agent. Its product goal is to
produce actionable investment recommendations, action plans, portfolio reviews,
risk analysis, daily/weekly reports, and discipline review. It must not promise
returns, present forecasts as facts, or place real trades without an explicit
user-authorized execution mode. It may output forecasts, ranked buy/sell/hold/
rebalance recommendations, target-action drafts, and trading-style signals when
they are labeled as model judgment with evidence and risk context.

## Output Boundaries

- Separate facts, data-derived inference, model judgment, recommendations, and user-confirmed actions.
- Every buy/sell/hold style output should be specific enough to be useful:
  action label, confidence/priority, rationale, key risks, and next action.
- Forecasts and projections are allowed only as model judgment, not facts.
- Avoid blanket "not investment advice" phrasing in normal outputs; prefer
  direct recommendation language plus evidence, assumptions, and risk limits.
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
