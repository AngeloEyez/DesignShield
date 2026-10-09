"""
DesignShield SDK 與安全沙盒全套單元測試 (SDK & Sandbox Unit Tests)

測試範圍:
1. SDK models (RuleResult, RuleViolation, ComponentNode, NetNode, RuleContext)
2. GraphAPI 唯讀查詢與節點自動包裝
3. PartDB 規格查表
4. ASTSecurityValidator 語法樹安全檢查 (阻擋 os, sys, open, eval)
5. SandboxedScriptRunner 沙盒隔離執行與逾時截斷
6. Level 2 TopologyEngine role_overrides 動態角色升級
"""

import time
import pytest
import networkx as nx

from designshield.sdk import (
    RuleResult,
    RuleViolation,
    RuleContext,
    ComponentNode,
    NetNode,
    GraphAPI,
    PartDB,
    ASTSecurityValidator,
    SandboxedScriptRunner,
    SecurityViolationError,
    ScriptTimeoutError,
)
from backend.app.engine.pattern_engine.topology_engine import TopologyPatternEngine
from backend.app.engine.pattern_engine.models import TopologyRule, RoleOverride


def test_sdk_models_and_dual_access():
    """測試資料模型與 ComponentNode / NetNode 之雙向屬性與字典存取"""
    comp_dict = {
        "_id": "comp:U1",
        "ref_des": "U1",
        "part_value": "STM32F405",
        "category": "IC",
        "sub_category": "Microcontroller",
        "functional_role": "Bus_Master",
        "is_electrical": True,
    }
    comp = ComponentNode(comp_dict)

    # 屬性存取
    assert comp.pn == "STM32F405"
    assert comp.ref_des == "U1"
    assert comp.category == "IC"
    assert comp.sub_category == "Microcontroller"
    assert comp.functional_role == "Bus_Master"
    assert comp.is_electrical is True

    # 字典存取
    assert comp["part_value"] == "STM32F405"
    assert comp["ref_des"] == "U1"

    # NetNode 雙向存取
    net_dict = {
        "_id": "net:I2C_SDA",
        "net_name": "I2C_SDA",
        "bus_type": "I2C",
        "is_power": False,
        "is_ground": False,
        "operating_voltage": 3.3,
    }
    net = NetNode(net_dict)
    assert net.name == "I2C_SDA"
    assert net.bus_type == "I2C"
    assert net.is_power is False
    assert net.operating_voltage == 3.3
    assert net["net_name"] == "I2C_SDA"

    # RuleViolation
    vio = RuleViolation(
        message="測試違規訊息",
        severity="error",
        evidence={"param": 100}
    )
    assert vio.severity == "ERROR"
    d = vio.to_dict()
    assert d["message"] == "測試違規訊息"
    assert d["severity"] == "ERROR"
    assert d["evidence"]["param"] == 100


def test_graph_api_queries():
    """測試 GraphAPI 拓撲查詢與方法"""
    G = nx.Graph()
    G.add_node("comp:U1", type="component", ref_des="U1", category="IC", sub_category="Microcontroller", functional_role="Bus_Master", part_value="STM32F405")
    G.add_node("comp:U2", type="component", ref_des="U2", category="IC", sub_category="Sensor", functional_role="Bus_Slave", part_value="SHT40")
    G.add_node("net:I2C_SCL", type="net", net_name="I2C_SCL", bus_type="I2C")
    G.add_node("net:VCC3V3", type="net", net_name="VCC3V3", is_power=True)
    G.add_node("net:GND", type="net", net_name="GND", is_ground=True)
    G.add_node("comp:R1", type="component", ref_des="R1", category="Passive", sub_category="Resistor", functional_role="Pull_up", part_value="4.7k")
    G.add_node("comp:C1", type="component", ref_des="C1", category="Passive", sub_category="Capacitor", part_value="100pF")

    G.add_edge("comp:U1", "net:I2C_SCL")
    G.add_edge("comp:U2", "net:I2C_SCL")
    G.add_edge("comp:R1", "net:I2C_SCL")
    G.add_edge("comp:R1", "net:VCC3V3")
    G.add_edge("comp:C1", "net:I2C_SCL")
    G.add_edge("comp:C1", "net:GND")

    api = GraphAPI(G)

    # 主控與受控查詢
    master = api.get_master_device("net:I2C_SCL")
    assert master is not None
    assert master.pn == "STM32F405"
    assert master.ref_des == "U1"

    slaves = api.get_slave_devices("net:I2C_SCL")
    assert len(slaves) == 1
    assert slaves[0].pn == "SHT40"

    # 上拉電阻
    pullups = api.get_pullup_resistors("net:I2C_SCL")
    assert len(pullups) == 1
    assert pullups[0].ref_des == "R1"
    assert pullups[0].get("resistance_ohm") == 4700.0

    # 接地電容
    assert api.has_capacitor_to_gnd("net:I2C_SCL") is True

    # 數值解析靜態方法
    assert GraphAPI.extract_resistance_ohms("10k") == 10000.0
    assert GraphAPI.extract_resistance_ohms("2.2M") == 2200000.0
    assert GraphAPI.extract_resistance_ohms("100R") == 100.0


def test_part_db_query():
    """測試 PartDB 零件規格查表"""
    db = PartDB()
    specs = db.query(pn="STM32F405", interface="I2C")
    assert specs is not None
    assert specs.get("forbid_gnd_capacitor") is True
    assert specs.get("pullup_range_ohms") == [2000, 10000]
    assert "_meta" in specs
    assert "STM32F405_Datasheet_Rev4.pdf" in specs["_meta"]["evidence"]


def test_sandbox_ast_security_violations():
    """測試 ASTSecurityValidator 攔截危險語法"""
    validator = ASTSecurityValidator()

    # 1. 攔截 import os / sys / subprocess
    with pytest.raises(SecurityViolationError) as exc_info:
        validator.validate_code("import os\nprint(os.getcwd())")
    assert "os" in str(exc_info.value)

    with pytest.raises(SecurityViolationError) as exc_info:
        validator.validate_code("from sys import exit\nexit(0)")
    assert "sys" in str(exc_info.value)

    # 2. 攔截 open()
    with pytest.raises(SecurityViolationError) as exc_info:
        validator.validate_code("def execute(c, g, p, a):\n    with open('/etc/passwd') as f: pass")
    assert "open()" in str(exc_info.value)

    # 3. 攔截 eval() / exec()
    with pytest.raises(SecurityViolationError) as exc_info:
        validator.validate_code("eval('1 + 1')")
    assert "eval()" in str(exc_info.value)

    # 4. 攔截反射屬性
    with pytest.raises(SecurityViolationError) as exc_info:
        validator.validate_code("x = ().__class__.__bases__")
    assert "__bases__" in str(exc_info.value)


def test_sandboxed_runner_success_and_timeout():
    """測試 SandboxedScriptRunner 執行合規腳本與逾時防護"""
    safe_code = """
from designshield.sdk import RuleResult, RuleViolation

def execute(context, graph_api, part_db, params=None):
    if params.get("trigger_fail"):
        return [RuleViolation(message="測試錯誤", severity="WARNING")]
    return RuleResult.PASS
"""

    ctx = RuleContext(target={"_id": "test_net"})
    res_pass = SandboxedScriptRunner.execute_script_source(
        safe_code,
        context=ctx,
        graph_api=None,
        part_db=None,
        params={"trigger_fail": False}
    )
    assert res_pass == RuleResult.PASS

    res_fail = SandboxedScriptRunner.execute_script_source(
        safe_code,
        context=ctx,
        graph_api=None,
        part_db=None,
        params={"trigger_fail": True}
    )
    assert len(res_fail) == 1
    assert res_fail[0].message == "測試錯誤"
    assert res_fail[0].severity == "WARNING"

    # 測試逾時中斷防護 (timeout = 0.5s)
    infinite_loop_code = """
def execute(context, graph_api, part_db, params=None):
    x = 0
    while True:
        x += 1
    return []
"""
    with pytest.raises(ScriptTimeoutError) as exc_info:
        SandboxedScriptRunner.execute_script_source(
            infinite_loop_code,
            context=ctx,
            graph_api=None,
            part_db=None,
            params={},
            timeout_seconds=0.5
        )
    assert "執行逾時" in str(exc_info.value)


def test_level2_role_overrides():
    """測試 Level 2 TopologyEngine _apply_role_overrides 動態角色升級"""
    engine = TopologyPatternEngine.get_instance()
    G = nx.Graph()

    # 建立電阻 R1: 一端接 I2C_SDA, 另一端接 VCC3V3 (PowerRail)
    G.add_node("comp:R1", type="component", ref_des="R1", category="Passive", sub_category="Resistor", functional_role="Passive_Support")
    G.add_node("net:I2C_SDA", type="net", net_name="I2C_SDA")
    G.add_node("net:VCC3V3", type="net", net_name="VCC3V3", is_power=True)

    G.add_edge("comp:R1", "net:I2C_SDA")
    G.add_edge("comp:R1", "net:VCC3V3")

    # 建立電阻 R2: 串聯於兩個訊號網路之間 (兩端皆無電源)
    G.add_node("comp:R2", type="component", ref_des="R2", category="Passive", sub_category="Resistor", functional_role="Passive_Support")
    G.add_node("net:I2C_SDA_IN", type="net", net_name="I2C_SDA_IN")
    G.add_edge("comp:R2", "net:I2C_SDA")
    G.add_edge("comp:R2", "net:I2C_SDA_IN")

    mock_rule = TopologyRule(
        name="I2C_Test_Rule",
        category="Communication",
        priority=700,
        signals=[],
        role_overrides=[
            RoleOverride(original_sub_category="Resistor", connected_to="PowerRail", new_role="Pull_up"),
            RoleOverride(original_sub_category="Resistor", connected_to="Signal", new_role="Series_Resistor"),
        ]
    )

    engine._apply_role_overrides(G, "net:I2C_SDA", mock_rule)

    assert G.nodes["comp:R1"]["functional_role"] == "Pull_up"
    assert "role_override:Pull_up" in G.nodes["comp:R1"]["evidence"]

    assert G.nodes["comp:R2"]["functional_role"] == "Series_Resistor"
    assert "role_override:Series_Resistor" in G.nodes["comp:R2"]["evidence"]
