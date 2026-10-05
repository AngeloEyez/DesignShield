"""
系統設定資料模型 (System Settings Model)

動態管理系統運作參數 (如檔案保留天數、逾時時間等)，支援透過 Web UI 即時修改與查詢。
"""

from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, JSON
from backend.app.db.session import Base


class SystemSetting(Base):
    """
    系統設定資料表 (system_settings)
    
    Attributes:
        key (str): 設定鍵值 (Primary Key)
        value (dict/any): 設定內容 (JSON 格式)
        description (str): 設定用途說明
        updated_at (datetime): 最後更新時間
    """
    __tablename__ = "system_settings"

    key = Column(String(64), primary_key=True)
    value = Column(JSON, nullable=False)
    description = Column(String(255), nullable=True)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return f"<SystemSetting(key='{self.key}')>"
