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


def test_parse_orcad_xml_power_and_ground_symbols():
    """驗證真實 OrCAD XML 中電源符號與接地符號已成功分流"""
    parsed = parse_orcad_xml(FIXTURE_XML)
    pwr_syms = set(parsed.get("power_symbol_nets", []))
    gnd_syms = set(parsed.get("ground_symbol_nets", []))

    # 接地符號應只包含 GND 系列
    assert "GND" in gnd_syms
    assert "DGND" in gnd_syms

    # 電源符號應包含 VCC, 電壓軌
    assert "+1.8V_AUX" in pwr_syms
    assert "+3.3V_AUX" in pwr_syms
    assert "VCC3P3" in pwr_syms
    assert "+5V_AUX" in pwr_syms

    # 電源網路絕不應被誤判進 ground_symbol_nets
    assert "+1.8V_AUX" not in gnd_syms
    assert "+3.3V_AUX" not in gnd_syms
    assert "VCC3P3" not in gnd_syms
    assert "+5V_AUX" not in gnd_syms
    assert "19V_USBC_DC_IN" not in gnd_syms


def test_orcad_xml_property_inheritance(tmp_path):
    """
    /**
     * @brief 驗證 OrCAD XML 屬性繼承與實例覆寫特性
     * @description 驗證零件實例 (<PartInst>) 繼承其 Package Symbol 庫屬性 (<SymbolUserProp>)，
     *              且實例屬性 (<PartInstUserProp>) 能正確覆寫庫屬性。
     * @param {pathlib.Path} tmp_path - pytest 臨時目錄路徑物件
     * @returns {None}
     */
    """
    # 建立包含 Package 庫屬性與不同實例設定的合成 XML 內容 (符合 OrCAD XML 結構)
    xml_content = '''<?xml version="1.0" encoding="utf-8"?>
<Design>
  <Packages>
    <Package>
      <Defn name="SHORT PAD-10"/>
      <LibPart>
        <NormalView graphic="SHORT PAD-10">
          <SymbolUserProp>
            <Defn name="BOM" val="NOBOM"/>
          </SymbolUserProp>
          <SymbolUserProp>
            <Defn name="Package Size" val="0402"/>
          </SymbolUserProp>
          <SymbolUserProp>
            <Defn name="Tolerance" val="5%"/>
          </SymbolUserProp>
        </NormalView>
      </LibPart>
    </Package>
  </Packages>
  <Schematic>
    <Pages>
      <Page>
        <PartInst>
          <!-- 實例 1 (ARS2): 無實例屬性，應完全繼承 Package 庫屬性 (包含 BOM="NOBOM") -->
          <Defn pkgName="SHORT PAD-10"/>
          <Reference>
            <Defn name="ARS2"/>
          </Reference>
          <GraphicName>
            <Defn name="SHORT PAD-10"/>
          </GraphicName>
        </PartInst>
        <PartInst>
          <!-- 實例 2 (ARS3): 覆寫 Package Size 與 BOM，但保留繼承 Tolerance="5%" -->
          <Defn pkgName="SHORT PAD-10"/>
          <Reference>
            <Defn name="ARS3"/>
          </Reference>
          <GraphicName>
            <Defn name="SHORT PAD-10"/>
          </GraphicName>
          <PartInstUserProp>
            <Defn name="Package Size" val="0402_10Mil"/>
          </PartInstUserProp>
          <PartInstUserProp>
            <Defn name="BOM" val="I"/>
          </PartInstUserProp>
        </PartInst>
      </Page>
    </Pages>
  </Schematic>
</Design>
'''
    test_file = tmp_path / "test_inheritance.xml"
    test_file.write_text(xml_content, encoding="utf-8")

    parsed = parse_orcad_xml(str(test_file))
    components = parsed["components"]

    # 1. 驗證 ARS2 完全繼承庫屬性
    assert "ARS2" in components
    ars2 = components["ARS2"]
    assert ars2["user_props"].get("BOM") == "NOBOM"
    assert ars2["user_props"].get("Package Size") == "0402"
    assert ars2["user_props"].get("Tolerance") == "5%"
    assert ars2["bom_tokens"] == ["NOBOM"]
    assert ars2["raw_bom"] == "NOBOM"

    # 2. 驗證 ARS3 實例屬性成功覆寫庫屬性，且未覆寫的屬性保留繼承
    assert "ARS3" in components
    ars3 = components["ARS3"]
    assert ars3["user_props"].get("BOM") == "I"
    assert ars3["user_props"].get("Package Size") == "0402_10Mil"
    assert ars3["user_props"].get("Tolerance") == "5%"
    assert ars3["bom_tokens"] == ["I"]
    assert ars3["raw_bom"] == "I"


def test_real_i219_ars2_bom_inheritance():
    """
    /**
     * @brief 驗證實際 D:\\Temp\\i219 XML 中 ARS2 零件之 BOM 屬性繼承
     * @description 若測試環境存在 i219 實際 XML 檔案，則驗證 ARS2 成功繼承 Package 庫屬性之 BOM="NOBOM"
     * @returns {None}
     */
    """
    xml_path = r"D:\Temp\i219\fy27_nvl_x2_si1_20260909_1500.xml"
    if not os.path.exists(xml_path):
        return

    parsed = parse_orcad_xml(xml_path)
    components = parsed["components"]

    # 驗證 ARS2 存在且 BOM 欄位為繼承而來的 NOBOM (在 4 個 Config 下皆為 NOBOM)
    assert "ARS2" in components
    ars2 = components["ARS2"]
    assert ars2["user_props"].get("BOM") == "NOBOM"
    assert ars2["raw_bom"] == "NOBOM"
    assert all(token == "NOBOM" for token in ars2["bom_tokens"])
    assert len(ars2["bom_tokens"]) == parsed["bom_config_info"]["config_count"]


