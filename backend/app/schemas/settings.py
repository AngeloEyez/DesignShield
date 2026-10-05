"""
系統設定 Pydantic 綱要模型 (System Settings Schemas)
"""

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field, ConfigDict


class SettingBase(BaseModel):
    """設定基本欄位"""
    value: Any = Field(..., description="設定值 (JSON 格式)")
    description: Optional[str] = Field(None, description="設定說明")


class SettingUpdate(SettingBase):
    """更新設定請求綱要"""
    pass


class SettingResponse(SettingBase):
    """設定回應綱要"""
    key: str = Field(..., description="設定鍵值")
    updated_at: Optional[datetime] = Field(None, description="更新時間")

    model_config = ConfigDict(from_attributes=True)
