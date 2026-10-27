"""
DesignShield SDK 差分對極性判定與夥伴推導單元測試 (Differential Pair Resolution Unit Tests)
"""

import pytest
from designshield.sdk.diff_pair import (
    DifferentialPairResolver,
    determine_diff_polarity,
    resolve_diff_pair_partner,
    DEFAULT_PARTNER_SWAP_RULES,
)


def test_determine_diff_polarity_standard():
    """驗證標準差分極性判定 (Positive & Negative)"""
    # 正極測試
    assert determine_diff_polarity("PCIE_TX_P") == "P"
    assert determine_diff_polarity("USB20_DP") == "P"
    assert determine_diff_polarity("USB_D+") == "P"
    assert determine_diff_polarity("DP_AUXP") == "P"
    assert determine_diff_polarity("SATA0_SATA_TXP") == "P"
    assert determine_diff_polarity("SATA0_SATA_RXP") == "P"
    assert determine_diff_polarity("SSTXP1") == "P"
    assert determine_diff_polarity("ETH_MDI0_PLUS") == "P"
    assert determine_diff_polarity("TCP0_TX0_P_C") == "P"

    # 負極測試
    assert determine_diff_polarity("PCIE_TX_N") == "N"
    assert determine_diff_polarity("USB20_DN") == "N"
    assert determine_diff_polarity("USB_D-") == "N"
    assert determine_diff_polarity("DP_AUXN") == "N"
    assert determine_diff_polarity("SATA0_SATA_TXN") == "N"
    assert determine_diff_polarity("SATA0_SATA_RXN") == "N"
    assert determine_diff_polarity("SSTXN1") == "N"
    assert determine_diff_polarity("ETH_MDI0_MINUS") == "N"
    assert determine_diff_polarity("TCP0_TX0_N_C") == "N"

    # 非差分訊號
    assert determine_diff_polarity("VCC_3V3") is None
    assert determine_diff_polarity("GND") is None
    assert determine_diff_polarity("I2C_SCL") is None
    assert determine_diff_polarity("RESET#") is None


def test_resolve_diff_pair_partner_bidirectional():
    """驗證差分夥伴雙向互推 (P -> N 與 N -> P)"""
    # 1. P -> N 推導
    assert resolve_diff_pair_partner("PCIE_TX_P") == "PCIE_TX_N"
    assert resolve_diff_pair_partner("USB20_DP") == "USB20_DN"
    assert resolve_diff_pair_partner("USB_D+") == "USB_D-"
    assert resolve_diff_pair_partner("DP_AUXP") == "DP_AUXN"
    assert resolve_diff_pair_partner("SATA0_SATA_TXP") == "SATA0_SATA_TXN"
    assert resolve_diff_pair_partner("SATA0_SATA_RXP") == "SATA0_SATA_RXN"
    assert resolve_diff_pair_partner("TCP0_TX0_P_C") == "TCP0_TX0_N_C"
    assert resolve_diff_pair_partner("ETH_MDI0_PLUS") == "ETH_MDI0_MINUS"

    # 2. N -> P 推導
    assert resolve_diff_pair_partner("PCIE_TX_N") == "PCIE_TX_P"
    assert resolve_diff_pair_partner("USB20_DN") == "USB20_DP"
    assert resolve_diff_pair_partner("USB_D-") == "USB_D+"
    assert resolve_diff_pair_partner("DP_AUXN") == "DP_AUXP"
    assert resolve_diff_pair_partner("SATA0_SATA_TXN") == "SATA0_SATA_TXP"
    assert resolve_diff_pair_partner("SATA0_SATA_RXN") == "SATA0_SATA_RXP"
    assert resolve_diff_pair_partner("TCP0_TX0_N_C") == "TCP0_TX0_P_C"
    assert resolve_diff_pair_partner("ETH_MDI0_MINUS") == "ETH_MDI0_PLUS"


def test_custom_swap_rules_registration():
    """驗證自訂規則註冊擴充功能"""
    resolver = DifferentialPairResolver()
    # 預設未知特殊自訂命名
    assert resolver.resolve_partner_name("RF_SIG_POS") is None

    # 動態註冊自訂規則
    resolver.register_swap_rule("_POS$", "_NEG$")
    assert resolver.resolve_partner_name("RF_SIG_POS", "N") == "RF_SIG_NEG"
    assert resolver.resolve_partner_name("RF_SIG_NEG", "P") == "RF_SIG_POS"


def test_from_yaml_derivation():
    """驗證從 YAML pair_derivation 字典建構 Resolver"""
    yaml_dict = {
        "positive_pattern": r"(?i)_HI$",
        "negative_pattern": r"(?i)_LO$",
        "partner_swap_rules": [
            ["_HI$", "_LO$"]
        ]
    }
    resolver = DifferentialPairResolver.from_yaml_derivation(yaml_dict)
    assert resolver.determine_polarity("CLK_DIFF_HI") == "P"
    assert resolver.determine_polarity("CLK_DIFF_LO") == "N"
    assert resolver.resolve_partner_name("CLK_DIFF_HI") == "CLK_DIFF_LO"
    assert resolver.resolve_partner_name("CLK_DIFF_LO") == "CLK_DIFF_HI"
