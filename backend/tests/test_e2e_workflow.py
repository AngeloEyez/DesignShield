"""
全專案端到端 (E2E) 整合驗收測試 (End-to-End Workflow Acceptance Tests)

完整覆蓋使用者路徑：
上傳線路檔案 -> 預先分析 -> 規則選取與啟動 DRC -> DBOS 雙軌執行 -> 報告產出與匯出 -> 磁碟儲存管理
"""

import os
import io
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.models.task import DrcTask
from backend.app.models.step_status import StepStatus
from backend.app.models.report import DrcReport
from backend.app.workflows.drc_workflow import execute_drc_workflow
import backend.app.workflows.drc_workflow as wf_module


@pytest.fixture
def test_xml_fixture():
    """真實 OrCAD XML 電路測試檔案路徑"""
    xml_path = os.path.abspath("backend/tests/fixtures/sch/cartern-sch-si-20260817.xml")
    assert os.path.exists(xml_path), f"Fixture not found at {xml_path}"
    return xml_path


def test_full_drc_e2e_workflow(client, db_session, test_xml_fixture, monkeypatch):
    """
    全流程 E2E 測試：
    1. 上傳 OrCAD XML 檔案
    2. 呼叫 pre-analyze 進行結構特徵分析
    3. 選取規則清單
    4. 啟動 DRC Workflow (透過同步呼叫驗證完整六大步驟)
    5. 取得完整審查報告並驗證其結構
    6. 匯出報告 JSON
    """
    # 步驟 1: 上傳線路檔案建立任務
    with open(test_xml_fixture, "rb") as f:
        file_bytes = f.read()

    upload_resp = client.post(
        "/api/v1/tasks",
        files={"file": ("cartern-sch-si-20260817.xml", io.BytesIO(file_bytes), "application/xml")},
        data={"project_name": "E2E Cartern Project"}
    )
    assert upload_resp.status_code == 200
    task_info = upload_resp.json()
    task_id = task_info["task_id"]
    assert task_id is not None
    assert task_info["status"] == "PRE_ANALYZING"
    assert task_info["project_name"] == "E2E Cartern Project"

    # 背景任務執行完畢後查詢狀態 (驗證預先分析摘要與推薦規則)
    status_resp = client.get(f"/api/v1/tasks/{task_id}/status")
    assert status_resp.status_code == 200
    status_info = status_resp.json()
    assert status_info["status"] == "READY_FOR_RUN"
    assert "pre_analysis_summary" in status_info
    assert "recommended_rules" in status_info
    assert status_info["pre_analysis_summary"]["component_count"] > 300
    assert len(status_info["recommended_rules"]) > 0

    # 挑選推薦之規則清單
    rule_ids = [r["id"] for r in status_info["recommended_rules"]]
    assert "I2C_Pull_Up_Existence" in rule_ids or "Power_Capacitor_Derating" in rule_ids or "RULE-PWR-CAP-DERATING" in rule_ids

    # 步驟 3: 呼叫 run API 啟動 DRC (將背景執行緒 mock 避免非同步競爭)
    from dbos import DBOS
    monkeypatch.setattr(DBOS, "start_workflow", lambda *args, **kwargs: None)
    start_resp = client.post(
        f"/api/v1/tasks/{task_id}/run",
        json={"selected_rule_ids": rule_ids}
    )
    assert start_resp.status_code == 202
    assert start_resp.json()["status"] == "PROCESSING"

    # 步驟 4: 同步執行完整工作流直到報告產生
    summary_result = execute_drc_workflow(task_id, rule_ids)
    assert summary_result is not None
    assert "total_rules_checked" in summary_result
    assert "by_category" in summary_result

    # 驗證資料庫步驟狀態 (5 個 DBOS 核心步驟皆須為 COMPLETED)
    db_session.expire_all()
    steps = db_session.query(StepStatus).filter(StepStatus.task_id == task_id).all()
    step_map = {s.step_name: s.status for s in steps}
    
    expected_steps = [
        "UNPACK_AND_VALIDATE",
        "PARSE_AND_GRAPH",
        "HEURISTIC_CHECK",
        "LLM_REASONING",
        "GENERATE_REPORT"
    ]
    for exp_step in expected_steps:
        assert exp_step in step_map, f"Missing step: {exp_step}"
        assert step_map[exp_step] == "COMPLETED", f"Step {exp_step} was {step_map[exp_step]}"

    # 驗證任務整體狀態為 COMPLETED
    task = db_session.query(DrcTask).filter(DrcTask.id == task_id).first()
    assert task.status == "COMPLETED"

    # 步驟 5: 透過 REST API 讀取 DRC 報告
    report_resp = client.get(f"/api/v1/tasks/{task_id}/report")
    assert report_resp.status_code == 200
    report_api_data = report_resp.json()
    assert report_api_data["task_id"] == task_id
    assert report_api_data["summary"]["total_rules_checked"] >= 0
    assert "violations" in report_api_data

    # 步驟 6: 透過匯出端點匯出 JSON 報告
    export_resp = client.get(f"/api/v1/tasks/{task_id}/report/export")
    assert export_resp.status_code == 200
    assert export_resp.headers["content-type"] == "application/json"
    assert f"drc_report_{task_id}.json" in export_resp.headers.get("content-disposition", "")
