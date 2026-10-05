"""
任務相關 Pydantic 驗證綱要 (Task Pydantic Schemas)

定義 API 請求與回應的型別模型，確保資料格式符合 docs/api_contract.md。
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class RecommendedRule(BaseModel):
    """預先分析推薦規則資料模型"""
    id: str = Field(..., description="規則代碼")
    name: str = Field(..., description="規則名稱")
    category: str = Field(..., description="規則分類")


class PreAnalysisSummary(BaseModel):
    """輕量預先分析摘要資料模型"""
    buses: List[str] = Field(default_factory=list, description="偵測到的匯流排清單 (如 I2C, SPI)")
    platforms: List[str] = Field(default_factory=list, description="偵測到的主控平台清單 (如 STM32, ESP32)")
    component_count: int = Field(default=0, description="元件總數")
    net_count: int = Field(default=0, description="網路總數")


class TaskCreateResponse(BaseModel):
    """上傳建立任務後之回應資料模型"""
    task_id: str = Field(..., description="任務 UUID")
    project_name: str = Field(..., description="專案名稱")
    status: str = Field(..., description="任務當前狀態")
    pre_analysis_summary: PreAnalysisSummary = Field(..., description="預先分析摘要")
    recommended_rules: List[RecommendedRule] = Field(default_factory=list, description="推薦規則清單")


class TaskRunRequest(BaseModel):
    """正式啟動 DRC 任務之請求參數"""
    selected_rule_ids: List[str] = Field(..., description="使用者勾選的規則代碼清單")


class TaskRunResponse(BaseModel):
    """啟動 DRC 任務後之回應 (202 Accepted)"""
    task_id: str = Field(..., description="任務 UUID")
    status: str = Field(..., description="任務狀態 (PROCESSING)")
    message: str = Field(..., description="狀態提示訊息")


class StepStatusResponse(BaseModel):
    """單一步驟進度資料模型 (用於 Timeline 與 SSE)"""
    id: Optional[str] = Field(None, description="步驟記錄 UUID")
    step_name: str = Field(..., description="步驟名稱")
    status: str = Field(..., description="步驟狀態")
    log_message: Optional[str] = Field(None, description="日誌訊息")
    started_at: Optional[datetime] = Field(None, description="開始時間")
    completed_at: Optional[datetime] = Field(None, description="完成時間")


class TaskDetailResponse(BaseModel):
    """任務詳細資訊回應模型"""
    task_id: str = Field(..., description="任務 UUID")
    project_name: str = Field(..., description="專案名稱")
    status: str = Field(..., description="任務狀態")
    pre_analysis_summary: Dict[str, Any] = Field(default_factory=dict, description="預先分析摘要")
    selected_rules: List[str] = Field(default_factory=list, description="選定規則")
    created_at: datetime = Field(..., description="建立時間")
    steps: List[StepStatusResponse] = Field(default_factory=list, description="所有步驟執行進度")
