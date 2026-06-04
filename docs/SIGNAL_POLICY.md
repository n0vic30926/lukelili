# Signal Policy

This project should output projections and buy/sell/hold-style signals when
they are useful for personal investment decisions. The goal is not to avoid
investment advice; the goal is to make recommendations explicit, evidenced, and
bounded by execution authority.

## Allowed

- Model projections, hypothetical scenarios, and stress tests.
- Candidate and recommended buy/sell/hold/rebalance/reduce-risk style signals.
- Short-term, long-term, watchlist, and risk-review signal labels.
- Action plans with priority, confidence, rationale, risk, and next action.

## Required Framing

- Projections must be labeled as model judgment or model projection, not facts.
- Signals must be labeled as recommendations or model judgment, not facts.
- Every signal must state whether it is informational, recommendation-level, or
  execution-ready.
- Until an explicit execution module exists, the output must keep
  `execution_allowed=false`.
- External data must keep source and freshness context when used.

## Still Prohibited

- Real automatic trading without an explicit user mandate.
- Silent broker execution integration.
- Executable order payloads.
- Promised returns.
- Presenting a projection as a fact.
- Treating a signal as user consent.
