# Open Source Agent Benchmark

Observed on 2026-06-04 from public GitHub project pages. These projects are
benchmark inputs, not endorsements.

## Product Reset

The prior system posture was too conservative for a useful personal investment
agent. The new product goal is:

- produce explicit investment recommendations, not only reminders;
- produce ranked action plans with action, confidence, rationale, risk, and next
  action;
- use research, quant signals, backtests, scenarios, and portfolio constraints
  to decide, not merely summarize;
- keep real broker execution behind explicit user mandate, pre-trade checks,
  audit logs, and a kill switch.

The core boundary is no longer "do not give investment advice." The boundary is
"do not present uncertainty as certainty, and do not execute without authority."

## Competitor Matrix

| Project | What It Proves | Capability To Borrow | Current Gap |
|---|---|---|---|
| OpenBB | A finance agent needs a broad data platform and many downstream surfaces. | Data-provider abstraction, Python/API/agent surfaces, extensible providers. | Current system has role adapters, but lacks a normalized provider registry and tool catalog. |
| Fincept Terminal | Terminal-grade finance products emphasize interactive exploration, analytics, and decision workflows. | Workspace-style market/research console, economic data, technical/fundamental analytics. | Current system is script/report-first, not a persistent analyst cockpit. |
| ai-hedge-fund | Multi-style investor agents can vote into final trading decisions. | Style agents, signal aggregation, portfolio manager final decision. | Current L4 roles are functional, but not opinionated investor-philosophy agents with votes. |
| AutoHedge | Users expect autonomous research, risk, and execution teams. | Director/Quant/Risk/Execution workflow, action handoff. | Current workflow stops at manual confirmation and has no mandate-aware action layer. |
| Vibe-Trading | Modern agentic trading projects include connectors, mandates, order guards, audit ledgers, alpha bench, goal runtime, and shadow accounts. | Mandate-gated paper/live connector model, strict alpha gate, run cards, shadow account, research goals. | Current system has readiness and history review, but lacks paper trading, run cards, alpha validation, and shadow account. |
| FinGPT | Financial LLM value comes from finance-specific sentiment, RAG, forecasting, and instruction tuning. | Sentiment/forecasting adapters and retrieval-grounded news/filing interpretation. | Current news signals are heuristic; no financial sentiment/forecast model layer. |
| FinRL | Trading agents need train/test/trade workflows and market environments. | RL/ML strategy sandbox with simulated policies. | Current system has no trainable strategy environment or policy evaluation loop. |
| Qlib | Production quant work needs a full alpha, risk, optimization, backtest, and execution pipeline. | Alpha research pipeline, risk model, portfolio optimization, order generation. | Current backtest is portfolio-return review, not strategy/alpha backtesting and optimization. |
| Backtrader | Strategy testing should support multi-data, multi-strategy, indicators, and live/paper modes. | Event-driven strategy backtesting and broker abstraction. | Current historical review cannot test entry/exit rules or generate trade logs. |
| Pyfolio | Useful portfolio analytics include Sharpe, Sortino, rolling stats, drawdown tables, and tear sheets. | Institutional-style performance tear sheet. | Current backtest lacks Sharpe/Sortino, rolling drawdown, beta, alpha, and benchmark comparison. |
| x2strategy | Research papers can be converted into structured strategy specs. | Paper-to-strategy extraction and validation. | Current research asks questions but does not convert papers into executable strategy hypotheses. |

## Capability Gaps

### P0: Product Principle Reset

- Replace defensive wording with actionable recommendation language.
- Define a recommendation schema: `action`, `instrument_ref`, `direction`,
  `horizon`, `confidence`, `rationale`, `risk`, `invalidators`,
  `position_effect`, and `next_action`.
- Split recommendation status into `informational`, `recommended`,
  `paper_executable`, and `live_executable`.

### P1: Minimum Useful Decision Agent

- Build a recommendation engine that aggregates L2 portfolio state, L3 reports,
  L4 role signals, scenario signals, rebalance drift, and backtest context into
  ranked recommendations.
- Add investor-style agents inspired by ai-hedge-fund: value, growth, macro,
  technical, sentiment, risk, and portfolio-manager agents.
- Add a portfolio manager layer that turns votes into a final action plan
  instead of only listing candidate actions.

### P2: Quant And Backtest Upgrade

- Upgrade `portfolio_backtest.py` toward Pyfolio-style tear sheets:
  Sharpe, Sortino, Calmar, beta, alpha, benchmark comparison, rolling return,
  rolling volatility, and drawdown table.
- Add Backtrader/Qlib-inspired strategy backtesting: strategy spec, signal
  series, trade ledger, position sizing, slippage/fees, and out-of-sample split.
- Add strict alpha gate: compare against same-universe random/buy-hold controls.

### P3: Strategy Extraction And Research Hypotheses

- Add x2strategy-style paper/news/filing-to-strategy extraction.
- Maintain a hypothesis registry with status, evidence, linked backtests,
  invalidation notes, and next experiment.
- Convert research outputs into structured hypotheses, not only prose.

### P4: Data Platform And Analyst Cockpit

- Add OpenBB-style provider registry for market, fundamentals, macro, options,
  crypto, filings, news, and broker/account data.
- Add a tool catalog showing each provider's status, freshness, and asset
  coverage.
- Later build a persistent local analyst cockpit; scripts remain the MVP.

### P5: Mandate-Gated Action Layer

- Start with paper trading and simulated execution.
- Add a user mandate file: universe, max order size, max exposure, leverage,
  daily loss cap, allowed account mode, expiry, and kill switch.
- Add pre-trade checks, action audit ledger, and order proposal artifacts.
- Only after paper mode is reliable should live broker integration be considered.

## Reordered TODO

1. Rewrite policy and docs around actionable recommendations.
2. Add a `recommendation_schema` and final recommendation packet.
3. Add portfolio-manager aggregation over existing signals.
4. Add investor-style voting agents.
5. Upgrade performance analytics to Pyfolio-style tear sheet.
6. Add strategy backtest with trade ledger and benchmark controls.
7. Add hypothesis registry and strategy extraction.
8. Add paper trading mandate and audit ledger.
9. Add provider registry and tool catalog.
10. Consider live broker integration only after paper execution, mandate checks,
    and audit logs are proven.

## Immediate MVP

The next implementation step should not be more guardrail work. It should be a
minimum useful recommendation packet:

- inputs: portfolio x-ray, rebalance review, scenario review, backtest metrics,
  research synthesis, and risk rules;
- output: 3-7 ranked recommendations with action, confidence, horizon,
  rationale, risk, invalidators, and next action;
- boundary: recommendation is allowed; real order placement remains unavailable
  until a future mandate-gated execution layer exists.
