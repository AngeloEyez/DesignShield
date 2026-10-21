"""
通用 MatchCondition 與 PatternEvaluator 運算子單元測試
(Generic Match Condition & Pattern Evaluator Unit Tests)
"""

import pytest
from backend.app.engine.pattern_engine import MatchCondition, ComponentRule, AssignData
from backend.app.engine.pattern_engine.evaluator import PatternEvaluator


def test_shorthand_exact_match():
    """驗證純值簡寫 (如 bom: 'NOBOM') 自動視為 exact 相等比對，且預設大小寫不敏感"""
    evaluator = PatternEvaluator()
    cond = {"bom": "NOBOM"}

    assert evaluator.evaluate(cond, {"bom": "NOBOM"}) is True
    assert evaluator.evaluate(cond, {"bom": "nobom"}) is True
    assert evaluator.evaluate(cond, {"bom": "I"}) is False


def test_operator_exact_and_ne_with_case_sensitivity():
    """驗證 exact, eq, ne 運算子與 case_sensitive 旗標"""
    evaluator = PatternEvaluator()

    # 1. 預設 case_sensitive: false
    cond_eq = {"ref_des": {"eq": "u1"}}
    assert evaluator.evaluate(cond_eq, {"ref_des": "U1"}) is True

    # 2. 顯式 case_sensitive: true
    cond_exact_case = {"ref_des": {"exact": "u1", "case_sensitive": True}}
    assert evaluator.evaluate(cond_exact_case, {"ref_des": "U1"}) is False
    assert evaluator.evaluate(cond_exact_case, {"ref_des": "u1"}) is True

    # 3. ne (不等於)
    cond_ne = {"bom": {"ne": "NOBOM"}}
    assert evaluator.evaluate(cond_ne, {"bom": "I"}) is True
    assert evaluator.evaluate(cond_ne, {"bom": "NOBOM"}) is False


def test_operator_prefix_and_suffix():
    """驗證 prefix 與 suffix 運算子"""
    evaluator = PatternEvaluator()

    cond_prefix = {"description": {"prefix": "CAP,"}}
    assert evaluator.evaluate(cond_prefix, {"description": "cap,100nF,50V"}) is True
    assert evaluator.evaluate(cond_prefix, {"description": "RES,10K"}) is False

    cond_suffix = {"package": {"suffix": "_SMD"}}
    assert evaluator.evaluate(cond_suffix, {"package": "0402_smd"}) is True
    assert evaluator.evaluate(cond_suffix, {"package": "0402_DIP"}) is False


def test_operator_in_and_not_in():
    """驗證 in (集合包含，支援列表簡寫) 與 not_in 運算子"""
    evaluator = PatternEvaluator()

    # 列表簡寫視為 in
    cond_in_shorthand = {"package": ["0402", "0603", "0805"]}
    assert evaluator.evaluate(cond_in_shorthand, {"package": "0603"}) is True
    assert evaluator.evaluate(cond_in_shorthand, {"package": "1206"}) is False

    # 顯式 not_in
    cond_not_in = {"bom": {"not_in": ["X", "NI"]}}
    assert evaluator.evaluate(cond_not_in, {"bom": "NOBOM"}) is True
    assert evaluator.evaluate(cond_not_in, {"bom": "NI"}) is False
    assert evaluator.evaluate(cond_not_in, {"bom": "X"}) is False


def test_operator_numeric_ranges():
    """驗證 min, max, gte, lte 數值比對"""
    evaluator = PatternEvaluator()

    cond_pins = {"pins_count": {"min": 2, "max": 4}}
    assert evaluator.evaluate(cond_pins, {"pins_count": 2}) is True
    assert evaluator.evaluate(cond_pins, {"pins_count": 3}) is True
    assert evaluator.evaluate(cond_pins, {"pins_count": 4}) is True
    assert evaluator.evaluate(cond_pins, {"pins_count": 1}) is False
    assert evaluator.evaluate(cond_pins, {"pins_count": 5}) is False

    cond_gte_lte = {"pins_count": {"gte": 8}}
    assert evaluator.evaluate(cond_gte_lte, {"pins_count": 8}) is True
    assert evaluator.evaluate(cond_gte_lte, {"pins_count": 16}) is True
    assert evaluator.evaluate(cond_gte_lte, {"pins_count": 4}) is False


def test_operator_exists():
    """驗證 exists 運算子檢查屬性是否存在且非空"""
    evaluator = PatternEvaluator()

    cond_exists = {"props.CCL": {"exists": True}}
    assert evaluator.evaluate(cond_exists, {"user_props": {"CCL": "N"}}) is True
    assert evaluator.evaluate(cond_exists, {"user_props": {}}) is False
    assert evaluator.evaluate(cond_exists, {}) is False

    cond_not_exists = {"props.CCL": {"exists": False}}
    assert evaluator.evaluate(cond_not_exists, {}) is True
    assert evaluator.evaluate(cond_not_exists, {"user_props": {"CCL": "N"}}) is False


def test_user_props_access():
    """驗證 props.<key> 與 user_props.<key> 支援任意 CAD 屬性精確讀取"""
    evaluator = PatternEvaluator()

    cond_prop = {"props.Manufacturer": "Murata"}
    data = {"user_props": {"Manufacturer": "MURATA", "CCL": "Y"}}
    assert evaluator.evaluate(cond_prop, data) is True

    # 直接回退查詢
    cond_fallback_prop = {"CCL": "Y"}
    assert evaluator.evaluate(cond_fallback_prop, data) is True


def test_any_text_virtual_field():
    """驗證 any_text 虛擬全文合成欄位 (part_value + mfg_pn + description + package)"""
    evaluator = PatternEvaluator()

    cond = {"any_text": {"regex": "(?i)\\bCOMMON\\s*MODE\\b"}}
    data = {
        "part_value": "DLM0NSN900HY2D",
        "mfg_pn": "DLM0NSN900HY2D",
        "description": "Chip Common Mode Choke Coil",
        "package": "0402",
    }
    assert evaluator.evaluate(cond, data) is True


def test_tree_nested_boolean_logic():
    """驗證 match_all 與 match_any 巢狀邏輯樹"""
    evaluator = PatternEvaluator()

    # 模擬測試點規則：
    # 必須 (AND) BOM=NOBOM，且 (OR) description 包含 TEST 或 value 包含 PROBE
    cond = MatchCondition(
        match_all=[
            {"bom": "NOBOM"},
            {
                "match_any": [
                    {"description": {"regex": "(?i)TEST"}},
                    {"part_value": {"regex": "(?i)PROBE"}},
                ]
            },
        ]
    )

    # 符合條件
    assert evaluator.evaluate(cond, {"bom": "NOBOM", "description": "Test Point SMD"}) is True
    assert evaluator.evaluate(cond, {"bom": "NOBOM", "part_value": "PROBE_PAD"}) is True

    # 缺少 BOM=NOBOM (雖然有 TEST) -> False
    assert evaluator.evaluate(cond, {"bom": "I", "description": "Test Point SMD"}) is False

    # BOM=NOBOM 但無匹配關鍵字 -> False
    assert evaluator.evaluate(cond, {"bom": "NOBOM", "description": "Resistor", "part_value": "10K"}) is False


def test_precompile_condition_caches_regex():
    """驗證 precompile_condition 正確遞迴預熱快取所有 regex"""
    evaluator = PatternEvaluator()
    evaluator.clear_cache()

    cond = {
        "match_all": [
            {"description": {"regex": "(?i)CAP"}},
            {
                "match_any": [
                    {"part_value": {"regex": "(?i)UF"}},
                    {"any_text": {"regex": "(?i)MLCC"}},
                ]
            },
        ]
    }

    count = evaluator.precompile_condition(cond)
    assert count == 3
    assert evaluator.get_cached_regex_count() == 3
