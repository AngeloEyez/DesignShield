"""
線路檢查任務資料模型 (DRC Task Model)

記錄 DRC 任務之專案資訊、生命週期狀態、預先分析摘要與使用者選定之檢驗規則。
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, JSON
from sqlalchemy.orm import relationship
from backend.app.db.session import Base


class DrcTask(Base):
    """
    DRC 分析任務資料表 (drc_tasks)
    
    Attributes:
        id (str): 任務唯一識別碼 (UUID4 字串)
        project_name (str): 專案名稱
        status (str): 任務當前狀態 (PENDING, READY_FOR_RUN, PROCESSING, COMPLETED, FAILED, CANCELLED)
        pre_analysis_summary (dict): 輕量預先分析結果摘要
        selected_rules (list): 使用者選定進行正式檢驗的 Rule ID 清單
        created_at (datetime): 任務建立時間
        updated_at (datetime): 任務更新時間
    """
    __tablename__ = "drc_tasks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_name = Column(String(255), nullable=False)
    task_type = Column(String(64), nullable=False, default="DRC")
    status = Column(String(32), nullable=False, default="PENDING")
    pre_analysis_summary = Column(JSON, default=dict)
    selected_rules = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # 關聯屬性
    step_statuses = relationship("StepStatus", back_populates="task", cascade="all, delete-orphan", order_by="StepStatus.started_at")
    report = relationship("DrcReport", back_populates="task", uselist=False, cascade="all, delete-orphan")
    logs = relationship("TaskLog", back_populates="task", cascade="all, delete-orphan", order_by="TaskLog.created_at")


    def __repr__(self) -> str:
        return f"<DrcTask(id='{self.id}', project='{self.project_name}', status='{self.status}')>"
