"""
USB 差分對極性反接 (Pin Swap) 與拓撲不對稱性 (Asymmetry) 檢查腳本

本腳本為 Level 3 DRC 伴生 Python 腳本，透過 DesignShield SDK (GraphAPI) 執行：
1. 情境 B (端點正負極性反接 / Pin Swap Check):
   穿越串聯 AC 耦合電容或阻抗匹配電阻，追蹤 USB 差分對 (DP/DM, SSTX_P/N, SSRX_P/N)
   到達的所有端點 IC / 連接器，比對網路極性與實體引腳名稱 (Pin Name)。
   若發現正極網路 (P/DP) 連接至負極引腳 (N/DN) 或負極網路 (N/DM) 連接至正極引腳，發出 ERROR 告警。
2. 情境 C (拓撲不對稱/懸空/錯位連線 / Differential Asymmetry Check):
   比對 P/N 夥伴網路的端點元件數量、引腳配置及途經之 AC 耦合電容數量。
   若發現單邊懸空 (Floating)、兩端連接不同 IC 或串聯電容不對稱，發出 ERROR 告警。
"""

import re
from typing import Dict, List, Any, Union, Optional
from designshield.sdk import (
    RuleResult,
    RuleViolation,
    RuleContext,
    GraphAPI,
    PartDB,
)


def _determine_net_polarity(net_name: str, net_attr_polarity: Optional[str] = None) -> Optional[str]:
    """
    判定網路名稱之極性 (P: 正極, N: 負極, None: 無法判定)

    Args:
        net_name: 網路名稱
        net_attr_polarity: 圖譜節點上預定之 diff_polarity 屬性 (若有)

    Returns:
        Optional[str]: "P", "N" 或 None
    """
    if net_attr_polarity in ["P", "N"]:
        return net_attr_polarity

    # 正極模式 (DP, D+, SSTX_P, SSRX_P, _P)
    p_regex = r"(?i)(?:_DP\b|DP\b|D\+|SSTX.*_P|SSRX.*_P|TX.*_P|RX.*_P|AUXP|_P$)"
    # 負極模式 (DN, DM, D-, SSTX_N, SSRX_N, _N)
    n_regex = r"(?i)(?:_DN\b|_DM\b|DM\b|D\- |SSTX.*_N|SSRX.*_N|TX.*_N|RX.*_N|AUXN|_N$)"

    if re.search(p_regex, net_name):
        return "P"
    if re.search(n_regex, net_name):
        return "N"
    return None


def _determine_pin_polarity(pin_name: str) -> Optional[str]:
    """
    判定引腳名稱之極性 (P: 正極, N: 負極, None: 無法判定)

    Args:
        pin_name: 元件實體引腳名稱 (例如 USB_DP, DM, D+, D-, TXP, RXN)

    Returns:
        Optional[str]: "P", "N" 或 None
    """
    if not pin_name:
        return None

    pin_upper = pin_name.upper()

    # 正極引腳特徵
    p_patterns = ["DP", "D+", "SSTXP", "SSRXP", "TXP", "RXP", "AUXP", "IN+", "OUT+"]
    # 負極引腳特徵
    n_patterns = ["DM", "DN", "D-", "SSTXN", "SSRXN", "TXN", "RXN", "AUXN", "IN-", "OUT-"]

    # 精確/包含匹配
    is_p = any(pat in pin_upper for pat in p_patterns) or pin_upper == "P"
    is_n = any(pat in pin_upper for pat in n_patterns) or pin_upper == "N"

    if is_p and not is_n:
        return "P"
    if is_n and not is_p:
        return "N"
    return None


def execute(
    context: RuleContext,
    graph_api: GraphAPI,
    part_db: PartDB,
    params: Dict[str, Any] = None
) -> Union[List[RuleViolation], RuleResult]:
    """
    執行 USB 差分對極性反接與拓撲不對稱檢查

    Args:
        context: 執行期上下文 (包含 context.target 目標網路節點)
        graph_api: SDK 拓撲查詢介面
        part_db: SDK 零件規格庫查詢介面
        params: YAML 外部參數

    Returns:
        Union[List[RuleViolation], RuleResult]: 違規報告清單或 RuleResult.PASS
    """
    target_net = context.target
    net_name = str(target_net.get("net_name") or target_net.get("name") or "")
    bus_type = str(target_net.get("bus_type") or "")

    # 僅針對 USB 相關或差分對網路進行驗證
    is_usb_related = (
        bus_type.upper() == "USB" or
        bool(re.search(r"(?i)(?:USB|TYPEC|DP|DM|SSTX|SSRX)", net_name))
    )

    if not is_usb_related:
        return RuleResult.PASS

    violations: List[RuleViolation] = []

    # 1. 取得網路極性
    net_polarity = _determine_net_polarity(net_name, target_net.get("diff_polarity"))

    # 2. 端到端端點追蹤 (穿越 AC 耦合電容與串聯阻抗電阻)
    endpoints = graph_api.trace_differential_end_to_end(target_net)

    # 檢查是否完全懸空
    if len(endpoints) == 0:
        violations.append(RuleViolation(
            error_message=f"USB 差分網路 ({net_name}) 未連接至任何實體元件引腳，呈現完全懸空 (Floating) 狀態。",
            recommendation="請檢查線路圖是否有未繪製完成的 Net Label，或將未使用的差分訊號線連接至適當終端",
            severity="ERROR",
            target_nodes={"nets": [net_name]}
        ))

    # --------------------------------------------------------------------------
    # [情境 B]: 驗證端點實體引腳名稱極性是否反接 (Pin Swap Check)
    # --------------------------------------------------------------------------
    if net_polarity:
        for ep in endpoints:
            comp = ep["component"]
            pin_name = ep["pin_name"]
            pin_polarity = _determine_pin_polarity(pin_name)

            if pin_polarity and pin_polarity != net_polarity:
                expected_str = "正極 (P/DP)" if net_polarity == "P" else "負極 (N/DM)"
                actual_str = "正極 (P/DP)" if pin_polarity == "P" else "負極 (N/DM)"

                violations.append(RuleViolation(
                    error_message=(
                        f"USB 差分對極性反接 (P/N Swap Fault)："
                        f"{expected_str} 網路 ({net_name}) 誤連接至元件 {comp.ref_des} ({comp.pn}) "
                        f"之 {actual_str} 引腳 [{pin_name}]！"
                    ),
                    recommendation=f"請交叉調換元件 {comp.ref_des} 上的差分對走線，確保 {net_name} 連接至正確極性引腳",
                    severity="ERROR",
                    evidence={
                        "net_name": net_name,
                        "net_polarity": net_polarity,
                        "component_ref_des": comp.ref_des,
                        "component_pn": comp.pn,
                        "pin_name": pin_name,
                        "pin_polarity": pin_polarity,
                    },
                    target_nodes={
                        "components": [comp.ref_des],
                        "nets": [net_name]
                    }
                ))

    # --------------------------------------------------------------------------
    # [情境 C]: 驗證 P/N 夥伴網路拓撲對稱性 (Differential Asymmetry Check)
    # --------------------------------------------------------------------------
    # 為避免 P 端與 N 端重複報錯，僅在當前網路為正極 (P) 或未指定且名稱字典序較小時執行對稱性評估
    partner_net_name = target_net.get("diff_pair_partner")
    should_run_symmetry = (
        partner_net_name and (
            net_polarity == "P" or
            (not net_polarity and net_name < str(partner_net_name))
        )
    )

    if should_run_symmetry:
        symmetry_result = graph_api.check_differential_pair_symmetry(target_net, partner_net_name)
        if not symmetry_result["is_symmetric"]:
            for reason in symmetry_result["asymmetry_reasons"]:
                violations.append(RuleViolation(
                    error_message=f"USB 差分對拓撲不對稱違規 ({net_name} ↔ {partner_net_name})：{reason}",
                    recommendation="請檢查差分對兩端之串聯電阻/電容容值、封裝與接地 TVS 防護規格，確保雙端硬體參數 100% 對稱",
                    severity="ERROR",
                    evidence={
                        "p_net": net_name,
                        "n_net": partner_net_name,
                        "asymmetry_reasons": symmetry_result["asymmetry_reasons"],
                    },
                    target_nodes={
                        "nets": [net_name, str(partner_net_name)]
                    }
                ))

    return violations if violations else RuleResult.PASS
