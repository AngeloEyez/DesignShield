"""
差分通道並聯穿透元件 / 中途 tap 端點 / PartDB 缺失 單元測試
(Parallel Pass-through, Mid-chain Tap Endpoint & PartDB-missing Tests)

情境 (對應 Step 6 截圖)：
    U4 ─ {R63 ∥ L19(CMC)} ─ CON 網路 (J90 tap) ─ R2 ─ PD1 網路 ─ U78   (P 軌)
    U4 ─ {R1  ∥ L19(CMC)} ─ CON 網路 (J90 tap) ─ R64 ─ PD1 網路 ─ U78  (N 軌)
"""

import networkx as nx

from designshield.sdk import (
    GraphAPI,
    PartDB,
    RuleContext,
    RulePass,
    RuleSkipped,
    SandboxedScriptRunner,
)

SCRIPT_PATH = "patterns/level3_rules/interfaces/differential_channel_continuity_check.py"


def _add_net(G, name, polarity):
    """新增差分網路節點"""
    G.add_node(f"net:{name}", type="net", net_name=name, net_type="Differential", diff_polarity=polarity)


def _add_res(G, ref, mounted=True):
    """新增 2-pin 串聯電阻 (0Ω 跳線)"""
    G.add_node(
        f"comp:{ref}", type="component", ref_des=ref, category="Passive", sub_category="Resistor",
        functional_role="Series_Resistor", is_mounted=mounted, bom="I" if mounted else "X",
    )


def _link(G, ref, net, pin, name=None):
    """元件引腳連至網路"""
    G.add_edge(f"comp:{ref}", f"net:{net}", pin_name=name or pin, pin_number=pin)


def _link_multi(G, ref, net, pins):
    """同一元件多個引腳連至同一網路 (邊屬性攜帶完整 pins 列表，與真實圖譜建構一致)"""
    first_num, first_name = pins[0]
    G.add_edge(
        f"comp:{ref}", f"net:{net}", pin_number=first_num, pin_name=first_name,
        pins=[{"pin_number": n, "pin_name": nm} for n, nm in pins],
    )


def build_graph(l19_mounted=False, l19_known=False, r63_mounted=True, r2_mounted=True):
    """
    建構截圖情境電路圖譜

    Args:
        l19_mounted: L19 共模扼流圈是否上件
        l19_known: L19 料號是否已存在於 PartDB (True 時使用真實 MURATA_DLM0NSN900HY2D 規格)
        r63_mounted: P 軌 R63 是否上件
        r2_mounted: P 軌 R2 是否上件
    """
    G = nx.Graph()
    G.add_node("comp:U4", type="component", ref_des="U4", category="IC", is_mounted=True)
    G.add_node("comp:J90", type="component", ref_des="J90", category="Connector", is_mounted=True)
    G.add_node("comp:U78", type="component", ref_des="U78", category="IC", is_mounted=True)

    attrs = dict(
        type="component", ref_des="L19", category="Passive", sub_category="Choke",
        functional_role="Common_Mode_Choke", is_electrical=True, is_mounted=l19_mounted,
        bom="I" if l19_mounted else "X",
    )
    if l19_known:
        attrs.update(mfg="MURATA", mfg_pn="DLM0NSN900HY2D", part_value="DLM0NSN900HY2D")
    else:
        attrs.update(mfg="GENERIC", mfg_pn="CMF_90_300mA", part_value="CMF_90_300mA")
    G.add_node("comp:L19", **attrs)

    _add_res(G, "R63", r63_mounted)
    _add_res(G, "R2", r2_mounted)
    _add_res(G, "R1")
    _add_res(G, "R64")

    for suffix, pol in (("P", "P"), ("N", "N")):
        _add_net(G, f"USBC1_USB20_{suffix}", pol)
        _add_net(G, f"USBC1_USB20_CON_{suffix}", pol)
        _add_net(G, f"USBC1_USB20_PD1_{suffix}", pol)
    G.nodes["net:USBC1_USB20_P"]["diff_pair_partner"] = "USBC1_USB20_N"
    G.nodes["net:USBC1_USB20_N"]["diff_pair_partner"] = "USBC1_USB20_P"

    # P 軌: U4.C12 → R63 → CON_P (J90 A6/B6 tap) → R2 → PD1_P → U78.28
    _link(G, "U4", "USBC1_USB20_P", "C12")
    _link(G, "R63", "USBC1_USB20_P", "2")
    _link(G, "R63", "USBC1_USB20_CON_P", "1")
    _link(G, "L19", "USBC1_USB20_P", "4")
    _link(G, "L19", "USBC1_USB20_CON_P", "3")
    _link_multi(G, "J90", "USBC1_USB20_CON_P", [("A6", "Dp1"), ("B6", "Dp2")])
    _link(G, "R2", "USBC1_USB20_CON_P", "1")
    _link(G, "R2", "USBC1_USB20_PD1_P", "2")
    _link(G, "U78", "USBC1_USB20_PD1_P", "28", "DP")

    # N 軌: U4.B12 → R1 → CON_N (J90 A7/B7 tap) → R64 → PD1_N → U78.27
    _link(G, "U4", "USBC1_USB20_N", "B12")
    _link(G, "R1", "USBC1_USB20_N", "2")
    _link(G, "R1", "USBC1_USB20_CON_N", "1")
    _link(G, "L19", "USBC1_USB20_N", "2")
    _link(G, "L19", "USBC1_USB20_CON_N", "1")
    _link_multi(G, "J90", "USBC1_USB20_CON_N", [("A7", "Dn1"), ("B7", "Dn2")])
    _link(G, "R64", "USBC1_USB20_CON_N", "1")
    _link(G, "R64", "USBC1_USB20_PD1_N", "2")
    _link(G, "U78", "USBC1_USB20_PD1_N", "27", "DM")
    return G


def run_rule(G):
    """於沙盒執行差分通道導通性規則"""
    api = GraphAPI(G, part_db=PartDB())
    with open(SCRIPT_PATH, "r", encoding="utf-8") as f:
        code = f.read()
    ctx = RuleContext(target=api._G.nodes["net:USBC1_USB20_P"])
    return SandboxedScriptRunner.execute_script_source(code, context=ctx, graph_api=api, part_db=PartDB())


def test_unmounted_unknown_cmc_does_not_fail_parallel_path_conducts():
    """未上件且 PartDB 缺失的並聯 CMC (L19) 不影響導通：R63/R1 導通 → PASS，並列入缺失清單"""
    res = run_rule(build_graph(l19_mounted=False, l19_known=False))
    assert isinstance(res, RulePass), f"預期 PASS，實際 {res}"
    missing = res.evidence["missing_partdb"]
    assert [m["ref_des"] for m in missing] == ["L19"]
    assert missing[0]["is_mounted"] is False
    assert missing[0]["mfg"] == "GENERIC" and missing[0]["pn"] == "CMF_90_300mA"


def test_topology_is_complete_directed_and_acyclic():
    """拓撲完整：U4 為源端、J90 為中途 tap、並聯 L19 為虛擬分支且無任何循環"""
    res = run_rule(build_graph(l19_mounted=False, l19_known=False))
    topo = res.evidence["topology"]
    nodes = {n["id"]: n for n in topo["nodes"]}
    assert set(nodes) == {"U4", "R63", "R1", "R2", "R64", "L19", "J90", "U78"}
    assert nodes["L19"]["lane"] == "branch" and nodes["L19"]["partdb_missing"] is True
    assert nodes["J90"]["lane"] == "tap"
    assert "lane" not in nodes["U4"] and "lane" not in nodes["U78"]

    edges = {(c["from_node"], c["to_node"], c["rail_id"]): c["is_branch"] for c in topo["connections"]}
    # P 軌主幹與 tap
    assert edges[("U4", "R63", "p_rail")] is False
    assert edges[("R63", "R2", "p_rail")] is False
    assert edges[("R63", "J90", "p_rail")] is False
    assert edges[("R2", "U78", "p_rail")] is False
    # N 軌主幹與 tap
    assert edges[("U4", "R1", "n_rail")] is False
    assert edges[("R1", "R64", "n_rail")] is False
    assert edges[("R64", "U78", "n_rail")] is False
    # 並聯 L19 僅為分支，且不連至 tap 端點 J90
    assert edges[("U4", "L19", "p_rail")] is True
    assert edges[("L19", "R2", "p_rail")] is True
    assert not any(f == "L19" and t == "J90" for f, t, _ in edges)
    # 無循環：並聯元件之間不得相連、也不得有回到源端之連線
    assert not any(t == "U4" for _, t, _ in edges)
    assert not any({f, t} == {"R63", "L19"} for f, t, _ in edges)

    # J90 的 P 軌 A6/B6 與 N 軌 A7/B7 皆有連線 (不再破碎缺失)
    j90_pins = {(c["to_pin"], c["rail_id"]) for c in topo["connections"] if c["to_node"] == "J90"}
    assert j90_pins == {("A6", "p_rail"), ("B6", "p_rail"), ("A7", "n_rail"), ("B7", "n_rail")}


def test_mounted_cmc_without_partdb_is_skipped():
    """已上件的 CMC 查無 PartDB：導通性未知，SKIPPED 並附缺失清單 (嚴禁猜測引腳)"""
    res = run_rule(build_graph(l19_mounted=True, l19_known=False))
    assert isinstance(res, RuleSkipped)
    assert "CMF_90_300mA" in res.reason
    assert res.evidence["missing_partdb"][0]["ref_des"] == "L19"
    assert res.evidence["missing_partdb"][0]["is_mounted"] is True


def test_all_parallel_candidates_unmounted_fails_with_all_candidates():
    """R63 與 L19 並聯群皆未上件 (L19 為已知料號) → 該躍點斷路 FAIL，訊息列出全部並聯候選"""
    res = run_rule(build_graph(l19_mounted=False, l19_known=True, r63_mounted=False))
    assert isinstance(res, list)
    assert len(res) == 1
    assert set(res[0].evidence["faulty_components"]) == {"R63", "L19"}
    assert "R63 [X]" in res[0].error_message and "L19 [X]" in res[0].error_message
    assert "並聯" in res[0].error_message


def test_parallel_cmc_mounted_rescues_unmounted_resistor():
    """R63 未上件但並聯 L19 (已知 PartDB) 已上件 → 並聯任一上件即導通 → PASS"""
    res = run_rule(build_graph(l19_mounted=True, l19_known=True, r63_mounted=False))
    assert isinstance(res, RulePass), f"預期 PASS，實際 {res}"


def test_unmounted_series_resistor_without_parallel_fails():
    """R2 (無並聯候選) 未上件 → U78 不可達 FAIL，只報 R2"""
    res = run_rule(build_graph(l19_mounted=False, l19_known=False, r2_mounted=False))
    assert isinstance(res, list)
    assert len(res) == 1
    assert res[0].evidence["faulty_components"] == ["R2"]
    assert res[0].evidence["unreachable_target"] == "U78"


def test_inline_relay_hub_and_bypass_convergence_with_test_point():
    """
    中繼 Hub (KU100, 3 跳已上件) 與 Bypass 電阻 (KR135/KR136, 2 跳未上件) 匯流於 UR800/UR801 → J80，
    且中途掛載單腳測試點 TP56/TP57：
    1. 單腳測試點 TP56/TP57 不做導通性阻斷審計，且標記為 tap。
    2. 雖 KR135/KR136 未上件，但透過 KU100 中繼路徑可抵達 J80 → 整體通道判定 PASS。
    3. 雙路徑匯流處 (FUSBA1_USB20_CON_DP/DN → UR800/UR801 與 UL800) 在 P 軌與 N 軌皆完整產生連線，不掉線。
    """
    G = nx.Graph()
    G.add_node("comp:U4", type="component", ref_des="U4", category="IC", is_mounted=True)
    G.add_node("comp:J80", type="component", ref_des="J80", category="Connector", is_mounted=True)
    G.add_node(
        "comp:KU100", type="component", ref_des="KU100", category="IC",
        sub_category="USB_Hub", is_mounted=True, bom="I",
    )
    G.add_node(
        "comp:TP56", type="component", ref_des="TP56", category="TestPoint",
        part_value="TP_D0.6", is_mounted=False, bom="X",
    )
    G.add_node(
        "comp:TP57", type="component", ref_des="TP57", category="TestPoint",
        part_value="TP_D0.6", is_mounted=False, bom="X",
    )

    # Bypass 電阻 (未上件)
    _add_res(G, "KR135", mounted=False)
    _add_res(G, "KR136", mounted=False)
    # Hub 上下游串聯電阻 (已上件)
    _add_res(G, "KR104", mounted=True)
    _add_res(G, "KR105", mounted=True)
    _add_res(G, "KR129", mounted=True)
    _add_res(G, "KR130", mounted=True)
    # 匯流後至 J80 的串聯電阻 (已上件)
    _add_res(G, "UR800", mounted=True)
    _add_res(G, "UR801", mounted=True)

    for base in ("USB2_P1", "USB_HUB1_UP", "USB_HUB1_DN1", "FUSBA1_USB20_CON", "FUSBA1_USB20"):
        _add_net(G, f"{base}_DP", "P")
        _add_net(G, f"{base}_DN", "N")
        G.nodes[f"net:{base}_DP"]["diff_pair_partner"] = f"{base}_DN"
        G.nodes[f"net:{base}_DN"]["diff_pair_partner"] = f"{base}_DP"

    # P 軌連線
    _link(G, "U4", "USB2_P1_DP", "AE9")
    _link(G, "TP56", "USB2_P1_DP", "1")
    _link(G, "KR135", "USB2_P1_DP", "1")
    _link(G, "KR135", "FUSBA1_USB20_CON_DP", "2")
    _link(G, "KR104", "USB2_P1_DP", "1")
    _link(G, "KR104", "USB_HUB1_UP_DP", "2")
    _link(G, "KU100", "USB_HUB1_UP_DP", "47", "UFP_DP")
    _link(G, "KU100", "USB_HUB1_DN1_DP", "49", "DFP1_DP")
    _link(G, "KR129", "USB_HUB1_DN1_DP", "1")
    _link(G, "KR129", "FUSBA1_USB20_CON_DP", "2")
    _link(G, "UR800", "FUSBA1_USB20_CON_DP", "1")
    _link(G, "UR800", "FUSBA1_USB20_DP", "2")
    _link(G, "J80", "FUSBA1_USB20_DP", "3", "D+")

    # N 軌連線
    _link(G, "U4", "USB2_P1_DN", "AE11")
    _link(G, "TP57", "USB2_P1_DN", "1")
    _link(G, "KR136", "USB2_P1_DN", "1")
    _link(G, "KR136", "FUSBA1_USB20_CON_DN", "2")
    _link(G, "KR105", "USB2_P1_DN", "1")
    _link(G, "KR105", "USB_HUB1_UP_DN", "2")
    _link(G, "KU100", "USB_HUB1_UP_DN", "46", "UFP_DM")
    _link(G, "KU100", "USB_HUB1_DN1_DN", "48", "DFP1_DM")
    _link(G, "KR130", "USB_HUB1_DN1_DN", "1")
    _link(G, "KR130", "FUSBA1_USB20_CON_DN", "2")
    _link(G, "UR801", "FUSBA1_USB20_CON_DN", "1")
    _link(G, "UR801", "FUSBA1_USB20_DN", "2")
    _link(G, "J80", "FUSBA1_USB20_DN", "2", "D-")

    api = GraphAPI(G, part_db=PartDB())
    with open(SCRIPT_PATH, "r", encoding="utf-8") as f:
        code = f.read()
    ctx = RuleContext(target=api._G.nodes["net:USB2_P1_DP"])
    res = SandboxedScriptRunner.execute_script_source(code, context=ctx, graph_api=api, part_db=PartDB())

    assert isinstance(res, RulePass), f"預期透過 KU100 中繼路徑導通 PASS，實際: {res}"
    topo = res.evidence["topology"]
    nodes = {n["id"]: n for n in topo["nodes"]}
    assert "KU100" in nodes
    assert nodes["KU100"]["role"] == "series"
    assert nodes["TP56"]["lane"] == "tap"
    assert nodes["TP57"]["lane"] == "tap"

    # 確認 P 軌與 N 軌匯流處皆有完整連線 (KR135/KR129 -> UR800 與 KR136/KR130 -> UR801)
    conn_pairs = {(c["from_node"], c["to_node"], c["rail_id"]) for c in topo["connections"]}
    assert ("KR135", "UR800", "p_rail") in conn_pairs
    assert ("KR129", "UR800", "p_rail") in conn_pairs
    assert ("KR136", "UR801", "n_rail") in conn_pairs
    assert ("KR130", "UR801", "n_rail") in conn_pairs

