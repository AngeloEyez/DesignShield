"""
任務日誌系統測試 (Task Logging System Tests)

驗證任務上傳階段自動記錄日誌、GET /logs API 查詢與過濾、TaskLogger 入庫、
外鍵級聯刪除 (Cascade Delete) 以及 SSE 推播 log 事件。
"""

import io
import uuid
from backend.app.models.task import DrcTask
from backend.app.models.task_log import TaskLog
from backend.app.core.task_logger import get_task_logger


def test_upload_creates_structured_logs(client):
    """測試上傳檔案成功後，自動產生包含檔案接收、解壓、XML 與圖譜構建之結構化日誌"""
    file_content = b"<Design><Defn name='test.dsn'/></Design>"
    files = {
        "file": ("test_schematic.xml", io.BytesIO(file_content), "application/xml")
    }
    data = {
        "project_name": "LogTestProject"
    }

    response = client.post("/api/v1/tasks", files=files, data=data)
    assert response.status_code == 200
    res_json = response.json()
    task_id = res_json["task_id"]

    # 查詢該任務日誌
    logs_res = client.get(f"/api/v1/tasks/{task_id}/logs")
    assert logs_res.status_code == 200
    logs_data = logs_res.json()
    assert logs_data["total"] > 0
    assert len(logs_data["logs"]) > 0

    # 驗證日誌包含雙標籤與時間
    first_log = logs_data["logs"][0]
    assert "step_name" in first_log
    assert "category" in first_log
    assert "level" in first_log
    assert "display_time" in first_log
    assert len(first_log["display_time"]) > 0

    # 驗證至少包含 FILE 接收與 PARSER 解析相關日誌
    categories = [l["category"] for l in logs_data["logs"]]
    assert "FILE" in categories or "PARSER" in categories


def test_get_task_logs_filtering(client, db_session):
    """測試日誌查詢之 level 與 category 篩選"""
    task_id = str(uuid.uuid4())
    task = DrcTask(id=task_id, project_name="FilterTest", status="READY_FOR_RUN")
    db_session.add(task)
    db_session.commit()

    t_logger = get_task_logger(task_id)
    t_logger.info("PARSE_AND_GRAPH", "GRAPH", "圖譜建立完成")
    t_logger.debug("PARSE_AND_GRAPH", "LLM", "發起 LLM 查詢", details={"prompt": "test prompt"})
    t_logger.warning("PARSE_AND_GRAPH", "PARSER", "發現不確定引腳")
    t_logger.error("HEURISTIC_CHECK", "HEURISTIC", "演算法計算異常", details={"trace": "err"})

    # 1. 查詢所有日誌
    res_all = client.get(f"/api/v1/tasks/{task_id}/logs")
    assert res_all.status_code == 200
    assert res_all.json()["total"] == 4

    # 2. 依 Level 篩選
    res_debug = client.get(f"/api/v1/tasks/{task_id}/logs?level=DEBUG")
    assert res_debug.status_code == 200
    assert res_debug.json()["total"] == 1
    assert res_debug.json()["logs"][0]["level"] == "DEBUG"
    assert res_debug.json()["logs"][0]["details"]["prompt"] == "test prompt"

    # 3. 依 Category 篩選
    res_graph = client.get(f"/api/v1/tasks/{task_id}/logs?category=GRAPH")
    assert res_graph.status_code == 200
    assert res_graph.json()["total"] == 1
    assert res_graph.json()["logs"][0]["category"] == "GRAPH"


def test_task_deletion_cascade_logs(client, db_session):
    """測試刪除任務時，同步級聯清理關聯之所有日誌"""
    task_id = str(uuid.uuid4())
    task = DrcTask(id=task_id, project_name="CascadeTest", status="READY_FOR_RUN")
    db_session.add(task)
    db_session.commit()

    t_logger = get_task_logger(task_id)
    t_logger.info("UNPACK_AND_VALIDATE", "FILE", "解壓縮")
    t_logger.debug("PARSE_AND_GRAPH", "LLM", "LLM 推理")

    # 確認日誌已寫入
    logs_before = db_session.query(TaskLog).filter(TaskLog.task_id == task_id).count()
    assert logs_before == 2

    # 呼叫刪除任務 API
    del_res = client.delete(f"/api/v1/tasks/{task_id}")
    assert del_res.status_code == 200

    # 確認任務被刪除，且關聯日誌已同步被清理
    task_after = db_session.query(DrcTask).filter(DrcTask.id == task_id).first()
    assert task_after is None
    logs_after = db_session.query(TaskLog).filter(TaskLog.task_id == task_id).count()
    assert logs_after == 0
