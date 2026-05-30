# Finance Agent

个人投资分析 Agent 的本地基础工程。它来自 OpenClaw 导出版本，当前目标是先变成本地可维护、可审计、边界清晰的长期工具。

## 项目定位

Finance Agent 用于：

- 投资纪律守护；
- 每日/周度市场简报；
- 本地持仓风险提示；
- ETF、基金、行业与宏观研究辅助；
- 帮助用户做决策前的结构化分析。

Finance Agent 不用于：

- 自动交易；
- 券商下单；
- 承诺收益；
- 预测短期涨跌；
- 代替用户最终确认。

## 当前能力

- `memory/investment_policy.md`：投资策略声明书和纪律边界。
- `memory/industry_cycle_framework.md`：AI/科技产业周期框架。
- `scripts/daily_finance_brief.py`：每日持仓简报。
- `scripts/weekly_finance_review.py`：周度复盘。
- `scripts/qdii_three_factor.py`：QDII/AI 基金因子归因与组合风险扫描。
- `scripts/valuation_anchor.py`：估值锚风险提示。
- `scripts/industry_intel.py`：可选 Tavily 新闻模块。
- `scripts/industry_cycle.py`：AI 产业周期信号。
- `scripts/common/market_research.py`：日报中的宏观观察与 ETF 代理观察，包括可配置宏观指标、ETF流动性、元数据和溢价/折价估算。
- `scripts/smoke_test.py`：本地基础设施检查。
- `scripts/mock_runtime_test.py`：离线测试缓存、运行状态和数据质量 helper。
- `scripts/mock_report_test.py`：离线生成日报/周报 mock 报告，验证成功、部分失败、新闻跳过和示例持仓分支。
- `scripts/report_index.py`：查看本地报告归档索引。
- `scripts/review_history.py`：聚合报告索引和决策记录，做纪律复盘摘要与策略评分卡。

## 快速开始

```bash
cp .env.example .env
cp config/settings.example.json config/settings.local.json
python3 -m pip install -r requirements.txt
```

把真实持仓放到：

```text
data/private/portfolio.local.json
```

不要把真实密钥、真实持仓、交易记录提交到 git。

## Smoke Test

```bash
python3 scripts/smoke_test.py
python3 scripts/mock_runtime_test.py
python3 scripts/mock_report_test.py
python3 scripts/mock_review_test.py
```

该命令检查项目规则、配置示例、schema、示例持仓、配置加载器、敏感信息隔离、OpenClaw 路径隔离和运行依赖。缺少 `akshare` 等依赖时会给出 WARN，但不会自动安装。

## 运行日报/周报

```bash
python3 scripts/daily_finance_brief.py
python3 scripts/weekly_finance_review.py
```

如果没有 `data/private/portfolio.local.json`，脚本会回退到 `data/examples/portfolio.example.json`，并在报告中标注当前使用示例数据。

如果缺少必要依赖，日报/周报会输出明确安装提示并退出，不生成伪市场分析。

生成成功后会写入：

- `reports/daily/`
- `reports/weekly/`
- `reports/index.jsonl`
- `logs/finance-agent.jsonl`
- `cache/`

查看最近报告索引：

```bash
python3 scripts/report_index.py
```

查看历史复盘摘要：

```bash
python3 scripts/review_history.py
```

复盘只输出聚合信息和策略级检查，不打印成本、份额、资产代码或交易明细。

## 新闻模块

默认关闭新闻模块。需要启用时：

1. 在 `.env` 中设置 `TAVILY_API_KEY`。
2. 在 `config/settings.local.json` 中把 `enable_news` 改为 `true`。

缺少 key 时，新闻模块会跳过，不应导致日报或周报整体失败。

## Portfolio 校验

```bash
python3 scripts/validate_portfolio.py data/examples/portfolio.example.json
```

真实持仓也可以用同一脚本校验，但脚本不会打印资产明细。

## 数据质量

报告会展示：

- 数据模块成功/失败/跳过数量；
- 缓存命中数量；
- 来源层级；
- 数据新鲜度；
- 低质量或异常模块。

## 风险边界

- 所有投资输出必须区分事实、数据推断、模型判断和用户确认动作。
- 不允许自动下单。
- 不允许承诺收益。
- 不允许把预测当事实。
- 外部数据必须尽量标注来源和时间。
- 用户最终确认优先于 Agent 输出。

更多说明见：

- `AGENTS.md`
- `docs/LOCAL_SETUP.md`
- `docs/SECURITY_AND_BOUNDARIES.md`
- `docs/ROADMAP.md`
