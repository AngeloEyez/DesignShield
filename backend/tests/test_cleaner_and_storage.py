"""
磁碟空間管理與檔案垃圾回收單元測試 (Storage Cleaner & Stats Tests)
"""

import os
import time
import shutil
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.config import settings
from backend.app.engine.cleaner import (
    get_directory_size_and_count,
    get_all_storage_stats,
    cleanup_expired_files,
    cleanup_task_artifacts,
)


@pytest.fixture
def mock_storage(tmp_path, monkeypatch):
    """建立模擬 storage 目錄環境"""
    mock_base = tmp_path / "mock_storage"
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
    
    return {
        "base": str(mock_base),
        "uploads": str(mock_uploads),
        "staging": str(mock_staging),
        "reports": str(mock_reports)
    }


def test_directory_size_and_count(mock_storage):
    """測試目錄檔案數量與位元組計算"""
    uploads_dir = mock_storage["uploads"]
    
    # 建立兩個測試檔案
    f1 = os.path.join(uploads_dir, "test1.txt")
    f2 = os.path.join(uploads_dir, "test2.txt")
    with open(f1, "w") as f:
        f.write("hello" * 100) # 500 bytes
    with open(f2, "w") as f:
        f.write("world" * 100) # 500 bytes
        
    stats = get_directory_size_and_count(uploads_dir)
    assert stats["file_count"] == 2
    assert stats["total_bytes"] == 1000


def test_get_all_storage_stats(mock_storage):
    """測試彙整所有 storage 子目錄空間指標"""
    uploads_dir = mock_storage["uploads"]
    f1 = os.path.join(uploads_dir, "upload1.bin")
    with open(f1, "wb") as f:
        f.write(b"x" * 2048)
        
    all_stats = get_all_storage_stats()
    assert all_stats["total_files"] == 1
    assert all_stats["total_bytes"] == 2048
    assert all_stats["uploads"]["file_count"] == 1
    assert all_stats["staging"]["file_count"] == 0
    assert all_stats["reports"]["file_count"] == 0


def test_cleanup_expired_files(mock_storage):
    """測試依保留期限清理過期檔案"""
    uploads_dir = mock_storage["uploads"]
    staging_dir = mock_storage["staging"]
    
    # 建立一個過期檔案 (修改 mtime 為 10 天前)
    old_file = os.path.join(uploads_dir, "old_file.zip")
    with open(old_file, "w") as f:
        f.write("old data")
    ten_days_ago = time.time() - (10 * 86400)
    os.utime(old_file, (ten_days_ago, ten_days_ago))
    
    # 建立一個過期目錄
    old_dir = os.path.join(staging_dir, "old_staging_task")
    os.makedirs(old_dir, exist_ok=True)
    with open(os.path.join(old_dir, "sub.xml"), "w") as f:
        f.write("test xml content")
    os.utime(old_dir, (ten_days_ago, ten_days_ago))
    
    # 建立一個新鮮檔案 (今天)
    new_file = os.path.join(uploads_dir, "new_file.zip")
    with open(new_file, "w") as f:
        f.write("new data")
        
    # 先以 dry_run 測試
    dry_result = cleanup_expired_files(retention_days=7, dry_run=True)
    assert dry_result["dry_run"] is True
    assert dry_result["deleted_files_count"] >= 2
    assert os.path.exists(old_file)
    assert os.path.exists(old_dir)
    assert os.path.exists(new_file)
    
    # 正式清理
    clean_result = cleanup_expired_files(retention_days=7, dry_run=False)
    assert clean_result["dry_run"] is False
    assert not os.path.exists(old_file)
    assert not os.path.exists(old_dir)
    assert os.path.exists(new_file)


def test_cleanup_task_artifacts(mock_storage):
    """測試特定任務 staging 目錄清理"""
    task_id = "test-task-uuid-1234"
    task_staging = os.path.join(mock_storage["staging"], task_id)
    os.makedirs(task_staging, exist_ok=True)
    with open(os.path.join(task_staging, "netlist.dat"), "w") as f:
        f.write("dummy netlist")
        
    assert os.path.exists(task_staging)
    ok = cleanup_task_artifacts(task_id)
    assert ok is True
    assert not os.path.exists(task_staging)


def test_settings_api_storage_endpoints(client, mock_storage):
    """測試 Storage 指標與清理 REST API 端點"""
    # 測試 GET /api/v1/settings/storage-stats
    resp = client.get("/api/v1/settings/storage-stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "uploads" in data
    assert "staging" in data
    assert "reports" in data
    assert "total_files" in data
    
    # 測試 POST /api/v1/settings/cleanup (dry_run)
    resp2 = client.post("/api/v1/settings/cleanup?retention_days=7&dry_run=true")
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["dry_run"] is True
    assert "freed_bytes" in data2
