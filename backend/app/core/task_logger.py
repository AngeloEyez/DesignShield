"""
任務專屬結構化日誌記錄器 (Task Logger Module)

提供各業務模組 (上傳、解壓、XML 解析、圖譜構建、啟發式比對、大語言模型推理、報告產出)
統一且線程安全的日誌記錄介面。同步入庫 task_logs 表並支援 SSE 即時推播。
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, Any, Dict, List

import backend.app.db.session as db_session
from backend.app.models.task_log import TaskLog

sys_logger = logging.getLogger("designshield.task_logger")


class TaskLogger:
    """任務專屬結構化日誌器"""

    def __init__(self, task_id: str):
        self.task_id = task_id

    def log(
        self,
        step_name: str,
        category: str,
        level: str,
        message: str,
        details: Optional[Any] = None
    ) -> Optional[TaskLog]:
        """
        記錄一則結構化任務日誌並寫入資料庫
        
        Args:
            step_name: 主要工作流步驟 (例如 UNPACK_AND_VALIDATE, PARSE_AND_GRAPH 等)
            category: 用途分類 (例如 LLM, DB, VLM, PARSER, GRAPH, FILE, HEURISTIC, SYSTEM 等)
            level: 分級 (INFO, WARNING, ERROR, DEBUG)
            message: 日誌主訊息 (單行摘要)
            details: 結構化詳細資訊 (可為 dict, list, string 或 None)
            
        Returns:
            Optional[TaskLog]: 持久化後的日誌實例
        """
        level_upper = level.upper()
        now_dt = datetime.now(timezone.utc)
        
        # 1. 印出至系統 Console 日誌 (便於本機終端除錯)
        log_fmt = f"[{self.task_id[:8]}][{step_name}][{category}][{level_upper}] {message}"
        if level_upper == "ERROR":
            sys_logger.error(log_fmt)
        elif level_upper == "WARNING":
            sys_logger.warning(log_fmt)
        elif level_upper == "DEBUG":
            sys_logger.debug(log_fmt)
        else:
            sys_logger.info(log_fmt)

        # 2. 持久化寫入 task_logs 資料庫表
        db = db_session.SessionLocal()
        try:
            log_entry = TaskLog(
                id=str(uuid.uuid4()),
                task_id=self.task_id,
                step_name=step_name,
                category=category,
                level=level_upper,
                message=message,
                details=details,
                created_at=now_dt
            )
            db.add(log_entry)
            db.commit()
            db.refresh(log_entry)
            return log_entry
        except Exception as e:
            db.rollback()
            sys_logger.error("Failed to persist task log into database for task %s: %s", self.task_id, e)
            return None
        finally:
            db.close()

    def info(self, step_name: str, category: str, message: str, details: Optional[Any] = None) -> Optional[TaskLog]:
        """記錄 INFO 等級日誌 (主要步驟進度)"""
        return self.log(step_name, category, "INFO", message, details)

    def warning(self, step_name: str, category: str, message: str, details: Optional[Any] = None) -> Optional[TaskLog]:
        """記錄 WARNING 等級日誌 (模糊/不確定/需確認)"""
        return self.log(step_name, category, "WARNING", message, details)

    def error(self, step_name: str, category: str, message: str, details: Optional[Any] = None) -> Optional[TaskLog]:
        """記錄 ERROR 等級日誌 (異常錯誤與 detail)"""
        return self.log(step_name, category, "ERROR", message, details)

    def debug(self, step_name: str, category: str, message: str, details: Optional[Any] = None) -> Optional[TaskLog]:
        """記錄 DEBUG 等級日誌 (子步驟、LLM查詢/回覆、除錯細節)"""
        return self.log(step_name, category, "DEBUG", message, details)


def get_task_logger(task_id: str) -> TaskLogger:
    """取得特定任務的 TaskLogger 實例"""
    return TaskLogger(task_id)
