"""
BOM 上件狀態解析與多 Config 驗證模組 (BOM Mount Status Parser & Config Validator)

依據 XML 零件屬性 BOM 欄位判定元件於樣品 (Sample) 或量產 (MP) 階段之上件狀態，
並支援多組 BOM Config (>1) 的完整性檢查與陣列正規化。
"""

import logging
from typing import Dict, List, Any, Set, Tuple, Optional

logger = logging.getLogger("designshield.bom_parser")

# 規範允許之 BOM 語法白名單
ALLOWED_BOM_TOKENS: Set[str] = {
    "I",      # 永遠上件
    "NOBOM",  # 永遠上件 (測點/預留測點)
    "NI",     # 永遠不上件
    "X",      # 永遠不上件
    "PROTO",  # 樣品上件，量產不上件
    "P",      # 樣品上件，量產不上件
    "MP",     # 量產上件，樣品不上件
    "M",      # 量產上件，樣品不上件
}

# 上件與不上件判定 Token 集合
MOUNTED_BOM_TOKENS: Set[str] = {"I", "P", "M", "NOBOM"}
UNMOUNTED_BOM_TOKENS: Set[str] = {"X", "NI"}


def normalize_bom_token(bom_val: str) -> str:
    """
    將 BOM 標記正規化為標準縮寫白名單 ('I', 'X', 'P', 'M', 'NOBOM')。
    
    對應規則:
      - 'I' -> 'I' (永遠上件)
      - 'NOBOM' -> 'NOBOM' (無 BOM / 預設上件)
      - 'NI', 'X' -> 'X' (永遠不上件)
      - 'PROTO', 'P' -> 'P' (樣品上件，量產不上件)
      - 'MP', 'M' -> 'M' (量產上件，樣品不上件)
    """
    if not bom_val or not isinstance(bom_val, str):
        return "NOBOM"
    token = bom_val.strip().upper()
    if token in {"I", "NOBOM"}:
        return token
    if token in {"NI", "X"}:
        return "X"
    if token in {"PROTO", "P"}:
        return "P"
    if token in {"MP", "M"}:
        return "M"
    return token


def is_component_mounted(bom_val: str, is_mp_mode: bool) -> bool:
    """
    依據單一 BOM 代碼與當前 MP Mode 狀態判定元件是否應當上件。
    
    Args:
        bom_val: 單一 BOM 標記 (如 'I', 'NI', 'P', 'MP', 'NOBOM')
        is_mp_mode: 是否處於量產模式 (True: MP Mode, False: 樣品/Sample Mode)
        
    Returns:
        bool: True 代表上件，False 代表不上件
        
    Raises:
        ValueError: 當 bom_val 為空或不符合白名單時拋出
    """
    if not bom_val or not isinstance(bom_val, str):
        raise ValueError("BOM 標記不可為空")
        
    token = bom_val.strip().upper()
    if token not in ALLOWED_BOM_TOKENS:
        raise ValueError(f"不合法的 BOM 標記 '{token}'，僅允許: {', '.join(sorted(ALLOWED_BOM_TOKENS))}")
        
    canonical = normalize_bom_token(token)
    if canonical in {"I", "NOBOM"}:
        return True
    if canonical == "X":
        return False
    if canonical == "P":
        return not is_mp_mode
    if canonical == "M":
        return is_mp_mode
        
    return False


def validate_and_extract_bom_configs(components: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    掃描並校驗所有元件之 BOM 屬性，提取全域 Config 數量並進行陣列展開。
    
    規則：
    1. 元件必須具備 BOM 屬性且不可為空字串。
    2. BOM 值可以逗號分隔支援多 Config (例如: "I,X,P,I,I")。
    3. 全域 Config 數為 N (取最大逗號切分數量)。
    4. 每個元件的 Config 數量僅能為 1 或 N；若出現其他數量則立即報錯。
    5. 若數量為 1，代表該元件在所有 N 組 Config 中設定相同。
    
    Args:
        components: 元件字典 (key 為 ref_des, value 為包含 user_props 的屬性字典)
        
    Returns:
        Dict: 包含:
            - config_count (int): Config 總數
            - config_names (List[str]): Config 名稱清單 (如 ["Config 1", "Config 2"])
            - is_multi_config (bool): 是否為多組 Config (>1)
            - component_bom_tokens (Dict[str, List[str]]): 每個元件對應至 N 組 Config 的正規化 token 清單
            - raw_bom_map (Dict[str, str]): 每個元件的原始 BOM 字串
            
    Raises:
        ValueError: 包含違規元件與詳細錯誤說明
    """
    if not components:
        return {
            "config_count": 1,
            "config_names": ["Config 1"],
            "is_multi_config": False,
            "component_bom_tokens": {},
            "raw_bom_map": {},
        }

    raw_bom_map: Dict[str, str] = {}
    comp_tokens: Dict[str, List[str]] = {}

    for ref_des, c_info in components.items():
        user_props = c_info.get("user_props", {})
        bom_val = user_props.get("BOM")
        if bom_val is None:
            bom_val = c_info.get("BOM")
            
        if bom_val is None or not str(bom_val).strip():
            raise ValueError(
                f"元件 {ref_des} 缺少 BOM 屬性或為空字串，線路圖規範所有元件皆須標記 BOM 上件狀態"
            )

        bom_str = str(bom_val).strip()
        raw_bom_map[ref_des] = bom_str

        # 逗號切分與空白防護
        parts = [p.strip() for p in bom_str.split(",")]
        if any(len(p) == 0 for p in parts):
            raise ValueError(
                f"元件 {ref_des} 的 BOM 屬性包含空白項目 ('{bom_str}')，請修正線路圖設定"
            )

        tokens = [p.upper() for p in parts]
        for t in tokens:
            if t not in ALLOWED_BOM_TOKENS:
                raise ValueError(
                    f"元件 {ref_des} 的 BOM 屬性包含不合法的狀態標記 '{t}' (完整設定: '{bom_str}')，僅允許: {', '.join(sorted(ALLOWED_BOM_TOKENS))}"
                )

        comp_tokens[ref_des] = tokens

    # 計算全域最大 Config 數量 N
    n_configs = max(len(toks) for toks in comp_tokens.values())
    if n_configs == 0:
        n_configs = 1

    # 驗證每個元件的 token 數量是否為 1 或 N
    for ref_des, toks in comp_tokens.items():
        tok_len = len(toks)
        if tok_len != 1 and tok_len != n_configs:
            raise ValueError(
                f"BOM Config 數量不合法：全域最高偵測為 {n_configs} 組 Config，但元件 {ref_des} 的 BOM 欄位具有 {tok_len} 組設定 ('{raw_bom_map[ref_des]}')，僅允許 1 或 {n_configs} 組"
            )

    # 正規化元件 tokens 為長度 N 的標準縮寫清單 ('I', 'X', 'P', 'M', 'NOBOM')
    normalized_tokens: Dict[str, List[str]] = {}
    for ref_des, toks in comp_tokens.items():
        canonical_toks = [normalize_bom_token(t) for t in toks]
        if len(canonical_toks) == n_configs:
            normalized_tokens[ref_des] = canonical_toks
        else:
            # 長度為 1 擴展至全域 N 組
            normalized_tokens[ref_des] = canonical_toks * n_configs

    config_names = [f"Config {i + 1}" for i in range(n_configs)]

    logger.info(
        "BOM Config 校驗通過: 共 %d 組 Config (%s), 涵蓋 %d 顆元件",
        n_configs,
        ", ".join(config_names),
        len(normalized_tokens)
    )

    return {
        "config_count": n_configs,
        "config_names": config_names,
        "is_multi_config": n_configs > 1,
        "component_bom_tokens": normalized_tokens,
        "raw_bom_map": raw_bom_map,
    }


def apply_bomslot_replacements(
    components: Dict[str, Dict[str, Any]],
    bom_config_info: Dict[str, Any],
    task_id: Optional[str] = None
) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Any]]:
    """
    執行 BOMSLOT 替代料判定、衝突檢驗、代碼繼承與屬性置換流程。

    業務規則：
    1. 篩選：零件 ref_des 包含 '=' 且 user_props 或頂層屬性之 function 欄位（不區分大小寫）等於 'BOMSLOT'。
    2. 基準元件：取 '=' 前之字串 (例如 'J41=Z2' -> 'J41')。
    3. 依各 Config 逐一比對：
       - 若在某 Config 下替代零件上件 (I, P, M, NOBOM) 且基準零件不上件 (X, NI)，則將替代料屬性標記為置換。
       - 基準零件在該 Config 的 BOM 上件代碼同步繼承替代零件的上件代碼。
    4. 衝突與錯誤檢驗（不中斷遍歷，累積所有錯誤後再統一報錯）：
       - 基準零件不存在於 components 中。
       - 同一 Config 下基準零件與替代零件同時標記為上件。
       - 同一 Config 下同一個基準零件有多個 BOMSLOT 同時標記為上件。
    5. 若有錯誤，拋出 ValueError 並輸出詳細清單；
       若無錯誤，將原始 BOMSLOT 元件從 components 字典與 bom_config_info 中移除，避免產生未連線的孤立節點。

    Args:
        components: 元件字典 (key 為 ref_des, value 為元件屬性)
        bom_config_info: validate_and_extract_bom_configs 回傳的 BOM 配置字典
        task_id: 可選的任務 ID (用於結構化日誌記錄)

    Returns:
        Tuple[Dict[str, Dict[str, Any]], Dict[str, Any]]:
            - 更新後的 components 字典 (已剔除 BOMSLOT 零件)
            - 更新後的 bom_config_info (已更新 token 與注入 bomslot_overrides)

    Raises:
        ValueError: 當存在任何 BOMSLOT 衝突或基準零件缺失時拋出
    """
    from backend.app.core.task_logger import get_task_logger
    t_logger = get_task_logger(task_id) if task_id else None

    # 1. 篩選 BOMSLOT 元件
    slot_components: Dict[str, Dict[str, Any]] = {}
    for ref_des, c_info in components.items():
        if "=" not in ref_des:
            continue

        func_val = None
        user_props = c_info.get("user_props", {})
        if isinstance(user_props, dict):
            for k, v in user_props.items():
                if k.strip().lower() == "function":
                    func_val = str(v).strip()
                    break
        if func_val is None:
            for k in ("function", "Function", "FUNCTION"):
                if k in c_info:
                    func_val = str(c_info[k]).strip()
                    break

        if func_val and func_val.upper() == "BOMSLOT":
            slot_components[ref_des] = c_info

    if not slot_components:
        return components, bom_config_info

    n_configs = bom_config_info.get("config_count", 1)
    comp_tokens = bom_config_info.get("component_bom_tokens", {})
    raw_bom_map = bom_config_info.get("raw_bom_map", {})

    errors: List[str] = []
    # bomslot_overrides 結構: {config_index: {target_ref: slot_comp_info}}
    bomslot_overrides: Dict[int, Dict[str, Dict[str, Any]]] = {
        i: {} for i in range(n_configs)
    }

    # 2. 檢查基準元件存在性
    for slot_ref in slot_components:
        target_ref = slot_ref.split("=")[0].strip()
        if target_ref not in components:
            errors.append(
                f"BOMSLOT 錯誤：零件 '{slot_ref}' 指定之基準零件 '{target_ref}' 不存在於線路圖元件清單中。"
            )

    # 3. 依 Config 逐一比對上件狀態與衝突
    for cfg_idx in range(n_configs):
        cfg_name = f"Config {cfg_idx + 1}"
        # 收集該 Config 下所有標記為上件的 BOMSLOT：target_ref -> list of (slot_ref, slot_token, slot_info)
        mounted_slots_by_target: Dict[str, List[Tuple[str, str, Dict[str, Any]]]] = {}

        for slot_ref, slot_info in slot_components.items():
            target_ref = slot_ref.split("=")[0].strip()
            slot_toks = comp_tokens.get(slot_ref, [])
            slot_tok = slot_toks[cfg_idx] if cfg_idx < len(slot_toks) else "NOBOM"

            if slot_tok in MOUNTED_BOM_TOKENS:
                mounted_slots_by_target.setdefault(target_ref, []).append(
                    (slot_ref, slot_tok, slot_info)
                )

        # 針對有上件替代料的各基準零件進行比對
        for target_ref, slots in mounted_slots_by_target.items():
            # 若基準元件不存在，前面已記錄錯誤，略過後續比對避免 KeyError
            if target_ref not in components:
                continue

            target_toks = comp_tokens.get(target_ref, [])
            target_tok = target_toks[cfg_idx] if cfg_idx < len(target_toks) else "NOBOM"
            is_target_mounted = target_tok in MOUNTED_BOM_TOKENS

            # 衝突 A：基準零件與替代零件同時上件
            if is_target_mounted:
                for slot_ref, slot_tok, _ in slots:
                    errors.append(
                        f"BOMSLOT 衝突：基準零件 '{target_ref}' 與替代零件 '{slot_ref}' 在 {cfg_name} 同時標記為上件 ({target_ref}='{target_tok}', {slot_ref}='{slot_tok}')。"
                    )

            # 衝突 B：多個 BOMSLOT 同時競爭上件
            if len(slots) > 1:
                slots_str = ", ".join([f"'{s[0]}'" for s in slots])
                errors.append(
                    f"BOMSLOT 衝突：基準零件 '{target_ref}' 在 {cfg_name} 同時有多個 BOMSLOT 標記為上件 ({slots_str})。"
                )

            # 合法置換：基準零件不上件，且剛好只有一個替代零件上件
            if not is_target_mounted and len(slots) == 1:
                slot_ref, slot_tok, slot_info = slots[0]
                bomslot_overrides[cfg_idx][target_ref] = slot_info

    # 4. 累積錯誤處理
    if errors:
        error_msg = f"BOMSLOT 置換校驗失敗，發現 {len(errors)} 個衝突或錯誤：\n" + "\n".join(f"- {e}" for e in errors)
        logger.error(error_msg)
        if t_logger:
            t_logger.error(
                "PARSE_AND_GRAPH",
                "BOMSLOT",
                f"BOMSLOT 置換校驗失敗，發現 {len(errors)} 個衝突或錯誤",
                details={"errors": errors}
            )
        raise ValueError(error_msg)

    # 5. 若無錯誤，套用置換、代碼繼承與移除 BOMSLOT 原始元件
    # 代碼繼承：target_ref 繼承 slot 的 BOM Token
    for cfg_idx, overrides in bomslot_overrides.items():
        for target_ref, slot_info in overrides.items():
            slot_ref = slot_info.get("ref_des")
            if slot_ref and slot_ref in comp_tokens:
                slot_tok = comp_tokens[slot_ref][cfg_idx]
                comp_tokens[target_ref][cfg_idx] = slot_tok

    bom_config_info["bomslot_overrides"] = bomslot_overrides

    # 自 components 與 bom_config_info 中完全剔除原始 BOMSLOT 元件
    for slot_ref in slot_components:
        components.pop(slot_ref, None)
        comp_tokens.pop(slot_ref, None)
        raw_bom_map.pop(slot_ref, None)

    logger.info(
        "BOMSLOT 置換完成: 移除 %d 個 BOMSLOT 替代元件，涵蓋 %d 組 Config 之置換對應",
        len(slot_components),
        n_configs
    )
    if t_logger:
        t_logger.info(
            "PARSE_AND_GRAPH",
            "BOMSLOT",
            f"BOMSLOT 置換完成: 移除 {len(slot_components)} 個替代元件，置換設定已載入",
            details={
                "slot_components_removed": list(slot_components.keys()),
                "configs_count": n_configs
            }
        )

    return components, bom_config_info
