"""
節點四維度分類器與核心元件識別單元測試 (Node Classifier & Key Components Tests)
"""

import networkx as nx
import pytest

from backend.app.engine.classifier import (
    classify_single_component_heuristic,
    classify_components_batch
)
from backend.app.engine.parser import (
    parse_orcad_xml,
    parse_allegro_netlist,
    merge_schematic_data
)
from backend.app.engine.graph import (
    build_schematic_graph,
    get_electrical_subgraph,
    identify_key_components
)

FIXTURE_XML = "backend/tests/fixtures/sch/cartern-sch-si-20260817.xml"
FIXTURE_NETLIST = "backend/tests/fixtures/sch/allegro/pstxnet.dat"


def test_classifier_non_electrical_filtering():
    """驗證螺絲、固定孔、光學點、測試探針與 SIM 測試點正確識別為 NonElectrical"""
    # 螺絲
    nut = classify_single_component_heuristic(ref="NUT1", val="Screw_4", desc="Screw,Diameter:4mm", pins_count=1)
    assert nut["category"] == "NonElectrical"
    assert nut["sub_category"] == "Mechanical"
    assert nut["is_electrical"] is False

    # 光學對位點
    fm = classify_single_component_heuristic(ref="FM1", val="MTG/ID4/OD7", desc="", package="FD55_CROSS", pins_count=1)
    assert fm["category"] == "NonElectrical"
    assert fm["sub_category"] == "Fiducial"
    assert fm["is_electrical"] is False

    # 固定孔
    mtg = classify_single_component_heuristic(ref="MTG1", val="Mounting Hole", desc="Mounting Hole,Circle", pins_count=11)
    assert mtg["category"] == "NonElectrical"
    assert mtg["sub_category"] == "MountingHole"
    assert mtg["is_electrical"] is False

    # 測試探針點
    ttp = classify_single_component_heuristic(ref="TTP1", val="probe", desc="TP,TPC32T", package="tpc26b_50", pins_count=1)
    assert ttp["category"] == "NonElectrical"
    assert ttp["sub_category"] == "TestPoint"
    assert ttp["is_electrical"] is False

    # SIM 測試 Pad
    e31 = classify_single_component_heuristic(ref="E31", val="test for SIM_7PIN", desc="SIM Test", pins_count=7)
    assert e31["category"] == "NonElectrical"
    assert e31["sub_category"] == "TestPoint"
    assert e31["is_electrical"] is False

    # 驗證即使零件編號具有誤導性 (如 U999 標記螺絲、R888 標記固定孔、J777 標記探針)，依然 100% 依據元數據正確判定
    fake_ref_screw = classify_single_component_heuristic(ref="U999", val="Screw_4", desc="Screw,Diameter:4mm", pins_count=1)
    assert fake_ref_screw["category"] == "NonElectrical"
    assert fake_ref_screw["is_electrical"] is False

    fake_ref_mtg = classify_single_component_heuristic(ref="R888", val="DFT_NP81", desc="MTG,HOLE,ID4,OD4,NPTH", package="118MIL-TOOLINGHOLE", pins_count=1)
    assert fake_ref_mtg["category"] == "NonElectrical"
    assert fake_ref_mtg["is_electrical"] is False

    fake_ref_probe = classify_single_component_heuristic(ref="J777", val="probe", desc="", package="tpc26b_50", pins_count=1)
    assert fake_ref_probe["category"] == "NonElectrical"
    assert fake_ref_probe["is_electrical"] is False


def test_classifier_power_domain_passives_and_ics():
    """驗證功率域 P 前綴元件 (PU, PC, PR, PL, PQ, PFB) 不再被誤殺為 Connector"""
    # PU 電源 IC
    pu400 = classify_single_component_heuristic(
        ref="PU400", val="AOZ13984DI-02", desc="IC,ECPower 20V 33mohm Smart Protection", pins_count=11
    )
    assert pu400["category"] == "IC"
    assert pu400["sub_category"] == "PowerIC"
    assert pu400["functional_role"] == "Power_Source"
    assert pu400["is_electrical"] is True

    # PC 功率電容
    pc500 = classify_single_component_heuristic(
        ref="PC500", val="100nF_X7R_10V", desc="CAP,100nF,+/-10%,X7R,10V", pins_count=2
    )
    assert pc500["category"] == "Passive"
    assert pc500["sub_category"] == "Capacitor"
    assert pc500["is_electrical"] is True

    # PR 功率電阻
    pr502 = classify_single_component_heuristic(
        ref="PR502", val="100K_5%", desc="RES,100K Ohm,+/-5%", pins_count=2
    )
    assert pr502["category"] == "Passive"
    assert pr502["sub_category"] == "Resistor"
    assert pr502["is_electrical"] is True

    # PL 功率電感
    pl100 = classify_single_component_heuristic(
        ref="PL100", val="1.0uH_4.8A", desc="Chip Inductor,1.0uH@1MHz", pins_count=2
    )
    assert pl100["category"] == "Passive"
    assert pl100["sub_category"] == "Inductor"
    assert pl100["functional_role"] == "Filter"
    assert pl100["is_electrical"] is True

    # PFB 功率磁珠
    pfb100 = classify_single_component_heuristic(
        ref="PFB100", val="30_1.7A", desc="FB,30 Ohm@100MHz", pins_count=2
    )
    assert pfb100["category"] == "Passive"
    assert pfb100["sub_category"] == "FerriteBead"
    assert pfb100["functional_role"] == "Filter"
    assert pfb100["is_electrical"] is True

    # PQ 功率 MOSFET
    pq501 = classify_single_component_heuristic(
        ref="PQ501", val="AOSS21115C", desc="MOS P,AOSS21115C,Vdss=-20V", pins_count=3
    )
    assert pq501["category"] == "Discrete"
    assert pq501["sub_category"] == "MOSFET"
    assert pq501["is_electrical"] is True


def test_real_fixture_key_components_and_centrality():
    """使用真實線路圖驗證核心元件識別與絕不造假原則"""
    xml_data = parse_orcad_xml(FIXTURE_XML)
    netlist_data = parse_allegro_netlist(FIXTURE_NETLIST)
    merged = merge_schematic_data(xml_data, netlist_data)
    G = build_schematic_graph(merged)

    # 驗證電氣子圖
    subG = get_electrical_subgraph(G)
    assert len(subG) < len(G)
    assert "comp:NUT1" not in subG
    assert "comp:FM1" not in subG
    assert "comp:TTP1" not in subG
    assert "comp:TU10" in subG

    # 執行核心元件與角色識別
    res = identify_key_components(G)
    key_ics = res["key_ics"]
    key_connectors = res["key_connectors"]
    ic_dir = res["ic_directory_by_role"]
    non_elec = res["non_electrical_components"]

    # 1. 核心 IC：TU1 (June Bridge) 與 TU10 (PTPS66994)
    assert any("TU1" in ic for ic in key_ics)
    assert any("TU10" in ic for ic in key_ics)
    # 絕不應包含螺絲或探針
    assert not any("NUT" in ic or "TTP" in ic or "FM" in ic for ic in key_ics)

    # 2. 關鍵連接器：TJ1 (Type-C) 與 P72 (BTB 120P)
    assert any("TJ1" in conn for conn in key_connectors)
    assert any("P72" in conn for conn in key_connectors)

    # 3. 角色目錄精準分組
    assert "Bus_Master" in ic_dir
    assert any("TU1" in ic for ic in ic_dir["Bus_Master"])
    assert "Power_Source" in ic_dir
    assert any("TU10" in ic for ic in ic_dir["Power_Source"])
    assert any("PU400" in ic for ic in ic_dir["Power_Source"])
    assert "Level_Shifter" in ic_dir
    assert any("TU12" in ic for ic in ic_dir["Level_Shifter"])

    # 4. 非電氣件計數與名單
    assert len(non_elec) >= 60


def test_empty_graph_returns_empty_and_no_fake_data():
    """驗證當圖譜中無主晶片時，核心清單回傳空清單，絕不虛構 U1 (STM32F4)"""
    empty_G = nx.Graph()
    # 僅放一顆電阻
    empty_G.add_node("comp:R1", type="component", ref_des="R1", category="Passive", sub_category="Resistor", is_electrical=True)
    empty_G.add_node("net:VCC", type="net", net_name="VCC")
    empty_G.add_edge("comp:R1", "net:VCC")

    res = identify_key_components(empty_G)
    assert res["key_ics"] == []
    assert res["key_connectors"] == []
    assert res["ic_directory_by_role"] == {}
