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
    severity: Optional[str] = Field(default="Error", description="嚴重等級 (Fatal, Error, Warning, Info)")
    domain: Optional[str] = Field(default="", description="實體領域 (interfaces, power 等)")
    tags: Optional[List[str]] = Field(default_factory=list, description="規則標籤")
    reason: Optional[str] = Field(default="", description="推薦理由說明")
    check_type: Optional[str] = Field(default="topology_check", description="檢測類型")


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
    pre_analysis_summary: Optional[PreAnalysisSummary] = Field(default_factory=PreAnalysisSummary, description="預先分析摘要")
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
    task_type: str = Field(default="DRC", description="任務類型 (DRC / RULE_EXTRACTION / DATASHEET_ANALYSIS)")
    status: str = Field(..., description="任務狀態")
    pre_analysis_summary: Dict[str, Any] = Field(default_factory=dict, description="預先分析摘要")
    recommended_rules: List[RecommendedRule] = Field(default_factory=list, description="推薦規則清單")
    selected_rules: List[str] = Field(default_factory=list, description="選定規則")
    created_at: datetime = Field(..., description="建立時間")
    updated_at: Optional[datetime] = Field(None, description="最後更新時間")
    steps: List[StepStatusResponse] = Field(default_factory=list, description="所有步驟執行進度")


class TaskListItem(BaseModel):
    """任務清單項目簡要資料模型"""
    id: str = Field(..., description="任務 UUID")
    project_name: str = Field(..., description="專案名稱")
    task_type: str = Field(default="DRC", description="任務類型")
    status: str = Field(..., description="任務狀態")
    created_at: datetime = Field(..., description="建立時間")
    updated_at: datetime = Field(..., description="更新時間")
    pre_analysis_summary: Dict[str, Any] = Field(default_factory=dict, description="預檢摘要")
    selected_rules: List[str] = Field(default_factory=list, description="選定規則清單")


class TaskListResponse(BaseModel):
    """任務清單分頁回應資料模型"""
    total: int = Field(..., description="總筆數")
    tasks: List[TaskListItem] = Field(default_factory=list, description="任務列表")


class ComponentDetail(BaseModel):
    """元件詳細資訊"""
    ref_des: str = Field(..., description="元件編號 (如 U1, R1)")
    category: str = Field(default="General", description="宏觀實體類別 (IC, Passive, Discrete...)")
    sub_category: Optional[str] = Field(None, description="細部元件類型 (Capacitor, Resistor, TVS...)")
    functional_role: Optional[str] = Field(None, description="電路拓撲角色 (Bus_Master, Power_Source...)")
    is_electrical: bool = Field(default=True, description="是否具電氣特性")
    part_value: Optional[str] = Field(None, description="型號或阻容值")
    package: Optional[str] = Field(None, description="封裝規格 (PCB Footprint)")
    description: Optional[str] = Field(None, description="元件描述說明")
    pins_count: int = Field(default=0, description="引腳數")
    connected_nets: List[str] = Field(default_factory=list, description="連接之 Net 清單")


class NetDetail(BaseModel):
    """網路詳細資訊"""
    net_name: str = Field(..., description="網路名稱")
    bus_type: Optional[str] = Field(None, description="匯流排類型 (如 I2C, SPI)")
    is_power: bool = Field(default=False, description="是否為電源")
    is_ground: bool = Field(default=False, description="是否為接地")
    connected_components: List[str] = Field(default_factory=list, description="連接之元件清單")


class TaskGraphDetailsResponse(BaseModel):
    """電路圖譜拓撲詳細分析資料模型 (供 Step 2 檢視)"""
    task_id: str = Field(..., description="任務 UUID")
    components_count: int = Field(default=0, description="元件總數")
    nets_count: int = Field(default=0, description="網路總數")
    pins_count: int = Field(default=0, description="引腳總數")
    buses: List[str] = Field(default_factory=list, description="匯流排種類清單")
    components: List[ComponentDetail] = Field(default_factory=list, description="元件清單")
    nets: List[NetDetail] = Field(default_factory=list, description="網路清單")
    key_ics: List[str] = Field(default_factory=list, description="核心晶片與控制器清單 (Pins >= 20 或高中心度)")
    key_connectors: List[str] = Field(default_factory=list, description="主要介面連接器清單 (Pins >= 20)")
    ic_directory_by_role: Dict[str, List[str]] = Field(default_factory=dict, description="晶片功能角色分組目錄")
    non_electrical_components: List[str] = Field(default_factory=list, description="非電氣機構件與測試點清單")
    main_ics: List[str] = Field(default_factory=list, description="主控 IC 清單 (相容欄位)")
    sub_ics: List[str] = Field(default_factory=list, description="周邊子 IC 清單 (相容欄位)")


class ArchiveFileItem(BaseModel):
    """解壓縮檔案項目"""
    filename: str = Field(..., description="檔案名稱")
    relative_path: str = Field(..., description="相對路徑")
    size_bytes: int = Field(default=0, description="檔案位元組大小")
    is_xml: bool = Field(default=False, description="是否為 OrCAD XML")
    is_netlist: bool = Field(default=False, description="是否為 Netlist")


class TaskArchiveDetailsResponse(BaseModel):
    """解壓縮包與檔案詳細資訊 (供 Step 1 檢視)"""
    task_id: str = Field(..., description="任務 UUID")
    original_filename: Optional[str] = Field(None, description="原始上傳檔案名稱")
    file_count: int = Field(default=0, description="檔案總數")
    total_bytes: int = Field(default=0, description="總大小 (bytes)")
    files: List[ArchiveFileItem] = Field(default_factory=list, description="解壓檔案清單")


class TaskActionResponse(BaseModel):
    """任務操作結果回應 (停止 / 刪除)"""
    task_id: str = Field(..., description="任務 UUID")
    status: str = Field(..., description="操作後狀態")
    message: str = Field(..., description="提示訊息")
