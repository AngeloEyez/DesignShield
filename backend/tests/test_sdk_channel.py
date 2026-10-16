"""
================================================================================
DesignShield SDK 通道模型與高階拓撲抽象單元測試 (SDK Channel Unit Tests)
================================================================================

測試範圍:
1. BaseChannel 基礎屬性 (root_ref, target_refs, endpoint_refs, pass_component_refs)
2. DifferentialChannel 直連點對點與 1 對多發散扇出 (Multi-drop)
3. DifferentialChannel 穿透元件串聯段落、開路審計 (is_continuous) 與未上件判定
4. SingleEndedChannel 單軌訊號、上拉電阻、下拉電阻、對地分流濾波元件
5. GraphAPI.get_differential_channel 起點正規化 (Canonical Root Selection)
================================================================================
"""

import pytest
import networkx as nx

from designshield.sdk import (
    GraphAPI,
    PartDB,
    DifferentialChannel,
    SingleEndedChannel,
    ComponentNode,
    NetNode,
)


def test_differential_channel_basic_point_to_point():
    """
    測試場景 1：基礎雙端點差分通道 (IC ↔ Connector)
    驗證權重排序判定主晶片為源端、終端為目標端，並能自動產生乾淨拓撲。
    """
    G = nx.Graph()
    G.add_node("comp:U1", type="component", ref_des="U1", category="IC", sub_category="Microcontroller", part_value="MCU", is_mounted=True, bom="I")
    G.add_node("comp:J1", type="component", ref_des="J1", category="Connector", sub_category="USB_Connector", part_value="TYPEC", is_mounted=True, bom="I")

    G.add_node("net:USB_DP", type="net", net_name="USB_DP", bus_type="USB", net_type="Differential", diff_polarity="P", diff_pair_partner="USB_DM")
    G.add_node("net:USB_DM", type="net", net_name="USB_DM", bus_type="USB", net_type="Differential", diff_polarity="N", diff_pair_partner="USB_DP")

    G.add_edge("comp:U1", "net:USB_DP", pin_name="DP", pin_number="1")
    G.add_edge("comp:U1", "net:USB_DM", pin_name="DM", pin_number="2")
    G.add_edge("comp:J1", "net:USB_DP", pin_name="A6", pin_number="A6")
    G.add_edge("comp:J1", "net:USB_DM", pin_name="A7", pin_number="A7")

    api = GraphAPI(G)
    channel: DifferentialChannel = api.get_differential_channel("net:USB_DP")

    assert channel is not None
    assert channel.p_net_name == "USB_DP"
    assert channel.n_net_name == "USB_DM"
    assert channel.root_ref == "U1"
    assert channel.target_refs == ["J1"]
    assert channel.endpoint_refs == ["U1", "J1"]
    assert channel.is_continuous is True
    assert channel.endpoints_mounted is True
    assert len(channel.unmounted_pass_components) == 0

    topo = channel.to_topology()
    assert topo["title"] == channel.title
    assert topo["channel_type"] == "differential"
    assert len(topo["rails"]) == 2
    assert len(topo["nodes"]) == 2
    # P/N 各一條連線
    assert len(topo["connections"]) == 2


def test_differential_channel_multi_drop_fanout():
    """
    測試場景 2：1 對多直連多端點發散通道 (如 CPU XU1 驅動雙 DIMM 插槽 XMM1, XMM2)
    驗證發散源端挑選與逗號分隔路徑標題。
    """
    G = nx.Graph()
    G.add_node("comp:XU1", type="component", ref_des="XU1", category="Connector", sub_category="Socket", part_value="LGA", is_mounted=True, bom="I")
    G.add_node("comp:XMM1", type="component", ref_des="XMM1", category="Connector", sub_category="Connector", part_value="UDIMM", is_mounted=True, bom="I")
    G.add_node("comp:XMM2", type="component", ref_des="XMM2", category="Connector", sub_category="Connector", part_value="UDIMM", is_mounted=True, bom="I")

    G.add_node("net:DDR_DQS0_DP", type="net", net_name="DDR_DQS0_DP", bus_type="DDR", net_type="Differential", diff_polarity="P", diff_pair_partner="DDR_DQS0_DN")
    G.add_node("net:DDR_DQS0_DN", type="net", net_name="DDR_DQS0_DN", bus_type="DDR", net_type="Differential", diff_polarity="N", diff_pair_partner="DDR_DQS0_DP")

    G.add_edge("comp:XU1", "net:DDR_DQS0_DP", pin_name="AL47", pin_number="AL47")
    G.add_edge("comp:XU1", "net:DDR_DQS0_DN", pin_name="AK48", pin_number="AK48")
    G.add_edge("comp:XMM1", "net:DDR_DQS0_DP", pin_name="14", pin_number="14")
    G.add_edge("comp:XMM1", "net:DDR_DQS0_DN", pin_name="13", pin_number="13")
    G.add_edge("comp:XMM2", "net:DDR_DQS0_DP", pin_name="14", pin_number="14")
    G.add_edge("comp:XMM2", "net:DDR_DQS0_DN", pin_name="13", pin_number="13")

    api = GraphAPI(G)
    channel: DifferentialChannel = api.get_differential_channel("DDR_DQS0_DP")

    assert channel.root_ref == "XU1"
    assert set(channel.target_refs) == {"XMM1", "XMM2"}
    assert "XU1 -> XMM1, XMM2" in channel.title
    assert channel.is_continuous is True

    topo = channel.to_topology()
    assert len(topo["nodes"]) == 3
    # P 軌發散 2 條 (XU1->XMM1, XU1->XMM2)，N 軌發散 2 條，共 4 條連線
    assert len(topo["connections"]) == 4


def test_differential_channel_series_pass_components_unmounted():
    """
    測試場景 3：途經串聯穿透元件且未上件 (電氣開路)
    驗證 unmounted_pass_components 與 is_continuous 判定。
    """
    G = nx.Graph()
    G.add_node("comp:U1", type="component", ref_des="U1", category="IC", is_mounted=True, bom="I")
    G.add_node("comp:J1", type="component", ref_des="J1", category="Connector", is_mounted=True, bom="I")

    # 串聯電容 C1 (未上件) 與 C2 (已上件)
    G.add_node("comp:C1", type="component", ref_des="C1", category="Passive", sub_category="Capacitor", functional_role="AC_Coupling_Capacitor", is_mounted=False, bom="NI")
    G.add_node("comp:C2", type="component", ref_des="C2", category="Passive", sub_category="Capacitor", functional_role="AC_Coupling_Capacitor", is_mounted=True, bom="I")

    G.add_node("net:PCIE_TX_P", type="net", net_name="PCIE_TX_P", bus_type="PCIe", net_type="Differential", diff_polarity="P", diff_pair_partner="PCIE_TX_N")
    G.add_node("net:PCIE_TX_P_C", type="net", net_name="PCIE_TX_P_C", bus_type="PCIe", net_type="Differential", diff_polarity="P")
    G.add_node("net:PCIE_TX_N", type="net", net_name="PCIE_TX_N", bus_type="PCIe", net_type="Differential", diff_polarity="N", diff_pair_partner="PCIE_TX_P")
    G.add_node("net:PCIE_TX_N_C", type="net", net_name="PCIE_TX_N_C", bus_type="PCIe", net_type="Differential", diff_polarity="N")

    G.add_edge("comp:U1", "net:PCIE_TX_P", pin_name="TX+", pin_number="1")
    G.add_edge("comp:C1", "net:PCIE_TX_P", pin_name="1", pin_number="1")
    G.add_edge("comp:C1", "net:PCIE_TX_P_C", pin_name="2", pin_number="2")
    G.add_edge("comp:J1", "net:PCIE_TX_P_C", pin_name="TX+", pin_number="A1")

    G.add_edge("comp:U1", "net:PCIE_TX_N", pin_name="TX-", pin_number="2")
    G.add_edge("comp:C2", "net:PCIE_TX_N", pin_name="1", pin_number="1")
    G.add_edge("comp:C2", "net:PCIE_TX_N_C", pin_name="2", pin_number="2")
    G.add_edge("comp:J1", "net:PCIE_TX_N_C", pin_name="TX-", pin_number="A2")

    api = GraphAPI(G)
    channel: DifferentialChannel = api.get_differential_channel("PCIE_TX_P")

    assert channel.is_continuous is False
    assert len(channel.unmounted_pass_components) == 1
    unmounted_ref = getattr(channel.unmounted_pass_components[0], "ref_des", None) or channel.unmounted_pass_components[0].get("ref_des")
    assert unmounted_ref == "C1"
    assert "C1" in channel.pass_component_refs
    assert "C2" in channel.pass_component_refs


def test_differential_channel_endpoints_unmounted():
    """
    測試場景 4：端點元件在當前 Config 下未上件
    驗證 endpoints_mounted == False。
    """
    G = nx.Graph()
    G.add_node("comp:U1", type="component", ref_des="U1", category="IC", is_mounted=True, bom="I")
    G.add_node("comp:J1", type="component", ref_des="J1", category="Connector", is_mounted=False, bom="NOBOM")

    G.add_node("net:USB_DP", type="net", net_name="USB_DP", bus_type="USB", net_type="Differential", diff_polarity="P", diff_pair_partner="USB_DM")
    G.add_node("net:USB_DM", type="net", net_name="USB_DM", bus_type="USB", net_type="Differential", diff_polarity="N", diff_pair_partner="USB_DP")

    G.add_edge("comp:U1", "net:USB_DP", pin_name="DP", pin_number="1")
    G.add_edge("comp:U1", "net:USB_DM", pin_name="DM", pin_number="2")
    G.add_edge("comp:J1", "net:USB_DP", pin_name="A6", pin_number="A6")
    G.add_edge("comp:J1", "net:USB_DM", pin_name="A7", pin_number="A7")

    api = GraphAPI(G)
    channel: DifferentialChannel = api.get_differential_channel("USB_DP")

    assert channel.endpoints_mounted is False
    assert len(channel.unmounted_endpoints) == 1
    unm_ref = getattr(channel.unmounted_endpoints[0].get("component"), "ref_des", None) or channel.unmounted_endpoints[0].get("ref_des")
    assert unm_ref == "J1"


def test_single_ended_channel_pullup_pulldown_shunts():
    """
    測試場景 5：單端匯流排通道 (SingleEndedChannel)
    驗證端到端、上拉電阻、下拉電阻、對地分流濾波電容之完整識別與拓撲結構。
    """
    G = nx.Graph()
    # 主端點 IC
    G.add_node("comp:U1", type="component", ref_des="U1", category="IC", sub_category="Microcontroller", is_mounted=True)
    G.add_node("comp:U2", type="component", ref_des="U2", category="IC", sub_category="Sensor", is_mounted=True)

    # 供電軌與接地軌
    G.add_node("net:VCC3V3", type="net", net_name="VCC3V3", is_power=True, operating_voltage=3.3)
    G.add_node("net:GND", type="net", net_name="GND", is_ground=True)

    # 主訊號網段
    G.add_node("net:I2C_SDA", type="net", net_name="I2C_SDA", bus_type="I2C", net_type="SingleEnded")

    # 上拉電阻 R1 (4.7k)
    G.add_node("comp:R1", type="component", ref_des="R1", category="Passive", sub_category="Resistor", functional_role="Pull_up", part_value="4.7K", is_mounted=True)
    # 下拉電阻 R2 (100k)
    G.add_node("comp:R2", type="component", ref_des="R2", category="Passive", sub_category="Resistor", functional_role="Pull_down", part_value="100K", is_mounted=True)
    # 對地分流電容 C10 (100nF)
    G.add_node("comp:C10", type="component", ref_des="C10", category="Passive", sub_category="Capacitor", part_value="100nF", is_mounted=True)

    # 連線
    G.add_edge("comp:U1", "net:I2C_SDA", pin_name="SDA", pin_number="5")
    G.add_edge("comp:U2", "net:I2C_SDA", pin_name="SDA", pin_number="2")

    # R1 接 I2C_SDA 與 VCC3V3
    G.add_edge("comp:R1", "net:I2C_SDA", pin_number="1")
    G.add_edge("comp:R1", "net:VCC3V3", pin_number="2")

    # R2 接 I2C_SDA 與 GND
    G.add_edge("comp:R2", "net:I2C_SDA", pin_number="1")
    G.add_edge("comp:R2", "net:GND", pin_number="2")

    # C10 接 I2C_SDA 與 GND
    G.add_edge("comp:C10", "net:I2C_SDA", pin_number="1")
    G.add_edge("comp:C10", "net:GND", pin_number="2")

    api = GraphAPI(G)
    channel: SingleEndedChannel = api.get_single_ended_channel("I2C_SDA")

    assert channel is not None
    assert channel.name == "I2C_SDA"
    assert channel.has_pullup is True
    assert channel.has_pulldown is True
    assert channel.has_shunt_cap is True
    assert len(channel.pull_ups) == 1
    assert channel.pull_ups[0].ref_des == "R1"
    assert len(channel.pull_downs) == 1
    assert channel.pull_downs[0].ref_des == "R2"
    assert len(channel.shunts) == 1
    assert channel.shunts[0].ref_des == "C10"

    topo = channel.to_topology()
    assert topo["channel_type"] == "single"
    assert len(topo["rails"]) == 1
    # 檢查是否含有 pull_up 與 shunt 節點
    node_roles = [n["role"] for n in topo["nodes"]]
    assert "pull_up" in node_roles
    assert "shunt_ground" in node_roles


def test_graph_api_get_differential_channel_canonical_root():
    """
    測試場景 6：從純中繼網段 (兩端皆為串聯被動元件，無實體 IC/Connector 端點) 呼叫 get_differential_channel
    驗證起點自動正規化 (Canonical Channel Root Selection)，錨定至板端 Connector TJ1 之 USB_DP。
    """
    G = nx.Graph()
    G.add_node("comp:TJ1", type="component", ref_des="TJ1", category="Connector", sub_category="USB_Connector", is_mounted=True)
    G.add_node("comp:U1", type="component", ref_des="U1", category="IC", sub_category="Microcontroller", is_mounted=True)

    # 兩顆串聯 2-pin 電阻/電容 C1, C2
    G.add_node("comp:C1", type="component", ref_des="C1", category="Passive", sub_category="Capacitor", functional_role="AC_Coupling_Capacitor", is_mounted=True)
    G.add_node("comp:C2", type="component", ref_des="C2", category="Passive", sub_category="Capacitor", functional_role="AC_Coupling_Capacitor", is_mounted=True)

    # 板端入口網段
    G.add_node("net:USB_DP", type="net", net_name="USB_DP", bus_type="USB", net_type="Differential", diff_polarity="P", diff_pair_partner="USB_DM")
    G.add_node("net:USB_DM", type="net", net_name="USB_DM", bus_type="USB", net_type="Differential", diff_polarity="N", diff_pair_partner="USB_DP")

    # 中繼網段 (無 IC/Connector 端點)
    G.add_node("net:USB_MID_DP", type="net", net_name="USB_MID_DP", bus_type="USB", net_type="Differential", diff_polarity="P")
    G.add_node("net:USB_MID_DM", type="net", net_name="USB_MID_DM", bus_type="USB", net_type="Differential", diff_polarity="N")

    # 晶片端網段
    G.add_node("net:USB_IC_DP", type="net", net_name="USB_IC_DP", bus_type="USB", net_type="Differential", diff_polarity="P")
    G.add_node("net:USB_IC_DM", type="net", net_name="USB_IC_DM", bus_type="USB", net_type="Differential", diff_polarity="N")

    # 連線: TJ1 -> USB_DP -> C1 -> USB_MID_DP -> C2 -> USB_IC_DP -> U1
    G.add_edge("comp:TJ1", "net:USB_DP", pin_name="A6", pin_number="A6")
    G.add_edge("comp:TJ1", "net:USB_DM", pin_name="A7", pin_number="A7")

    G.add_edge("comp:C1", "net:USB_DP", pin_name="1", pin_number="1")
    G.add_edge("comp:C1", "net:USB_MID_DP", pin_name="2", pin_number="2")

    G.add_edge("comp:C2", "net:USB_MID_DP", pin_name="1", pin_number="1")
    G.add_edge("comp:C2", "net:USB_IC_DP", pin_name="2", pin_number="2")

    G.add_edge("comp:U1", "net:USB_IC_DP", pin_name="DP", pin_number="1")
    G.add_edge("comp:U1", "net:USB_IC_DM", pin_name="DM", pin_number="2")

    api = GraphAPI(G)
    # 從純中繼網段 USB_MID_DP 查詢
    channel: DifferentialChannel = api.get_differential_channel("USB_MID_DP")

    assert channel is not None
    # 斷言自動起點正規化為板端入口 USB_DP
    assert channel.p_net_name == "USB_DP"
    assert channel.root_ref == "U1"
    assert channel.target_refs == ["TJ1"]
