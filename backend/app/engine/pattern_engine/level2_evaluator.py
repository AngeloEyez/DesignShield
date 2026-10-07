import re
import networkx as nx
from backend.app.engine.pattern_engine.models import SignalPattern, SignalMatchCondition, SignalMatchBlock

def evaluate_net_against_signal(G: nx.Graph, net_node: str, signal: SignalPattern) -> (bool, float):
    """
    遞迴評估 net 節點是否吻合指定的 SignalPattern
    Returns:
        (是否吻合: bool, 貢獻之信心度: float)
    """
    net_data = G.nodes[net_node]
    
    # 若有設定 matches，則遞迴解析
    if signal.matches:
        return _eval_match_condition(G, net_node, net_data, signal.matches)
    
    return False, 0.0

def _eval_match_condition(G: nx.Graph, net_node: str, net_data: dict, cond: SignalMatchCondition) -> (bool, float):
    # 檢查是否為遞迴區塊 match_any / match_all
    if cond.match_any:
        for block in cond.match_any:
            matched, conf = _eval_match_block(G, net_node, net_data, block)
            if matched:
                return True, conf
        return False, 0.0
    
    if cond.match_all:
        total_conf = 0.0
        for sub_cond in cond.match_all:
            matched, conf = _eval_match_condition(G, net_node, net_data, sub_cond)
            if not matched:
                return False, 0.0
            total_conf += conf
        return True, total_conf
        
    # 基本條件 (Primitive conditions)
    return _eval_primitive_conditions(G, net_node, net_data, cond)
    
def _eval_match_block(G: nx.Graph, net_node: str, net_data: dict, block: SignalMatchBlock) -> (bool, float):
    for cond in block.match_all:
        matched, _ = _eval_match_condition(G, net_node, net_data, cond)
        if not matched:
            return False, 0.0
    return True, block.confidence_contribution

def _eval_primitive_conditions(G: nx.Graph, net_node: str, net_data: dict, cond: SignalMatchCondition) -> (bool, float):
    net_name = net_data.get("net_name", "")
    
    # 1. 物理鐵證判斷 (Power/GND Symbols)
    if cond.is_power_symbol_connected is not None:
        if net_data.get("is_power_symbol_connected", False) != cond.is_power_symbol_connected:
            return False, 0.0
            
    if cond.is_ground_symbol_connected is not None:
        if net_data.get("is_power_symbol_connected", False) != cond.is_ground_symbol_connected:
            return False, 0.0
            
    # 2. Net Name 判斷
    if cond.net_name_regex:
        if not re.search(cond.net_name_regex, net_name):
            return False, 0.0
            
    # 3. Pin Name 判斷 (檢驗這條線上掛載的所有 IC pin name)
    if cond.pin_name_regex:
        pin_matched = False
        for neighbor in G.neighbors(net_node):
            if G.nodes[neighbor].get("type") == "component":
                edge_data = G.get_edge_data(neighbor, net_node)
                pin_name = edge_data.get("pin_name", "")
                if re.search(cond.pin_name_regex, pin_name):
                    pin_matched = True
                    break
        if not pin_matched:
            return False, 0.0
            
    return True, 0.0
