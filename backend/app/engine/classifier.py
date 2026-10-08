"""
四維度元件分類與語意推斷引擎 (Multi-Dimensional Component Classifier)
- Phase 1: Pattern Engine 實作 (Level 1)
依據 YAML 規則引擎與 Cadence OrCAD XML 元數據進行分類：
1. 實體類別 (category): IC, Passive, Discrete, Connector, Electromechanical, NonElectrical
2. 細部類型 (sub_category): Resistor, Capacitor, Inductor, TVS, MOSFET, Crystal, TestPoint, Fiducial 等
3. 拓撲角色 (functional_role): Bus_Master, Bus_Slave, Power_Source, Level_Shifter, Protection, Filter, None
4. 電氣標籤 (is_electrical): True / False (機構件、對位點與測試點隔離)
支援批次 LLM 模糊推斷與離線優雅降級。
"""

import re
import json
import logging
from typing import Dict, List, Any, Optional

from backend.app.engine.pattern_engine import get_component_engine

logger = logging.getLogger("designshield.classifier")


def classify_single_component_heuristic(
    ref: str,
    val: str = "",
    desc: str = "",
    package: str = "",
    mfg_pn: str = "",
    pins_count: int = 0
) -> Dict[str, Any]:
    """
    根據元數據與 YAML 規則引擎推斷單一元件的四維度分類
    
    Returns:
        Dict: 包含 category, sub_category, functional_role, is_electrical, confidence, evidence
    """
    engine = get_component_engine()
    assign_dict, rule_name = engine.classify(
        ref_des=ref,
        part_value=val,
        description=desc,
        package=package,
        mfg_pn=mfg_pn,
        pins_count=pins_count
    )
    
    assign_dict["evidence"] = [f"rule:{rule_name}"]
    return assign_dict


def classify_components_batch(
    components_raw: Dict[str, Dict[str, Any]],
    enable_llm_fallback: bool = True,
    task_id: Optional[str] = None
) -> Dict[str, Dict[str, Any]]:
    """
    批次分類所有元件：
    1. 執行規則推斷與非電氣件白名單過濾
    2. 針對信心度低於 0.6 且具電氣引腳的模糊元件，整批彙整呼叫 LiteLLM 結構化推斷
    3. 若 LLM 離線、逾時或未配置 Key，優雅降級並記錄警告日誌
    """
    from backend.app.core.task_logger import get_task_logger
    t_logger = get_task_logger(task_id) if task_id else None

    classified: Dict[str, Dict[str, Any]] = {}
    ambiguous_items: List[Dict[str, Any]] = []

    for ref, c in components_raw.items():
        val = c.get("part_value", "")
        desc = c.get("description", "")
        pkg = c.get("package", "")
        mfg_pn = c.get("mfg_pn", "")
        pins = c.get("pins", [])
        pins_count = len(pins)

        res = classify_single_component_heuristic(
            ref=ref,
            val=val,
            desc=desc,
            package=pkg,
            mfg_pn=mfg_pn,
            pins_count=pins_count
        )

        classified[ref] = {**c, **res}

        # 若信心度過低且為多引腳潛在主動元件，列入批次清單
        if res["confidence"] < 0.6 and res["is_electrical"]:
            ambiguous_items.append({
                "ref_des": ref,
                "part_value": val,
                "description": desc,
                "package": pkg,
                "mfg_pn": mfg_pn,
                "pins_count": pins_count
            })

    # 若需要且有模糊元件，嘗試批次呼叫 LiteLLM
    if enable_llm_fallback and ambiguous_items:
        logger.info("[Classifier] Found %d ambiguous components, attempting batch LLM categorization...", len(ambiguous_items))
        if t_logger:
            t_logger.warning(
                "PARSE_AND_GRAPH",
                "LLM",
                f"發現 {len(ambiguous_items)} 個模糊元件屬性無法確定，發起微批次 LLM 語意查詢",
                details={"ambiguous_components": [i["ref_des"] for i in ambiguous_items]}
            )
        try:
            from backend.app.engine.rules.llm import call_litellm_completion, LLMProfile

            # 微批次切分 (每批 20 個元件)，避免單一 Prompt/Output Token 爆表並隔離超時風險
            CHUNK_SIZE = 20
            total_chunks = (len(ambiguous_items) + CHUNK_SIZE - 1) // CHUNK_SIZE
            total_resolved = 0

            for chunk_idx in range(0, len(ambiguous_items), CHUNK_SIZE):
                chunk = ambiguous_items[chunk_idx:chunk_idx + CHUNK_SIZE]
                chunk_num = (chunk_idx // CHUNK_SIZE) + 1

                prompt = (
                    "You are an expert electronics hardware engineer. Categorize the following electronic components into standard schemas.\n"
                    "Return ONLY a valid JSON list of objects matching this schema:\n"
                    "[\n"
                    "  {\n"
                    "    \"ref_des\": string,\n"
                    "    \"category\": \"IC\" | \"Passive\" | \"Discrete\" | \"Connector\" | \"Electromechanical\" | \"NonElectrical\",\n"
                    "    \"sub_category\": string (e.g. Capacitor, Resistor, Inductor, TVS, MOSFET, Crystal, PowerIC, LevelShifter, Microcontroller, Memory, etc.),\n"
                    "    \"functional_role\": \"Bus_Master\" | \"Bus_Slave\" | \"Power_Source\" | \"Power_Sink\" | \"Level_Shifter\" | \"Protection\" | \"Filter\" | \"None\",\n"
                    "    \"is_electrical\": boolean\n"
                    "  }\n"
                    "]\n"
                    "Strict rule: No evidence, no assertion. If unknown, use functional_role 'None'.\n\n"
                    f"Components to categorize:\n{json.dumps(chunk, ensure_ascii=False, indent=2)}"
                )

                if t_logger:
                    t_logger.debug(
                        "PARSE_AND_GRAPH",
                        "LLM",
                        f"向 LLM 發送提示詞進行元件語意識別 (批次 {chunk_num}/{total_chunks}，共 {len(chunk)} 個元件)",
                        details={
                            "model": "default (configured in llm.py)",
                            "profile": "FAST (thinking disabled, temp 0.0)",
                            "timeout": 600.0,
                            "chunk_num": chunk_num,
                            "total_chunks": total_chunks,
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

                    # 提取 JSON 區塊
                    json_match = re.search(r"\[\s*\{.*\}\s*\]", content, re.DOTALL)
                    if json_match:
                        try:
                            items = json.loads(json_match.group(0))
                            for item in items:
                                r = item.get("ref_des")
                                if r in classified:
                                    classified[r]["category"] = item.get("category", classified[r]["category"])
                                    classified[r]["sub_category"] = item.get("sub_category", classified[r]["sub_category"])
                                    classified[r]["functional_role"] = item.get("functional_role", classified[r]["functional_role"])
                                    classified[r]["is_electrical"] = bool(item.get("is_electrical", classified[r]["is_electrical"]))
                                    classified[r]["confidence"] = 0.85
                                    classified[r]["evidence"].append("llm_batch_inference")
                            total_resolved += len(items)
                            logger.info("[Classifier] Successfully resolved %d ambiguous components in chunk %d/%d via batch LLM.", len(items), chunk_num, total_chunks)
                            if t_logger:
                                t_logger.debug(
                                    "PARSE_AND_GRAPH",
                                    "LLM",
                                    f"LLM 批次分類回覆成功 (批次 {chunk_num}/{total_chunks})，解析出 {len(items)} 個元件結構化類別",
                                    details={"parsed_items": items}
                                )
                        except json.JSONDecodeError as je:
                            logger.error("[Classifier] LLM response JSON decode error (chunk %d/%d): %s", chunk_num, total_chunks, je)
                            if t_logger:
                                t_logger.warning(
                                    "PARSE_AND_GRAPH",
                                    "LLM",
                                    f"LLM 回覆的 JSON 格式錯誤，無法解析 (批次 {chunk_num}/{total_chunks})",
                                    details={"error": str(je), "matched_string": json_match.group(0)}
                                )
                    else:
                        logger.warning("[Classifier] Could not find JSON array in LLM response (chunk %d/%d).", chunk_num, total_chunks)
                        if t_logger:
                            t_logger.warning(
                                "PARSE_AND_GRAPH",
                                "LLM",
                                f"無法從 LLM 的回覆中提取 JSON 陣列結構 (批次 {chunk_num}/{total_chunks})",
                                details={"raw_content": content}
                            )
                else:
                    logger.warning("[Classifier] Invalid or empty response from LLM (chunk %d/%d).", chunk_num, total_chunks)
                    if t_logger:
                        t_logger.warning(
                            "PARSE_AND_GRAPH",
                            "LLM",
                            f"LLM 回覆為空或格式不合法 (批次 {chunk_num}/{total_chunks})",
                            details={"response_obj": str(response)}
                        )
            if t_logger:
                t_logger.info(
                    "PARSE_AND_GRAPH",
                    "LLM",
                    f"LLM 微批次語意識別完成，共成功識別 {total_resolved}/{len(ambiguous_items)} 個元件",
                    details={"total_resolved": total_resolved, "total_ambiguous": len(ambiguous_items)}
                )
        except Exception as e:
            logger.warning("[Classifier] Batch LLM inference unavailable or failed (%s). Gracefully falling back to heuristic results.", e)
            if t_logger:
                t_logger.warning(
                    "PARSE_AND_GRAPH",
                    "LLM",
                    f"LLM 批次分類連線失敗或逾時 ({str(e)[:60]})，優雅降級為啟發式結果",
                    details={"error": str(e)}
                )
    elif t_logger and not ambiguous_items:
        # 計算類別統計便於放入 details
        quick_cats: Dict[str, int] = {}
        for c in classified.values():
            quick_cats[c["category"]] = quick_cats.get(c["category"], 0) + 1
        t_logger.debug(
            "PARSE_AND_GRAPH",
            "PARSER",
            f"所有元件均已透過 YAML 規則完全識別 (共 {len(classified)} 個)，無需呼叫 LLM 進行模糊分類",
            details={
                "total_components": len(classified),
                "categories": quick_cats
            }
        )

    # 統計日誌
    cat_counts: Dict[str, int] = {}
    for c in classified.values():
        cat = c["category"]
        cat_counts[cat] = cat_counts.get(cat, 0) + 1
    logger.info("[Classifier] Component classification finished: Total=%d, Categories=%s", len(classified), cat_counts)

    return classified
