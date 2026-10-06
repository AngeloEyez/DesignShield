"""
任務生命週期、狀態控制與孤兒清理單元測試 (Task Lifecycle & Cleanup Tests)
"""

import os
import time
from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.config import settings
from backend.app.models.task import DrcTask
from backend.app.models.step_status import StepStatus
from backend.app.engine.cleaner import (
    cleanup_expired_tasks_and_orphan_files,
    delete_task_storage_artifacts,
)


@pytest.fixture
def client(db_session):
    return TestClient(app)


def test_list_tasks_and_filter(client, db_session):
    """測試 GET /api/v1/tasks 清單與篩選功能"""
    t1 = DrcTask(id="task-111", project_name="Proj 1", status="PENDING", task_type="DRC")
    t2 = DrcTask(id="task-222", project_name="Proj 2", status="COMPLETED", task_type="DRC")
    t3 = DrcTask(id="task-333", project_name="Proj 3", status="PROCESSING", task_type="RULE_EXTRACTION")
    db_session.add_all([t1, t2, t3])
    db_session.commit()

    resp = client.get("/api/v1/tasks")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 3

    resp_completed = client.get("/api/v1/tasks?status=COMPLETED")
    assert resp_completed.status_code == 200
    data_completed = resp_completed.json()
    assert all(t["status"] == "COMPLETED" for t in data_completed["tasks"])

    resp_type = client.get("/api/v1/tasks?task_type=RULE_EXTRACTION")
    assert resp_type.status_code == 200
    data_type = resp_type.json()
    assert any(t["id"] == "task-333" for t in data_type["tasks"])


def test_stop_task(client, db_session):
    """測試 POST /api/v1/tasks/{task_id}/stop 中斷任務"""
    task = DrcTask(id="task-stop-test", project_name="Stop Test", status="PROCESSING")
    step = StepStatus(task_id="task-stop-test", step_name="PARSE_AND_GRAPH", status="PROCESSING")
    db_session.add_all([task, step])
    db_session.commit()

    resp = client.post("/api/v1/tasks/task-stop-test/stop")
    assert resp.status_code == 200
    res = resp.json()
    assert res["status"] == "CANCELLED"

    db_session.refresh(task)
    db_session.refresh(step)
    assert task.status == "CANCELLED"
    assert step.status == "SKIPPED"


def test_delete_task_and_artifacts(client, db_session, tmp_path, monkeypatch):
    """測試 DELETE /api/v1/tasks/{task_id} 清除任務與實體磁碟檔案"""
    task_id = "task-delete-me"
    task = DrcTask(id=task_id, project_name="Delete Me", status="COMPLETED")
    db_session.add(task)
    db_session.commit()

    mock_base = tmp_path / "storage"
    mock_uploads = mock_base / "uploads"
    mock_staging = mock_base / "staging" / task_id
    mock_uploads.mkdir(parents=True)
    mock_staging.mkdir(parents=True)

    dummy_upload = mock_uploads / f"{task_id}.zip"
    dummy_upload.write_text("dummy zip content")
    dummy_stage_file = mock_staging / "file.xml"
    dummy_stage_file.write_text("<xml></xml>")

    monkeypatch.setattr(settings, "STORAGE_DIR", str(mock_base))
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(mock_uploads))
    monkeypatch.setattr(settings, "STAGING_DIR", str(mock_base / "staging"))

    resp = client.delete(f"/api/v1/tasks/{task_id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "DELETED"

    # 確認 DB 刪除
    assert db_session.query(DrcTask).filter(DrcTask.id == task_id).first() is None
    # 確認實體磁碟刪除
    assert not dummy_upload.exists()
    assert not mock_staging.exists()


def test_archive_and_graph_details_endpoints(client, db_session):
    """測試 /archive-details 與 /graph-details 檢視端點"""
    task = DrcTask(id="task-details-test", project_name="Details Test", status="READY_FOR_RUN")
    db_session.add(task)
    db_session.commit()

    r1 = client.get("/api/v1/tasks/task-details-test/archive-details")
    assert r1.status_code == 200
    d1 = r1.json()
    assert "file_count" in d1
    assert "files" in d1

    r2 = client.get("/api/v1/tasks/task-details-test/graph-details")
    assert r2.status_code == 200
    d2 = r2.json()
    assert "components_count" in d2
    assert "buses" in d2
    assert "main_ics" in d2


def test_cleanup_expired_and_orphan_files(db_session, tmp_path, monkeypatch):
    """測試未開始 (2天) 與已完成 (5天) 過期任務清除，以及孤兒檔案回收"""
    mock_base = tmp_path / "clean_storage"
    mock_uploads = mock_base / "uploads"
    mock_staging = mock_base / "staging"
    mock_reports = mock_base / "reports"
    mock_uploads.mkdir(parents=True)
    mock_staging.mkdir(parents=True)
    mock_reports.mkdir(parents=True)

    monkeypatch.setattr(settings, "STORAGE_DIR", str(mock_base))
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(mock_uploads))
    monkeypatch.setattr(settings, "STAGING_DIR", str(mock_staging))
    monkeypatch.setattr(settings, "REPORT_DIR", str(mock_reports))

    now = datetime.now(timezone.utc)
    # 1. 建立未開始過期任務 (3 天前建立，> 2 天)
    old_unstarted = DrcTask(
        id="task-old-unstarted",
        project_name="Old Unstarted",
        status="READY_FOR_RUN",
        created_at=now - timedelta(days=3),
        updated_at=now - timedelta(days=3),
    )
    # 2. 建立已完成過期任務 (6 天前建立，> 5 天)
    old_finished = DrcTask(
        id="task-old-finished",
        project_name="Old Finished",
        status="COMPLETED",
        created_at=now - timedelta(days=6),
        updated_at=now - timedelta(days=6),
    )
    # 3. 建立新鮮任務 (今天)
    fresh_task = DrcTask(
        id="task-fresh",
        project_name="Fresh Task",
        status="COMPLETED",
        created_at=now - timedelta(days=1),
        updated_at=now - timedelta(days=1),
    )
    db_session.add_all([old_unstarted, old_finished, fresh_task])
    db_session.commit()

    # 建立對應檔案
    (mock_uploads / "task-old-unstarted.zip").write_text("old unstarted zip")
    (mock_uploads / "task-old-finished.zip").write_text("old finished zip")
    (mock_uploads / "task-fresh.zip").write_text("fresh zip")

    # 建立一個孤兒檔案 (mtime 設為 2 小時前)
    orphan_file = mock_uploads / "orphan-unknown.zip"
    orphan_file.write_text("orphan content")
    two_hours_ago = time.time() - 7200
    os.utime(str(orphan_file), (two_hours_ago, two_hours_ago))

    # 執行清理
    res = cleanup_expired_tasks_and_orphan_files(db_session, retention_unstarted=2, retention_finished=5)

    assert res["expired_tasks_count"] == 2
    assert "task-old-unstarted" in res["deleted_task_ids"]
    assert "task-old-finished" in res["deleted_task_ids"]
    assert res["orphan_files_count"] >= 1

    # 驗證 DB 狀態
    assert db_session.query(DrcTask).filter(DrcTask.id == "task-old-unstarted").first() is None
    assert db_session.query(DrcTask).filter(DrcTask.id == "task-old-finished").first() is None
    assert db_session.query(DrcTask).filter(DrcTask.id == "task-fresh").first() is not None

    # 驗證實體檔案
    assert not (mock_uploads / "task-old-unstarted.zip").exists()
    assert not (mock_uploads / "task-old-finished.zip").exists()
    assert not orphan_file.exists()
    assert (mock_uploads / "task-fresh.zip").exists()
