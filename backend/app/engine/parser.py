"""
Cadence OrCAD XML 與 Allegro Netlist 解析器 (Cadence OrCAD XML & Netlist Parser)

解析 XML 中的 PartInst 元件屬性、Pins 與 Alias 網路名稱，並支援讀取 Allegro pstxnet.dat 實體連線。
"""

import os
import re
import logging
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional

from backend.app.engine.classifier import classify_components_batch

logger = logging.getLogger("designshield.parser")


def parse_orcad_xml(xml_path: str, task_id: Optional[str] = None) -> Dict[str, Any]:
    """
    解析 Cadence OrCAD Capture XML 檔案
    
    Args:
        xml_path: XML 檔案路徑
        task_id: 可選的任務 ID (用於結構化日誌記錄)
        
    Returns:
        Dict: 包含 components (元件字典) 與 nets (網路基本資訊)
    """
    logger.info("Parsing OrCAD XML: %s", xml_path)
    components: Dict[str, Dict[str, Any]] = {}
    net_aliases: Dict[str, List[Dict[str, int]]] = {}
    
    # 使用 iterparse 節省記憶體並高效迭代
    context = ET.iterparse(xml_path, events=("end",))
    
    for _, elem in context:
        if elem.tag == "PartInst":
            ref = None
            ref_elem = elem.find("Reference/Defn")
            if ref_elem is not None:
                ref = ref_elem.get("name")
                
            val = ""
            val_elem = elem.find("PartValue/Defn")
            if val_elem is not None:
                val = val_elem.get("name") or ""
                
            defn_elem = elem.find("Defn")
            loc_x = int(defn_elem.get("locX", 0)) if defn_elem is not None else 0
            loc_y = int(defn_elem.get("locY", 0)) if defn_elem is not None else 0
            pkg_name = defn_elem.get("pkgName", "") if defn_elem is not None else ""
            
            # 解析 PartInstUserProp
            user_props = {}
            for prop in elem.findall("PartInstUserProp"):
                p_defn = prop.find("Defn")
                if p_defn is not None:
                    p_name = p_defn.get("name", "")
                    p_val = p_defn.get("val", "")
                    if p_name:
                        user_props[p_name] = p_val
                        
            # 解析引腳 Pins (PortInstScalar)
            pins = []
            for port in elem.findall("PortInstScalar"):
                p_defn = port.find("Defn")
                if p_defn is not None:
                    p_num = p_defn.get("name", "")
                    start_x = int(p_defn.get("startX", 0))
                    start_y = int(p_defn.get("startY", 0))
                    hotpt_x = int(p_defn.get("hotptX", 0))
                    hotpt_y = int(p_defn.get("hotptY", 0))
                    pins.append({
                        "pin_number": p_num,
                        "pin_name": p_num,
                        "abs_x": loc_x + hotpt_x,
                        "abs_y": loc_y + hotpt_y,
                        "start_x": loc_x + start_x,
                        "start_y": loc_y + start_y
                    })
                    
            if ref:
                package = user_props.get("PCB Footprint", pkg_name)
                mfg_pn = user_props.get("Mfg Part Number", user_props.get("Part Number", ""))
                components[ref] = {
                    "ref_des": ref,
                    "part_value": val,
                    "package": package,
                    "package_size": user_props.get("Package Size", ""),
                    "description": user_props.get("Description", ""),
                    "mfg": user_props.get("Mfg", ""),
                    "mfg_pn": mfg_pn,
                    "voltage": user_props.get("Voltage", ""),
                    "loc": (loc_x, loc_y),
                    "user_props": user_props,
                    "pins": pins
                }
            elem.clear()
            
        elif elem.tag == "Alias":
            defn = elem.find("Defn")
            if defn is not None:
                net_name = defn.get("name")
                if net_name:
                    loc_x = int(defn.get("locX", 0))
                    loc_y = int(defn.get("locY", 0))
                    if net_name not in net_aliases:
                        net_aliases[net_name] = []
                    net_aliases[net_name].append({"locX": loc_x, "locY": loc_y})
            elem.clear()
            
    # 執行元數據與證據鏈批次分類
    classified_components = classify_components_batch(components, task_id=task_id)

    return {
        "components": classified_components,
        "net_aliases": net_aliases
    }


def parse_allegro_netlist(netlist_path: str) -> Dict[str, List[Dict[str, str]]]:
    """
    解析 Allegro Netlist (pstxnet.dat) 檔案
    
    Args:
        netlist_path: pstxnet.dat 檔案路徑
        
    Returns:
        Dict: net_name -> 清單包含各節點 {"ref_des": ref, "pin_number": pin, "pin_name": pin_name}
    """
    logger.info("Parsing Allegro Netlist: %s", netlist_path)
    nets: Dict[str, List[Dict[str, str]]] = {}
    
    if not os.path.exists(netlist_path):
        return nets
        
    with open(netlist_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
        
    # 分割各個 NET 區塊
    net_blocks = content.split("NET_NAME")
    for block in net_blocks[1:]:
        lines = block.strip().splitlines()
        if not lines:
            continue
            
        # 第一行為 'NET_NAME'
        first_line = lines[0].strip()
        net_match = re.search(r"'([^']+)'", first_line)
        if not net_match:
            continue
        net_name = net_match.group(1).strip()
        
        connections = []
        # 解析該 NET 下的所有 NODE_NAME
        node_matches = re.finditer(r"NODE_NAME\s+([^\s]+)\s+([^\s\n]+)", block)
        for nm in node_matches:
            ref = nm.group(1).strip()
            pin = nm.group(2).strip()
            connections.append({
                "ref_des": ref,
                "pin_number": pin,
                "pin_name": pin
            })
            
        if net_name:
            nets[net_name] = connections
            
    return nets


def merge_schematic_data(xml_data: Dict[str, Any], netlist_data: Optional[Dict[str, List[Dict[str, str]]]] = None) -> Dict[str, Any]:
    """
    整合 XML 元件屬性與 Netlist 連線圖譜
    
    Args:
        xml_data: 由 parse_orcad_xml 產生的字典
        netlist_data: 由 parse_allegro_netlist 產生的字典 (若無則使用 XML 內網路別名建立)
        
    Returns:
        Dict: 整合後的 components 與 nets
    """
    components = xml_data.get("components", {})
    net_aliases = xml_data.get("net_aliases", {})
    
    nets: Dict[str, List[Dict[str, str]]] = {}
    
    if netlist_data:
        nets.update(netlist_data)
    else:
        # 若無外部 netlist，將 XML 別名轉為基本網路節點
        for net_name in net_aliases.keys():
            nets[net_name] = []
            
    return {
        "components": components,
        "nets": nets
    }
