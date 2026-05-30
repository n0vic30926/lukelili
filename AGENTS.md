# Finance Agent Project Instructions

## System Positioning

This repository is a personal investment analysis agent.

It is intended to support:

- investment discipline guardrails;
- daily and weekly market briefs;
- portfolio risk reminders;
- investment research assistance;
- local, auditable decision support.

It is not:

- an automated trading system;
- a broker integration;
- a return prediction system;
- a replacement for user judgment;
- financial advice.

## Investment Output Boundaries

Every investment-related output must clearly distinguish:

- **Known facts**: values directly read from user data, market data, filings, official announcements, or other cited sources.
- **Data inferences**: calculations derived from known facts, such as returns, drawdowns, exposure, valuation percentiles, or correlations.
- **Model judgments**: qualitative interpretation by the agent, such as risk level, scenario assessment, or thesis strength.
- **User-confirmed actions**: any buy, sell, hold, rebalance, or watchlist action that requires explicit user confirmation.

Do not blur predictions into facts. Do not present model judgment as certainty.

## Risk Principles

- Risk control has higher priority than return maximization.
- Do not promise returns or imply guaranteed outcomes.
- Do not make deterministic claims without a source and timestamp.
- Do not ignore the user's stated risk preference, strategy type, or investment policy.
- Do not place orders, route trades, connect to brokers, or automate transactions.
- Do not bypass user confirmation for any action that changes a portfolio, strategy, or risk posture.
- For DCA positions, preserve the declared strategy boundary unless the user explicitly changes it.
- For trial or short-term positions, label any exit, stop, or take-profit idea as decision support requiring user confirmation.

## Engineering Rules

- Do not commit real API keys, tokens, cookies, passwords, or private credentials.
- Do not commit user real asset details outside approved private files.
- Do not copy real portfolio values into examples, tests, fixtures, generated docs, or public reports.
- Keep private portfolio data in ignored local paths such as `data/private/portfolio.local.json`.
- Changing investment logic must update the relevant docs or policy notes.
- New scripts must include a smoke test or be covered by `scripts/smoke_test.py`.
- External data shown in reports must include source and timestamp where practical.
- Failures must be visible. Do not silently swallow errors that affect report correctness.
- Prefer Python standard library for foundation work unless a dependency already exists in the project.
- Do not write to old OpenClaw paths such as `~/.openclaw`.
- Do not modify files outside this repository during normal project work.

## Safety Defaults

When unsure whether data is real user asset data, treat it as private.

When unsure whether an output could be interpreted as an instruction to trade, rewrite it as a risk-aware decision aid and require user confirmation.

When an external data source fails, keep the report running but mark that module as unavailable.
