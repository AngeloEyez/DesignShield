"""
四維度元件分類與語意推斷引擎 (Multi-Dimensional Component Classifier)

依據 Cadence OrCAD XML 元數據 (Description, Footprint, PartValue, Pins) 進行證據鏈推斷：
1. 實體類別 (category): IC, Passive, Discrete, Connector, Electromechanical, NonElectrical
2. 細部類型 (sub_category): Resistor, Capacitor, Inductor, TVS, MOSFET, Crystal, TestPoint, Fiducial 等
3. 拓撲角色 (functional_role): 遵循「無證據不可下結論」鐵律 (Bus_Master, Bus_Slave, Power_Source, Level_Shifter, Protection, Filter, None)
4. 電氣標籤 (is_electrical): True / False (機構件、對位點與測試點隔離)
支援批次 LLM 模糊推斷與離線優雅降級。
"""

import re
import json
import logging
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger("designshield.classifier")

# 1. 非電氣機構件與測試點特徵正規表示式 (完全依據 Description / Footprint / Value 綜合判斷，絕不依賴零件編號 RefDes)
NON_ELECTRICAL_METADATA_PATTERNS = [
    # 1. 光學對位點 (Fiducial Mark): 依 Footprint (FD55_CROSS, CROSS, FD*) 或 Description/Value 判定
    (re.compile(r"(\bFD\d+_CROSS\b|\bFD\d+\b|\bFIDUCIAL\b|MTG/ID\d+/OD\d+)", re.IGNORECASE), "Fiducial"),
    # 2. 螺絲固定孔與工藝定位孔 (Mounting Hole / Tooling Hole): 依 Description、Value 或 Footprint 判定
    (re.compile(r"(\bMOUNTING\s*HOLE\b|\bTOOLING\s*HOLE\b|\bTOOLINGHO\b|\bNPTH\b|\bDFT_NP\d*\b|\bMH_\d+|\bMH-)", re.IGNORECASE), "MountingHole"),
    # 3. 機構螺絲、螺帽、銅柱、散熱銅皮 (Mechanical / Hardware): 依 Description / Value / Footprint 判定
    (re.compile(r"(\bSCREW\b|\bSTANDOFF\b|\bNUT\b|DIAMETER:\s*\d+MM|EX-COPPER|COPPER_AREA|EX_COPPER|LAYER\s*PCB|AGENCY\s*(LOGO\s*)?LABEL)", re.IGNORECASE), "Mechanical"),
    # 4. 測試點、測試探針、測試 Pad (Test Point / Test Probe / Test Pad): 依 Description / Footprint / Value 判定
    (re.compile(r"(\bTEST\s*PROBE\b|\bTEST\s*PAD\b|\bTEST\s*FOR\b|\bSIM\s*TEST\b|\bTPC\d+\b|\bPROBE\b|\bDELTAL\d*\b)", re.IGNORECASE), "TestPoint"),
]

# 2. 複合前綴識別表
COMPOUND_REF_PREFIXES = [
    # 功率域被動/分離/IC
    ("PFB", ("Passive", "FerriteBead", "Filter")),
    ("PR", ("Passive", "Resistor", "Passive_Support")),
    ("PC", ("Passive", "Capacitor", "Passive_Support")),
    ("PL", ("Passive", "Inductor", "Filter")),
    ("PQ", ("Discrete", "MOSFET", "None")),
    ("PU", ("IC", "PowerIC", "Power_Source")),
    ("TJ", ("Connector", "Connector", "None")),
    ("TX", ("Discrete", "Crystal", "None")),
    ("TD", ("Discrete", "TVS", "Protection")),  # 預設 TD 多為 TVS-Array
    ("TC", ("Passive", "Capacitor", "Passive_Support")),
    ("TR", ("Passive", "Resistor", "Passive_Support")),
    ("TL", ("Passive", "Inductor", "Filter")),
    ("TQ", ("Discrete", "Transistor", "None")),
    ("TU", ("IC", "Other", "None")),
    ("TSW", ("Electromechanical", "Switch", "None")),
]

# 3. 單一常規前綴識別表
STANDARD_REF_PREFIXES = [
    ("R", ("Passive", "Resistor", "Passive_Support")),
    ("C", ("Passive", "Capacitor", "Passive_Support")),
    ("L", ("Passive", "Inductor", "Filter")),
    ("D", ("Discrete", "Diode", "None")),
    ("Q", ("Discrete", "Transistor", "None")),
    ("J", ("Connector", "Connector", "None")),
    ("P", ("Connector", "Connector", "None")),
    ("U", ("IC", "Other", "None")),
    ("SW", ("Electromechanical", "Switch", "None")),
    ("Y", ("Discrete", "Crystal", "None")),
    ("X", ("Discrete", "Crystal", "None")),
    ("F", ("Passive", "Fuse", "Protection")),
]


def _match_non_electrical(val: str, desc: str, package: str, pins_count: int) -> Optional[Tuple[str, str]]:
    """
    純依據 Description、Footprint/Package、Part Value 與引腳數綜合判斷是否為非電氣機構件或測試點。
    嚴格禁止由零件編號 (RefDes) 判定！
    """
    combined_meta = f"{val} {desc} {package}".strip()
    
    for pat, sub_cat in NON_ELECTRICAL_METADATA_PATTERNS:
        m = pat.search(combined_meta)
        if m:
            return sub_cat, f"metadata_match:{m.group(0)}"

    # 0 引腳無電氣連線且描述含 PCB / LABEL / COPPER
    if pins_count == 0 and any(k in combined_meta.upper() for k in ["COPPER", "PCB", "LABEL", "HOLE"]):
        return "Mechanical", "zero_pin_non_electrical"

    return None


def classify_single_component_heuristic(
    ref: str,
    val: str = "",
    desc: str = "",
    package: str = "",
    mfg_pn: str = "",
    pins_count: int = 0
) -> Dict[str, Any]:
    """
    根據元數據與規則啟發式推斷單一元件的四維度分類
    
    Returns:
        Dict: 包含 category, sub_category, functional_role, is_electrical, confidence, evidence
    """
    upper_ref = ref.upper()
    upper_val = val.upper()
    upper_desc = desc.upper()
    upper_pkg = package.upper()
    upper_mpn = mfg_pn.upper()
    combined_text = f"{upper_val} {upper_mpn} {upper_desc} {upper_pkg}"

    evidence: List[str] = []

    # 階段 1：機構件與測試點過濾 (Non-Electrical Filter，純依據元數據與引腳綜合判定)
    non_elec = _match_non_electrical(val=val, desc=desc, package=package, pins_count=pins_count)
    if non_elec:
        sub_cat, ev = non_elec
        logger.debug("[Classifier] Non-electrical match: %s -> sub_cat=%s (%s)", ref, sub_cat, ev)
        return {
            "category": "NonElectrical",
            "sub_category": sub_cat,
            "functional_role": "None",
            "is_electrical": False,
            "confidence": 0.99,
            "evidence": [ev]
        }

    # 階段 2：Description / Footprint / Value 關鍵字與標準前綴證據鏈分析
    # 2.1 檢查 Cadence OrCAD 標準 Description 前綴 (權重最高)
    if upper_desc.startswith("IC,") or upper_desc.startswith("DUT,"):
        # 判定 IC 之細部類型與拓撲角色
        if re.search(r"\b(PD|DRP|CONTROLLER|POWER\s*SWITCH|BUCK|BOOST|CONVERTER|REGULATOR|LDO|PMIC|POWER\s*MANAGEMENT|ECPOWER|SYNCHRONOUS|SMART\s*PR)\b", combined_text) or upper_ref.startswith("PU"):
            sub_cat = "PowerIC"
            role = "Power_Source"
        elif re.search(r"\b(LEVEL\s*SHIFTER|LEVEL\s*TRANSLATOR|BIDIRECTIONAL\s*LEVEL)\b", combined_text):
            sub_cat = "LevelShifter"
            role = "Level_Shifter"
        elif re.search(r"\b(MCU|MICROCONTROLLER|STM32|ESP32|CPU|SOC|PROCESSOR|BRIDGE|INTEL)\b", combined_text):
            sub_cat = "Microcontroller"
            role = "Bus_Master"
        elif re.search(r"\b(SERIAL\s*FLASH|FLASH\s*M|EEPROM|W25Q|SRAM|DRAM)\b", combined_text):
            sub_cat = "Memory"
            role = "Bus_Slave"
        elif re.search(r"\b(REDRIVER|TRANSCEIVER|PHY|SIGNAL\s*CO|SIGNAL\s*CONDITIONER|TUSB)\b", combined_text):
            sub_cat = "InterfaceIC"
            role = "None"
        else:
            sub_cat = "Other"
            role = "None"
        evidence.append("desc_prefix:IC")
        return {
            "category": "IC",
            "sub_category": sub_cat,
            "functional_role": role,
            "is_electrical": True,
            "confidence": 0.98,
            "evidence": evidence
        }

    if upper_desc.startswith("CONN,"):
        evidence.append("desc_prefix:CONN")
        return {
            "category": "Connector",
            "sub_category": "Connector",
            "functional_role": "None",
            "is_electrical": True,
            "confidence": 0.98,
            "evidence": evidence
        }

    if upper_desc.startswith("RES,"):
        evidence.append("desc_prefix:RES")
        return {
            "category": "Passive",
            "sub_category": "Resistor",
            "functional_role": "Passive_Support",
            "is_electrical": True,
            "confidence": 0.98,
            "evidence": evidence
        }

    if upper_desc.startswith("CAP,"):
        evidence.append("desc_prefix:CAP")
        return {
            "category": "Passive",
            "sub_category": "Capacitor",
            "functional_role": "Passive_Support",
            "is_electrical": True,
            "confidence": 0.98,
            "evidence": evidence
        }

    if upper_desc.startswith("FB,"):
        evidence.append("desc_prefix:FB")
        return {
            "category": "Passive",
            "sub_category": "FerriteBead",
            "functional_role": "Filter",
            "is_electrical": True,
            "confidence": 0.98,
            "evidence": evidence
        }

    if upper_desc.startswith("XTAL,"):
        evidence.append("desc_prefix:XTAL")
        return {
            "category": "Discrete",
            "sub_category": "Crystal",
            "functional_role": "None",
            "is_electrical": True,
            "confidence": 0.98,
            "evidence": evidence
        }

    if upper_desc.startswith(("MOS N,", "MOS P,", "MOS,")):
        evidence.append("desc_prefix:MOS")
        return {
            "category": "Discrete",
            "sub_category": "MOSFET",
            "functional_role": "None",
            "is_electrical": True,
            "confidence": 0.98,
            "evidence": evidence
        }

    if upper_desc.startswith("CHIP INDUCTOR") or upper_desc.startswith("INDUCTOR,"):
        evidence.append("desc_prefix:INDUCTOR")
        return {
            "category": "Passive",
            "sub_category": "Inductor",
            "functional_role": "Filter",
            "is_electrical": True,
            "confidence": 0.98,
            "evidence": evidence
        }

    # 2.2 全文關鍵字正則比對 (若無標準 Description 前綴)
    # TVS / ESD 保護陣列
    if re.search(r"\b(TVS|ESD|TRANSIENT\s+VOLTAGE|TVS-ARRAY)\b", combined_text):
        evidence.append("keyword:TVS/ESD")
        return {
            "category": "Discrete",
            "sub_category": "TVS",
            "functional_role": "Protection",
            "is_electrical": True,
            "confidence": 0.95,
            "evidence": evidence
        }

    # 磁珠 (Ferrite Bead)
    if re.search(r"\b(FERRITE|CHIP\s+BEAD|FB)\b", combined_text):
        evidence.append("keyword:FerriteBead")
        return {
            "category": "Passive",
            "sub_category": "FerriteBead",
            "functional_role": "Filter",
            "is_electrical": True,
            "confidence": 0.95,
            "evidence": evidence
        }

    # 晶體振盪器 (Crystal / Oscillator)
    if re.search(r"\b(XTAL|CRYSTAL|OSCILLATOR|RESONATOR)\b", combined_text) or "MHZ" in upper_val:
        evidence.append("keyword:Crystal")
        return {
            "category": "Discrete",
            "sub_category": "Crystal",
            "functional_role": "None",
            "is_electrical": True,
            "confidence": 0.95,
            "evidence": evidence
        }

    # MOSFET / 電晶體 (先於電阻檢查，避免 DCR / Ron Ohm 誤殺)
    if (re.search(r"\b(MOSFET|MOS\s+[NP]|TRANSISTOR|BJT)\b", combined_text)
            or upper_ref.startswith(("PQ", "TQ"))):
        evidence.append("pattern:MOSFET")
        return {
            "category": "Discrete",
            "sub_category": "MOSFET",
            "functional_role": "None",
            "is_electrical": True,
            "confidence": 0.92,
            "evidence": evidence
        }

    # 電感 (先於電阻檢查，避免 DCR Ohm 誤殺)
    if (re.search(r"\b(INDUCTOR|CHIP\s+INDUCTOR|COIL|CHOKE)\b", combined_text)
            or re.search(r"\b\d+(\.\d+)?(UH|NH|MH)\b", upper_val)
            or upper_ref.startswith(("PL", "TL"))):
        evidence.append("pattern:Inductor")
        return {
            "category": "Passive",
            "sub_category": "Inductor",
            "functional_role": "Filter",
            "is_electrical": True,
            "confidence": 0.95,
            "evidence": evidence
        }

    # 連接器 (Connector)
    if (re.search(r"\b(CONN|CONNECTOR|HEADER|RECEPTACLE|PLUG|JACK|SOCKET)\b", combined_text)
            or "USBC" in upper_pkg or "BTB" in upper_pkg or upper_ref.startswith("TJ")):
        evidence.append("keyword:Connector")
        return {
            "category": "Connector",
            "sub_category": "Connector",
            "functional_role": "None",
            "is_electrical": True,
            "confidence": 0.95,
            "evidence": evidence
        }

    # 電源類 IC (Power Management / Buck / Boost / LDO / Protection IC)
    if (re.search(r"\b(BUCK|BOOST|CONVERTER|REGULATOR|LDO|PMIC|POWER\s+MANAGEMENT|ECPOWER|SYNCHRONOUS|SMART\s+PR)\b", combined_text)
            or upper_ref.startswith("PU")):
        evidence.append("keyword:PowerIC")
        return {
            "category": "IC",
            "sub_category": "PowerIC",
            "functional_role": "Power_Source",
            "is_electrical": True,
            "confidence": 0.92,
            "evidence": evidence
        }

    # 電平轉換 IC (Level Shifter)
    if re.search(r"\b(LEVEL\s+SHIFTER|LEVEL\s+TRANSLATOR|BIDIRECTIONAL\s+LEVEL)\b", combined_text):
        evidence.append("keyword:LevelShifter")
        return {
            "category": "IC",
            "sub_category": "LevelShifter",
            "functional_role": "Level_Shifter",
            "is_electrical": True,
            "confidence": 0.92,
            "evidence": evidence
        }

    # 主控與處理器 (Microcontroller / CPU / SoC / Bridge)
    if re.search(r"\b(MCU|MICROCONTROLLER|STM32|ESP32|CPU|SOC|PROCESSOR|DUT.*BRIDGE|JUNE\s+BRIDGE)\b", combined_text):
        evidence.append("keyword:BusMaster")
        return {
            "category": "IC",
            "sub_category": "Microcontroller",
            "functional_role": "Bus_Master",
            "is_electrical": True,
            "confidence": 0.92,
            "evidence": evidence
        }

    # 儲存元件 (Flash / EEPROM)
    if re.search(r"\b(SERIAL\s+FLASH|FLASH\s+M|EEPROM|W25Q|SRAM|DRAM)\b", combined_text):
        evidence.append("keyword:Memory")
        return {
            "category": "IC",
            "sub_category": "Memory",
            "functional_role": "Bus_Slave",
            "is_electrical": True,
            "confidence": 0.90,
            "evidence": evidence
        }

    # 介面訊號調節 IC (USB Redriver / Transceiver / Interface IC)
    if re.search(r"\b(REDRIVER|TRANSCEIVER|PHY|SIGNAL\s+CO|SIGNAL\s+CONDITIONER|TUSB)\b", combined_text):
        evidence.append("keyword:InterfaceIC")
        return {
            "category": "IC",
            "sub_category": "InterfaceIC",
            "functional_role": "None",
            "is_electrical": True,
            "confidence": 0.90,
            "evidence": evidence
        }

    # 電容 (Capacitor)
    if (re.search(r"\b(CAP|CAPACITOR|MLCC)\b", combined_text)
            or re.match(r"^[TC]?C\d{4}", upper_pkg)
            or re.search(r"\b\d+(\.\d+)?(UF|NF|PF)\b", upper_val)
            or upper_ref.startswith(("C", "TC", "PC"))):
        evidence.append("pattern:Capacitor")
        return {
            "category": "Passive",
            "sub_category": "Capacitor",
            "functional_role": "Passive_Support",
            "is_electrical": True,
            "confidence": 0.95,
            "evidence": evidence
        }

    # 電阻 (Resistor)
    if (re.search(r"\b(RES|RESISTOR|OHM)\b", combined_text)
            or re.match(r"^[TR]?R\d{4}", upper_pkg)
            or re.search(r"\b\d+(\.\d+)?[KM]?\s*(OHM|%|_1%|_5%)\b", upper_val)
            or upper_ref.startswith(("R", "TR", "PR"))):
        evidence.append("pattern:Resistor")
        return {
            "category": "Passive",
            "sub_category": "Resistor",
            "functional_role": "Passive_Support",
            "is_electrical": True,
            "confidence": 0.95,
            "evidence": evidence
        }

    # 電感 (Inductor)
    if (re.search(r"\b(INDUCTOR|CHIP\s+INDUCTOR|COIL|CHOKE)\b", combined_text)
            or re.search(r"\b\d+(\.\d+)?(UH|NH|MH)\b", upper_val)
            or upper_ref.startswith(("L", "TL", "PL"))):
        evidence.append("pattern:Inductor")
        return {
            "category": "Passive",
            "sub_category": "Inductor",
            "functional_role": "Filter",
            "is_electrical": True,
            "confidence": 0.95,
            "evidence": evidence
        }

    # 二極體 (Diode)
    if (re.search(r"\b(DIODE|SCHOTTKY|ZENER|RECTIFIER|LED)\b", combined_text)
            or upper_ref.startswith(("D", "TD"))):
        evidence.append("pattern:Diode")
        return {
            "category": "Discrete",
            "sub_category": "Diode",
            "functional_role": "None",
            "is_electrical": True,
            "confidence": 0.90,
            "evidence": evidence
        }

    # MOSFET / 電晶體 (Transistor)
    if (re.search(r"\b(MOSFET|MOS\s+[NP]|TRANSISTOR|BJT)\b", combined_text)
            or upper_ref.startswith(("Q", "TQ", "PQ"))):
        evidence.append("pattern:MOSFET")
        return {
            "category": "Discrete",
            "sub_category": "MOSFET",
            "functional_role": "None",
            "is_electrical": True,
            "confidence": 0.90,
            "evidence": evidence
        }

    # 開關 (Switch)
    if (re.search(r"\b(SWITCH|PUSH\s+BUTTON|TACT)\b", combined_text)
            or upper_ref.startswith(("SW", "TSW"))):
        evidence.append("pattern:Switch")
        return {
            "category": "Electromechanical",
            "sub_category": "Switch",
            "functional_role": "None",
            "is_electrical": True,
            "confidence": 0.90,
            "evidence": evidence
        }

    # 階段 3：複合與常規 RefDes 前綴安全降級推斷
    for prefix, (cat, sub_cat, role) in COMPOUND_REF_PREFIXES:
        if upper_ref.startswith(prefix):
            evidence.append(f"compound_prefix:{prefix}")
            return {
                "category": cat,
                "sub_category": sub_cat,
                "functional_role": role,
                "is_electrical": True,
                "confidence": 0.85,
                "evidence": evidence
            }

    for prefix, (cat, sub_cat, role) in STANDARD_REF_PREFIXES:
        if upper_ref.startswith(prefix):
            evidence.append(f"standard_prefix:{prefix}")
            return {
                "category": cat,
                "sub_category": sub_cat,
                "functional_role": role,
                "is_electrical": True,
                "confidence": 0.75,
                "evidence": evidence
            }

    # 預設未知元件 (嚴守鐵律：無證據不可下結論，不預設為 IC)
    evidence.append("no_evidence_fallback")
    return {
        "category": "IC" if pins_count >= 8 else "Discrete" if pins_count >= 3 else "Passive" if pins_count == 2 else "NonElectrical",
        "sub_category": "Other",
        "functional_role": "None",
        "is_electrical": pins_count > 0,
        "confidence": 0.40,
        "evidence": evidence
    }


def classify_components_batch(
    components_raw: Dict[str, Dict[str, Any]],
    enable_llm_fallback: bool = True,
    task_id: Optional[str] = None
) -> Dict[str, Dict[str, Any]]:
    """
    批次分類所有元件：
    1. 執行規則推斷與非電氣件白名單過濾
    2. 針對信心度低於 0.6 且具電氣引腳的模糊元件，整批彙整呼叫 LiteLLM 結構化推斷
    3. 若 LLM 離線、逾時或未配置 Key，優雅降級並記錄警告日誌
    """
    from backend.app.core.task_logger import get_task_logger
    t_logger = get_task_logger(task_id) if task_id else None

    classified: Dict[str, Dict[str, Any]] = {}
    ambiguous_items: List[Dict[str, Any]] = []

    for ref, c in components_raw.items():
        val = c.get("part_value", "")
        desc = c.get("description", "")
        pkg = c.get("package", "")
        mfg_pn = c.get("mfg_pn", "")
        pins = c.get("pins", [])
        pins_count = len(pins)

        res = classify_single_component_heuristic(
            ref=ref,
            val=val,
            desc=desc,
            package=pkg,
            mfg_pn=mfg_pn,
            pins_count=pins_count
        )

        classified[ref] = {**c, **res}

        # 若信心度過低且為多引腳潛在主動元件，列入批次清單
        if res["confidence"] < 0.6 and res["is_electrical"]:
            ambiguous_items.append({
                "ref_des": ref,
                "part_value": val,
                "description": desc,
                "package": pkg,
                "mfg_pn": mfg_pn,
                "pins_count": pins_count
            })

    # 若需要且有模糊元件，嘗試批次呼叫 LiteLLM
    if enable_llm_fallback and ambiguous_items:
        logger.info("[Classifier] Found %d ambiguous components, attempting batch LLM categorization...", len(ambiguous_items))
        if t_logger:
            t_logger.warning(
                "PARSE_AND_GRAPH",
                "LLM",
                f"發現 {len(ambiguous_items)} 個模糊元件屬性無法確定，發起批次 LLM 語意查詢",
                details={"ambiguous_components": [i["ref_des"] for i in ambiguous_items]}
            )
        try:
            from backend.app.engine.rules.llm import call_litellm_completion
            
            prompt = (
                "You are an expert electronics hardware engineer. Categorize the following electronic components into standard schemas.\n"
                "Return ONLY a valid JSON list of objects matching this schema:\n"
                "[\n"
                "  {\n"
                "    \"ref_des\": string,\n"
                "    \"category\": \"IC\" | \"Passive\" | \"Discrete\" | \"Connector\" | \"Electromechanical\" | \"NonElectrical\",\n"
                "    \"sub_category\": string (e.g. Capacitor, Resistor, Inductor, TVS, MOSFET, Crystal, PowerIC, LevelShifter, Microcontroller, Memory, etc.),\n"
                "    \"functional_role\": \"Bus_Master\" | \"Bus_Slave\" | \"Power_Source\" | \"Power_Sink\" | \"Level_Shifter\" | \"Protection\" | \"Filter\" | \"None\",\n"
                "    \"is_electrical\": boolean\n"
                "  }\n"
                "]\n"
                "Strict rule: No evidence, no assertion. If unknown, use functional_role 'None'.\n\n"
                f"Components to categorize:\n{json.dumps(ambiguous_items, ensure_ascii=False, indent=2)}"
            )

            if t_logger:
                t_logger.debug(
                    "PARSE_AND_GRAPH",
                    "LLM",
                    f"向 LLM 發送提示詞進行元件語意識別 ({len(ambiguous_items)} 個元件)",
                    details={"prompt": prompt, "model": "openai/qwen"}
                )

            response = call_litellm_completion(prompt=prompt, timeout=15.0)
            if response and "choices" in response:
                content = response["choices"][0]["message"]["content"]
                # 提取 JSON 區塊
                json_match = re.search(r"\[\s*\{.*\}\s*\]", content, re.DOTALL)
                if json_match:
                    items = json.loads(json_match.group(0))
                    for item in items:
                        r = item.get("ref_des")
                        if r in classified:
                            classified[r]["category"] = item.get("category", classified[r]["category"])
                            classified[r]["sub_category"] = item.get("sub_category", classified[r]["sub_category"])
                            classified[r]["functional_role"] = item.get("functional_role", classified[r]["functional_role"])
                            classified[r]["is_electrical"] = bool(item.get("is_electrical", classified[r]["is_electrical"]))
                            classified[r]["confidence"] = 0.85
                            classified[r]["evidence"].append("llm_batch_inference")
                    logger.info("[Classifier] Successfully resolved %d ambiguous components via batch LLM.", len(items))
                    if t_logger:
                        t_logger.debug(
                            "PARSE_AND_GRAPH",
                            "LLM",
                            f"LLM 批次分類回覆成功，解析出 {len(items)} 個元件結構化類別",
                            details={"classified_items": items}
                        )
        except Exception as e:
            logger.warning("[Classifier] Batch LLM inference unavailable or failed (%s). Gracefully falling back to heuristic results.", e)
            if t_logger:
                t_logger.warning(
                    "PARSE_AND_GRAPH",
                    "LLM",
                    f"LLM 批次分類連線失敗或逾時 ({str(e)[:60]})，優雅降級為啟發式結果",
                    details={"error": str(e)}
                )
    elif t_logger and not ambiguous_items:
        t_logger.debug(
            "PARSE_AND_GRAPH",
            "PARSER",
            f"所有元件均已透過啟發式規則完全識別 (共 {len(classified)} 個)，無需呼叫 LLM 進行模糊分類"
        )

    # 統計日誌
    cat_counts: Dict[str, int] = {}
    for c in classified.values():
        cat = c["category"]
        cat_counts[cat] = cat_counts.get(cat, 0) + 1
    logger.info("[Classifier] Component classification finished: Total=%d, Categories=%s", len(classified), cat_counts)

    return classified
