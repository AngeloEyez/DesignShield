"""
四維度網路語意推斷與模糊 LLM 分類引擎 (Net Semantic Classifier & LLM Fallback)

提供與元件分類流程完全對齊的三層網路語意推斷架構：
1. Level 1 啟發式特徵推斷 (Heuristic & Global Power Symbols)
2. Level 2 TopologyPatternEngine (Power & Bus 規則匹配)
3. Level 3 微批次 LLM 語意補足 (針對無規則命中、命名含混但掛載 IC 引腳之模糊網路)
全程補足 DEBUG 等級結構化日誌與狀態詳情，支援離線與超時優雅降級。
"""

import re
import json
import logging
from typing import Dict, List, Any, Optional
import networkx as nx

from backend.app.core.task_logger import get_task_logger

logger = logging.getLogger("designshield.net_classifier")


def classify_single_net_heuristic(G: nx.Graph, net_node: str) -> Dict[str, Any]:
    """
    依據圖譜既有標記與啟發式特徵，評估單一網路之語意分類與信心度
    
    Returns:
        Dict: 包含 net_type, bus_type, functional_role, confidence, evidence
    """
    net_data = G.nodes[net_node]
    net_name = net_data.get("net_name", net_node.replace("net:", ""))
    
    is_pwr = bool(net_data.get("is_power", False))
    is_gnd = bool(net_data.get("is_ground", False))
    is_bus = bool(net_data.get("is_bus", False))
    bus_type = net_data.get("bus_type")
    is_pwr_sym = bool(net_data.get("is_power_symbol_connected", False))
    is_gnd_sym = bool(net_data.get("is_ground_symbol_connected", False))
    bus_conf = float(net_data.get("bus_confidence", 0.0))

    evidence = []

    # 0. 若圖譜已由 Level 2 拓撲規則命中 (如 Differential, Control, Clock, Analog, Bus 等)
    l2_net_type = net_data.get("net_type")
    l2_conf = float(net_data.get("confidence", 0.0))
    if l2_net_type and l2_conf >= 0.6 and not (is_pwr and is_gnd):
        return {
            "net_type": l2_net_type,
            "net_types": net_data.get("net_types", [l2_net_type]),
            "bus_type": bus_type,
            "functional_role": net_data.get("functional_role", "General_Signal"),
            "functional_roles": net_data.get("functional_roles", [net_data.get("functional_role", "General_Signal")]),
            "confidence": l2_conf,
            "evidence": list(net_data.get("evidence", [f"level2:{l2_net_type}"]))
        }

    # 0. 電源與接地雙重特性 (電氣衝突/短路異常)
    if is_pwr and is_gnd:
        if is_pwr_sym:
            evidence.append("symbol:Power")
        else:
            evidence.append("regex:Power")
        if is_gnd_sym:
            evidence.append("symbol:GND")
        else:
            evidence.append("regex:GND")
        evidence.append("conflict:power_ground_short")
        return {
            "net_type": "Power_GND_Conflict",
            "net_types": ["Power", "Ground"],
            "bus_type": bus_type,
            "functional_role": "Power_Ground_Short",
            "functional_roles": ["Power_Rail", "Reference_Ground"],
            "confidence": 1.0,
            "evidence": evidence
        }

    # 1. 接地網路
    if is_gnd:
        evidence.append("symbol:GND" if is_gnd_sym else "regex:GND")
        return {
            "net_type": "Ground",
            "net_types": ["Ground"],
            "bus_type": None,
            "functional_role": "Reference_Ground",
            "functional_roles": ["Reference_Ground"],
            "confidence": 1.0,
            "evidence": evidence
        }

    # 2. 電源網路
    if is_pwr:
        conf = 1.0 if is_pwr_sym else 0.95
        evidence.append("symbol:Power" if is_pwr_sym else "regex:Power")
        return {
            "net_type": "Power",
            "net_types": ["Power"],
            "bus_type": None,
            "functional_role": "Power_Rail",
            "functional_roles": ["Power_Rail"],
            "confidence": conf,
            "evidence": evidence
        }

    # 3. 匯流排
    if is_bus and bus_type:
        conf = max(0.9, bus_conf)
        evidence.append(f"bus_rule:{bus_type}")
        return {
            "net_type": "Bus",
            "net_types": ["Bus"],
            "bus_type": bus_type,
            "functional_role": "Single_Ended_Bus",
            "functional_roles": ["Single_Ended_Bus"],
            "confidence": conf,
            "evidence": evidence
        }

    # 4. 常見信號特徵簡易啟發式
    upper_name = net_name.upper()
    if re.search(r"(RESET|RST|NRST)", upper_name):
        return {
            "net_type": "Control",
            "net_types": ["Control"],
            "bus_type": None,
            "functional_role": "Reset",
            "functional_roles": ["Reset"],
            "confidence": 0.85,
            "evidence": ["regex:Reset"]
        }
    if re.search(r"(CLK|CLOCK|OSC|XTAL)", upper_name):
        return {
            "net_type": "Clock",
            "net_types": ["Clock"],
            "bus_type": None,
            "functional_role": "Clock",
            "functional_roles": ["Clock"],
            "confidence": 0.85,
            "evidence": ["regex:Clock"]
        }
    if re.search(r"(INT|IRQ|ALERT)", upper_name):
        return {
            "net_type": "Control",
            "net_types": ["Control"],
            "bus_type": None,
            "functional_role": "Interrupt",
            "functional_roles": ["Interrupt"],
            "confidence": 0.85,
            "evidence": ["regex:Interrupt"]
        }
    if re.search(r"(_EN|ENABLE|SHDN|SLEEP)", upper_name):
        return {
            "net_type": "Control",
            "net_types": ["Control"],
            "bus_type": None,
            "functional_role": "Enable",
            "functional_roles": ["Enable"],
            "confidence": 0.80,
            "evidence": ["regex:Enable"]
        }

    # 5. 未識別一般信號 (若未命中明確規則，初始信心度設為 0.3)
    return {
        "net_type": "Signal",
        "net_types": ["Signal"],
        "bus_type": None,
        "functional_role": "General_Signal",
        "functional_roles": ["General_Signal"],
        "confidence": 0.3,
        "evidence": ["default:heuristic_unclassified"]
    }


def classify_nets_batch(
    G: nx.Graph,
    enable_llm_fallback: bool = True,
    task_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    批次分類圖譜中所有網路，並對模糊網路發配微批次 LLM 語意推論：
    1. 執行啟發式與拓撲信心度評估
    2. 針對信心度低於 0.6 且連接主動元件 (IC/Connector/Discrete) 的模糊網路，彙整連接引腳並發起微批次 LiteLLM 推理
    3. 解析 LLM 回覆並回填更新 NetworkX 圖譜節點屬性
    4. 支援離線/逾時優雅降級與全鏈路結構化 Debug 日誌記錄
    """
    t_logger = get_task_logger(task_id) if task_id else None

    net_nodes = [n for n, d in G.nodes(data=True) if d.get("type") == "net"]
    ambiguous_items: List[Dict[str, Any]] = []

    if t_logger:
        t_logger.debug(
            "PARSE_AND_GRAPH",
            "PARSER",
            f"開始對圖譜中 {len(net_nodes)} 條網路進行語意特徵掃描與信心度計算...",
            details={"total_nets_to_scan": len(net_nodes)}
        )

    for net_node in net_nodes:
        net_data = G.nodes[net_node]
        net_name = net_data.get("net_name", net_node.replace("net:", ""))

        heur = classify_single_net_heuristic(G, net_node)
        
        # 回填基本屬性 (若已有更高等級標記則不覆寫)
        if "functional_role" not in net_data or not net_data.get("functional_role"):
            net_data["functional_role"] = heur["functional_role"]
        if "functional_roles" not in net_data:
            net_data["functional_roles"] = heur.get("functional_roles", [heur["functional_role"]])
        if "net_type" not in net_data or not net_data.get("net_type"):
            net_data["net_type"] = heur["net_type"]
        if "net_types" not in net_data:
            net_data["net_types"] = heur.get("net_types", [heur["net_type"]])
        if "confidence" not in net_data:
            net_data["confidence"] = heur["confidence"]
        if "evidence" not in net_data:
            net_data["evidence"] = list(heur["evidence"])

        # 檢查是否為模糊網路：信心度 < 0.6，且非明確電源/接地/匯流排
        if net_data.get("confidence", 0.0) < 0.6 and not net_data.get("is_power") and not net_data.get("is_ground") and not net_data.get("bus_type"):
            # 收集該網路周邊掛載之元件與引腳上下文
            connected_pins = []
            has_active_comp = False

            for neighbor in G.neighbors(net_node):
                comp_data = G.nodes[neighbor]
                if comp_data.get("type") == "component":
                    cat = comp_data.get("category", "")
                    if cat in ["IC", "Discrete", "Connector"]:
                        has_active_comp = True
                    edge_data = G.get_edge_data(neighbor, net_node) or {}
                    connected_pins.append({
                        "ref_des": comp_data.get("ref_des", neighbor.replace("comp:", "")),
                        "part_value": comp_data.get("part_value", ""),
                        "category": cat,
                        "pin_number": edge_data.get("pin_number", ""),
                        "pin_name": edge_data.get("pin_name", "")
                    })

            # 若連接主動元件或有效引腳連線 >= 2 處，列入模糊需推論清單 (排除單一孤立測試點或浮接線)
            if has_active_comp or len(connected_pins) >= 2:
                ambiguous_items.append({
                    "net_name": net_name,
                    "net_node": net_node,
                    "connected_pins": connected_pins,
                    "is_power_symbol_connected": bool(net_data.get("is_power_symbol_connected", False))
                })

    # 若發現模糊網路且允許 LLM 補足，發起微批次查詢
    if enable_llm_fallback and ambiguous_items:
        logger.info("[NetClassifier] Found %d ambiguous nets, attempting batch LLM categorization...", len(ambiguous_items))
        if t_logger:
            t_logger.warning(
                "PARSE_AND_GRAPH",
                "LLM",
                f"發現 {len(ambiguous_items)} 條命名模糊或無規則命中之網路，發起微批次 LLM 拓撲語意識別",
                details={
                    "total_ambiguous_nets": len(ambiguous_items),
                    "ambiguous_sample": [item["net_name"] for item in ambiguous_items[:20]]
                }
            )

        try:
            from backend.app.engine.rules.llm import call_litellm_completion, LLMProfile

            # 微批次切分 (每批 15 條網路)，避免引腳資訊長度爆表並降低超時風險
            CHUNK_SIZE = 15
            total_chunks = (len(ambiguous_items) + CHUNK_SIZE - 1) // CHUNK_SIZE
            total_resolved = 0

            for chunk_idx in range(0, len(ambiguous_items), CHUNK_SIZE):
                chunk = ambiguous_items[chunk_idx:chunk_idx + CHUNK_SIZE]
                chunk_num = (chunk_idx // CHUNK_SIZE) + 1

                # 準備發送給 LLM 的輕量精準 prompt 資料
                llm_input_items = []
                for item in chunk:
                    llm_input_items.append({
                        "net_name": item["net_name"],
                        "connected_pins": item["connected_pins"],
                        "is_power_symbol": item["is_power_symbol_connected"]
                    })

                prompt = (
                    "You are an expert electronics hardware design engineer. Analyze the following ambiguous PCB nets "
                    "based on their net names and connected IC pin names/components, then classify their electrical roles.\n"
                    "Return ONLY a valid JSON list of objects matching this schema:\n"
                    "[\n"
                    "  {\n"
                    "    \"net_name\": string,\n"
                    "    \"net_type\": \"Power\" | \"Ground\" | \"Bus\" | \"Control\" | \"Clock\" | \"Analog\" | \"Differential\" | \"Signal\",\n"
                    "    \"bus_type\": \"I2C\" | \"SPI\" | \"UART\" | \"USB\" | \"CAN\" | \"Ethernet\" | \"MIPI\" | \"JTAG\" | null,\n"
                    "    \"operating_voltage\": number | null,\n"
                    "    \"functional_role\": \"Power_Rail\" | \"Reference_Ground\" | \"High_Speed_Differential\" | \"Single_Ended_Bus\" | \"Interrupt\" | \"Reset\" | \"Enable\" | \"Clock\" | \"General_Signal\",\n"
                    "    \"confidence\": number (0.0 to 1.0)\n"
                    "  }\n"
                    "]\n"
                    "Strict rules:\n"
                    "1. If IC pins indicate an I2C/SPI/UART/USB bus (e.g. SCL/SDA, MOSI/MISO, TX/RX, DP/DM), assign the correct bus_type.\n"
                    "2. If net delivers power to VDD/VCC pins, classify as 'Power' and estimate voltage if possible.\n"
                    "3. If insufficient evidence, default to net_type 'Signal', bus_type null, functional_role 'General_Signal', confidence 0.5.\n\n"
                    f"Nets to classify:\n{json.dumps(llm_input_items, ensure_ascii=False, indent=2)}"
                )

                if t_logger:
                    t_logger.debug(
                        "PARSE_AND_GRAPH",
                        "LLM",
                        f"向 LLM 發送提示詞進行網路語意識別 (批次 {chunk_num}/{total_chunks}，共 {len(chunk)} 條網路)",
                        details={
                            "profile": "FAST (thinking disabled, temp 0.0)",
                            "timeout": 600.0,
                            "chunk_num": chunk_num,
                            "total_chunks": total_chunks,
                            "sample_nets": [it["net_name"] for it in chunk],
                            "prompt": prompt
                        }
                    )

                response = call_litellm_completion(prompt=prompt, timeout=600.0, max_tokens=4000, profile=LLMProfile.FAST)
                if response and "choices" in response:
                    msg = response["choices"][0]["message"]
                    content = (getattr(msg, "content", None) or (msg.get("content") if isinstance(msg, dict) else None) or "").strip()
                    reasoning = (getattr(msg, "reasoning_content", None) or getattr(msg, "reasoning", None) or (msg.get("reasoning_content") if isinstance(msg, dict) else None) or "").strip()
                    if not content and reasoning:
                        content = reasoning

                    if t_logger:
                        t_logger.debug(
                            "PARSE_AND_GRAPH",
                            "LLM",
                            f"收到 LLM 原始回覆字串 (批次 {chunk_num}/{total_chunks})",
                            details={"raw_response": content, "has_reasoning": bool(reasoning)}
                        )

                    json_match = re.search(r"\[\s*\{.*\}\s*\]", content, re.DOTALL)
                    if json_match:
                        try:
                            items = json.loads(json_match.group(0))
                            chunk_map = {item["net_name"]: item["net_node"] for item in chunk}
                            resolved_this_chunk = 0

                            for item in items:
                                net_nm = item.get("net_name")
                                if net_nm in chunk_map:
                                    n_node = chunk_map[net_nm]
                                    nd = G.nodes[n_node]
                                    net_t = item.get("net_type", "Signal")
                                    bus_t = item.get("bus_type")
                                    v_est = item.get("operating_voltage")
                                    f_role = item.get("functional_role", "General_Signal")
                                    conf = float(item.get("confidence", 0.85))

                                    if net_t == "Power":
                                        nd["is_power"] = True
                                    elif net_t == "Ground":
                                        nd["is_ground"] = True
                                    elif net_t == "Bus" and bus_t:
                                        nd["is_bus"] = True
                                        nd["bus_type"] = bus_t

                                    if v_est is not None:
                                        nd["operating_voltage"] = float(v_est)

                                    nd["functional_role"] = f_role
                                    nd["confidence"] = conf
                                    if "evidence" not in nd:
                                        nd["evidence"] = []
                                    nd["evidence"].append("llm_net_semantic_inference")
                                    resolved_this_chunk += 1

                            total_resolved += resolved_this_chunk
                            logger.info("[NetClassifier] Successfully resolved %d ambiguous nets in chunk %d/%d via batch LLM.", resolved_this_chunk, chunk_num, total_chunks)
                            if t_logger:
                                t_logger.debug(
                                    "PARSE_AND_GRAPH",
                                    "LLM",
                                    f"LLM 網路批次分類回覆成功 (批次 {chunk_num}/{total_chunks})，成功標註 {resolved_this_chunk} 條網路語意",
                                    details={"parsed_items": items}
                                )
                        except json.JSONDecodeError as je:
                            logger.error("[NetClassifier] LLM response JSON decode error (chunk %d/%d): %s", chunk_num, total_chunks, je)
                            if t_logger:
                                t_logger.warning(
                                    "PARSE_AND_GRAPH",
                                    "LLM",
                                    f"LLM 回覆之 JSON 格式錯誤，無法解析 (批次 {chunk_num}/{total_chunks})",
                                    details={"error": str(je), "matched_string": json_match.group(0)}
                                )
                    else:
                        logger.warning("[NetClassifier] Could not find JSON array in LLM response (chunk %d/%d).", chunk_num, total_chunks)
                        if t_logger:
                            t_logger.warning(
                                "PARSE_AND_GRAPH",
                                "LLM",
                                f"無法從 LLM 回覆中提取 JSON 陣列結構 (批次 {chunk_num}/{total_chunks})",
                                details={"raw_content": content}
                            )
                else:
                    logger.warning("[NetClassifier] Invalid or empty response from LLM (chunk %d/%d).", chunk_num, total_chunks)
                    if t_logger:
                        t_logger.warning(
                            "PARSE_AND_GRAPH",
                            "LLM",
                            f"LLM 回覆為空或結構無效 (批次 {chunk_num}/{total_chunks})",
                            details={"response_obj": str(response)}
                        )

            if t_logger:
                t_logger.info(
                    "PARSE_AND_GRAPH",
                    "LLM",
                    f"LLM 模糊網路語意識別完成，共成功標註 {total_resolved}/{len(ambiguous_items)} 條網路",
                    details={"total_resolved": total_resolved, "total_ambiguous": len(ambiguous_items)}
                )
        except Exception as e:
            logger.warning("[NetClassifier] Batch LLM net inference unavailable or failed (%s). Gracefully falling back to heuristic.", e)
            if t_logger:
                t_logger.warning(
                    "PARSE_AND_GRAPH",
                    "LLM",
                    f"LLM 網路批次分類連線失敗或逾時 ({str(e)[:60]})，優雅降級為啟發式結果",
                    details={"error": str(e)}
                )
    elif t_logger and not ambiguous_items:
        t_logger.debug(
            "PARSE_AND_GRAPH",
            "PARSER",
            f"所有網路均已透過規則與拓撲完全識別 (共 {len(net_nodes)} 條)，無需呼叫 LLM 進行模糊分類",
            details={"total_nets": len(net_nodes)}
        )

    # 最終統計與日誌
    final_pwr = len([n for n, d in G.nodes(data=True) if d.get("type") == "net" and d.get("is_power")])
    final_gnd = len([n for n, d in G.nodes(data=True) if d.get("type") == "net" and d.get("is_ground")])
    final_bus = len([n for n, d in G.nodes(data=True) if d.get("type") == "net" and d.get("bus_type")])

    if t_logger:
        t_logger.debug(
            "PARSE_AND_GRAPH",
            "GRAPH",
            f"網路全維度語意分類完成: 總網路 {len(net_nodes)} 條 (電源線 {final_pwr} 條, 接地線 {final_gnd} 條, 匯流排 {final_bus} 條)",
            details={
                "total_nets": len(net_nodes),
                "power_nets": final_pwr,
                "ground_nets": final_gnd,
                "bus_nets": final_bus,
                "ambiguous_count": len(ambiguous_items)
            }
        )

    return {
        "total_nets": len(net_nodes),
        "power_nets": final_pwr,
        "ground_nets": final_gnd,
        "bus_nets": final_bus,
        "ambiguous_nets_count": len(ambiguous_items)
    }
