"""
DesignShield SDK GraphAPI 拓撲查詢介面 (GraphAPI Topology Interface)

提供唯讀、安全之電路圖譜拓撲查詢方法，供伴生 Python 檢查腳本呼叫。
所有回傳節點均自動封裝為 ComponentNode 或 NetNode 物件。
"""

import re
from typing import Dict, List, Any, Optional, Union
import networkx as nx

from designshield.sdk.models import ComponentNode, NetNode


class GraphAPI:
    """
    電路圖譜拓撲安全查詢介面 (GraphAPI)

    封裝底層 NetworkX 圖論資料結構，僅提供唯讀查詢方法，防止腳本任意異動圖譜拓撲。
    """

    def __init__(self, G: nx.Graph):
        self._G = G

    def _resolve_node_id(self, node: Union[ComponentNode, NetNode, Dict[str, Any], str]) -> str:
        """解析節點唯一標識 ID"""
        if isinstance(node, str):
            return node
        if isinstance(node, dict):
            return str(node.get("_id") or node.get("net_name") or node.get("ref_des") or "")
        return ""

    def get_master_device(self, bus_node: Union[NetNode, Dict[str, Any], str]) -> Optional[ComponentNode]:
        """
        取得連接至此匯流排/網路的主控晶片 (Bus_Master 或 Microcontroller)

        Args:
            bus_node: 目標網路節點或網路識別名稱

        Returns:
            Optional[ComponentNode]: 主控晶片節點包裝物件，若未找到則為 None
        """
        node_id = self._resolve_node_id(bus_node)
        if not node_id:
            return None

        # 若圖譜無直接節點，嘗試補齊 net: 前綴
        if not self._G.has_node(node_id):
            if self._G.has_node(f"net:{node_id}"):
                node_id = f"net:{node_id}"
            else:
                return None

        for neighbor in self._G.neighbors(node_id):
            ndata = self._G.nodes[neighbor]
            if ndata.get("type") == "component":
                role = ndata.get("functional_role", "")
                cat = ndata.get("category", "")
                sub = ndata.get("sub_category", "")
                if role == "Bus_Master" or sub == "Microcontroller" or cat == "IC":
                    res = ComponentNode(ndata)
                    res["_id"] = neighbor
                    return res
        return None

    def get_slave_devices(self, bus_node: Union[NetNode, Dict[str, Any], str]) -> List[ComponentNode]:
        """
        取得連接至此匯流排之受控設備 (Slave Devices)

        Args:
            bus_node: 目標網路節點

        Returns:
            List[ComponentNode]: 所有受控元件清單
        """
        node_id = self._resolve_node_id(bus_node)
        if not node_id:
            return []

        if not self._G.has_node(node_id) and self._G.has_node(f"net:{node_id}"):
            node_id = f"net:{node_id}"

        slaves: List[ComponentNode] = []
        if not self._G.has_node(node_id):
            return slaves

        for neighbor in self._G.neighbors(node_id):
            ndata = self._G.nodes[neighbor]
            if ndata.get("type") == "component":
                role = ndata.get("functional_role", "")
                if role == "Bus_Slave" or (ndata.get("category") == "IC" and role != "Bus_Master"):
                    res = ComponentNode(ndata)
                    res["_id"] = neighbor
                    slaves.append(res)
        return slaves

    def get_pullup_resistors(self, net_node: Union[NetNode, Dict[str, Any], str]) -> List[ComponentNode]:
        """
        取得一端連接至該網路、另一端連接至合法電源軌的上拉電阻清單

        Args:
            net_node: 目標網路節點

        Returns:
            List[ComponentNode]: 上拉電阻節點清單 (已注入 resistance_ohm 數值)
        """
        node_id = self._resolve_node_id(net_node)
        if not node_id:
            return []

        if not self._G.has_node(node_id) and self._G.has_node(f"net:{node_id}"):
            node_id = f"net:{node_id}"

        resistors: List[ComponentNode] = []
        if not self._G.has_node(node_id):
            return resistors

        for neighbor in self._G.neighbors(node_id):
            ndata = self._G.nodes[neighbor]
            if ndata.get("type") == "component":
                sub = ndata.get("sub_category", "")
                role = ndata.get("functional_role", "")
                if sub == "Resistor" or role == "Pull_up":
                    is_pullup = (role == "Pull_up")
                    for other_net in self._G.neighbors(neighbor):
                        if other_net != node_id:
                            odata = self._G.nodes[other_net]
                            if odata.get("is_power") or odata.get("net_type") == "Power" or "VCC" in other_net.upper() or "VDD" in other_net.upper():
                                is_pullup = True
                                break
                    if is_pullup:
                        r_dict = ComponentNode(ndata)
                        r_dict["_id"] = neighbor
                        r_dict["resistance_ohm"] = self.extract_resistance_ohms(ndata.get("part_value", ""))
                        resistors.append(r_dict)
        return resistors

    def has_capacitor_to_gnd(self, net_node: Union[NetNode, Dict[str, Any], str]) -> bool:
        """
        檢查該網路是否有電容連接至基準接地 (GND)

        Args:
            net_node: 目標網路節點

        Returns:
            bool: 若存在連接至地之電容回傳 True，否則為 False
        """
        node_id = self._resolve_node_id(net_node)
        if not node_id:
            return False

        if not self._G.has_node(node_id) and self._G.has_node(f"net:{node_id}"):
            node_id = f"net:{node_id}"

        if not self._G.has_node(node_id):
            return False

        for neighbor in self._G.neighbors(node_id):
            ndata = self._G.nodes[neighbor]
            if ndata.get("type") == "component":
                sub = ndata.get("sub_category", "") or ndata.get("category", "")
                if sub == "Capacitor":
                    for other_net in self._G.neighbors(neighbor):
                        if other_net != node_id:
                            odata = self._G.nodes[other_net]
                            if odata.get("is_ground") or "GND" in other_net.upper():
                                return True
        return False

    def has_series_resistor(self, net_node: Union[NetNode, Dict[str, Any], str]) -> bool:
        """
        檢查該網路上是否掛載串聯電阻 (Series Resistor)

        Args:
            net_node: 目標網路節點

        Returns:
            bool: 是否存在串聯電阻
        """
        return self.has_component_in_series(net_node, component_type="Resistor")

    def has_component_in_series(self, net_node: Union[NetNode, Dict[str, Any], str], component_type: str = "Resistor") -> bool:
        """
        檢查該訊號路徑上是否配置特定種類之串聯元件

        Args:
            net_node: 目標網路節點
            component_type: 元件次類別或類別 (例如 "Resistor", "Capacitor")

        Returns:
            bool: 是否具備串聯元件
        """
        node_id = self._resolve_node_id(net_node)
        if not node_id:
            return False

        if not self._G.has_node(node_id) and self._G.has_node(f"net:{node_id}"):
            node_id = f"net:{node_id}"

        if not self._G.has_node(node_id):
            return False

        for neighbor in self._G.neighbors(node_id):
            ndata = self._G.nodes[neighbor]
            if ndata.get("type") == "component":
                role = ndata.get("functional_role", "")
                sub = ndata.get("sub_category", "") or ndata.get("category", "")
                if (role == "Series_Resistor" or role == "AC_Coupling_Capacitor") and (component_type.lower() in sub.lower()):
                    return True
                # 若元件兩端皆接訊號線 (非電源也非地) 且型態符合
                if sub.lower() == component_type.lower():
                    connected_nets = [n for n in self._G.neighbors(neighbor) if self._G.nodes[n].get("type") == "net"]
                    if len(connected_nets) >= 2:
                        is_pure_signal = all(not (self._G.nodes[n].get("is_power") or self._G.nodes[n].get("is_ground")) for n in connected_nets)
                        if is_pure_signal:
                            return True
        return False

    def get_connected_components(self, net_node: Union[NetNode, Dict[str, Any], str]) -> List[ComponentNode]:
        """
        取得連接至此網路的所有電路元件清單

        Args:
            net_node: 目標網路節點

        Returns:
            List[ComponentNode]: 元件包裝物件清單
        """
        node_id = self._resolve_node_id(net_node)
        if not node_id:
            return []

        if not self._G.has_node(node_id) and self._G.has_node(f"net:{node_id}"):
            node_id = f"net:{node_id}"

        comps: List[ComponentNode] = []
        if not self._G.has_node(node_id):
            return comps

        for neighbor in self._G.neighbors(node_id):
            ndata = self._G.nodes[neighbor]
            if ndata.get("type") == "component":
                c = ComponentNode(ndata)
                c["_id"] = neighbor
                comps.append(c)
        return comps

    def get_connected_nets(self, comp_node: Union[ComponentNode, Dict[str, Any], str]) -> List[NetNode]:
        """
        取得連接至此元件的所有網路清單

        Args:
            comp_node: 目標元件節點

        Returns:
            List[NetNode]: 網路包裝物件清單
        """
        node_id = self._resolve_node_id(comp_node)
        if not node_id:
            return []

        if not self._G.has_node(node_id) and self._G.has_node(f"comp:{node_id}"):
            node_id = f"comp:{node_id}"

        nets: List[NetNode] = []
        if not self._G.has_node(node_id):
            return nets

        for neighbor in self._G.neighbors(node_id):
            ndata = self._G.nodes[neighbor]
            if ndata.get("type") == "net":
                n = NetNode(ndata)
                n["_id"] = neighbor
                nets.append(n)
        return nets

    @staticmethod
    def extract_resistance_ohms(val_str: str) -> Optional[float]:
        """
        從數值標稱字串中解析電阻標準歐姆值 (支援 4.7k, 10K, 100R, 2.2M, 470 等格式)

        Args:
            val_str: 零件數值字串

        Returns:
            Optional[float]: 解析出之歐姆數值 (Ω)，若無法解析回傳 None
        """
        if not val_str:
            return None
        match = re.search(r"(\d+(?:\.\d+)?)\s*([KkMmRr]?)(?:[Ω\s]|$)", str(val_str))
        if not match:
            return None
        try:
            num = float(match.group(1))
            unit = match.group(2).upper()
            if unit == "K":
                return num * 1000.0
            elif unit == "M":
                return num * 1000000.0
            return num
        except (ValueError, TypeError):
            return None
