"""
網路語意推斷與模糊 LLM 分類器單元測試 (Net Classifier & Semantic Inference Tests)
"""

import os
from unittest.mock import patch, MagicMock
import networkx as nx
import pytest

from backend.app.engine.parser import (
    parse_orcad_xml,
    parse_allegro_netlist,
    merge_schematic_data,
)
from backend.app.engine.graph import build_schematic_graph
from backend.app.engine.pattern_engine.topology_engine import TopologyPatternEngine
from backend.app.engine.net_classifier import (
    classify_single_net_heuristic,
    classify_nets_batch,
)

FIXTURE_XML = "backend/tests/fixtures/sch/cartern-sch-si-20260817.xml"
FIXTURE_NETLIST = "backend/tests/fixtures/sch/allegro/pstxnet.dat"


def test_classify_single_net_heuristic():
    """驗證單一網路之確定性啟發式分類"""
    G = nx.Graph()
    G.add_node("net:VCC3V3", type="net", net_name="VCC3V3", is_power=True, is_ground=False)
    G.add_node("net:GND", type="net", net_name="GND", is_power=False, is_ground=True)
    G.add_node("net:I2C1_SDA", type="net", net_name="I2C1_SDA", is_bus=True, bus_type="I2C", bus_confidence=0.92)
    G.add_node("net:SYS_RESET_N", type="net", net_name="SYS_RESET_N", is_power=False, is_ground=False)
    G.add_node("net:CLK_24M", type="net", net_name="CLK_24M", is_power=False, is_ground=False)
    G.add_node("net:MY_SIGNAL", type="net", net_name="MY_SIGNAL", is_power=False, is_ground=False)

    pwr = classify_single_net_heuristic(G, "net:VCC3V3")
    assert pwr["net_type"] == "Power"
    assert pwr["confidence"] >= 0.95

    gnd = classify_single_net_heuristic(G, "net:GND")
    assert gnd["net_type"] == "Ground"
    assert gnd["confidence"] == 1.0

    bus = classify_single_net_heuristic(G, "net:I2C1_SDA")
    assert bus["net_type"] == "Bus"
    assert bus["bus_type"] == "I2C"
    assert bus["confidence"] >= 0.9

    rst = classify_single_net_heuristic(G, "net:SYS_RESET_N")
    assert rst["net_type"] == "Control"
    assert rst["functional_role"] == "Reset"

    clk = classify_single_net_heuristic(G, "net:CLK_24M")
    assert clk["net_type"] == "Clock"

    sig = classify_single_net_heuristic(G, "net:MY_SIGNAL")
    assert sig["net_type"] == "Signal"
    assert sig["confidence"] < 0.6


def test_classify_nets_batch_without_llm():
    """驗證批次網路評估與模糊件過濾 (無 LLM 模式)"""
    G = nx.Graph()
    G.add_node("comp:U1", type="component", ref_des="U1", category="IC")
    G.add_node("comp:U2", type="component", ref_des="U2", category="IC")
    G.add_node("net:NET_MYSTERY", type="net", net_name="NET_MYSTERY", is_power=False, is_ground=False)
    G.add_edge("comp:U1", "net:NET_MYSTERY", pin_name="TXD", pin_number="1")
    G.add_edge("comp:U2", "net:NET_MYSTERY", pin_name="RXD", pin_number="2")

    stats = classify_nets_batch(G, enable_llm_fallback=False)
    assert stats["total_nets"] == 1
    assert stats["ambiguous_nets_count"] == 1
    assert G.nodes["net:NET_MYSTERY"]["confidence"] < 0.6


def test_classify_nets_batch_with_mock_llm():
    """驗證微批次 LLM 模糊網路分類與圖譜屬性回填"""
    G = nx.Graph()
    G.add_node("comp:U1", type="component", ref_des="U1", category="IC", part_value="STM32F4")
    G.add_node("comp:U2", type="component", ref_des="U2", category="IC", part_value="CH340G")
    G.add_node("net:NET_087", type="net", net_name="NET_087", is_power=False, is_ground=False)
    G.add_edge("comp:U1", "net:NET_087", pin_name="UART1_TX", pin_number="9")
    G.add_edge("comp:U2", "net:NET_087", pin_name="RXD", pin_number="3")

    mock_llm_response = {
        "choices": [
            {
                "message": {
                    "content": """
                    [
                      {
                        "net_name": "NET_087",
                        "net_type": "Bus",
                        "bus_type": "UART",
                        "operating_voltage": 3.3,
                        "functional_role": "Single_Ended_Bus",
                        "confidence": 0.95
                      }
                    ]
                    """
                }
            }
        ]
    }

    with patch("backend.app.engine.rules.llm.call_litellm_completion", return_value=mock_llm_response):
        stats = classify_nets_batch(G, enable_llm_fallback=True)

    net_node_data = G.nodes["net:NET_087"]
    assert net_node_data["is_bus"] is True
    assert net_node_data["bus_type"] == "UART"
    assert net_node_data["confidence"] == 0.95
    assert net_node_data["operating_voltage"] == 3.3
    assert "llm_net_semantic_inference" in net_node_data["evidence"]


def test_parser_and_net_classifier_on_real_fixture():
    """使用真實樣本檢驗 OrCAD XML + Netlist + Topology + NetClassifier 全流程"""
    assert os.path.exists(FIXTURE_XML)
    assert os.path.exists(FIXTURE_NETLIST)

    xml_data = parse_orcad_xml(FIXTURE_XML)
    assert "power_symbol_nets" in xml_data
    assert len(xml_data["power_symbol_nets"]) > 0

    netlist_data = parse_allegro_netlist(FIXTURE_NETLIST)
    merged = merge_schematic_data(xml_data, netlist_data)
    assert "power_symbol_nets" in merged
    assert len(merged["power_symbol_nets"]) > 0

    G = build_schematic_graph(merged)
    assert G.number_of_nodes() > 500

    topo = TopologyPatternEngine()
    topo.execute(G)

    stats = classify_nets_batch(G, enable_llm_fallback=False)
    assert stats["total_nets"] > 200
    assert stats["power_nets"] > 0
    assert stats["ground_nets"] > 0
