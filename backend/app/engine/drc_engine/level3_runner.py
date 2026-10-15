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

class Level3Engine:
    """
    Level 3 DRC 混合執行引擎
    
    具備高效分流能力：
    - run_heuristic_checks: 毫秒級執行 topology_check 與沙盒 python_script
    - run_llm_checks: 執行非同步 llm_agent 語意推理與優雅降級
    """

    def __init__(self, pattern_service: Optional[PatternService] = None):
        self.pattern_svc = pattern_service or PatternService.get_instance()

    async def run_heuristic_checks(self, G: nx.Graph, selected_rule_ids: List[str]) -> List[Dict[str, Any]]:
        """
        非同步執行選定規則中的傳統啟發式與拓撲比對（topology_check, python_script）
        """
        return await self._execute_rules(G, selected_rule_ids, allowed_types={"topology_check", "python_script"})

    async def run_llm_checks(
        self,
        G: nx.Graph,
        selected_rule_ids: List[str],
        progress_callback: Optional[Any] = None
    ) -> List[Dict[str, Any]]:
        """
        非同步執行選定規則中的大語言模型邏輯推理檢測（llm_agent，純協程無阻塞）
        """
        return await self._execute_rules(
            G,
            selected_rule_ids,
            allowed_types={"llm_agent"},
            progress_callback=progress_callback
        )

    async def run_checks(self, G: nx.Graph, selected_rule_ids: List[str]) -> List[Dict[str, Any]]:
        """
        全域檢查入口（執行所有選定規則步驟）
        """
        return await self._execute_rules(
            G,
            selected_rule_ids,
            allowed_types={"topology_check", "python_script", "llm_agent"}
        )

    async def _execute_rules(
        self,
        G: nx.Graph,
        selected_rule_ids: List[str],
        allowed_types: Set[str],
        progress_callback: Optional[Any] = None
    ) -> List[Dict[str, Any]]:
        """
        非同步通用規則執行調度器
        """
        findings: List[Dict[str, Any]] = []
        graph_api = GraphAPI(G)
        evaluator = TopologyEvaluator(G, graph_api)

        all_l3_rules = self.pattern_svc.get_level3_rules()
        rule_by_name = {r.get("name"): r for r in all_l3_rules if r.get("name")}

        # 按照使用者傳入的 selected_rule_ids 順序挑選候選規則 (單軌小寫蛇形精準匹配)
        candidate_rules = []
        seen_rules = set()

        for req_id in selected_rule_ids:
            rule = rule_by_name.get(req_id)
            if not rule:
                logger.warning("未知的 Level 3 規則 ID: %s", req_id)
                continue

            if rule.get("enabled", True) is False:
                logger.info("規則 %s 已停用 (enabled: false)，跳過執行", req_id)
                continue

            r_name = rule.get("name")
            if r_name in seen_rules:
                continue
            seen_rules.add(r_name)

            check_logics = rule.get("check_logic", [])
            if isinstance(check_logics, dict):
                check_logics = [check_logics]

            matching_steps = [s for s in check_logics if s.get("type") in allowed_types]
            if matching_steps:
                candidate_rules.append((rule, matching_steps, r_name))

        total_rules = len(candidate_rules)

        for idx, (rule, active_steps, requested_id) in enumerate(candidate_rules, start=1):
            r_name = rule.get("name")
            output_rule_id = r_name
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

            # 若無目標節點，視為 SKIPPED (未觸發)
            if not targets:
                check_type_label = "LLM" if any(s.get("type") == "llm_agent" for s in active_steps) else "LEVEL3_TOPOLOGY"
                findings.append({
                    "item_id": f"v-{uuid.uuid4().hex[:8]}",
                    "rule_id": output_rule_id,
                    "rule_category": primary_cat,
                    "rule_title": r_title,
                    "check_type": check_type_label,
                    "status": "SKIPPED",
                    "severity": "INFO",
                    "target_nodes": {"components": [], "nets": []},
                    "error_message": "",
                    "recommendation": "",
                    "evidence_trail": {"trigger_matched": False}
                })
                if progress_callback:
                    try:
                        progress_callback(idx, total_rules, output_rule_id, r_title, "DONE")
                    except Exception as pe:
                        logger.warning("進度回呼通知失敗 (DONE): %s", pe)
                continue

            rule_rec = rule.get("recommendation", "")

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
                                err_msg = res.get("error_message") or res.get("message", "拓撲斷言失敗")
                                rec_msg = res.get("recommendation") or rule_rec
                                findings.append({
                                    "item_id": f"v-{uuid.uuid4().hex[:8]}",
                                    "rule_id": output_rule_id,
                                    "rule_category": primary_cat,
                                    "rule_title": r_title,
                                    "check_type": "LEVEL3_TOPOLOGY",
                                    "status": "FAIL",
                                    "severity": severity,
                                    "target_nodes": {"components": target_components, "nets": target_nets},
                                    "error_message": err_msg,
                                    "recommendation": rec_msg,
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
                                "error_message": "",
                                "recommendation": rule_rec,
                                "evidence_trail": {"checked_target": target_id}
                            })

                # 模式 B: PartDB Python 腳本查表與動態拓撲檢查
                elif step_type == "python_script":
                    script_path = step.get("script_path", "")
                    visited_channel_targets = set()

                    for target in targets:
                        target_id = target.get("_id", target.get("net_name", target.get("ref_des", "")))
                        target_net_name = target.get("net_name", "")

                        # 通道網段靜默去重：若該網段已在先前的端到端通道審計中被涵蓋，靜默略過，不重複堆疊
                        if (target_id in visited_channel_targets) or (target_net_name and target_net_name in visited_channel_targets):
                            continue

                        target_components = [target.get("ref_des")] if target.get("type") == "component" else []
                        target_nets = [target.get("net_name")] if target.get("type") == "net" else []

                        script_res = self._run_python_script(script_path, target, G, graph_api)

                        # 收集伴生腳本宣告已涵蓋之全通道網段清單 (covered_nets)，納入已訪問集合
                        covered_list = list(script_res.get("evidence", {}).get("covered_nets") or [])
                        if not covered_list and script_res.get("violations"):
                            for sv in script_res["violations"]:
                                cn = sv.get("evidence", {}).get("covered_nets")
                                if cn:
                                    covered_list.extend(cn)
                            covered_list = list(dict.fromkeys(covered_list))

                        for c_net in covered_list:
                            visited_channel_targets.add(c_net)
                            visited_channel_targets.add(f"net:{c_net}")
                        
                        if script_res["status"] == "FAIL":
                            for sv in script_res["violations"]:
                                err_msg = sv.get("error_message") or sv.get("message", "PartDB 特規不符")
                                rec_msg = sv.get("recommendation") or rule_rec
                                sv_tn = sv.get("target_nodes") or {}
                                tn_components = sv_tn.get("components", target_components)
                                tn_nets = sv_tn.get("nets", target_nets)
                                findings.append({
                                    "item_id": f"v-{uuid.uuid4().hex[:8]}",
                                    "rule_id": output_rule_id,
                                    "rule_category": primary_cat,
                                    "rule_title": r_title,
                                    "check_type": "LEVEL3_PARTDB",
                                    "status": "FAIL",
                                    "severity": sv.get("severity", severity),
                                    "target_nodes": {"components": tn_components, "nets": tn_nets},
                                    "error_message": err_msg,
                                    "recommendation": rec_msg,
                                    "evidence_trail": sv.get("evidence", {}),
                                    "_meta": sv.get("evidence", {})
                                })
                        elif script_res["status"] == "SKIPPED":
                            findings.append({
                                "item_id": f"v-{uuid.uuid4().hex[:8]}",
                                "rule_id": output_rule_id,
                                "rule_category": primary_cat,
                                "rule_title": r_title,
                                "check_type": "LEVEL3_PARTDB",
                                "status": "SKIPPED",
                                "severity": "INFO",
                                "target_nodes": {"components": target_components, "nets": target_nets},
                                "error_message": "",
                                "recommendation": "",
                                "evidence_trail": script_res.get("evidence") or {"checked_target": target_id, "skipped": True}
                            })
                        else:
                            # 判定 PASS：合併腳本回傳之額外目標節點與結構化審計證據
                            extra_tn = script_res.get("target_nodes") or {}
                            merged_components = list(dict.fromkeys(target_components + extra_tn.get("components", [])))
                            merged_nets = list(dict.fromkeys(target_nets + extra_tn.get("nets", [])))

                            evidence = script_res.get("evidence") or {}
                            if not evidence:
                                evidence = {"checked_target": target_id}
                            elif "checked_target" not in evidence:
                                evidence["checked_target"] = target_id

                            findings.append({
                                "item_id": f"v-{uuid.uuid4().hex[:8]}",
                                "rule_id": output_rule_id,
                                "rule_category": primary_cat,
                                "rule_title": r_title,
                                "check_type": "LEVEL3_PARTDB",
                                "status": "PASS",
                                "severity": "INFO",
                                "target_nodes": {"components": merged_components, "nets": merged_nets},
                                "error_message": "",
                                "recommendation": rule_rec,
                                "evidence_trail": evidence
                            })

                # 模式 C: LLM Agent 語意邏輯推理
                elif step_type == "llm_agent":
                    keyword = step.get("context_extraction", {}).get("keyword", "")
                    subgraph_ctx = self._extract_subgraph_context(G, keyword=keyword, targets=targets)
                    prompt_template = step.get("agent_prompt", "")
                    subgraph_json_str = json.dumps(subgraph_ctx, ensure_ascii=False)
                    prompt = prompt_template.replace("${context.subgraph}", subgraph_json_str)

                    llm_finding = await self._run_llm_step(
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

    async def _run_llm_step(
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
        """非同步調用 LLM 或執行專家規則安全降級"""
        from backend.app.engine.rules.llm import call_local_llm_reasoning, LLMProfile
        from backend.app.core.config import settings

        profile_val = step.get("profile", "BALANCED")
        try:
            profile = LLMProfile(profile_val)
        except Exception:
            profile = LLMProfile.BALANCED

        start_time = time.time()
        # 純非同步協程呼叫，釋放主執行緒
        llm_resp = await call_local_llm_reasoning(prompt, profile=profile)
        elapsed_ms = round((time.time() - start_time) * 1000, 1)

        fallback_cfg = step.get("fallback_summary", {})

        if llm_resp and "status" in llm_resp:
            status = llm_resp.get("status", "PASS")
            severity = llm_resp.get("severity", default_severity)
            raw_err = llm_resp.get("error_message") or llm_resp.get("description", "")
            error_message = "" if status in ("PASS", "SKIPPED") else raw_err
            recommendation = llm_resp.get("recommendation") or llm_resp.get("comment", "")
            reasoning_summary = llm_resp.get("reasoning_summary", "")
            actual_called = True
        elif llm_resp and "raw_response" in llm_resp:
            status = "PASS"
            severity = "INFO"
            error_message = ""
            recommendation = "建議工程師複核介面配置"
            reasoning_summary = str(llm_resp["raw_response"])[:300]
            actual_called = True
        else:
            # 優雅降級 (Fallback)
            status = fallback_cfg.get("status", "PASS")
            severity = fallback_cfg.get("severity", "INFO")
            raw_err = fallback_cfg.get("error_message") or fallback_cfg.get("description", "")
            error_message = "" if status in ("PASS", "SKIPPED") else raw_err
            recommendation = fallback_cfg.get("recommendation") or fallback_cfg.get("comment", "LLM 服務離線，使用專家規則備援")
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
            "error_message": error_message,
            "recommendation": recommendation,
            "evidence_trail": {
                "llm_provider": f"litellm/{getattr(settings, 'LOCAL_LLM_MODEL', 'qwen')}",
                "endpoint": getattr(settings, "LOCAL_LLM_URL", ""),
                "llm_actual_called": actual_called,
                "llm_reasoning_summary": reasoning_summary,
                "execution_time_ms": elapsed_ms
            }
        }

    def _run_python_script(self, rel_script_path: str, target: Dict[str, Any], G: nx.Graph, graph_api: GraphAPI) -> Dict[str, Any]:
        """沙盒執行 patterns/rules/ 或伴生之 Python 腳本並回傳統一審計結果字典"""
        from designshield.sdk import (
            RuleResult,
            RulePass,
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
        
        # 智慧解析腳本實體路徑 (支援同目錄同檔名伴生腳本與子目錄)
        candidates = [
            rel_script_path if os.path.isabs(rel_script_path) else os.path.join(base_dir, rel_script_path),
            os.path.join(base_dir, "patterns", "rules", rel_script_path),
            os.path.join(base_dir, "patterns", "rules", "interfaces", os.path.basename(rel_script_path)),
            os.path.join(base_dir, "patterns", "rules", "power", os.path.basename(rel_script_path)),
        ]
        full_path = next((p for p in candidates if os.path.exists(p)), None)
        if not full_path:
            # 遞迴搜尋 patterns/rules/ 下同名檔案
            for root, _, files in os.walk(os.path.join(base_dir, "patterns", "rules")):
                if os.path.basename(rel_script_path) in files:
                    full_path = os.path.join(root, os.path.basename(rel_script_path))
                    break
        if not full_path:
            logger.warning(f"DRC script not found: {rel_script_path} (searched: {candidates})")
            return {
                "status": "PASS",
                "violations": [],
                "evidence": {"warning": f"Script not found: {rel_script_path}"},
                "message": "",
                "target_nodes": None
            }

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

            # 1. 支援新型態 RulePass (審計合格物件)
            if isinstance(raw_res, RulePass):
                return {
                    "status": "PASS",
                    "violations": [],
                    "evidence": raw_res.evidence,
                    "message": raw_res.message,
                    "target_nodes": raw_res.target_nodes
                }

            # 2. 傳統 PASS 狀態
            if raw_res is None or raw_res == RuleResult.PASS or raw_res == "PASS":
                return {
                    "status": "PASS",
                    "violations": [],
                    "evidence": {},
                    "message": "",
                    "target_nodes": None
                }

            # 3. 支援 SKIPPED 狀態
            if raw_res == RuleResult.SKIPPED or raw_res == "SKIPPED":
                return {
                    "status": "SKIPPED",
                    "violations": [],
                    "evidence": {"skipped": True},
                    "message": "",
                    "target_nodes": None
                }

            # 4. 單一違規物件
            if isinstance(raw_res, RuleViolation):
                return {
                    "status": "FAIL",
                    "violations": [raw_res.to_dict()],
                    "evidence": raw_res.evidence,
                    "message": raw_res.error_message,
                    "target_nodes": raw_res.target_nodes
                }

            # 5. 違規物件列表
            normalized_violations: List[Dict[str, Any]] = []
            if isinstance(raw_res, list):
                for item in raw_res:
                    if isinstance(item, RuleViolation):
                        normalized_violations.append(item.to_dict())
                    elif isinstance(item, dict):
                        normalized_violations.append(item)

                if normalized_violations:
                    return {
                        "status": "FAIL",
                        "violations": normalized_violations,
                        "evidence": normalized_violations[0].get("evidence", {}),
                        "message": normalized_violations[0].get("error_message", ""),
                        "target_nodes": normalized_violations[0].get("target_nodes")
                    }

            return {
                "status": "PASS",
                "violations": [],
                "evidence": {},
                "message": "",
                "target_nodes": None
            }

        except SecurityViolationError as sve:
            logger.error(f"DRC script security violation in {full_path}: {sve}")
            return {
                "status": "FAIL",
                "violations": [{
                    "error_message": f"沙盒安全性違規阻擋: {sve}",
                    "message": f"沙盒安全性違規阻擋: {sve}",
                    "recommendation": "請檢查伴生腳本程式碼，避免調用未授權之系統或 I/O 模組",
                    "severity": "FATAL",
                    "evidence": {"security_violation": str(sve)}
                }],
                "evidence": {"security_violation": str(sve)},
                "message": str(sve),
                "target_nodes": None
            }
        except ScriptTimeoutError as ste:
            logger.error(f"DRC script execution timeout in {full_path}: {ste}")
            return {
                "status": "FAIL",
                "violations": [{
                    "error_message": f"動態腳本執行逾時: {ste}",
                    "message": f"動態腳本執行逾時: {ste}",
                    "recommendation": "請優化伴生腳本演算法複雜度，避免耗時過長",
                    "severity": "ERROR",
                    "evidence": {"timeout": str(ste)}
                }],
                "evidence": {"timeout": str(ste)},
                "message": str(ste),
                "target_nodes": None
            }
        except Exception as e:
            logger.error(f"Failed to execute DRC script {full_path}: {e}")
            return {
                "status": "FAIL",
                "violations": [{
                    "error_message": f"腳本執行失敗: {e}",
                    "message": f"腳本執行失敗: {e}",
                    "recommendation": "請檢查伴生腳本語法邏輯與輸入參數型別",
                    "severity": "ERROR",
                    "evidence": {"exception": str(e)}
                }],
                "evidence": {"exception": str(e)},
                "message": str(e),
                "target_nodes": None
            }
