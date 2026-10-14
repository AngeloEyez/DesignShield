"""
NetworkX 圖譜構建與預先分析單元測試 (Graph & Pre-analysis Tests)

驗證二分圖譜 (Bipartite Graph) 拓撲查詢、匯流排與電源識別及智慧推薦規則生成。
"""

import networkx as nx
from backend.app.engine.parser import parse_orcad_xml, parse_allegro_netlist, merge_schematic_data
from backend.app.engine.graph import (
    build_schematic_graph,
    get_components_on_net,
    get_nets_of_component,
)
from backend.app.engine.pattern_engine.topology_engine import TopologyPatternEngine
from backend.app.engine.pre_analyzer import analyze_schematic_features

FIXTURE_XML = "backend/tests/fixtures/sch/cartern-sch-si-20260817.xml"
FIXTURE_NETLIST = "backend/tests/fixtures/sch/allegro/pstxnet.dat"


def test_power_and_bus_net_detection():
    """測試 Level 2 規則引擎 (TopologyPatternEngine) 之電源、接地、匯流排與差分訊號識別"""
    engine = TopologyPatternEngine.get_instance()
    engine.reload()

    test_nets = [
        "VCC3V3", "VBUS_IN", "1V8_CORE", "PW_VCC", "P5V", "DATA_LINE",
        "GND", "AGND", "VSS", "SGND", "EGND", "VCC",
        "I2C_SDA", "SPI_MOSI", "UART_TXD", "USB_DP", "GPIO_LED1",
        "USBC0_TCSS_AUX_N"
    ]

    G = nx.Graph()
    for net in test_nets:
        G.add_node(f"net:{net}", type="net", net_name=net, is_power=False, is_ground=False, is_bus=False, bus_type=None)

    engine.execute(G)

    # 1. 電源網路驗證 (依 900_generic_power.yaml 規則)
    assert G.nodes["net:VCC3V3"].get("is_power") is True
    assert G.nodes["net:VBUS_IN"].get("is_power") is True
    assert G.nodes["net:1V8_CORE"].get("is_power") is True
    assert G.nodes["net:PW_VCC"].get("is_power") is True
    assert G.nodes["net:P5V"].get("is_power") is True
    assert G.nodes["net:DATA_LINE"].get("is_power") is not True

    # 2. 接地網路驗證 (依 950_generic_gnd.yaml 規則)
    assert G.nodes["net:GND"].get("is_ground") is True
    assert G.nodes["net:AGND"].get("is_ground") is True
    assert G.nodes["net:VSS"].get("is_ground") is True
    assert G.nodes["net:SGND"].get("is_ground") is True
    assert G.nodes["net:EGND"].get("is_ground") is True
    assert G.nodes["net:VCC"].get("is_ground") is not True

    # 3. 匯流排驗證 (依 patterns/buses/ YAML 規則)
    assert G.nodes["net:I2C_SDA"].get("bus_type") == "I2C"
    assert G.nodes["net:SPI_MOSI"].get("bus_type") == "SPI"
    assert G.nodes["net:UART_TXD"].get("bus_type") == "UART"
    assert G.nodes["net:USB_DP"].get("bus_type") == "USB"
    assert G.nodes["net:GPIO_LED1"].get("bus_type") is None
    assert G.nodes["net:GPIO_LED1"].get("is_bus") is not True

    # 4. USBC0_TCSS_AUX_N 絕對不可被打上 USB bus 標籤，而應被 600_differential_pair.yaml 標記為 Differential
    aux_node = G.nodes["net:USBC0_TCSS_AUX_N"]
    assert aux_node.get("bus_type") is None
    assert aux_node.get("is_bus") is not True
    assert aux_node.get("net_type") == "Differential"
    assert aux_node.get("diff_polarity") == "N"
    assert aux_node.get("diff_pair_partner") == "USBC0_TCSS_AUX_P"


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

    # 執行 Level 2 拓撲模式引擎以解析電源、接地與匯流排語意
    topo_engine = TopologyPatternEngine.get_instance()
    topo_engine.reload()
    topo_engine.execute(G)

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

    # 驗證真實 Fixture 中的 USBC0_TCSS_AUX_N 不帶 USB bus 標籤，且被識別為 Differential
    if "net:USBC0_TCSS_AUX_N" in G:
        aux_node = G.nodes["net:USBC0_TCSS_AUX_N"]
        assert aux_node.get("bus_type") is None
        assert aux_node.get("is_bus") is not True
        assert aux_node.get("net_type") == "Differential"
        assert aux_node.get("diff_polarity") == "N"
        assert aux_node.get("diff_pair_partner") == "USBC0_TCSS_AUX_P"
