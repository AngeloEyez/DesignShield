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
    from designshield.sdk import RulePass
    assert isinstance(res, RulePass)
    assert res.evidence["checked_target"] == "U1 ↔ U2 (USB 差分通道)"
    assert res.evidence["p_net"] == "USB_DP"
    assert res.evidence["n_net"] == "USB_DM"
    assert res.evidence["symmetry_check"]["is_symmetric"] is True
    assert "U1" in res.target_nodes["components"]
    assert "U2" in res.target_nodes["components"]
    assert "USB_DP" in res.target_nodes["nets"]
    assert "USB_DM" in res.target_nodes["nets"]
    assert "audit_summary" in res.evidence


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


@pytest.mark.anyio
async def test_usb_pn_swap_rule_level3_engine_selective_trigger():
    """驗證 Level3Engine 執行 usb_pn_swap_check 時僅觸發 USB 且精確產出一筆雙端合一報告"""
    from backend.app.engine.drc_engine import Level3Engine
    
    G = nx.Graph()
    # 1. 建立非 USB 差分對 (PCIe)，不應被觸發
    G.add_node("net:PCIE_TX_P", type="net", net_name="PCIE_TX_P", bus_type="PCIe", net_type="Differential", diff_polarity="P")
    G.add_node("net:PCIE_TX_N", type="net", net_name="PCIE_TX_N", bus_type="PCIe", net_type="Differential", diff_polarity="N")
    
    # 2. 建立正常 USB 差分對
    G.add_node("comp:U1", type="component", ref_des="U1", category="IC", sub_category="Microcontroller", part_value="MCU")
    G.add_node("comp:J1", type="component", ref_des="J1", category="Connector", sub_category="USB", part_value="TYPE_C")
    
    G.add_node("net:USB_DP", type="net", net_name="USB_DP", bus_type="USB", net_type="Differential", diff_polarity="P", diff_pair_partner="USB_DM")
    G.add_node("net:USB_DM", type="net", net_name="USB_DM", bus_type="USB", net_type="Differential", diff_polarity="N", diff_pair_partner="USB_DP")
    
    G.add_edge("comp:U1", "net:USB_DP", pin_name="USB_DP")
    G.add_edge("comp:J1", "net:USB_DP", pin_name="DP")
    G.add_edge("comp:U1", "net:USB_DM", pin_name="USB_DM")
    G.add_edge("comp:J1", "net:USB_DM", pin_name="DM")
    
    engine = Level3Engine()
    findings = await engine.run_checks(G, ["usb_pn_swap_check"])
    
    # 應該只產出一筆報告 (只針對 USB_DP 觸發，且雙端合一審計合格)
    assert len(findings) == 1
    f = findings[0]
    assert f["status"] == "PASS"
    assert f["rule_id"] == "usb_pn_swap_check"
    assert "U1" in f["target_nodes"]["components"]
    assert "J1" in f["target_nodes"]["components"]
    assert "USB_DP" in f["target_nodes"]["nets"]
    assert "USB_DM" in f["target_nodes"]["nets"]
    assert f["evidence_trail"]["checked_target"] == "U1 ↔ J1 (USB 差分通道)"
    assert "PCIE" not in str(f)


def test_trace_differential_does_not_penetrate_gnd_or_power():
    """驗證差分端到端追蹤絕不穿透至 GND 或 Power，且濾除螺絲孔與接地旁路元件"""
    G = nx.Graph()
    # 建立晶片與連接器
    G.add_node("comp:U1", type="component", ref_des="U1", category="IC", sub_category="Microcontroller", is_electrical=True)
    G.add_node("comp:J1", type="component", ref_des="J1", category="Connector", sub_category="USB", is_electrical=True)

    # 建立差分網路
    G.add_node("net:USB_DP", type="net", net_name="USB_DP", bus_type="USB", net_type="Differential", diff_polarity="P")
    G.add_node("net:GND", type="net", net_name="GND", is_ground=True)

    # U1 與 J1 連接至 USB_DP
    G.add_edge("comp:U1", "net:USB_DP", pin_name="DP", pin_number="1")
    G.add_edge("comp:J1", "net:USB_DP", pin_name="DP", pin_number="A6")

    # 建立對地濾波電容 TC7 (一端接 USB_DP，另一端接 GND)
    G.add_node("comp:TC7", type="component", ref_des="TC7", category="Passive", sub_category="Capacitor", is_electrical=True)
    G.add_edge("comp:TC7", "net:USB_DP", pin_name="1")
    G.add_edge("comp:TC7", "net:GND", pin_name="2")

    # 建立連接至 GND 的螺絲孔與其他 IC
    G.add_node("comp:MTG1", type="component", ref_des="MTG1", category="Mechanical", sub_category="MountingHole", is_electrical=False)
    G.add_node("comp:NUT1", type="component", ref_des="NUT1", category="Mechanical", sub_category="Hardware", is_electrical=False)
    G.add_node("comp:U99_PWR", type="component", ref_des="U99_PWR", category="IC", sub_category="PMIC", is_electrical=True)
    G.add_edge("comp:MTG1", "net:GND", pin_name="1")
    G.add_edge("comp:NUT1", "net:GND", pin_name="1")
    G.add_edge("comp:U99_PWR", "net:GND", pin_name="GND_PIN")

    api = GraphAPI(G)
    endpoints = api.trace_differential_end_to_end("net:USB_DP")

    # 必須只有 U1 與 J1，絕對不可穿透到 GND，也不可抓出 MTG1、NUT1 或 U99_PWR
    endpoint_refs = [ep["component"].ref_des for ep in endpoints]
    assert "U1" in endpoint_refs
    assert "J1" in endpoint_refs
    assert "TC7" not in endpoint_refs  # 對地旁路被動元件被排除
    assert "MTG1" not in endpoint_refs # 接地螺絲孔被排除
    assert "NUT1" not in endpoint_refs # 接地螺帽被排除
    assert "U99_PWR" not in endpoint_refs # GND 上的其他晶片被排除
    assert len(endpoints) == 2


def test_spi_cs_pattern_does_not_match_tcss():
    """驗證 Level 2 匯流排模式引擎載入 710_spi.yaml 時，不會將 TCSS (如 USBC0_TCSS_AUX_P) 誤判為 SPI"""
    from backend.app.engine.pattern_engine.topology_engine import TopologyPatternEngine

    G = nx.Graph()
    G.add_node("net:USBC0_TCSS_AUX_P", type="net", net_name="USBC0_TCSS_AUX_P")
    G.add_node("net:USBC0_TCSS_AUX_N", type="net", net_name="USBC0_TCSS_AUX_N")
    G.add_node("net:SPI_CS#", type="net", net_name="SPI_CS#")

    engine = TopologyPatternEngine.get_instance()
    engine.reload()
    engine.execute(G)

    # USBC0_TCSS_AUX_P 與 N 絕對不能被打上 bus_type: "SPI"
    assert G.nodes["net:USBC0_TCSS_AUX_P"].get("bus_type") != "SPI"
    assert G.nodes["net:USBC0_TCSS_AUX_N"].get("bus_type") != "SPI"
    assert G.nodes["net:USBC0_TCSS_AUX_P"].get("is_bus") is not True
    assert G.nodes["net:USBC0_TCSS_AUX_N"].get("is_bus") is not True
    # 正確的 SPI_CS# 必須成功識別
    assert G.nodes["net:SPI_CS#"].get("bus_type") == "SPI"


@pytest.mark.anyio
async def test_usb_channel_tracing_through_4pin_cmc_and_runner_deduplication():
    """
    驗證差分通道端到端穿透 4-pin 共模扼流圈 (TL1 CMC)，
    且 Level3Engine 針對多個子網段自動執行通道網段靜默去重 (僅產出單一全通道審計報表)
    拓撲路徑:
      P72 (MCU) -- USB8_USB20_P (pin 1) --> TL1 (CMC pin 1 ➔ 4) -- USB8_USB20_CMC_P --> TJ1 (Conn pin A6)
      P72 (MCU) -- USB8_USB20_N (pin 2) --> TL1 (CMC pin 2 ➔ 3) -- USB8_USB20_CMC_N --> TJ1 (Conn pin A7)
    """
    from backend.app.engine.drc_engine import Level3Engine

    G = nx.Graph()
    # 1. 建立端點晶片與連接器
    G.add_node("comp:P72", type="component", ref_des="P72", category="IC", sub_category="Microcontroller", is_electrical=True, part_value="MCU")
    G.add_node("comp:TJ1", type="component", ref_des="TJ1", category="Connector", sub_category="USB", is_electrical=True, part_value="TYPEC_CONN")

    # 2. 建立 4-pin 共模扼流圈 TL1 (CMC)，指名真實 PartDB 料號 TDK ACM2012 (Pin 1⟷4, Pin 2⟷3)
    G.add_node(
        "comp:TL1",
        type="component",
        ref_des="TL1",
        mfg="TDK",
        mfg_pn="ACM2012",
        category="Passive",
        sub_category="Choke",
        functional_role="Common_Mode_Choke",
        is_electrical=True,
        part_value="ACM2012-900-2P"
    )

    # 3. 建立 4 條差分網段 (皆具備 USB 差分屬性，模擬 Level 2 標註)
    G.add_node("net:USB8_USB20_P", type="net", net_name="USB8_USB20_P", bus_type="USB", net_type="Differential", diff_polarity="P", diff_pair_partner="USB8_USB20_N")
    G.add_node("net:USB8_USB20_N", type="net", net_name="USB8_USB20_N", bus_type="USB", net_type="Differential", diff_polarity="N", diff_pair_partner="USB8_USB20_P")

    G.add_node("net:USB8_USB20_CMC_P", type="net", net_name="USB8_USB20_CMC_P", bus_type="USB", net_type="Differential", diff_polarity="P", diff_pair_partner="USB8_USB20_CMC_N")
    G.add_node("net:USB8_USB20_CMC_N", type="net", net_name="USB8_USB20_CMC_N", bus_type="USB", net_type="Differential", diff_polarity="N", diff_pair_partner="USB8_USB20_CMC_P")

    # 4. 連接正極鏈路: P72 (pin 1) -> USB8_USB20_P -> TL1 (pin 1) | TL1 (pin 4) -> USB8_USB20_CMC_P -> TJ1 (pin A6)
    G.add_edge("comp:P72", "net:USB8_USB20_P", pin_name="DP", pin_number="1")
    G.add_edge("comp:TL1", "net:USB8_USB20_P", pin_name="IN+", pin_number="1")
    G.add_edge("comp:TL1", "net:USB8_USB20_CMC_P", pin_name="OUT+", pin_number="4")
    G.add_edge("comp:TJ1", "net:USB8_USB20_CMC_P", pin_name="DP", pin_number="A6")

    # 5. 連接負極鏈路: P72 (pin 2) -> USB8_USB20_N -> TL1 (pin 2) | TL1 (pin 3) -> USB8_USB20_CMC_N -> TJ1 (pin A7)
    G.add_edge("comp:P72", "net:USB8_USB20_N", pin_name="DM", pin_number="2")
    G.add_edge("comp:TL1", "net:USB8_USB20_N", pin_name="IN-", pin_number="2")
    G.add_edge("comp:TL1", "net:USB8_USB20_CMC_N", pin_name="OUT-", pin_number="3")
    G.add_edge("comp:TJ1", "net:USB8_USB20_CMC_N", pin_name="DM", pin_number="A7")

    # 驗證 A: GraphAPI 能成功透過 4-pin CMC 穿透追蹤到 P72 與 TJ1
    api = GraphAPI(G)
    p_endpoints = api.trace_differential_end_to_end("net:USB8_USB20_P")
    assert len(p_endpoints) == 2
    ep_refs = [ep["component"].ref_des for ep in p_endpoints]
    assert "P72" in ep_refs
    assert "TJ1" in ep_refs

    # 檢查穿透記錄
    assert any(len(ep.get("pass_through_components", [])) > 0 for ep in p_endpoints)
    tl1_found = any(c.ref_des == "TL1" for ep in p_endpoints for c in ep.get("pass_through_components", []))
    assert tl1_found is True

    # 驗證 B: Level3Engine 執行 usb_pn_swap_check，同通道僅產生 1 筆報告 (次要網段自動靜默去重)
    engine = Level3Engine()
    findings = await engine.run_checks(G, ["usb_pn_swap_check"])

    # 雖然有 USB8_USB20_P 與 USB8_USB20_CMC_P 兩個符合條件的 target，但因同通道只會有一筆
    assert len(findings) == 1
    f = findings[0]
    assert f["status"] == "PASS"
    assert f["rule_id"] == "usb_pn_swap_check"

    # 檢查通道標題與審計結論
    ev = f["evidence_trail"]
    assert "P72 ↔ TJ1" in ev["channel_title"]
    assert "USB8_USB20" in ev["channel_title"]
    assert "TL1" in ev["audit_summary"]

    # 檢查 target_nodes 是否涵蓋所有元件與所有網段
    tn = f["target_nodes"]
    assert "P72" in tn["components"]
    assert "TL1" in tn["components"]
    assert "TJ1" in tn["components"]
    assert "USB8_USB20_P" in tn["nets"]
    assert "USB8_USB20_CMC_P" in tn["nets"]
    assert "USB8_USB20_N" in tn["nets"]
    assert "USB8_USB20_CMC_N" in tn["nets"]


def test_murata_dlm0ns_partdb_pinout_pairing():
    """驗證 Murata DLM0NSN900HY2D 依 PartDB 真實規格 (Pin 1⟷2, Pin 3⟷4) 精確穿透"""
    G = nx.Graph()
    G.add_node("comp:TU2", type="component", ref_des="TU2", mfg="TI", mfg_pn="TUSB212RWBR", category="IC")
    G.add_node("comp:TJ1", type="component", ref_des="TJ1", category="Connector")

    # TL1: Murata DLM0NS (Pin 3⟷4 正極線圈, Pin 2⟷1 負極線圈)
    G.add_node(
        "comp:TL1",
        type="component",
        ref_des="TL1",
        mfg="MURATA",
        mfg_pn="DLM0NSN900HY2D",
        category="Passive",
        sub_category="Choke",
        functional_role="Common_Mode_Choke",
        is_electrical=True
    )

    G.add_node("net:USB8_USB20_P", type="net", net_name="USB8_USB20_P")
    G.add_node("net:USB8_USB20_CMC_P", type="net", net_name="USB8_USB20_CMC_P")

    # 正極路徑: TU2 (pin 2) -> USB8_USB20_P -> TL1 (pin 4) | TL1 (pin 3) -> USB8_USB20_CMC_P -> TJ1 (pin A6)
    G.add_edge("comp:TU2", "net:USB8_USB20_P", pin_name="D1P", pin_number="2")
    G.add_edge("comp:TL1", "net:USB8_USB20_P", pin_name="4", pin_number="4")
    G.add_edge("comp:TL1", "net:USB8_USB20_CMC_P", pin_name="3", pin_number="3")
    G.add_edge("comp:TJ1", "net:USB8_USB20_CMC_P", pin_name="DP1", pin_number="A6")

    api = GraphAPI(G)
    endpoints = api.trace_differential_end_to_end("net:USB8_USB20_CMC_P")
    assert len(endpoints) == 2
    refs = [ep["component"].ref_des for ep in endpoints]
    assert "TJ1" in refs
    assert "TU2" in refs

    # 確認途經元件為 TL1 且 pin 為 3 -> 4
    tu2_ep = next(ep for ep in endpoints if ep["component"].ref_des == "TU2")
    seg = tu2_ep["path_segments"][0]
    assert seg["pass_component"] == "TL1"
    assert seg["in_pin"] == "3"
    assert seg["out_pin"] == "4"
    assert seg["pass_component_type"] == "Common_Mode_Choke"


def test_unregistered_cmc_raises_warning_and_stops_tracing():
    """驗證未在 PartDB 註冊之 4-pin 扼流圈會發出警告且終止穿透 (徹底杜絕預設假資料)"""
    import pytest

    G = nx.Graph()
    G.add_node("comp:TU2", type="component", ref_des="TU2", category="IC")
    G.add_node("comp:TJ1", type="component", ref_des="TJ1", category="Connector")

    # 未註冊料號的 4-pin CMC
    G.add_node(
        "comp:TL_UNKNOWN",
        type="component",
        ref_des="TL_UNKNOWN",
        mfg="UNKNOWN_VENDOR",
        mfg_pn="NO_SUCH_PART_XYZ",
        category="Passive",
        sub_category="Choke",
        functional_role="Common_Mode_Choke",
        is_electrical=True
    )

    G.add_node("net:USB_P1", type="net", net_name="USB_P1")
    G.add_node("net:USB_P2", type="net", net_name="USB_P2")

    G.add_edge("comp:TU2", "net:USB_P1", pin_name="DP", pin_number="1")
    G.add_edge("comp:TL_UNKNOWN", "net:USB_P1", pin_name="1", pin_number="1")
    G.add_edge("comp:TL_UNKNOWN", "net:USB_P2", pin_name="2", pin_number="2")
    G.add_edge("comp:TJ1", "net:USB_P2", pin_name="DP", pin_number="A6")

    api = GraphAPI(G)
    with pytest.warns(UserWarning, match="PartDB 穿透缺失警告"):
        endpoints = api.trace_differential_end_to_end("net:USB_P1")

    # 由於拒絕盲猜直通，未穿透過去，只到達 TU2
    refs = [ep["component"].ref_des for ep in endpoints]
    assert "TU2" in refs
    assert "TJ1" not in refs


def test_xml_package_pin_mapping_extraction():
    """驗證 OrCAD XML Package 標籤能正確解析 PinNumber <-> PinName 映射並注入網表連線"""
    from backend.app.engine.parser import parse_orcad_xml, parse_allegro_netlist, merge_schematic_data

    xml_path = "backend/tests/fixtures/sch/cartern-sch-si-20260817.xml"
    netlist_path = "backend/tests/fixtures/sch/allegro/pstxnet.dat"

    xml_data = parse_orcad_xml(xml_path)
    assert "package_pin_map" in xml_data
    assert "USB_TYPE_C_SINK" in xml_data["package_pin_map"]
    typec_map = xml_data["package_pin_map"]["USB_TYPE_C_SINK"]

    # 驗證實體腳位與邏輯引腳名稱映射正確
    assert typec_map.get("A6") == "DP1"
    assert typec_map.get("A7") == "DN1"
    assert typec_map.get("B6") == "DP2"
    assert typec_map.get("B7") == "DN2"

    # 驗證 merge 後網表連線具備邏輯 pin_name
    netlist_data = parse_allegro_netlist(netlist_path)
    merged = merge_schematic_data(xml_data, netlist_data)

    tj1_conns = [c for c in merged["nets"]["USB8_USB20_CMC_N"] if c["ref_des"] == "TJ1"]
    conn_map = {c["pin_number"]: c["pin_name"] for c in tj1_conns}
    assert conn_map.get("A6") == "DP1"
    assert conn_map.get("B7") == "DN2"


def test_multipin_edge_order_insensitivity():
    """驗證同一網路連接同一元件多個腳位時，邊屬性包含完整 pins 列表且端點追蹤對順序不敏感"""
    from backend.app.engine.graph import build_schematic_graph
    from designshield.sdk import GraphAPI

    # 模擬狀況 A: 先 A6 (DP1) 後 B7 (DN2)
    merged_a = {
        "components": {
            "TJ1": {"category": "Connector", "sub_category": "USB", "is_electrical": True, "package": "TYPE-C"}
        },
        "nets": {
            "USB_N": [
                {"ref_des": "TJ1", "pin_number": "A6", "pin_name": "DP1"},
                {"ref_des": "TJ1", "pin_number": "B7", "pin_name": "DN2"}
            ]
        }
    }
    G_a = build_schematic_graph(merged_a)
    api_a = GraphAPI(G_a)
    eps_a = api_a.trace_differential_end_to_end("net:USB_N")
    pins_a = sorted([(ep["pin_number"], ep["pin_name"]) for ep in eps_a if ep["component"].ref_des == "TJ1"])
    assert pins_a == [("A6", "DP1"), ("B7", "DN2")]

    # 模擬狀況 B: 反序 先 B7 (DN2) 後 A6 (DP1)
    merged_b = {
        "components": {
            "TJ1": {"category": "Connector", "sub_category": "USB", "is_electrical": True, "package": "TYPE-C"}
        },
        "nets": {
            "USB_N": [
                {"ref_des": "TJ1", "pin_number": "B7", "pin_name": "DN2"},
                {"ref_des": "TJ1", "pin_number": "A6", "pin_name": "DP1"}
            ]
        }
    }
    G_b = build_schematic_graph(merged_b)
    api_b = GraphAPI(G_b)
    eps_b = api_b.trace_differential_end_to_end("net:USB_N")
    pins_b = sorted([(ep["pin_number"], ep["pin_name"]) for ep in eps_b if ep["component"].ref_des == "TJ1"])
    assert pins_b == [("A6", "DP1"), ("B7", "DN2")]


def test_pin_polarity_regex_boundaries_and_fallback():
    """驗證引腳極性正規表示式邊界安全性與 Connector Type-C Fallback 機制（且排除非高速 AUX/SBU 信號）"""
    from patterns.rules.interfaces.usb_pn_swap_check import (
        _determine_net_polarity,
        _determine_pin_polarity,
        _determine_connector_pin_polarity_fallback,
        _infer_negative_partner_name,
    )

    # 1. 精確識別帶編號之引腳
    assert _determine_pin_polarity("DP1") == "P"
    assert _determine_pin_polarity("DP2") == "P"
    assert _determine_pin_polarity("DN1") == "N"
    assert _determine_pin_polarity("DN2") == "N"
    assert _determine_pin_polarity("USB0_DP") == "P"
    assert _determine_pin_polarity("USB0_DN") == "N"
    assert _determine_pin_polarity("SSTXP1") == "P"
    assert _determine_pin_polarity("SSTXN1") == "N"

    # 2. 安全排除非差分關鍵字與 AUX 低速旁帶信號
    assert _determine_pin_polarity("PDN") is None
    assert _determine_pin_polarity("PWRDN") is None
    assert _determine_pin_polarity("VDDP") is None
    assert _determine_pin_polarity("GND_PIN") is None
    assert _determine_pin_polarity("AUXP") is None
    assert _determine_pin_polarity("AUXN") is None
    assert _determine_net_polarity("DP_AUXP") is None
    assert _determine_net_polarity("DP_AUXN") is None
    assert _infer_negative_partner_name("DP_AUXP") is None

    # 3. Connector Pinout Fallback (Type-C 標準高速引腳，且排除 SBU A8/B8)
    mock_conn = {
        "category": "Connector",
        "sub_category": "USB",
        "package": "USBC_24P",
        "part_value": "TYPE-C_CONN"
    }
    assert _determine_connector_pin_polarity_fallback(mock_conn, "A6") == "P"
    assert _determine_connector_pin_polarity_fallback(mock_conn, "A7") == "N"
    assert _determine_connector_pin_polarity_fallback(mock_conn, "B6") == "P"
    assert _determine_connector_pin_polarity_fallback(mock_conn, "B7") == "N"
    assert _determine_connector_pin_polarity_fallback(mock_conn, "A2") == "P"
    assert _determine_connector_pin_polarity_fallback(mock_conn, "A3") == "N"
    assert _determine_connector_pin_polarity_fallback(mock_conn, "A1") is None # GND4 不應判為差分
    assert _determine_connector_pin_polarity_fallback(mock_conn, "A8") is None # SBU1(AUXP) 不納入 USB 高速差分
    assert _determine_connector_pin_polarity_fallback(mock_conn, "B8") is None # SBU2(AUXN) 不納入 USB 高速差分


def test_real_fixture_usb8_swap_fault_detected():
    """驗證真實 Fixture (cartern-sch-si-20260817.xml) 中 TJ1 A6/A7 極性反接錯誤能 100% 精確檢出"""
    from backend.app.engine.parser import parse_orcad_xml, parse_allegro_netlist, merge_schematic_data
    from backend.app.engine.graph import build_schematic_graph
    from backend.app.engine.pattern_engine.topology_engine import TopologyPatternEngine
    from designshield.sdk import GraphAPI, PartDB, RuleContext, SandboxedScriptRunner

    xml_path = "backend/tests/fixtures/sch/cartern-sch-si-20260817.xml"
    netlist_path = "backend/tests/fixtures/sch/allegro/pstxnet.dat"

    xml_data = parse_orcad_xml(xml_path)
    netlist_data = parse_allegro_netlist(netlist_path)
    merged = merge_schematic_data(xml_data, netlist_data)
    G = build_schematic_graph(merged)

    engine = TopologyPatternEngine.get_instance()
    engine.reload()
    engine.execute(G)

    api = GraphAPI(G)
    part_db = PartDB()

    with open("patterns/rules/interfaces/usb_pn_swap_check.py", "r", encoding="utf-8") as f:
        script_code = f.read()

    # 1. 檢驗主正極通道 USB8_USB20_P
    ctx_p = RuleContext(target=G.nodes["net:USB8_USB20_P"])
    res_p = SandboxedScriptRunner.execute_script_source(script_code, context=ctx_p, graph_api=api, part_db=part_db)

    assert isinstance(res_p, list), f"Expected violations, got {type(res_p)}"
    assert len(res_p) == 2

    # 斷言正極網路接到了 TJ1 的負極引腳 (DN1 / Pin A7)
    assert any("DN1" in v.error_message and "Pin A7" in v.error_message and "TJ1" in v.error_message for v in res_p)
    # 斷言負極網路接到了 TJ1 的正極引腳 (DP1 / Pin A6)
    assert any("DP1" in v.error_message and "Pin A6" in v.error_message and "TJ1" in v.error_message for v in res_p)

    # 2. 檢驗穿越 CMC 後的子網段 USB8_USB20_CMC_P
    ctx_cmc = RuleContext(target=G.nodes["net:USB8_USB20_CMC_P"])
    res_cmc = SandboxedScriptRunner.execute_script_source(script_code, context=ctx_cmc, graph_api=api, part_db=part_db)

    assert isinstance(res_cmc, list), f"Expected violations, got {type(res_cmc)}"
    assert len(res_cmc) == 2
    assert any("DN1" in v.error_message and "TJ1" in v.error_message for v in res_cmc)
    assert any("DP1" in v.error_message and "TJ1" in v.error_message for v in res_cmc)

    # 驗證 violations 中包含全通道 covered_nets
    for v in res_cmc:
        assert "covered_nets" in v.evidence
        assert "USB8_USB20_CMC_P" in v.evidence["covered_nets"]
        assert "USB8_USB20_P" in v.evidence["covered_nets"]


@pytest.mark.anyio
async def test_level3_runner_usb8_channel_deduplication():
    """驗證 Level3Engine 執行全線路檢查時，USB8 差分通道透過 covered_nets 機制精確去重，不重複報出 4 條違規"""
    from backend.app.engine.parser import parse_orcad_xml, parse_allegro_netlist, merge_schematic_data
    from backend.app.engine.graph import build_schematic_graph
    from backend.app.engine.pattern_engine.topology_engine import TopologyPatternEngine
    from backend.app.engine.drc_engine.level3_runner import Level3Engine

    xml_path = "backend/tests/fixtures/sch/cartern-sch-si-20260817.xml"
    netlist_path = "backend/tests/fixtures/sch/allegro/pstxnet.dat"

    xml_data = parse_orcad_xml(xml_path)
    netlist_data = parse_allegro_netlist(netlist_path)
    merged = merge_schematic_data(xml_data, netlist_data)
    G = build_schematic_graph(merged)

    TopologyPatternEngine.get_instance().reload()
    TopologyPatternEngine.get_instance().execute(G)

    runner = Level3Engine()
    findings = await runner.run_heuristic_checks(G, ["usb_pn_swap_check"])

    # 篩選出針對 USB8 通道的違規項目
    usb8_fail_findings = [
        f for f in findings
        if f["status"] == "FAIL" and any("USB8_USB20" in net for net in f.get("target_nodes", {}).get("nets", []))
    ]

    # 去重機制生效後，同一個物理通道只會產出一組極性反接違規（1 筆 P 反接 + 1 筆 N 反接），而非 4 筆
    assert len(usb8_fail_findings) == 2, f"預期通道去重後僅保留 2 筆違規，實際得到 {len(usb8_fail_findings)} 筆"

    # 驗證違規項目的佐證歷程具備完整鏈路拓撲資料，以供前端 UI 繪製差分端到端流程
    for f in usb8_fail_findings:
        ev = f.get("evidence_trail", {})
        assert "topology" in ev, "違規報告需包含通用鏈路拓撲"
        topo = ev["topology"]
        assert topo.get("channel_type") == "differential"
        assert len(topo.get("nodes", [])) > 0
        assert "pass_through_components" in ev and "TL1" in ev["pass_through_components"], "違規報告需包含途經穿透元件 TL1"


@pytest.mark.anyio
async def test_real_fixture_ssrx1_channel_topology_normalization():
    """驗證真實 Fixture 中中繼網段 (如 TCP0_RT_SSRX1_P_C) 能自動正規化為 TJ1 實體連接器起點，杜絕虛擬 Endpoint 產生"""
    from backend.app.engine.parser import parse_orcad_xml, parse_allegro_netlist, merge_schematic_data
    from backend.app.engine.graph import build_schematic_graph
    from backend.app.engine.pattern_engine.topology_engine import TopologyPatternEngine
    from backend.app.engine.drc_engine.level3_runner import Level3Engine
    from designshield.sdk import GraphAPI, PartDB, RuleContext, SandboxedScriptRunner

    xml_path = "backend/tests/fixtures/sch/cartern-sch-si-20260817.xml"
    netlist_path = "backend/tests/fixtures/sch/allegro/pstxnet.dat"

    xml_data = parse_orcad_xml(xml_path)
    netlist_data = parse_allegro_netlist(netlist_path)
    merged = merge_schematic_data(xml_data, netlist_data)
    G = build_schematic_graph(merged)

    TopologyPatternEngine.get_instance().reload()
    TopologyPatternEngine.get_instance().execute(G)

    api = GraphAPI(G)
    part_db = PartDB()

    with open("patterns/rules/interfaces/usb_pn_swap_check.py", "r", encoding="utf-8") as f:
        script_code = f.read()

    # 模擬直接以中間被動網段 TCP0_RT_SSRX1_P_C 觸發
    ctx_c = RuleContext(target=G.nodes["net:TCP0_RT_SSRX1_P_C"])
    res_c = SandboxedScriptRunner.execute_script_source(script_code, context=ctx_c, graph_api=api, part_db=part_db)

    ev = res_c.evidence if hasattr(res_c, "evidence") else res_c[0].evidence
    # 斷言正極網段已自動正規化為 TJ1 連接器所在之主網段
    assert ev.get("p_net") == "TCP0_RT_SSRX1_P"
    assert ev.get("n_net") == "TCP0_RT_SSRX1_N"
    assert "TJ1 ↔ TU1" in ev.get("channel_title", "")

    # 驗證通用拓撲圖
    topo = ev.get("topology", {})
    assert topo.get("channel_type") == "differential"
    node_ids = [n["id"] for n in topo.get("nodes", [])]
    # 驗證包含起點 TJ1、穿透元件 TC9, TR4 與終端 TU1
    assert "TJ1" in node_ids
    assert "TC9" in node_ids
    assert "TR4" in node_ids
    assert "TU1" in node_ids
    # 驗證連線包含正極網段 TCP0_RT_SSRX1_P
    conn_nets = [c["net_name"] for c in topo.get("connections", [])]
    assert any("TCP0_RT_SSRX1_P" in net for net in conn_nets)




