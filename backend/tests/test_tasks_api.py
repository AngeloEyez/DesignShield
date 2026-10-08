"""
任務 API 端點測試 (Task API Endpoints Tests)

驗證檔案上傳、預先分析、啟動正式 DRC、狀態查詢與報告產出。
"""

import io
import uuid
from backend.app.models.task import DrcTask
from backend.app.models.report import DrcReport
from backend.app.models.step_status import StepStatus


def test_upload_and_pre_analyze_api(client):
    """測試上傳檔案並取得輕量預先分析結果 (POST /api/v1/tasks)"""
    file_content = b"<Design><Defn name='test.dsn'/></Design>"
    files = {
        "file": ("test_schematic.xml", io.BytesIO(file_content), "application/xml")
    }
    data = {
        "project_name": "Test_Carrier_Board"
    }

    response = client.post("/api/v1/tasks", files=files, data=data)
    assert response.status_code == 200
    res_json = response.json()

    assert "task_id" in res_json
    task_id = res_json["task_id"]
    assert res_json["project_name"] == "Test_Carrier_Board"
    # 即時返回之初始狀態為 PRE_ANALYZING，避免阻塞 HTTP 回應
    assert res_json["status"] == "PRE_ANALYZING"

    # 背景任務執行完畢後，查詢任務狀態應轉為 READY_FOR_RUN 且具備推薦規則
    status_resp = client.get(f"/api/v1/tasks/{task_id}/status")
    assert status_resp.status_code == 200
    status_json = status_resp.json()
    assert status_json["status"] == "READY_FOR_RUN"
    assert "pre_analysis_summary" in status_json
    assert len(status_json["recommended_rules"]) > 0


def test_start_formal_drc_api(client, db_session):
    """測試確認規則並啟動正式 DRC 任務 (POST /api/v1/tasks/{task_id}/run)"""
    task_id = str(uuid.uuid4())
    task = DrcTask(id=task_id, project_name="RunTest", status="READY_FOR_RUN")
    db_session.add(task)
    db_session.commit()

    payload = {
        "selected_rule_ids": ["RULE-BUS-I2C-ADDR", "RULE-PWR-CAP-DERATING"]
    }
    response = client.post(f"/api/v1/tasks/{task_id}/run", json=payload)
    assert response.status_code == 202
    res_json = response.json()

    assert res_json["task_id"] == task_id
    assert res_json["status"] == "PROCESSING"

    # 驗證資料庫中的選定規則
    refreshed_task = db_session.query(DrcTask).filter(DrcTask.id == task_id).first()
    assert refreshed_task.selected_rules == payload["selected_rule_ids"]


def test_start_formal_drc_not_found_or_invalid_status(client, db_session):
    """測試任務不存在或狀態不允許啟動時之錯誤回應"""
    # 404
    non_existent_id = str(uuid.uuid4())
    res_404 = client.post(f"/api/v1/tasks/{non_existent_id}/run", json={"selected_rule_ids": []})
    assert res_404.status_code == 404

    # 400
    task_id = str(uuid.uuid4())
    task = DrcTask(id=task_id, project_name="InvalidStatusTest", status="COMPLETED")
    db_session.add(task)
    db_session.commit()

    res_400 = client.post(f"/api/v1/tasks/{task_id}/run", json={"selected_rule_ids": []})
    assert res_400.status_code == 400


def test_get_task_status_api(client, db_session):
    """測試查詢任務狀態與步驟進度 (GET /api/v1/tasks/{task_id}/status)"""
    task_id = str(uuid.uuid4())
    task = DrcTask(id=task_id, project_name="StatusTest", status="PROCESSING")
    step = StepStatus(task_id=task_id, step_name="PARSE_AND_GRAPH", status="PROCESSING", log_message="建圖中")
    db_session.add(task)
    db_session.add(step)
    db_session.commit()

    response = client.get(f"/api/v1/tasks/{task_id}/status")
    assert response.status_code == 200
    res_json = response.json()

    assert res_json["task_id"] == task_id
    assert res_json["status"] == "PROCESSING"
    assert len(res_json["steps"]) == 1
    assert res_json["steps"][0]["step_name"] == "PARSE_AND_GRAPH"


def test_get_task_report_api(client, db_session):
    """測試取得最終報告 (GET /api/v1/tasks/{task_id}/report)"""
    task_id = str(uuid.uuid4())
    task = DrcTask(id=task_id, project_name="ReportTest", status="COMPLETED")
    report = DrcReport(
        task_id=task_id,
        summary={"total_rules_checked": 1, "pass_count": 1, "fail_count": 0, "warning_count": 0, "skip_count": 0, "pass_rate_percentage": 100.0, "by_category": {}},
        violations=[{
            "item_id": "v-1",
            "rule_id": "RULE-BUS-I2C-ADDR",
            "rule_category": "Bus Integrity",
            "rule_title": "I2C 匯流排地址檢查",
            "check_type": "HEURISTIC",
            "status": "PASS",
            "severity": "INFO",
            "target_nodes": {"components": ["U1"], "nets": ["I2C_SDA"], "page_indices": [1]},
            "description": "無地址衝突",
            "evidence_trail": {}
        }]
    )
    db_session.add(task)
    db_session.add(report)
    db_session.commit()

    response = client.get(f"/api/v1/tasks/{task_id}/report")
    assert response.status_code == 200
    res_json = response.json()

    assert res_json["task_id"] == task_id
    assert res_json["summary"]["pass_count"] == 1
    assert len(res_json["violations"]) == 1
    assert res_json["violations"][0]["rule_id"] == "RULE-BUS-I2C-ADDR"


def test_get_task_report_not_found(client, db_session):
    """測試報告尚未產出時回傳 404"""
    task_id = str(uuid.uuid4())
    task = DrcTask(id=task_id, project_name="NoReportTest", status="PROCESSING")
    db_session.add(task)
    db_session.commit()

    response = client.get(f"/api/v1/tasks/{task_id}/report")
    assert response.status_code == 404


def test_graph_cache_persistence_and_reuse(client):
    """測試預先分析完成後圖譜二進位快取落地且後續可重用"""
    import os
    from backend.app.core.config import settings
    from backend.app.workflows.drc_workflow import get_graph_cache_path, load_task_graph

    file_content = b"<Design><Defn name='cache_test.dsn'/></Design>"
    files = {
        "file": ("cache_schematic.xml", io.BytesIO(file_content), "application/xml")
    }
    data = {"project_name": "CacheTestProject"}

    resp = client.post("/api/v1/tasks", files=files, data=data)
    assert resp.status_code == 200
    task_id = resp.json()["task_id"]

    # 驗證快取檔案已落地
    cache_path = get_graph_cache_path(task_id)
    assert os.path.exists(cache_path), f"圖譜快取檔案應存在於 {cache_path}"

    # 驗證 load_task_graph 可直接讀取快取
    G = load_task_graph(task_id)
    assert G is not None

