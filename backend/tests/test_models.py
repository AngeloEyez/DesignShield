"""
資料模型單元測試 (Model Unit Tests)

驗證 DrcTask, StepStatus, DrcRule, DrcReport 與 SystemSetting 的 CRUD 與關聯關係。
"""

import uuid
from datetime import datetime, timezone
from backend.app.models.task import DrcTask
from backend.app.models.step_status import StepStatus
from backend.app.models.rule import DrcRule
from backend.app.models.report import DrcReport
from backend.app.models.settings import SystemSetting


def test_drc_task_crud(db_session):
    """測試 DrcTask 建立與讀取"""
    task_id = str(uuid.uuid4())
    task = DrcTask(
        id=task_id,
        project_name="Motherboard_Rev1",
        status="READY_FOR_RUN",
        pre_analysis_summary={"buses": ["I2C"]},
        selected_rules=["RULE-PWR-CAP-DERATING"]
    )
    db_session.add(task)
    db_session.commit()

    saved = db_session.query(DrcTask).filter(DrcTask.id == task_id).first()
    assert saved is not None
    assert saved.project_name == "Motherboard_Rev1"
    assert saved.status == "READY_FOR_RUN"
    assert saved.pre_analysis_summary["buses"] == ["I2C"]
    assert "Motherboard_Rev1" in repr(saved)


def test_step_status_cascade_delete(db_session):
    """測試 StepStatus 關聯與級聯刪除 (Cascade Delete)"""
    task = DrcTask(project_name="TestProject", status="PROCESSING")
    db_session.add(task)
    db_session.commit()

    step = StepStatus(
        task_id=task.id,
        step_name="UNPACK_AND_VALIDATE",
        status="COMPLETED",
        log_message="解壓縮完成"
    )
    db_session.add(step)
    db_session.commit()

    assert len(task.step_statuses) == 1
    assert task.step_statuses[0].step_name == "UNPACK_AND_VALIDATE"
    assert "UNPACK_AND_VALIDATE" in repr(step)

    # 刪除 task 應級聯刪除 step
    db_session.delete(task)
    db_session.commit()

    orphaned = db_session.query(StepStatus).filter(StepStatus.id == step.id).first()
    assert orphaned is None


def test_drc_rule_crud(db_session):
    """測試 DrcRule 規則建立與查詢"""
    rule = DrcRule(
        id="RULE-PWR-001",
        name="電源去偶電容檢查",
        category="Power Domain",
        check_type="HEURISTIC",
        is_active=True,
        parameters={"min_capacitance_uf": 0.1}
    )
    db_session.add(rule)
    db_session.commit()

    saved = db_session.query(DrcRule).filter(DrcRule.id == "RULE-PWR-001").first()
    assert saved is not None
    assert saved.name == "電源去偶電容檢查"
    assert saved.parameters["min_capacitance_uf"] == 0.1
    assert "RULE-PWR-001" in repr(saved)


def test_drc_report_crud(db_session):
    """測試 DrcReport 報告建立與關聯"""
    task = DrcTask(project_name="ReportProject", status="COMPLETED")
    db_session.add(task)
    db_session.commit()

    report = DrcReport(
        task_id=task.id,
        summary={"total_rules_checked": 10, "pass_count": 9, "fail_count": 1},
        violations=[{"rule_id": "RULE-1", "status": "FAIL"}]
    )
    db_session.add(report)
    db_session.commit()

    assert task.report is not None
    assert task.report.summary["pass_count"] == 9
    assert len(task.report.violations) == 1
    assert task.id in repr(report)


def test_system_settings_crud(db_session):
    """測試 SystemSetting 系統設定 CRUD"""
    setting = SystemSetting(
        key="upload_retention_days",
        value=7,
        description="檔案保留天數"
    )
    db_session.add(setting)
    db_session.commit()

    saved = db_session.query(SystemSetting).filter(SystemSetting.key == "upload_retention_days").first()
    assert saved is not None
    assert saved.value == 7
    assert "upload_retention_days" in repr(saved)
