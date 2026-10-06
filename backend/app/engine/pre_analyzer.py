"""
輕量預先分析引擎 (Lightweight Pre-analysis Engine)

快速掃描線路特徵 (匯流排協定、主控晶片平台、元件與網路規模)，避免阻塞重型佇列並產生規則推薦清單。
"""

import re
import logging
from typing import Dict, List, Any, Set
import networkx as nx

from backend.app.schemas.task import PreAnalysisSummary, RecommendedRule

logger = logging.getLogger("designshield.pre_analyzer")

# 已知晶片平台特徵關鍵字比對
PLATFORM_KEYWORDS = {
    "STM32": re.compile(r"STM32[A-Z0-9]+", re.IGNORECASE),
    "ESP32": re.compile(r"ESP32|ESP8266", re.IGNORECASE),
    "TI MSP": re.compile(r"MSP430", re.IGNORECASE),
    "NXP i.MX": re.compile(r"IMX\d+|MIMX", re.IGNORECASE),
    "Microchip SAM": re.compile(r"ATSAM[A-Z0-9]+", re.IGNORECASE),
    "Nordic nRF": re.compile(r"nRF5\d+", re.IGNORECASE),
    "TI Power/Type-C": re.compile(r"TPS\d+", re.IGNORECASE),
}


def analyze_schematic_features(G: nx.Graph) -> Dict[str, Any]:
    """
    分析圖譜特徵並回傳統計資訊與推薦規則
    
    Args:
        G: NetworkX 線路二分圖
        
    Returns:
        Dict: 包含 'summary' (PreAnalysisSummary) 與 'recommended_rules' (List[RecommendedRule])
    """
    detected_buses: Set[str] = set()
    detected_platforms: Set[str] = set()
    
    comp_count = 0
    net_count = 0
    has_capacitors = False
    has_connectors = False
    
    for _, node_data in G.nodes(data=True):
        node_type = node_data.get("type")
        if node_type == "component":
            comp_count += 1
            category = node_data.get("category", "")
            sub_category = node_data.get("sub_category", "")
            is_electrical = node_data.get("is_electrical", True)
            part_val = node_data.get("part_value", "")
            mfg_pn = node_data.get("mfg_pn", "")
            desc = node_data.get("description", "")
            full_text = f"{part_val} {mfg_pn} {desc}"
            
            if sub_category == "Capacitor" or category == "Capacitor":
                has_capacitors = True
            elif category == "Connector" or sub_category == "Connector":
                has_connectors = True
                
            # 偵測主控平台 (僅限電氣元件)
            if is_electrical:
                for platform, pattern in PLATFORM_KEYWORDS.items():
                    if pattern.search(full_text):
                        detected_platforms.add(platform)
                    
        elif node_type == "net":
            net_count += 1
            bus_type = node_data.get("bus_type")
            if bus_type:
                detected_buses.add(bus_type)
                
    summary = PreAnalysisSummary(
        buses=sorted(list(detected_buses)),
        platforms=sorted(list(detected_platforms)),
        component_count=comp_count,
        net_count=net_count
    )
    
    # 智慧規則推薦
    recommended_rules: List[RecommendedRule] = []
    
    # 1. 匯流排類別
    if "I2C" in detected_buses:
        recommended_rules.append(
            RecommendedRule(
                id="RULE-BUS-I2C-ADDR",
                name="I2C 匯流排地址唯一性檢查",
                category="Bus Integrity"
            )
        )
    if "SPI" in detected_buses or "SD" in "".join(detected_buses):
        recommended_rules.append(
            RecommendedRule(
                id="RULE-LLM-SD-MODE",
                name="MicroSD / SPI 介面模式合理性確認",
                category="Interface Mode"
            )
        )
        
    # 2. 電源類別
    if has_capacitors:
        recommended_rules.append(
            RecommendedRule(
                id="RULE-PWR-CAP-DERATING",
                name="電源濾波電容耐壓降額檢查",
                category="Power Domain"
            )
        )
        recommended_rules.append(
            RecommendedRule(
                id="RULE-PWR-DECOUPLING",
                name="晶片電源引腳去耦電容配置檢查",
                category="Power Domain"
            )
        )
        
    # 3. 連接器引腳類別
    if has_connectors:
        recommended_rules.append(
            RecommendedRule(
                id="RULE-CONN-PINOUT",
                name="連接器引腳訊號完整性與保護檢查",
                category="Pin Connection"
            )
        )
        
    # 若圖譜無特殊關鍵字，預設提供標準檢測規則
    if not recommended_rules:
        recommended_rules.append(
            RecommendedRule(
                id="RULE-BUS-I2C-ADDR",
                name="I2C 匯流排地址唯一性檢查",
                category="Bus Integrity"
            )
        )
        recommended_rules.append(
            RecommendedRule(
                id="RULE-PWR-CAP-DERATING",
                name="電源濾波電容耐壓降額檢查",
                category="Power Domain"
            )
        )
        
    return {
        "summary": summary,
        "recommended_rules": recommended_rules
    }
