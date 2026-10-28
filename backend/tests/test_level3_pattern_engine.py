"""
Level 3 DRC 規則引擎與 Pattern API 單元測試 (Level 3 Engine & Pattern API Tests)
"""

import networkx as nx
from backend.app.services.pattern_service import PatternService
from backend.app.engine.drc_engine import Level3Engine
from backend.app.engine.pre_analyzer import analyze_schematic_features


def test_pattern_service_load_and_tree():
    svc = PatternService.get_instance()
    tree = svc.get_pattern_tree(force_refresh=True)
    
    assert "level1" in tree
    assert "level2" in tree
    assert "level3" in tree
    assert "partdb" in tree
    assert "tags" in tree
    
    assert tree["summary"]["level3_count"] >= 5
    assert tree["summary"]["partdb_parts_count"] >= 2
    assert "I2C" in tree["tags"]
    assert "Fatal" in tree["tags"]


def test_patterns_api(client):
    # 測試 GET /api/v1/patterns/tree
    res = client.get("/api/v1/patterns/tree")
    assert res.status_code == 200
    data = res.json()
    assert "summary" in data
    assert data["summary"]["level3_count"] >= 5

    # 測試 POST /api/v1/patterns/reload
    res_reload = client.post("/api/v1/patterns/reload")
    assert res_reload.status_code == 200
    assert res_reload.json()["success"] is True

    # 測試 GET /api/v1/patterns/tags
    res_tags = client.get("/api/v1/patterns/tags")
    assert res_tags.status_code == 200
    assert "I2C" in res_tags.json()

    # 測試 GET /api/v1/patterns/level2-categories (SSOT 白名單端點)
    res_l2_cats = client.get("/api/v1/patterns/level2-categories")
    assert res_l2_cats.status_code == 200
    l2_cats = res_l2_cats.json()
    assert isinstance(l2_cats, list)
    assert "Bus" in l2_cats
    assert "GND" in l2_cats
    assert "Power" in l2_cats
    assert "Differential" in l2_cats


import pytest

@pytest.mark.anyio
async def test_level3_engine_power_ground_short():
    G = nx.Graph()
    G.add_node("net:PWR_GND_ERR", type="net", net_name="PWR_GND_ERR", is_power=True, is_ground=True)
    
    engine = Level3Engine()
    findings = await engine.run_checks(G, ["power_ground_short_fatal"])
    
    assert len(findings) == 1
    f = findings[0]
    assert f["rule_id"] == "power_ground_short_fatal"
    assert f["status"] == "FAIL"
    assert f["severity"] == "FATAL"
    assert "致命電源短路" in f["error_message"]
    assert "隔離或移除" in f["recommendation"]


@pytest.mark.anyio
async def test_level3_engine_i2c_pullup_missing_and_present():
    engine = Level3Engine()

    # 情境 1: 缺少上拉電阻 (FAIL)
    G1 = nx.Graph()
    G1.add_node("net:I2C_SDA", type="net", net_name="I2C_SDA", bus_type="I2C")
    findings1 = await engine.run_checks(G1, ["i2c_pull_up_existence"])
    assert len(findings1) == 1
    assert findings1[0]["status"] == "FAIL"
    assert "缺少上拉電阻" in findings1[0]["error_message"]
    assert "建議在 I2C 訊號線配置" in findings1[0]["recommendation"]

    # 情境 2: 具備合法上拉電阻 (PASS)
    G2 = nx.Graph()
    G2.add_node("net:I2C_SDA", type="net", net_name="I2C_SDA", bus_type="I2C")
    G2.add_node("net:VCC3V3", type="net", net_name="VCC3V3", is_power=True)
    G2.add_node("comp:R1", type="component", ref_des="R1", category="Passive", sub_category="Resistor", functional_role="Pull_up", part_value="4.7k")
    G2.add_edge("comp:R1", "net:I2C_SDA")
    G2.add_edge("comp:R1", "net:VCC3V3")

    findings2 = await engine.run_checks(G2, ["i2c_pull_up_existence"])
    assert len(findings2) == 1
    assert findings2[0]["status"] == "PASS"
    assert findings2[0]["error_message"] == ""
    assert "R1" in findings2[0]["target_nodes"]["components"]
    ev2 = findings2[0]["evidence_trail"]
    assert ev2.get("pullup_found") is True
    assert len(ev2.get("resistors", [])) == 1
    assert ev2["resistors"][0]["ref_des"] == "R1"
    assert ev2["resistors"][0]["resistance_ohm"] == 4700.0
    assert ev2["resistors"][0]["power_rail"] == "VCC3V3"
    assert "audit_summary" in ev2

    # 情境 3: 電路圖中無任何 I2C 網路節點 (SKIPPED)
    G3 = nx.Graph()
    G3.add_node("net:SPI_CLK", type="net", net_name="SPI_CLK", bus_type="SPI")
    findings3 = await engine.run_checks(G3, ["i2c_pull_up_existence"])
    assert len(findings3) == 1
    assert findings3[0]["status"] == "SKIPPED"
    assert findings3[0]["error_message"] == ""
    assert findings3[0]["recommendation"] == ""


@pytest.mark.anyio
async def test_level3_engine_partdb_dynamic_checker():
    engine = Level3Engine()
    
    # 建立連接至 TPS66994 的 I2C 匯流排，但違反上拉電阻阻值範圍特規 (TPS66994 要求 1000~2400 歐姆，此處給予 4.7k)
    G = nx.Graph()
    G.add_node("comp:U1", type="component", ref_des="U1", category="IC", sub_category="Power", functional_role="Bus_Master", part_value="TPS66994", is_electrical=True)
    G.add_node("net:I2C_SCL", type="net", net_name="I2C_SCL", bus_type="I2C")
    G.add_node("net:VCC3V3", type="net", net_name="VCC3V3", is_power=True)
    G.add_node("comp:R1", type="component", ref_des="R1", category="Passive", sub_category="Resistor", functional_role="Pull_up", part_value="4.7k")
    
    G.add_edge("comp:U1", "net:I2C_SCL")
    G.add_edge("comp:R1", "net:I2C_SCL")
    G.add_edge("comp:R1", "net:VCC3V3")

    findings = await engine.run_checks(G, ["i2c_stm32_dynamic"])
    assert len(findings) >= 1
    err = next((f for f in findings if f["status"] == "FAIL"), None)
    assert err is not None
    assert "1000Ω ~ 2400Ω" in err["error_message"]
    assert "阻值不在晶片規格書要求範圍" in err["error_message"]
    assert "_meta" in err
    assert err["_meta"]["evidence"] == "TI_TPS66994CBREPR.pdf"


def test_pre_analyzer_recommends_level3_rules():
    G = nx.Graph()
    G.add_node("comp:U1", type="component", ref_des="U1", category="IC", sub_category="Microcontroller", functional_role="Bus_Master", part_value="STM32F405", is_electrical=True)
    G.add_node("net:I2C_SDA", type="net", net_name="I2C_SDA", bus_type="I2C")
    G.add_edge("comp:U1", "net:I2C_SDA")

    analysis = analyze_schematic_features(G)
    rules = [r.id for r in analysis["recommended_rules"]]
    
    assert "i2c_pull_up_existence" in rules
    assert "i2c_stm32_dynamic" in rules


def test_generic_regex_in_attributes_level3_runner():
    """驗證 Level3Engine 支援在 attributes 內部進行通用 *_regex 匹配，並廢除外層 net_name_regex"""
    engine = Level3Engine()
    G = nx.Graph()
    G.add_node("comp:U1", type="component", ref_des="U1", mfg_pn="LSF0102DCUR", category="IC")
    G.add_node("comp:U2", type="component", ref_des="U2", mfg_pn="TXS0102DCUR", category="IC")
    G.add_node("comp:U3", type="component", ref_des="U3", category="IC")  # mfg_pn 為 None
    G.add_node("net:SD_CLK", type="net", net_name="SD_CLK")
    G.add_node("net:I2C_SDA", type="net", net_name="I2C_SDA")

    # 1. 測試 mfg_pn_regex 在 attributes 內部比對
    tc_mfg = {
        "graph_match": {
            "attributes": {
                "type": "component",
                "mfg_pn_regex": r"(?i)^LSF0102.*"
            }
        }
    }
    targets_mfg = engine._find_matching_targets(G, tc_mfg)
    target_ids = [t["_id"] for t in targets_mfg]
    assert "comp:U1" in target_ids
    assert "comp:U2" not in target_ids
    assert "comp:U3" not in target_ids

    # 2. 測試 net_name_regex 在 attributes 內部比對
    tc_net = {
        "graph_match": {
            "attributes": {
                "type": "net",
                "net_name_regex": r"(?i).*SD_.*"
            }
        }
    }
    targets_net = engine._find_matching_targets(G, tc_net)
    net_ids = [t["_id"] for t in targets_net]
    assert "net:SD_CLK" in net_ids
    assert "net:I2C_SDA" not in net_ids

    # 3. 測試外層 net_name_regex 已徹底被廢除且被忽略 (不會生效)
    tc_outer_deprecated = {
        "graph_match": {
            "attributes": {
                "type": "net"
            },
            "net_name_regex": r"^NEVER_MATCH_ANYTHING$"
        }
    }
    # 因外層被徹底廢除，引擎僅比對 attributes 中的 type=="net"，因此兩條 net 都會命中
    targets_deprecated = engine._find_matching_targets(G, tc_outer_deprecated)
    assert len(targets_deprecated) == 2


def test_generic_regex_in_attributes_pre_analyzer():
    """驗證預先分析引擎支援在 attributes 內部進行通用 *_regex 推薦比對"""
    from backend.app.engine.pre_analyzer import _match_rule_trigger
    G = nx.Graph()
    G.add_node("comp:U1", type="component", ref_des="U1", mfg_pn="LSF0102DCUR", category="IC")

    rule_match = {
        "name": "test_lsf_rule",
        "trigger_conditions": {
            "graph_match": {
                "attributes": {
                    "type": "component",
                    "mfg_pn_regex": r"(?i)^LSF0102.*"
                }
            }
        }
    }
    matched, reason = _match_rule_trigger(G, rule_match, set())
    assert matched is True
    assert "U1" in reason

    rule_unmatch = {
        "name": "test_lsf_unmatch",
        "trigger_conditions": {
            "graph_match": {
                "attributes": {
                    "type": "component",
                    "mfg_pn_regex": r"(?i)^TXS0102.*"
                }
            }
        }
    }
    matched_un, _ = _match_rule_trigger(G, rule_unmatch, set())
    assert matched_un is False

