#!/usr/bin/env python3
"""
行业情报采集 — 每日外部资讯+盘面数据融合分析
从Tavily搜索行业资讯，结合持仓做信号标注和行动建议
"""

import json, os, sys, requests, traceback
from datetime import datetime, timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
from common.config_loader import get_portfolio_path, get_tavily_api_key, news_enabled

PORTFOLIO_PATH = str(get_portfolio_path())

INJECTION_PATTERNS = [
    "ignore previous instructions",
    "developer message",
    "system prompt",
    "reveal system prompt",
    "泄露系统提示",
    "忽略之前的指令",
]


def get_news_status():
    if not news_enabled():
        return {"skipped": True, "reason": "enable_news=false or API key missing"}
    return {"skipped": False, "reason": ""}


def sanitize_external_text(text, max_length=300):
    cleaned = str(text or "")
    lowered = cleaned.lower()
    for pattern in INJECTION_PATTERNS:
        start = lowered.find(pattern)
        while start >= 0:
            end = start + len(pattern)
            cleaned = cleaned[:start] + "[removed external instruction]" + cleaned[end:]
            lowered = cleaned.lower()
            start = lowered.find(pattern)
    return cleaned.strip()[:max_length]

def _load_portfolio():
    with open(PORTFOLIO_PATH, encoding="utf-8") as f:
        return json.load(f)


def _compact_terms(*values):
    terms = []
    for value in values:
        text = str(value or "").strip()
        if text:
            terms.append(text)
    return " ".join(terms)


def _holding_label(item):
    return str(item.get("name") or item.get("code") or "组合")


def build_search_queries(portfolio):
    """Build news search queries from holdings and watchlist instead of fixed codes."""
    queries = []
    for holding in portfolio.get("holdings", []):
        label = _holding_label(holding)
        query = _compact_terms(
            label,
            holding.get("market"),
            holding.get("type"),
            "走势 风险 资金流 新闻",
        )
        queries.append(
            {
                "query": query,
                "tags": ["holding", str(holding.get("strategy_type") or "unknown")],
                "impact": str(holding.get("code") or label),
                "impact_label": label,
            }
        )

    for item in portfolio.get("watchlist", []):
        label = _holding_label(item)
        query = _compact_terms(label, item.get("reason"), "走势 新闻")
        queries.append(
            {
                "query": query,
                "tags": ["watchlist"],
                "impact": str(item.get("code") or label),
                "impact_label": label,
            }
        )

    if not queries:
        queries.append(
            {
                "query": "全球市场 宏观 利率 汇率 财经新闻",
                "tags": ["macro"],
                "impact": "portfolio",
                "impact_label": "组合",
            }
        )
    return queries


def _impact_label(article):
    return str(article.get("impact_label") or article.get("impact") or "组合")


def search_tavily(query, days=3, max_results=5, tracker=None):
    """Tavily搜索，返回最近N天的相关资讯"""
    if not news_enabled():
        if tracker:
            tracker.skipped("industry_intel", source="Tavily", reason="disabled")
        return []
    api_key = get_tavily_api_key()
    url = "https://api.tavily.com/search"
    payload = {
        "api_key": api_key,
        "query": query,
        "search_depth": "basic",
        "max_results": max_results,
        "include_answer": False,
        "topic": "news",
        "days": days,
    }
    try:
        resp = requests.post(url, json=payload, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
        if tracker:
            tracker.success("industry_intel", source="Tavily", detail=query)
        return results
    except Exception as e:
        if tracker:
            tracker.failure("industry_intel", source="Tavily", error=e)
        return []


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


def fetch_industry_intel(tracker=None):
    """采集全部行业资讯，去重+分级"""
    if not news_enabled():
        if tracker:
            tracker.skipped("industry_intel", source="Tavily", reason="disabled")
        return []

    all_articles = []
    seen_titles = set()

    portfolio = _load_portfolio()
    for sq in build_search_queries(portfolio):
        results = search_tavily(sq["query"], days=3, max_results=5, tracker=tracker)
        for r in results:
            title = sanitize_external_text(r.get("title", ""), max_length=160)
            if not title or title in seen_titles:
                continue
            seen_titles.add(title)

            content = sanitize_external_text(r.get("content", ""), max_length=300)
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
                "content": content,
                "url": url,
                "tags": sq["tags"],
                "impact": sq["impact"],
                "impact_label": sq["impact_label"],
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
            funds = _impact_label(a)
            lines.append(f"**[{funds}] {a['title']}**")
            lines.append(f"  {a['signal_level']} | {a['content'][:200]}")
            if a["url"]:
                lines.append(f"  [原文链接]({a['url']})")
            lines.append("")

    if yellow:
        lines.append("## 🟡 趋势变化（持续观察）")
        lines.append("")
        for a in yellow[:5]:  # 最多5条
            funds = _impact_label(a)
            lines.append(f"**[{funds}] {a['title']}**")
            lines.append(f"  {a['signal_level']} | {a['content'][:150]}")
            lines.append("")

    if green:
        lines.append("## 🟢 利好信号")
        lines.append("")
        for a in green[:3]:
            funds = _impact_label(a)
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
    impacted_labels = sorted({_impact_label(a) for a in red + yellow + green})
    if impacted_labels:
        for label in impacted_labels:
            red_count = len([a for a in red if _impact_label(a) == label])
            yellow_count = len([a for a in yellow if _impact_label(a) == label])
            green_count = len([a for a in green if _impact_label(a) == label])
            if red_count:
                lines.append(f"- 🔴 **{label}**: {red_count}条重大信号，需在报告中单独标注来源与影响路径")
            elif yellow_count:
                lines.append(f"- 🟡 **{label}**: {yellow_count}条趋势变化信号，持续观察")
            elif green_count:
                lines.append(f"- 🟢 **{label}**: {green_count}条利好信号，作为状态参考")
    else:
        lines.append("- ✅ 当前 portfolio 关联资产无重大信号")

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
