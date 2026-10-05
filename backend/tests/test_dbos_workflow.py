"""
DBOS 工作流程與步驟單元測試 (DBOS Workflow & Steps Tests)

驗證各個 DBOS 步驟執行、狀態持久化記錄 (step_status 表) 與整體 Durable Execution 工作流。
"""

import uuid
from backend.app.models.task import DrcTask
from backend.app.models.step_status import StepStatus
from backend.app.models.report import DrcReport
from backend.app.workflows.drc_workflow import (
    record_step_status,
    step_unpack_and_validate,
    step_parse_and_graph,
    step_heuristic_check,
    step_llm_reasoning,
    step_generate_report,
    execute_drc_workflow,
)


def test_record_step_status_new_and_update(db_session, monkeypatch):
    """測試 record_step_status 建立與更新步驟狀態"""
    import backend.app.workflows.drc_workflow as wf_module
    monkeypatch.setattr(wf_module, "SessionLocal", lambda: db_session)

    task_id = str(uuid.uuid4())
    task = DrcTask(id=task_id, project_name="TestWF", status="READY_FOR_RUN")
    db_session.add(task)
    db_session.commit()

    # 1. 建立步驟為 PROCESSING
    step1 = record_step_status(
        task_id=task_id,
        step_name="UNPACK_AND_VALIDATE",
        status="PROCESSING",
        log_message="解壓中..."
    )
    assert step1.status == "PROCESSING"
    assert step1.step_name == "UNPACK_AND_VALIDATE"
    
    # 驗證任務主表狀態被同步更新為 PROCESSING
    refreshed_task = db_session.query(DrcTask).filter(DrcTask.id == task_id).first()
    assert refreshed_task.status == "PROCESSING"

    # 2. 更新同一步驟為 COMPLETED
    step2 = record_step_status(
        task_id=task_id,
        step_name="UNPACK_AND_VALIDATE",
        status="COMPLETED",
        log_message="解壓完成"
    )
    assert step2.id == step1.id
    assert step2.status == "COMPLETED"
    assert step2.completed_at is not None
    assert step2.log_message == "解壓完成"


def test_individual_steps_execution(db_session, monkeypatch):
    """測試個別 DBOS Step 函式執行"""
    import backend.app.workflows.drc_workflow as wf_module
    monkeypatch.setattr(wf_module, "SessionLocal", lambda: db_session)

    task_id = str(uuid.uuid4())
    task = DrcTask(id=task_id, project_name="StepsProject", status="READY_FOR_RUN")
    db_session.add(task)
    db_session.commit()

    # 步驟 1
    res1 = step_unpack_and_validate(task_id)
    assert res1["status"] == "valid"

    # 步驟 2
    res2 = step_parse_and_graph(task_id)
    assert "components_count" in res2

    # 步驟 3
    res3 = step_heuristic_check(task_id, ["RULE-BUS-I2C-ADDR"])
    assert len(res3) > 0
    assert res3[0]["rule_id"] == "RULE-BUS-I2C-ADDR"

    # 步驟 4
    res4 = step_llm_reasoning(task_id, ["RULE-LLM-SD-MODE"])
    assert len(res4) > 0
    assert res4[0]["check_type"] == "LLM"

    # 步驟 5
    summary = step_generate_report(task_id, res3, res4)
    assert summary["total_rules_checked"] == 2
    assert summary["pass_count"] == 2

    # 驗證資料庫已產生 DrcReport
    report = db_session.query(DrcReport).filter(DrcReport.task_id == task_id).first()
    assert report is not None
    assert len(report.violations) == 2


def test_full_drc_workflow_execution(db_session, monkeypatch):
    """測試完整的 DBOS Workflow 執行與最終狀態轉變"""
    import backend.app.workflows.drc_workflow as wf_module
    monkeypatch.setattr(wf_module, "SessionLocal", lambda: db_session)

    task_id = str(uuid.uuid4())
    task = DrcTask(id=task_id, project_name="FullWorkflowProject", status="READY_FOR_RUN")
    db_session.add(task)
    db_session.commit()

    rule_ids = ["RULE-BUS-I2C-ADDR", "RULE-PWR-CAP-DERATING"]
    result = execute_drc_workflow(task_id, rule_ids)

    assert result["total_rules_checked"] >= 2
    assert result["pass_rate_percentage"] == 100.0

    # 驗證 step_status 表包含所有步驟
    steps = db_session.query(StepStatus).filter(StepStatus.task_id == task_id).all()
    step_names = [s.step_name for s in steps]
    assert "UNPACK_AND_VALIDATE" in step_names
    assert "PARSE_AND_GRAPH" in step_names
    assert "HEURISTIC_CHECK" in step_names
    assert "LLM_REASONING" in step_names
    assert "GENERATE_REPORT" in step_names

    # 驗證任務最終狀態為 COMPLETED
    refreshed_task = db_session.query(DrcTask).filter(DrcTask.id == task_id).first()
    assert refreshed_task.status == "COMPLETED"
