"""
DesignShield SDK 資料模型與核心契約 (Data Models & Core Contracts)

提供 Level 3 DRC 伴生 Python 腳本與引擎通訊之強型別合約，包含違規物件、結果枚舉與節點抽象封裝。
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Union


class RuleResult(str, Enum):
    """
    DRC 規則評估結果枚舉 (Rule Evaluation Result Status)
    """
    PASS = "PASS"
    FAIL = "FAIL"
    WARNING = "WARNING"
    INFO = "INFO"


@dataclass
class RuleViolation:
    """
    DRC 規則違規報告資料模型 (Rule Violation Finding Item)

    Attributes:
        message: 違規詳細描述訊息 (繁體中文)
        severity: 違規嚴重度 ("FATAL", "ERROR", "WARNING", "INFO")
        evidence: 結構化佐證資料 (例如 PartDB 溯源資訊、數值比對軌跡)
        target_nodes: 受測目標節點清單字典 (例如 {"components": ["U1"], "nets": ["I2C_SDA"]})
    """
    message: str
    severity: str = "ERROR"
    evidence: Dict[str, Any] = field(default_factory=dict)
    target_nodes: Optional[Dict[str, List[str]]] = None

    def __post_init__(self):
        # 正規化 severity 為全大寫
        if isinstance(self.severity, str):
            self.severity = self.severity.upper()

    def to_dict(self) -> Dict[str, Any]:
        """
        轉換為標準字典格式，向下相容舊版 DRC 報表項目
        """
        res: Dict[str, Any] = {
            "message": self.message,
            "severity": self.severity,
            "evidence": self.evidence,
        }
        if self.target_nodes:
            res["target_nodes"] = self.target_nodes
        return res


class ComponentNode(dict):
    """
    智慧電路圖元件節點包裝物件 (Component Node Wrapper)

    同時支援屬性存取 (`node.pn`, `node.ref_des`) 與字典索引 (`node['part_value']`)，
    達成雙向語意相容性與卓越的開發者體驗 (DX)。
    """

    @property
    def pn(self) -> str:
        """取得元件料號或數值 (優先順序: part_value > mfg_pn)"""
        return str(self.get("part_value") or self.get("mfg_pn") or "")

    @property
    def ref_des(self) -> str:
        """取得元件參考編號 (例如 U1, R10, C5)"""
        return str(self.get("ref_des") or "")

    @property
    def category(self) -> str:
        """取得主實體類別 (例如 IC, Passive, Discrete)"""
        return str(self.get("category") or "")

    @property
    def sub_category(self) -> str:
        """取得實體次分類 (例如 Microcontroller, Resistor, Capacitor)"""
        return str(self.get("sub_category") or "")

    @property
    def functional_role(self) -> str:
        """取得動態/靜態拓撲角色 (例如 Bus_Master, Pull_up, Filter)"""
        return str(self.get("functional_role") or "")

    @property
    def part_value(self) -> str:
        """取得元件標稱值 (例如 10k, 100nF, STM32F405)"""
        return str(self.get("part_value") or "")

    @property
    def is_electrical(self) -> bool:
        """是否為具備電氣功能之元件"""
        return bool(self.get("is_electrical", True))


class NetNode(dict):
    """
    智慧線路/網路節點包裝物件 (Net Node Wrapper)

    同時支援屬性存取 (`net.name`, `net.is_power`) 與字典索引 (`net['net_name']`)。
    """

    @property
    def name(self) -> str:
        """取得網路名稱"""
        return str(self.get("net_name") or self.get("_id", "").replace("net:", ""))

    @property
    def net_name(self) -> str:
        """取得網路名稱 (相容別名)"""
        return self.name

    @property
    def bus_type(self) -> Optional[str]:
        """匯流排協定類型 (例如 I2C, SPI, UART, 若無則為 None)"""
        return self.get("bus_type")

    @property
    def is_power(self) -> bool:
        """是否為供電軌道網路"""
        return bool(self.get("is_power", False))

    @property
    def is_ground(self) -> bool:
        """是否為基準接地網路"""
        return bool(self.get("is_ground", False))

    @property
    def operating_voltage(self) -> Optional[float]:
        """工作公稱電壓值 (例如 3.3, 5.0, 0.0)"""
        v = self.get("operating_voltage")
        if v is not None:
            try:
                return float(v)
            except (ValueError, TypeError):
                return None
        return None


@dataclass
class RuleContext:
    """
    注入至 Python 腳本之執行期上下文物件 (Rule Execution Context)

    Attributes:
        target: 被 Trigger 条件匹配中之目標實例節點 (ComponentNode 或 NetNode)
        params: YAML 外部傳遞之參數字典
        task_id: 關聯之工作流任務 UUID
        G: 底層 NetworkX 圖譜 (受限唯讀封裝)
    """
    target: Union[ComponentNode, NetNode, Dict[str, Any]]
    params: Dict[str, Any] = field(default_factory=dict)
    task_id: Optional[str] = None
    G: Optional[Any] = None
