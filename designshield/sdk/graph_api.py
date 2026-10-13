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

    def _resolve_node_id(self, node: Union[ComponentNode, NetNode, Dict[str, Any], str], expected_prefix: str = "") -> str:
        """解析節點唯一標識 ID"""
        if isinstance(node, str):
            node_id = node
        elif isinstance(node, dict):
            node_id = str(node.get("_id") or node.get("net_name") or node.get("ref_des") or "")
        else:
            node_id = ""

        if not node_id:
            return ""

        if self._G.has_node(node_id):
            return node_id

        if expected_prefix and not node_id.startswith(expected_prefix):
            prefixed = f"{expected_prefix}{node_id}"
            if self._G.has_node(prefixed):
                return prefixed

        if self._G.has_node(f"net:{node_id}"):
            return f"net:{node_id}"
        if self._G.has_node(f"comp:{node_id}"):
            return f"comp:{node_id}"

        return node_id

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
                    detected_power_rail = None
                    detected_voltage = None
                    for other_net in self._G.neighbors(neighbor):
                        if other_net != node_id:
                            odata = self._G.nodes[other_net]
                            is_pwr = (
                                bool(odata.get("is_power")) or
                                odata.get("net_type") == "Power" or
                                bool(re.search(r"(?i)(?:VCC|VDD|VBUS|3V3|5V|1V8|PWR|\+?\d+(?:\.\d+)?V)", other_net))
                            )
                            if is_pwr:
                                is_pullup = True
                                detected_power_rail = str(odata.get("net_name") or other_net.replace("net:", ""))
                                detected_voltage = odata.get("operating_voltage")
                                break
                    if is_pullup:
                        r_dict = ComponentNode(ndata)
                        r_dict["_id"] = neighbor
                        r_dict["resistance_ohm"] = self.extract_resistance_ohms(ndata.get("part_value", ""))
                        r_dict["power_rail"] = detected_power_rail
                        r_dict["power_rail_voltage"] = detected_voltage
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

    def get_pin_name(
        self,
        comp_node: Union[ComponentNode, Dict[str, Any], str],
        net_node: Union[NetNode, Dict[str, Any], str]
    ) -> Optional[str]:
        """
        取得指定元件連接至指定網路的實體引腳名稱 (pin_name)

        Args:
            comp_node: 元件節點包裝物件或元件識別名稱 (如 U1 或 comp:U1)
            net_node: 網路節點包裝物件或網路識別名稱 (如 USB_DP 或 net:USB_DP)

        Returns:
            Optional[str]: 引腳名稱 (例如 "DP", "D+", "IN+"), 若未找到邊或無引腳名稱則回傳 None
        """
        comp_id = self._resolve_node_id(comp_node, expected_prefix="comp:")
        net_id = self._resolve_node_id(net_node, expected_prefix="net:")

        if not comp_id or not net_id:
            return None

        if self._G.has_edge(comp_id, net_id):
            edge_data = self._G.get_edge_data(comp_id, net_id) or {}
            pin_name = edge_data.get("pin_name")
            if pin_name:
                return str(pin_name)
            pin_num = edge_data.get("pin_number")
            if pin_num:
                return str(pin_num)
        return None

    @staticmethod
    def _resolve_cmc_out_pin(cdata: Dict[str, Any], in_pin: str) -> Optional[str]:
        """
        解析 4-pin 共模扼流圈 (CMC) 之差分線圈穿透對應引腳
        預設直通型: Pin 1 ⟷ Pin 4, Pin 2 ⟷ Pin 3
        [架構預留]: 後續可透過 PartDB 規格書 schema 讀取自訂 choke_pin_pairs 擴充
        """
        if not in_pin:
            return None
        pin_str = str(in_pin).strip()
        # [Placeholder] 未來 PartDB 自訂擴充介面
        part_spec = cdata.get("part_spec") or {}
        custom_pairs = part_spec.get("choke_pin_pairs")
        if custom_pairs and isinstance(custom_pairs, dict):
            matched = custom_pairs.get(pin_str)
            if matched:
                return str(matched)

        # 預設標準 4-pin CMC 直通型線圈對應
        DEFAULT_CMC_PAIRS = {
            "1": "4",
            "4": "1",
            "2": "3",
            "3": "2",
        }
        return DEFAULT_CMC_PAIRS.get(pin_str)

    def _find_net_connected_to_pin(self, comp_id: str, pin: Optional[str]) -> Optional[str]:
        """找出元件特定引腳編號所連接的網路節點 ID"""
        if not pin or not self._G.has_node(comp_id):
            return None
        target_pin_str = str(pin).strip()
        for n in self._G.neighbors(comp_id):
            if self._G.nodes[n].get("type") == "net":
                edge = self._G.get_edge_data(comp_id, n) or {}
                edge_pin = str(edge.get("pin_number") or edge.get("pin") or "").strip()
                if edge_pin == target_pin_str:
                    return n
        return None

    def trace_differential_end_to_end(
        self,
        net_node: Union[NetNode, Dict[str, Any], str]
    ) -> List[Dict[str, Any]]:
        """
        穿越串聯被動元件 (如 AC 耦合電容、串聯電阻)，追蹤訊號網路到達的所有端點 IC/連接器與引腳名稱

        Args:
            net_node: 起始網路節點

        Returns:
            List[Dict[str, Any]]: 端點資訊字典清單，每一項包含:
                - "component": ComponentNode (端點元件)
                - "pin_name": str (端點引腳名稱)
                - "pin_number": str (端點引腳編號)
                - "terminal_net": NetNode (該端點所連接的最終網路)
                - "pass_through_components": List[ComponentNode] (途經之串聯被動元件清單)
        """
        start_net_id = self._resolve_node_id(net_node, expected_prefix="net:")
        if not start_net_id or not self._G.has_node(start_net_id):
            return []

        endpoints: List[Dict[str, Any]] = []
        visited_nets = set([start_net_id])
        visited_comps = set()

        start_net_name = str(self._G.nodes[start_net_id].get("net_name") or start_net_id)
        # queue 元素: (curr_net_id, pass_through_comps_list, path_segments_list, covered_nets_list)
        queue = [(start_net_id, [], [], [start_net_name])]

        while queue:
            curr_net_id, pass_through_comps, path_segments, covered_nets = queue.pop(0)

            for neighbor_comp_id in self._G.neighbors(curr_net_id):
                cdata = self._G.nodes[neighbor_comp_id]
                if cdata.get("type") != "component":
                    continue

                if neighbor_comp_id in visited_comps:
                    continue

                cat = cdata.get("category", "")
                sub = cdata.get("sub_category", "")
                role = cdata.get("functional_role", "")

                # 輔助判定是否為電源或接地網路 (嚴禁訊號路徑穿透至供電軌或接地)
                def _is_pwr_or_gnd_net(net_id: str) -> bool:
                    nd = self._G.nodes[net_id]
                    if nd.get("is_power") or nd.get("is_ground"):
                        return True
                    n_type = nd.get("net_type", "")
                    if n_type in ["Power", "Ground"]:
                        return True
                    nm = str(nd.get("net_name") or net_id).upper()
                    if any(gnd_tag in nm for gnd_tag in ["GND", "VSS", "AGND", "DGND", "PGND", "SGND"]):
                        return True
                    if re.search(r"^(?:VCC|VDD|VBUS|VIN|VBAT|VSYS|\+?\d+(?:\.\d+)?V)", nm):
                        return True
                    return False

                # 取得該元件連向的所有 Net 節點
                connected_nets = [
                    n for n in self._G.neighbors(neighbor_comp_id)
                    if self._G.nodes[n].get("type") == "net"
                ]

                has_power_or_gnd = any(_is_pwr_or_gnd_net(n) for n in connected_nets)

                # 取得連入邊之引腳資訊
                edge_data_in = self._G.get_edge_data(neighbor_comp_id, curr_net_id) or {}
                in_pin = str(edge_data_in.get("pin_number") or edge_data_in.get("pin") or "")

                # 穿透模式 A: 2-pin 串聯被動元件 (如 AC 耦合電容、串聯電阻、磁珠)
                is_2pin_pass_through = (
                    len(connected_nets) == 2 and
                    not has_power_or_gnd and
                    (cat in ["Passive", "Discrete"] or sub in ["Resistor", "Capacitor", "Inductor", "FerriteBead"]) and
                    role in ["Series_Resistor", "AC_Coupling_Capacitor", "Filter", "Passive_Support", "None", ""]
                )

                # 穿透模式 B: 4-pin 共模扼流圈 (Common Mode Choke, CMC，例如 TL1)
                is_cmc_candidate = (
                    len(connected_nets) == 4 and
                    not has_power_or_gnd and
                    (sub in ["Inductor", "Choke", "Filter"] or
                     role in ["Common_Mode_Choke", "Filter", "Choke", "CMC"] or
                     "CHOKE" in str(cdata.get("part_value", "")).upper() or
                     "CMC" in str(cdata.get("part_value", "")).upper() or
                     cat in ["Passive", "Discrete"])
                )
                cmc_out_pin = self._resolve_cmc_out_pin(cdata, in_pin) if is_cmc_candidate else None
                cmc_next_net = self._find_net_connected_to_pin(neighbor_comp_id, cmc_out_pin) if cmc_out_pin else None
                is_cmc_pass_through = bool(is_cmc_candidate and cmc_next_net and cmc_next_net != curr_net_id)

                if is_2pin_pass_through or is_cmc_pass_through:
                    visited_comps.add(neighbor_comp_id)
                    c_node = ComponentNode(cdata)
                    c_node["_id"] = neighbor_comp_id

                    if is_2pin_pass_through:
                        next_net_id = [n for n in connected_nets if n != curr_net_id][0]
                        edge_data_out = self._G.get_edge_data(neighbor_comp_id, next_net_id) or {}
                        out_pin = str(edge_data_out.get("pin_number") or edge_data_out.get("pin") or "")
                    else:
                        next_net_id = cmc_next_net
                        out_pin = str(cmc_out_pin)

                    next_net_name = str(self._G.nodes[next_net_id].get("net_name") or next_net_id)
                    curr_net_name = str(self._G.nodes[curr_net_id].get("net_name") or curr_net_id)

                    seg = {
                        "from_net": curr_net_name,
                        "pass_component": str(cdata.get("ref_des") or neighbor_comp_id),
                        "pass_component_type": str(sub or cat or "Passive"),
                        "in_pin": in_pin,
                        "out_pin": out_pin,
                        "to_net": next_net_name,
                    }

                    if next_net_id not in visited_nets and not _is_pwr_or_gnd_net(next_net_id):
                        visited_nets.add(next_net_id)
                        queue.append((
                            next_net_id,
                            pass_through_comps + [c_node],
                            path_segments + [seg],
                            covered_nets + [next_net_name]
                        ))
                else:
                    # 若為連接電源或地線的旁路被動元件 (如對地濾波電容、上拉/下拉電阻)，非訊號端點，直接忽略
                    is_pwr_gnd_passive = (
                        (cat in ["Passive", "Discrete"] or sub in ["Resistor", "Capacitor", "Inductor", "FerriteBead"]) and
                        has_power_or_gnd
                    )
                    if is_pwr_gnd_passive:
                        continue

                    # 忽略機械/非電氣結構件 (例如螺絲孔 MTG、螺帽 NUT 等)
                    if not cdata.get("is_electrical", True) or cat in ["Mechanical", "Non_Electrical"]:
                        continue

                    # 非穿透型主動/連接器元件，視為實質端點 (如 IC, MCU, Connector, TVS 等)
                    edge_data = self._G.get_edge_data(neighbor_comp_id, curr_net_id) or {}
                    pin_name = str(edge_data.get("pin_name") or edge_data.get("pin_number") or "")
                    pin_number = str(edge_data.get("pin_number") or "")

                    comp_node = ComponentNode(cdata)
                    comp_node["_id"] = neighbor_comp_id

                    term_net_data = self._G.nodes[curr_net_id]
                    term_net_node = NetNode(term_net_data)
                    term_net_node["_id"] = curr_net_id

                    endpoints.append({
                        "component": comp_node,
                        "pin_name": pin_name,
                        "pin_number": pin_number,
                        "terminal_net": term_net_node,
                        "pass_through_components": pass_through_comps,
                        "path_segments": path_segments,
                        "covered_nets": list(dict.fromkeys(covered_nets)),
                    })

        return endpoints

    def check_differential_pair_symmetry(
        self,
        p_net_node: Union[NetNode, Dict[str, Any], str],
        n_net_node: Union[NetNode, Dict[str, Any], str]
    ) -> Dict[str, Any]:
        """
        對稱性評估：比較正端 (P) 與負端 (N) 差分網路的端點元件、引腳名稱與串聯電容被動元件

        Args:
            p_net_node: 正端 (P) 差分網路
            n_net_node: 負端 (N) 差分網路

        Returns:
            Dict[str, Any]: 對稱性評估結果，包含:
                - "is_symmetric": bool (拓撲結構與元件數量是否完全對稱)
                - "p_endpoints": List[Dict] (P 端端點資訊)
                - "n_endpoints": List[Dict] (N 端端點資訊)
                - "asymmetry_reasons": List[str] (若不對稱之詳細原因說明)
        """
        p_endpoints = self.trace_differential_end_to_end(p_net_node)
        n_endpoints = self.trace_differential_end_to_end(n_net_node)

        reasons = []

        if len(p_endpoints) != len(n_endpoints):
            reasons.append(f"端點元件數量不對稱：P 端有 {len(p_endpoints)} 個端點，N 端有 {len(n_endpoints)} 個端點")

        # 檢查 P 端每個端點元件是否在 N 端有對應元件
        p_comp_ids = set(ep["component"].ref_des for ep in p_endpoints if ep["component"].ref_des)
        n_comp_ids = set(ep["component"].ref_des for ep in n_endpoints if ep["component"].ref_des)

        missing_in_n = p_comp_ids - n_comp_ids
        missing_in_p = n_comp_ids - p_comp_ids

        if missing_in_n:
            reasons.append(f"元件 {', '.join(missing_in_n)} 僅連接至 P 端，未連接至 N 端")
        if missing_in_p:
            reasons.append(f"元件 {', '.join(missing_in_p)} 僅連接至 N 端，未連接至 P 端")

        # 比較 P/N 途經之 AC 耦合電容數量與規格
        p_caps = [
            c for ep in p_endpoints for c in ep["pass_through_components"]
            if c.sub_category == "Capacitor" or c.functional_role == "AC_Coupling_Capacitor"
        ]
        n_caps = [
            c for ep in n_endpoints for c in ep["pass_through_components"]
            if c.sub_category == "Capacitor" or c.functional_role == "AC_Coupling_Capacitor"
        ]

        if len(p_caps) != len(n_caps):
            reasons.append(f"串聯 AC 耦合電容數量不對稱：P 端有 {len(p_caps)} 個，N 端有 {len(n_caps)} 個")

        is_symmetric = len(reasons) == 0

        # 收集 P/N 雙端差分通道所覆蓋的所有子網段與鏈路段落
        all_covered = []
        for ep in p_endpoints + n_endpoints:
            all_covered.extend(ep.get("covered_nets", []))
        all_covered_nets = list(dict.fromkeys(all_covered))

        p_segs = []
        for ep in p_endpoints:
            p_segs.extend(ep.get("path_segments", []))
        n_segs = []
        for ep in n_endpoints:
            n_segs.extend(ep.get("path_segments", []))

        return {
            "is_symmetric": is_symmetric,
            "p_endpoints": p_endpoints,
            "n_endpoints": n_endpoints,
            "asymmetry_reasons": reasons,
            "covered_nets": all_covered_nets,
            "p_path_segments": p_segs,
            "n_path_segments": n_segs,
        }

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
