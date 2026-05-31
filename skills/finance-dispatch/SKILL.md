# Finance Dispatch Skill

金融意图路由层——根据用户自然语言问题，自动选择正确的数据工具和分析模式。

## 触发条件

用户提到任何与投资、基金、股票、市场、指数、汇率、定投、盈亏相关的关键词时激活。

## 四模式调度映射

### 1. Monitor（日常监控）
**触发信号**: "简报"、"今天怎么样"、"每天"、"持仓"、"盘面"
**数据采集**:
- `daily_finance_brief.py` 完整输出
**输出格式**: 简报格式，简洁为主

### 2. Discover（行业发现）
**触发信号**: "AI板块"、"半导体"、"新能源"、"概念"、"热点"、"涨得好的"、"跌得多的"
**数据采集**:
- AkShare: `stock_fund_flow_industry()`（90个行业资金流向，首选）
- AkShare: `stock_fund_flow_concept()`（概念板块资金流）
- cn-financial: `get_industry_list`（行业列表/名称查询）
- cn-financial: `get_concept_list`（概念板块列表）
**输出格式**: 行业涨跌排名 + 资金流向 + 与持仓关联分析

### 3. Analyze（深度分析）
**触发信号**: "值不值得"、"还能买吗"、"定投评估"、"这只基金怎么样"、"持仓穿透"、"重仓股"
**数据采集**:
- AkShare: `fund_portfolio_hold_em`（基金持仓穿透——十大重仓+占比）
- AkShare: `stock_zh_growth_comparison_em`（成长性+行业排名）
- AkShare: `stock_research_report_em`（机构评级+盈利预测）
- cn-financial: `get_income_statement`（营收/成本/研发/净利润/每股收益）
- cn-financial: `get_valuation_metrics`（PE/PB时间序列）
- cn-financial: `get_financial_line_item`（关键财务科目趋势）
**输出格式**: 深度分析报告，含估值判断、财务健康度、机构观点

### 4. Macro（宏观因子）
**触发信号**: "美联储"、"降息"、"汇率"、"QE"、"通胀"、"GDP"、"PMI"、"利率"、"宏观"
**数据采集**:
- AkShare: `currency_boc_safe()`（USD/CNY中间价历史，1994至今日线）
- AkShare: `fx_spot_quote()`（实时汇率）
- AkShare: `index_us_stock_sina`（纳斯达克/标普等美股指数）
- cn-financial: `get_macro_cpi` / `get_macro_gdp` / `get_macro_pmi` / `get_macro_money_supply`
- cn-financial: `get_bond_yield_curve`（国债收益率）
**输出格式**: 因子拆解——宏观事件→对持仓的具体影响路径

### 4.5 Industry Cycle（产业周期 — 事件触发，非定时）
**触发信号**: "AI产业什么阶段"、"产业周期"、"半导体周期"、"AI泡沫"、"产业链全景"、重大决策前（调仓/升级仓位）
**调用模式**（按需，不走cron）:
- `industry_cycle.py --quant`（块1量化信号，<5秒）→ 想快速看硬件赛道涨跌+纳指/北向信号
- `industry_cycle.py --full`（完整15赛道报告，30-60秒）→ 深度决策辅助
- **weekly review 自动集成**: 块1量化信号已嵌入周六周报，无需手动跑
**数据源**:
- 块1: AkShare（纳指/北向/行业资金流/半导体/光学/通信）
- 块2: Tavily News（9个定性赛道的新闻信号采集）
**信号分级**: 🔴影响持仓 / 🟡趋势变化 / 🟢利好 / ⚪参考信息
**输出格式**: 15赛道全景图 + 信号汇总

### 5. Risk（风险分析）
**触发信号**: "风险"、"回调"、"止损"、"仓位"、"相关性"、"分散"、"组合"
**数据采集**:
- AkShare: 两只持仓基金的历史净值序列（计算相关性）
- cn-financial: `get_money_flow`（个股资金流向，穿透后用）
- portfolio.json 风控规则
**输出格式**: 风险评估——组合相关性、因子暴露、集中度分析

## 调度规则

1. **单模式优先**: 用户意图匹配一个模式就用一个，不混用
2. **混合意图拆分**: 用户一句话涉及多个模式时，按 Monitor→Risk→Analyze→Discover→Macro 优先级取最高的两个
3. **默认兜底**: 无法识别意图时走 Monitor 模式
4. **术语扫盲**: 已扫盲概念（QDII、ETF溢价、净值vs市价、管理费、定投DCA、Buy the Dip、VOO、资本利得税、宽基指数、股息预扣税、标普500、纳指100）不重复解释
5. **新概念自动扫盲**: 首次出现未扫盲术语时附带一句话解释

## 工具可用性（2026-05-27实战验证）

### ✅ 可用
- **估值指标**: cn-financial `get_valuation_metrics` — PE/PB/市值时间序列（仅个股，ETF不可用）
- **利润表**: cn-financial `get_income_statement` — 营收/成本/研发/净利润/每股收益
- **财务科目趋势**: cn-financial `get_financial_line_item` — 支持模糊匹配科目名
- **公司主营**: cn-financial `get_company_profile` — 业务构成+经营范围
- **行业板块列表**: cn-financial `get_industry_list` — 88个行业全覆盖
- **实时汇率**: cn-financial `get_fx_rate` + AkShare `fx_spot_quote` — 实时可用
- **基金持仓穿透**: AkShare `fund_portfolio_hold_em` — 十大重仓+占比
- **场外基金净值**: AkShare `fund_open_fund_info_em` — 历史序列+当日
- **美股指数**: AkShare `index_us_stock_sina` — 纳指/标普等
- **大盘指数**: AkShare `stock_hsgt_fund_flow_summary_em` — 沪深指数涨跌
- **搜索**: cn-financial `search_stock` — 模糊匹配

### ❌ 不可用（数据源缺陷，非配置问题）
- **公司基本信息** `get_company_info` — 部分股票查不到
- **财务指标汇总** `get_financial_indicators` — 返回空（ROE/毛利率等）
- **成长指标** `get_growth_rates` — 返回空
- **分析师评级** `get_analyst_rating` — 空列表
- **行业资金流向** `get_sector_fund_flow` — 云服务器被东方财富反爬拦截
- **行业成分股** `get_industry_stocks` — 同上被拦截
- **竞争对手** `get_competitors` — 同上被拦截

### 绕行方案（已验证）
- **ROE/毛利率** → cn-financial `get_income_statement` 手动计算（净利润/营收、毛利润/营收）
- **成长性+行业排名** → AkShare `stock_zh_growth_comparison_em(symbol='SZ002415')` — 完美替代！含3年复合增长率+TTM+行业排名
- **机构评级+盈利预测** → AkShare `stock_research_report_em(symbol='002415')` — 含东财评级、机构名、2026-2028盈利预测EPS+PE
- **行业资金流向** → ✅ AkShare `stock_fund_flow_industry()` — 90个行业板块，流入/流出/净额/领涨股全有！比cn-financial原接口更完整
- **概念板块资金流** → ✅ AkShare `stock_fund_flow_concept()` — 概念板块资金流，同上格式
- **汇率历史30天** → ✅ AkShare `currency_boc_safe()` — 人民银行中间价，1994年至今日线数据，单位：人民币/百美元，除以100即可
- **竞争对手** → AkShare `stock_zh_growth_comparison_em` 返回同行业排名公司列表

## 用户持仓读取规则

- 从 `data/private/portfolio.local.json` 读取真实持仓；没有该文件时只使用 `data/examples/portfolio.example.json` 并明确标注示例数据。
- 不在 Skill、README、docs 或测试样例中写入真实基金代码、名称、成本、份额、预算或交易记录。
- 风控规则以 portfolio 文件中的 `risk_rules` 为准；缺失时只提示“风控规则未声明”，不要替用户编造。
- 组合集中度、底层相关性和策略类型必须从本地 portfolio 推导，不能依赖硬编码持仓。
