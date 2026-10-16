"""
差分通道導通與串聯元件完整性檢查單元測試 (Differential Channel Continuity DRC Unit Tests)
"""

import os
import pytest
import networkx as nx

from designshield.sdk import (
    RuleResult,
    RulePass,
    RuleViolation,
    RuleContext,
    GraphAPI,
    PartDB,
    SandboxedScriptRunner,
)


def _load_script_code() -> str:
    script_path = "patterns/rules/interfaces/differential_channel_continuity_check.py"
    with open(script_path, "r", encoding="utf-8") as f:
        return f.read()


def test_differential_channel_continuity_all_mounted_pass():
    """
    測試場景 1：全數上件 (PASS)
    兩端端點 (U1 ↔ J1) 皆上件，中間串聯 AC 耦合電容 (C1, C2) 皆上件，
    通道電氣訊號完整導通，判定 PASS。
    """
    G = nx.Graph()

    # 端點
    G.add_node("comp:U1", type="component", ref_des="U1", category="IC", sub_category="Microcontroller", part_value="MCU", is_mounted=True)
    G.add_node("comp:J1", type="component", ref_des="J1", category="Connector", sub_category="USB_Connector", part_value="TYPEC", is_mounted=True)

    # 串聯 AC 耦合電容 (皆上件)
    G.add_node("comp:C1", type="component", ref_des="C1", category="Passive", sub_category="Capacitor", functional_role="AC_Coupling_Capacitor", part_value="100nF", is_mounted=True)
    G.add_node("comp:C2", type="component", ref_des="C2", category="Passive", sub_category="Capacitor", functional_role="AC_Coupling_Capacitor", part_value="100nF", is_mounted=True)

    # 網路
    G.add_node("net:USB_DP", type="net", net_name="USB_DP", bus_type="USB", net_type="Differential", diff_polarity="P", diff_pair_partner="USB_DM")
    G.add_node("net:USB_DP_C", type="net", net_name="USB_DP_C", bus_type="USB", net_type="Differential", diff_polarity="P")
    G.add_node("net:USB_DM", type="net", net_name="USB_DM", bus_type="USB", net_type="Differential", diff_polarity="N", diff_pair_partner="USB_DP")
    G.add_node("net:USB_DM_C", type="net", net_name="USB_DM_C", bus_type="USB", net_type="Differential", diff_polarity="N")

    # P 軌道連線: U1 -> USB_DP -> C1 -> USB_DP_C -> J1
    G.add_edge("comp:U1", "net:USB_DP", pin_name="DP", pin_number="1")
    G.add_edge("comp:C1", "net:USB_DP", pin_name="1", pin_number="1")
    G.add_edge("comp:C1", "net:USB_DP_C", pin_name="2", pin_number="2")
    G.add_edge("comp:J1", "net:USB_DP_C", pin_name="DP", pin_number="A6")

    # N 軌道連線: U1 -> USB_DM -> C2 -> USB_DM_C -> J1
    G.add_edge("comp:U1", "net:USB_DM", pin_name="DM", pin_number="2")
    G.add_edge("comp:C2", "net:USB_DM", pin_name="1", pin_number="1")
    G.add_edge("comp:C2", "net:USB_DM_C", pin_name="2", pin_number="2")
    G.add_edge("comp:J1", "net:USB_DM_C", pin_name="DM", pin_number="A7")

    api = GraphAPI(G)
    code = _load_script_code()

    ctx = RuleContext(target=api._G.nodes["net:USB_DP"])
    res = SandboxedScriptRunner.execute_script_source(code, context=ctx, graph_api=api, part_db=PartDB())

    assert isinstance(res, RulePass), f"預期 RulePass，實際得到 {res}"
    assert "U1" in res.evidence["channel_title"] and "J1" in res.evidence["channel_title"]
    assert "->" in res.evidence["channel_title"]
    assert "topology" in res.evidence
    assert len(res.evidence["topology"]["connections"]) > 0
    assert "電氣訊號完整導通" in res.evidence["audit_summary"]
    assert "C1" in res.evidence["pass_through_components"]
    assert "C2" in res.evidence["pass_through_components"]


def test_differential_channel_continuity_unmounted_cap_error():
    """
    測試場景 2：兩端端點上件，但途中串聯 AC 耦合電容未上件 (ERROR)
    兩端端點 (U1 ↔ J1) 皆上件，但 C1 標記為未上件 (is_mounted=False)，
    造成差分訊號開路中斷，判定為 ERROR。
    """
    G = nx.Graph()

    # 端點皆上件
    G.add_node("comp:U1", type="component", ref_des="U1", category="IC", sub_category="Microcontroller", part_value="MCU", is_mounted=True)
    G.add_node("comp:J1", type="component", ref_des="J1", category="Connector", sub_category="USB_Connector", part_value="TYPEC", is_mounted=True)

    # 串聯電容：C1 未上件，C2 已上件
    G.add_node("comp:C1", type="component", ref_des="C1", category="Passive", sub_category="Capacitor", functional_role="AC_Coupling_Capacitor", part_value="100nF", is_mounted=False, bom="NI", bom_status="UNMOUNTED")
    G.add_node("comp:C2", type="component", ref_des="C2", category="Passive", sub_category="Capacitor", functional_role="AC_Coupling_Capacitor", part_value="100nF", is_mounted=True)

    # 網路
    G.add_node("net:USB_DP", type="net", net_name="USB_DP", bus_type="USB", net_type="Differential", diff_polarity="P", diff_pair_partner="USB_DM")
    G.add_node("net:USB_DP_C", type="net", net_name="USB_DP_C", bus_type="USB", net_type="Differential", diff_polarity="P")
    G.add_node("net:USB_DM", type="net", net_name="USB_DM", bus_type="USB", net_type="Differential", diff_polarity="N", diff_pair_partner="USB_DP")
    G.add_node("net:USB_DM_C", type="net", net_name="USB_DM_C", bus_type="USB", net_type="Differential", diff_polarity="N")

    # 連線
    G.add_edge("comp:U1", "net:USB_DP", pin_name="DP", pin_number="1")
    G.add_edge("comp:C1", "net:USB_DP", pin_name="1", pin_number="1")
    G.add_edge("comp:C1", "net:USB_DP_C", pin_name="2", pin_number="2")
    G.add_edge("comp:J1", "net:USB_DP_C", pin_name="DP", pin_number="A6")

    G.add_edge("comp:U1", "net:USB_DM", pin_name="DM", pin_number="2")
    G.add_edge("comp:C2", "net:USB_DM", pin_name="1", pin_number="1")
    G.add_edge("comp:C2", "net:USB_DM_C", pin_name="2", pin_number="2")
    G.add_edge("comp:J1", "net:USB_DM_C", pin_name="DM", pin_number="A7")

    api = GraphAPI(G)
    code = _load_script_code()

    ctx = RuleContext(target=api._G.nodes["net:USB_DP"])
    res = SandboxedScriptRunner.execute_script_source(code, context=ctx, graph_api=api, part_db=PartDB())

    assert isinstance(res, list), f"預期違規清單，實際得到 {res}"
    assert len(res) == 1
    violation = res[0]
    assert violation.severity == "ERROR"
    assert "C1 [X]" in violation.error_message
    assert "電氣開路中斷" in violation.error_message
    assert violation.evidence["faulty_component"] == "C1"
    assert violation.evidence["is_mounted"] is False


def test_differential_channel_continuity_unmounted_choke_error():
    """
    測試場景 3：兩端端點上件，但途中穿透之共模扼流圈 CMC 未上件 (ERROR)
    """
    G = nx.Graph()

    G.add_node("comp:U1", type="component", ref_des="U1", category="IC", sub_category="Microcontroller", part_value="MCU", is_mounted=True)
    G.add_node("comp:J1", type="component", ref_des="J1", category="Connector", sub_category="USB_Connector", part_value="TYPEC", is_mounted=True)

    # 串聯共模扼流圈 TL1 (未上件)
    G.add_node(
        "comp:TL1",
        type="component",
        ref_des="TL1",
        mfg="MURATA",
        mfg_pn="DLM0NSN900HY2D",
        category="Passive",
        sub_category="Choke",
        functional_role="Common_Mode_Choke",
        is_electrical=True,
        part_value="DLM0NSN900HY2D",
        is_mounted=False,
        bom="NI",
        bom_status="UNMOUNTED"
    )

    G.add_node("net:USB_DP", type="net", net_name="USB_DP", bus_type="USB", net_type="Differential", diff_polarity="P", diff_pair_partner="USB_DM")
    G.add_node("net:USB_DP_FLT", type="net", net_name="USB_DP_FLT", bus_type="USB", net_type="Differential", diff_polarity="P")
    G.add_node("net:USB_DM", type="net", net_name="USB_DM", bus_type="USB", net_type="Differential", diff_polarity="N", diff_pair_partner="USB_DP")
    G.add_node("net:USB_DM_FLT", type="net", net_name="USB_DM_FLT", bus_type="USB", net_type="Differential", diff_polarity="N")

    # TL1 穿透連線 (Murata DLM0NSN900HY2D: Pin 1 穿透至 Pin 2; Pin 3 穿透至 Pin 4)
    G.add_edge("comp:U1", "net:USB_DP", pin_name="DP", pin_number="1")
    G.add_edge("comp:TL1", "net:USB_DP", pin_name="1", pin_number="1")
    G.add_edge("comp:TL1", "net:USB_DP_FLT", pin_name="2", pin_number="2")
    G.add_edge("comp:J1", "net:USB_DP_FLT", pin_name="DP", pin_number="A6")

    G.add_edge("comp:U1", "net:USB_DM", pin_name="DM", pin_number="2")
    G.add_edge("comp:TL1", "net:USB_DM", pin_name="3", pin_number="3")
    G.add_edge("comp:TL1", "net:USB_DM_FLT", pin_name="4", pin_number="4")
    G.add_edge("comp:J1", "net:USB_DM_FLT", pin_name="DM", pin_number="A7")

    api = GraphAPI(G)
    code = _load_script_code()

    ctx = RuleContext(target=api._G.nodes["net:USB_DP"])
    res = SandboxedScriptRunner.execute_script_source(code, context=ctx, graph_api=api, part_db=PartDB())

    assert isinstance(res, list)
    assert len(res) == 1
    assert res[0].severity == "ERROR"
    assert "TL1 [X]" in res[0].error_message
    assert "開路中斷" in res[0].error_message


def test_differential_channel_continuity_endpoint_unmounted_safe_pass():
    """
    測試場景 4：端點元件未上件時安全略過 (PASS)
    當差分通道端點元件（如連接器 J1 或從晶片）在該 BOM 配置下標註為未上件 (is_mounted=False)，
    代表該通道未啟用，即使中間串聯電容亦未上件，也不構成致命開路，安全略過。
    """
    G = nx.Graph()

    # 主晶片已上件，但從端點 J1 未上件
    G.add_node("comp:U1", type="component", ref_des="U1", category="IC", sub_category="Microcontroller", part_value="MCU", is_mounted=True)
    G.add_node("comp:J1", type="component", ref_des="J1", category="Connector", sub_category="USB_Connector", part_value="TYPEC", is_mounted=False, bom="NI", bom_status="UNMOUNTED")

    # 串聯電容未上件
    G.add_node("comp:C1", type="component", ref_des="C1", category="Passive", sub_category="Capacitor", functional_role="AC_Coupling_Capacitor", part_value="100nF", is_mounted=False)

    G.add_node("net:USB_DP", type="net", net_name="USB_DP", bus_type="USB", net_type="Differential", diff_polarity="P", diff_pair_partner="USB_DM")
    G.add_node("net:USB_DP_C", type="net", net_name="USB_DP_C", bus_type="USB", net_type="Differential", diff_polarity="P")
    G.add_node("net:USB_DM", type="net", net_name="USB_DM", bus_type="USB", net_type="Differential", diff_polarity="N", diff_pair_partner="USB_DP")

    G.add_edge("comp:U1", "net:USB_DP", pin_name="DP", pin_number="1")
    G.add_edge("comp:C1", "net:USB_DP", pin_name="1", pin_number="1")
    G.add_edge("comp:C1", "net:USB_DP_C", pin_name="2", pin_number="2")
    G.add_edge("comp:J1", "net:USB_DP_C", pin_name="DP", pin_number="A6")

    G.add_edge("comp:U1", "net:USB_DM", pin_name="DM", pin_number="2")
    G.add_edge("comp:J1", "net:USB_DM", pin_name="DM", pin_number="A7")

    api = GraphAPI(G)
    code = _load_script_code()

    ctx = RuleContext(target=api._G.nodes["net:USB_DP"])
    res = SandboxedScriptRunner.execute_script_source(code, context=ctx, graph_api=api, part_db=PartDB())

    assert isinstance(res, RulePass)
    assert "未處於啟用工作狀態" in res.evidence["audit_summary"]
    assert "J1 [X]" in res.evidence["audit_summary"]


@pytest.mark.anyio
async def test_differential_channel_continuity_real_fixture():
    """
    測試場景 5：在真實測試板 (cartern-sch-si-20260817.xml) 上執行 differential_channel_continuity_check
    驗證規則腳本可正常執行無異常。
    """
    from backend.app.engine.parser import parse_orcad_xml, parse_allegro_netlist, merge_schematic_data
    from backend.app.engine.graph import build_schematic_graph, create_config_subgraph
    from backend.app.engine.pattern_engine.topology_engine import TopologyPatternEngine

    xml_path = "backend/tests/fixtures/sch/cartern-sch-si-20260817.xml"
    netlist_path = "backend/tests/fixtures/sch/allegro/pstxnet.dat"

    xml_data = parse_orcad_xml(xml_path)
    netlist_data = parse_allegro_netlist(netlist_path)
    merged = merge_schematic_data(xml_data, netlist_data)
    G = build_schematic_graph(merged)

    TopologyPatternEngine.get_instance().reload()
    TopologyPatternEngine.get_instance().execute(G)

    sub_g = create_config_subgraph(G, config_index=0, is_mp_mode=False)
    api = GraphAPI(sub_g)
    code = _load_script_code()

    # 測試以 TCP0_RT_SSRX1_P 為目標執行
    ctx = RuleContext(target=sub_g.nodes["net:TCP0_RT_SSRX1_P"])
    res = SandboxedScriptRunner.execute_script_source(code, context=ctx, graph_api=api, part_db=PartDB())

    assert res is not None
    if isinstance(res, list):
        for v in res:
            assert v.severity in ["ERROR", "WARNING", "INFO"]
    else:
        assert isinstance(res, RulePass)


@pytest.mark.anyio
async def test_differential_channel_continuity_coupon_testpoint_topology():
    """
    測試場景 6：驗證測試點/Coupon 差分線 (L1_85_MS_5INCH_P_DL4) 具有完整的 E33 -> E34 通道標題與拓撲輸出
    """
    from backend.app.engine.parser import parse_orcad_xml, parse_allegro_netlist, merge_schematic_data
    from backend.app.engine.graph import build_schematic_graph, create_config_subgraph
    from backend.app.engine.pattern_engine.topology_engine import TopologyPatternEngine

    xml_path = "backend/tests/fixtures/sch/cartern-sch-si-20260817.xml"
    netlist_path = "backend/tests/fixtures/sch/allegro/pstxnet.dat"

    xml_data = parse_orcad_xml(xml_path)
    netlist_data = parse_allegro_netlist(netlist_path)
    merged = merge_schematic_data(xml_data, netlist_data)
    G = build_schematic_graph(merged)

    sub_g = create_config_subgraph(G, config_index=0, is_mp_mode=False)
    api = GraphAPI(sub_g)
    code = _load_script_code()

    ctx = RuleContext(target=sub_g.nodes["net:L1_85_MS_5INCH_P_DL4"])
    res = SandboxedScriptRunner.execute_script_source(code, context=ctx, graph_api=api, part_db=PartDB())

    assert isinstance(res, RulePass)
    assert "channel_title" in res.evidence
    assert "E33 -> E34" in res.evidence["channel_title"]
    assert "topology" in res.evidence
    topo = res.evidence["topology"]
    node_refs = [n["ref_des"] for n in topo["nodes"]]
    assert "E33" in node_refs
    assert "E34" in node_refs
    assert len(topo["connections"]) == 2  # P 軌與 N 軌直連


def test_differential_channel_continuity_multi_drop_ddr_topology():
    """
    測試場景 7：驗證多端點直連差分通道 (如 CPU XU1 驅動雙 DIMM 插槽 XMM1, XMM2)
    1 對多發散扇出拓撲與逗號分隔路徑標題
    """
    G = nx.Graph()
    # 建立 CPU Socket XU1
    G.add_node(
        "comp:XU1",
        type="component",
        ref_des="XU1",
        category="Connector",
        sub_category="Socket",
        mfg_pn="PE19547-11NK0-1H",
        part_value="Socket_LGA 1954_15u_Black",
        is_electrical=True,
        is_mounted=True,
        bom="I"
    )
    # 建立雙 DIMM 插槽 XMM1, XMM2
    G.add_node(
        "comp:XMM1",
        type="component",
        ref_des="XMM1",
        category="Connector",
        sub_category="Connector",
        mfg_pn="ATF8787-82B10-2H",
        part_value="UDIMM_287P_15u_Black",
        is_electrical=True,
        is_mounted=True,
        bom="I"
    )
    G.add_node(
        "comp:XMM2",
        type="component",
        ref_des="XMM2",
        category="Connector",
        sub_category="Connector",
        mfg_pn="ATF8787-82W20-2H",
        part_value="UDIMM_287P_15u_Natural",
        is_electrical=True,
        is_mounted=True,
        bom="I"
    )

    # 建立差分對網段
    G.add_node("net:M_B_DDR1_DQS0_DP", type="net", net_name="M_B_DDR1_DQS0_DP", bus_type="DDR", net_type="Differential", diff_polarity="P", diff_pair_partner="M_B_DDR1_DQS0_DN")
    G.add_node("net:M_B_DDR1_DQS0_DN", type="net", net_name="M_B_DDR1_DQS0_DN", bus_type="DDR", net_type="Differential", diff_polarity="N", diff_pair_partner="M_B_DDR1_DQS0_DP")

    # XU1 -> P: AL47, N: AK48
    G.add_edge("comp:XU1", "net:M_B_DDR1_DQS0_DP", pin_name="AL47", pin_number="AL47")
    G.add_edge("comp:XU1", "net:M_B_DDR1_DQS0_DN", pin_name="AK48", pin_number="AK48")

    # XMM1 -> P: 14, N: 13
    G.add_edge("comp:XMM1", "net:M_B_DDR1_DQS0_DP", pin_name="14", pin_number="14")
    G.add_edge("comp:XMM1", "net:M_B_DDR1_DQS0_DN", pin_name="13", pin_number="13")

    # XMM2 -> P: 14, N: 13
    G.add_edge("comp:XMM2", "net:M_B_DDR1_DQS0_DP", pin_name="14", pin_number="14")
    G.add_edge("comp:XMM2", "net:M_B_DDR1_DQS0_DN", pin_name="13", pin_number="13")

    api = GraphAPI(G)
    code = _load_script_code()

    ctx = RuleContext(target=api._G.nodes["net:M_B_DDR1_DQS0_DP"])
    res = SandboxedScriptRunner.execute_script_source(code, context=ctx, graph_api=api, part_db=PartDB())

    assert isinstance(res, RulePass)
    assert "channel_title" in res.evidence
    # 斷言標題以 XU1 為源端，多目標以逗號展開
    assert "XU1 -> XMM1, XMM2" in res.evidence["channel_title"]
    assert "topology" in res.evidence
    topo = res.evidence["topology"]

    # 斷言 3 個端點皆被收錄
    node_refs = [n["ref_des"] for n in topo["nodes"]]
    assert set(node_refs) == {"XU1", "XMM1", "XMM2"}

    # 斷言產生 4 條連線 (P/N 軌各 2 條，由 XU1 扇出至 XMM1 與 XMM2)
    connections = topo["connections"]
    assert len(connections) == 4

    p_conns = [c for c in connections if c["rail_id"] == "p_rail"]
    n_conns = [c for c in connections if c["rail_id"] == "n_rail"]
    assert len(p_conns) == 2
    assert len(n_conns) == 2

    assert all(c["from_node"] == "XU1" for c in connections)
    assert {c["to_node"] for c in p_conns} == {"XMM1", "XMM2"}
    assert {c["to_node"] for c in n_conns} == {"XMM1", "XMM2"}


