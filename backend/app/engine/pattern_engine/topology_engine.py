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

    @classmethod
    def get_instance(cls) -> "TopologyPatternEngine":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def reload(self) -> int:
        """強制重新讀取 Level 2 規則 YAML 並依優先順序排序"""
        self._load_rules()
        return len(self.rules)

    def _load_rules(self):
        base_dir = os.path.join(os.path.dirname(__file__), "../../../..")
        power_dir = os.path.join(base_dir, "patterns", "power")
        buses_dir = os.path.join(base_dir, "patterns", "buses")
        signals_dir = os.path.join(base_dir, "patterns", "signals")
        
        self.rules = []
        for d in [power_dir, buses_dir, signals_dir]:
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
        import re
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
        matched_sig_count = 0
        matches_detail = []
        
        for net_node in nets:
            net_data = G.nodes[net_node]
            net_name = net_data.get("net_name", net_node.replace("net:", ""))
            
            # 各特徵領域解耦標記：接地、電源軌、通訊匯流排、功能訊號各允許匹配一條最佳規則
            gnd_matched = False
            pwr_matched = False
            bus_matched = False
            sig_matched = False

            for rule in self.rules:
                is_gnd_rule = rule.category == "Power" and "GND" in rule.name
                is_pwr_rule = rule.category == "Power" and "GND" not in rule.name
                is_bus_rule = rule.category == "Communication"
                is_sig_rule = rule.category in ["Differential", "Control", "Clock", "Analog", "Signal"]

                # 若該領域已匹配最高優先級規則，跳過該領域之低優先級規則
                if is_gnd_rule and gnd_matched:
                    continue
                if is_pwr_rule and pwr_matched:
                    continue
                if is_bus_rule and bus_matched:
                    continue
                if is_sig_rule and sig_matched:
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
                    elif is_sig_rule:
                        self._apply_signal_rule(G, net_node, rule, confidence)
                        sig_matched = True
                        matched_sig_count += 1

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

                    # 若四大領域皆已匹配完畢，提前結束此網路之比對
                    if gnd_matched and pwr_matched and bus_matched and sig_matched:
                        break

        if t_logger:
            t_logger.debug(
                "PARSE_AND_GRAPH",
                "GRAPH",
                f"Level 2 拓撲模式引擎評估完成: 成功識別 {len(matches_detail)} 條網路 (電源規則 {matched_power_count} 處, 匯流排規則 {matched_bus_count} 處, 功能訊號 {matched_sig_count} 處)",
                details={
                    "total_matched": len(matches_detail),
                    "matched_power": matched_power_count,
                    "matched_bus": matched_bus_count,
                    "matched_sig": matched_sig_count,
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
        net_data["confidence"] = max(float(net_data.get("confidence", 0.0)), confidence)
        if "evidence" not in net_data:
            net_data["evidence"] = []
        net_data["evidence"].append(f"bus_rule:{rule.name}")

    def _apply_signal_rule(self, G: nx.Graph, net_node: str, rule: TopologyRule, confidence: float):
        import re
        net_data = G.nodes[net_node]
        net_name = net_data.get("net_name", net_node.replace("net:", ""))
        net_data["net_type"] = rule.category
        sig_role = rule.signals[0].role if rule.signals else rule.name
        net_data["functional_role"] = sig_role
        net_data["confidence"] = max(float(net_data.get("confidence", 0.0)), confidence)
        if "evidence" not in net_data:
            net_data["evidence"] = []
        net_data["evidence"].append(f"rule:{rule.name}")

        # 若命中差分規則，自動提取極性與推導配對夥伴
        if rule.category == "Differential":
            self._derive_differential_properties(G, net_node, net_name)

    def _derive_differential_properties(self, G: nx.Graph, net_node: str, net_name: str):
        import re
        net_data = G.nodes[net_node]
        polarity = None
        partner = None

        # 模式 1: 帶有 _P_ / _N_ 或結尾 _P / _N (如 _P_C, _N_C, _P_DL4, _P_R)
        if re.search(r'_P(_|$)', net_name):
            polarity = 'P'
            partner = re.sub(r'_P(_|$)', r'_N\1', net_name, count=1)
        elif re.search(r'_N(_|$)', net_name):
            polarity = 'N'
            partner = re.sub(r'_N(_|$)', r'_P\1', net_name, count=1)
        # 模式 2: AUXP / AUXN (如 AUXP_R, AUX_TCP0_P_C)
        elif re.search(r'AUXP(_|$)', net_name):
            polarity = 'P'
            partner = re.sub(r'AUXP(_|$)', r'AUXN\1', net_name, count=1)
        elif re.search(r'AUXN(_|$)', net_name):
            polarity = 'N'
            partner = re.sub(r'AUXN(_|$)', r'AUXP\1', net_name, count=1)
        # 模式 3: _DP / _DN
        elif re.search(r'_DP(_|$)', net_name):
            polarity = 'P'
            partner = re.sub(r'_DP(_|$)', r'_DN\1', net_name, count=1)
        elif re.search(r'_DN(_|$)', net_name):
            polarity = 'N'
            partner = re.sub(r'_DN(_|$)', r'_DP\1', net_name, count=1)

        if polarity:
            net_data["diff_polarity"] = polarity
        if partner:
            net_data["diff_pair_partner"] = partner

    def _apply_role_overrides(self, G: nx.Graph, net_node: str, rule: TopologyRule):
        """
        拓撲角色動態覆寫 (Dynamic Role Overrides)
        依據 YAML 設定，將掛載於此網路之被動元件 (如電阻、電容) 升級為具體的電路角色 (如 Pull_up, Series_Resistor, AC_Coupling_Capacitor)
        """
        if not rule.role_overrides:
            return

        for comp_node in list(G.neighbors(net_node)):
            cdata = G.nodes[comp_node]
            if cdata.get("type") != "component":
                continue

            sub_cat = str(cdata.get("sub_category") or cdata.get("category") or "")

            for override in rule.role_overrides:
                if override.original_sub_category.lower() != sub_cat.lower():
                    continue

                # 尋找該元件所連接之其他網路
                other_nets = [n for n in G.neighbors(comp_node) if n != net_node and G.nodes[n].get("type") == "net"]
                matched_override = False

                if override.connected_to == "PowerRail":
                    for onet in other_nets:
                        odata = G.nodes[onet]
                        if odata.get("is_power") or odata.get("net_type") == "Power" or "VCC" in onet.upper() or "VDD" in onet.upper():
                            matched_override = True
                            break

                elif override.connected_to == "GND":
                    for onet in other_nets:
                        odata = G.nodes[onet]
                        if odata.get("is_ground") or "GND" in onet.upper():
                            matched_override = True
                            break

                elif override.connected_to == "Signal":
                    if other_nets:
                        is_all_signals = all(
                            not (G.nodes[n].get("is_power") or G.nodes[n].get("is_ground") or "VCC" in n.upper() or "GND" in n.upper())
                            for n in other_nets
                        )
                        if is_all_signals:
                            matched_override = True

                elif override.connected_to == "Any":
                    matched_override = True

                if matched_override:
                    cdata["functional_role"] = override.new_role
                    if "evidence" not in cdata:
                        cdata["evidence"] = []
                    cdata["evidence"].append(f"role_override:{override.new_role}")
                    logger.debug(f"元件 {comp_node} 拓撲角色升級覆寫為: {override.new_role} (規則: {rule.name})")
                    break
