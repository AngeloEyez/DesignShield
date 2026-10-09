"""
NetworkX 圖譜構建與預先分析單元測試 (Graph & Pre-analysis Tests)

驗證二分圖譜 (Bipartite Graph) 拓撲查詢、匯流排與電源識別及智慧推薦規則生成。
"""

from backend.app.engine.parser import parse_orcad_xml, parse_allegro_netlist, merge_schematic_data
from backend.app.engine.graph import (
    build_schematic_graph,
    get_components_on_net,
    get_nets_of_component,
    is_power_net,
    is_ground_net,
    detect_bus_type,
)
from backend.app.engine.pre_analyzer import analyze_schematic_features

FIXTURE_XML = "backend/tests/fixtures/sch/cartern-sch-si-20260817.xml"
FIXTURE_NETLIST = "backend/tests/fixtures/sch/allegro/pstxnet.dat"


def test_power_and_bus_net_detection():
    """測試電源、接地與匯流排命名特徵識別"""
    assert is_power_net("VCC3V3") is True
    assert is_power_net("VBUS_IN") is True
    assert is_power_net("1V8_CORE") is True
    assert is_power_net("DATA_LINE") is False

    assert is_ground_net("GND") is True
    assert is_ground_net("AGND") is True
    assert is_ground_net("VSS") is True
    assert is_ground_net("VCC") is False

    assert detect_bus_type("I2C_SDA") == "I2C"
    assert detect_bus_type("SPI_MOSI") == "SPI"
    assert detect_bus_type("UART_TXD") == "UART"
    assert detect_bus_type("USB_DP") == "USB"
    assert detect_bus_type("PCIE_TXP") == "PCIE"
    assert detect_bus_type("GPIO_LED1") is None


def test_build_schematic_graph_and_queries():
    """測試構建 NetworkX 圖譜與拓撲查詢功能"""
    mock_data = {
        "components": {
            "U1": {"ref_des": "U1", "category": "IC", "part_value": "STM32F4", "package": "LQFP64"},
            "R1": {"ref_des": "R1", "category": "Resistor", "part_value": "4.7K", "package": "0402"},
        },
        "nets": {
            "I2C_SCL": [
                {"ref_des": "U1", "pin_number": "PB6", "pin_name": "PB6"},
                {"ref_des": "R1", "pin_number": "1", "pin_name": "1"}
            ],
            "VCC3V3": [
                {"ref_des": "R1", "pin_number": "2", "pin_name": "2"}
            ]
        }
    }

    G = build_schematic_graph(mock_data)
    assert G.number_of_nodes() == 4  # 2 components + 2 nets
    assert G.number_of_edges() == 3

    # 驗證查詢網路上的元件
    i2c_comps = get_components_on_net(G, "I2C_SCL")
    assert len(i2c_comps) == 2
    refs = [c["ref_des"] for c in i2c_comps]
    assert "U1" in refs
    assert "R1" in refs

    # 驗證查詢元件上的網路
    r1_nets = get_nets_of_component(G, "R1")
    assert len(r1_nets) == 2
    net_names = [n["net_name"] for n in r1_nets]
    assert "I2C_SCL" in net_names
    assert "VCC3V3" in net_names


def test_e2e_real_fixture_graph_and_pre_analysis():
    """使用真實線路圖 Fixture 執行端到端解析、圖譜構建與特徵分析"""
    xml_data = parse_orcad_xml(FIXTURE_XML)
    netlist_data = parse_allegro_netlist(FIXTURE_NETLIST)
    merged = merge_schematic_data(xml_data, netlist_data)

    G = build_schematic_graph(merged)
    assert G.number_of_nodes() > 500
    assert G.number_of_edges() >= 800

    # 執行輕量預先分析
    analysis = analyze_schematic_features(G)
    summary = analysis["summary"]
    rules = analysis["recommended_rules"]

    # 驗證特徵摘要
    assert summary.component_count >= 300
    assert summary.net_count >= 200
    assert "USB" in summary.buses or "SPI" in summary.buses or "I2C" in summary.buses
    assert len(rules) >= 1

    rule_ids = [r.id for r in rules]
    assert "power_capacitor_derating" in rule_ids or "i2c_pull_up_existence" in rule_ids
