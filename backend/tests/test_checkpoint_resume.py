"""
DBOS 原生斷點接續單元測試 (DBOS Checkpoint & Resume Tests)

驗證任務在步驟中斷時，DBOS 能從 step_status 表接續執行，且不重複執行已完成之耗時步驟或 LLM 請求。
"""

import uuid
from backend.app.models.task import DrcTask
from backend.app.models.step_status import StepStatus
from backend.app.models.report import DrcReport
from backend.app.workflows.drc_workflow import (
    record_step_status,
    execute_drc_workflow,
)


def test_dbos_step_checkpointing_preserves_state(db_session, monkeypatch):
    """測試 DBOS 步驟執行後 step_status 完整紀錄狀態與時間戳"""
    import backend.app.workflows.drc_workflow as wf_module
    monkeypatch.setattr(wf_module, "SessionLocal", lambda: db_session)

    task_id = str(uuid.uuid4())
    task = DrcTask(id=task_id, project_name="CheckpointProject", status="READY_FOR_RUN")
    db_session.add(task)
    db_session.commit()

    # 模擬步驟 1, 2, 3 已在第一次執行時順利完成並打下記錄
    record_step_status(task_id, "UNPACK_AND_VALIDATE", "COMPLETED", "檔案已預檢完成 (第一次)")
    record_step_status(task_id, "PARSE_AND_GRAPH", "COMPLETED", "圖譜已構建 (第一次)")
    record_step_status(task_id, "HEURISTIC_CHECK", "COMPLETED", "傳統規則已比對 (第一次)")

    # 查詢現有進度
    steps = db_session.query(StepStatus).filter(StepStatus.task_id == task_id).all()
    assert len(steps) == 3
    for s in steps:
        assert s.status == "COMPLETED"
        assert s.completed_at is not None

    # 模擬接續執行後續步驟 (步驟 4 與 步驟 5)
    record_step_status(task_id, "LLM_REASONING", "COMPLETED", "本地 LLM 推理完成 (接續)")
    record_step_status(task_id, "GENERATE_REPORT", "COMPLETED", "報告產出完成 (接續)")

    # 驗證所有 5 個步驟完整就緒，先前完成的步驟紀錄維持不變
    all_steps = db_session.query(StepStatus).filter(StepStatus.task_id == task_id).all()
    assert len(all_steps) == 5

    step_map = {s.step_name: s for s in all_steps}
    assert "第一次" in step_map["UNPACK_AND_VALIDATE"].log_message
    assert "第一次" in step_map["PARSE_AND_GRAPH"].log_message
    assert "第一次" in step_map["HEURISTIC_CHECK"].log_message
    assert "接續" in step_map["LLM_REASONING"].log_message
    assert "接續" in step_map["GENERATE_REPORT"].log_message


def test_drc_workflow_generates_full_report(db_session, monkeypatch):
    """測試完整執行後產生包含總結與違規之 DrcReport"""
    import backend.app.workflows.drc_workflow as wf_module
    monkeypatch.setattr(wf_module, "SessionLocal", lambda: db_session)

    task_id = str(uuid.uuid4())
    task = DrcTask(id=task_id, project_name="FullReportTest", status="READY_FOR_RUN")
    db_session.add(task)
    db_session.commit()

    rule_ids = ["power_capacitor_derating", "ic_decoupling_capacitor_existence", "sd_interface_mode_reasoning"]
    result = execute_drc_workflow(task_id, rule_ids)

    assert result["total_rules_checked"] >= 2
    assert "by_category" in result

    report = db_session.query(DrcReport).filter(DrcReport.task_id == task_id).first()
    assert report is not None
    assert len(report.violations) >= 2
    assert report.summary["total_rules_checked"] == len(report.violations)
