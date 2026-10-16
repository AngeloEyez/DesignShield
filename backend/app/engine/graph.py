"""
線路圖譜 NetworkX 二分圖資料模型 (NetworkX Bipartite Schematic Graph)

實作 docs/pipeline_workflow.md 定義之二分異質圖 (Component 與 Net 節點，Pin 連線邊)，提供拓撲查詢與子圖分析。
"""

import logging
from typing import Dict, List, Any, Optional, Set
import networkx as nx

logger = logging.getLogger("designshield.graph")


def build_schematic_graph(merged_data: Dict[str, Any], task_id: Optional[str] = None) -> nx.Graph:
    """
    構建線路圖 NetworkX 二分圖譜 (Bipartite Graph)
    
    Args:
        merged_data: 包含 components 與 nets 的字典
        task_id: 可選的任務 ID (用於結構化日誌記錄)
        
    Returns:
        nx.Graph: 構建完成之 NetworkX 無向圖譜
    """
    from backend.app.core.task_logger import get_task_logger
    t_logger = get_task_logger(task_id) if task_id else None

    G = nx.Graph()
    components = merged_data.get("components", {})
    nets = merged_data.get("nets", {})
    power_symbol_nets = set(merged_data.get("power_symbol_nets", []))
    ground_symbol_nets = set(merged_data.get("ground_symbol_nets", []))
    net_symbols = merged_data.get("net_symbols", {})
    
    bom_config_info = merged_data.get("bom_config_info", {})
    G.graph["bom_config_info"] = bom_config_info

    elec_comp_count = 0
    # 1. 新增 Component 節點 (bipartite=0)
    for ref_des, c_info in components.items():
        node_id = f"comp:{ref_des}"
        is_elec = bool(c_info.get("is_electrical", True))
        if is_elec:
            elec_comp_count += 1
        G.add_node(
            node_id,
            bipartite=0,
            type="component",
            ref_des=ref_des,
            part_value=c_info.get("part_value", ""),
            category=c_info.get("category", "Unknown"),
            sub_category=c_info.get("sub_category", "Other"),
            component_role=c_info.get("component_role") or c_info.get("functional_role", "None"),
            functional_role=c_info.get("component_role") or c_info.get("functional_role", "None"),
            is_electrical=is_elec,
            confidence=c_info.get("confidence", 1.0),
            evidence=c_info.get("evidence", []),
            pins_count=len(c_info.get("pins", [])),
            package=c_info.get("package", ""),
            description=c_info.get("description", ""),
            mfg=c_info.get("mfg", ""),
            mfg_pn=c_info.get("mfg_pn", ""),
            voltage=c_info.get("voltage", ""),
            loc=c_info.get("loc", (0, 0)),
            user_props=c_info.get("user_props", {}),
            raw_bom=c_info.get("raw_bom") or c_info.get("user_props", {}).get("BOM", ""),
            bom=c_info.get("raw_bom") or c_info.get("user_props", {}).get("BOM", ""),
            bom_tokens=c_info.get("bom_tokens") or bom_config_info.get("component_bom_tokens", {}).get(ref_des, ["I"])
        )
        
    # 2. 新增 Net 節點 (bipartite=1，純二分圖拓撲結構，語意標籤留待 Level 2 規則引擎判定)
    pwr_sym_count = 0
    gnd_sym_count = 0

    for net_name in nets.keys():
        node_id = f"net:{net_name}"
        is_pwr_sym = net_name in power_symbol_nets
        is_gnd_sym = net_name in ground_symbol_nets
        
        if is_pwr_sym:
            pwr_sym_count += 1
        if is_gnd_sym:
            gnd_sym_count += 1

        G.add_node(
            node_id,
            bipartite=1,
            type="net",
            net_name=net_name,
            is_power=False,
            is_ground=False,
            is_bus=False,
            bus_type=None,
            is_power_symbol_connected=is_pwr_sym,
            is_ground_symbol_connected=is_gnd_sym,
            symbol_names=net_symbols.get(net_name, [])
        )
        
    # 3. 建立 Pin 邊 (連接 Component 與 Net)
    auto_supp_count = 0
    for net_name, conns in nets.items():
        net_node = f"net:{net_name}"
        for conn in conns:
            ref_des = conn.get("ref_des")
            pin_num = conn.get("pin_number", "")
            pin_name = conn.get("pin_name", pin_num)
            comp_node = f"comp:{ref_des}"
            
            # 若元件節點尚未在圖中 (例如外接接頭未列於 XML)，自動補充
            if comp_node not in G:
                auto_supp_count += 1
                G.add_node(
                    comp_node,
                    bipartite=0,
                    type="component",
                    ref_des=ref_des,
                    part_value="",
                    category="Unknown",
                    sub_category="Other",
                    component_role="None",
                    functional_role="None",
                    is_electrical=True,
                    raw_bom="",
                    bom="NOBOM",
                    bom_tokens=["I"]
                )
                
            if G.has_edge(comp_node, net_node):
                # 邊已存在（同網路連接同元件多腳位，如 Type-C 正反插）: 累加 pins 列表
                edge_data = G.get_edge_data(comp_node, net_node)
                pins_list = edge_data.setdefault("pins", [])
                pin_entry = {"pin_number": pin_num, "pin_name": pin_name}
                if pin_entry not in pins_list:
                    pins_list.append(pin_entry)
            else:
                # 邊不存在：建立邊並初始化 pins 列表，同時保留單值屬性達成 100% 向下相容
                G.add_edge(
                    comp_node,
                    net_node,
                    pin_number=pin_num,
                    pin_name=pin_name,
                    pins=[{"pin_number": pin_num, "pin_name": pin_name}]
                )
            
    comp_total = len([n for n, d in G.nodes(data=True) if d.get("type") == "component"])
    net_total = len([n for n, d in G.nodes(data=True) if d.get("type") == "net"])

    if t_logger:
        t_logger.debug(
            "PARSE_AND_GRAPH",
            "GRAPH",
            f"電路二分圖譜構建完成: 節點 {G.number_of_nodes()} 個 (元件 {comp_total} 顆, 網路 {net_total} 條), 拓撲邊 {G.number_of_edges()} 條 [電源符號 {pwr_sym_count}, 接地符號 {gnd_sym_count}]",
            details={
                "total_nodes": G.number_of_nodes(),
                "components_count": comp_total,
                "electrical_components_count": elec_comp_count,
                "non_electrical_components_count": comp_total - elec_comp_count,
                "nets_count": net_total,
                "power_symbol_nets_count": pwr_sym_count,
                "ground_symbol_nets_count": gnd_sym_count,
                "total_edges": G.number_of_edges(),
                "supplemented_components": auto_supp_count
            }
        )

    logger.info(
        "Built Schematic Graph: %d nodes, %d edges (Components: %d, Nets: %d)",
        G.number_of_nodes(),
        G.number_of_edges(),
        comp_total,
        net_total
    )
    return G


def get_components_on_net(G: nx.Graph, net_name: str) -> List[Dict[str, Any]]:
    """
    查詢連接至指定網路的所有元件與引腳
    
    Args:
        G: NetworkX 圖譜
        net_name: 網路名稱
        
    Returns:
        List[Dict]: 元件資訊與引腳代號清單
    """
    net_node = f"net:{net_name}"
    results = []
    if net_node not in G:
        return results
        
    for neighbor in G.neighbors(net_node):
        edge_data = G.get_edge_data(neighbor, net_node) or {}
        node_data = G.nodes[neighbor]
        results.append({
            "ref_des": node_data.get("ref_des"),
            "category": node_data.get("category"),
            "part_value": node_data.get("part_value"),
            "mfg_pn": node_data.get("mfg_pn"),
            "pin_number": edge_data.get("pin_number"),
            "pin_name": edge_data.get("pin_name")
        })
    return results


def get_nets_of_component(G: nx.Graph, ref_des: str) -> List[Dict[str, Any]]:
    """
    查詢指定元件連接的所有網路
    
    Args:
        G: NetworkX 圖譜
        ref_des: 元件編號 (例如 U1)
        
    Returns:
        List[Dict]: 網路資訊清單
    """
    comp_node = f"comp:{ref_des}"
    results = []
    if comp_node not in G:
        return results
        
    for neighbor in G.neighbors(comp_node):
        edge_data = G.get_edge_data(comp_node, neighbor) or {}
        node_data = G.nodes[neighbor]
        results.append({
            "net_name": node_data.get("net_name"),
            "is_power": node_data.get("is_power"),
            "is_ground": node_data.get("is_ground"),
            "bus_type": node_data.get("bus_type"),
            "pin_number": edge_data.get("pin_number"),
            "pin_name": edge_data.get("pin_name")
        })
    return results


def get_electrical_subgraph(G: nx.Graph) -> nx.Graph:
    """
    抽取電氣有效子圖 (排除非電氣機構件、對位點與測試點)
    
    Args:
        G: 全域 NetworkX 圖譜
        
    Returns:
        nx.Graph: 僅包含 is_electrical=True 元件與其相連網路的子圖
    """
    electrical_nodes = set()
    for n, d in G.nodes(data=True):
        if d.get("type") == "component":
            if d.get("is_electrical", True):
                electrical_nodes.add(n)
        elif d.get("type") == "net":
            electrical_nodes.add(n)
            
    # 建立包含電氣元件與網路的誘導子圖，並移除孤立網路節點
    subG = G.subgraph(electrical_nodes).copy()
    isolated_nets = [
        n for n, d in subG.nodes(data=True)
        if d.get("type") == "net" and subG.degree(n) == 0
    ]
    subG.remove_nodes_from(isolated_nets)
    return subG


def identify_key_components(G: nx.Graph) -> Dict[str, Any]:
    """
    使用度中心性 (Degree Centrality) 與引腳規模識別核心節點與角色目錄
    
    Returns:
        Dict: 包含 key_ics, key_connectors, ic_directory_by_role, non_electrical_components
    """
    subG = get_electrical_subgraph(G)
    centrality = nx.degree_centrality(subG) if len(subG) > 0 else {}
    
    ic_candidates = []
    connector_candidates = []
    ic_directory_by_role: Dict[str, List[str]] = {}
    non_electrical_components: List[str] = []

    for n, d in G.nodes(data=True):
        if d.get("type") != "component":
            continue
            
        ref = d.get("ref_des") or n.replace("comp:", "")
        pval = d.get("part_value", "")
        cat = d.get("category", "Unknown")
        role = d.get("component_role") or d.get("functional_role", "None")
        is_elec = d.get("is_electrical", True)
        pins_cnt = len(list(G.neighbors(n)))
        raw_pins = d.get("pins_count", 0)
        effective_pins = max(raw_pins, pins_cnt)
        cent_score = centrality.get(n, 0.0)

        label = f"{ref} ({pval})" if pval else ref

        if not is_elec:
            non_electrical_components.append(label)
            continue

        if cat == "IC":
            # 依角色分組目錄
            if role not in ic_directory_by_role:
                ic_directory_by_role[role] = []
            ic_directory_by_role[role].append(label)

            # 核心 IC 門檻：有效引腳數 >= 20 或 (角色為 Bus_Master 且引腳 >= 10)
            if effective_pins >= 20 or (role == "Bus_Master" and effective_pins >= 10):
                ic_candidates.append({
                    "label": label,
                    "pins": effective_pins,
                    "centrality": cent_score
                })

        elif cat == "Connector":
            # 關鍵連接器門檻：有效引腳數 >= 20
            if effective_pins >= 20:
                connector_candidates.append({
                    "label": label,
                    "pins": effective_pins,
                    "centrality": cent_score
                })

    # 排序：優先引腳數降序，再以中心性降序
    ic_candidates.sort(key=lambda x: (x["pins"], x["centrality"]), reverse=True)
    connector_candidates.sort(key=lambda x: (x["pins"], x["centrality"]), reverse=True)

    return {
        "key_ics": [c["label"] for c in ic_candidates],
        "key_connectors": [c["label"] for c in connector_candidates],
        "ic_directory_by_role": ic_directory_by_role,
        "non_electrical_components": non_electrical_components
    }


def create_config_subgraph(
    G: nx.Graph,
    config_index: int = 0,
    is_mp_mode: bool = False
) -> nx.Graph:
    """
    依據指定的 BOM Config 索引與 MP Mode 狀態構建「裝配狀態標註圖譜」(Mounting-Annotated Graph)。
    
    雙軌架構原則：
    1. 實體拓撲全開：100% 保留所有元件與網路節點及連線邊（絕不破壞性刪點），確保走線極性與端到端通道可完整被追蹤。
    2. 節點狀態標註：為各元件節點標註 `is_mounted` (布林值) 與 `bom` (正規化代碼：'I', 'X', 'P', 'M', 'NOBOM')。
    3. 供伴生腳本與 GraphAPI 自由依情境判斷（例如檢查 TU2 差分引腳極性、或 AC Cap / 串聯電阻是否上件導通）。
    
    Args:
        G: NetworkX 基礎完整電路圖
        config_index: Config 索引 (0-based)
        is_mp_mode: 是否為量產模式 (True: MP Mode, False: 樣品/Sample Mode)
        
    Returns:
        nx.Graph: 標註當前 Config 上件狀態之完整拓撲圖
    """
    from backend.app.engine.bom_parser import is_component_mounted, normalize_bom_token

    sub_G = G.copy()
    bom_info = G.graph.get("bom_config_info", {})
    comp_tokens = bom_info.get("component_bom_tokens", {})

    unmounted_components: Dict[str, Dict[str, Any]] = {}

    for node, data in sub_G.nodes(data=True):
        if data.get("type") == "component":
            ref_des = data.get("ref_des", node.replace("comp:", ""))
            tokens = comp_tokens.get(ref_des) or data.get("bom_tokens") or ["I"]
            raw_token = tokens[config_index] if config_index < len(tokens) else tokens[0]
            canonical_token = normalize_bom_token(raw_token)

            try:
                mounted = is_component_mounted(canonical_token, is_mp_mode=is_mp_mode)
            except Exception:
                mounted = True

            # 核心雙軌屬性: is_mounted (極速布林判斷) 與 bom (當前正規化縮寫: I, X, P, M, NOBOM)
            data["is_mounted"] = mounted
            data["bom"] = canonical_token

            if not mounted:
                unmounted_components[ref_des] = dict(data)

    # 完整保留所有節點與拓撲邊，不進行任何 remove_nodes_from 破壞性刪減！
    # 記錄未上件資訊與當前環境變數至圖譜中繼，供 GraphAPI 與伴生腳本存取
    sub_G.graph["unmounted_components"] = unmounted_components
    sub_G.graph["active_config_index"] = config_index
    config_names = bom_info.get("config_names", [])
    sub_G.graph["active_config_name"] = (
        config_names[config_index] if config_index < len(config_names) else f"Config {config_index + 1}"
    )
    sub_G.graph["is_mp_mode"] = is_mp_mode

    return sub_G

