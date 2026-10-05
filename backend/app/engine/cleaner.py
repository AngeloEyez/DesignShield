"""
磁碟空間管理與檔案垃圾回收模組 (Storage Garbage Collection & Cleaner)

負責定期掃描 storage 目錄 (uploads, staging, reports)，
依據系統設定之保留天數清理過期檔案與解壓暫存目錄，防止磁碟空間耗盡。
"""

import os
import shutil
import time
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from backend.app.core.config import settings

logger = logging.getLogger("designshield.cleaner")


def get_directory_size_and_count(dir_path: str) -> Dict[str, Any]:
    """
    計算指定目錄之總檔案數與佔用位元組 (bytes)
    
    Args:
        dir_path: 目錄絕對路徑
        
    Returns:
        Dict: {"file_count": int, "total_bytes": int}
    """
    if not os.path.exists(dir_path):
        return {"file_count": 0, "total_bytes": 0}
        
    file_count = 0
    total_bytes = 0
    for root, _, files in os.walk(dir_path):
        for f in files:
            fp = os.path.join(root, f)
            try:
                if not os.path.islink(fp):
                    total_bytes += os.path.getsize(fp)
                    file_count += 1
            except (OSError, FileNotFoundError):
                continue
                
    return {"file_count": file_count, "total_bytes": total_bytes}


def get_all_storage_stats() -> Dict[str, Any]:
    """
    彙整所有 storage 子目錄 (uploads, staging, reports) 的空間佔用指標
    
    Returns:
        Dict: 各目錄統計與合計總大小
    """
    base_dir = os.path.abspath(settings.STORAGE_DIR)
    uploads_dir = os.path.join(base_dir, "uploads")
    staging_dir = os.path.join(base_dir, "staging")
    reports_dir = os.path.join(base_dir, "reports")
    
    uploads_stat = get_directory_size_and_count(uploads_dir)
    staging_stat = get_directory_size_and_count(staging_dir)
    reports_stat = get_directory_size_and_count(reports_dir)
    
    total_files = uploads_stat["file_count"] + staging_stat["file_count"] + reports_stat["file_count"]
    total_bytes = uploads_stat["total_bytes"] + staging_stat["total_bytes"] + reports_stat["total_bytes"]
    
    return {
        "storage_root": base_dir,
        "uploads": uploads_stat,
        "staging": staging_stat,
        "reports": reports_stat,
        "total_files": total_files,
        "total_bytes": total_bytes,
        "total_mb": round(total_bytes / (1024 * 1024), 2)
    }


def cleanup_expired_files(
    retention_days: int = 7,
    dry_run: bool = False,
    include_reports: bool = False
) -> Dict[str, Any]:
    """
    清除超過保留期限之暫存與上傳檔案
    
    Args:
        retention_days: 保留天數，預設 7 天；若為 0 則清除所有暫存檔案
        dry_run: 若為 True 僅模擬並計算欲刪除之項目，不實際執行刪除
        include_reports: 是否連同過期的報告檔案一同清除 (預設為 False 避免刪除審查結果)
        
    Returns:
        Dict: 清理結果摘要，包含刪除個數、釋放空間 (bytes) 與清單
    """
    base_dir = os.path.abspath(settings.STORAGE_DIR)
    target_dirs = [
        os.path.join(base_dir, "uploads"),
        os.path.join(base_dir, "staging")
    ]
    if include_reports:
        target_dirs.append(os.path.join(base_dir, "reports"))
        
    cutoff_time = time.time() - (retention_days * 86400)
    
    deleted_files_count = 0
    freed_bytes = 0
    deleted_paths: List[str] = []
    
    for t_dir in target_dirs:
        if not os.path.exists(t_dir):
            continue
            
        for entry in os.listdir(t_dir):
            entry_path = os.path.join(t_dir, entry)
            try:
                mtime = os.path.getmtime(entry_path)
                if mtime < cutoff_time:
                    # 計算檔案或目錄大小
                    if os.path.isdir(entry_path):
                        dir_stat = get_directory_size_and_count(entry_path)
                        freed_bytes += dir_stat["total_bytes"]
                        deleted_files_count += dir_stat["file_count"]
                        deleted_paths.append(entry_path)
                        if not dry_run:
                            shutil.rmtree(entry_path, ignore_errors=True)
                            logger.info("Cleaned up expired directory: %s", entry_path)
                    else:
                        fsize = os.path.getsize(entry_path)
                        freed_bytes += fsize
                        deleted_files_count += 1
                        deleted_paths.append(entry_path)
                        if not dry_run:
                            os.remove(entry_path)
                            logger.info("Cleaned up expired file: %s", entry_path)
            except Exception as e:
                logger.warning("Error processing file during cleanup (%s): %s", entry_path, e)
                
    return {
        "retention_days": retention_days,
        "dry_run": dry_run,
        "deleted_files_count": deleted_files_count,
        "freed_bytes": freed_bytes,
        "freed_mb": round(freed_bytes / (1024 * 1024), 2),
        "deleted_paths": deleted_paths
    }


def cleanup_task_artifacts(task_id: str) -> bool:
    """
    清除特定任務的 staging 解壓目錄
    
    Args:
        task_id: 任務 UUID
        
    Returns:
        bool: 是否成功清理
    """
    staging_dir = os.path.join(settings.STORAGE_DIR, "staging", task_id)
    if os.path.exists(staging_dir) and os.path.isdir(staging_dir):
        try:
            shutil.rmtree(staging_dir, ignore_errors=True)
            logger.info("Successfully cleaned up staging artifacts for task: %s", task_id)
            return True
        except Exception as e:
            logger.warning("Failed to clean up staging directory for task %s: %s", task_id, e)
            return False
    return False
