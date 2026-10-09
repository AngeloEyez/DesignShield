"""
輕量預先分析引擎 (Lightweight Pre-analysis Engine)

快速掃描線路特徵 (匯流排協定、主控晶片平台、元件與網路規模)，避免阻塞重型佇列並產生規則推薦清單。
"""

import re
import logging
from typing import Dict, List, Any, Set, Tuple, Optional
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


def _match_rule_trigger(G: nx.Graph, rule: Dict[str, Any], detected_buses: Set[str]) -> Tuple[bool, str]:
    """
    通用動態圖譜特徵比對器 (Generic Trigger Matcher)
    檢驗給定之 Level 3 規則 trigger_conditions 是否在圖譜中存在吻合節點。
    完全零業務硬編碼，所有判斷皆由 YAML 宣告之 graph_match attributes 驅動。
    """
    tc = rule.get("trigger_conditions", {})
    if not tc:
        return False, ""

    gm = tc.get("graph_match", {})
    attrs = gm.get("attributes", {})
    if not attrs:
        return False, ""

    # 若宣告包含特定匯流排協定需求 (快速快篩)
    if "bus_type" in attrs:
        req_bus = attrs["bus_type"]
        if req_bus in detected_buses:
            return True, f"圖譜中偵測到 {req_bus} 匯流排連線"
        return False, ""

    target_type = tc.get("target") or attrs.get("type")
    sample_identifier = None
    matching_count = 0

    for node, data in G.nodes(data=True):
        if target_type and data.get("type") != target_type:
            continue
        matched = True
        for k, v in attrs.items():
            if k == "type":
                continue
            if data.get(k) != v:
                matched = False
                break
        if matched:
            matching_count += 1
            if not sample_identifier:
                sample_identifier = data.get("ref_des") or data.get("net_name") or node
            break

    if matching_count > 0:
        desc = f" (如節點 {sample_identifier})" if sample_identifier else ""
        return True, f"圖譜中偵測到符合觸發條件之電氣目標{desc}"

    return False, ""


def analyze_schematic_features(G: nx.Graph) -> Dict[str, Any]:
    """
    分析圖譜特徵並回傳統計資訊與動態推薦規則 (完全由 YAML 規則庫自驅動)
    
    Args:
        G: NetworkX 線路二分圖
        
    Returns:
        Dict: 包含 'summary' (PreAnalysisSummary) 與 'recommended_rules' (List[RecommendedRule])
    """
    detected_buses: Set[str] = set()
    detected_platforms: Set[str] = set()
    
    comp_count = 0
    net_count = 0
    
    for _, node_data in G.nodes(data=True):
        node_type = node_data.get("type")
        if node_type == "component":
            comp_count += 1
            is_electrical = node_data.get("is_electrical", True)
            part_val = node_data.get("part_value", "")
            mfg_pn = node_data.get("mfg_pn", "")
            desc = node_data.get("description", "")
            full_text = f"{part_val} {mfg_pn} {desc}"
            
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
    
    # 動態規則推薦：完全由 patterns/rules/ 現存 YAML 規則自驅動 (Zero-Hardcoding)
    recommended_rules: List[RecommendedRule] = []
    seen_rule_names = set()

    try:
        from backend.app.services.pattern_service import PatternService
        l3_rules = PatternService.get_instance().get_level3_rules()
        for rule in l3_rules:
            r_name = rule.get("name")
            if not r_name or r_name in seen_rule_names:
                continue

            matched, reason = _match_rule_trigger(G, rule, detected_buses)
            if matched:
                seen_rule_names.add(r_name)
                ck_logics = rule.get("check_logic", [])
                first_type = ck_logics[0].get("type", "topology_check") if isinstance(ck_logics, list) and ck_logics else "topology_check"
                tags = rule.get("tags", [])
                primary_category = tags[0] if tags else rule.get("_domain", "DRC")
                recommended_rules.append(
                    RecommendedRule(
                        id=r_name,
                        name=rule.get("description") or r_name,
                        category=primary_category,
                        severity=rule.get("severity", "Error"),
                        domain=rule.get("_domain", "DRC"),
                        tags=tags,
                        reason=reason,
                        check_type=first_type
                    )
                )
    except Exception as e:
        logger.warning(f"動態掃描規則推薦失敗: {e}")

    return {
        "summary": summary,
        "recommended_rules": recommended_rules
    }
