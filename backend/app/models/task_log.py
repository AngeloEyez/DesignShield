"""
任務日誌資料模型 (Task Log Model)

持久化儲存 DRC 任務執行過程中的各級日誌 (INFO, WARNING, ERROR, DEBUG)，
支援 Timeline 步驟與用途分類雙標籤、詳細結構化除錯資訊 (details)，以及隨任務級聯清理。
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.db.session import Base


class TaskLog(Base):
    """
    任務日誌資料表 (task_logs)
    
    Attributes:
        id (str): 日誌唯一識別碼 (UUID4 字串)
        task_id (str): 所屬任務 ID (Foreign Key，級聯刪除)
        step_name (str): 第一標籤：對應 Timeline 主要步驟名稱 (如 UNPACK_AND_VALIDATE, PARSE_AND_GRAPH, HEURISTIC_CHECK, LLM_REASONING, GENERATE_REPORT)
        category (str): 第二標籤：用途分類 (如 LLM, DB, VLM, PARSER, GRAPH, FILE, HEURISTIC, SYSTEM)
        level (str): 日誌分級 (INFO, WARNING, ERROR, DEBUG)
        message (str): 日誌主訊息 (單行摘要)
        details (dict): 結構化詳細資訊 (如 LLM Prompt 與回覆、錯誤堆疊、節點統計等)
        created_at (datetime): 記錄產生時間 (含時區)
    """
    __tablename__ = "task_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String(36), ForeignKey("drc_tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    step_name = Column(String(64), nullable=False, index=True)
    category = Column(String(32), nullable=False, index=True)
    level = Column(String(16), nullable=False, default="INFO", index=True)
    message = Column(Text, nullable=False)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)

    # 關聯屬性
    task = relationship("DrcTask", back_populates="logs")

    def __repr__(self) -> str:
        return f"<TaskLog(id='{self.id}', task_id='{self.task_id}', level='{self.level}', step='{self.step_name}', category='{self.category}')>"
