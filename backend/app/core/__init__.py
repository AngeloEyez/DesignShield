"""
核心配置與共用邏輯模組
"""
from backend.app.core.config import settings
from backend.app.core.task_logger import TaskLogger, get_task_logger

__all__ = ["settings", "TaskLogger", "get_task_logger"]

