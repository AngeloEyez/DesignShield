"""
傳統啟發式 DRC 圖論規則單元測試 (Heuristic Rules Tests)

驗證 I2C 地址衝突檢測、電容耐壓降額演算法與去耦檢查邏輯。
"""

import networkx as nx
from backend.app.engine.rules.heuristic import (
    check_capacitor_voltage_derating,
    check_power_pin_decoupling,
    check_connector_protection,
    run_all_heuristic_checks,
    extract_voltage_from_string,
    extract_operating_voltage_from_net,
)


def test_voltage_extraction_helpers():
    """測試電壓抽取輔助函式"""
    assert extract_voltage_from_string("6.3V") == 6.3
    assert extract_voltage_from_string("10V_X7R") == 10.0
    assert extract_voltage_from_string("no_voltage") is None

    assert extract_operating_voltage_from_net("VCC3V3") == 3.3
    assert extract_operating_voltage_from_net("PB_VBUS_2") == 5.0
    assert extract_operating_voltage_from_net("12V_MAIN") == 12.0
    assert extract_operating_voltage_from_net("1V8_CORE") == 1.8
    assert extract_operating_voltage_from_net("SIGNAL_CLK") is None


def test_check_capacitor_voltage_derating_fail_and_warning():
    """測試電容耐壓不足 (如 5V 網路上使用 6.3V 或 4V 電容) 觸發 FAIL 或 WARNING"""
    G = nx.Graph()
    # C1: 耐壓 4V，位於 5V 網路 -> FAIL
    G.add_node("comp:C1", type="component", ref_des="C1", category="Capacitor", voltage="4V", part_value="10uF_4V")
    # C2: 耐壓 6.3V，位於 5V 網路 (裕量不足 30%) -> WARNING
    G.add_node("comp:C2", type="component", ref_des="C2", category="Capacitor", voltage="6.3V", part_value="10uF_6.3V")
    # C3: 耐壓 16V，位於 5V 網路 -> PASS
    G.add_node("comp:C3", type="component", ref_des="C3", category="Capacitor", voltage="16V", part_value="10uF_16V")

    G.add_node("net:VBUS_5V", type="net", net_name="VBUS_5V", is_power=True)
    G.add_edge("comp:C1", "net:VBUS_5V")
    G.add_edge("comp:C2", "net:VBUS_5V")
    G.add_edge("comp:C3", "net:VBUS_5V")

    findings = check_capacitor_voltage_derating(G)
    statuses = [f["status"] for f in findings]
    assert "FAIL" in statuses
    assert "WARNING" in statuses
    assert "PASS" in statuses


def test_run_all_heuristic_checks():
    """測試批量執行 Heuristic 檢測規則"""
    G = nx.Graph()
    G.add_node("comp:TU10", type="component", ref_des="TU10", category="IC")
    G.add_node("comp:P72", type="component", ref_des="P72", category="Connector")
    G.add_node("net:PB_VBUS_2", type="net", net_name="PB_VBUS_2", is_power=True)
    G.add_edge("comp:TU10", "net:PB_VBUS_2")

    rule_ids = [
        "power_capacitor_derating",
        "ic_decoupling_capacitor_existence",
        "connector_pinout_protection"
    ]
    results = run_all_heuristic_checks(G, rule_ids)
    assert len(results) >= 2
    rule_found = [r["rule_id"] for r in results]
    assert "ic_decoupling_capacitor_existence" in rule_found
    assert "connector_pinout_protection" in rule_found
