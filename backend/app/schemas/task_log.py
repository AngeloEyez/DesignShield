"""
任務日誌資料結構綱要 (Task Log Schemas)

定義 TaskLog API 回應格式，包含四級日誌分級、雙標籤與詳細資訊。
"""

from datetime import datetime
from typing import Optional, Any, List
from pydantic import BaseModel, Field, ConfigDict, computed_field


class TaskLogResponse(BaseModel):
    """單筆任務日誌回應綱要"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    task_id: str
    step_name: str
    category: str
    level: str = Field(description="INFO, WARNING, ERROR, DEBUG")
    message: str
    details: Optional[Any] = None
    created_at: datetime

    @computed_field
    @property
    def display_time(self) -> str:
        """顯示時間格式: MM-DD HH:mm:ss"""
        if self.created_at:
            return self.created_at.strftime("%m-%d %H:%M:%S")
        return ""



class TaskLogListResponse(BaseModel):
    """任務日誌清單回應綱要"""
    total: int
    task_id: str
    logs: List[TaskLogResponse]
