# 金融投资辅助Agent — 完整包

> 从零搭建、经过实战验证的个人投资辅助系统。
> 3天从Phase 1到Phase 4，2189行代码，7个脚本，3个cron任务。

## 系统定位

**纪律守护系统，不是alpha预测系统。**

核心理念：定投系统的真正敌人不是判断错误，而是行为偏差（恐慌割肉、追涨杀跌）。系统增强纪律，绝不替代纪律。

### 三层架构

| 层级 | 作用 | 完成度 |
|---|---|---|
| L1 执行纪律 | 策略隔离、纪律守护、反事实追踪 | ✅ 完成 |
| L2 世界认知 | 15赛道产业周期框架、行业情报 | ✅ 完成 |
| L3 投资哲学 | IPS投资者档案、策略声明书 | 🔄 初版完成 |

## 6条固化原则

1. **估值锚是风险提示器，不是交易信号器** — 永远不输出"暂停/加仓/止盈"
2. **反事实追踪评估"建议是否符合系统原则"** — 不是"结果赚没赚钱"
3. **系统增强纪律，绝不替代纪律** — "暂停定投"出现在输出中就是系统bug
4. **输出设计本身就是策略设计** — 隐性择时语言必须清除
5. **Agent永远不能替用户定义投资哲学/策略类型** — strategy_type必须用户声明
6. **人格标签化是危险信号** — 应改为时间戳行为记录

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
| `portfolio.json` | 持仓档案（基金代码+策略类型+成本+份额+风控规则+用户画像） |
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

## Cron任务配置

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
2. **择时语言清除** — 所有隐性择时措辞（"建议关注"/"关注回调"）已替换为纯状态描述
3. **QDII三因子归因** — 纳指贡献+汇率贡献+残差，30天解释75.5%
4. **15赛道产业周期** — 从存储芯片到CPO到AI SaaS的全产业链覆盖
5. **反事实追踪** — 自动记录每日建议，周度检查是否偏离纪律原则
6. **估值锚纯风险提示** — 99.6%百分位只输出"高估区注意风险"，绝不输出"暂停定投"

## 路线图

- [ ] Phase 4a: 投资者画像完善（风险承受力量化测试）
- [ ] Phase 4b: 策略声明书IPS正式版（Luke定义，Agent执行）
- [ ] Phase 5: 产业周期地图可视化 + narrative追踪 + 观点可信度系统
- [ ] 拆分为独立Agent（已决定，暂不急）

---

_打包时间: 2026-05-30_
_代码行数: 2189行（7个脚本）_
_建设周期: 2026-05-27 ~ 05-28（2天）_
_版本: Phase 4 完成_
