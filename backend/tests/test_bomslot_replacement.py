"""
BOMSLOT 替代料動態置換機制單元測試 (BOMSLOT Replacement Unit Tests)

驗證 OrCAD 電路圖中以 '=' 命名且 Function="BOMSLOT" 之替代料在多 Config 環境下的：
1. 正常單/多 Config 置換與代碼繼承
2. 圖譜 create_config_subgraph 動態屬性覆蓋
3. 基準零件不存在報錯
4. 同一 Config 基準件與替代件同時上件衝突報錯
5. 多個 BOMSLOT 同時競爭上件衝突報錯
6. 錯誤累積不中斷機制 (Accumulated Error Reporting)
7. 大小寫與空白容錯能力
"""

import pytest
import networkx as nx

from backend.app.engine.bom_parser import (
    validate_and_extract_bom_configs,
    apply_bomslot_replacements,
)
from backend.app.engine.graph import (
    build_schematic_graph,
    create_config_subgraph,
)


def test_bomslot_single_config_replacement():
    """測試單一 Config 下 BOMSLOT 正常置換、代碼繼承與原始節點自圖譜移除"""
    components = {
        "J41": {
            "ref_des": "J41",
            "part_value": "HEADER_OLD",
            "mfg_pn": "PN_OLD_123",
            "mfg": "Molex",
            "package": "HDR_1X10",
            "description": "Old Header",
            "pins": [{"pin_number": "1", "pin_name": "PIN1"}],
            "loc": (100, 200),
            "user_props": {"BOM": "X"},
        },
        "J41=Z2": {
            "ref_des": "J41=Z2",
            "part_value": "HEADER_NEW_Z2",
            "mfg_pn": "PN_Z2_456",
            "mfg": "TE",
            "package": "HDR_1X10_SMD",
            "description": "New Z2 Header Option",
            "pins": [{"pin_number": "1", "pin_name": "PIN1"}],
            "loc": (150, 250),
            "user_props": {"BOM": "I", "Function": "BOMSLOT", "CustomProp": "OptionZ2"},
        },
        "R1": {
            "ref_des": "R1",
            "part_value": "10K",
            "user_props": {"BOM": "I"},
        },
    }

    bom_info = validate_and_extract_bom_configs(components)
    updated_comps, updated_bom_info = apply_bomslot_replacements(components, bom_info)

    # 1. 驗證 J41=Z2 已從 components 中移除
    assert "J41=Z2" not in updated_comps
    assert "J41" in updated_comps

    # 2. 驗證 J41 繼承上件代碼變為 'I'
    assert updated_bom_info["component_bom_tokens"]["J41"] == ["I"]
    assert "J41=Z2" not in updated_bom_info["component_bom_tokens"]

    # 3. 驗證 bomslot_overrides 記錄正確
    overrides = updated_bom_info["bomslot_overrides"][0]
    assert "J41" in overrides
    assert overrides["J41"]["part_value"] == "HEADER_NEW_Z2"

    # 4. 驗證圖譜動態覆蓋 (create_config_subgraph)
    nets = {
        "NET_TEST": [{"ref_des": "J41", "pin_number": "1", "pin_name": "PIN1"}]
    }
    merged_data = {
        "components": updated_comps,
        "nets": nets,
        "bom_config_info": updated_bom_info,
    }
    G = build_schematic_graph(merged_data)
    assert f"comp:J41=Z2" not in G
    assert f"comp:J41" in G

    sub_G = create_config_subgraph(G, config_index=0)
    j41_data = sub_G.nodes["comp:J41"]
    assert j41_data["is_mounted"] is True
    assert j41_data["bom"] == "I"
    assert j41_data["part_value"] == "HEADER_NEW_Z2"
    assert j41_data["mfg_pn"] == "PN_Z2_456"
    assert j41_data["mfg"] == "TE"
    assert j41_data["package"] == "HDR_1X10_SMD"
    assert j41_data["loc"] == (100, 200)  # 保留原始坐標
    assert j41_data["user_props"].get("CustomProp") == "OptionZ2"  # 差分更新
    assert j41_data.get("is_bomslot_replaced") is True
    assert j41_data.get("bomslot_source_ref") == "J41=Z2"


def test_bomslot_multi_config_dynamic_switching():
    """測試多組 Config 下，基準件與不同替代料的動態切換"""
    # Config 1: J41 原料上件 (I), Z2 不上件 (X), Z3 不上件 (X)
    # Config 2: J41 原料不上件 (X), Z2 上件 (I), Z3 不上件 (X)
    # Config 3: J41 原料不上件 (X), Z2 不上件 (X), Z3 樣品上件 (P)
    components = {
        "J41": {
            "ref_des": "J41",
            "part_value": "RAW_J41",
            "mfg_pn": "PN_RAW",
            "user_props": {"BOM": "I,X,X"},
        },
        "J41=Z2": {
            "ref_des": "J41=Z2",
            "part_value": "VAL_Z2",
            "mfg_pn": "PN_Z2",
            "user_props": {"BOM": "X,I,X", "function": "BOMSLOT"},
        },
        "J41=Z3": {
            "ref_des": "J41=Z3",
            "part_value": "VAL_Z3",
            "mfg_pn": "PN_Z3",
            "user_props": {"BOM": "X,X,P", "FUNCTION": "BOMSLOT"},
        },
    }

    bom_info = validate_and_extract_bom_configs(components)
    updated_comps, updated_bom_info = apply_bomslot_replacements(components, bom_info)

    assert "J41=Z2" not in updated_comps
    assert "J41=Z3" not in updated_comps

    # J41 的 token 原本是 ['I', 'X', 'X']，經置換後 Config 2 繼承 Z2 的 'I'，Config 3 繼承 Z3 的 'P'
    assert updated_bom_info["component_bom_tokens"]["J41"] == ["I", "I", "P"]

    merged_data = {
        "components": updated_comps,
        "nets": {},
        "bom_config_info": updated_bom_info,
    }
    G = build_schematic_graph(merged_data)

    # Config 1 (Index 0): J41 使用原始料
    sub_0 = create_config_subgraph(G, config_index=0)
    data_0 = sub_0.nodes["comp:J41"]
    assert data_0["is_mounted"] is True
    assert data_0["bom"] == "I"
    assert data_0["part_value"] == "RAW_J41"
    assert data_0.get("is_bomslot_replaced") is None

    # Config 2 (Index 1): J41 被 Z2 置換
    sub_1 = create_config_subgraph(G, config_index=1)
    data_1 = sub_1.nodes["comp:J41"]
    assert data_1["is_mounted"] is True
    assert data_1["bom"] == "I"
    assert data_1["part_value"] == "VAL_Z2"
    assert data_1.get("is_bomslot_replaced") is True
    assert data_1.get("bomslot_source_ref") == "J41=Z2"

    # Config 3 (Index 2): J41 被 Z3 置換 (樣品模式上件，量產模式不上件)
    sub_2_sample = create_config_subgraph(G, config_index=2, is_mp_mode=False)
    assert sub_2_sample.nodes["comp:J41"]["is_mounted"] is True
    assert sub_2_sample.nodes["comp:J41"]["bom"] == "P"
    assert sub_2_sample.nodes["comp:J41"]["part_value"] == "VAL_Z3"

    sub_2_mp = create_config_subgraph(G, config_index=2, is_mp_mode=True)
    assert sub_2_mp.nodes["comp:J41"]["is_mounted"] is False
    assert sub_2_mp.nodes["comp:J41"]["bom"] == "P"


def test_bomslot_error_missing_target_component():
    """測試找不到基準元件時拋出錯誤"""
    components = {
        "J99=Z1": {
            "ref_des": "J99=Z1",
            "part_value": "VAL_Z1",
            "user_props": {"BOM": "I", "Function": "BOMSLOT"},
        }
    }
    bom_info = validate_and_extract_bom_configs(components)
    with pytest.raises(ValueError) as excinfo:
        apply_bomslot_replacements(components, bom_info)

    err = str(excinfo.value)
    assert "零件 'J99=Z1' 指定之基準零件 'J99' 不存在於線路圖元件清單中" in err


def test_bomslot_error_simultaneous_mount_conflict():
    """測試基準料與替代料在同一個 Config 同時標記為上件時報錯"""
    components = {
        "J41": {
            "ref_des": "J41",
            "part_value": "VAL_ORIG",
            "user_props": {"BOM": "I,X"},
        },
        "J41=Z2": {
            "ref_des": "J41=Z2",
            "part_value": "VAL_Z2",
            "user_props": {"BOM": "I,I", "Function": "BOMSLOT"},
        },
    }
    bom_info = validate_and_extract_bom_configs(components)
    with pytest.raises(ValueError) as excinfo:
        apply_bomslot_replacements(components, bom_info)

    err = str(excinfo.value)
    assert "BOMSLOT 衝突：基準零件 'J41' 與替代零件 'J41=Z2' 在 Config 1" in err
    assert "同時標記為上件" in err


def test_bomslot_error_multiple_bomslots_conflict():
    """測試同一個基準零件在同一 Config 下有多個 BOMSLOT 同時上件競爭衝突報錯"""
    components = {
        "J41": {
            "ref_des": "J41",
            "part_value": "VAL_ORIG",
            "user_props": {"BOM": "X"},
        },
        "J41=Z1": {
            "ref_des": "J41=Z1",
            "part_value": "VAL_Z1",
            "user_props": {"BOM": "I", "Function": "BOMSLOT"},
        },
        "J41=Z2": {
            "ref_des": "J41=Z2",
            "part_value": "VAL_Z2",
            "user_props": {"BOM": "I", "Function": "BOMSLOT"},
        },
    }
    bom_info = validate_and_extract_bom_configs(components)
    with pytest.raises(ValueError) as excinfo:
        apply_bomslot_replacements(components, bom_info)

    err = str(excinfo.value)
    assert "BOMSLOT 衝突：基準零件 'J41' 在 Config 1" in err
    assert "同時有多個 BOMSLOT 標記為上件" in err


def test_bomslot_accumulated_error_reporting():
    """測試遍歷所有 BOMSLOT 元件不中斷，一次累積所有錯誤後再終止報錯"""
    components = {
        # 錯誤 1: 缺少基準件 J99
        "J99=Z1": {
            "ref_des": "J99=Z1",
            "user_props": {"BOM": "I", "Function": "BOMSLOT"},
        },
        # 錯誤 2: J41 與 J41=OPT1 同時上件
        "J41": {
            "ref_des": "J41",
            "user_props": {"BOM": "I"},
        },
        "J41=OPT1": {
            "ref_des": "J41=OPT1",
            "user_props": {"BOM": "I", "Function": "BOMSLOT"},
        },
        # 錯誤 3: R10 有 OPT_A 與 OPT_B 競爭上件
        "R10": {
            "ref_des": "R10",
            "user_props": {"BOM": "X"},
        },
        "R10=OPT_A": {
            "ref_des": "R10=OPT_A",
            "user_props": {"BOM": "I", "Function": "BOMSLOT"},
        },
        "R10=OPT_B": {
            "ref_des": "R10=OPT_B",
            "user_props": {"BOM": "I", "Function": "BOMSLOT"},
        },
    }

    bom_info = validate_and_extract_bom_configs(components)
    with pytest.raises(ValueError) as excinfo:
        apply_bomslot_replacements(components, bom_info)

    err = str(excinfo.value)
    assert "共有 3 個衝突或錯誤" in err or "發現 3 個衝突或錯誤" in err
    assert "零件 'J99=Z1' 指定之基準零件 'J99' 不存在" in err
    assert "基準零件 'J41' 與替代零件 'J41=OPT1' 在 Config 1" in err
    assert "基準零件 'R10' 在 Config 1" in err
    assert "同時有多個 BOMSLOT 標記為上件" in err


def test_bomslot_case_and_whitespace_insensitivity():
    """測試 user_props 的 key 與 value 大小寫與空白容錯"""
    components = {
        "C5": {
            "ref_des": "C5",
            "part_value": "10uF",
            "user_props": {"BOM": "X"},
        },
        "C5=OPT": {
            "ref_des": "C5=OPT",
            "part_value": "22uF",
            "user_props": {"BOM": "I", "  fuNCtion  ": "  bomSlot  "},
        },
    }
    bom_info = validate_and_extract_bom_configs(components)
    updated_comps, updated_bom_info = apply_bomslot_replacements(components, bom_info)

    assert "C5=OPT" not in updated_comps
    assert updated_bom_info["bomslot_overrides"][0]["C5"]["part_value"] == "22uF"


def test_bomslot_npi_vs_mp_complementary():
    """測試 P 與 M 互補替代料在 NPI 模式與 MP 模式下的精確判定，不再誤判衝突"""
    components = {
        "J41": {
            "ref_des": "J41",
            "part_value": "VAL_RAW",
            "mfg_pn": "PN_RAW",
            "user_props": {"BOM": "P"},  # 樣品上件，量產不上件
        },
        "J41=Z2": {
            "ref_des": "J41=Z2",
            "part_value": "VAL_Z2",
            "mfg_pn": "PN_Z2",
            "user_props": {"BOM": "M", "Function": "BOMSLOT"},  # 量產上件，樣品不上件
        },
    }

    # 1. 測試 NPI 模式 (is_mp_mode=False) -> J41 上件, J41=Z2 不上件 -> 不置換且不衝突
    bom_info_npi = validate_and_extract_bom_configs(dict(components))
    comps_npi, bom_npi = apply_bomslot_replacements(dict(components), bom_info_npi, is_mp_mode=False)
    assert "J41=Z2" not in comps_npi
    assert "J41" in comps_npi
    # NPI 模式下 J41=Z2 不上件，因此沒有發生置換
    assert "J41" not in bom_npi["bomslot_overrides"][0]
    G_npi = build_schematic_graph({"components": comps_npi, "nets": {}, "bom_config_info": bom_npi})
    sub_npi = create_config_subgraph(G_npi, config_index=0, is_mp_mode=False)
    assert sub_npi.nodes["comp:J41"]["part_value"] == "VAL_RAW"
    assert sub_npi.nodes["comp:J41"]["is_mounted"] is True

    # 2. 測試 MP 模式 (is_mp_mode=True) -> J41 不上件, J41=Z2 上件 -> 成功置換且不衝突
    bom_info_mp = validate_and_extract_bom_configs(dict(components))
    comps_mp, bom_mp = apply_bomslot_replacements(dict(components), bom_info_mp, is_mp_mode=True)
    assert "J41=Z2" not in comps_mp
    assert "J41" in comps_mp
    # MP 模式下 J41=Z2 生效置換
    assert "J41" in bom_mp["bomslot_overrides"][0]
    G_mp = build_schematic_graph({"components": comps_mp, "nets": {}, "bom_config_info": bom_mp})
    sub_mp = create_config_subgraph(G_mp, config_index=0, is_mp_mode=True)
    assert sub_mp.nodes["comp:J41"]["part_value"] == "VAL_Z2"
    assert sub_mp.nodes["comp:J41"]["is_mounted"] is True
    assert sub_mp.nodes["comp:J41"]["is_bomslot_replaced"] is True


def test_is_component_mounted_in_config_helper():
    """測試統一高階輔助函式 is_component_mounted_in_config"""
    from backend.app.engine.bom_parser import is_component_mounted_in_config

    comp_multi = {"bom_tokens": ["I", "X", "P", "M"]}
    # Config 0: I -> True
    assert is_component_mounted_in_config(comp_multi, config_index=0, is_mp_mode=False) is True
    assert is_component_mounted_in_config(comp_multi, config_index=0, is_mp_mode=True) is True
    # Config 1: X -> False
    assert is_component_mounted_in_config(comp_multi, config_index=1, is_mp_mode=False) is False
    # Config 2: P -> NPI True, MP False
    assert is_component_mounted_in_config(comp_multi, config_index=2, is_mp_mode=False) is True
    assert is_component_mounted_in_config(comp_multi, config_index=2, is_mp_mode=True) is False
    # Config 3: M -> NPI False, MP True
    assert is_component_mounted_in_config(comp_multi, config_index=3, is_mp_mode=False) is False
    assert is_component_mounted_in_config(comp_multi, config_index=3, is_mp_mode=True) is True

