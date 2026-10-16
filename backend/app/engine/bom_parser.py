"""
BOM 上件狀態解析與多 Config 驗證模組 (BOM Mount Status Parser & Config Validator)

依據 XML 零件屬性 BOM 欄位判定元件於樣品 (Sample) 或量產 (MP) 階段之上件狀態，
並支援多組 BOM Config (>1) 的完整性檢查與陣列正規化。
"""

import logging
from typing import Dict, List, Any, Set, Tuple

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
