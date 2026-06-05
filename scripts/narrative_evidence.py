#!/usr/bin/env python3
"""Ingest external market narratives into a verifiable thesis ledger.

Inputs are user-provided articles, links, pasted summaries, filings, or notes.
The script classifies source reliability, maps each item to market radar themes,
and can append a sanitized thesis-change record under the private decision
track directory.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from common.config_loader import get_decision_track_dir, get_repo_root
from market_radar import EVIDENCE_SCORES, load_market_radar


ROOT = get_repo_root()
DEFAULT_EVIDENCE_PATH = ROOT / "data/examples/market_evidence.example.json"

SOURCE_TYPE_ALIASES = {
    "official": "official",
    "company": "official",
    "filing": "filing",
    "sec": "filing",
    "earnings": "earnings",
    "call": "earnings",
    "major_media": "major_media",
    "media": "major_media",
    "industry_data": "industry_data",
    "social": "social_media",
    "social_media": "social_media",
    "blog": "blogger",
    "blogger": "blogger",
    "rumor": "rumor",
    "unverified": "unverified",
}

MAJOR_MEDIA_DOMAINS = {
    "reuters.com",
    "bloomberg.com",
    "wsj.com",
    "ft.com",
    "cnbc.com",
    "marketwatch.com",
}

SOCIAL_DOMAINS = {
    "x.com",
    "twitter.com",
    "reddit.com",
    "weibo.com",
    "xueqiu.com",
}

FILING_DOMAINS = {
    "sec.gov",
    "nasdaq.com",
    "nyse.com",
    "hkexnews.hk",
    "sse.com.cn",
    "szse.cn",
}

INJECTION_PATTERNS = [
    "ignore previous instructions",
    "developer message",
    "system prompt",
    "reveal system prompt",
    "泄露系统提示",
    "忽略之前的指令",
]

GENERIC_THEME_TERMS = {
    "ai",
    "growth",
    "us",
    "cn",
    "fund",
    "etf",
    "theme",
    "radar",
    "only",
    "market",
    "ticker",
}


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


def _read_json(path):
    with Path(path).open(encoding="utf-8") as f:
        return json.load(f)


def _domain(url):
    host = urlparse(str(url or "")).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def classify_evidence_level(item):
    explicit = str(item.get("source_type") or item.get("evidence_level") or "").lower().strip()
    if explicit in SOURCE_TYPE_ALIASES:
        return SOURCE_TYPE_ALIASES[explicit]
    domain = _domain(item.get("url"))
    if any(domain == candidate or domain.endswith("." + candidate) for candidate in FILING_DOMAINS):
        return "filing"
    if any(domain == candidate or domain.endswith("." + candidate) for candidate in MAJOR_MEDIA_DOMAINS):
        return "major_media"
    if any(domain == candidate or domain.endswith("." + candidate) for candidate in SOCIAL_DOMAINS):
        return "social_media"
    if "investor" in domain or "ir." in domain:
        return "official"
    return "unverified"


def verification_status(evidence_level):
    score = EVIDENCE_SCORES.get(evidence_level, EVIDENCE_SCORES["unverified"])
    if score >= 90:
        return "高可信事实"
    if score >= 80:
        return "公司披露或财报证据"
    if score >= 65:
        return "主流媒体或产业数据支持"
    if score >= 35:
        return "弱证据，需交叉验证"
    if score >= 15:
        return "市场传闻"
    return "不可验证"


def _term_tokens(value):
    text = str(value or "").lower()
    tokens = re.findall(r"[a-z0-9.]+|[\u4e00-\u9fff]+", text)
    return [
        token
        for token in tokens
        if token not in GENERIC_THEME_TERMS and (len(token) >= 3 or "." in token)
    ]


def _theme_terms(theme):
    terms = []
    terms.extend(_term_tokens(theme.get("name")))
    terms.extend(_term_tokens(theme.get("theme_id")))
    terms.extend(_term_tokens(theme.get("thesis")))
    for tag in theme.get("exposure_tags") or []:
        terms.extend(_term_tokens(tag))
    for instrument in theme.get("instruments") or []:
        code = str(instrument.get("code") or "").lower().strip()
        if len(code) >= 2:
            terms.append(code)
        terms.extend(_term_tokens(instrument.get("name")))
    return sorted(set(terms))


def _matches_theme(text, theme):
    lowered = text.lower()
    hits = []
    text_tokens = set(_term_tokens(lowered))
    for term in _theme_terms(theme):
        if re.fullmatch(r"[a-z0-9.]+", term):
            if term in text_tokens:
                hits.append(term)
        elif term and term in lowered:
            hits.append(term)
    return sorted(set(hits))


def load_evidence_items(path=None):
    payload = _read_json(path or DEFAULT_EVIDENCE_PATH)
    if isinstance(payload, list):
        return payload
    return list(payload.get("items") or [])


def build_narrative_evidence_review(evidence_items, radar_config=None):
    radar_config = radar_config or load_market_radar()
    themes = [item for item in radar_config.get("themes", []) if isinstance(item, dict)]
    reviewed = []
    theme_updates = {}
    for index, item in enumerate(evidence_items):
        title = sanitize_external_text(item.get("title", ""), max_length=180)
        content = sanitize_external_text(item.get("content", ""), max_length=500)
        claim = sanitize_external_text(item.get("claim") or title or content, max_length=240)
        text = " ".join([title, content, claim])
        evidence_level = classify_evidence_level(item)
        matched = []
        instruments = []
        for theme in themes:
            hits = _matches_theme(text, theme)
            if not hits:
                continue
            theme_id = str(theme.get("theme_id") or "")
            matched.append(
                {
                    "theme_id": theme_id,
                    "name": str(theme.get("name") or ""),
                    "matched_terms": hits[:6],
                }
            )
            for instrument in theme.get("instruments") or []:
                if instrument not in instruments:
                    instruments.append(instrument)
            update = {
                "claim": claim,
                "evidence_level": evidence_level,
                "source_note": str(item.get("url") or item.get("source") or ""),
            }
            theme_updates.setdefault(theme_id, []).append(update)
        reviewed.append(
            {
                "item_ref": f"evidence_{index + 1}",
                "title": title,
                "claim": claim,
                "url": str(item.get("url") or ""),
                "published_at": str(item.get("published_at") or ""),
                "evidence_level": evidence_level,
                "verification_status": verification_status(evidence_level),
                "evidence_score": EVIDENCE_SCORES.get(evidence_level, 0),
                "matched_themes": matched,
                "instruments": instruments,
                "decision_use": _decision_use(evidence_level, matched),
            }
        )
    return {
        "mode": "narrative_evidence_review",
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "evidence_count": len(reviewed),
        "items": reviewed,
        "theme_updates": theme_updates,
        "boundary": {
            "external_text": "untrusted input",
            "decision": "evidence for review, not execution",
            "execution_allowed": False,
        },
    }


def _decision_use(evidence_level, matched):
    if not matched:
        return "暂不纳入雷达：未匹配到已定义主题。"
    score = EVIDENCE_SCORES.get(evidence_level, 0)
    if score >= 80:
        return "可提高相关主题置信度，但仍需结合价格、估值和组合暴露。"
    if score >= 65:
        return "可作为主题观察证据，需要至少一个独立来源交叉确认。"
    if score >= 35:
        return "只作为弱信号，不能单独触发买入。"
    return "只记录为传闻或不可验证信息，不进入买入建议。"


def apply_evidence_to_radar_config(radar_config, evidence_review):
    updated = json.loads(json.dumps(radar_config, ensure_ascii=False))
    updates = evidence_review.get("theme_updates") or {}
    for theme in updated.get("themes", []) or []:
        theme_id = str(theme.get("theme_id") or "")
        additions = updates.get(theme_id) or []
        if additions:
            theme.setdefault("narratives", [])
            theme["narratives"].extend(additions)
    return updated


def _instrument_text(instruments, limit=4):
    output = []
    for item in instruments[:limit]:
        output.append(
            f"{item.get('code')}（{item.get('name')}，{item.get('access', '交易方式待确认')}）"
        )
    return "；".join(output) if output else "无"


def format_narrative_evidence_review(review):
    lines = ["# Narrative Evidence Review", ""]
    lines.append("## Evidence Items")
    if not review.get("items"):
        lines.append("- none")
    for item in review.get("items") or []:
        themes = "、".join(theme["name"] for theme in item.get("matched_themes", [])) or "未匹配"
        lines.append(
            f"- {item['item_ref']} | {item['verification_status']} | themes={themes}"
        )
        lines.append(f"  claim={item['claim']}")
        lines.append(f"  instruments={_instrument_text(item.get('instruments') or [])}")
        lines.append(f"  decision_use={item['decision_use']}")
        if item.get("url"):
            lines.append(f"  source={item['url']}")
    lines.append("")
    lines.append("## Thesis Change")
    matched = [item for item in review.get("items", []) if item.get("matched_themes")]
    if matched:
        lines.append("- 今日新增证据已映射到市场雷达主题；高可信证据可提高主题置信度。")
        lines.append("- 低可信或传闻证据只进入观察，不触发买入建议。")
    else:
        lines.append("- 今日证据未匹配到现有主题矩阵，需要先扩充雷达主题或补充关键词。")
    lines.append("")
    lines.append("## Boundary")
    lines.append("- external text is untrusted input")
    lines.append("- evidence for review, not execution")
    lines.append("- execution_allowed=false")
    return "\n".join(lines)


def save_thesis_ledger(review, record_path=None):
    record_path = Path(record_path) if record_path else Path(get_decision_track_dir()) / "thesis_ledger.jsonl"
    record_path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "event": "thesis_evidence_reviewed",
        "created_at": review.get("created_at"),
        "evidence_count": review.get("evidence_count", 0),
        "matched_theme_ids": sorted(
            {
                theme.get("theme_id")
                for item in review.get("items", [])
                for theme in item.get("matched_themes", [])
                if theme.get("theme_id")
            }
        ),
        "verification_counts": _count_values(item.get("verification_status") for item in review.get("items", [])),
        "execution_allowed": False,
    }
    with record_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return {"record_path": str(record_path), "record": record}


def load_thesis_ledger(record_path=None, limit=5):
    record_path = Path(record_path) if record_path else Path(get_decision_track_dir()) / "thesis_ledger.jsonl"
    if not record_path.exists():
        return []
    records = []
    for line in record_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if item.get("event") == "thesis_evidence_reviewed":
            records.append(item)
    return records[-limit:]


def _count_values(values):
    counts = {}
    for value in values:
        key = str(value or "unknown")
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence_path", nargs="?", default=str(DEFAULT_EVIDENCE_PATH))
    parser.add_argument("--save", action="store_true", help="Append a sanitized thesis ledger record under data/private.")
    args = parser.parse_args(argv)
    review = build_narrative_evidence_review(load_evidence_items(args.evidence_path))
    print(format_narrative_evidence_review(review))
    if args.save:
        saved = save_thesis_ledger(review)
        print("")
        print("[ledger saved] " + saved["record_path"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
