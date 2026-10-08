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

