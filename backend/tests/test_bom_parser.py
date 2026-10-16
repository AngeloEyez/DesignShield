"""
BOM 上件狀態解析器與多 Config 驗證單元測試 (BOM Parser Unit Tests)
"""

import pytest
from backend.app.engine.bom_parser import (
    is_component_mounted,
    normalize_bom_token,
    validate_and_extract_bom_configs,
    ALLOWED_BOM_TOKENS,
)


def test_normalize_bom_token():
    """測試 normalize_bom_token 將各種代碼正規化為標準縮寫"""
    assert normalize_bom_token("I") == "I"
    assert normalize_bom_token("i") == "I"
    assert normalize_bom_token("NOBOM") == "NOBOM"
    assert normalize_bom_token("nobom") == "NOBOM"
    assert normalize_bom_token("") == "NOBOM"
    assert normalize_bom_token(None) == "NOBOM"  # type: ignore

    # 永遠不上件 (NI, X) -> X
    assert normalize_bom_token("NI") == "X"
    assert normalize_bom_token("ni") == "X"
    assert normalize_bom_token("X") == "X"
    assert normalize_bom_token("x") == "X"

    # 樣品上件 (PROTO, P) -> P
    assert normalize_bom_token("PROTO") == "P"
    assert normalize_bom_token("proto") == "P"
    assert normalize_bom_token("P") == "P"
    assert normalize_bom_token("p") == "P"

    # 量產上件 (MP, M) -> M
    assert normalize_bom_token("MP") == "M"
    assert normalize_bom_token("mp") == "M"
    assert normalize_bom_token("M") == "M"
    assert normalize_bom_token("m") == "M"


def test_is_component_mounted_allowed_tokens():
    """測試所有合法 BOM 代碼在樣品 (Sample) 與量產 (MP) 模式下的判定"""
    # 永遠上件
    assert is_component_mounted("I", is_mp_mode=False) is True
    assert is_component_mounted("I", is_mp_mode=True) is True
    assert is_component_mounted("NOBOM", is_mp_mode=False) is True
    assert is_component_mounted("nobom", is_mp_mode=True) is True

    # 永遠不上件
    assert is_component_mounted("NI", is_mp_mode=False) is False
    assert is_component_mounted("ni", is_mp_mode=True) is False
    assert is_component_mounted("X", is_mp_mode=False) is False
    assert is_component_mounted("x", is_mp_mode=True) is False

    # 樣品上件，量產不上件 (PROTO / P)
    assert is_component_mounted("PROTO", is_mp_mode=False) is True
    assert is_component_mounted("proto", is_mp_mode=True) is False
    assert is_component_mounted("P", is_mp_mode=False) is True
    assert is_component_mounted("p", is_mp_mode=True) is False

    # 量產上件，樣品不上件 (MP / M)
    assert is_component_mounted("MP", is_mp_mode=False) is False
    assert is_component_mounted("mp", is_mp_mode=True) is True
    assert is_component_mounted("M", is_mp_mode=False) is False
    assert is_component_mounted("m", is_mp_mode=True) is True


def test_is_component_mounted_invalid_tokens():
    """測試非白名單值拋出 ValueError"""
    with pytest.raises(ValueError, match="不合法的 BOM 標記"):
        is_component_mounted("UNKNOWN", is_mp_mode=False)

    with pytest.raises(ValueError, match="BOM 標記不可為空"):
        is_component_mounted("", is_mp_mode=False)

    with pytest.raises(ValueError, match="BOM 標記不可為空"):
        is_component_mounted(None, is_mp_mode=False)  # type: ignore


def test_validate_and_extract_bom_configs_single():
    """測試單一 Config 之提取與陣列正規化"""
    components = {
        "R1": {"user_props": {"BOM": "I"}},
        "R2": {"user_props": {"BOM": "P"}},
        "R3": {"user_props": {"BOM": "X"}},
        "TP1": {"user_props": {"BOM": "NOBOM"}},
    }
    res = validate_and_extract_bom_configs(components)
    assert res["config_count"] == 1
    assert res["config_names"] == ["Config 1"]
    assert res["is_multi_config"] is False
    assert res["component_bom_tokens"]["R1"] == ["I"]
    assert res["component_bom_tokens"]["R2"] == ["P"]
    assert res["component_bom_tokens"]["R3"] == ["X"]
    assert res["component_bom_tokens"]["TP1"] == ["NOBOM"]


def test_validate_and_extract_bom_configs_multi():
    """測試多組 Config (長度為 5) 與單一值 (長度為 1 自動擴展至 5)"""
    components = {
        "R1": {"user_props": {"BOM": "I,X,P,I,I"}},
        "R2": {"user_props": {"BOM": "I"}},  # 1 代表全為 I
        "R3": {"user_props": {"BOM": "PROTO,MP,NI,I,X"}},
    }
    res = validate_and_extract_bom_configs(components)
    assert res["config_count"] == 5
    assert res["config_names"] == ["Config 1", "Config 2", "Config 3", "Config 4", "Config 5"]
    assert res["is_multi_config"] is True
    assert res["component_bom_tokens"]["R1"] == ["I", "X", "P", "I", "I"]
    assert res["component_bom_tokens"]["R2"] == ["I", "I", "I", "I", "I"]
    assert res["component_bom_tokens"]["R3"] == ["P", "M", "X", "I", "X"]


def test_validate_and_extract_bom_configs_missing_bom():
    """測試元件缺少 BOM 屬性時拋出明確錯誤"""
    components = {
        "R1": {"user_props": {"BOM": "I"}},
        "R2": {"user_props": {}},
    }
    with pytest.raises(ValueError, match="元件 R2 缺少 BOM 屬性或為空字串"):
        validate_and_extract_bom_configs(components)


def test_validate_and_extract_bom_configs_empty_bom():
    """測試元件 BOM 屬性為空字串時拋出明確錯誤"""
    components = {
        "R1": {"user_props": {"BOM": "   "}},
    }
    with pytest.raises(ValueError, match="元件 R1 缺少 BOM 屬性或為空字串"):
        validate_and_extract_bom_configs(components)


def test_validate_and_extract_bom_configs_invalid_token():
    """測試元件包含未知 BOM 代碼時拋出明確錯誤"""
    components = {
        "R1": {"user_props": {"BOM": "I,ABC,X"}},
    }
    with pytest.raises(ValueError, match="元件 R1 的 BOM 屬性包含不合法的狀態標記 'ABC'"):
        validate_and_extract_bom_configs(components)


def test_validate_and_extract_bom_configs_empty_comma_slot():
    """測試元件包含逗號空白項 (如 'I,,X') 時拋出明確錯誤"""
    components = {
        "R1": {"user_props": {"BOM": "I,,X"}},
    }
    with pytest.raises(ValueError, match="包含空白項目"):
        validate_and_extract_bom_configs(components)


def test_validate_and_extract_bom_configs_illegal_count():
    """測試元件 Config 數量不合法 (既非 1 亦非 5) 時拋出明確錯誤"""
    components = {
        "R1": {"user_props": {"BOM": "I,X,P,I,I"}},  # 5 configs
        "R2": {"user_props": {"BOM": "I,X,P"}},      # 3 configs -> 非 1 亦非 5，報錯！
    }
    with pytest.raises(ValueError, match="BOM Config 數量不合法.*元件 R2 的 BOM 欄位具有 3 組設定.*僅允許 1 或 5 組"):
        validate_and_extract_bom_configs(components)
