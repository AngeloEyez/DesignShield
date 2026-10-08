import os
import yaml
import logging
import networkx as nx
from typing import Dict, List, Any, Optional

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

    def execute(self, G: nx.Graph, task_id: Optional[str] = None):
        """
        執行 Level 2 評估，將結果直接寫入 G (Graph)
        """
        from backend.app.core.task_logger import get_task_logger
        t_logger = get_task_logger(task_id) if task_id else None

        nets = [n for n, d in G.nodes(data=True) if d.get('type') == 'net']
        if t_logger:
            t_logger.debug(
                "PARSE_AND_GRAPH",
                "GRAPH",
                f"開始執行 Level 2 拓撲模式引擎 (載入 {len(self.rules)} 條規則，評估 {len(nets)} 條網路)...",
                details={"rules_count": len(self.rules), "nets_count": len(nets)}
            )

        matched_power_count = 0
        matched_bus_count = 0
        matches_detail = []
        
        for net_node in nets:
            net_data = G.nodes[net_node]
            net_name = net_data.get("net_name", net_node.replace("net:", ""))
            
            # 各特徵領域解耦標記：接地、電源軌、通訊匯流排各允許匹配一條最佳規則
            gnd_matched = False
            pwr_matched = False
            bus_matched = False

            for rule in self.rules:
                is_gnd_rule = rule.category == "Power" and "GND" in rule.name
                is_pwr_rule = rule.category == "Power" and "GND" not in rule.name
                is_bus_rule = rule.category == "Communication"

                # 若該領域已匹配最高優先級規則，跳過該領域之低優先級規則
                if is_gnd_rule and gnd_matched:
                    continue
                if is_pwr_rule and pwr_matched:
                    continue
                if is_bus_rule and bus_matched:
                    continue

                matched, confidence = self._evaluate_rule(G, net_node, rule)
                if matched:
                    if is_gnd_rule:
                        self._apply_power_rule(G, net_node, rule)
                        gnd_matched = True
                        matched_power_count += 1
                    elif is_pwr_rule:
                        self._apply_power_rule(G, net_node, rule)
                        pwr_matched = True
                        matched_power_count += 1
                    elif is_bus_rule:
                        self._apply_bus_rule(G, net_node, rule, confidence)
                        bus_matched = True
                        matched_bus_count += 1

                    matches_detail.append({
                        "net_name": net_name,
                        "rule_name": rule.name,
                        "category": rule.category,
                        "confidence": confidence
                    })

                    if t_logger:
                        t_logger.debug(
                            "PARSE_AND_GRAPH",
                            "GRAPH",
                            f"Level 2 拓撲規則命中: 網路 {net_name} 匹配規則 [{rule.name}] (類別: {rule.category}, 信心度: {confidence:.2f})",
                            details={"net_name": net_name, "rule_name": rule.name, "category": rule.category, "confidence": confidence}
                        )

                    # 進行拓撲角色覆寫
                    if rule.role_overrides:
                        self._apply_role_overrides(G, net_node, rule)

                    # 若三大領域皆已匹配完畢，提前結束此網路之比對
                    if gnd_matched and pwr_matched and bus_matched:
                        break

        if t_logger:
            t_logger.debug(
                "PARSE_AND_GRAPH",
                "GRAPH",
                f"Level 2 拓撲模式引擎評估完成: 成功識別 {len(matches_detail)} 條網路 (電源規則 {matched_power_count} 處, 匯流排規則 {matched_bus_count} 處)",
                details={
                    "total_matched": len(matches_detail),
                    "matched_power": matched_power_count,
                    "matched_bus": matched_bus_count,
                    "sample_matches": matches_detail[:15]
                }
            )

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
