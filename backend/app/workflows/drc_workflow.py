"""
DRC 任務 DBOS 工作流程定義 (DRC DBOS Workflows & Steps)

基於 Postgres DBOS 實作 Durable Execution 工作流，包含各步驟的持久化狀態記錄與斷點接續。
"""

import os
import glob
import pickle
from datetime import datetime, timezone
import logging
from typing import List, Dict, Any, Optional
import networkx as nx
from dbos import DBOS

from backend.app.core.config import settings
from backend.app.core.task_logger import get_task_logger
from backend.app.db.session import SessionLocal
from backend.app.models.task import DrcTask
from backend.app.models.step_status import StepStatus, STEP_ORDER_MAP
from backend.app.models.report import DrcReport
from backend.app.engine import (
    extract_archive,
    find_schematic_files,
    parse_orcad_xml,
    parse_allegro_netlist,
    merge_schematic_data,
    build_schematic_graph,
    create_config_subgraph,
)
from backend.app.engine.drc_engine import Level3Engine

logger = logging.getLogger("designshield.workflow")


def record_step_status(
    task_id: str,
    step_name: str,
    status: str,
    log_message: Optional[str] = None,
    preserve_existing_timing: bool = False,
    force_override: bool = False
) -> StepStatus:
    """
    更新或新增指定步驟狀態紀錄至資料庫 (step_status 表)
    
    Args:
        task_id: 任務 UUID
        step_name: 步驟名稱 (例如: UNPACK_AND_VALIDATE)
        status: 狀態 (PENDING, PROCESSING, COMPLETED, FAILED, SKIPPED)
        log_message: 步驟產生的即時日誌或摘要
        preserve_existing_timing: 若為 True 且已存在有效起訖時間，則保留原時間戳（適用於快取命中復用）
        force_override: 是否強制覆寫（若既有步驟已處於 FAILED，預設禁止以 PROCESSING 或 COMPLETED 覆寫，除非 force_override=True）
        
    Returns:
        StepStatus: 更新後的資料庫記錄物件
    """
    db = SessionLocal()
    try:
        step = (
            db.query(StepStatus)
            .filter(StepStatus.task_id == task_id, StepStatus.step_name == step_name)
            .first()
        )
        now = datetime.now(timezone.utc)
        step_order_val = STEP_ORDER_MAP.get(step_name, 1)

        if not step:
            step = StepStatus(
                task_id=task_id,
                step_name=step_name,
                step_order=step_order_val,
                status=status,
                log_message=log_message,
                started_at=now if status == "PROCESSING" else None,
                completed_at=now if status in ["COMPLETED", "FAILED"] else None
            )
            db.add(step)
        else:
            # 狀態防覆寫守衛：已處於 FAILED 之步驟，若非強制覆寫，嚴禁以正常狀態沖掉失敗標記
            if not force_override and step.status == "FAILED" and status in ["PROCESSING", "COMPLETED"]:
                logger.warning(
                    "步驟 %s 在任務 %s 處於 FAILED 狀態，禁止以 %s 靜默覆寫",
                    step_name, task_id, status
                )
                if log_message and not step.log_message:
                    step.log_message = log_message
                    db.commit()
                return step

            step.step_order = step_order_val
            step.status = status
            if log_message:
                step.log_message = log_message

            # 若指定保留既有時間戳（如預分析快取命中）且時間戳皆存在，則不覆寫
            if preserve_existing_timing and step.started_at and step.completed_at:
                pass
            else:
                if status == "PROCESSING":
                    # 進入 PROCESSING 狀態時，若原本為 PENDING 或尚未有開始時間，校正為真實當前時間
                    if not step.started_at or step.status == "PENDING":
                        step.started_at = now
                elif status in ["COMPLETED", "FAILED"]:
                    if not step.started_at:
                        step.started_at = now
                    step.completed_at = now
        
        task = db.query(DrcTask).filter(DrcTask.id == task_id).first()
        if task:
            if step_name == "RULE_SELECTION" and status == "PROCESSING":
                task.status = "READY_FOR_RUN"
            elif status == "PROCESSING" and task.status != "PROCESSING" and task.status != "PRE_ANALYZING":
                task.status = "PROCESSING"
            elif step_name == "GENERATE_REPORT" and status == "COMPLETED":
                task.status = "COMPLETED"
            elif status == "FAILED":
                task.status = "FAILED"
        
        db.commit()
        db.refresh(step)
        return step
    except Exception as e:
        db.rollback()
        logger.error("Failed to record step status: %s", e)
        raise
    finally:
        db.close()


def get_graph_cache_path(task_id: str) -> str:
    """取得特定任務之圖譜二進位快取檔路徑"""
    return os.path.join(settings.STAGING_DIR, task_id, "graph_cache.pkl")


def save_task_graph(task_id: str, G: nx.Graph) -> None:
    """持久化圖譜物件至 staging 快取目錄"""
    cache_path = get_graph_cache_path(task_id)
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    with open(cache_path, "wb") as f:
        pickle.dump(G, f)


def load_task_graph(task_id: str) -> nx.Graph:
    """從快取或 staging 目錄為特定任務構建或載入圖譜。絕不使用 Mock 圖譜，缺失即拋出異常。"""
    cache_path = get_graph_cache_path(task_id)
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "rb") as f:
                G = pickle.load(f)
                return G
        except Exception as e:
            logger.warning("載入圖譜快取失敗，將回退重新解析: %s", e)

    staging_dir = os.path.join(settings.STAGING_DIR, task_id)
    if not os.path.exists(staging_dir):
        raise FileNotFoundError(f"任務 {task_id} 之暫存目錄不存在: {staging_dir}")

    files = find_schematic_files(staging_dir)
    xml_path = files.get("xml_path")
    if not xml_path:
        raise FileNotFoundError(f"任務 {task_id} 之暫存目錄中未發現 OrCAD XML 設計檔案")

    xml_data = parse_orcad_xml(xml_path, task_id=task_id)
    netlist_data = parse_allegro_netlist(files["netlist_path"], task_id=task_id) if files.get("netlist_path") else None
    merged = merge_schematic_data(xml_data, netlist_data, task_id=task_id)
    G = build_schematic_graph(merged, task_id=task_id)

    from backend.app.engine.pattern_engine.topology_engine import TopologyPatternEngine
    topology_engine = TopologyPatternEngine()
    topology_engine.execute(G, task_id=task_id)

    from backend.app.engine.net_classifier import classify_nets_batch
    classify_nets_batch(G, enable_llm_fallback=False, task_id=task_id)
    
    save_task_graph(task_id, G)
    return G


@DBOS.step()
async def step_unpack_and_validate(task_id: str) -> Dict[str, Any]:
    """步驟 1: 解壓縮與檔案格式預檢"""
    t_logger = get_task_logger(task_id)
    cache_path = get_graph_cache_path(task_id)
    staging_dir = os.path.join(settings.STAGING_DIR, task_id)

    # 若圖譜快取已存在或 staging 目錄已具備有效檔案，命中快取直接快速通過 (保留預分析真實耗時)
    if os.path.exists(cache_path):
        log_msg = "解壓縮通過，直接使用預先分析已解壓檔案與驗證成果 (快取命中)"
        t_logger.info("UNPACK_AND_VALIDATE", "PARSER", log_msg)
        record_step_status(
            task_id=task_id,
            step_name="UNPACK_AND_VALIDATE",
            status="COMPLETED",
            log_message=log_msg,
            preserve_existing_timing=True
        )
        return {"status": "valid", "file_type": "Cadence OrCAD XML", "cached": True}

    t_logger.info("UNPACK_AND_VALIDATE", "FILE", "開始驗證檔案結構與 XML/Netlist 完整性...")

    record_step_status(
        task_id=task_id,
        step_name="UNPACK_AND_VALIDATE",
        status="PROCESSING",
        log_message="正在驗證壓縮檔結構與 XML/Netlist 完整性..."
    )
    
    os.makedirs(staging_dir, exist_ok=True)
    t_logger.debug("UNPACK_AND_VALIDATE", "FILE", f"工作暫存目錄已確認: {staging_dir}")
    
    search_pattern = os.path.join(settings.UPLOAD_DIR, f"{task_id}*")
    matching_files = glob.glob(search_pattern)
    
    if not matching_files:
        err_msg = f"未在伺服器上傳目錄發現任務 {task_id} 之任何有效檔案"
        t_logger.error("UNPACK_AND_VALIDATE", "FILE", err_msg)
        record_step_status(
            task_id=task_id,
            step_name="UNPACK_AND_VALIDATE",
            status="FAILED",
            log_message=err_msg,
            force_override=True
        )
        raise FileNotFoundError(err_msg)

    upload_path = matching_files[0]
    try:
        t_logger.debug("UNPACK_AND_VALIDATE", "FILE", f"解壓檔案: {upload_path}")
        extract_archive(upload_path, staging_dir)
        files = find_schematic_files(staging_dir)
        if not files["xml_path"]:
            err_msg = f"解壓縮完成，但未發現標準 Cadence OrCAD XML 檔案 ({os.path.basename(upload_path)})"
            t_logger.error("UNPACK_AND_VALIDATE", "PARSER", err_msg)
            record_step_status(
                task_id=task_id,
                step_name="UNPACK_AND_VALIDATE",
                status="FAILED",
                log_message=err_msg,
                force_override=True
            )
            raise FileNotFoundError(err_msg)

        found_info = {"status": "valid", "file_type": "Cadence OrCAD XML", "xml_found": True}
        log_msg = f"解壓縮通過，發現 OrCAD XML: {os.path.basename(files['xml_path'])}"
        t_logger.info("UNPACK_AND_VALIDATE", "PARSER", log_msg, details={"xml_path": files["xml_path"]})
    except Exception as e:
        log_msg = f"解壓縮或格式預檢失敗: {str(e)}"
        t_logger.error("UNPACK_AND_VALIDATE", "FILE", log_msg, details={"error": str(e)})
        record_step_status(
            task_id=task_id,
            step_name="UNPACK_AND_VALIDATE",
            status="FAILED",
            log_message=log_msg,
            force_override=True
        )
        raise
        
    record_step_status(
        task_id=task_id,
        step_name="UNPACK_AND_VALIDATE",
        status="COMPLETED",
        log_message=log_msg
    )
    return found_info


@DBOS.step()
async def step_parse_and_graph(task_id: str) -> Dict[str, Any]:
    """步驟 2: 解析線路圖並構建 NetworkX 二分圖譜"""
    t_logger = get_task_logger(task_id)
    cache_path = get_graph_cache_path(task_id)

    # 優先嘗試快取命中 (保留預分析真實耗時)
    if os.path.exists(cache_path):
        t_logger.info("PARSE_AND_GRAPH", "GRAPH", "使用預先分析已構建之拓撲圖譜快取進行檢測 (命中快取)")
        G = load_task_graph(task_id)
        comp_cnt = len([n for n, d in G.nodes(data=True) if d.get("type") == "component"])
        net_cnt = len([n for n, d in G.nodes(data=True) if d.get("type") == "net"])
        summary = {
            "components_count": comp_cnt,
            "nets_count": net_cnt,
            "pins_count": G.number_of_edges(),
            "cached": True
        }
        log_msg = f"圖譜快取載入成功 (元件節點: {comp_cnt}, 網路節點: {net_cnt})"
        t_logger.info("PARSE_AND_GRAPH", "GRAPH", log_msg, details=summary)
        record_step_status(
            task_id=task_id,
            step_name="PARSE_AND_GRAPH",
            status="COMPLETED",
            log_message=log_msg,
            preserve_existing_timing=True
        )
        return summary

    t_logger.info("PARSE_AND_GRAPH", "GRAPH", "開始解析電路圖 XML 階層與網路拓撲，構建 NetworkX 圖譜...")

    record_step_status(
        task_id=task_id,
        step_name="PARSE_AND_GRAPH",
        status="PROCESSING",
        log_message="開始解析電路圖 XML 階層與網路拓撲，構建 NetworkX 圖譜..."
    )
    
    try:
        G = load_task_graph(task_id)

        # 非同步協程執行網路微批次 LLM 語意識別 (若有模糊網路，自動遵循 ENABLE_LEVEL2_LLM_FALLBACK 系統設定)
        from backend.app.engine.net_classifier import classify_nets_batch
        net_stats = await classify_nets_batch(G, task_id=task_id)

        # 儲存快取
        save_task_graph(task_id, G)

        comp_cnt = len([n for n, d in G.nodes(data=True) if d.get("type") == "component"])
        net_cnt = len([n for n, d in G.nodes(data=True) if d.get("type") == "net"])
        summary = {
            "components_count": comp_cnt,
            "nets_count": net_cnt,
            "pins_count": G.number_of_edges(),
            "power_nets_count": net_stats.get("power_nets", 0),
            "ground_nets_count": net_stats.get("ground_nets", 0),
            "bus_nets_count": net_stats.get("bus_nets", 0)
        }
        
        t_logger.debug("PARSE_AND_GRAPH", "GRAPH", f"圖譜拓撲構建完成: 元件 {comp_cnt} 個, 網路 {net_cnt} 條, 引腳連接 {summary['pins_count']} 處", details=summary)
        t_logger.info("PARSE_AND_GRAPH", "GRAPH", f"圖譜構建完成 (元件節點: {summary['components_count']}, 網路節點: {summary['nets_count']})")

        record_step_status(
            task_id=task_id,
            step_name="PARSE_AND_GRAPH",
            status="COMPLETED",
            log_message=f"圖譜構建完成 (元件節點: {summary['components_count']}, 網路節點: {summary['nets_count']})"
        )
        return summary
    except Exception as e:
        err_msg = f"圖譜構建與線路解析失敗: {str(e)}"
        t_logger.error("PARSE_AND_GRAPH", "GRAPH", err_msg, details={"error": str(e)})
        record_step_status(
            task_id=task_id,
            step_name="PARSE_AND_GRAPH",
            status="FAILED",
            log_message=err_msg,
            force_override=True
        )
        raise


@DBOS.step()
async def step_heuristic_check(
    task_id: str,
    rule_ids: List[str],
    selected_configs: Optional[List[str]] = None,
    is_mp_mode: bool = False
) -> List[Dict[str, Any]]:
    """步驟 3: 傳統啟發式圖論演算法規則比對 (歷遍選定之各 BOM Config，純非同步協程)"""
    t_logger = get_task_logger(task_id)
    G = load_task_graph(task_id)
    bom_info = G.graph.get("bom_config_info", {})
    all_config_names = bom_info.get("config_names", ["Config 1"])

    if selected_configs:
        target_configs = [c for c in all_config_names if c in selected_configs]
        if not target_configs:
            target_configs = all_config_names[:1]
    else:
        target_configs = all_config_names

    t_logger.info(
        "HEURISTIC_CHECK",
        "HEURISTIC",
        f"正在比對傳統演算法規則 (共 {len(rule_ids)} 條規則，檢測 {len(target_configs)} 組 Config: {', '.join(target_configs)}，MP Mode: {'開' if is_mp_mode else '關'})..."
    )

    record_step_status(
        task_id=task_id,
        step_name="HEURISTIC_CHECK",
        status="PROCESSING",
        log_message=f"正在比對傳統演算法規則 ({len(target_configs)} 組 Config，共 {len(rule_ids)} 條規則)..."
    )

    from backend.app.engine.drc_engine import Level3Engine
    l3_engine = Level3Engine()
    all_findings: List[Dict[str, Any]] = []

    for cfg_name in target_configs:
        cfg_idx = all_config_names.index(cfg_name) if cfg_name in all_config_names else 0
        cfg_G = create_config_subgraph(G, config_index=cfg_idx, is_mp_mode=is_mp_mode)

        t_logger.debug(
            "HEURISTIC_CHECK",
            "HEURISTIC",
            f"開始比對 [{cfg_name}] 拓撲線路 (已上件節點數: {cfg_G.number_of_nodes()}, 未上件: {len(cfg_G.graph.get('unmounted_components', {}))})"
        )

        def on_heuristic_progress(idx: int, total: int, rule_id: str, rule_name: str, stage: str):
            if stage == "START":
                msg = f"[{cfg_name}][{idx}/{total}] 正在比對傳統演算法規則「{rule_name}」..."
                record_step_status(
                    task_id=task_id,
                    step_name="HEURISTIC_CHECK",
                    status="PROCESSING",
                    log_message=msg
                )
                t_logger.info(
                    "HEURISTIC_CHECK",
                    "HEURISTIC",
                    msg,
                    details={"bom_config": cfg_name, "rule_id": rule_id, "current": idx, "total": total}
                )
            elif stage == "DONE":
                t_logger.debug(
                    "HEURISTIC_CHECK",
                    "HEURISTIC",
                    f"[{cfg_name}][{idx}/{total}] 規則 {rule_id} 比對完成",
                    details={"bom_config": cfg_name, "rule_id": rule_id}
                )

        findings = await l3_engine.run_heuristic_checks(cfg_G, rule_ids, progress_callback=on_heuristic_progress)

        for item in findings:
            item["bom_config"] = cfg_name
            st = item.get("status", "PASS")
            lvl = "WARNING" if st == "WARNING" else ("ERROR" if st == "FAIL" else "DEBUG")
            t_logger.log(
                "HEURISTIC_CHECK",
                "HEURISTIC",
                lvl,
                f"[{cfg_name}] 規則 {item.get('rule_id')} 比對完成: [{st}] {item.get('rule_title')}",
                details=item
            )
        all_findings.extend(findings)

    t_logger.info(
        "HEURISTIC_CHECK",
        "HEURISTIC",
        f"傳統演算法規則比對完成，產出 {len(all_findings)} 項比對結果 ({len(target_configs)} 組 Config)",
        details={
            "total_findings": len(all_findings),
            "pass_count": len([f for f in all_findings if f.get("status") == "PASS"]),
            "warning_count": len([f for f in all_findings if f.get("status") == "WARNING"]),
            "fail_count": len([f for f in all_findings if f.get("status") == "FAIL"]),
            "configs_checked": target_configs,
            "rules_checked": list(set([f.get("rule_id") for f in all_findings if f.get("rule_id")]))
        }
    )

    record_step_status(
        task_id=task_id,
        step_name="HEURISTIC_CHECK",
        status="COMPLETED",
        log_message=f"傳統演算法規則比對完成，產出 {len(all_findings)} 項比對結果 ({len(target_configs)} 組 Config)"
    )
    return all_findings


@DBOS.step()
async def step_llm_reasoning(
    task_id: str,
    rule_ids: List[str],
    selected_configs: Optional[List[str]] = None,
    is_mp_mode: bool = False
) -> List[Dict[str, Any]]:
    """步驟 4: 本地 LLM 語意邏輯推理檢測 (歷遍選定之各 BOM Config，純非同步協程)"""
    t_logger = get_task_logger(task_id)
    G = load_task_graph(task_id)
    bom_info = G.graph.get("bom_config_info", {})
    all_config_names = bom_info.get("config_names", ["Config 1"])

    if selected_configs:
        target_configs = [c for c in all_config_names if c in selected_configs]
        if not target_configs:
            target_configs = all_config_names[:1]
    else:
        target_configs = all_config_names

    t_logger.info(
        "LLM_REASONING",
        "LLM",
        f"正在呼叫本地 LLM 進行語意分析與介面模式合理性推理 (共 {len(rule_ids)} 條規則，檢測 {len(target_configs)} 組 Config: {', '.join(target_configs)})..."
    )

    record_step_status(
        task_id=task_id,
        step_name="LLM_REASONING",
        status="PROCESSING",
        log_message=f"正在呼叫本地 LLM 進行語意分析與介面模式合理性推理 ({len(target_configs)} 組 Config)..."
    )

    from backend.app.engine.drc_engine import Level3Engine
    l3_engine = Level3Engine()
    all_llm_findings: List[Dict[str, Any]] = []

    for cfg_name in target_configs:
        cfg_idx = all_config_names.index(cfg_name) if cfg_name in all_config_names else 0
        cfg_G = create_config_subgraph(G, config_index=cfg_idx, is_mp_mode=is_mp_mode)

        def on_llm_progress(idx: int, total: int, rule_id: str, rule_name: str, stage: str):
            if stage == "START":
                msg = f"[{cfg_name}][{idx}/{total}] 正在呼叫本地 LLM 進行「{rule_name}」語意推理..."
                record_step_status(
                    task_id=task_id,
                    step_name="LLM_REASONING",
                    status="PROCESSING",
                    log_message=msg
                )
                t_logger.info(
                    "LLM_REASONING",
                    "LLM",
                    msg,
                    details={"bom_config": cfg_name, "rule_id": rule_id, "current": idx, "total": total}
                )
            elif stage == "DONE":
                t_logger.debug(
                    "LLM_REASONING",
                    "LLM",
                    f"[{cfg_name}][{idx}/{total}] 規則 {rule_id} LLM 語意推理完成",
                    details={"bom_config": cfg_name, "rule_id": rule_id}
                )

        cfg_llm_findings = await l3_engine.run_llm_checks(cfg_G, rule_ids, progress_callback=on_llm_progress)

        for item in cfg_llm_findings:
            item["bom_config"] = cfg_name
            st = item.get("status", "PASS")
            lvl = "WARNING" if st == "WARNING" else ("ERROR" if st == "FAIL" else "DEBUG")
            t_logger.log(
                "LLM_REASONING",
                "LLM",
                lvl,
                f"[{cfg_name}] LLM 推理判定: 規則 {item.get('rule_id')} - {item.get('rule_title')} [{st}]",
                details=item.get("evidence_trail") or item
            )
        all_llm_findings.extend(cfg_llm_findings)

    t_logger.info(
        "LLM_REASONING",
        "LLM",
        f"本地 LLM 邏輯推理完成，產出 {len(all_llm_findings)} 項檢測結論 ({len(target_configs)} 組 Config)",
        details={
            "total_findings": len(all_llm_findings),
            "pass_count": len([f for f in all_llm_findings if f.get("status") == "PASS"]),
            "warning_count": len([f for f in all_llm_findings if f.get("status") == "WARNING"]),
            "fail_count": len([f for f in all_llm_findings if f.get("status") == "FAIL"]),
            "configs_checked": target_configs,
            "rules_checked": list(set([f.get("rule_id") for f in all_llm_findings if f.get("rule_id")]))
        }
    )

    record_step_status(
        task_id=task_id,
        step_name="LLM_REASONING",
        status="COMPLETED",
        log_message=f"本地 LLM 邏輯推理完成，產出 {len(all_llm_findings)} 項檢測結論 ({len(target_configs)} 組 Config)"
    )
    return all_llm_findings


@DBOS.step()
async def step_generate_report(
    task_id: str,
    heuristic_findings: List[Dict[str, Any]],
    llm_findings: List[Dict[str, Any]],
    target_configs: Optional[List[str]] = None
) -> Dict[str, Any]:
    """步驟 5: 彙總 DRC 報告並落地儲存至資料庫 (支援多 BOM Config 獨立彙整)"""
    t_logger = get_task_logger(task_id)
    t_logger.info("GENERATE_REPORT", "DB", "正在彙整檢測結果並計算統計數據...")

    record_step_status(
        task_id=task_id,
        step_name="GENERATE_REPORT",
        status="PROCESSING",
        log_message="正在彙整檢測結果並計算統計數據..."
    )

    all_violations = heuristic_findings + llm_findings

    # 解析涵蓋的 Config 清單
    distinct_configs: List[str] = []
    if target_configs:
        distinct_configs = list(target_configs)
    else:
        for v in all_violations:
            cfg = v.get("bom_config")
            if cfg and cfg not in distinct_configs:
                distinct_configs.append(cfg)
    if not distinct_configs:
        distinct_configs = ["Config 1"]

    # 為每組 Config 計算專屬統計指標
    configs_summary: Dict[str, Dict[str, Any]] = {}
    for cfg_name in distinct_configs:
        cfg_violations = [v for v in all_violations if v.get("bom_config") == cfg_name]
        c_pass = sum(1 for v in cfg_violations if v.get("status") == "PASS")
        c_fail = sum(1 for v in cfg_violations if v.get("status") == "FAIL")
        c_warn = sum(1 for v in cfg_violations if v.get("status") == "WARNING")
        c_skip = sum(1 for v in cfg_violations if v.get("status") == "SKIPPED")
        c_total = len(cfg_violations)
        c_eval = c_pass + c_fail + c_warn
        c_rate = round((c_pass / c_eval * 100), 2) if c_eval > 0 else 100.0

        c_by_cat: Dict[str, Dict[str, int]] = {}
        for item in cfg_violations:
            cat = item.get("rule_category", "General")
            st = item.get("status", "PASS")
            if cat not in c_by_cat:
                c_by_cat[cat] = {"pass": 0, "fail": 0, "warning": 0, "skip": 0}
            if st == "PASS":
                c_by_cat[cat]["pass"] += 1
            elif st == "FAIL":
                c_by_cat[cat]["fail"] += 1
            elif st == "WARNING":
                c_by_cat[cat]["warning"] += 1
            elif st == "SKIPPED":
                c_by_cat[cat]["skip"] += 1

        configs_summary[cfg_name] = {
            "total_rules_checked": c_total,
            "pass_count": c_pass,
            "fail_count": c_fail,
            "warning_count": c_warn,
            "skip_count": c_skip,
            "pass_rate_percentage": c_rate,
            "by_category": c_by_cat
        }

    # 頂層總結指標 (以第一組 Config 為基準展示，並提供 configs 完整字典供切換)
    first_cfg = distinct_configs[0]
    base_stat = configs_summary[first_cfg]

    summary = {
        "total_rules_checked": base_stat["total_rules_checked"],
        "pass_count": base_stat["pass_count"],
        "fail_count": base_stat["fail_count"],
        "warning_count": base_stat["warning_count"],
        "skip_count": base_stat["skip_count"],
        "pass_rate_percentage": base_stat["pass_rate_percentage"],
        "by_category": base_stat["by_category"],
        "configs": configs_summary
    }

    t_logger.debug(
        "GENERATE_REPORT",
        "DB",
        f"統計完成 (涵蓋 {len(distinct_configs)} 組 Config): 首組通過 {base_stat['pass_count']}, 失敗 {base_stat['fail_count']}",
        details=summary
    )

    db = SessionLocal()
    try:
        report = db.query(DrcReport).filter(DrcReport.task_id == task_id).first()
        if not report:
            report = DrcReport(task_id=task_id, summary=summary, violations=all_violations)
            db.add(report)
        else:
            report.summary = summary
            report.violations = all_violations
        db.commit()
    finally:
        db.close()

    t_logger.info(
        "GENERATE_REPORT",
        "DB",
        f"DRC 分析報告產出完成，總檢查 {base_stat['total_rules_checked']} 項 (首組通過率: {base_stat['pass_rate_percentage']}%, 涵蓋 Config: {', '.join(distinct_configs)})",
        details=summary
    )

    record_step_status(
        task_id=task_id,
        step_name="GENERATE_REPORT",
        status="COMPLETED",
        log_message=f"DRC 分析報告產出完成 (共 {len(distinct_configs)} 組 Config，首組通過率: {base_stat['pass_rate_percentage']}%)"
    )
    return summary


@DBOS.workflow()
async def execute_drc_workflow(
    task_id: str,
    rule_ids: List[str],
    selected_configs: Optional[List[str]] = None,
    is_mp_mode: bool = False
) -> Dict[str, Any]:
    """
    DRC 分析完整 DBOS Workflow (純非同步協程 Durable Execution，支援多 Config 歷遍與 MP Mode)
    """
    await step_unpack_and_validate(task_id)
    await step_parse_and_graph(task_id)
    heuristic_results = await step_heuristic_check(task_id, rule_ids, selected_configs, is_mp_mode)
    llm_results = await step_llm_reasoning(task_id, rule_ids, selected_configs, is_mp_mode)
    report_summary = await step_generate_report(task_id, heuristic_results, llm_results, selected_configs)
    return report_summary
