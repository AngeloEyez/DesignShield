"""
Cadence OrCAD XML 與 Allegro Netlist 解析器 (Cadence OrCAD XML & Netlist Parser)

解析 XML 中的 PartInst 元件屬性、Pins 與 Alias 網路名稱，並支援讀取 Allegro pstxnet.dat 實體連線。
"""

import os
import re
import yaml
import logging
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional, Tuple, Set

from backend.app.engine.classifier import classify_components_batch
from backend.app.engine.bom_parser import validate_and_extract_bom_configs, apply_bomslot_replacements

logger = logging.getLogger("designshield.parser")


def _extract_power_ground_regexes() -> Tuple[List[str], List[str], List[str], List[str]]:
    """
    動態自 patterns/level2_topology/power/ (或相容 patterns/power/) YAML 規則提取電源與接地之正則表達式，
    消除主程式中之硬編碼正則字串。
    
    Returns:
        (gnd_sym_regexes, gnd_net_regexes, pwr_sym_regexes, pwr_net_regexes)
    """
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../patterns/level2_topology/power"))
    if not os.path.exists(base_dir):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../patterns/power"))

    gnd_sym_regexes: List[str] = []
    gnd_net_regexes: List[str] = []
    pwr_sym_regexes: List[str] = []
    pwr_net_regexes: List[str] = []

    if not os.path.exists(base_dir):
        return gnd_sym_regexes, gnd_net_regexes, pwr_sym_regexes, pwr_net_regexes

    for fname in sorted(os.listdir(base_dir)):
        if (fname.endswith(".yaml") or fname.endswith(".yml")) and not fname.startswith("_"):
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


def extract_package_properties(pkg_elem: ET.Element) -> Tuple[Dict[str, str], Dict[str, Dict[str, str]]]:
    """
    自 OrCAD Package XML 元素中擷取 Library Symbol 層級的使用者定義屬性 (實作 OrCAD 屬性繼承機制)。
    
    在 OrCAD Capture 中，零件庫 (.OLB) 定義之預設屬性 (Property Editor 中顯示有底線的屬性，如 BOM='NOBOM')
    儲存於 <Package> 下的 <LibPart> -> <NormalView> / <ConvertView> -> <SymbolUserProp>。
    
    @param {ET.Element} pkg_elem - <Package> XML 節點
    @returns {Tuple[Dict[str, str], Dict[str, Dict[str, str]]]} 
        回傳包含 (pkg_props, view_props) 之元組:
        - pkg_props: 該 Package 統整之預設屬性字典 {prop_name: prop_val}
        - view_props: 依特定圖形視圖劃分之屬性字典 {graphic_name: {prop_name: prop_val}}
    """
    pkg_props: Dict[str, str] = {}
    view_props: Dict[str, Dict[str, str]] = {}

    # 1. 遍歷 LibPart 中的各個圖形視圖 (NormalView 與 ConvertView)
    for lp in pkg_elem.findall("LibPart"):
        lp_defn = lp.find("Defn")
        cell_name = lp_defn.get("CellName", "") if lp_defn is not None else ""
        for view_tag in ("NormalView", "ConvertView"):
            for view in lp.findall(view_tag):
                v_defn = view.find("Defn")
                suffix = v_defn.get("suffix", "") if v_defn is not None else ""
                graphic_name = f"{cell_name}{suffix}" if cell_name else ""
                v_dict: Dict[str, str] = {}
                for sup in view.findall("SymbolUserProp"):
                    p_defn = sup.find("Defn")
                    if p_defn is not None:
                        p_name = p_defn.get("name")
                        p_val = p_defn.get("val", "")
                        if p_name and p_val is not None:
                            v_dict[p_name] = p_val
                            pkg_props[p_name] = p_val
                if graphic_name and v_dict:
                    view_props[graphic_name] = v_dict

    # 2. 遞迴補充可能直接位於 Package 或其他子層級的 SymbolUserProp 與 PackageUserProp
    for sup in pkg_elem.findall(".//SymbolUserProp"):
        p_defn = sup.find("Defn")
        if p_defn is not None:
            p_name = p_defn.get("name")
            p_val = p_defn.get("val", "")
            if p_name and p_name not in pkg_props and p_val is not None:
                pkg_props[p_name] = p_val

    for pup in pkg_elem.findall(".//PackageUserProp"):
        p_defn = pup.find("Defn")
        if p_defn is not None:
            p_name = pup.get("name")
            p_val = pup.get("val", "")
            if p_name and p_name not in pkg_props and p_val is not None:
                pkg_props[p_name] = p_val

    return pkg_props, view_props


def _scan_orcad_hierarchy_and_occurrences(
    xml_path: str,
    task_id: Optional[str] = None
) -> Tuple[str, Set[str], Set[str], Dict[str, Dict[str, str]]]:
    """
    預掃描 Cadence OrCAD XML 階層架構與 Occurrence 實例記錄 (Strict Mode)

    嚴格檢驗規範：
    1. 必須具備 <Design> 頂層根線路定義 (<Defn rootName="...">)
    2. 必須具備 <Occurrences> 節點且含有有效的 <InstOccurrence> 實例
    3. 透過 <DrawnInst> 階層區塊 (ContentsViewName) 遞迴推導所有啟用的子線路 (active_schematics)

    Args:
        xml_path: OrCAD XML 檔案實體路徑
        task_id: 可選任務 ID 用於 TaskLogger

    Returns:
        Tuple:
            - root_name: 頂層主線路名稱 (如 'NVL')
            - active_schematics: 所有在主線路階層樹內生效的 Schematic 名稱集合
            - active_ref_inst_ids: 所有在 <Occurrences> 中標記為生效的元件實例 dbId 集合
            - occ_props_by_ref_id: 各 dbId 對應之 Occurrence 屬性覆寫字典 (OccUserProp)

    Raises:
        ValueError: 當缺少 rootName、缺少 Occurrences 或無有效實例記錄時拋出
    """
    from backend.app.core.task_logger import get_task_logger
    t_logger = get_task_logger(task_id) if task_id else None

    root_name: Optional[str] = None
    has_occurrences_tag = False
    active_ref_inst_ids: Set[str] = set()
    occ_props_by_ref_id: Dict[str, Dict[str, str]] = {}
    schematic_children: Dict[str, Set[str]] = {}
    current_schematic: Optional[str] = None
    stack: List[str] = []

    context = ET.iterparse(xml_path, events=("start", "end"))
    for event, elem in context:
        if event == "start":
            stack.append(elem.tag)
            if elem.tag == "Occurrences":
                has_occurrences_tag = True
        elif event == "end":
            if elem.tag == "Defn":
                if len(stack) >= 2 and stack[-2] == "Design":
                    root_name = elem.get("rootName")
                elif len(stack) >= 2 and stack[-2] == "Schematic":
                    current_schematic = elem.get("name", "")
            elif elem.tag == "Schematic":
                current_schematic = None
            elif elem.tag == "DrawnInst":
                cview_elem = elem.find("ContentsViewName/Defn")
                if cview_elem is not None:
                    cname = cview_elem.get("name")
                    if cname and current_schematic:
                        schematic_children.setdefault(current_schematic, set()).add(cname)
                elem.clear()
            elif elem.tag == "InstOccurrence":
                defn = elem.find("Defn")
                if defn is not None:
                    ref_id = defn.get("refInstId")
                    if ref_id and ref_id != "-1":
                        active_ref_inst_ids.add(ref_id)
                        props: Dict[str, str] = {}
                        for p in elem.findall("OccUserProp"):
                            pd = p.find("Defn")
                            if pd is not None:
                                pname = pd.get("name")
                                pval = pd.get("val")
                                if pname:
                                    props[pname] = pval if pval is not None else ""
                        if props:
                            occ_props_by_ref_id[ref_id] = props
                elem.clear()
            elif elem.tag in ("Package", "PartInst", "Alias", "Global", "WireScalar", "PortInstScalar"):
                elem.clear()
            stack.pop()

    if not root_name:
        raise ValueError("無效的 OrCAD XML 檔案：缺少 <Design> 頂層根線路名稱 (<Defn rootName='...'>)。")

    if not has_occurrences_tag:
        raise ValueError("無效的 OrCAD XML 檔案：缺少 <Occurrences> 節點，無法判定生效階層元件。")

    if not active_ref_inst_ids:
        raise ValueError("無效的 OrCAD XML 檔案：<Occurrences> 節點內未包含任何有效的實例記錄 (<InstOccurrence>)。")

    # 遞迴或 BFS 解析所有生效的 Schematic
    active_schematics: Set[str] = set()
    queue = [root_name]
    while queue:
        curr = queue.pop(0)
        if curr not in active_schematics:
            active_schematics.add(curr)
            for child in schematic_children.get(curr, []):
                if child not in active_schematics:
                    queue.append(child)

    logger.info(
        "OrCAD 階層掃描完成: 根線路='%s', 生效線路共 %d 個 (%s), 生效 Occurrence 元件共 %d 個",
        root_name,
        len(active_schematics),
        ", ".join(sorted(list(active_schematics))),
        len(active_ref_inst_ids)
    )

    if t_logger:
        t_logger.info(
            "PARSE_AND_GRAPH",
            "PARSER",
            f"OrCAD 階層結構掃描完成: 根線路 '{root_name}'，包含 {len(active_schematics)} 個有效線路與 {len(active_ref_inst_ids)} 個生效元件",
            details={
                "root_name": root_name,
                "active_schematics": sorted(list(active_schematics)),
                "active_occurrences_count": len(active_ref_inst_ids),
                "schematic_children": {k: list(v) for k, v in schematic_children.items()}
            }
        )

    return root_name, active_schematics, active_ref_inst_ids, occ_props_by_ref_id


def parse_orcad_xml(
    xml_path: str,
    is_mp_mode: bool = False,
    task_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    解析 Cadence OrCAD Capture XML 檔案，支援階層式線路與 Occurrence 屬性優先級處理 (Strict Mode)。
    
    Args:
        xml_path: XML 檔案路徑
        is_mp_mode: 是否處於量產模式 (True: MP Mode, False: 樣品/NPI Mode)
        task_id: 可選的任務 ID (用於結構化日誌記錄)
        
    Returns:
        Dict: 包含 components (元件字典)、net_aliases (網路別名)、power_symbol_nets、ground_symbol_nets、net_symbols 與 bom_config_info
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

    # 1. 嚴格模式階層預掃描：識別 Root Schematic、生效子線路與 Occurrence 白名單
    root_name, active_schematics, active_ref_inst_ids, occ_props_by_ref_id = _scan_orcad_hierarchy_and_occurrences(
        xml_path, task_id=task_id
    )

    components: Dict[str, Dict[str, Any]] = {}
    net_aliases: Dict[str, List[Dict[str, int]]] = {}
    net_symbols: Dict[str, List[str]] = {}
    power_symbol_nets = set()
    ground_symbol_nets = set()
    package_pin_map: Dict[str, Dict[str, str]] = {}
    ref_pin_map: Dict[str, Dict[str, str]] = {}
    package_props: Dict[str, Dict[str, str]] = {}
    package_view_props: Dict[Tuple[str, str], Dict[str, str]] = {}
    
    current_schematic: Optional[str] = None
    stack: List[str] = []

    # 2. 串流解析第二階段：僅提取生效線路與 Occurrence 白名單內之元件與網路
    context = ET.iterparse(xml_path, events=("start", "end"))
    
    for event, elem in context:
        if event == "start":
            stack.append(elem.tag)
        elif event == "end":
            if elem.tag == "Defn":
                if len(stack) >= 2 and stack[-2] == "Schematic":
                    current_schematic = elem.get("name", "")
            elif elem.tag == "Schematic":
                current_schematic = None
            elif elem.tag == "Package":
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
                        package_pin_map[pkg_name.lower()] = pin_map

                    # 擷取 Library Package 原生使用者屬性 (實作 OrCAD 屬性繼承特性)
                    pkg_user_props, v_props = extract_package_properties(elem)
                    if pkg_user_props:
                        package_props[pkg_name] = pkg_user_props
                        package_props[pkg_name.lower()] = pkg_user_props
                    for g_name, vp in v_props.items():
                        package_view_props[(pkg_name, g_name)] = vp
                        package_view_props[(pkg_name.lower(), g_name.lower())] = vp
                elem.clear()

            elif elem.tag == "PartInst":
                defn_elem = elem.find("Defn")
                db_id = defn_elem.get("dbId") if defn_elem is not None else None

                # 僅載入「屬於有效線路」且「存在於 Occurrence 白名單」之元件
                if current_schematic in active_schematics and db_id in active_ref_inst_ids:
                    ref = None
                    ref_elem = elem.find("Reference/Defn")
                    if ref_elem is not None:
                        ref = ref_elem.get("name")
                        
                    val = ""
                    val_elem = elem.find("PartValue/Defn")
                    if val_elem is not None:
                        val = val_elem.get("name") or ""
                        
                    loc_x = int(defn_elem.get("locX", 0)) if defn_elem is not None else 0
                    loc_y = int(defn_elem.get("locY", 0)) if defn_elem is not None else 0
                    pkg_name = defn_elem.get("pkgName", "") if defn_elem is not None else ""

                    graphic_name = ""
                    g_elem = elem.find("GraphicName/Defn")
                    if g_elem is not None:
                        graphic_name = g_elem.get("name", "")

                    # 依據 OrCAD 屬性繼承機制：
                    # 1. 優先以 Package / Library Symbol 層級屬性為基礎預設值
                    user_props = {}
                    if pkg_name:
                        if pkg_name in package_props:
                            user_props.update(package_props[pkg_name])
                        elif pkg_name.lower() in package_props:
                            user_props.update(package_props[pkg_name.lower()])

                    if pkg_name and graphic_name:
                        if (pkg_name, graphic_name) in package_view_props:
                            user_props.update(package_view_props[(pkg_name, graphic_name)])
                        elif (pkg_name.lower(), graphic_name.lower()) in package_view_props:
                            user_props.update(package_view_props[(pkg_name.lower(), graphic_name.lower())])

                    # 2. 實例層級 PartInstUserProp 覆寫庫屬性
                    for prop in elem.findall("PartInstUserProp"):
                        p_defn = prop.find("Defn")
                        if p_defn is not None:
                            p_name = p_defn.get("name", "")
                            p_val = p_defn.get("val", "")
                            if p_name:
                                user_props[p_name] = p_val

                    # 3. Occurrence 層級 OccUserProp 具備最高優先權 (Occurrence Precedence)
                    if db_id in occ_props_by_ref_id:
                        for o_name, o_val in occ_props_by_ref_id[db_id].items():
                            if o_name in ("Part Reference", "Reference") and o_val:
                                ref = o_val
                            elif o_name in ("Value", "Part Value") and o_val:
                                val = o_val
                            else:
                                user_props[o_name] = o_val

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
                        if ref in components:
                            # 多 Section 元件合併引腳與屬性
                            components[ref]["pins"].extend(pins)
                            for uk, uv in user_props.items():
                                if uk not in components[ref]["user_props"]:
                                    components[ref]["user_props"][uk] = uv
                        else:
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
                                "pins": pins,
                                "schematic_name": current_schematic,
                                "db_id": db_id
                            }
                elem.clear()
                
            elif elem.tag == "Alias":
                # 僅收集有效線路範圍之網路別名
                if current_schematic in active_schematics:
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
                # 僅收集有效線路範圍之電源與接地全域符號
                if current_schematic in active_schematics:
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

            elif elem.tag in ("WireScalar", "GraphicLineInst", "GraphicBoxInst", "DrawnInst", "InstOccurrence"):
                elem.clear()

            stack.pop()
            
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

    # 執行 BOMSLOT 零件置換與清理 (依據當前專案之 NPI / MP 模式)
    classified_components, bom_config_info = apply_bomslot_replacements(
        classified_components,
        bom_config_info,
        is_mp_mode=is_mp_mode,
        task_id=task_id
    )

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
        "package_props": package_props,
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
