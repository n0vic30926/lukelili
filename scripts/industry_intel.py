#!/usr/bin/env python3
"""
行业情报采集 — 每日外部资讯+盘面数据融合分析
从Tavily搜索行业资讯，结合持仓做信号标注和行动建议
"""

import json, os, sys, traceback
from datetime import datetime, timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
from common.config_loader import get_portfolio_path, get_tavily_api_key, load_settings
from common.data_runtime import DataStatusTracker, cached_call, missing_dependencies

try:
    import requests
except ImportError:
    requests = None

SETTINGS = load_settings()
PORTFOLIO_PATH, USING_EXAMPLE_PORTFOLIO = get_portfolio_path(SETTINGS)
TAVILY_API_KEY = get_tavily_api_key(SETTINGS)
TRACKER = DataStatusTracker()
MISSING_RUNTIME_DEPS = missing_dependencies(["requests"])


def get_news_status():
    if not SETTINGS.get("enable_news", False):
        return {"skipped": True, "reason": "enable_news=false"}
    if not TAVILY_API_KEY:
        return {"skipped": True, "reason": f"{SETTINGS.get('tavily_api_key_env', 'TAVILY_API_KEY')} 未设置"}
    if MISSING_RUNTIME_DEPS:
        return {"skipped": True, "reason": f"缺少依赖: {', '.join(MISSING_RUNTIME_DEPS)}"}
    return {"skipped": False, "reason": ""}

# 搜索关键词矩阵：按持仓关联度分组
SEARCH_QUERIES = [
    # QDII相关（纳指100/美股科技）
    {
        "query": "纳斯达克 美股科技 走势分析",
        "tags": ["QDII", "美股"],
        "impact": "016452"
    },
    {
        "query": "美联储 利率决议 美元指数",
        "tags": ["QDII", "宏观", "汇率"],
        "impact": "016452"
    },
    # AI基金相关（中证AI/A股科技）
    {
        "query": "AI人工智能 半导体 板块 资金流向",
        "tags": ["AI", "A股"],
        "impact": "011840"
    },
    {
        "query": "AI行业 政策 技术突破 产业动态",
        "tags": ["AI", "行业"],
        "impact": "011840"
    },
    # 宏观/汇率
    {
        "query": "人民币汇率 离岸人民币 央行政策",
        "tags": ["汇率", "宏观"],
        "impact": "016452"
    },
]


def search_tavily(query, days=3, max_results=5):
    """Tavily搜索，返回最近N天的相关资讯"""
    if get_news_status().get("skipped"):
        return []
    url = "https://api.tavily.com/search"
    payload = {
        "api_key": TAVILY_API_KEY,
        "query": query,
        "search_depth": "basic",
        "max_results": max_results,
        "include_answer": False,
        "topic": "news",
        "days": days,
    }
    def producer():
        resp = requests.post(url, json=payload, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
        return results

    return cached_call(
        SETTINGS,
        TRACKER,
        f"tavily:{query}",
        "Tavily News",
        f"tavily:{query}:{days}:{max_results}",
        producer,
        [{"title": f"搜索失败: {query}", "content": "Tavily request failed", "url": ""}],
    )


def classify_signal(title, content, tags):
    """根据内容关键词标注信号等级"""
    text = (title + " " + content).lower()

    red_keywords = ["暴跌", "崩盘", "危机", "黑天鹅", "制裁", "紧急", "熔断",
                    "重大利空", "大幅下调", "crash", "plunge", "tariff hike",
                    "selloff", "recession"]
    yellow_keywords = ["回调", "调整", "震荡", "分化", "谨慎", "观望",
                       "转向", "拐点", "放缓", "压力", "concern", "caution",
                       "pullback", "correction", "mixed", "inflation",
                       "rate hike"]
    green_keywords = ["利好", "突破", "新高", "上涨", "增长", "反弹",
                      "政策支持", "超预期", "加速", "rise", "rally", "high",
                      "gain", "surge", "record", "optimism", "boom",
                      "all-time high", "soar"]

    red_score = sum(1 for kw in red_keywords if kw in text)
    yellow_score = sum(1 for kw in yellow_keywords if kw in text)
    green_score = sum(1 for kw in green_keywords if kw in text)

    # 考虑英文和中文双语匹配
    if red_score >= 1:
        return "🔴", "需关注"
    elif green_score >= 1 and yellow_score == 0:
        return "🟢", "利好信号"
    elif yellow_score >= 1:
        return "🟡", "趋势变化"
    else:
        return "⚪", "参考信息"


def fetch_industry_intel():
    """采集全部行业资讯，去重+分级"""
    all_articles = []
    seen_titles = set()

    for sq in SEARCH_QUERIES:
        results = search_tavily(sq["query"], days=3, max_results=5)
        for r in results:
            title = r.get("title", "").strip()
            if not title or title in seen_titles:
                continue
            seen_titles.add(title)

            content = r.get("content", "").strip()
            # 过滤导航栏垃圾内容
            if 'Best gifts for' in content or len(content) < 50:
                continue
            url = r.get("url", "")
            # 过滤非新闻页面
            if any(skip in url for skip in ['/video/', '/watch/', '/market-talk/']):
                continue
            signal_emoji, signal_level = classify_signal(title, content, sq["tags"])

            all_articles.append({
                "title": title,
                "content": content[:300],  # 截断
                "url": url,
                "tags": sq["tags"],
                "impact": sq["impact"],
                "signal": signal_emoji,
                "signal_level": signal_level,
            })

    # 按信号等级排序：🔴 > 🟡 > 🟢 > ⚪
    signal_order = {"🔴": 0, "🟡": 1, "🟢": 2, "⚪": 3}
    all_articles.sort(key=lambda x: signal_order.get(x["signal"], 9))

    return all_articles


def format_intel_report(articles):
    """格式化输出"""
    lines = []
    lines.append("# 📡 行业情报速递 | " + datetime.now().strftime("%Y-%m-%d"))
    lines.append("")

    if not articles:
        status = get_news_status()
        if status.get("skipped"):
            lines.append(f"新闻模块跳过: {status['reason']}")
        else:
            lines.append("今日无重要行业资讯更新。")
        return "\n".join(lines)

    # 按信号等级分组
    red = [a for a in articles if a["signal"] == "🔴"]
    yellow = [a for a in articles if a["signal"] == "🟡"]
    green = [a for a in articles if a["signal"] == "🟢"]
    white = [a for a in articles if a["signal"] == "⚪"]

    if red:
        lines.append("## 🔴 重大信号（直接影响持仓）")
        lines.append("")
        for a in red:
            funds = "QDII" if a["impact"] == "016452" else "AI基金" if a["impact"] == "011840" else "组合"
            lines.append(f"**[{funds}] {a['title']}**")
            lines.append(f"  {a['signal_level']} | {a['content'][:200]}")
            if a["url"]:
                lines.append(f"  [原文链接]({a['url']})")
            lines.append("")

    if yellow:
        lines.append("## 🟡 趋势变化（持续观察）")
        lines.append("")
        for a in yellow[:5]:  # 最多5条
            funds = "QDII" if a["impact"] == "016452" else "AI基金" if a["impact"] == "011840" else "组合"
            lines.append(f"**[{funds}] {a['title']}**")
            lines.append(f"  {a['signal_level']} | {a['content'][:150]}")
            lines.append("")

    if green:
        lines.append("## 🟢 利好信号")
        lines.append("")
        for a in green[:3]:
            funds = "QDII" if a["impact"] == "016452" else "AI基金" if a["impact"] == "011840" else "组合"
            lines.append(f"- [{funds}] {a['title']}")
        lines.append("")

    if white:
        lines.append(f"## ⚪ 参考信息（{len(white)}条）")
        lines.append("")
        for a in white[:3]:
            lines.append(f"- {a['title'][:60]}")
        if len(white) > 3:
            lines.append(f"- ...还有{len(white)-3}条")
        lines.append("")

    # 持仓影响汇总
    lines.append("## 📊 持仓影响速判")
    lines.append("")
    qdii_red = len([a for a in red if a["impact"] == "016452"])
    qdii_yellow = len([a for a in yellow if a["impact"] == "016452"])
    ai_red = len([a for a in red if a["impact"] == "011840"])
    ai_yellow = len([a for a in yellow if a["impact"] == "011840"])

    if qdii_red > 0:
        lines.append(f"- 🔴 **QDII**: {qdii_red}条重大信号，建议关注今日简报中的因子归因变化")
    elif qdii_yellow > 0:
        lines.append(f"- 🟡 **QDII**: {qdii_yellow}条趋势变化信号，持续观察")
    else:
        lines.append(f"- ✅ **QDII**: 今日无重大信号")

    if ai_red > 0:
        lines.append(f"- 🔴 **AI基金**: {ai_red}条重大信号，建议关注板块资金流")
    elif ai_yellow > 0:
        lines.append(f"- 🟡 **AI基金**: {ai_yellow}条趋势变化信号，持续观察")
    else:
        lines.append(f"- ✅ **AI基金**: 今日无重大信号")

    lines.append("")
    lines.append(f"---")
    lines.append(f"_采集时间: {datetime.now().strftime('%Y-%m-%d %H:%M')} | 数据源: Tavily News_")

    return "\n".join(lines)


if __name__ == "__main__":
    articles = fetch_industry_intel()
    print(f"采集到 {len(articles)} 条资讯")
    print()
    report = format_intel_report(articles)
    print(report)
