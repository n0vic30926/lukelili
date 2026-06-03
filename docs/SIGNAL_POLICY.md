# Signal Policy

This project may output projections and buy/sell/hold-style signals when they
are useful for personal decision support. These signals are allowed only under
the boundaries below.

## Allowed

- Model projections, hypothetical scenarios, and stress tests.
- Candidate buy/sell/hold/rebalance/reduce-risk style signals.
- Short-term, long-term, watchlist, and risk-review signal labels.

## Required Framing

- Projections must be labeled as model judgment or model projection, not facts.
- Signals must be labeled as decision support, not user consent.
- Every signal must require explicit user confirmation.
- The output must keep `execution_allowed=false`.
- External data must keep source and freshness context when used.

## Still Prohibited

- Automatic trading.
- Broker execution integration.
- Executable order payloads.
- Promised returns.
- Presenting a projection as a fact.
- Treating a signal as user consent.
