import pytest
import networkx as nx
from backend.app.engine.pattern_engine.models import TopologyRule, SignalPattern, SignalMatchCondition
from backend.app.engine.pattern_engine.topology_engine import TopologyPatternEngine
from unittest.mock import patch, MagicMock



@pytest.fixture
def mock_graph():
    G = nx.Graph()
    # 建立 Net 節點
    G.add_node("net:I2C_SDA", type="net", net_name="I2C_SDA")
    G.add_node("net:VCC_3V3", type="net", net_name="VCC_3V3", is_power_symbol_connected=True)
    G.add_node("net:GND", type="net", net_name="GND", is_power_symbol_connected=False)
    
    # 建立 Component 節點
    G.add_node("comp:R1", type="component", ref_des="R1", category="Passive", sub_category="Resistor", functional_role="None")
    G.add_node("comp:U1", type="component", ref_des="U1", category="IC", sub_category="Microcontroller")
    
    # 連接邊 (模擬引腳連線)
    G.add_edge("comp:U1", "net:I2C_SDA", pin_name="SDA")
    G.add_edge("comp:R1", "net:I2C_SDA", pin_name="1")
    G.add_edge("comp:R1", "net:VCC_3V3", pin_name="2")
    
    return G

def test_topology_engine_execution(mock_graph):
    engine = TopologyPatternEngine()
    engine.execute(mock_graph)
    
    # 驗證 PowerPattern (VCC_3V3 應該被標為 is_power, 因為有 is_power_symbol_connected)
    assert "net:VCC_3V3" in mock_graph.nodes
    vcc_data = mock_graph.nodes["net:VCC_3V3"]
    assert vcc_data.get("is_power") is True
    assert vcc_data.get("is_ground") is not True


def test_topology_engine_power_and_ground_separation():
    G = nx.Graph()
    G.add_node("net:VCC3P3", type="net", net_name="VCC3P3", is_power_symbol_connected=True, is_ground_symbol_connected=False)
    G.add_node("net:GND", type="net", net_name="GND", is_power_symbol_connected=False, is_ground_symbol_connected=True)
    G.add_node("net:+1.8V_AUX", type="net", net_name="+1.8V_AUX", is_power_symbol_connected=True, is_ground_symbol_connected=False)
    G.add_node("net:+1P35V_PD_LDO", type="net", net_name="+1P35V_PD_LDO", is_power_symbol_connected=True, is_ground_symbol_connected=False)
    G.add_node("net:NC", type="net", net_name="NC", is_power_symbol_connected=False, is_ground_symbol_connected=False)

    engine = TopologyPatternEngine()
    engine.execute(G)

    # VCC3P3
    assert G.nodes["net:VCC3P3"].get("is_power") is True
    assert G.nodes["net:VCC3P3"].get("is_ground") is not True

    # GND
    assert G.nodes["net:GND"].get("is_ground") is True
    assert G.nodes["net:GND"].get("is_power") is not True

    # +1.8V_AUX (小數點電壓)
    assert G.nodes["net:+1.8V_AUX"].get("is_power") is True
    assert G.nodes["net:+1.8V_AUX"].get("is_ground") is not True

    # +1P35V_PD_LDO (P 表記電壓)
    assert G.nodes["net:+1P35V_PD_LDO"].get("is_power") is True
    assert G.nodes["net:+1P35V_PD_LDO"].get("is_ground") is not True

    # NC (非電源非接地)
    assert G.nodes["net:NC"].get("is_power") is not True
    assert G.nodes["net:NC"].get("is_ground") is not True


def test_topology_engine_dual_connected_short_circuit_retention():
    """驗證當一條 net 確實同時連接了 Power Symbol 與 Ground Symbol 時，兩者特性皆必須被保留以供 DRC 短路告警"""
    G = nx.Graph()
    G.add_node(
        "net:VCC_SHORT_GND",
        type="net",
        net_name="VCC_SHORT_GND",
        is_power_symbol_connected=True,
        is_ground_symbol_connected=True
    )

    engine = TopologyPatternEngine()
    engine.execute(G)

    node = G.nodes["net:VCC_SHORT_GND"]
    # 核心驗證：同時具備電源與接地特性！
    assert node.get("is_power") is True
    assert node.get("is_ground") is True

    # 驗證語意層分類推論
    from backend.app.engine.net_classifier import classify_single_net_heuristic
    heur = classify_single_net_heuristic(G, "net:VCC_SHORT_GND")
    assert heur["net_type"] == "Power_GND_Conflict"
    assert "Power" in heur["net_types"]
    assert "Ground" in heur["net_types"]
    assert heur["functional_role"] == "Power_Ground_Short"
    assert "conflict:power_ground_short" in heur["evidence"]


def test_topology_engine_signals_and_differential_pairs():
    """驗證新擴充之 signals YAML 規則 (差分對、JTAG、SPI、時脈、電源控制) 正常執行與極性推導"""
    G = nx.Graph()
    G.add_node("net:TCP0_RT_SSTX0_P", type="net", net_name="TCP0_RT_SSTX0_P")
    G.add_node("net:TCP0_RT_SSTX0_N", type="net", net_name="TCP0_RT_SSTX0_N")
    G.add_node("net:DG_JBR0_TCK", type="net", net_name="DG_JBR0_TCK")
    G.add_node("net:DG_EE_DI", type="net", net_name="DG_EE_DI")
    G.add_node("net:EN_1P8V", type="net", net_name="EN_1P8V")
    G.add_node("net:AN_JBR0_25M_XO", type="net", net_name="AN_JBR0_25M_XO")

    # 確保重載規則
    TopologyPatternEngine._instance = None
    engine = TopologyPatternEngine()
    engine.execute(G)

    # 1. 差分對極性與配對夥伴
    p_node = G.nodes["net:TCP0_RT_SSTX0_P"]
    n_node = G.nodes["net:TCP0_RT_SSTX0_N"]
    assert p_node.get("net_type") == "Differential"
    assert p_node.get("diff_polarity") == "P"
    assert p_node.get("diff_pair_partner") == "TCP0_RT_SSTX0_N"

    assert n_node.get("net_type") == "Differential"
    assert n_node.get("diff_polarity") == "N"
    assert n_node.get("diff_pair_partner") == "TCP0_RT_SSTX0_P"

    # 2. JTAG 匯流排
    jtag_node = G.nodes["net:DG_JBR0_TCK"]
    assert jtag_node.get("is_bus") is True
    assert jtag_node.get("bus_type") == "JTAG"

    # 3. SPI 匯流排
    spi_node = G.nodes["net:DG_EE_DI"]
    assert spi_node.get("is_bus") is True
    assert spi_node.get("bus_type") == "SPI"

    # 4. 電源致能控制
    en_node = G.nodes["net:EN_1P8V"]
    assert en_node.get("net_type") == "Control"
    assert en_node.get("functional_role") == "Power_Enable"

    # 5. 晶振時脈
    clk_node = G.nodes["net:AN_JBR0_25M_XO"]
    assert clk_node.get("net_type") == "Clock"
    assert clk_node.get("functional_role") == "Clock"


def test_topology_engine_fixture_ambiguity_reduction():
    """回歸測試：驗證真實 209 條 net fixture 中，落入 LLM 的模糊網路從 112 條大幅降至 10 條以下"""
    import os
    from backend.app.engine.parser import parse_orcad_xml, parse_allegro_netlist, merge_schematic_data
    from backend.app.engine.graph import build_schematic_graph
    from backend.app.engine.net_classifier import classify_single_net_heuristic

    xml_path = 'backend/tests/fixtures/sch/cartern-sch-si-20260817.xml'
    netlist_path = 'backend/tests/fixtures/sch/allegro/pstxnet.dat'

    xml_data = parse_orcad_xml(xml_path)
    netlist_data = parse_allegro_netlist(netlist_path) if os.path.exists(netlist_path) else None
    merged = merge_schematic_data(xml_data, netlist_data)
    G = build_schematic_graph(merged)

    TopologyPatternEngine._instance = None
    engine = TopologyPatternEngine()
    engine.execute(G)

    ambiguous_count = 0
    for net_node in [n for n, d in G.nodes(data=True) if d.get('type') == 'net']:
        heur = classify_single_net_heuristic(G, net_node)
        if heur.get('confidence', 0.0) < 0.6:
            ambiguous_count += 1

    # 驗證絕大多數常規網路皆在本地確定性解決，模糊網路 <= 10
    assert ambiguous_count <= 10, f"Ambiguous nets count ({ambiguous_count}) exceeds threshold (10)"


