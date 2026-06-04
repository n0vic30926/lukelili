# Finance Agent

个人投资 Agent 的本地基础工程。它来自 OpenClaw 导出版本，当前方向是逐步变成本地可维护、可审计、能给出明确建议和行动计划的长期工具。

## 系统定位

**投资建议与行动计划系统，不是收益承诺系统。**

核心理念：Agent 应该能综合研究、组合状态、风险、回测和市场证据，给出可执行前的明确建议：买/卖/持有/再平衡/降低风险、优先级、信心、理由、风险、失效条件和下一步。硬边界不是“不能给投资建议”，而是不能承诺收益、不能把预测说成事实、不能在未授权状态下真实下单。

### 三层架构

| 层级 | 作用 | 完成度 |
|---|---|---|
| L1 证据与规则 | 策略隔离、事实/推断/判断分层、风险边界 | ✅ 完成 |
| L2 组合与市场认知 | 组合暴露、回测、再平衡、行业情报、场景压力 | ✅ 持续扩展 |
| L3 建议与行动 | 推荐排序、行动计划、纸面执行、审计复盘 | 🔄 重新编排 |

## 6条固化原则

1. **建议必须明确** — 不再用泛化免责声明替代结论；输出要给方向、理由、风险和下一步
2. **反事实追踪评估"建议是否符合系统原则"** — 不是"结果赚没赚钱"
3. **系统增强纪律，也要形成行动** — "暂停定投"/"降低风险"/"加仓观察"可以成为建议，但真实执行需要授权
4. **输出设计本身就是策略设计** — 隐性含糊语言必须收敛成推荐、证据和失效条件
5. **Agent永远不能替用户定义投资哲学/策略类型** — strategy_type必须用户声明
6. **真实下单是独立能力** — 未来需要 mandate、pre-trade checks、audit ledger、kill switch

## 策略类型系统（First-Class Citizen）

- `dca`（定投）→ 纪律守护模式
- `trial`（试水仓）→ 状态输出only
- `short_term`（短线）→ 止盈止损信号
- `watch`（观察仓）→ research only
- 🔵信念仓 / 🟡试水仓 / ⚪观察仓 — 三层资产分类
- **策略不可变性**：Agent永远不能将策略往反方向拉

## 文件清单

### scripts/（核心脚本，2189行）

| 文件 | 行数 | 功能 |
|---|---|---|
| `daily_finance_brief.py` | 491 | 每日收盘推送（持仓+ETF+指数+估值锚+三因子归因+风控+行业情报+纪律守护） |
| `daily_insight.py` | - | 读者层日报洞察，把组合、风险、推荐、数据盲区翻译成可执行的中文判断 |
| `weekly_finance_review.py` | 341 | 周度回顾（收益+行业资金流+QDII因子周变化+产业周期+定投曲线+决策建议） |
| `industry_cycle.py` | 598 | 15赛道产业周期框架（6量化+9定性+信号整合） |
| `qdii_three_factor.py` | 210 | QDII三因子归因（纳指+汇率+残差）+ AI基金三因子归因（中证AI+行业轮动+残差） |
| `industry_intel.py` | 227 | 行业情报采集（Tavily多关键词+信号分级🔴🟡🟢⚪） |
| `valuation_anchor.py` | 124 | 估值锚（纳指点位百分位+AI指数PE百分位，纯风险提示器） |
| `decision_tracker.py` | 85 | 反事实追踪（每日决策记录→周度合规检查） |

### skills/finance-dispatch/

| 文件 | 功能 |
|---|---|
| `SKILL.md` | 6模式调度：Monitor/Discover/Analyze/Macro/Risk/Industry Cycle |

### memory/

| 文件 | 功能 |
|---|---|
| `portfolio.json` | 已脱敏的 legacy 持仓模板；真实持仓放入 `data/private/portfolio.local.json` |
| `investment_policy.md` | IPS投资者策略声明书 |
| `industry_cycle_framework.md` | 15赛道4层产业周期框架 |

### docs/

| 文件 | 功能 |
|---|---|
| `execution-discipline-no-talk.json` | 执行纪律Gene（防"说了没做"） |

## 数据层

全部基于 **AkShare 直连**（零API Key），覆盖：

| 数据 | AkShare接口 | 状态 |
|---|---|---|
| 场外基金净值 | `fund_open_fund_info_em` | ✅ |
| 基金持仓穿透 | `fund_portfolio_hold_em` | ✅ |
| 场内ETF行情 | `fund_etf_spot_em` | ✅ |
| 北向资金+大盘 | `stock_hsgt_fund_flow_summary_em` | ✅ |
| 美股指数(纳指) | `index_us_stock_sina` | ✅ |
| 汇率实时 | `fx_spot_quote` | ✅ |
| 汇率历史 | `currency_boc_safe` | ✅ |
| 中证指数PE | `stock_zh_index_hist_csindex` | ✅ |
| 行业资金流 | `stock_fund_flow_industry` | ✅ |
| 概念资金流 | `stock_fund_flow_concept` | ✅ |
| 成长性对比 | `stock_zh_growth_comparison_em` | ✅ |
| 研报+盈利预测 | `stock_research_report_em` | ✅ |
| 行业资金流(备用) | `stock_sector_fund_flow_hist` | ⚠️ 间歇性 |

**已知限制**：东方财富反爬拦截云服务器IP（stock_board_industry_name_em等不可用）

## 本地化状态

当前 worktree 已补上本地基础：

- `AGENTS.md`：项目级投资与工程边界；
- `.env.example` / `config/settings.example.json`：本地密钥和路径配置示例；
- `schemas/portfolio.schema.json`：portfolio schema，包含风险规则、持仓数值和买入记录约束；
- `data/examples/portfolio.example.json`：虚构示例持仓；
- `scripts/common/config_loader.py`：统一读取本地配置；
- `scripts/common/report_decision_context.py`：将 portfolio x-ray 与情景信号并入日报/周报输出契约；
- `scripts/validate_portfolio.py`：标准库 portfolio 校验；
- `scripts/smoke_test.py`：离线基础检查。
- `docs/OPEN_SOURCE_AGENT_BENCHMARK.md`：开源投资 Agent 横向对比与重新排序 TODO。

真实持仓应放在 `data/private/portfolio.local.json`，不要提交到 git。用户确认后的策略类型、目标权重、现金和补充交易可放在 ignored 的 `data/private/portfolio.overlay.json`，并在确认后设置 `enabled=true`。

## 本地检查

```bash
python3 scripts/smoke_test.py
python3 scripts/competitive_readiness.py
python3 scripts/ideal_agent_readiness.py
python3 scripts/portfolio_backtest.py
python3 scripts/portfolio_intersection.py
python3 scripts/portfolio_gap_review.py
python3 scripts/portfolio_xray.py
python3 scripts/portfolio_scenarios.py
python3 scripts/rebalance_review.py
python3 scripts/validate_portfolio.py data/examples/portfolio.example.json
python3 scripts/validate_scenarios.py data/examples/scenario_assumptions.example.json
python3 scripts/mock_competitive_readiness_test.py
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
python3 scripts/mock_portfolio_backtest_test.py
python3 scripts/mock_portfolio_exposure_test.py
python3 scripts/mock_portfolio_intersection_test.py
python3 scripts/mock_portfolio_overlay_test.py
python3 scripts/mock_portfolio_scenarios_test.py
python3 scripts/mock_portfolio_validation_test.py
python3 scripts/mock_portfolio_xray_test.py
python3 scripts/mock_rebalance_review_test.py
python3 scripts/mock_report_branch_fixtures_test.py
python3 scripts/mock_report_advice_classification_test.py
python3 scripts/mock_report_decision_context_test.py
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
python3 scripts/mock_research_coverage_test.py
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
python3 scripts/mock_scenario_validation_test.py
python3 scripts/mock_reporting_test.py
python3 scripts/mock_security_scan_test.py
python3 scripts/mock_signal_ranking_test.py
python3 scripts/mock_weekly_status_test.py
python3 scripts/security_scan.py
```

运行日报/周报前需要用户手动安装依赖：

```bash
python3 -m pip install -r requirements.txt
```

如果缺少 `akshare` 等运行依赖，日报/周报会输出安装提示并退出，不生成伪报告。

生成成功后会写入：

- `reports/daily/`
- `reports/weekly/`
- `reports/index.jsonl`
- `logs/finance-agent.jsonl`
- `cache/`

报告运行摘要会展示模块成功/失败/跳过数量、来源层级和数据新鲜度标签。

查看报告归档索引：

```bash
python3 scripts/report_index.py
```

生成面向日常决策的可读日报洞察：

```bash
python3 scripts/daily_insight.py
```

查看报告连续性、重复失败模块和私有决策记录的策略类型摘要：

```bash
python3 scripts/review_history.py
```

`review_history.py` 只输出聚合信息，不打印持仓代码、名称、成本或份额。

生成 L4 研究角色调度计划：

```bash
python3 scripts/research_dispatch.py "宏观 利率 个股 财报 ETF 组合风险 复盘"
```

执行本地只读角色并合并研究报告：

```bash
python3 scripts/research_dispatch.py --execute "宏观 利率 个股 财报 ETF 组合风险 复盘"
```

`research_dispatch.py` 只输出研究任务契约或聚合研究报告，不连接券商、不下单、不替用户确认交易。

生成 L5 ranked recommendation 决策包：

```bash
python3 scripts/decision_support.py "组合风险 复盘 决策辅助"
```

`decision_support.py` 会先输出 3-7 条 ranked recommendations，每条包含
action、instrument_ref、direction、confidence、horizon、status、rationale、
risks、invalidators、position_effect 和 next_action；随后保留候选动作、
证据、风险规则、场景信号、再平衡信号和人工确认清单作为审计层。
`execution_allowed` 仍为 `false`，直到未来 mandate-gated execution 模块存在。

## 原 Cron 任务配置

```
daily-finance-brief   Mon-Fri 15:30   每日收盘推送
weekly-finance-review  Sat 11:00      周度回顾
weekly-intel-briefing  Sat 10:00      行业情报（共用）
```

Delivery配置（所有cron通用）：
```json
{
  "channel": "openclaw-weixin",
  "to": "<user_id@im.wechat>",
  "accountId": "<account_id>"
}
```

## 依赖

- Python 3.12+
- akshare（pip install akshare）
- tavily-python（行业情报搜索）
- 基金净值走东方财富API（fundgz.1234567.com.cn）
- 美股指数走新浪财经
- 汇率走国家外汇局

## 设计亮点

1. **策略类型不可变** — Agent永远不能修改用户声明的策略类型
2. **行动语言显性化** — 隐性择时措辞要落到推荐、置信度、风险和失效条件
3. **QDII三因子归因** — 纳指贡献+汇率贡献+残差，30天解释75.5%
4. **15赛道产业周期** — 从存储芯片到CPO到AI SaaS的全产业链覆盖
5. **反事实追踪** — 自动记录每日建议，周度检查是否偏离纪律原则
6. **估值锚进入建议层** — 99.6%百分位可进入风险/信号判断和仓位建议；真实下单另行授权

## 路线图

- [x] L1/L2 本地基础：规则、配置隔离、示例数据、schema、smoke test、输出分层契约
- [x] L1 报告源头分类：日报/周报建议区内部按 Facts/Inferences/Judgment/Confirmation 分层
- [x] L2 本地暴露检查：现金/持仓比例、最大单仓、策略/因子/市场分布匿名汇总
- [x] L2 本地历史回测：可选 return_history 计算组合累计收益、最大回撤、年化波动
- [x] L2 目标配置漂移：可选 target_weight_pct 与 rebalance_tolerance_pct 生成再平衡复核信号
- [x] L2 底层持仓交叉：本地 underlying_holdings 穿透、直接/间接重叠和集中度脱敏输出
- [x] L3 报告稳定化：依赖检查、日志、缓存、归档、模块状态摘要
- [x] L3 数据质量：宏观/ETF/新闻数据源质量分层和失败可见化
- [x] L3 历史复盘摘要：报告连续性、重复失败模块、策略纪律聚合统计
- [x] L3 报告分支夹具：脱敏覆盖 success/failed/skipped/cache_hit 输出路径
- [x] L3 数据源解释：运行摘要将 data_module 状态映射为报告可信度影响
- [x] 安全基线：tracked 文件敏感信息扫描、memory/Skill 脱敏模板化
- [x] 行业情报本地化：从 portfolio 动态生成资讯查询和影响标签
- [x] 因子归因本地化：从 portfolio `factor_profile` 动态路由 QDII/AI 归因
- [x] L4 最小研究调度：Macro / Industry / Security / ETF / Risk / Review 角色契约
- [x] L4 只读研究执行：本地角色 runner 与聚合研究报告
- [x] 证据可靠性排序：source_tier / freshness / score 进入研究与决策输出
- [x] L4 Macro 只读数据适配：利率、汇率、流动性 AkShare 状态与缺依赖降级
- [x] L4 Industry 只读数据适配：组合驱动新闻查询数、行业/概念轮动 AkShare 状态与缺依赖降级
- [x] L4 Risk 只读数据适配：匿名组合暴露、风险规则/因子状态、市场报价状态与缺依赖降级
- [x] L4 Review 只读数据适配：报告连续性、重复失败、数据质量、决策记录与确认阻断项脱敏汇总
- [x] L4 Security 数据适配扩展：财务/公告/估值之外加入个股行情流动性与研报状态
- [x] L4 ETF 数据适配扩展：行情/流动性/溢价之外加入净值历史与持仓穿透状态
- [x] L4 ETF 持仓规范化：AkShare holdings 行转为 stock-intersection 可消费的底层持仓结构
- [x] L4 Macro 数据适配扩展：利率/汇率/流动性之外加入通胀与 PMI 状态
- [x] L4 Industry 数据适配扩展：新闻搜索可用性之外加入新闻结果计数与信号分布
- [x] L4 Risk 数据适配扩展：本地硬规则违例、现金缓冲与指数基准状态
- [x] L4 跨角色证据综合：角色状态、数据源状态、缺口和 ranked evidence 汇总进入 L5 审计
- [x] L4 研究覆盖矩阵：跨角色数据源覆盖率、缺口优先级和 coverage gaps 进入研究/L5 输出
- [x] L4 数据状态解释：将角色数据源可用性映射为组合影响路径和未确认限制
- [x] L4 角色研究问题：按角色和数据源状态生成下一步核查问题
- [x] L4 研究分支夹具：脱敏覆盖 ok/skipped/failed、证据、解释、问题路径
- [ ] L4 多 Agent 研究角色：接入更完整的真实数据工具与证据排序
- [x] L5 决策辅助安全层：候选动作、风险、风险硬规则检查、确认清单，不允许自动交易
- [x] L5 人工确认工作流：pending confirmation state、阻断项、不可执行边界
- [x] L5 确认记录与复盘：脱敏 confirmation JSONL 与 history review 汇总
- [x] L5 确认状态审计：跨角色未确认数据源进入 manual confirmation blockers
- [x] L5 半自动决策辅助：确认状态审计与人工复核队列，不允许自动交易
- [x] L5 人工复核结果记录：脱敏 resolution JSONL 与 history review 汇总，不构成交易授权
- [x] 端到端验收矩阵：用 tracked 示例数据检查 L1-L5 与安全边界 readiness
- [x] 竞品重编排：基于 OpenBB / Fincept / ai-hedge-fund / AutoHedge / Vibe-Trading / FinGPT / FinRL / Qlib / Backtrader / Pyfolio / x2strategy 重排 TODO
- [ ] P1 推荐引擎 MVP：生成 ranked recommendations，包含 action / confidence / horizon / rationale / risk / invalidators / next_action
- [ ] P1 投资风格 Agent 投票：value / growth / macro / technical / sentiment / risk / portfolio manager
- [ ] P2 Pyfolio 风格绩效分析：Sharpe / Sortino / Calmar / beta / alpha / benchmark / rolling stats
- [ ] P2 策略回测：strategy spec / signal series / trade ledger / sizing / fees / OOS split
- [ ] P3 hypothesis registry 与 x2strategy 风格研究转策略
- [ ] P5 纸面执行：mandate / order proposal / pre-trade checks / audit ledger / kill switch

---

_打包时间: 2026-05-30_
_代码行数: 2189行（7个脚本）_
_建设周期: 2026-05-27 ~ 05-28（2天）_
_版本: Phase 4 完成_
