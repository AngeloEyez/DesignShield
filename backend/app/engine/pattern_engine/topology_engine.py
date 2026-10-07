import os
import yaml
import logging
import networkx as nx
from typing import Dict, List, Any

from backend.app.engine.pattern_engine.models import TopologyRule
from backend.app.engine.pattern_engine.level2_evaluator import evaluate_net_against_signal
from backend.app.engine.rules.heuristic import extract_operating_voltage_from_net

logger = logging.getLogger("designshield.topology_engine")

class TopologyPatternEngine:
    """
    Level 2 網路與匯流排拓撲引擎
    負責評估 PowerPattern 與 BusPattern
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.rules = []
            cls._instance._load_rules()
        return cls._instance

    def _load_rules(self):
        base_dir = os.path.join(os.path.dirname(__file__), "../../../..")
        power_dir = os.path.join(base_dir, "patterns", "power")
        buses_dir = os.path.join(base_dir, "patterns", "buses")
        
        self.rules = []
        for d in [power_dir, buses_dir]:
            if not os.path.exists(d):
                continue
            for f in os.listdir(d):
                if f.endswith(".yaml"):
                    try:
                        with open(os.path.join(d, f), 'r', encoding='utf-8') as ymlfile:
                            data = yaml.safe_load(ymlfile)
                            if data:
                                self.rules.append(TopologyRule(**data))
                    except Exception as e:
                        logger.error(f"Failed to load topology rule {f}: {e}")
                        
        # 依 priority 降冪排序
        self.rules.sort(key=lambda r: r.priority, reverse=True)
        logger.info(f"TopologyPatternEngine loaded {len(self.rules)} rules.")

    def execute(self, G: nx.Graph):
        """
        執行 Level 2 評估，將結果直接寫入 G (Graph)
        """
        nets = [n for n, d in G.nodes(data=True) if d.get('type') == 'net']
        
        for net_node in nets:
            net_data = G.nodes[net_node]
            # 依序匹配規則
            for rule in self.rules:
                matched, confidence = self._evaluate_rule(G, net_node, rule)
                if matched:
                    if rule.category == "Power":
                        self._apply_power_rule(G, net_node, rule)
                    elif rule.category == "Communication":
                        self._apply_bus_rule(G, net_node, rule, confidence)
                    # 進行拓撲角色覆寫
                    if rule.role_overrides:
                        self._apply_role_overrides(G, net_node, rule)
                    # 優先級消耗制：一旦匹配，不再套用較低 priority 規則
                    break

    def _evaluate_rule(self, G: nx.Graph, net_node: str, rule: TopologyRule):
        total_confidence = 0.0
        # 只要任一 required 訊號吻合，即視為該網路部分屬於此 Rule
        # (這裡針對單一訊號線評估。對於 Bus，真正的群組在之後實作)
        for sig in rule.signals:
            matched, conf = evaluate_net_against_signal(G, net_node, sig)
            if matched:
                return True, conf
        return False, 0.0

    def _apply_power_rule(self, G: nx.Graph, net_node: str, rule: TopologyRule):
        net_data = G.nodes[net_node]
        # 更新網路屬性
        if "GND" in rule.name:
            net_data["is_ground"] = True
        else:
            net_data["is_power"] = True
            
        # 處理 extra_fields 推論
        if rule.extra_fields and "operating_voltage" in rule.extra_fields:
            field = rule.extra_fields["operating_voltage"]
            if field.source == "static":
                net_data["operating_voltage"] = field.value
            elif field.source == "infer" and field.infer_strategy == "parse_voltage_from_name":
                net_data["operating_voltage"] = extract_operating_voltage_from_net(net_data.get("net_name", ""))

    def _apply_bus_rule(self, G: nx.Graph, net_node: str, rule: TopologyRule, confidence: float):
        net_data = G.nodes[net_node]
        net_data["is_bus"] = True
        net_data["bus_type"] = rule.name
        net_data["bus_confidence"] = confidence

    def _apply_role_overrides(self, G: nx.Graph, net_node: str, rule: TopologyRule):
        # 尋找連接到此 net 的元件，若符合 overrides，則更改其 functional_role
        pass # 詳細的被動元件升級實作將在後續擴充
