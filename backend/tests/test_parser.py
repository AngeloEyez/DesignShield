"""
Cadence XML 與 Allegro Netlist 解析器單元與端到端測試 (Parser E2E Tests)

使用真實 Fixture 檔案驗證 XML 與 Netlist 解析正確性。
"""

import os
from backend.app.engine.parser import (
    parse_orcad_xml,
    parse_allegro_netlist,
    merge_schematic_data,
)

FIXTURE_XML = "backend/tests/fixtures/sch/cartern-sch-si-20260817.xml"
FIXTURE_NETLIST = "backend/tests/fixtures/sch/allegro/pstxnet.dat"


def test_parse_orcad_xml_real_fixture():
    """使用真實 Cadence OrCAD XML 檔案驗證元件與網路別名解析"""
    assert os.path.exists(FIXTURE_XML), f"Fixture not found: {FIXTURE_XML}"

    parsed = parse_orcad_xml(FIXTURE_XML)
    components = parsed["components"]
    net_aliases = parsed["net_aliases"]

    # 驗證元件解析總量與各關鍵元件
    assert len(components) >= 300
    assert "TC118" in components
    assert "TU10" in components
    assert "TR124" in components

    # 驗證元件屬性
    tc118 = components["TC118"]
    assert tc118["ref_des"] == "TC118"
    assert tc118["category"] == "Passive"
    assert tc118["sub_category"] == "Capacitor"
    assert tc118["is_electrical"] is True
    assert tc118["part_value"] == "1uF_X7R_6.3V"
    assert len(tc118["pins"]) == 2

    tu10 = components["TU10"]
    assert tu10["ref_des"] == "TU10"
    assert tu10["category"] == "IC"
    assert tu10["is_electrical"] is True

    # 驗證非電氣機構件過濾
    assert "NUT1" in components
    assert components["NUT1"]["category"] == "NonElectrical"
    assert components["NUT1"]["is_electrical"] is False

    assert "FM1" in components
    assert components["FM1"]["category"] == "NonElectrical"
    assert components["FM1"]["is_electrical"] is False

    # 驗證別名網路名稱解析
    assert len(net_aliases) > 0
    assert "AN_TCP0_RT_AUXN_R" in net_aliases


def test_parse_allegro_netlist_real_fixture():
    """使用真實 Allegro pstxnet.dat 檔案驗證連線拓撲解析"""
    assert os.path.exists(FIXTURE_NETLIST), f"Fixture not found: {FIXTURE_NETLIST}"

    nets = parse_allegro_netlist(FIXTURE_NETLIST)
    assert len(nets) >= 200

    # 驗證特定網路節點連線關係
    assert "AN_TCP0_RT_AUXN_R" in nets
    conns = nets["AN_TCP0_RT_AUXN_R"]
    refs = [c["ref_des"] for c in conns]
    assert "TR124" in refs
    assert "TU10" in refs


def test_merge_schematic_data():
    """測試整合 XML 元件與 Netlist 連線資料"""
    xml_data = {
        "components": {
            "U1": {"ref_des": "U1", "category": "IC", "part_value": "STM32F407"},
            "R1": {"ref_des": "R1", "category": "Resistor", "part_value": "10K"}
        },
        "net_aliases": {
            "I2C_SCL": [{"locX": 100, "locY": 200}]
        }
    }
    netlist_data = {
        "I2C_SCL": [
            {"ref_des": "U1", "pin_number": "1", "pin_name": "PB6"},
            {"ref_des": "R1", "pin_number": "1", "pin_name": "1"}
        ]
    }

    merged = merge_schematic_data(xml_data, netlist_data)
    assert len(merged["components"]) == 2
    assert "I2C_SCL" in merged["nets"]
    assert len(merged["nets"]["I2C_SCL"]) == 2
