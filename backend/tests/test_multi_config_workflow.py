"""
多 BOM Config 執行與已上件子圖檢測工作流單元測試 (Multi-Config Workflow Tests)
"""

import pytest
import networkx as nx
from backend.app.models.task import DrcTask
from backend.app.models.step_status import StepStatus
from backend.app.models.report import DrcReport
from backend.app.engine.graph import build_schematic_graph, create_config_subgraph
from backend.app.engine.drc_engine.graph_api import GraphAPI
from backend.app.engine.bom_parser import validate_and_extract_bom_configs
from backend.app.workflows.drc_workflow import step_generate_report


def test_create_config_subgraph_and_graph_api():
    """
    測試已上件子圖生成：
    驗證不上件元件於有效拓撲中被移除（等同不存在），
    但其節點資訊妥善保存於 unmounted_components 中，且 GraphAPI 能精準查詢 Placeholder。
    """
    # 建立包含 3 個元件的模擬線路資料
    components_data = {
        "U1": {
            "ref_des": "U1",
            "category": "IC",
            "functional_role": "Bus_Master",
            "part_value": "STM32F4",
            "user_props": {"BOM": "I"},  # 永遠上件
            "is_electrical": True,
            "pins": [{"pin_number": "1", "pin_name": "SDA"}]
        },
        "R_PU": {
            "ref_des": "R_PU",
            "category": "Passive",
            "sub_category": "Resistor",
            "component_role": "Pull_up",
            "functional_role": "Pull_up",
            "part_value": "4.7k",
            "user_props": {"BOM": "I,X,P"},  # 3 組 Config: Config 1 上件, Config 2 不上件, Config 3 樣品上件
            "is_electrical": True,
            "pins": [{"pin_number": "1", "pin_name": "1"}, {"pin_number": "2", "pin_name": "2"}]
        },
        "C_DEC": {
            "ref_des": "C_DEC",
            "category": "Passive",
            "sub_category": "Capacitor",
            "part_value": "0.1uF",
            "user_props": {"BOM": "PROTO,MP,NI"},  # 3 組 Config
            "is_electrical": True,
            "pins": [{"pin_number": "1", "pin_name": "1"}, {"pin_number": "2", "pin_name": "2"}]
        }
    }
    bom_config_info = validate_and_extract_bom_configs(components_data)

    merged_data = {
        "components": components_data,
        "nets": {
            "I2C_SDA": [
                {"ref_des": "U1", "pin_number": "1", "pin_name": "SDA"},
                {"ref_des": "R_PU", "pin_number": "1", "pin_name": "1"}
            ],
            "VCC3V3": [
                {"ref_des": "R_PU", "pin_number": "2", "pin_name": "2"},
                {"ref_des": "C_DEC", "pin_number": "1", "pin_name": "1"}
            ],
            "GND": [
                {"ref_des": "C_DEC", "pin_number": "2", "pin_name": "2"}
            ]
        },
        "power_symbol_nets": ["VCC3V3"],
        "ground_symbol_nets": ["GND"],
        "bom_config_info": bom_config_info
    }

    G = build_schematic_graph(merged_data)

    # 驗證基礎圖譜 bom_config_info 存在
    assert G.graph["bom_config_info"]["config_count"] == 3
    assert G.graph["bom_config_info"]["is_multi_config"] is True

    # 1. 測試 Config 1 (config_index=0, is_mp_mode=False) -> U1: I (True), R_PU: I (True), C_DEC: PROTO (True)
    g_cfg1 = create_config_subgraph(G, config_index=0, is_mp_mode=False)
    api_cfg1 = GraphAPI(g_cfg1)
    assert g_cfg1.has_node("comp:U1")
    assert g_cfg1.has_node("comp:R_PU")
    assert g_cfg1.has_node("comp:C_DEC")
    assert api_cfg1.is_component_mounted("R_PU") is True
    assert api_cfg1.has_placeholder("R_PU") is False
    assert len(api_cfg1.get_unmounted_components()) == 0

    pullups_cfg1 = api_cfg1.get_pullup_resistors({"net_name": "I2C_SDA"})
    assert len(pullups_cfg1) == 1
    assert pullups_cfg1[0]["ref_des"] == "R_PU"

    # 2. 測試 Config 2 (config_index=1, is_mp_mode=False) -> U1: I (True), R_PU: X (False), C_DEC: MP -> M (False)
    g_cfg2 = create_config_subgraph(G, config_index=1, is_mp_mode=False)
    api_cfg2 = GraphAPI(g_cfg2)
    # 雙軌解耦架構：圖譜完整保留所有節點，不作破壞性刪剪
    assert g_cfg2.has_node("comp:U1")
    assert g_cfg2.has_node("comp:R_PU")
    assert g_cfg2.has_node("comp:C_DEC")
    assert api_cfg2.is_component_mounted("R_PU") is False
    assert api_cfg2.is_component_mounted("C_DEC") is False
    assert api_cfg2.has_placeholder("R_PU") is True
    assert api_cfg2.has_placeholder("C_DEC") is True
    assert len(api_cfg2.get_unmounted_components()) == 2

    # 驗證 bom 與 raw_bom 屬性收斂
    assert g_cfg2.nodes["comp:R_PU"]["bom"] == "X"
    assert g_cfg2.nodes["comp:C_DEC"]["bom"] == "M"
    assert g_cfg2.nodes["comp:R_PU"]["raw_bom"] == "I,X,P"

    # 此時 I2C_SDA 實體電阻 R_PU 存在 (可確認預留或走線)，但其 is_mounted 為 False
    pullups_cfg2 = api_cfg2.get_pullup_resistors({"net_name": "I2C_SDA"})
    assert len(pullups_cfg2) == 1
    assert pullups_cfg2[0].is_mounted is False
    assert pullups_cfg2[0].bom == "X"
    assert pullups_cfg2[0].display_ref_des == "R_PU [X]"
    mounted_pullups = [r for r in pullups_cfg2 if r.is_mounted]
    assert len(mounted_pullups) == 0

    # 3. 測試 Config 3 在 MP Mode 下 (config_index=2, is_mp_mode=True)
    # R_PU: P (MP Mode -> False), C_DEC: NI -> X (False)
    g_cfg3_mp = create_config_subgraph(G, config_index=2, is_mp_mode=True)
    api_cfg3_mp = GraphAPI(g_cfg3_mp)
    assert g_cfg3_mp.has_node("comp:R_PU")
    assert api_cfg3_mp.is_component_mounted("R_PU") is False
    assert api_cfg3_mp.has_placeholder("R_PU") is True
    assert g_cfg3_mp.nodes["comp:R_PU"]["bom"] == "P"
    from designshield.sdk.models import ComponentNode
    r_pu_comp = ComponentNode(g_cfg3_mp.nodes["comp:R_PU"])
    assert r_pu_comp.display_ref_des == "R_PU [P]"


@pytest.mark.asyncio
async def test_step_generate_report_multi_config(db_session, monkeypatch):
    """測試 step_generate_report 彙整多 Config 獨立統計與總結指標"""
    import backend.app.workflows.drc_workflow as wf_module
    monkeypatch.setattr(wf_module, "SessionLocal", lambda: db_session)

    task_id = "test-multi-config-task-001"
    task = DrcTask(id=task_id, project_name="MultiConfigProject", status="PROCESSING")
    db_session.add(task)
    db_session.commit()

    findings_heuristic = [
        {
            "item_id": "v-1",
            "rule_id": "i2c_pullup_check",
            "rule_category": "Interfaces",
            "rule_title": "I2C 上拉電阻檢測",
            "check_type": "HEURISTIC",
            "status": "PASS",
            "severity": "INFO",
            "bom_config": "Config 1",
            "target_nodes": {"components": ["R_PU"], "nets": ["I2C_SDA"]}
        },
        {
            "item_id": "v-2",
            "rule_id": "i2c_pullup_check",
            "rule_category": "Interfaces",
            "rule_title": "I2C 上拉電阻檢測",
            "check_type": "HEURISTIC",
            "status": "FAIL",
            "severity": "ERROR",
            "bom_config": "Config 2",
            "target_nodes": {"components": [], "nets": ["I2C_SDA"]}
        }
    ]
    findings_llm = []

    # 執行報告彙整
    summary = await step_generate_report(
        task_id=task_id,
        heuristic_findings=findings_heuristic,
        llm_findings=findings_llm,
        target_configs=["Config 1", "Config 2"]
    )

    assert "configs" in summary
    assert "Config 1" in summary["configs"]
    assert "Config 2" in summary["configs"]

    cfg1_stat = summary["configs"]["Config 1"]
    assert cfg1_stat["pass_count"] == 1
    assert cfg1_stat["fail_count"] == 0
    assert cfg1_stat["pass_rate_percentage"] == 100.0

    cfg2_stat = summary["configs"]["Config 2"]
    assert cfg2_stat["pass_count"] == 0
    assert cfg2_stat["fail_count"] == 1
    assert cfg2_stat["pass_rate_percentage"] == 0.0

    # 驗證資料庫落地儲存的報告
    report = db_session.query(DrcReport).filter(DrcReport.task_id == task_id).first()
    assert report is not None
    assert "configs" in report.summary
    assert len(report.violations) == 2
