"""
DesignShield SDK 通用電路拓撲建造者單元測試 (Unit Tests for TopologyGraphBuilder)
"""

import pytest
from designshield.sdk.topology import (
    UniversalPin,
    UniversalNode,
    UniversalConnection,
    UniversalRail,
    UniversalTopologyData,
    TopologyGraphBuilder,
)
from designshield.sdk.sandbox import SandboxedScriptRunner


def test_topology_data_models_serialization():
    """驗證資料模型結構與 to_dict 序列化能力"""
    pin = UniversalPin(pin_number="1", pin_name="VCC", orientation="top")
    assert pin.to_dict() == {"pin_number": "1", "pin_name": "VCC", "orientation": "top"}

    node = UniversalNode(
        id="R1",
        ref_des="R1",
        category="Resistor",
        role="pull_up",
        value="4.7kΩ",
        pins=[pin]
    )
    node_dict = node.to_dict()
    assert node_dict["id"] == "R1"
    assert node_dict["ref_des"] == "R1"
    assert node_dict["category"] == "Resistor"
    assert node_dict["role"] == "pull_up"
    assert node_dict["value"] == "4.7kΩ"
    assert len(node_dict["pins"]) == 1

    conn = UniversalConnection(
        net_name="I2C_SDA",
        rail_id="sda",
        from_node="U1",
        from_pin="3",
        to_node="R1",
        to_pin="1",
        is_branch=True
    )
    conn_dict = conn.to_dict()
    assert conn_dict["net_name"] == "I2C_SDA"
    assert conn_dict["is_branch"] is True

    rail = UniversalRail(id="p_rail", name="Positive Rail", polarity="P")
    assert rail.to_dict() == {"id": "p_rail", "name": "Positive Rail", "polarity": "P"}


def test_builder_differential_channel():
    """驗證 Builder 建造差分通道 (以 USB 差分為例)"""
    builder = TopologyGraphBuilder(title="TJ1 ↔ TU1 (USB 差分通道)", channel_type="differential")
    
    # 建立雙軌
    builder.add_rail("p_rail", "正極軌道 (P)", polarity="P")
    builder.add_rail("n_rail", "負極軌道 (N)", polarity="N")

    # 建立端點晶片與連接器
    builder.add_terminal("TJ1", "TJ1", category="Connector", part_number="Type-C", pins=[
        {"pin_number": "B11", "pin_name": "SSRXP1"},
        {"pin_number": "B10", "pin_name": "SSRXN1"}
    ])
    builder.add_terminal("TU1", "TU1", category="IC", part_number="Bridge", pins=[
        {"pin_number": "N12", "pin_name": "PB_TX1_DRX1_P"},
        {"pin_number": "N13", "pin_name": "PB_TX1_DRX1_N"}
    ])

    # 建立串聯被動元件
    builder.add_series_component("TC13", "TC13", category="Capacitor", value="0.1µF", in_pin="2", out_pin="1")
    builder.add_series_component("TC14", "TC14", category="Capacitor", value="0.1µF", in_pin="2", out_pin="1")

    # 建立 P 端連線
    builder.add_connection("USB_SSRX_P", "p_rail", "TJ1", "B11", "TC13", "2")
    builder.add_connection("USB_SSRX_P_C", "p_rail", "TC13", "1", "TU1", "N12")

    # 建立 N 端連線
    builder.add_connection("USB_SSRX_N", "n_rail", "TJ1", "B10", "TC14", "2")
    builder.add_connection("USB_SSRX_N_C", "n_rail", "TC14", "1", "TU1", "N13")

    builder.set_metadata({"is_symmetric": True})

    data = builder.to_dict()
    assert data["title"] == "TJ1 ↔ TU1 (USB 差分通道)"
    assert data["channel_type"] == "differential"
    assert len(data["rails"]) == 2
    assert len(data["nodes"]) == 4
    assert len(data["connections"]) == 4
    assert data["metadata"]["is_symmetric"] is True


def test_builder_pull_up_and_shunt_ground():
    """驗證 Builder 建造上拉電阻與接地濾波電容 (單端/匯流排拓撲)"""
    builder = TopologyGraphBuilder(title="I2C SCL 匯流排鏈路", channel_type="single")
    builder.add_rail("scl_rail", "I2C SCL")

    # Master, Slave
    builder.add_terminal("U1", "U1", category="IC", pins=[{"pin_number": "10", "pin_name": "SCL"}])
    builder.add_terminal("U2", "U2", category="IC", pins=[{"pin_number": "5", "pin_name": "SCL"}])

    # 上拉電阻與濾波電容
    builder.add_pull_up("R1", "R1", power_net="+3.3V", value="4.7kΩ")
    builder.add_shunt_ground("C1", "C1", category="Capacitor", value="10pF", gnd_net="GND")

    # 主幹連線
    builder.add_connection("I2C_SCL", "scl_rail", "U1", "10", "U2", "5")
    # 上拉分支
    builder.add_connection("I2C_SCL", "scl_rail", "U1", "10", "R1", "1", is_branch=True)
    # 濾波接地分支
    builder.add_connection("I2C_SCL", "scl_rail", "U1", "10", "C1", "1", is_branch=True)

    data = builder.to_dict()
    assert data["channel_type"] == "single"
    assert len(data["nodes"]) == 4
    node_roles = {n["id"]: n["role"] for n in data["nodes"]}
    assert node_roles["R1"] == "pull_up"
    assert node_roles["C1"] == "shunt_ground"
    assert len(data["connections"]) == 3


def test_sandbox_allows_topology_builder():
    """驗證沙盒環境可順利匯入並執行 TopologyGraphBuilder"""
    script_code = """
from designshield.sdk import TopologyGraphBuilder, RulePass

def execute(context, graph_api, part_db, params=None):
    builder = TopologyGraphBuilder(title="Sandbox Test", channel_type="single")
    builder.add_rail("main", "Main Signal")
    builder.add_terminal("U1", "U1", category="IC")
    builder.add_pull_up("R1", "R1", power_net="+3.3V", value="2.2kΩ")
    res = builder.to_dict()
    return RulePass(evidence={"topology": res}, message="成功建構拓撲")
"""
    result = SandboxedScriptRunner.execute_script_source(
        script_code,
        context=None,
        graph_api=None,
        part_db=None,
        params={}
    )
    assert result is not None
    assert isinstance(result, object)
    assert "topology" in result.evidence
    assert result.evidence["topology"]["title"] == "Sandbox Test"

