"""
設計規則資料模型 (DRC Rule Model)

儲存傳統啟發式圖論規則 (HEURISTIC) 與大語言模型邏輯推理規則 (LLM)。
"""

from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, Text, JSON
from backend.app.db.session import Base


class DrcRule(Base):
    """
    DRC 規則資料表 (drc_rules)
    
    Attributes:
        id (str): 規則代碼 (例如: RULE-PWR-CAP-DERATING, 主鍵)
        name (str): 規則中文名稱
        category (str): 規則分類 (例如: Bus Integrity, Power Domain, Pin Connection)
        check_type (str): 檢查型態 (HEURISTIC: 傳統演算法, LLM: 本地大模型推理)
        is_active (bool): 是否啟用該規則
        parameters (dict): 規則自訂參數 (JSON)
        prompt_template (str): LLM 專用提示詞樣板 (若為 HEURISTIC 則為空)
        context_extractor (str): 圖譜上下文抽取函式識別碼
        created_at (datetime): 建立時間
    """
    __tablename__ = "drc_rules"

    id = Column(String(64), primary_key=True)
    name = Column(String(255), nullable=False)
    category = Column(String(64), nullable=False, index=True)
    check_type = Column(String(32), nullable=False, default="HEURISTIC")
    is_active = Column(Boolean, nullable=False, default=True)
    parameters = Column(JSON, default=dict)
    prompt_template = Column(Text, nullable=True)
    context_extractor = Column(String(128), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return f"<DrcRule(id='{self.id}', name='{self.name}', type='{self.check_type}')>"
