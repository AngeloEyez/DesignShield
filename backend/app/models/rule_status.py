"""
規則狀態資料模型 (Rule Status Model)

職責:
管理 Level 1 ~ Level 3 規則的啟用/停用 (enabled) 執行期狀態，
實現 GitOps (YAML 定義) 與 Runtime State (DB 狀態) 的職責解耦。
"""

from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime
from backend.app.db.session import Base


class RuleStatus(Base):
    """
    規則啟用狀態資料表 (rule_statuses)

    Attributes:
        rule_name (str): 規則唯一識別碼 (Primary Key, 小寫蛇形)
        level (str): 規則層級 ("level1", "level2", "level3")
        category_path (str): 所屬目錄相對路徑 (如 "rules/interfaces", "components")
        enabled (bool): 啟用狀態 (True/False)
        updated_at (datetime): 最後更新時間戳 (UTC)
    """
    __tablename__ = "rule_statuses"

    rule_name = Column(String(128), primary_key=True, index=True)
    level = Column(String(32), nullable=False, index=True)
    category_path = Column(String(256), nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    def __repr__(self) -> str:
        return f"<RuleStatus(rule_name='{self.rule_name}', level='{self.level}', enabled={self.enabled})>"
