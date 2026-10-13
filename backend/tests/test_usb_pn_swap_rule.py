"""
USB P/N 差分對極性反接與拓撲不對稱單元測試 (USB Differential Pair DRC Unit Tests)
"""

import os
import pytest
import networkx as nx

from designshield.sdk import (
    RuleResult,
    RuleViolation,
    RuleContext,
    GraphAPI,
    PartDB,
    SandboxedScriptRunner,
)


def test_graph_api_pin_name_and_differential_tracing():
    """測試 GraphAPI 之 get_pin_name 與 trace_differential_end_to_end"""
    G = nx.Graph()

    # 建立 U1 (Master)
    G.add_node("comp:U1", type="component", ref_des="U1", category="IC", sub_category="Microcontroller", part_value="MCU")
    # 建立 U2 (USB Connector / Receiver)
    G.add_node("comp:U2", type="component", ref_des="U2", category="IC", sub_category="InterfaceIC", part_value="USB_PHY")
    # 建立 C1, C2 (AC 耦合電容)
    G.add_node("comp:C1", type="component", ref_des="C1", category="Passive", sub_category="Capacitor", functional_role="AC_Coupling_Capacitor", part_value="100nF")
    G.add_node("comp:C2", type="component", ref_des="C2", category="Passive", sub_category="Capacitor", functional_role="AC_Coupling_Capacitor", part_value="100nF")

    # 網路
    G.add_node("net:USB_DP", type="net", net_name="USB_DP", bus_type="USB", net_type="Differential", diff_polarity="P", diff_pair_partner="USB_DM")
    G.add_node("net:USB_DP_C", type="net", net_name="USB_DP_C", bus_type="USB", net_type="Differential", diff_polarity="P")

    G.add_node("net:USB_DM", type="net", net_name="USB_DM", bus_type="USB", net_type="Differential", diff_polarity="N", diff_pair_partner="USB_DP")
    G.add_node("net:USB_DM_C", type="net", net_name="USB_DM_C", bus_type="USB", net_type="Differential", diff_polarity="N")

    # 正端連線: U1 (DP) -> USB_DP -> C1 -> USB_DP_C -> U2 (DP)
    G.add_edge("comp:U1", "net:USB_DP", pin_name="DP", pin_number="1")
    G.add_edge("comp:C1", "net:USB_DP", pin_name="1", pin_number="1")
    G.add_edge("comp:C1", "net:USB_DP_C", pin_name="2", pin_number="2")
    G.add_edge("comp:U2", "net:USB_DP_C", pin_name="DP", pin_number="5")

    # 負端連線: U1 (DM) -> USB_DM -> C2 -> USB_DM_C -> U2 (DM)
    G.add_edge("comp:U1", "net:USB_DM", pin_name="DM", pin_number="2")
    G.add_edge("comp:C2", "net:USB_DM", pin_name="1", pin_number="1")
    G.add_edge("comp:C2", "net:USB_DM_C", pin_name="2", pin_number="2")
    G.add_edge("comp:U2", "net:USB_DM_C", pin_name="DM", pin_number="6")

    api = GraphAPI(G)

    # 1. 測試 get_pin_name
    assert api.get_pin_name("comp:U1", "net:USB_DP") == "DP"
    assert api.get_pin_name("comp:U1", "net:USB_DM") == "DM"

    # 2. 測試 trace_differential_end_to_end (穿越 C1 追蹤至 U2)
    p_endpoints = api.trace_differential_end_to_end("net:USB_DP")
    assert len(p_endpoints) == 2
    ref_dess = [ep["component"].ref_des for ep in p_endpoints]
    assert "U1" in ref_dess
    assert "U2" in ref_dess

    # 3. 測試 check_differential_pair_symmetry (完全對稱)
    sym = api.check_differential_pair_symmetry("net:USB_DP", "net:USB_DM")
    assert sym["is_symmetric"] is True
    assert len(sym["asymmetry_reasons"]) == 0


def test_usb_pn_swap_rule_pass():
    """測試正常 USB 差分對連線 (PASS)"""
    G = nx.Graph()
    G.add_node("comp:U1", type="component", ref_des="U1", category="IC", sub_category="Microcontroller", part_value="MCU")
    G.add_node("comp:U2", type="component", ref_des="U2", category="IC", sub_category="Connector", part_value="TYPEC_CONN")

    G.add_node("net:USB_DP", type="net", net_name="USB_DP", bus_type="USB", net_type="Differential", diff_polarity="P", diff_pair_partner="USB_DM")
    G.add_node("net:USB_DM", type="net", net_name="USB_DM", bus_type="USB", net_type="Differential", diff_polarity="N", diff_pair_partner="USB_DP")

    G.add_edge("comp:U1", "net:USB_DP", pin_name="USB_DP")
    G.add_edge("comp:U2", "net:USB_DP", pin_name="DP")

    G.add_edge("comp:U1", "net:USB_DM", pin_name="USB_DM")
    G.add_edge("comp:U2", "net:USB_DM", pin_name="DM")

    api = GraphAPI(G)

    script_path = "patterns/rules/interfaces/usb_pn_swap_check.py"
    with open(script_path, "r", encoding="utf-8") as f:
        code = f.read()

    ctx = RuleContext(target=api._G.nodes["net:USB_DP"])
    res = SandboxedScriptRunner.execute_script_source(code, context=ctx, graph_api=api, part_db=PartDB())

    assert res == RuleResult.PASS


def test_usb_pn_swap_rule_scenario_b_swap_fault():
    """測試情境 B: 端點正負極性反接 (FAIL)"""
    G = nx.Graph()
    G.add_node("comp:U1", type="component", ref_des="U1", category="IC", sub_category="Microcontroller", part_value="MCU")
    G.add_node("comp:U2", type="component", ref_des="U2", category="IC", sub_category="InterfaceIC", part_value="PHY")

    # 正極網路 USB_DP 誤連向 U2 的 DM 引腳！
    G.add_node("net:USB_DP", type="net", net_name="USB_DP", bus_type="USB", net_type="Differential", diff_polarity="P")

    G.add_edge("comp:U1", "net:USB_DP", pin_name="USB_DP")
    G.add_edge("comp:U2", "net:USB_DP", pin_name="DM")  # 錯誤反接！

    api = GraphAPI(G)

    script_path = "patterns/rules/interfaces/usb_pn_swap_check.py"
    with open(script_path, "r", encoding="utf-8") as f:
        code = f.read()

    ctx = RuleContext(target=api._G.nodes["net:USB_DP"])
    res = SandboxedScriptRunner.execute_script_source(code, context=ctx, graph_api=api, part_db=PartDB())

    assert isinstance(res, list)
    assert len(res) == 1
    assert "極性反接" in res[0].error_message
    assert res[0].recommendation is not None
    assert res[0].severity == "ERROR"


def test_usb_pn_swap_rule_scenario_c_asymmetry_and_floating():
    """測試情境 C: 拓撲不對稱與單邊懸空 (FAIL)"""
    G = nx.Graph()
    G.add_node("comp:U1", type="component", ref_des="U1", category="IC", sub_category="Microcontroller", part_value="MCU")
    G.add_node("comp:U2", type="component", ref_des="U2", category="IC", sub_category="Connector", part_value="CONN")

    # P 端連接至 U1 與 U2，但 N 端僅連接至 U1 (U2 未連接，呈現不對稱)
    G.add_node("net:USB_DP", type="net", net_name="USB_DP", bus_type="USB", net_type="Differential", diff_polarity="P", diff_pair_partner="USB_DM")
    G.add_node("net:USB_DM", type="net", net_name="USB_DM", bus_type="USB", net_type="Differential", diff_polarity="N", diff_pair_partner="USB_DP")

    G.add_edge("comp:U1", "net:USB_DP", pin_name="USB_DP")
    G.add_edge("comp:U2", "net:USB_DP", pin_name="DP")

    G.add_edge("comp:U1", "net:USB_DM", pin_name="USB_DM")

    api = GraphAPI(G)

    script_path = "patterns/rules/interfaces/usb_pn_swap_check.py"
    with open(script_path, "r", encoding="utf-8") as f:
        code = f.read()

    ctx = RuleContext(target=api._G.nodes["net:USB_DP"])
    res = SandboxedScriptRunner.execute_script_source(code, context=ctx, graph_api=api, part_db=PartDB())

    assert isinstance(res, list)
    assert len(res) >= 1
    assert "拓撲不對稱" in res[0].error_message
    assert res[0].recommendation is not None
