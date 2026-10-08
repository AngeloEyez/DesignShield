"""
Level 3 DRC 拓撲斷言評估器 (Topology Evaluator)

評估 YAML 宣告式 topology_check 規則中的 asserts 條件，產出違規詳情。
"""

import re
from typing import Dict, List, Any, Optional
import networkx as nx
from backend.app.engine.drc_engine.graph_api import GraphAPI

# 常見 I2C 晶片位址資料庫
DEFAULT_I2C_ADDRESSES = {
    "SHT40": "0x44",
    "SHT40-AD1B": "0x44",
    "SHT40-BD1B": "0x45",
    "BQ27220": "0x55",
    "PCF8563": "0x51",
    "LSM6DS3": "0x6A",
    "LSM6DS3TR": "0x6A",
    "AT24C02": "0x50",
    "AT24C04": "0x50",
    "AT24C08": "0x50",
    "TMP102": "0x48",
    "INA219": "0x40",
    "DS3231": "0x68",
    "MPU6050": "0x68",
}


class TopologyEvaluator:
    def __init__(self, G: nx.Graph, graph_api: GraphAPI):
        self.G = G
        self.api = graph_api

    def evaluate_assert(self, assertion: Dict[str, Any], target: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        評估單一斷言條件。若合規回傳 None；若違規回傳錯誤資訊字典。
        """
        cond = assertion.get("condition")
        raw_msg = assertion.get("error_message", "拓撲斷言失敗")

        def format_msg(msg: str) -> str:
            msg = msg.replace("${context.target.net_name}", str(target.get("net_name", "")))
            msg = msg.replace("${context.target.ref_des}", str(target.get("ref_des", "")))
            msg = msg.replace("${context.target.part_value}", str(target.get("part_value", "")))
            msg = msg.replace("${context.target.name}", str(target.get("name", target.get("net_name", ""))))
            return msg

        # 1. 屬性不等判定 (如 電源網路不能標註 is_ground = true)
        if cond == "attribute_not_equal":
            attr = assertion.get("attribute")
            expected_val = assertion.get("value")
            actual_val = target.get(attr)
            if actual_val == expected_val:
                return {
                    "violation": True,
                    "message": format_msg(raw_msg),
                    "evidence": {attr: actual_val}
                }

        # 2. I2C 上拉電阻存在性
        elif cond == "has_pullup_resistor":
            min_count = assertion.get("min_count", 1)
            pullups = self.api.get_pullup_resistors(target)
            if len(pullups) < min_count:
                return {
                    "violation": True,
                    "message": format_msg(raw_msg),
                    "evidence": {"found_pullups": len(pullups), "required_min": min_count}
                }

        # 3. 上拉電阻連接至合法電源
        elif cond == "pullup_connected_to_power":
            pullups = self.api.get_pullup_resistors(target)
            if pullups:
                for pu in pullups:
                    connected_nets = [n for n in self.G.neighbors(pu["_id"]) if n != target.get("_id") and n != target.get("net_name")]
                    has_power = any(self.G.nodes[cn].get("is_power") or "VCC" in cn.upper() or "VDD" in cn.upper() for cn in connected_nets)
                    if not has_power:
                        return {
                            "violation": True,
                            "message": format_msg(raw_msg),
                            "evidence": {"pullup_resistor": pu.get("ref_des"), "connected_nets": connected_nets}
                        }

        # 4. 電源電容耐壓降額
        elif cond == "capacitor_voltage_derating":
            min_ratio = assertion.get("min_derating_ratio", 1.5)
            node_id = target.get("_id") or target.get("ref_des")
            cap_rated_v = self._extract_voltage(target.get("voltage", "") or target.get("part_value", "") or target.get("description", ""))

            # 尋找其所連接之電源網路工作電壓
            op_voltage = 0.0
            connected_power_net = None
            for neighbor in self.G.neighbors(node_id):
                ndata = self.G.nodes[neighbor]
                if ndata.get("type") == "net":
                    v = ndata.get("operating_voltage") or self._infer_voltage_from_name(neighbor)
                    if v and v > op_voltage:
                        op_voltage = v
                        connected_power_net = neighbor

            if cap_rated_v and op_voltage > 0:
                if cap_rated_v < op_voltage * min_ratio:
                    return {
                        "violation": True,
                        "message": f"電容 {target.get('ref_des')} 額定耐壓 ({cap_rated_v}V) 未達電源網路 {connected_power_net} ({op_voltage}V) 之降額規範 (需至少 {op_voltage * min_ratio:.1f}V)",
                        "evidence": {
                            "rated_voltage": cap_rated_v,
                            "operating_voltage": op_voltage,
                            "required_min_voltage": round(op_voltage * min_ratio, 2),
                            "power_net": connected_power_net
                        }
                    }

        # 5. IC 去耦電容存在性
        elif cond == "has_decoupling_capacitor":
            node_id = target.get("_id") or target.get("ref_des")
            has_decoupling = False
            for neighbor in self.G.neighbors(node_id):
                ndata = self.G.nodes[neighbor]
                if ndata.get("type") == "net" and (ndata.get("is_power") or "VCC" in neighbor.upper()):
                    # 檢查此電源網路上是否掛載電容
                    for net_neighbor in self.G.neighbors(neighbor):
                        cdata = self.G.nodes[net_neighbor]
                        if cdata.get("sub_category") == "Capacitor" or cdata.get("category") == "Capacitor":
                            has_decoupling = True
                            break
            if not has_decoupling:
                return {
                    "violation": True,
                    "message": format_msg(raw_msg),
                    "evidence": {"ic": target.get("ref_des")}
                }

        # 6. I2C 設備位址唯一性
        elif cond == "i2c_address_unique":
            slaves = self.api.get_slave_devices(target)
            seen_addresses = {}
            for s in slaves:
                pn = s.get("part_value") or s.get("mfg_pn") or ""
                addr = None
                for k, v in DEFAULT_I2C_ADDRESSES.items():
                    if k.upper() in pn.upper():
                        addr = v
                        break
                if addr:
                    if addr in seen_addresses:
                        conflicting_dev = seen_addresses[addr]
                        return {
                            "violation": True,
                            "message": f"I2C 匯流排 ({target.get('net_name')}) 上元件 {s.get('ref_des')} ({pn}) 與 {conflicting_dev.get('ref_des')} ({conflicting_dev.get('part_value')}) 7-bit 地址皆為 {addr}，發生衝突",
                            "evidence": {
                                "conflicting_address": addr,
                                "devices": [s.get("ref_des"), conflicting_dev.get("ref_des")]
                            }
                        }
                    else:
                        seen_addresses[addr] = s

        return None

    def _extract_voltage(self, text: str) -> Optional[float]:
        match = re.search(r"(\d+(?:\.\d+)?)\s*V(?=[^0-9.]|$)", text, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass
        return None

    def _infer_voltage_from_name(self, net_name: str) -> Optional[float]:
        upper = net_name.upper()
        if "3V3" in upper or "3.3V" in upper:
            return 3.3
        if "5V" in upper or "+5V" in upper or "VBUS" in upper:
            return 5.0
        if "12V" in upper or "+12V" in upper:
            return 12.0
        if "1V8" in upper or "1.8V" in upper:
            return 1.8
        return None
