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


def test_level3_engine_power_ground_short():
    G = nx.Graph()
    G.add_node("net:PWR_GND_ERR", type="net", net_name="PWR_GND_ERR", is_power=True, is_ground=True)
    
    engine = Level3Engine()
    findings = engine.run_checks(G, ["power_ground_short_fatal"])
    
    assert len(findings) == 1
    f = findings[0]
    assert f["rule_id"] == "power_ground_short_fatal"
    assert f["status"] == "FAIL"
    assert f["severity"] == "FATAL"
    assert "致命電源短路" in f["description"]


def test_level3_engine_i2c_pullup_missing_and_present():
    engine = Level3Engine()

    # 情境 1: 缺少上拉電阻
    G1 = nx.Graph()
    G1.add_node("net:I2C_SDA", type="net", net_name="I2C_SDA", bus_type="I2C")
    findings1 = engine.run_checks(G1, ["i2c_pull_up_existence"])
    assert len(findings1) == 1
    assert findings1[0]["status"] == "FAIL"
    assert "缺少上拉電阻" in findings1[0]["description"]

    # 情境 2: 具備合法上拉電阻
    G2 = nx.Graph()
    G2.add_node("net:I2C_SDA", type="net", net_name="I2C_SDA", bus_type="I2C")
    G2.add_node("net:VCC3V3", type="net", net_name="VCC3V3", is_power=True)
    G2.add_node("comp:R1", type="component", ref_des="R1", category="Passive", sub_category="Resistor", functional_role="Pull_up", part_value="4.7k")
    G2.add_edge("comp:R1", "net:I2C_SDA")
    G2.add_edge("comp:R1", "net:VCC3V3")

    findings2 = engine.run_checks(G2, ["i2c_pull_up_existence"])
    assert len(findings2) == 1
    assert findings2[0]["status"] == "PASS"


def test_level3_engine_partdb_dynamic_checker():
    engine = Level3Engine()
    
    # 建立連接至 STM32F405 的 I2C 匯流排，但違反禁止對地電容特規
    G = nx.Graph()
    G.add_node("comp:U1", type="component", ref_des="U1", category="IC", sub_category="Microcontroller", functional_role="Bus_Master", part_value="STM32F405", is_electrical=True)
    G.add_node("net:I2C_SCL", type="net", net_name="I2C_SCL", bus_type="I2C")
    G.add_node("net:GND", type="net", net_name="GND", is_ground=True)
    G.add_node("comp:C_ERR", type="component", ref_des="C_ERR", category="Passive", sub_category="Capacitor", part_value="100pF")
    
    G.add_edge("comp:U1", "net:I2C_SCL")
    G.add_edge("comp:C_ERR", "net:I2C_SCL")
    G.add_edge("comp:C_ERR", "net:GND")

    findings = engine.run_checks(G, ["i2c_stm32_dynamic"])
    assert len(findings) >= 1
    err = next((f for f in findings if f["status"] == "FAIL"), None)
    assert err is not None
    assert "STM32F405" in err["description"]
    assert "嚴禁外接接地電容" in err["description"]
    assert "_meta" in err
    assert err["_meta"]["evidence"] == "STM32F405_Datasheet_Rev4.pdf"


def test_pre_analyzer_recommends_level3_rules():
    G = nx.Graph()
    G.add_node("comp:U1", type="component", ref_des="U1", category="IC", sub_category="Microcontroller", functional_role="Bus_Master", part_value="STM32F405", is_electrical=True)
    G.add_node("net:I2C_SDA", type="net", net_name="I2C_SDA", bus_type="I2C")
    G.add_edge("comp:U1", "net:I2C_SDA")

    analysis = analyze_schematic_features(G)
    rules = [r.id for r in analysis["recommended_rules"]]
    
    assert "i2c_pull_up_existence" in rules
    assert "i2c_stm32_dynamic" in rules
