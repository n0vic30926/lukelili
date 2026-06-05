#!/usr/bin/env python3
"""Market narrative radar and portfolio-fit review.

The radar is deliberately separated from live news fetching. It gives the
system a stable theme matrix, a narrative verification contract, and a
portfolio-overlap check before external news is added.
"""

from __future__ import annotations

import json
from pathlib import Path

from common.config_loader import load_portfolio, get_repo_root


ROOT = get_repo_root()
DEFAULT_RADAR_PATH = ROOT / "data/examples/market_radar.example.json"

EVIDENCE_SCORES = {
    "official": 95,
    "filing": 90,
    "earnings": 85,
    "major_media": 70,
    "industry_data": 65,
    "social_media": 35,
    "blogger": 25,
    "rumor": 15,
    "radar_only": 10,
    "unverified": 5,
}

TAG_ALIASES = {
    "cn_ai_theme_equity": {"ai", "a_share", "semiconductor", "growth"},
    "qdii_us_equity": {"us_tech", "ai", "semiconductor", "growth"},
    "nasdaq100": {"us_tech", "ai", "semiconductor", "growth"},
    "csi_ai_theme": {"ai", "a_share", "semiconductor", "growth"},
}


def _number(value, default=0.0):
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    return default


def _read_json(path):
    with Path(path).open(encoding="utf-8") as f:
        return json.load(f)


def load_market_radar(path=None):
    return _read_json(path or DEFAULT_RADAR_PATH)


def _token_tags(*values):
    tags = set()
    for value in values:
        text = str(value or "").lower()
        if not text:
            continue
        for key, mapped in TAG_ALIASES.items():
            if key in text:
                tags.update(mapped)
        if "ai" in text or "人工智能" in text:
            tags.add("ai")
        if "nasdaq" in text or "纳指" in text or "科技" in text:
            tags.update({"us_tech", "growth"})
        if "semiconductor" in text or "半导体" in text or "芯片" in text:
            tags.add("semiconductor")
        if "robot" in text or "机器人" in text:
            tags.add("robotics")
        if "space" in text or "航天" in text:
            tags.add("space")
        if "nuclear" in text or "电力" in text or "核电" in text:
            tags.update({"power", "nuclear"})
    return tags


def portfolio_exposure_tags(portfolio):
    holdings = [item for item in portfolio.get("holdings", []) if isinstance(item, dict)]
    total = sum(max(_number(item.get("cost_basis")), 0.0) for item in holdings)
    tag_weights = {}
    holding_tags = []
    for index, holding in enumerate(holdings):
        factor = holding.get("factor_profile") or {}
        tags = _token_tags(
            holding.get("name"),
            holding.get("code"),
            holding.get("market"),
            factor.get("type"),
            factor.get("benchmark"),
        )
        value = max(_number(holding.get("cost_basis")), 0.0)
        weight_pct = round(value / total * 100, 1) if total > 0 else 0.0
        for tag in tags:
            tag_weights[tag] = round(tag_weights.get(tag, 0.0) + weight_pct, 1)
        holding_tags.append(
            {
                "holding_ref": f"holding_{index + 1}",
                "tags": sorted(tags),
                "weight_pct": weight_pct,
            }
        )
    return {"tag_weights": tag_weights, "holding_tags": holding_tags}


def _theme_evidence(theme):
    narratives = [item for item in theme.get("narratives", []) if isinstance(item, dict)]
    if not narratives:
        return {
            "evidence_score": 0,
            "verification_status": "无叙事输入",
            "top_claim": "",
            "source_note": "没有可核验叙事",
        }
    scored = []
    for item in narratives:
        level = str(item.get("evidence_level") or "unverified")
        scored.append(
            {
                "claim": str(item.get("claim") or ""),
                "evidence_level": level,
                "score": EVIDENCE_SCORES.get(level, EVIDENCE_SCORES["unverified"]),
                "source_note": str(item.get("source_note") or ""),
            }
        )
    best = max(scored, key=lambda item: item["score"])
    if best["score"] >= 90:
        status = "高可信事实"
    elif best["score"] >= 80:
        status = "公司披露或财报证据"
    elif best["score"] >= 65:
        status = "有媒体或产业数据支持"
    elif best["score"] >= 35:
        status = "弱证据，需复核"
    else:
        status = "雷达观察，未核验"
    return {
        "evidence_score": best["score"],
        "verification_status": status,
        "top_claim": best["claim"],
        "source_note": best["source_note"],
        "evidence_level": best["evidence_level"],
    }


def _portfolio_relation(theme_tags, tag_weights):
    overlap_tags = sorted(set(theme_tags) & set(tag_weights))
    overlap_pct = round(sum(tag_weights.get(tag, 0.0) for tag in overlap_tags), 1)
    if {"defensive", "financials", "healthcare", "quality"} & set(theme_tags):
        return {
            "relation": "分散候选",
            "overlap_tags": overlap_tags,
            "overlap_pct": min(overlap_pct, 100.0),
            "fit_note": "与当前科技成长主线不同，可作为分散候选，但仍需估值和流动性确认。",
        }
    if not overlap_tags:
        return {
            "relation": "新增方向",
            "overlap_tags": [],
            "overlap_pct": 0.0,
            "fit_note": "与当前组合标签重叠较低，但仍需单独核验基本面和交易可得性。",
        }
    if {"power", "nuclear", "industrial", "automation", "robotics"} & set(theme_tags):
        relation = "相邻扩展"
        note = "与 AI 主题相关，但风险来源不完全等同；可作为扩展候选，不能直接当作防守。"
    else:
        relation = "增厚原有风险"
        note = "会增加当前已有的科技成长或 AI 暴露，不应被误认为分散。"
    return {
        "relation": relation,
        "overlap_tags": overlap_tags,
        "overlap_pct": min(overlap_pct, 100.0),
        "fit_note": note,
    }


def _action_for(theme, evidence, relation):
    status = evidence["verification_status"]
    relation_name = relation["relation"]
    if status == "雷达观察，未核验":
        return "只观察：先等待官方公告、财报、主流媒体或价格/成交量确认。"
    if relation_name == "增厚原有风险":
        return "小仓或暂缓：若要买，只能作为趋势仓，并设置仓位上限和复核条件。"
    if relation_name == "分散候选":
        return "可进入候选池：先比较估值、流动性和与现有组合的相关性。"
    return "研究候选：补齐事实核验后再讨论仓位。"


def build_market_radar(portfolio, radar_config=None):
    radar_config = radar_config or load_market_radar()
    exposure = portfolio_exposure_tags(portfolio)
    tag_weights = exposure["tag_weights"]
    rows = []
    for theme in radar_config.get("themes", []):
        theme_tags = [str(tag) for tag in theme.get("exposure_tags", [])]
        evidence = _theme_evidence(theme)
        relation = _portfolio_relation(theme_tags, tag_weights)
        score = round(
            evidence["evidence_score"] * 0.45
            + min(relation["overlap_pct"], 100.0) * 0.15
            + (20 if relation["relation"] == "分散候选" else 0),
            1,
        )
        row = {
            "theme_id": str(theme.get("theme_id") or ""),
            "name": str(theme.get("name") or ""),
            "thesis": str(theme.get("thesis") or ""),
            "theme_tags": theme_tags,
            "instruments": list(theme.get("instruments") or []),
            "execution_note": str(theme.get("execution_note") or ""),
            **evidence,
            **relation,
            "radar_score": score,
        }
        row["suggested_action"] = _action_for(theme, evidence, relation)
        rows.append(row)
    rows.sort(key=lambda item: (-item["radar_score"], item["name"]))
    return {
        "mode": "market_radar",
        "portfolio_exposure": exposure,
        "theme_count": len(rows),
        "themes": rows,
        "boundary": {
            "news": "radar matrix only unless external evidence is supplied",
            "decision": "decision support only",
            "execution_allowed": False,
        },
    }


def _instrument_text(instruments, limit=4):
    items = []
    for item in instruments[:limit]:
        code = str(item.get("code") or "")
        name = str(item.get("name") or "")
        access = str(item.get("access") or "")
        items.append(f"{code}（{name}，{access}）")
    return "；".join(items) if items else "无"


def format_market_radar(radar, limit=8):
    lines = ["# Market Narrative Radar", ""]
    lines.append("## Portfolio Exposure Tags")
    tag_weights = radar.get("portfolio_exposure", {}).get("tag_weights", {})
    if tag_weights:
        for tag, weight in sorted(tag_weights.items()):
            lines.append(f"- {tag}: {weight}%")
    else:
        lines.append("- none")
    lines.append("")
    lines.append("## Themes")
    for item in (radar.get("themes") or [])[:limit]:
        lines.append(f"- {item['name']} | {item['verification_status']} | {item['relation']} | score={item['radar_score']}")
        lines.append(f"  claim={item['top_claim']}")
        lines.append(f"  instruments={_instrument_text(item.get('instruments') or [])}")
        lines.append(f"  action={item['suggested_action']}")
        lines.append(f"  fit={item['fit_note']}")
    lines.append("")
    lines.append("## Boundary")
    lines.append("- radar matrix only unless external evidence is supplied")
    lines.append("- decision support only")
    lines.append("- execution_allowed=false")
    return "\n".join(lines)


def main():
    portfolio, _, _, _ = load_portfolio()
    print(format_market_radar(build_market_radar(portfolio)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
