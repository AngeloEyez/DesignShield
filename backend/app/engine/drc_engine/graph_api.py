"""
Level 3 DRC GraphAPI 輔助類別 (GraphAPI SDK)

提供標準拓撲探索方法，供 topology_evaluator 與 PartDB dynamic checker 呼叫。
"""

import re
import networkx as nx
from typing import Dict, List, Any, Optional


class GraphAPI:
    def __init__(self, G: nx.Graph):
        self.G = G

    def get_master_device(self, bus_node: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """取得連接至匯流排的主控晶片 (Bus_Master 或 Microcontroller)"""
        node_id = bus_node.get("_id")
        if not node_id and self.G.has_node(bus_node.get("net_name", "")):
            node_id = bus_node.get("net_name")

        # 遍歷鄰居節點
        for neighbor in self.G.neighbors(node_id):
            ndata = self.G.nodes[neighbor]
            if ndata.get("type") == "component":
                role = ndata.get("functional_role", "")
                cat = ndata.get("category", "")
                sub = ndata.get("sub_category", "")
                if role == "Bus_Master" or sub == "Microcontroller" or cat == "IC":
                    res = dict(ndata)
                    res["_id"] = neighbor
                    return res
        return None

    def get_slave_devices(self, bus_node: Dict[str, Any]) -> List[Dict[str, Any]]:
        """取得連接至匯流排的受控設備 (Slave Devices)"""
        node_id = bus_node.get("_id") or bus_node.get("net_name")
        slaves = []
        for neighbor in self.G.neighbors(node_id):
            ndata = self.G.nodes[neighbor]
            if ndata.get("type") == "component":
                role = ndata.get("functional_role", "")
                if role == "Bus_Slave" or (ndata.get("category") == "IC" and role != "Bus_Master"):
                    res = dict(ndata)
                    res["_id"] = neighbor
                    slaves.append(res)
        return slaves

    def get_pullup_resistors(self, net_node: Dict[str, Any]) -> List[Dict[str, Any]]:
        """取得一端連接至該網路、另一端連接至電源軌的上拉電阻"""
        node_id = net_node.get("_id") or net_node.get("net_name")
        resistors = []
        for neighbor in self.G.neighbors(node_id):
            ndata = self.G.nodes[neighbor]
            if ndata.get("type") == "component":
                sub = ndata.get("sub_category", "")
                role = ndata.get("functional_role", "")
                # 電阻且有 Pull_up 角色或連接至電源
                if sub == "Resistor" or role == "Pull_up":
                    # 檢查該電阻的其他連接網路是否有電源
                    is_pullup = (role == "Pull_up")
                    for other_net in self.G.neighbors(neighbor):
                        if other_net != node_id:
                            odata = self.G.nodes[other_net]
                            if odata.get("is_power") or odata.get("net_type") == "Power":
                                is_pullup = True
                                break
                    if is_pullup:
                        r_dict = dict(ndata)
                        r_dict["_id"] = neighbor
                        r_dict["resistance_ohm"] = self._extract_resistance_ohms(ndata.get("part_value", ""))
                        resistors.append(r_dict)
        return resistors

    def has_capacitor_to_gnd(self, net_node: Dict[str, Any]) -> bool:
        """檢查該網路是否有電容連接至地線 (GND)"""
        node_id = net_node.get("_id") or net_node.get("net_name")
        for neighbor in self.G.neighbors(node_id):
            ndata = self.G.nodes[neighbor]
            if ndata.get("type") == "component":
                sub = ndata.get("sub_category", "") or ndata.get("category", "")
                if sub == "Capacitor":
                    for other_net in self.G.neighbors(neighbor):
                        if other_net != node_id:
                            odata = self.G.nodes[other_net]
                            if odata.get("is_ground") or "GND" in other_net.upper():
                                return True
        return False

    def has_series_resistor(self, net_node: Dict[str, Any]) -> bool:
        """檢查該網路是否配置串聯電阻"""
        node_id = net_node.get("_id") or net_node.get("net_name")
        for neighbor in self.G.neighbors(node_id):
            ndata = self.G.nodes[neighbor]
            if ndata.get("type") == "component":
                role = ndata.get("functional_role", "")
                if role == "Series_Resistor":
                    return True
        return False

    def _extract_resistance_ohms(self, val_str: str) -> Optional[float]:
        """從數值字串提取電阻歐姆值 (例: 4.7k -> 4700, 10K -> 10000, 100R -> 100)"""
        if not val_str:
            return None
        match = re.search(r"(\d+(?:\.\d+)?)\s*([KkMmRr]?)(?:[Ω\s]|$)", val_str)
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
        except ValueError:
            return None
