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


class EnvSettingItem(BaseModel):
    """單一 .env 設定項目綱要"""
    key: str = Field(..., description="變數名稱")
    value: Any = Field(..., description="目前數值")
    category: str = Field(..., description="所屬分類代號")
    category_name: str = Field(..., description="分類中文名稱")
    label: str = Field(..., description="中文標籤")
    description: str = Field(..., description="中文詳細說明")
    example: str = Field(..., description="範例格式")
    default: Optional[str] = Field("", description="預設數值")
    is_secret: bool = Field(False, description="是否為機密資料")
    requires_restart: bool = Field(True, description="變更後是否需重啟伺服器")


class EnvCategory(BaseModel):
    """分類綱要"""
    id: str
    name: str
    icon: str


class EnvSettingsResponse(BaseModel):
    """.env 設定總覽回應"""
    env_file_path: str
    items: list[EnvSettingItem]
    categories: list[EnvCategory]
    total_count: int


class EnvSettingsUpdateRequest(BaseModel):
    """.env 更新請求"""
    settings: dict[str, Any] = Field(..., description="欲更新之鍵值對")


class EnvSettingsUpdateResponse(BaseModel):
    """.env 更新回應"""
    success: bool
    changed_keys: list[str]
    requires_restart: bool
    restart_reasons: list[str]
    message: str


class RestartResponse(BaseModel):
    """伺服器重啟回應"""
    success: bool
    mode: str
    message: str


class LlmModelsResponse(BaseModel):
    """查詢 LLM 可用模型回應"""
    success: bool
    api_base: str
    models: list[str]
    message: str


