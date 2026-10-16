"""
Cadence OrCAD XML 與 Allegro Netlist 解析器 (Cadence OrCAD XML & Netlist Parser)

解析 XML 中的 PartInst 元件屬性、Pins 與 Alias 網路名稱，並支援讀取 Allegro pstxnet.dat 實體連線。
"""

import os
import re
import yaml
import logging
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional, Tuple

from backend.app.engine.classifier import classify_components_batch
from backend.app.engine.bom_parser import validate_and_extract_bom_configs

logger = logging.getLogger("designshield.parser")


def _extract_power_ground_regexes() -> Tuple[List[str], List[str], List[str], List[str]]:
    """
    動態自 patterns/power/ YAML 規則提取電源與接地之正則表達式，
    消除主程式中之硬編碼正則字串。
    
    Returns:
        (gnd_sym_regexes, gnd_net_regexes, pwr_sym_regexes, pwr_net_regexes)
    """
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../patterns/power"))
    gnd_sym_regexes: List[str] = []
    gnd_net_regexes: List[str] = []
    pwr_sym_regexes: List[str] = []
    pwr_net_regexes: List[str] = []

    if not os.path.exists(base_dir):
        return gnd_sym_regexes, gnd_net_regexes, pwr_sym_regexes, pwr_net_regexes

    for fname in sorted(os.listdir(base_dir)):
        if fname.endswith(".yaml"):
            fpath = os.path.join(base_dir, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as yf:
                    rule_data = yaml.safe_load(yf)
                if not rule_data or rule_data.get("enabled", True) is False:
                    continue
                name_lower = rule_data.get("name", "").lower()
                is_gnd = "gnd" in name_lower or "ground" in name_lower
                for sig in rule_data.get("signals", []):
                    matches = sig.get("matches", {})
                    for any_clause in matches.get("match_any", []):
                        for all_item in any_clause.get("match_all", []):
                            sym_reg = all_item.get("symbol_name_regex")
                            net_reg = all_item.get("net_name_regex")
                            if is_gnd:
                                if sym_reg and sym_reg not in gnd_sym_regexes:
                                    gnd_sym_regexes.append(sym_reg)
                                if net_reg and net_reg not in gnd_net_regexes:
                                    gnd_net_regexes.append(net_reg)
                            else:
                                if sym_reg and sym_reg not in pwr_sym_regexes:
                                    pwr_sym_regexes.append(sym_reg)
                                if net_reg and net_reg not in pwr_net_regexes:
                                    pwr_net_regexes.append(net_reg)
            except Exception as e:
                logger.warning(f"Failed to load power regex from {fname}: {e}")

    return gnd_sym_regexes, gnd_net_regexes, pwr_sym_regexes, pwr_net_regexes


def parse_orcad_xml(xml_path: str, task_id: Optional[str] = None) -> Dict[str, Any]:
    """
    解析 Cadence OrCAD Capture XML 檔案
    
    Args:
        xml_path: XML 檔案路徑
        task_id: 可選的任務 ID (用於結構化日誌記錄)
        
    Returns:
        Dict: 包含 components (元件字典)、net_aliases (網路別名)、power_symbol_nets、ground_symbol_nets 與 net_symbols
    """
    from backend.app.core.task_logger import get_task_logger
    t_logger = get_task_logger(task_id) if task_id else None

    logger.info("Parsing OrCAD XML: %s", xml_path)
    file_size = os.path.getsize(xml_path) if os.path.exists(xml_path) else 0
    if t_logger:
        t_logger.debug(
            "PARSE_AND_GRAPH",
            "PARSER",
            f"開始串流解析 OrCAD XML 檔案: {os.path.basename(xml_path)} ({file_size / 1024:.1f} KB)",
            details={"xml_path": xml_path, "file_size_bytes": file_size}
        )

    components: Dict[str, Dict[str, Any]] = {}
    net_aliases: Dict[str, List[Dict[str, int]]] = {}
    net_symbols: Dict[str, List[str]] = {}
    power_symbol_nets = set()
    ground_symbol_nets = set()
    package_pin_map: Dict[str, Dict[str, str]] = {}
    ref_pin_map: Dict[str, Dict[str, str]] = {}
    
    # 使用 iterparse 節省記憶體並高效迭代
    context = ET.iterparse(xml_path, events=("end",))
    
    for _, elem in context:
        if elem.tag == "Package":
            defn = elem.find("Defn")
            pkg_name = defn.get("name", "") if defn is not None else ""
            if pkg_name:
                pos_to_pnum = {}
                for phys in elem.findall(".//PhysicalPart"):
                    for pn in phys.findall("PinNumber"):
                        p_defn = pn.find("Defn")
                        if p_defn is not None:
                            pos = p_defn.get("position")
                            num = p_defn.get("number")
                            if pos is not None and num is not None:
                                pos_to_pnum[pos] = num

                pos_to_pname = {}
                for sp in elem.findall(".//SymbolPinScalar"):
                    sp_defn = sp.find("Defn")
                    if sp_defn is not None:
                        pos = sp_defn.get("position")
                        name = sp_defn.get("name")
                        if pos is not None and name is not None:
                            pos_to_pname[pos] = name

                pin_map = {}
                for pos, num in pos_to_pnum.items():
                    if pos in pos_to_pname:
                        pin_map[num] = pos_to_pname[pos]

                if pin_map:
                    package_pin_map[pkg_name] = pin_map
            elem.clear()

        elif elem.tag == "PartInst":
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
                mfg_val = user_props.get("Mfg", user_props.get("Supplier", user_props.get("Manufacturer", "")))
                components[ref] = {
                    "ref_des": ref,
                    "part_value": val,
                    "package": package,
                    "pkg_name": pkg_name,
                    "package_size": user_props.get("Package Size", ""),
                    "description": user_props.get("Description", ""),
                    "mfg": mfg_val,
                    "mfg_pn": mfg_pn,
                    "supplier": mfg_val,
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
            
        elif elem.tag == "Global":
            defn = elem.find("Defn")
            if defn is not None:
                net_name = defn.get("name")
                sym_name = defn.get("symbolName", "")
                if net_name:
                    if net_name not in net_symbols:
                        net_symbols[net_name] = []
                    if sym_name and sym_name not in net_symbols[net_name]:
                        net_symbols[net_name].append(sym_name)
            elem.clear()
            
    # 依據 YAML 規則動態推論電源與接地網路標籤 (完全解耦硬編碼)
    gnd_sym_regexes, gnd_net_regexes, pwr_sym_regexes, pwr_net_regexes = _extract_power_ground_regexes()
    for net_name, sym_list in net_symbols.items():
        is_gnd = False
        for reg in gnd_sym_regexes:
            if any(re.search(reg, s) for s in sym_list):
                is_gnd = True
                break
        if not is_gnd:
            for reg in gnd_net_regexes:
                if re.search(reg, net_name):
                    is_gnd = True
                    break
        if is_gnd:
            ground_symbol_nets.add(net_name)

        is_pwr = False
        for reg in pwr_sym_regexes:
            if any(re.search(reg, s) for s in sym_list):
                is_pwr = True
                break
        if not is_pwr:
            for reg in pwr_net_regexes:
                if re.search(reg, net_name):
                    is_pwr = True
                    break
        if is_pwr:
            power_symbol_nets.add(net_name)

    pwr_sym_list = sorted(list(power_symbol_nets))
    gnd_sym_list = sorted(list(ground_symbol_nets))
    if t_logger:
        t_logger.debug(
            "PARSE_AND_GRAPH",
            "PARSER",
            f"OrCAD XML 元素提取完畢: 元件 {len(components)} 個, 別名網路 {len(net_aliases)} 條, 全局電源符號 {len(pwr_sym_list)} 個, 全局接地符號 {len(gnd_sym_list)} 個",
            details={
                "components_raw_count": len(components),
                "net_aliases_count": len(net_aliases),
                "power_symbol_nets_count": len(pwr_sym_list),
                "power_symbol_nets": pwr_sym_list,
                "ground_symbol_nets_count": len(gnd_sym_list),
                "ground_symbol_nets": gnd_sym_list
            }
        )

    # 建立元件實例專屬的引腳映射表
    for ref, c_info in components.items():
        pkg = c_info.get("pkg_name") or c_info.get("package")
        if pkg and pkg in package_pin_map:
            ref_pin_map[ref] = package_pin_map[pkg]

    # 執行元數據與證據鏈批次分類
    classified_components = classify_components_batch(components, task_id=task_id)

    # 執行零件 BOM 上件狀態與多 Config 驗證
    bom_config_info = validate_and_extract_bom_configs(classified_components)
    for ref, c_data in classified_components.items():
        c_data["bom_tokens"] = bom_config_info["component_bom_tokens"].get(ref, [])
        c_data["raw_bom"] = bom_config_info["raw_bom_map"].get(ref, "")

    return {
        "components": classified_components,
        "net_aliases": net_aliases,
        "power_symbol_nets": pwr_sym_list,
        "ground_symbol_nets": gnd_sym_list,
        "net_symbols": net_symbols,
        "package_pin_map": package_pin_map,
        "ref_pin_map": ref_pin_map,
        "bom_config_info": bom_config_info
    }


def parse_allegro_netlist(netlist_path: str, task_id: Optional[str] = None) -> Dict[str, List[Dict[str, str]]]:
    """
    解析 Allegro Netlist (pstxnet.dat) 檔案
    
    Args:
        netlist_path: pstxnet.dat 檔案路徑
        task_id: 可選的任務 ID (用於結構化日誌記錄)
        
    Returns:
        Dict: net_name -> 清單包含各節點 {"ref_des": ref, "pin_number": pin, "pin_name": pin_name}
    """
    from backend.app.core.task_logger import get_task_logger
    t_logger = get_task_logger(task_id) if task_id else None

    logger.info("Parsing Allegro Netlist: %s", netlist_path)
    nets: Dict[str, List[Dict[str, str]]] = {}
    
    if not os.path.exists(netlist_path):
        if t_logger:
            t_logger.debug(
                "PARSE_AND_GRAPH",
                "PARSER",
                f"未發現 Allegro Netlist 實體檔案: {netlist_path}，將僅使用 XML 內嵌網路結構",
                details={"netlist_path": netlist_path}
            )
        return nets

    file_size = os.path.getsize(netlist_path)
    with open(netlist_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    total_lines = content.count("\n") + 1
    if t_logger:
        t_logger.debug(
            "PARSE_AND_GRAPH",
            "PARSER",
            f"開始解析 Allegro Netlist 拓撲連線: {os.path.basename(netlist_path)} ({file_size / 1024:.1f} KB, 共 {total_lines} 行)",
            details={"netlist_path": netlist_path, "size_bytes": file_size, "lines": total_lines}
        )
        
    # 分割各個 NET 區塊
    net_blocks = content.split("NET_NAME")
    skipped_blocks = 0
    total_connections = 0

    for block in net_blocks[1:]:
        lines = block.strip().splitlines()
        if not lines:
            skipped_blocks += 1
            continue
            
        # 第一行為 'NET_NAME'
        first_line = lines[0].strip()
        net_match = re.search(r"'([^']+)'", first_line)
        if not net_match:
            skipped_blocks += 1
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
            total_connections += len(connections)

    # 排序統計最大連接度網路 (Top 5 fanout nets)
    sorted_fanout = sorted(nets.items(), key=lambda kv: len(kv[1]), reverse=True)[:5]
    top_fanouts = [{"net_name": k, "connected_pins": len(v)} for k, v in sorted_fanout]

    if t_logger:
        top_fanout_str = ", ".join([f"{item['net_name']}({item['connected_pins']})" for item in top_fanouts[:3]])
        t_logger.debug(
            "PARSE_AND_GRAPH",
            "PARSER",
            f"Allegro Netlist 解析完成: 網路 {len(nets)} 條, 接腳連線 {total_connections} 處 (高連線度: {top_fanout_str})",
            details={
                "nets_count": len(nets),
                "total_connections": total_connections,
                "skipped_blocks": skipped_blocks,
                "top_fanout_nets": top_fanouts
            }
        )
            
    return nets


def merge_schematic_data(
    xml_data: Dict[str, Any],
    netlist_data: Optional[Dict[str, List[Dict[str, str]]]] = None,
    task_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    整合 XML 元件屬性與 Netlist 連線圖譜
    
    Args:
        xml_data: 由 parse_orcad_xml 產生的字典
        netlist_data: 由 parse_allegro_netlist 產生的字典 (若無則使用 XML 內網路別名建立)
        task_id: 可選的任務 ID (用於結構化日誌記錄)
        
    Returns:
        Dict: 整合後的 components, nets 與 power_symbol_nets
    """
    from backend.app.core.task_logger import get_task_logger
    t_logger = get_task_logger(task_id) if task_id else None

    components = xml_data.get("components", {})
    net_aliases = xml_data.get("net_aliases", {})
    power_symbols = xml_data.get("power_symbol_nets", [])
    ground_symbols = xml_data.get("ground_symbol_nets", [])
    net_symbols = xml_data.get("net_symbols", {})
    
    package_pin_map = xml_data.get("package_pin_map", {})
    ref_pin_map = xml_data.get("ref_pin_map", {})
    
    nets: Dict[str, List[Dict[str, str]]] = {}
    netlist_count = len(netlist_data) if netlist_data else 0
    alias_count = len(net_aliases)
    
    if netlist_data:
        for net_name, conns in netlist_data.items():
            enriched_conns = []
            for conn in conns:
                ref = conn.get("ref_des", "")
                pnum = conn.get("pin_number", "")
                
                # 優先自元件實例映射表查詢，次查 Package 映射表
                pname = None
                if ref in ref_pin_map and pnum in ref_pin_map[ref]:
                    pname = ref_pin_map[ref][pnum]
                elif ref in components:
                    pkg = components[ref].get("pkg_name") or components[ref].get("package", "")
                    if pkg in package_pin_map and pnum in package_pin_map[pkg]:
                        pname = package_pin_map[pkg][pnum]
                
                # 若查得有意義之引腳邏輯名稱則填入，否則保留原 pin_name 或 pnum
                final_pname = pname if pname else conn.get("pin_name", pnum)
                enriched_conns.append({
                    "ref_des": ref,
                    "pin_number": pnum,
                    "pin_name": final_pname
                })
            nets[net_name] = enriched_conns
        shared_count = len(set(net_aliases.keys()) & set(netlist_data.keys()))
    else:
        # 若無外部 netlist，將 XML 別名轉為基本網路節點
        for net_name in net_aliases.keys():
            nets[net_name] = []
        shared_count = 0
            
    if t_logger:
        t_logger.debug(
            "PARSE_AND_GRAPH",
            "PARSER",
            f"線路資料整合完畢: 元件 {len(components)} 顆, 合併網路 {len(nets)} 條 (網表 {netlist_count} 條, 別名 {alias_count} 條, 電源符號 {len(power_symbols)} 個, 接地符號 {len(ground_symbols)} 個)",
            details={
                "components_count": len(components),
                "total_nets_count": len(nets),
                "netlist_nets_count": netlist_count,
                "alias_nets_count": alias_count,
                "shared_nets_count": shared_count,
                "power_symbols_count": len(power_symbols),
                "power_symbols": power_symbols,
                "ground_symbols_count": len(ground_symbols),
                "ground_symbols": ground_symbols
            }
        )

    bom_config_info = xml_data.get("bom_config_info")
    if not bom_config_info:
        try:
            bom_config_info = validate_and_extract_bom_configs(components)
        except Exception:
            bom_config_info = {
                "config_count": 1,
                "config_names": ["Config 1"],
                "is_multi_config": False,
                "component_bom_tokens": {ref: ["I"] for ref in components},
                "raw_bom_map": {ref: "I" for ref in components},
            }

    return {
        "components": components,
        "nets": nets,
        "power_symbol_nets": power_symbols,
        "ground_symbol_nets": ground_symbols,
        "net_symbols": net_symbols,
        "bom_config_info": bom_config_info
    }
