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
- `scripts/smoke_test.py`：本地基础设施检查。

## 快速开始

```bash
cp .env.example .env
cp config/settings.example.json config/settings.local.json
```

把真实持仓放到：

```text
data/private/portfolio.local.json
```

不要把真实密钥、真实持仓、交易记录提交到 git。

## Smoke Test

```bash
python3 scripts/smoke_test.py
```

该命令检查项目规则、配置示例、schema、示例持仓、配置加载器、敏感信息隔离和 OpenClaw 路径隔离。

## 运行日报/周报

```bash
python3 scripts/daily_finance_brief.py
python3 scripts/weekly_finance_review.py
```

如果没有 `data/private/portfolio.local.json`，脚本会回退到 `data/examples/portfolio.example.json`，并在报告中标注当前使用示例数据。

## 新闻模块

默认关闭新闻模块。需要启用时：

1. 在 `.env` 中设置 `TAVILY_API_KEY`。
2. 在 `config/settings.local.json` 中把 `enable_news` 改为 `true`。

缺少 key 时，新闻模块会跳过，不应导致日报或周报整体失败。

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
