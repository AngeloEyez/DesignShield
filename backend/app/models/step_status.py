"""
步驟進度追蹤資料模型 (Step Status Model)

配合 DBOS 每個 Step 的執行狀態與 Log 訊息，提供前端 PrimeVue Timeline 即時渲染與斷點接續狀態回放。
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.db.session import Base


class StepStatus(Base):
    """
    步驟狀態資料表 (step_status)
    
    Attributes:
        id (str): 步驟記錄唯一識別碼 (UUID4 字串)
        task_id (str): 所屬任務 ID (Foreign Key)
        step_name (str): 步驟名稱 (例如: UNPACK_AND_VALIDATE, PARSE_AND_GRAPH, HEURISTIC_CHECK, LLM_REASONING, GENERATE_REPORT)
        status (str): 步驟狀態 (PENDING, PROCESSING, COMPLETED, FAILED, SKIPPED)
        log_message (str): 該步驟輸出的詳細日誌或摘要訊息
        started_at (datetime): 步驟開始執行時間
        completed_at (datetime): 步驟結束時間 (可為空)
    """
    __tablename__ = "step_status"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String(36), ForeignKey("drc_tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    step_name = Column(String(128), nullable=False)
    status = Column(String(32), nullable=False, default="PENDING")
    log_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # 關聯屬性
    task = relationship("DrcTask", back_populates="step_statuses")

    def __repr__(self) -> str:
        return f"<StepStatus(task_id='{self.task_id}', step='{self.step_name}', status='{self.status}')>"
