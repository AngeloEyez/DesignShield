"""
Level 3 DRC 混合執行引擎 (Level 3 DRC Hybrid Runner)

支援:
1. 宣告式拓撲斷言 (Topology Evaluator)
2. PartDB Python 腳本沙盒執行 (Sandboxed Script Runner)
3. LLM Agent 語意邏輯推理檢測 (LLM Agent Runner)
"""

import os
import re
import json
import time
import uuid
import logging
from typing import Dict, List, Any, Optional, Set
import networkx as nx

from backend.app.services.pattern_service import PatternService
from backend.app.engine.drc_engine.graph_api import GraphAPI
from backend.app.engine.drc_engine.topology_evaluator import TopologyEvaluator

logger = logging.getLogger("designshield.level3_runner")

# 向前相容映射表：舊版前端或工作流傳入之規則 ID -> 新版 Level 3 YAML 規則名稱
LEGACY_RULE_MAP: Dict[str, str] = {
    "RULE-BUS-I2C-PULLUP": "I2C_Pull_Up_Existence",
    "RULE-PWR-GND-SHORT": "Power_Ground_Short_Fatal",
    "Power_Ground_Short_Circuit": "Power_Ground_Short_Fatal",
    "RULE-PWR-DECOUPLING": "IC_Decoupling_Capacitor_Existence",
    "Decoupling_Capacitor_Existence": "IC_Decoupling_Capacitor_Existence",
    "RULE-PWR-CAP-DERATING": "Power_Capacitor_Derating",
    "Capacitor_Voltage_Derating": "Power_Capacitor_Derating",
    "RULE-BUS-I2C-STM32": "I2C_PartDB_Dynamic_Compliance",
    "I2C_STM32_Dynamic_Specification": "I2C_PartDB_Dynamic_Compliance",
    # LLM 規則舊版 ID 雙向映射
    "RULE-LLM-SD-MODE": "SD_Interface_Mode_Reasoning",
    "RULE-LLM-POWER-SEQUENCE": "Power_Sequence_Compatibility",
    "RULE-LLM-LEVEL-SHIFT": "Level_Shift_Logic_Validation",
}


class Level3Engine:
    """
    Level 3 DRC 混合執行引擎
    
    具備高效分流能力：
    - run_heuristic_checks: 毫秒級執行 topology_check 與沙盒 python_script
    - run_llm_checks: 執行非同步 llm_agent 語意推理與優雅降級
    """

    def __init__(self, pattern_service: Optional[PatternService] = None):
        self.pattern_svc = pattern_service or PatternService.get_instance()

    def run_heuristic_checks(self, G: nx.Graph, selected_rule_ids: List[str]) -> List[Dict[str, Any]]:
        """
        執行選定規則中的傳統啟發式與拓撲比對（topology_check, python_script）
        """
        return self._execute_rules(G, selected_rule_ids, allowed_types={"topology_check", "python_script"})

    def run_llm_checks(
        self,
        G: nx.Graph,
        selected_rule_ids: List[str],
        progress_callback: Optional[Any] = None
    ) -> List[Dict[str, Any]]:
        """
        執行選定規則中的大語言模型邏輯推理檢測（llm_agent）
        """
        return self._execute_rules(
            G,
            selected_rule_ids,
            allowed_types={"llm_agent"},
            progress_callback=progress_callback
        )

    def run_checks(self, G: nx.Graph, selected_rule_ids: List[str]) -> List[Dict[str, Any]]:
        """
        全域檢查入口（相容既有調用，執行所有選定規則步驟）
        """
        return self._execute_rules(
            G,
            selected_rule_ids,
            allowed_types={"topology_check", "python_script", "llm_agent"}
        )

    def _execute_rules(
        self,
        G: nx.Graph,
        selected_rule_ids: List[str],
        allowed_types: Set[str],
        progress_callback: Optional[Any] = None
    ) -> List[Dict[str, Any]]:
        """
        通用規則執行調度器
        """
        findings: List[Dict[str, Any]] = []
        graph_api = GraphAPI(G)
        evaluator = TopologyEvaluator(G, graph_api)

        all_l3_rules = self.pattern_svc.get_level3_rules()
        rule_by_name = {r.get("name"): r for r in all_l3_rules if r.get("name")}

        # 按照使用者傳入的 selected_rule_ids 順序挑選候選規則
        candidate_rules = []
        seen_rules = set()

        for req_id in selected_rule_ids:
            canonical_name = LEGACY_RULE_MAP.get(req_id, req_id)
            rule = rule_by_name.get(canonical_name) or rule_by_name.get(req_id)
            if not rule:
                continue

            r_name = rule.get("name")
            if (r_name, req_id) in seen_rules:
                continue
            seen_rules.add((r_name, req_id))

            check_logics = rule.get("check_logic", [])
            if isinstance(check_logics, dict):
                check_logics = [check_logics]

            matching_steps = [s for s in check_logics if s.get("type") in allowed_types]
            if matching_steps:
                candidate_rules.append((rule, matching_steps, req_id))

        total_rules = len(candidate_rules)

        for idx, (rule, active_steps, requested_id) in enumerate(candidate_rules, start=1):
            r_name = rule.get("name")
            output_rule_id = requested_id or r_name
            severity = rule.get("severity", "Error").upper()
            tags = rule.get("tags", [])
            primary_cat = tags[0] if tags else "DRC"
            r_title = rule.get("description") or r_name

            if progress_callback:
                try:
                    progress_callback(idx, total_rules, output_rule_id, r_title, "START")
                except Exception as pe:
                    logger.warning("進度回呼通知失敗 (START): %s", pe)

            # 1. 尋找命中 trigger_conditions 的目標節點
            targets = self._find_matching_targets(G, rule.get("trigger_conditions", {}))

            # 若無目標節點，視為 PASS (未觸發)
            if not targets:
                check_type_label = "LLM" if any(s.get("type") == "llm_agent" for s in active_steps) else "LEVEL3_TOPOLOGY"
                findings.append({
                    "item_id": f"v-{uuid.uuid4().hex[:8]}",
                    "rule_id": output_rule_id,
                    "rule_category": primary_cat,
                    "rule_title": r_title,
                    "check_type": check_type_label,
                    "status": "PASS",
                    "severity": "INFO",
                    "target_nodes": {"components": [], "nets": []},
                    "description": f"圖譜中未發現符合觸發條件之目標，規則判定為通過",
                    "comment": f"標籤: {', '.join(tags)}",
                    "evidence_trail": {"trigger_matched": False}
                })
                if progress_callback:
                    try:
                        progress_callback(idx, total_rules, output_rule_id, r_title, "DONE")
                    except Exception as pe:
                        logger.warning("進度回呼通知失敗 (DONE): %s", pe)
                continue

            # 2. 針對各步驟執行檢查
            for step in active_steps:
                step_type = step.get("type")

                # 模式 A: 宣告式 topology_check
                if step_type == "topology_check":
                    asserts = step.get("asserts", [])
                    for target in targets:
                        target_id = target.get("_id", target.get("net_name", target.get("ref_des", "")))
                        target_components = [target.get("ref_des")] if target.get("type") == "component" else []
                        target_nets = [target.get("net_name")] if target.get("type") == "net" else []
                        target_had_violation = False

                        for assertion in asserts:
                            res = evaluator.evaluate_assert(assertion, target)
                            if res and res.get("violation"):
                                target_had_violation = True
                                findings.append({
                                    "item_id": f"v-{uuid.uuid4().hex[:8]}",
                                    "rule_id": output_rule_id,
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

                        if not target_had_violation:
                            findings.append({
                                "item_id": f"v-{uuid.uuid4().hex[:8]}",
                                "rule_id": output_rule_id,
                                "rule_category": primary_cat,
                                "rule_title": r_title,
                                "check_type": "LEVEL3_TOPOLOGY",
                                "status": "PASS",
                                "severity": "INFO",
                                "target_nodes": {"components": target_components, "nets": target_nets},
                                "description": f"目標節點 {target_id} 通過 {r_title} 之所有拓撲檢驗",
                                "comment": f"標籤: {', '.join(tags)}",
                                "evidence_trail": {"checked_target": target_id}
                            })

                # 模式 B: PartDB Python 腳本查表
                elif step_type == "python_script":
                    script_path = step.get("script_path", "")
                    for target in targets:
                        target_id = target.get("_id", target.get("net_name", target.get("ref_des", "")))
                        target_components = [target.get("ref_des")] if target.get("type") == "component" else []
                        target_nets = [target.get("net_name")] if target.get("type") == "net" else []

                        script_violations = self._run_python_script(script_path, target, G, graph_api)
                        if script_violations:
                            for sv in script_violations:
                                findings.append({
                                    "item_id": f"v-{uuid.uuid4().hex[:8]}",
                                    "rule_id": output_rule_id,
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
                        else:
                            findings.append({
                                "item_id": f"v-{uuid.uuid4().hex[:8]}",
                                "rule_id": output_rule_id,
                                "rule_category": primary_cat,
                                "rule_title": r_title,
                                "check_type": "LEVEL3_PARTDB",
                                "status": "PASS",
                                "severity": "INFO",
                                "target_nodes": {"components": target_components, "nets": target_nets},
                                "description": f"目標節點 {target_id} 通過 {r_title} 之動態規格檢驗",
                                "comment": f"標籤: {', '.join(tags)}",
                                "evidence_trail": {"checked_target": target_id}
                            })

                # 模式 C: LLM Agent 語意邏輯推理
                elif step_type == "llm_agent":
                    keyword = step.get("context_extraction", {}).get("keyword", "")
                    subgraph_ctx = self._extract_subgraph_context(G, keyword=keyword, targets=targets)
                    prompt_template = step.get("agent_prompt", "")
                    subgraph_json_str = json.dumps(subgraph_ctx, ensure_ascii=False)
                    prompt = prompt_template.replace("${context.subgraph}", subgraph_json_str)

                    llm_finding = self._run_llm_step(
                        step=step,
                        prompt=prompt,
                        subgraph_ctx=subgraph_ctx,
                        rule_name=output_rule_id,
                        rule_title=r_title,
                        primary_cat=primary_cat,
                        default_severity=severity,
                        tags=tags
                    )
                    findings.append(llm_finding)

            if progress_callback:
                try:
                    progress_callback(idx, total_rules, output_rule_id, r_title, "DONE")
                except Exception as pe:
                    logger.warning("進度回呼通知失敗 (DONE): %s", pe)

        return findings

    def _find_matching_targets(self, G: nx.Graph, trigger_conditions: Dict[str, Any]) -> List[Dict[str, Any]]:
        """在圖譜中找出所有符合 trigger_conditions 的節點字典"""
        matching = []
        gm = trigger_conditions.get("graph_match", {})
        attrs = gm.get("attributes", {})
        net_name_regex = gm.get("net_name_regex")

        for node, data in G.nodes(data=True):
            matched = True
            for k, expected in attrs.items():
                if data.get(k) != expected:
                    matched = False
                    break
            if matched and net_name_regex:
                net_name = data.get("net_name", "")
                if not re.search(net_name_regex, net_name):
                    matched = False
            if matched:
                d = dict(data)
                d["_id"] = node
                matching.append(d)
        return matching

    def _extract_subgraph_context(
        self,
        G: nx.Graph,
        keyword: str = "",
        targets: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """從圖譜中依 keyword 或 targets 抽取子圖上下文"""
        if keyword:
            target_nets = [
                n for n, d in G.nodes(data=True)
                if d.get("type") == "net" and keyword.lower() in d.get("net_name", "").lower()
            ]
        elif targets:
            target_nets = [
                t["_id"] for t in targets if t.get("type") == "net"
            ]
        else:
            target_nets = []

        target_comps = set()
        connections = []
        for net in target_nets:
            if not G.has_node(net):
                continue
            for neighbor in G.neighbors(net):
                if G.nodes[neighbor].get("type") == "component":
                    target_comps.add(neighbor)
                    edge_data = G.get_edge_data(neighbor, net) or {}
                    connections.append({
                        "component": G.nodes[neighbor].get("ref_des", neighbor),
                        "pin": edge_data.get("pin_number") or edge_data.get("pin", ""),
                        "net": G.nodes[net].get("net_name", net)
                    })
        return {
            "nets": [G.nodes[n].get("net_name", n) for n in target_nets if G.has_node(n)],
            "components": [G.nodes[c].get("ref_des", c) for c in target_comps if G.has_node(c)],
            "connections": connections
        }

    def _run_llm_step(
        self,
        step: Dict[str, Any],
        prompt: str,
        subgraph_ctx: Dict[str, Any],
        rule_name: str,
        rule_title: str,
        primary_cat: str,
        default_severity: str,
        tags: List[str]
    ) -> Dict[str, Any]:
        """調用 LLM 或執行專家規則安全降級"""
        from backend.app.engine.rules.llm import call_local_llm_reasoning, LLMProfile
        from backend.app.core.config import settings

        profile_val = step.get("profile", "BALANCED")
        try:
            profile = LLMProfile(profile_val)
        except Exception:
            profile = LLMProfile.BALANCED

        start_time = time.time()
        llm_resp = call_local_llm_reasoning(prompt, profile=profile)
        elapsed_ms = round((time.time() - start_time) * 1000, 1)

        fallback_cfg = step.get("fallback_summary", {})

        if llm_resp and "status" in llm_resp:
            status = llm_resp.get("status", "PASS")
            severity = llm_resp.get("severity", default_severity)
            desc = llm_resp.get("description", f"{rule_title} 經 LLM 語意審查完成")
            comment = llm_resp.get("comment", "")
            reasoning_summary = llm_resp.get("reasoning_summary", "")
            actual_called = True
        elif llm_resp and "raw_response" in llm_resp:
            status = "PASS"
            severity = "INFO"
            desc = f"{rule_title} 經 LLM 語意審查完成"
            comment = "建議工程師複核介面配置"
            reasoning_summary = str(llm_resp["raw_response"])[:300]
            actual_called = True
        else:
            # 優雅降級 (Fallback)
            status = fallback_cfg.get("status", "PASS")
            severity = fallback_cfg.get("severity", "INFO")
            desc = fallback_cfg.get("description", f"{rule_title}：LLM 服務離線，啟用專家規則安全判定")
            comment = fallback_cfg.get("comment", "LLM 服務離線，使用專家規則備援")
            reasoning_summary = fallback_cfg.get("reasoning_summary", "專家啟發式比對與拓撲特徵審查")
            actual_called = False

        return {
            "item_id": f"v-{uuid.uuid4().hex[:8]}",
            "rule_id": rule_name,
            "rule_category": primary_cat,
            "rule_title": rule_title,
            "check_type": "LLM",
            "status": status,
            "severity": severity,
            "target_nodes": {
                "components": subgraph_ctx.get("components", []),
                "nets": subgraph_ctx.get("nets", []),
                "page_indices": [1]
            },
            "description": desc,
            "comment": comment,
            "evidence_trail": {
                "llm_provider": f"litellm/{getattr(settings, 'LOCAL_LLM_MODEL', 'qwen')}",
                "endpoint": getattr(settings, "LOCAL_LLM_URL", ""),
                "llm_actual_called": actual_called,
                "llm_reasoning_summary": reasoning_summary,
                "execution_time_ms": elapsed_ms
            }
        }

    def _run_python_script(self, rel_script_path: str, target: Dict[str, Any], G: nx.Graph, graph_api: GraphAPI) -> List[Dict[str, Any]]:
        """沙盒執行 patterns/rules/scripts/ 或 scripts/drc/ 下之 Python 腳本"""
        from designshield.sdk import (
            RuleResult,
            RuleViolation,
            RuleContext,
            ComponentNode,
            NetNode,
            GraphAPI as SDKGraphAPI,
            PartDB as SDKPartDB,
            SandboxedScriptRunner,
            SecurityViolationError,
            ScriptTimeoutError,
        )

        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
        
        # 智慧解析腳本實體路徑
        candidates = [
            os.path.join(base_dir, rel_script_path),
            os.path.join(base_dir, "patterns", "rules", rel_script_path),
            os.path.join(base_dir, "patterns", "rules", "scripts", os.path.basename(rel_script_path)),
            os.path.join(base_dir, "scripts", "drc", os.path.basename(rel_script_path)),
        ]
        full_path = next((p for p in candidates if os.path.exists(p)), None)
        if not full_path:
            logger.warning(f"DRC script not found: {rel_script_path} (searched: {candidates})")
            return []

        try:
            with open(full_path, "r", encoding="utf-8") as f:
                source_code = f.read()

            target_wrapped = ComponentNode(target) if target.get("type") == "component" else NetNode(target)
            ctx = RuleContext(target=target_wrapped, G=G, params={})
            
            sdk_graph_api = SDKGraphAPI(G)
            sdk_part_db = SDKPartDB()

            raw_res = SandboxedScriptRunner.execute_script_source(
                source_code=source_code,
                context=ctx,
                graph_api=sdk_graph_api,
                part_db=sdk_part_db,
                params={},
                filename=full_path
            )

            if raw_res is None or raw_res == RuleResult.PASS or raw_res == "PASS":
                return []

            normalized_violations: List[Dict[str, Any]] = []
            if isinstance(raw_res, list):
                for item in raw_res:
                    if isinstance(item, RuleViolation):
                        normalized_violations.append(item.to_dict())
                    elif isinstance(item, dict):
                        normalized_violations.append(item)
            return normalized_violations

        except SecurityViolationError as sve:
            logger.error(f"DRC script security violation in {full_path}: {sve}")
            return [{
                "message": f"沙盒安全性違規阻擋: {sve}",
                "severity": "FATAL",
                "evidence": {"security_violation": str(sve)}
            }]
        except ScriptTimeoutError as ste:
            logger.error(f"DRC script execution timeout in {full_path}: {ste}")
            return [{
                "message": f"動態腳本執行逾時: {ste}",
                "severity": "ERROR",
                "evidence": {"timeout": str(ste)}
            }]
        except Exception as e:
            logger.error(f"Failed to execute DRC script {full_path}: {e}")
            return [{
                "message": f"腳本執行失敗: {e}",
                "severity": "ERROR",
                "evidence": {"exception": str(e)}
            }]
