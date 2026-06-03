# Competitive Benchmark

This benchmark is the prerequisite for roadmap iteration. Future work should not
add capabilities only because they sound useful. Each meaningful roadmap item
should map to a competitor-proven capability, a local competitive advantage, or
an explicit guardrail.

## Competitor Capability Matrix

| Segment | Benchmarks | Capabilities to Track | Local Iteration Implication |
|---|---|---|---|
| Robo-advisors | Betterment, Wealthfront, Schwab Intelligent Portfolios, Vanguard Digital Advisor | goal/risk profiling, diversified portfolios, automated rebalancing, tax-loss harvesting where applicable, tax-aware portfolio maintenance | Match the discipline loop and risk visibility, but keep this project decision support only with no broker execution. |
| Portfolio dashboards | Empower, Morningstar, Portfolio Visualizer, Koyfin | portfolio tracking, portfolio x-ray, allocation and overlap checks, fee/exposure analysis, backtesting, factor analysis, Monte Carlo, efficient frontier, dashboards and reports | Prioritize exposure transparency, scenario review, and explainable historical/risk context before adding broader surface area. |
| AI research and strategy tools | Magnifi, FinChat, Seeking Alpha, Composer | AI research, company/filing/transcript synthesis, watchlists, ratings/factor grades, backtested strategy libraries, strategy automation | Use AI to accelerate research and verification, not to bypass user judgment or trigger trades. |

## Local Competitive Advantages

- local-first privacy: real holdings, costs, shares, account ids, cookies, and API
  keys stay in ignored local files.
- explicit user confirmation: every decision-support packet keeps
  `execution_allowed=false` and requires manual confirmation.
- decision support only: the system must not connect to broker execution
  endpoints, place orders, or present buy/sell/hold language as execution.
- evidence ranking: research output ranks facts by source tier, freshness, and
  reliability instead of flattening all observations into one narrative.
- stock intersection and holdings matrix: local optional `underlying_holdings`
  inputs can expose direct/indirect concentration while keeping only
  anonymized holding and underlying refs in rendered output.
- local backtesting: optional `return_history` inputs can expose historical
  return, drawdown, volatility, and coverage warnings without implying future
  returns.
- rebalance drift review: optional target allocation and tolerance inputs can
  surface drift-based rebalance signals for manual confirmation, preserving the
  automated-advisor discipline loop without broker execution.
- data freshness: reports and research roles show data-source status, freshness,
  and degraded paths when a source is missing or stale.
- multi-role research: Macro, Industry, Individual Security, ETF, Risk, and
  Review roles preserve separation of concerns.
- discipline review loop: daily/weekly reporting, decision records, review
  history, and confirmation blockers make behavior drift visible.
- auditability: smoke tests, security scans, readiness matrices, and sanitized
  fixtures make the system locally inspectable.

## Iteration Gate

Before a roadmap item is implemented, it should satisfy at least one of these
conditions:

1. It closes a capability gap visible in the Competitor Capability Matrix.
2. It strengthens a Local Competitive Advantages item.
3. It reinforces a guardrail required by AGENTS.md or
   docs/SECURITY_AND_BOUNDARIES.md.

If an item cannot satisfy one of these conditions, defer it until the benchmark
or roadmap is updated with a clear reason.

## Source Notes

Observed on 2026-06-03 using public product/help pages. These links are used as
benchmark inputs, not endorsements or investment advice.

- Betterment automated investing and tax-loss harvesting:
  https://www.betterment.com/investing
- Betterment portfolio rebalancing methods:
  https://www.betterment.com/help/portfolio-rebalancing-methods
- Wealthfront tax-loss harvesting:
  https://www.wealthfront.com/tax-loss-harvesting
- Wealthfront rebalancing support:
  https://support.wealthfront.com/hc/en-us/articles/209353766-How-often-do-you-rebalance-my-Automated-Investing-Account
- Wealthfront US Direct Indexing:
  https://support.wealthfront.com/hc/en-us/articles/211005023-Wealthfront-s-US-Direct-Indexing
- Schwab Intelligent Portfolios:
  https://www.schwab.com/intelligent-portfolios
- Schwab tax-loss harvesting disclosures:
  https://www.schwab.com/legal/institutional-intelligent-portfolios-tax-loss-harvesting-disclosures
- Vanguard Digital Advisor:
  https://investor.vanguard.com/advice/robo-advisor
- Vanguard advice comparison:
  https://investor.vanguard.com/advice
- Empower financial tools:
  https://www.empower.com/tools
- Empower investment account details:
  https://support-personalwealth.empower.com/hc/en-us/articles/201169720-Investment-Account-Details
- Empower retirement fee analyzer:
  https://support-personalwealth.empower.com/hc/en-us/articles/201169600-Retirement-Fee-Analyzer-Calculations-Overview
- Morningstar X-Ray:
  https://www.morningstar.com/help-center/portfolio/xray
- Morningstar Stock Intersection:
  https://www.morningstar.com/help-center/portfolio/stock-intersection
- Morningstar Investor portfolio tools:
  https://www.morningstar.com/tools/portfolio/all
- Portfolio Visualizer:
  https://www.portfoliovisualizer.com/
- Koyfin model portfolios:
  https://www.koyfin.com/features/model-portfolios/
- Koyfin holdings matrix:
  https://www.koyfin.com/help/model-portfolio-holdings-matrix/
- Magnifi personal AI investing:
  https://magnifi.com/magnifi-personal
- FinChat:
  https://finchat.io/
- Seeking Alpha portfolio ratings:
  https://help.seekingalpha.com/migration/premium/how-to-track-and-optimize-your-portfolio-using-seeking-alphas-ratings
- Composer symphony database:
  https://www.composer.trade/trading-strategies
