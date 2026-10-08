"""
Level 3 DRC 混合執行引擎核心 (Level 3 DRC Runner)

無狀態、平行獨立評估所有 Level 3 規則 (topology_check 與 python_script / PartDB)。
產出標準化之 DRC 報告比對項目 (Finding Items)。
"""

import os
import uuid
import importlib.util
import logging
from typing import Dict, List, Any
import networkx as nx

from backend.app.services.pattern_service import PatternService
from backend.app.engine.drc_engine.graph_api import GraphAPI
from backend.app.engine.drc_engine.part_db import PartDB
from backend.app.engine.drc_engine.topology_evaluator import TopologyEvaluator

logger = logging.getLogger("designshield.level3_runner")

# 既有規則代碼至 Level 3 規則名稱之雙向映射
LEGACY_RULE_MAP = {
    "RULE-PWR-CAP-DERATING": "Power_Capacitor_Derating",
    "RULE-PWR-DECOUPLING": "IC_Decoupling_Capacitor_Existence",
    "RULE-CONN-PINOUT": "I2C_Pull_Up_Existence",
}


class Context:
    """提供注入至檢查邏輯中的內容"""
    def __init__(self, target: Dict[str, Any], G: nx.Graph):
        self.target = target
        self.G = G


class Level3Engine:
    def __init__(self):
        self.pattern_svc = PatternService.get_instance()
        self.part_db = PartDB()

    def run_checks(self, G: nx.Graph, selected_rule_ids: List[str]) -> List[Dict[str, Any]]:
        """
        執行選定的 Level 3 規則清單
        
        Args:
            G: NetworkX 電路圖譜
            selected_rule_ids: 使用者選取的規則 ID 陣列
            
        Returns:
            List[Dict[str, Any]]: 規格化的違規與判定報告項目清單
        """
        findings: List[Dict[str, Any]] = []
        graph_api = GraphAPI(G)
        evaluator = TopologyEvaluator(G, graph_api)

        # 展開並映射規則 ID
        normalized_ids = set()
        for r_id in selected_rule_ids:
            mapped = LEGACY_RULE_MAP.get(r_id, r_id)
            normalized_ids.add(mapped)
            normalized_ids.add(r_id)

        all_l3_rules = self.pattern_svc.get_level3_rules()

        for rule in all_l3_rules:
            r_name = rule.get("name")
            if r_name not in normalized_ids:
                # 檢查是否有 alias 命中
                is_alias_matched = any(LEGACY_RULE_MAP.get(k) == r_name and k in selected_rule_ids for k in selected_rule_ids)
                if not is_alias_matched:
                    continue

            # 1. 尋找命中 trigger_conditions 的目標節點
            targets = self._find_matching_targets(G, rule.get("trigger_conditions", {}))
            severity = rule.get("severity", "Error").upper()
            tags = rule.get("tags", [])
            primary_cat = tags[0] if tags else "DRC"
            r_title = rule.get("description") or r_name

            check_logics = rule.get("check_logic", [])
            if isinstance(check_logics, dict):
                check_logics = [check_logics]

            # 若無目標節點，視為 PASS (未觸發)
            if not targets:
                findings.append({
                    "item_id": f"v-{uuid.uuid4().hex[:8]}",
                    "rule_id": r_name,
                    "rule_category": primary_cat,
                    "rule_title": r_title,
                    "check_type": "LEVEL3_TOPOLOGY",
                    "status": "PASS",
                    "severity": "INFO",
                    "target_nodes": {"components": [], "nets": []},
                    "description": f"圖譜中未發現符合觸發條件之目標，規則判定為通過",
                    "comment": f"標籤: {', '.join(tags)}",
                    "evidence_trail": {"trigger_matched": False}
                })
                continue

            # 2. 針對各目標節點執行檢查邏輯
            for target in targets:
                target_id = target.get("_id", target.get("net_name", target.get("ref_des", "")))
                target_components = [target.get("ref_des")] if target.get("type") == "component" else []
                target_nets = [target.get("net_name")] if target.get("type") == "net" else []

                target_had_violation = False

                for step in check_logics:
                    step_type = step.get("type")

                    # 模式 A: 宣告式 topology_check
                    if step_type == "topology_check":
                        asserts = step.get("asserts", [])
                        for assertion in asserts:
                            res = evaluator.evaluate_assert(assertion, target)
                            if res and res.get("violation"):
                                target_had_violation = True
                                findings.append({
                                    "item_id": f"v-{uuid.uuid4().hex[:8]}",
                                    "rule_id": r_name,
                                    "rule_category": primary_cat,
                                    "rule_title": r_title,
                                    "check_type": "LEVEL3_TOPOLOGY",
                                    "status": "FAIL",
                                    "severity": severity,
                                    "target_nodes": {"components": target_components, "nets": target_nets},
                                    "description": res.get("message"),
                                    "comment": f"觸發節點: {target_id}",
                                    "evidence_trail": res.get("evidence", {})
                                })

                    # 模式 B: PartDB Python 腳本查表
                    elif step_type == "python_script":
                        script_path = step.get("script_path", "")
                        script_violations = self._run_python_script(script_path, target, G, graph_api)
                        for sv in script_violations:
                            target_had_violation = True
                            findings.append({
                                "item_id": f"v-{uuid.uuid4().hex[:8]}",
                                "rule_id": r_name,
                                "rule_category": primary_cat,
                                "rule_title": r_title,
                                "check_type": "LEVEL3_PARTDB",
                                "status": "FAIL",
                                "severity": sv.get("severity", severity),
                                "target_nodes": {"components": target_components, "nets": target_nets},
                                "description": sv.get("message", "PartDB 特規不符"),
                                "comment": f"觸發節點: {target_id}",
                                "evidence_trail": sv.get("evidence", {}),
                                "_meta": sv.get("evidence", {})
                            })

                # 若所有檢查皆通過
                if not target_had_violation:
                    findings.append({
                        "item_id": f"v-{uuid.uuid4().hex[:8]}",
                        "rule_id": r_name,
                        "rule_category": primary_cat,
                        "rule_title": r_title,
                        "check_type": "LEVEL3_TOPOLOGY",
                        "status": "PASS",
                        "severity": "INFO",
                        "target_nodes": {"components": target_components, "nets": target_nets},
                        "description": f"目標節點 {target_id} 通過 {r_title} 之所有拓撲與規格檢驗",
                        "comment": f"標籤: {', '.join(tags)}",
                        "evidence_trail": {"checked_target": target_id}
                    })

        return findings

    def _find_matching_targets(self, G: nx.Graph, trigger_conditions: Dict[str, Any]) -> List[Dict[str, Any]]:
        """在圖譜中找出所有符合 trigger_conditions 的節點字典"""
        matching = []
        gm = trigger_conditions.get("graph_match", {})
        attrs = gm.get("attributes", {})

        for node, data in G.nodes(data=True):
            matched = True
            for k, expected in attrs.items():
                if data.get(k) != expected:
                    matched = False
                    break
            if matched:
                d = dict(data)
                d["_id"] = node
                matching.append(d)
        return matching

    def _run_python_script(self, rel_script_path: str, target: Dict[str, Any], G: nx.Graph, graph_api: GraphAPI) -> List[Dict[str, Any]]:
        """沙盒執行 scripts/drc/ 下之 Python 腳本"""
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
        full_path = os.path.join(base_dir, rel_script_path)
        if not os.path.exists(full_path):
            logger.warning(f"DRC script not found: {full_path}")
            return []

        try:
            spec = importlib.util.spec_from_file_location("drc_module", full_path)
            if not spec or not spec.loader:
                return []
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            if hasattr(module, "execute"):
                ctx = Context(target=target, G=G)
                return module.execute(ctx, graph_api, self.part_db, {})
        except Exception as e:
            logger.error(f"Failed to execute DRC script {full_path}: {e}")
        return []
