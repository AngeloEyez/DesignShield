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
                category="Bus Integrity",
                severity="Error",
                domain="interfaces",
                tags=["I2C", "Bus Integrity"],
                reason="偵測到 I2C 匯流排連線",
                check_type="topology_check"
            )
        )
    if "SPI" in detected_buses or "SD" in "".join(detected_buses):
        recommended_rules.append(
            RecommendedRule(
                id="RULE-LLM-SD-MODE",
                name="MicroSD / SPI 介面模式合理性確認",
                category="Interface Mode",
                severity="Warning",
                domain="interfaces",
                tags=["SPI", "Interface Mode"],
                reason="偵測到 SPI/SD 介面",
                check_type="llm_agent"
            )
        )
        
    # 2. 電源類別
    if has_capacitors:
        recommended_rules.append(
            RecommendedRule(
                id="RULE-PWR-CAP-DERATING",
                name="電源濾波電容耐壓降額檢查",
                category="Power Domain",
                severity="Error",
                domain="power",
                tags=["Power Domain", "Derating"],
                reason="偵測到電容元件",
                check_type="topology_check"
            )
        )
        recommended_rules.append(
            RecommendedRule(
                id="RULE-PWR-DECOUPLING",
                name="晶片電源引腳去耦電容配置檢查",
                category="Power Domain",
                severity="Warning",
                domain="power",
                tags=["Power Domain", "Decoupling"],
                reason="偵測到晶片電源引腳",
                check_type="topology_check"
            )
        )
        
    # 3. 連接器引腳類別
    if has_connectors:
        recommended_rules.append(
            RecommendedRule(
                id="RULE-CONN-PINOUT",
                name="連接器引腳訊號完整性與保護檢查",
                category="Pin Connection",
                severity="Warning",
                domain="interfaces",
                tags=["Pin Connection"],
                reason="偵測到連接器元件",
                check_type="topology_check"
            )
        )

    # 4. Level 3 檔案式規則動態推薦
    try:
        from backend.app.services.pattern_service import PatternService
        l3_rules = PatternService.get_instance().get_level3_rules()
        for l3 in l3_rules:
            r_name = l3.get("name")
            tc = l3.get("trigger_conditions", {})
            gm = tc.get("graph_match", {}).get("attributes", {})
            matched = False
            reason = ""

            if gm.get("bus_type") == "I2C" and "I2C" in detected_buses:
                matched = True
                reason = "偵測到 I2C 匯流排連線"
            elif gm.get("is_power") and gm.get("is_ground"):
                for _, nd in G.nodes(data=True):
                    if nd.get("type") == "net" and nd.get("is_power") and nd.get("is_ground"):
                        matched = True
                        reason = "偵測到電源-接地衝突異常網路"
                        break
            elif gm.get("sub_category") == "Capacitor" and has_capacitors:
                matched = True
                reason = "偵測到電源電容元件"
            elif gm.get("category") == "IC" and comp_count > 0:
                matched = True
                reason = "偵測到電氣 IC 元件"

            if matched:
                ck_logics = l3.get("check_logic", [])
                first_type = ck_logics[0].get("type", "topology_check") if isinstance(ck_logics, list) and ck_logics else "topology_check"
                recommended_rules.append(
                    RecommendedRule(
                        id=r_name,
                        name=l3.get("description") or r_name,
                        category=l3.get("_domain", "DRC"),
                        severity=l3.get("severity", "Error"),
                        domain=l3.get("_domain", "DRC"),
                        tags=l3.get("tags", []),
                        reason=reason,
                        check_type=first_type
                    )
                )
    except Exception as e:
        logger.warning(f"Failed to match Level 3 recommendations: {e}")
        
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
