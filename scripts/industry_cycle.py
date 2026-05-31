#!/usr/bin/env python3
"""
industry_cycle.py - AI产业周期追踪器
分块构建：块1=可量化赛道（AkShare数据驱动）
"""

import akshare as ak
import pandas as pd
import numpy as np
import json
import sys
import os
from datetime import datetime, timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
from common.config_loader import get_tavily_api_key, news_enabled

# ============================================================
# 块1A: 宏观层 — 利率/流动性 + 北向资金
# ============================================================

def get_macro_liquidity():
    """利率/流动性：纳指走势 + USD/CNY汇率"""
    results = {}
    
    # 1. 纳指综合指数（30日趋势）
    try:
        df = ak.index_us_stock_sina(symbol=".IXIC")
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').tail(30)
        latest = float(df.iloc[-1]['close'])
        month_ago = float(df.iloc[0]['close'])
        chg = (latest / month_ago - 1) * 100
        
        # 52周高低
        df_year = ak.index_us_stock_sina(symbol=".IXIC")
        df_year['date'] = pd.to_datetime(df_year['date'])
        df_year = df_year.sort_values('date').tail(252)
        high_52w = float(df_year['close'].max())
        low_52w = float(df_year['close'].min())
        pct_from_high = (latest / high_52w - 1) * 100
        
        results['nasdaq'] = {
            'price': round(latest, 2),
            '30d_change': round(chg, 2),
            '52w_high': round(high_52w, 2),
            'pct_from_52w_high': round(pct_from_high, 2),
            'signal': '🔴过热' if pct_from_high > -3 else ('🟡正常' if pct_from_high > -10 else '🟢低迷')
        }
    except Exception as e:
        results['nasdaq'] = {'error': str(e)}
    
    # 2. USD/CNY汇率
    try:
        df_fx = ak.fx_spot_quote()
        usdcny = df_fx[df_fx['名称'].str.contains('美元兑人民币')]
        if len(usdcny) > 0:
            rate = float(usdcny.iloc[0]['最新价'])
            results['usdcny'] = {
                'rate': rate,
                'trend': '↑美元走强' if rate > 7.2 else ('→震荡' if rate > 6.8 else '↓美元走弱'),
                'signal': '🟡中性'
            }
    except Exception as e:
        results['usdcny'] = {'error': str(e)}
    
    return results


def get_north_bound():
    """北向资金：净流入趋势"""
    results = {}
    
    try:
        df = ak.stock_hsgt_fund_flow_summary_em()
        if df is not None and len(df) > 0:
            # 取最近有数据的记录
            latest = df.iloc[-1]
            results['latest'] = {
                'date': str(latest.get('日期', '')),
                'north_net_flow': _safe_float(latest.get('北向资金净流入(万元)')),
                'sh_net_flow': _safe_float(latest.get('沪股通净流入(万元)')),
                'sz_net_flow': _safe_float(latest.get('沪股通净流入(万元)')),
            }
            
            # 近5日趋势
            recent = df.tail(5)
            net_flows = [_safe_float(r.get('北向资金净流入(万元)', 0)) for _, r in recent.iterrows()]
            avg_flow = np.mean([x for x in net_flows if x is not None]) if net_flows else 0
            
            results['5d_avg'] = round(avg_flow, 0)
            results['5d_trend'] = '净流入↑' if avg_flow > 0 else '净流出↓'
            results['signal'] = '🔴过热' if avg_flow > 100000 else ('🟡正常' if avg_flow > -100000 else '🟢低迷')
    except Exception as e:
        results['error'] = str(e)
    
    return results


# ============================================================
# 块1B: 半导体制造 — 行业资金流
# ============================================================

def get_semiconductor_flow():
    """半导体制造：行业资金流+板块涨跌"""
    results = {}
    
    # 关键词匹配半导体相关行业
    semi_keywords = ['半导体', '芯片', '集成电路', '电子元件', '光学光电']
    
    try:
        # 行业资金流
        df = ak.stock_fund_flow_industry()
        if df is not None and len(df) > 0:
            # 筛选半导体相关
            semi_rows = df[df['行业'].str.contains('|'.join(semi_keywords), na=False)]
            if len(semi_rows) > 0:
                top = semi_rows.head(3)
                sectors = []
                for _, row in top.iterrows():
                    sectors.append({
                        'name': row['行业'],
                        'net_flow': _safe_float(row.get('净额', 0)),
                        'pct': _safe_float(row.get('行业-涨跌幅', 0)),
                    })
                results['top_sectors'] = sectors
                
                total_net = sum(s['net_flow'] for s in sectors if s['net_flow'] is not None)
                results['total_net_flow'] = round(total_net, 2)  # 亿元
                results['signal'] = '🔴过热' if total_net > 50 else ('🟡正常' if total_net > -20 else '🟢低迷')
    except Exception as e:
        results['error'] = str(e)
    
    # 备用：概念资金流
    try:
        df_concept = ak.stock_fund_flow_concept()
        if df_concept is not None and len(df_concept) > 0:
            concept_keywords = ['芯片', '半导体', 'GPU', '光刻', 'HBM', '存储']
            concept_rows = df_concept[df_concept['概念'].str.contains('|'.join(concept_keywords), na=False)]
            if len(concept_rows) > 0:
                top_concepts = []
                for _, row in concept_rows.head(3).iterrows():
                    top_concepts.append({
                        'name': row['概念'],
                        'net_flow': _safe_float(row.get('主力净流入-净额', 0)),
                        'pct': _safe_float(row.get('涨跌幅', 0)),
                    })
                results['top_concepts'] = top_concepts
    except Exception as e:
        pass  # 概念资金流是补充数据，失败不影响
    
    return results


# ============================================================
# 块1C: 硬件层 — AI芯片/存储/光通信（通用板块筛选）
# ============================================================

def get_sector_signal(sector_name, keywords, fallback_concept_keywords=None):
    """通用板块信号函数"""
    results = {'sector': sector_name}
    
    try:
        df = ak.stock_fund_flow_industry()
        if df is not None and len(df) > 0:
            matched = df[df['行业'].str.contains('|'.join(keywords), na=False)]
            if len(matched) > 0:
                row = matched.iloc[0]
                results['industry'] = {
                    'name': row['行业'],
                    'net_flow': _safe_float(row.get('净额', 0)),
                    'pct': _safe_float(row.get('行业-涨跌幅', 0)),
                }
                net = results['industry']['net_flow']
                if net is not None:
                    results['signal'] = '🔴过热' if net > 30 else ('🟡正常' if net > -10 else '🟢低迷')
    except Exception as e:
        results['industry_error'] = str(e)
    
    # 概念资金流补充
    if fallback_concept_keywords:
        try:
            df_c = ak.stock_fund_flow_concept()
            if df_c is not None and len(df_c) > 0:
                matched_c = df_c[df_c['概念'].str.contains('|'.join(fallback_concept_keywords), na=False)]
                if len(matched_c) > 0:
                    row = matched_c.iloc[0]
                    results['concept'] = {
                        'name': row['概念'],
                        'net_flow': _safe_float(row.get('净额', 0)),
                        'pct': _safe_float(row.get('概念-涨跌幅', 0)),
                    }
        except:
            pass
    
    return results


def get_ai_chip_sector():
    """AI芯片/GPU板块信号"""
    return get_sector_signal(
        'AI芯片/GPU',
        keywords=['半导体', '芯片'],
        fallback_concept_keywords=['GPU', 'AI芯片', '英伟达', '算力']
    )


def get_memory_sector():
    """存储芯片/HBM板块信号"""
    return get_sector_signal(
        '存储芯片/HBM',
        keywords=['半导体', '电子元件'],
        fallback_concept_keywords=['存储芯片', 'HBM', 'DRAM', '内存']
    )


def get_optical_sector():
    """光通信/CPO板块信号"""
    return get_sector_signal(
        '光通信/CPO',
        keywords=['光学光电', '通信'],
        fallback_concept_keywords=['光模块', 'CPO', '光通信', '硅光']
    )


# ============================================================
# 块2: 定性赛道（Tavily新闻驱动）
# ============================================================

# 9个定性赛道的搜索配置
QUALITATIVE_SECTORS = [
    # 单元A: Layer 0 能源层
    {
        "id": "power_supply",
        "name": "电力供应",
        "layer": "Layer 0",
        "queries": [
            "AI data center electricity demand 2026 power grid",
            "数据中心 电力需求 用电缺口 电网",
        ]
    },
    {
        "id": "liquid_cooling",
        "name": "液冷散热",
        "layer": "Layer 0",
        "queries": [
            "data center liquid cooling AI thermal management 2026",
            "液冷 数据中心 散热 PUE 技术",
        ]
    },
    # 单元B: Layer 2 平台层
    {
        "id": "ai_model",
        "name": "AI模型层",
        "layer": "Layer 2",
        "queries": [
            "AI model training inference cost 2026 LLM pricing war",
            "大模型 训练成本 推理 开源闭源 价格战 2026",
        ]
    },
    {
        "id": "cloud_iaas",
        "name": "云计算/IaaS",
        "layer": "Layer 2",
        "queries": [
            "cloud capex AI infrastructure spending 2026 hyperscaler",
            "云计算 资本开支 数据中心 超大规模 产能利用率",
        ]
    },
    {
        "id": "edge_ai",
        "name": "边缘AI/端侧",
        "layer": "Layer 2",
        "queries": [
            "edge AI chip on-device AI PC smartphone 2026",
            "端侧AI 芯片 AI手机 AIPC 边缘计算",
        ]
    },
    # 单元C: Layer 3 应用层
    {
        "id": "ai_saas",
        "name": "AI应用层/SaaS",
        "layer": "Layer 3",
        "queries": [
            "AI SaaS enterprise adoption revenue 2026 monetization gap",
            "AI应用 企业付费 SaaS收入 变现 商业化",
        ]
    },
    {
        "id": "embodied_ai",
        "name": "具身智能/机器人",
        "layer": "Layer 3",
        "queries": [
            "embodied AI humanoid robot 2026 market",
            "具身智能 人形机器人 工业机器人 2026",
        ]
    },
    {
        "id": "autonomous_driving",
        "name": "自动驾驶",
        "layer": "Layer 3",
        "queries": [
            "autonomous driving L4 robotaxi 2026 commercial",
            "自动驾驶 L4 Robotaxi 商业化 监管",
        ]
    },
    {
        "id": "critical_minerals",
        "name": "关键矿物/材料",
        "layer": "Layer 1",
        "queries": [
            "critical minerals AI chip supply chain lithium copper rare earth 2026",
            "关键矿物 锂 铜 稀土 供应链 AI芯片 短缺",
        ]
    },
]


def _tavily_search(query, days=7, max_results=3):
    """复用Tavily搜索"""
    if not news_enabled():
        return []
    api_key = get_tavily_api_key()
    import requests as req
    url = "https://api.tavily.com/search"
    payload = {
        "api_key": api_key,
        "query": query,
        "search_depth": "basic",
        "max_results": max_results,
        "topic": "news",
        "days": days,
    }
    try:
        resp = req.post(url, json=payload, timeout=15)
        resp.raise_for_status()
        return resp.json().get("results", [])
    except Exception:
        return []


def _classify_news_signal(title, content):
    """新闻信号分级（复用industry_intel逻辑）"""
    text = (title + " " + content).lower()
    red_kw = ["暴跌", "崩盘", "危机", "制裁", "短缺", "critical", "shortage", "crisis", "ban"]
    yellow_kw = ["调整", "放缓", "压力", "分化", "caution", "slowdown", "mixed", "concern"]
    green_kw = ["突破", "新高", "增长", "加速", "surge", "boom", "record", "breakthrough"]

    r = sum(1 for kw in red_kw if kw in text)
    y = sum(1 for kw in yellow_kw if kw in text)
    g = sum(1 for kw in green_kw if kw in text)

    if r >= 1:
        return "🔴", "需关注"
    elif g >= 1 and y == 0:
        return "🟢", "利好"
    elif y >= 1:
        return "🟡", "变化"
    else:
        return "⚪", "参考"


def get_qualitative_sector(sector_config):
    """采集单个定性赛道的新闻信号"""
    result = {
        "id": sector_config["id"],
        "name": sector_config["name"],
        "layer": sector_config["layer"],
        "headlines": [],
        "dominant_signal": "⚪",
        "signal_label": "参考",
    }

    signal_counts = {"🔴": 0, "🟡": 0, "🟢": 0, "⚪": 0}
    seen = set()

    for q in sector_config["queries"]:
        articles = _tavily_search(q, days=7, max_results=3)
        for a in articles:
            title = a.get("title", "").strip()
            if not title or title in seen:
                continue
            seen.add(title)
            content = a.get("content", "")[:200]
            sig, label = _classify_news_signal(title, content)
            signal_counts[sig] += 1
            result["headlines"].append({
                "title": title[:60],
                "signal": sig,
                "label": label,
            })

    # 取主导信号
    if signal_counts["🔴"] > 0:
        result["dominant_signal"] = "🔴"
        result["signal_label"] = "需关注"
    elif signal_counts["🟢"] > signal_counts["🟡"]:
        result["dominant_signal"] = "🟢"
        result["signal_label"] = "利好"
    elif signal_counts["🟡"] > 0:
        result["dominant_signal"] = "🟡"
        result["signal_label"] = "变化"
    else:
        result["dominant_signal"] = "⚪"
        result["signal_label"] = "参考"

    return result


def generate_block2_report():
    """生成定性赛道报告"""
    lines = []
    lines.append("=" * 50)
    lines.append("📰 AI产业周期追踪 — 定性赛道（新闻驱动）")
    lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("=" * 50)

    current_layer = ""
    for sector in QUALITATIVE_SECTORS:
        if sector["layer"] != current_layer:
            current_layer = sector["layer"]
            lines.append(f"\n## {current_layer}")

        data = get_qualitative_sector(sector)
        lines.append(f"  [{data['name']}] {data['dominant_signal']}{data['signal_label']}")
        for h in data["headlines"][:3]:  # 每个赛道最多显示3条
            lines.append(f"    {h['signal']} {h['title']}")

    return "\n".join(lines)


# ============================================================
# 工具函数
# ============================================================

def _safe_float(val):
    """安全转换为float"""
    if val is None or val == '' or val == '-' or val == 'nan':
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


# ============================================================
# 主函数：生成块1报告
# ============================================================

def generate_block1_report():
    """生成可量化赛道的产业周期报告"""
    lines = []
    lines.append("=" * 50)
    lines.append("📊 AI产业周期追踪 — 可量化赛道")
    lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("=" * 50)
    
    # 宏观层
    lines.append("\n## 🔵 Layer 4: 宏观/流动性")
    
    macro = get_macro_liquidity()
    if 'nasdaq' in macro and 'error' not in macro['nasdaq']:
        n = macro['nasdaq']
        lines.append(f"  纳指: {n['price']} | 30日{n['30d_change']:+.1f}% | 距52周高{n['pct_from_52w_high']:+.1f}% {n['signal']}")
    if 'usdcny' in macro and 'error' not in macro['usdcny']:
        fx = macro['usdcny']
        lines.append(f"  USD/CNY: {fx['rate']} | {fx['trend']} {fx['signal']}")
    
    north = get_north_bound()
    if '5d_avg' in north:
        lines.append(f"  北向资金5日均值: {north['5d_avg']/10000:.1f}亿 | {north['5d_trend']} {north['signal']}")
    
    # 半导体制造
    lines.append("\n## 🟠 Layer 1: 基础设施硬件")
    
    semi = get_semiconductor_flow()
    if 'top_sectors' in semi:
        lines.append("  [半导体制造]")
        for s in semi['top_sectors']:
            flow_str = f"{s['net_flow']/10000:.1f}亿" if s['net_flow'] else 'N/A'
            pct_str = f"{s['pct']:+.2f}%" if s['pct'] else 'N/A'
            lines.append(f"    {s['name']}: 净流入{flow_str} | 涨跌{pct_str}")
        if 'signal' in semi:
            lines.append(f"    信号: {semi['signal']}")
    
    # AI芯片/存储/光通信
    for func, label in [(get_ai_chip_sector, 'AI芯片/GPU'), (get_memory_sector, '存储芯片/HBM'), (get_optical_sector, '光通信/CPO')]:
        data = func()
        lines.append(f"  [{label}]")
        if 'industry' in data:
            ind = data['industry']
            flow_str = f"{ind['net_flow']/10000:.1f}亿" if ind['net_flow'] else 'N/A'
            pct_str = f"{ind['pct']:+.2f}%" if ind['pct'] else 'N/A'
            lines.append(f"    行业: {ind['name']} | 净流入{flow_str} | 涨跌{pct_str}")
        if 'concept' in data:
            con = data['concept']
            flow_str = f"{con['net_flow']/10000:.1f}亿" if con['net_flow'] else 'N/A'
            pct_str = f"{con['pct']:+.2f}%" if con['pct'] else 'N/A'
            lines.append(f"    概念: {con['name']} | 净流入{flow_str} | 涨跌{pct_str}")
        if 'signal' in data:
            lines.append(f"    信号: {data['signal']}")
    
    return "\n".join(lines)


# ============================================================
# 块3: 整合输出 — 15赛道完整产业周期报告
# ============================================================

def generate_industry_cycle_report():
    """生成完整的AI产业周期报告（块1+块2合并）"""
    lines = []
    lines.append("🗺️ AI产业周期全景图")
    lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")

    # ---- 块1: 可量化赛道 ----
    lines.append("━━ 📊 量化信号 ━━")

    # 宏观
    lines.append("\n【宏观/流动性】")
    macro = get_macro_liquidity()
    if 'nasdaq' in macro and 'error' not in macro['nasdaq']:
        n = macro['nasdaq']
        lines.append(f"  纳指 {n['price']} | 30日{n['30d_change']:+.1f}% | 52周高位{n['pct_from_52w_high']:+.1f}% {n['signal']}")
    if 'usdcny' in macro and 'error' not in macro['usdcny']:
        fx = macro['usdcny']
        lines.append(f"  USD/CNY {fx['rate']} | {fx['trend']} {fx['signal']}")
    north = get_north_bound()
    if '5d_avg' in north:
        lines.append(f"  北向5日均值 {north['5d_avg']/10000:.1f}亿 | {north['5d_trend']} {north['signal']}")

    # 硬件层
    lines.append("\n【基础设施硬件】")
    semi = get_semiconductor_flow()
    if 'top_sectors' in semi:
        for s in semi['top_sectors']:
            flow = f"{s['net_flow']:.1f}亿" if s['net_flow'] else 'N/A'
            pct = f"{s['pct']:+.2f}%" if s['pct'] else 'N/A'
            lines.append(f"  {s['name']}: {pct} | 净流入{flow}")

    for func, label in [(get_ai_chip_sector, 'AI芯片/GPU'), (get_memory_sector, '存储芯片/HBM'), (get_optical_sector, '光通信/CPO')]:
        data = func()
        sig = data.get('signal', '⚪')
        ind = data.get('industry', {})
        pct = f"{ind['pct']:+.2f}%" if ind.get('pct') else 'N/A'
        lines.append(f"  {label}: {pct} {sig}")

    # ---- 块2: 定性赛道 + 信号汇总 ----
    # 收集所有信号（复用已采集的定性数据，避免重复API调用）
    all_qual_data = []
    for sector in QUALITATIVE_SECTORS:
        all_qual_data.append(get_qualitative_sector(sector))

    # 重新生成新闻信号部分（用已采集数据）
    lines.append("\n━━ 📰 新闻信号 ━━")
    layer_order = ["Layer 0", "Layer 2", "Layer 3", "Layer 1"]
    layer_names = {"Layer 0": "能源", "Layer 1": "材料", "Layer 2": "平台", "Layer 3": "应用"}

    for layer in layer_order:
        sectors_in_layer = [(s, d) for s, d in zip(QUALITATIVE_SECTORS, all_qual_data) if s["layer"] == layer]
        if not sectors_in_layer:
            continue
        lines.append(f"\n【{layer_names.get(layer, layer)}】")
        for sector, data in sectors_in_layer:
            lines.append(f"  {data['dominant_signal']} {data['name']}: {data['signal_label']}")
            for h in data["headlines"][:2]:
                lines.append(f"    {h['signal']} {h['title']}")

    # 汇总
    reds, yellows, greens = [], [], []
    if 'nasdaq' in macro and 'error' not in macro.get('nasdaq', {}):
        if '🔴' in macro['nasdaq'].get('signal', ''):
            reds.append('纳指过热')
    for data in all_qual_data:
        if data['dominant_signal'] == '🔴':
            reds.append(data['name'])
        elif data['dominant_signal'] == '🟡':
            yellows.append(data['name'])
        elif data['dominant_signal'] == '🟢':
            greens.append(data['name'])

    lines.append("\n━━ 📋 信号汇总 ━━")
    lines.append(f"  🔴需关注: {', '.join(reds) if reds else '无'}")
    lines.append(f"  🟡变化中: {', '.join(yellows) if yellows else '无'}")
    lines.append(f"  🟢利好: {', '.join(greens) if greens else '无'}")

    return "\n".join(lines)


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == '--full':
            print(generate_industry_cycle_report())
        elif arg == '--quant':
            print(generate_block1_report())
        else:
            print(f"Usage: {sys.argv[0]} [--quant|--full]")
    else:
        print(generate_block1_report())
