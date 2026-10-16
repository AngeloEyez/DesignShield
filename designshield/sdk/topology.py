"""
DesignShield SDK 通用電路拓撲資料模型與建構器 (Universal Circuit Topology Models & Builder)

提供標準圖論資料結構與流式建構器 (Builder Pattern)，支援單端信號 (Single-ended)、
差分信號 (Differential)、匯流排 (Bus)、上拉/下拉電阻 (Pull-up/Pull-down) 以及接地電容/濾波器 (Shunt Capacitor)
之標準拓撲表達，供 Level 3 DRC 伴生腳本無縫產出電路圖譜供前端渲染。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Union


@dataclass
class UniversalPin:
    """
    元件引腳規格定義
    
    Attributes:
        pin_number: 實體引腳編號 (例如 "1", "2", "A1", "SSRXP1")
        pin_name: 引腳功能名稱 (例如 "VCC", "GND", "TX+", "SCL")
        orientation: 引腳朝向，供排版引擎計算連線方向 ("left" | "right" | "top" | "bottom")
    """
    pin_number: str
    pin_name: Optional[str] = None
    orientation: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """轉為標準字典"""
        d: Dict[str, Any] = {"pin_number": str(self.pin_number)}
        if self.pin_name:
            d["pin_name"] = str(self.pin_name)
        if self.orientation:
            d["orientation"] = self.orientation
        return d


@dataclass
class UniversalNode:
    """
    電路拓撲節點定義 (包含 IC、連接器、被動元件、電源軌、接地等)

    Attributes:
        id: 節點唯一識別碼 (通常為 ref_des 或特定別名)
        ref_des: 元件位號 (例如 "U1", "R1", "C1", "+3.3V", "GND")
        category: 元件大類別 ("IC" | "Connector" | "Resistor" | "Capacitor" | "Inductor" | "Diode" | "PowerRail" | "Ground")
        role: 電氣角色 ("terminal" | "series" | "pull_up" | "pull_down" | "shunt_ground" | "bridge")
        part_number: 零件料號 (例如 "June Bridge A0", "CH340G")
        value: 零件規格標稱值 (例如 "4.7kΩ", "0.1µF", "100Ω")
        pins: 元件引腳清單
    """
    id: str
    ref_des: str
    category: str
    role: str
    part_number: Optional[str] = None
    value: Optional[str] = None
    pins: List[UniversalPin] = field(default_factory=list)
    is_mounted: bool = True
    bom: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """轉為標準字典"""
        d: Dict[str, Any] = {
            "id": self.id,
            "ref_des": self.ref_des,
            "category": self.category,
            "role": self.role,
            "is_mounted": self.is_mounted,
            "pins": [p.to_dict() if hasattr(p, "to_dict") else p for p in self.pins]
        }
        if self.bom:
            d["bom"] = self.bom
        if self.part_number:
            d["part_number"] = self.part_number
        if self.value:
            d["value"] = self.value
        return d


@dataclass
class UniversalConnection:
    """
    電路連線/網段連接定義

    Attributes:
        net_name: 網段名稱 (例如 "TCP0_RT_SSRX0_P", "I2C_SCL")
        rail_id: 歸屬軌道識別碼 (例如 "main", "p_rail", "n_rail", "scl", "sda")
        from_node: 起始節點 id
        from_pin: 起始節點引腳 pin_number
        to_node: 目標節點 id
        to_pin: 目標節點引腳 pin_number
        is_branch: 是否為分支線路 (例如垂直上拉或垂直接地分支)
    """
    net_name: str
    rail_id: str
    from_node: str
    from_pin: str
    to_node: str
    to_pin: str
    is_branch: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """轉為標準字典"""
        return {
            "net_name": self.net_name,
            "rail_id": self.rail_id,
            "from_node": self.from_node,
            "from_pin": str(self.from_pin),
            "to_node": self.to_node,
            "to_pin": str(self.to_pin),
            "is_branch": self.is_branch,
        }


@dataclass
class UniversalRail:
    """
    通道軌道定義 (支援多軌道，例如差分正負軌、匯流排多線軌道)

    Attributes:
        id: 軌道 ID (例如 "p_rail", "n_rail", "main", "scl")
        name: 軌道顯示名稱 (例如 "Positive Rail (P)", "I2C Clock (SCL)")
        polarity: 極性標記 ("P" | "N" | None)
    """
    id: str
    name: str
    polarity: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """轉為標準字典"""
        d: Dict[str, Any] = {"id": self.id, "name": self.name}
        if self.polarity:
            d["polarity"] = self.polarity
        return d


@dataclass
class UniversalTopologyData:
    """
    通用電路拓撲標準合約 (Universal Topology Contract)

    Attributes:
        title: 通道標題 (例如 "TJ1 ↔ TU1 (TCP0_RT_SSRX0 差分通道)")
        channel_type: 通道類型 ("single" | "differential" | "bus")
        rails: 軌道清單
        nodes: 元件節點清單
        connections: 連線段清單
        metadata: 補充中繼資料 (例如 symmetry_check, audit_summary 等)
    """
    title: str
    channel_type: str = "single"
    rails: List[UniversalRail] = field(default_factory=list)
    nodes: List[UniversalNode] = field(default_factory=list)
    connections: List[UniversalConnection] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """轉為標準字典"""
        return {
            "title": self.title,
            "channel_type": self.channel_type,
            "rails": [r.to_dict() if hasattr(r, "to_dict") else r for r in self.rails],
            "nodes": [n.to_dict() if hasattr(n, "to_dict") else n for n in self.nodes],
            "connections": [c.to_dict() if hasattr(c, "to_dict") else c for c in self.connections],
            "metadata": self.metadata,
        }


class TopologyGraphBuilder:
    """
    通用電路拓撲流式建造者 (Fluent Builder for Universal Circuit Topology)

    提供簡潔、防呆的 API 讓伴生腳本以幾行 Python 代碼宣告電路拓撲結構。
    """

    def __init__(self, title: str, channel_type: str = "single"):
        """
        初始化拓撲建造者

        Args:
            title: 通道標題
            channel_type: "single" | "differential" | "bus"
        """
        self.title: str = title
        self.channel_type: str = channel_type
        self.rails: List[UniversalRail] = []
        self._rail_ids: set = set()
        self.nodes: Dict[str, UniversalNode] = {}
        self.connections: List[UniversalConnection] = []
        self.metadata: Dict[str, Any] = {}

    def add_rail(self, rail_id: str, name: str, polarity: Optional[str] = None) -> "TopologyGraphBuilder":
        """
        新增信號軌道

        Args:
            rail_id: 軌道識別 ID (例如 "p_rail", "n_rail", "main")
            name: 軌道名稱 (例如 "P 極性軌道", "SCL 時脈線")
            polarity: 極性標記 ("P" | "N" | None)
        """
        if rail_id not in self._rail_ids:
            self.rails.append(UniversalRail(id=rail_id, name=name, polarity=polarity))
            self._rail_ids.add(rail_id)
        return self

    def add_terminal(
        self,
        id: str,
        ref_des: str,
        category: str = "IC",
        part_number: Optional[str] = None,
        pins: Optional[List[Union[UniversalPin, Dict[str, Any]]]] = None,
        role: str = "terminal",
        is_mounted: bool = True,
        bom: Optional[str] = None
    ) -> "TopologyGraphBuilder":
        """
        新增終端元件 (如主晶片 IC、連接器 Connector)

        Args:
            id: 節點唯一識別碼 (通常為 ref_des)
            ref_des: 位號 (例如 "TU1", "TJ1")
            category: 元件類型 ("IC" | "Connector")
            part_number: 零件型號
            pins: 引腳清單 (可傳入 UniversalPin 或 dict)
            role: 電氣角色 (預設 "terminal")
            is_mounted: 是否於當前 Config 上件 (預設 True)
            bom: 當前 Config 之正規化 BOM 代碼 ('I', 'X', 'P', 'M', 'NOBOM')
        """
        parsed_pins: List[UniversalPin] = []
        if pins:
            for p in pins:
                if isinstance(p, UniversalPin):
                    parsed_pins.append(p)
                elif isinstance(p, dict):
                    parsed_pins.append(UniversalPin(
                        pin_number=str(p.get("pin_number") or p.get("pin") or ""),
                        pin_name=p.get("pin_name") or p.get("pin"),
                        orientation=p.get("orientation")
                    ))

        if id in self.nodes:
            # 合併現有節點之 pins
            existing = self.nodes[id]
            existing_pin_nums = {p.pin_number for p in existing.pins}
            for p in parsed_pins:
                if p.pin_number not in existing_pin_nums:
                    existing.pins.append(p)
                    existing_pin_nums.add(p.pin_number)
            if part_number and not existing.part_number:
                existing.part_number = part_number
            existing.is_mounted = is_mounted
            if bom:
                existing.bom = bom
        else:
            self.nodes[id] = UniversalNode(
                id=id,
                ref_des=ref_des,
                category=category,
                role=role,
                part_number=part_number,
                pins=parsed_pins,
                is_mounted=is_mounted,
                bom=bom
            )
        return self

    def add_series_component(
        self,
        id: str,
        ref_des: str,
        category: str,
        value: Optional[str] = None,
        in_pin: str = "1",
        out_pin: str = "2",
        in_pin_name: Optional[str] = None,
        out_pin_name: Optional[str] = None,
        part_number: Optional[str] = None,
        is_mounted: bool = True,
        bom: Optional[str] = None
    ) -> "TopologyGraphBuilder":
        """
        新增串聯穿透元件 (如 AC 耦合電容、串聯電阻、共模扼流圈等)

        Args:
            id: 節點唯一識別碼
            ref_des: 元件位號 (例如 "TC13", "TR8")
            category: 元件類別 ("Capacitor" | "Resistor" | "Inductor")
            value: 標稱值 (例如 "0.1µF", "0Ω")
            in_pin: 輸入端引腳編號 (預設 "1")
            out_pin: 輸出端引腳編號 (預設 "2")
            in_pin_name: 輸入引腳名稱 (可選)
            out_pin_name: 輸出引腳名稱 (可選)
            part_number: 零件型號 (可選)
            is_mounted: 是否於當前 Config 上件 (預設 True)
            bom: 當前 Config 之正規化 BOM 代碼 ('I', 'X', 'P', 'M', 'NOBOM')
        """
        pins = [
            UniversalPin(pin_number=str(in_pin), pin_name=in_pin_name, orientation="left"),
            UniversalPin(pin_number=str(out_pin), pin_name=out_pin_name, orientation="right"),
        ]
        if id in self.nodes:
            existing = self.nodes[id]
            existing_pin_nums = {p.pin_number for p in existing.pins}
            for p in pins:
                if p.pin_number not in existing_pin_nums:
                    existing.pins.append(p)
                    existing_pin_nums.add(p.pin_number)
            if value and not existing.value:
                existing.value = value
            if part_number and not existing.part_number:
                existing.part_number = part_number
            existing.is_mounted = is_mounted
            if bom:
                existing.bom = bom
        else:
            self.nodes[id] = UniversalNode(
                id=id,
                ref_des=ref_des,
                category=category,
                role="series",
                part_number=part_number,
                value=value,
                pins=pins,
                is_mounted=is_mounted,
                bom=bom
            )
        return self

    def add_pull_up(
        self,
        id: str,
        ref_des: str,
        power_net: str = "+3.3V",
        value: Optional[str] = None,
        pin_to_rail: str = "1",
        pin_to_pwr: str = "2",
        part_number: Optional[str] = None
    ) -> "TopologyGraphBuilder":
        """
        新增垂直上拉元件 (如 I2C/RESET 上拉電阻)

        Args:
            id: 節點唯一識別碼
            ref_des: 元件位號 (例如 "R1")
            power_net: 連接之電源軌名稱 (例如 "+3.3V", "VCC")
            value: 阻值 (例如 "4.7kΩ")
            pin_to_rail: 連接至訊號線之引腳 (預設 "1", 朝下)
            pin_to_pwr: 連接至電源軌之引腳 (預設 "2", 朝上)
            part_number: 零件型號 (可選)
        """
        pins = [
            UniversalPin(pin_number=str(pin_to_rail), pin_name="SIG", orientation="bottom"),
            UniversalPin(pin_number=str(pin_to_pwr), pin_name=power_net, orientation="top"),
        ]
        self.nodes[id] = UniversalNode(
            id=id,
            ref_des=ref_des,
            category="Resistor",
            role="pull_up",
            part_number=part_number,
            value=value,
            pins=pins
        )
        return self

    def add_shunt_ground(
        self,
        id: str,
        ref_des: str,
        category: str = "Capacitor",
        value: Optional[str] = None,
        pin_to_rail: str = "1",
        pin_to_gnd: str = "2",
        gnd_net: str = "GND",
        part_number: Optional[str] = None
    ) -> "TopologyGraphBuilder":
        """
        新增垂直接地元件 (如濾波電容、TVS 靜電防護管、下拉電阻)

        Args:
            id: 節點唯一識別碼
            ref_des: 元件位號 (例如 "C1", "D1")
            category: 元件類型 ("Capacitor" | "Diode" | "Resistor")
            value: 規格值 (例如 "10pF", "5.6V")
            pin_to_rail: 連接至訊號線之引腳 (預設 "1", 朝上)
            pin_to_gnd: 連接至接地之引腳 (預設 "2", 朝下)
            gnd_net: 接地網路名稱 (預設 "GND")
            part_number: 零件型號 (可選)
        """
        role = "pull_down" if category == "Resistor" else "shunt_ground"
        pins = [
            UniversalPin(pin_number=str(pin_to_rail), pin_name="SIG", orientation="top"),
            UniversalPin(pin_number=str(pin_to_gnd), pin_name=gnd_net, orientation="bottom"),
        ]
        self.nodes[id] = UniversalNode(
            id=id,
            ref_des=ref_des,
            category=category,
            role=role,
            part_number=part_number,
            value=value,
            pins=pins
        )
        return self

    def add_connection(
        self,
        net_name: str,
        rail_id: str,
        from_node: str,
        from_pin: str,
        to_node: str,
        to_pin: str,
        is_branch: bool = False
    ) -> "TopologyGraphBuilder":
        """
        新增節點間的網段連接

        Args:
            net_name: 網段名稱 (例如 "TCP0_RT_SSRX0_P")
            rail_id: 所屬軌道 ID
            from_node: 起始節點 ID
            from_pin: 起始引腳編號
            to_node: 目標節點 ID
            to_pin: 目標引腳編號
            is_branch: 是否為分支 (例如上拉或接地支線)
        """
        self.connections.append(UniversalConnection(
            net_name=net_name,
            rail_id=rail_id,
            from_node=from_node,
            from_pin=str(from_pin),
            to_node=to_node,
            to_pin=str(to_pin),
            is_branch=is_branch
        ))
        return self

    def set_metadata(self, metadata: Dict[str, Any]) -> "TopologyGraphBuilder":
        """設定中繼資料"""
        self.metadata.update(metadata)
        return self

    def build(self) -> UniversalTopologyData:
        """產出標準 UniversalTopologyData 物件"""
        return UniversalTopologyData(
            title=self.title,
            channel_type=self.channel_type,
            rails=self.rails,
            nodes=list(self.nodes.values()),
            connections=self.connections,
            metadata=self.metadata
        )

    def to_dict(self) -> Dict[str, Any]:
        """產出標準前端可直接消費之字典結構"""
        return self.build().to_dict()
