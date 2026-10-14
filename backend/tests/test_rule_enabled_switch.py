"""
Level 1~3 規則 enabled 開關功能與驗證器測試 (Rule Enabled Switch Tests)

測試項目:
1. validate_rules 校驗器對 enabled 欄位之型別校驗 (必須為 bool)
2. PatternService 載入各層規則時對 enabled 屬性之解析與預設值
3. Level 1 ComponentPatternEngine 於 enabled: false 時之忽略行為
4. Level 2 TopologyPatternEngine 於 enabled: false 時之忽略行為
5. Level 3 Level3Runner 於 enabled: false 時之跳過執行行為
6. pre_analyzer 於 enabled: false 時排除推薦之行為
"""

import pytest
import networkx as nx
from backend.app.engine.pattern_engine.models import (
    ComponentRule,
    MatchCondition,
    AssignData,
    TopologyRule,
    SignalPattern,
    SignalMatchCondition,
    SignalMatchBlock,
)
from backend.app.engine.pattern_engine.component_engine import ComponentPatternEngine
from backend.app.engine.pattern_engine.topology_engine import TopologyPatternEngine
from backend.app.engine.drc_engine.level3_runner import Level3Engine
from backend.app.engine.pre_analyzer import analyze_schematic_features
from backend.app.services.pattern_service import PatternService
from scripts.validate_rules import (
    validate_level1_rules,
    validate_level2_rules,
    validate_level3_rules,
)


def test_validate_rules_rejects_non_boolean_enabled(tmp_path):
    """驗證 validate_rules.py 當 enabled 欄位非布林值時拋出錯誤"""
    # 建立臨時 patterns 目錄結構
    p_dir = tmp_path / "patterns"
    l1_dir = p_dir / "components"
    l2_dir = p_dir / "buses"
    l3_dir = p_dir / "rules" / "interfaces"
    l1_dir.mkdir(parents=True)
    l2_dir.mkdir(parents=True)
    l3_dir.mkdir(parents=True)

    # Level 1 錯誤型別
    (l1_dir / "bad_l1.yaml").write_text(
        """
name: "rule_bad_enabled"
enabled: "false"  # 錯誤：字串而非布林值
priority: 500
matches: {}
assigns:
  category: "Passive"
  sub_category: "Resistor"
  functional_role: "Passive_Support"
  is_electrical: true
  confidence: 0.9
""",
        encoding="utf-8",
    )

    errs_l1 = validate_level1_rules(str(p_dir))
    assert any("'enabled' 欄位必須為布林值" in e for e in errs_l1)

    # Level 2 錯誤型別
    (l2_dir / "bad_l2.yaml").write_text(
        """
name: "bad_l2_rule"
category: "Communication"
priority: 600
enabled: 1  # 錯誤：整數而非布林值
signals: []
""",
        encoding="utf-8",
    )

    errs_l2 = validate_level2_rules(str(p_dir))
    assert any("'enabled' 欄位必須為布林值" in e for e in errs_l2)

    # Level 3 錯誤型別
    (l3_dir / "bad_l3.yaml").write_text(
        """
name: "bad_l3_rule"
severity: "Error"
tags: []
enabled: "no"  # 錯誤：字串而非布林值
trigger_conditions: {}
check_logic:
  type: "topology_check"
""",
        encoding="utf-8",
    )

    errs_l3 = validate_level3_rules(tags_whitelist=set(), patterns_dir=str(p_dir))
    assert any("'enabled' 欄位必須為布林值" in e for e in errs_l3)


def test_level1_component_engine_ignores_disabled_rule():
    """驗證 Level 1 元件引擎在 enabled: false 時自動跳過該規則"""
    engine = ComponentPatternEngine()
    engine.evaluator.clear_cache()
    engine._is_loaded = True

    # 建立兩條規則：較高優先權但已停用，較低優先權但啟用
    rule_disabled = ComponentRule(
        name="rule_disabled_mcu",
        priority=900,
        enabled=False,
        matches=MatchCondition(ref_prefix="U"),
        assigns=AssignData(
            category="IC",
            sub_category="Microcontroller",
            functional_role="Bus_Master",
            is_electrical=True,
            confidence=0.95,
        ),
    )

    rule_fallback = ComponentRule(
        name="rule_fallback_ic",
        priority=500,
        enabled=True,
        matches=MatchCondition(ref_prefix="U"),
        assigns=AssignData(
            category="IC",
            sub_category="Other",
            functional_role="None",
            is_electrical=True,
            confidence=0.5,
        ),
    )

    engine.rules = [rule_disabled, rule_fallback]
    engine.evaluator.precompile_condition(rule_disabled.matches)
    engine.evaluator.precompile_condition(rule_fallback.matches)

    # 進行分類測試
    assigned, matched_name = engine.classify(
        ref_des="U1",
        part_value="MCU_CHIP",
        description="Microcontroller",
        package="LQFP",
        mfg_pn="STM32",
        pins_count=48,
    )

    # 雖然 rule_disabled 符合 U1 且優先級 900，但因為停用，命中備援規則
    assert matched_name == "rule_fallback_ic"
    assert assigned["sub_category"] == "Other"

    # 若將 rule_disabled 重新啟用，則應命中 rule_disabled_mcu
    rule_disabled.enabled = True
    assigned2, matched_name2 = engine.classify(
        ref_des="U1",
        part_value="MCU_CHIP",
        description="Microcontroller",
        package="LQFP",
        mfg_pn="STM32",
        pins_count=48,
    )
    assert matched_name2 == "rule_disabled_mcu"
    assert assigned2["sub_category"] == "Microcontroller"


def test_level2_topology_engine_ignores_disabled_rule():
    """驗證 Level 2 拓撲引擎在 enabled: false 時跳過特徵評估"""
    topo_engine = TopologyPatternEngine()

    rule_i2c = TopologyRule(
        name="test_i2c_bus",
        category="Communication",
        priority=700,
        enabled=False,  # 設為停用
        signals=[
            SignalPattern(
                role="SCL",
                required=True,
                matches=SignalMatchCondition(
                    match_any=[
                        SignalMatchBlock(
                            match_all=[SignalMatchCondition(net_name_regex=".*SCL.*")],
                            confidence_contribution=1.0,
                        )
                    ]
                ),
            )
        ],
    )

    topo_engine.rules = [rule_i2c]

    G = nx.Graph()
    G.add_node("net:I2C_SCL", type="net", net_name="I2C_SCL")

    # 執行拓撲評估
    topo_engine.execute(G)

    # 由於 rule_i2c 為停用狀態，網路不應被標註為 bus_type="test_i2c_bus" 或 is_bus=True
    net_data = G.nodes["net:I2C_SCL"]
    assert net_data.get("is_bus") is not True
    assert net_data.get("bus_type") is None

    # 當重新啟用時
    rule_i2c.enabled = True
    topo_engine.execute(G)
    net_data_after = G.nodes["net:I2C_SCL"]
    assert net_data_after.get("is_bus") is True
    assert net_data_after.get("bus_type") == "TEST_I2C"


@pytest.mark.anyio
async def test_level3_runner_skips_disabled_rules():
    """驗證 Level 3 執行引擎在 selected_rule_ids 中即使含有停用規則，亦自動忽略跳過"""
    svc = PatternService.get_instance()
    # 取得現存之一條規則並暫時改為停用
    l3_rules = svc.get_level3_rules()
    assert len(l3_rules) > 0, "Level 3 規則庫不可為空"

    target_rule = l3_rules[0]
    rule_name = target_rule["name"]
    original_enabled = target_rule.get("enabled", True)

    try:
        # 將該規則設為停用
        target_rule["enabled"] = False

        engine = Level3Engine(pattern_service=svc)
        G = nx.Graph()
        # 即使傳入包含該 rule_name
        findings = await engine.run_checks(G, selected_rule_ids=[rule_name])
        # 由於已停用，不應產出任何 finding
        assert len(findings) == 0
    finally:
        target_rule["enabled"] = original_enabled


def test_pre_analyzer_does_not_recommend_disabled_rule():
    """驗證預先分析引擎不會將 enabled: false 的規則列入推薦名單"""
    svc = PatternService.get_instance()
    l3_rules = svc.get_level3_rules()
    assert len(l3_rules) > 0

    target_rule = l3_rules[0]
    original_enabled = target_rule.get("enabled", True)

    try:
        target_rule["enabled"] = False
        G = nx.Graph()
        G.add_node("comp:U1", type="component", ref_des="U1", is_electrical=True)
        G.add_node("net:VCC", type="net", net_name="VCC", is_power=True)

        res = analyze_schematic_features(G)
        recommended_ids = [r.id for r in res["recommended_rules"]]
        assert target_rule["name"] not in recommended_ids
    finally:
        target_rule["enabled"] = original_enabled
