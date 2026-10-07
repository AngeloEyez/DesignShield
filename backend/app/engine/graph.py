"""
線路圖譜 NetworkX 二分圖資料模型 (NetworkX Bipartite Schematic Graph)

實作 docs/pipeline_workflow.md 定義之二分異質圖 (Component 與 Net 節點，Pin 連線邊)，提供拓撲查詢與子圖分析。
"""

import re
import logging
from typing import Dict, List, Any, Optional, Set
import networkx as nx

logger = logging.getLogger("designshield.graph")

# 電源網路命名特徵常規正規表示式
POWER_NET_PATTERN = re.compile(
    r"^(VCC|VDD|VBUS|VIN|VBAT|\+\d+V|\+\d+V\d+|\d+V\d+|\d+V|P\d+V|V_\w+|VSYS|VREG|VOUT)",
    re.IGNORECASE
)

# 接地網路命名特徵常規正規表示式
GND_NET_PATTERN = re.compile(
    r"^(GND|AGND|DGND|PGND|SGND|VSS|EGND)",
    re.IGNORECASE
)

# 匯流排命名特徵 (依優先級排序)
BUS_PATTERNS = {
    "PCIE": re.compile(r"PCIE|PCI-E", re.IGNORECASE),
    "I2C": re.compile(r"I2C|SMBUS|SDA|SCL", re.IGNORECASE),
    "SPI": re.compile(r"SPI|MOSI|MISO|SCLK|SS_N|SPICLK", re.IGNORECASE),
    "UART": re.compile(r"UART|TXD|RXD|USART", re.IGNORECASE),
    "USB": re.compile(r"USB|USB_DP|USB_DM|VBUS|CC1|CC2|TYPEC|TYPE-C", re.IGNORECASE),
    "CAN": re.compile(r"CANH|CANL|CAN_TX|CAN_RX", re.IGNORECASE),
}


def is_power_net(name: str) -> bool:
    """判斷網路是否為電源網路 (Power Net)"""
    return bool(POWER_NET_PATTERN.search(name))


def is_ground_net(name: str) -> bool:
    """判斷網路是否為接地網路 (Ground Net)"""
    return bool(GND_NET_PATTERN.search(name))


def detect_bus_type(name: str) -> Optional[str]:
    """判斷網路屬於何種匯流排介面類型 (I2C, SPI, UART, USB, etc.)"""
    for bus_type, pattern in BUS_PATTERNS.items():
        if pattern.search(name):
            return bus_type
    return None


def build_schematic_graph(merged_data: Dict[str, Any]) -> nx.Graph:
    """
    構建線路圖 NetworkX 二分圖譜 (Bipartite Graph)
    
    Args:
        merged_data: 包含 components 與 nets 的字典
        
    Returns:
        nx.Graph: 構建完成之 NetworkX 無向圖譜
    """
    G = nx.Graph()
    components = merged_data.get("components", {})
    nets = merged_data.get("nets", {})
    power_symbol_nets = set(merged_data.get("power_symbol_nets", []))
    
    # 1. 新增 Component 節點 (bipartite=0)
    for ref_des, c_info in components.items():
        node_id = f"comp:{ref_des}"
        G.add_node(
            node_id,
            bipartite=0,
            type="component",
            ref_des=ref_des,
            part_value=c_info.get("part_value", ""),
            category=c_info.get("category", "Unknown"),
            sub_category=c_info.get("sub_category", "Other"),
            functional_role=c_info.get("functional_role", "None"),
            is_electrical=bool(c_info.get("is_electrical", True)),
            confidence=c_info.get("confidence", 1.0),
            evidence=c_info.get("evidence", []),
            pins_count=len(c_info.get("pins", [])),
            package=c_info.get("package", ""),
            description=c_info.get("description", ""),
            mfg=c_info.get("mfg", ""),
            mfg_pn=c_info.get("mfg_pn", ""),
            voltage=c_info.get("voltage", ""),
            loc=c_info.get("loc", (0, 0)),
            user_props=c_info.get("user_props", {})
        )
        
    # 2. 新增 Net 節點 (bipartite=1)
    for net_name in nets.keys():
        node_id = f"net:{net_name}"
        is_pwr = is_power_net(net_name)
        is_gnd = is_ground_net(net_name)
        bus_t = detect_bus_type(net_name)
        is_pwr_sym = net_name in merged_data.get("power_symbol_nets", [])
        
        G.add_node(
            node_id,
            bipartite=1,
            type="net",
            net_name=net_name,
            is_power=is_pwr,
            is_ground=is_gnd,
            is_bus=bool(bus_t),
            bus_type=bus_t,
            is_power_symbol_connected=is_pwr_sym
        )
        
    # 3. 建立 Pin 邊 (連接 Component 與 Net)
    for net_name, conns in nets.items():
        net_node = f"net:{net_name}"
        for conn in conns:
            ref_des = conn.get("ref_des")
            pin_num = conn.get("pin_number", "")
            pin_name = conn.get("pin_name", pin_num)
            comp_node = f"comp:{ref_des}"
            
            # 若元件節點尚未在圖中 (例如外接接頭未列於 XML)，自動補充
            if comp_node not in G:
                G.add_node(
                    comp_node,
                    bipartite=0,
                    type="component",
                    ref_des=ref_des,
                    part_value="",
                    category="Unknown",
                    sub_category="Other",
                    functional_role="None",
                    is_electrical=True
                )
                
            G.add_edge(
                comp_node,
                net_node,
                pin_number=pin_num,
                pin_name=pin_name
            )
            
    logger.info(
        "Built Schematic Graph: %d nodes, %d edges (Components: %d, Nets: %d)",
        G.number_of_nodes(),
        G.number_of_edges(),
        len([n for n, d in G.nodes(data=True) if d.get("type") == "component"]),
        len([n for n, d in G.nodes(data=True) if d.get("type") == "net"])
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
        role = d.get("functional_role", "None")
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
