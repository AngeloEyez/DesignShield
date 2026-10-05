"""
DRC 檢查報告資料模型 (DRC Report Model)

落地儲存分析任務最終產生的違規報告清單與總結統計。
"""

from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.db.session import Base


class DrcReport(Base):
    """
    DRC 分析報告資料表 (drc_reports)
    
    Attributes:
        task_id (str): 對應任務 ID (Primary Key, Foreign Key)
        summary (dict): 總結資訊 (包含規則數、PASS/FAIL/WARNING 統計與類別分佈)
        violations (list): 檢測項目與違規項目清單
        created_at (datetime): 報告產出時間
    """
    __tablename__ = "drc_reports"

    task_id = Column(String(36), ForeignKey("drc_tasks.id", ondelete="CASCADE"), primary_key=True)
    summary = Column(JSON, nullable=False, default=dict)
    violations = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # 關聯屬性
    task = relationship("DrcTask", back_populates="report")

    def __repr__(self) -> str:
        return f"<DrcReport(task_id='{self.task_id}')>"
