"""
規則相關 Pydantic 綱要模型 (Rule Schemas)
"""

from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict


class RuleBase(BaseModel):
    """規則基本欄位"""
    name: str = Field(..., description="規則中文名稱")
    category: str = Field(..., description="規則分類")
    check_type: str = Field("HEURISTIC", description="檢測方式 (HEURISTIC 或 LLM)")
    is_active: bool = Field(True, description="是否啟用")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="規則參數")
    prompt_template: Optional[str] = Field(None, description="LLM 提示樣板")
    context_extractor: Optional[str] = Field(None, description="上下文抽取器")


class RuleCreate(RuleBase):
    """新增規則請求綱要"""
    id: str = Field(..., description="規則代碼 (唯一值)")


class RuleResponse(RuleBase):
    """規則查詢回應綱要"""
    id: str = Field(..., description="規則代碼")
    created_at: Optional[datetime] = Field(None, description="建立時間")

    model_config = ConfigDict(from_attributes=True)
