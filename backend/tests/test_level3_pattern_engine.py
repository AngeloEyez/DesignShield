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
