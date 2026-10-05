"""
DRC 報告 Pydantic 綱要模型 (Report Schemas)

定義符合 docs/report_schema.md 標準之分析結果資料規格。
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class TargetNodes(BaseModel):
    """受檢查目標節點與元件"""
    components: List[str] = Field(default_factory=list, description="元件代號清單 (如 U1, U2)")
    nets: List[str] = Field(default_factory=list, description="網路名稱清單 (如 I2C_SDA, I2C_SCL)")
    page_indices: List[int] = Field(default_factory=list, description="出現在線路圖的頁碼索引")


class ViolationItem(BaseModel):
    """單一檢測結果項目 (PASS, FAIL, WARNING, SKIPPED, ERROR)"""
    item_id: str = Field(..., description="單一檢測唯一識別碼")
    rule_id: str = Field(..., description="規則代碼")
    rule_category: str = Field(..., description="規則分類")
    rule_title: str = Field(..., description="中文規則名稱")
    check_type: str = Field(..., description="檢測方式 (HEURISTIC 或 LLM)")
    status: str = Field(..., description="檢測狀態 (PASS, FAIL, WARNING, SKIPPED, ERROR)")
    severity: str = Field("INFO", description="嚴重等級 (CRITICAL, HIGH, MEDIUM, LOW, INFO)")
    target_nodes: TargetNodes = Field(default_factory=TargetNodes, description="受檢測節點")
    description: str = Field(..., description="檢測結果詳細說明")
    comment: Optional[str] = Field(None, description="工程建議或備註")
    evidence_trail: Dict[str, Any] = Field(default_factory=dict, description="檢驗佐證與歷程資料")


class ReportSummary(BaseModel):
    """總結報告資料模型"""
    total_rules_checked: int = Field(default=0, description="總檢查規則數")
    pass_count: int = Field(default=0, description="通過數量")
    fail_count: int = Field(default=0, description="違規數量")
    warning_count: int = Field(default=0, description="警告數量")
    skip_count: int = Field(default=0, description="略過數量")
    pass_rate_percentage: float = Field(default=0.0, description="通過率百分比")
    by_category: Dict[str, Dict[str, int]] = Field(default_factory=dict, description="各分類通過統計")


class ReportResponse(BaseModel):
    """DRC 最終完整報告回應綱要"""
    task_id: str = Field(..., description="任務 UUID")
    project_name: Optional[str] = Field(None, description="專案名稱")
    created_at: Optional[datetime] = Field(None, description="開始時間")
    completed_at: Optional[datetime] = Field(None, description="完成時間")
    total_execution_time_seconds: Optional[float] = Field(None, description="執行總秒數")
    summary: ReportSummary = Field(..., description="總結摘要")
    violations: List[ViolationItem] = Field(default_factory=list, description="違規與檢測詳細列表")
