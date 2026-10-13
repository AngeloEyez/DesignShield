"""
USB 差分對極性反接 (Pin Swap) 與拓撲不對稱性 (Asymmetry) 雙端合一檢查腳本

本腳本為 Level 3 DRC 伴生 Python 腳本，採「P 端主導雙端合一審計 (Unified Differential Inspection)」模型：
1. 檢驗標的：以正極 (P/DP) 網路為入口，自動解析關聯之負極 (N/DM) 夥伴網路。
2. 情境 B (端點正負極性反接 / Pin Swap Check):
   穿越串聯 AC 耦合電容或阻抗匹配電阻，追蹤 P/N 雙端到達的所有端點 IC / 連接器引腳名稱 (Pin Name)。
   若發現正極網路 (P/DP) 誤接至負極引腳 (N/DN) 或負極網路 (N/DM) 誤接至正極引腳，發出 ERROR 告警。
3. 情境 C (拓撲不對稱/懸空/錯位連線 / Differential Asymmetry Check):
   比對 P/N 雙端到達之端點元件數量、引腳配置及途經之 AC 耦合電容數量與容值。
   若發現單邊懸空 (Floating)、兩端連接不同 IC 或串聯電容不對稱，發出 ERROR 告警。
4. 結構化審計 (Evidence Trail):
   合規 (PASS) 時回傳包含雙端端點晶片、引腳名稱與對稱性比對之完整 RulePass 審計歷程，
   並將所有涉及之端點 IC 與串聯電容納入 target_nodes。
"""

import re
from typing import Dict, List, Any, Union, Optional
from designshield.sdk import (
    RuleResult,
    RulePass,
    RuleViolation,
    RuleContext,
    GraphAPI,
    PartDB,
)


def _determine_net_polarity(net_name: str, net_attr_polarity: Optional[str] = None) -> Optional[str]:
    """
    判定網路名稱之極性 (P: 正極, N: 負極, None: 無法判定)
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
    判定元件實體引腳名稱之極性 (P: 正極, N: 負極, None: 無法判定)
    """
    if not pin_name:
        return None

    pin_upper = pin_name.upper()

    # 正極引腳特徵
    p_patterns = ["DP", "D+", "SSTXP", "SSRXP", "TXP", "RXP", "AUXP", "IN+", "OUT+"]
    # 負極引腳特徵
    n_patterns = ["DM", "DN", "D-", "SSTXN", "SSRXN", "TXN", "RXN", "AUXN", "IN-", "OUT-"]

    is_p = any(pat in pin_upper for pat in p_patterns) or pin_upper == "P"
    is_n = any(pat in pin_upper for pat in n_patterns) or pin_upper == "N"

    if is_p and not is_n:
        return "P"
    if is_n and not is_p:
        return "N"
    return None


def _infer_negative_partner_name(p_net_name: str) -> Optional[str]:
    """
    由正極差分網路名稱推導負極夥伴網路名稱
    """
    if re.search(r"(?i)_DP$", p_net_name):
        return re.sub(r"(?i)_DP$", "_DM", p_net_name)
    if re.search(r"(?i)DP$", p_net_name):
        return re.sub(r"(?i)DP$", "DM", p_net_name)
    if re.search(r"D\+$", p_net_name):
        return re.sub(r"D\+$", "D-", p_net_name)
    if re.search(r"_P$", p_net_name):
        return re.sub(r"_P$", "_N", p_net_name)
    if "_P_" in p_net_name:
        return p_net_name.replace("_P_", "_N_")
    if "_DP_" in p_net_name:
        return p_net_name.replace("_DP_", "_DM_")
    if "AUXP" in p_net_name:
        return p_net_name.replace("AUXP", "AUXN")
    return None


def execute(
    context: RuleContext,
    graph_api: GraphAPI,
    part_db: PartDB,
    params: Dict[str, Any] = None
) -> Union[List[RuleViolation], RulePass, RuleResult]:
    """
    執行 USB 差分對極性反接與拓撲不對稱雙端合一檢查

    Args:
        context: 執行期上下文 (context.target 為觸發之正極網路節點)
        graph_api: SDK 拓撲查詢介面
        part_db: SDK 零件規格庫查詢介面
        params: YAML 外部參數字典

    Returns:
        Union[List[RuleViolation], RulePass, RuleResult]: 違規報告清單或結構化合格證明物件
    """
    target_net = context.target
    p_net_name = str(target_net.get("net_name") or target_net.get("name") or "")
    violations: List[RuleViolation] = []
    involved_components: set = set()

    # 1. 追蹤 P 端端到端連線 (穿越 AC 耦合電容與串聯匹配電阻)
    p_endpoints = graph_api.trace_differential_end_to_end(target_net)
    for ep in p_endpoints:
        involved_components.add(ep["component"].ref_des)
        for pc in ep.get("passed_components", []):
            involved_components.add(pc.ref_des)

    if len(p_endpoints) == 0:
        violations.append(RuleViolation(
            error_message=f"USB 差分對正極網路 ({p_net_name}) 未連接至任何實體元件引腳，呈現完全懸空 (Floating) 狀態。",
            recommendation="請檢查線路圖是否有未繪製完成的 Net Label，或將未使用的差分訊號線連接至適當終端",
            severity="ERROR",
            evidence={"net_name": p_net_name, "floating": True},
            target_nodes={"nets": [p_net_name]}
        ))

    # --------------------------------------------------------------------------
    # [情境 B]: P 端實體引腳極性反接驗證 (Pin Swap Check)
    # --------------------------------------------------------------------------
    p_ep_audit = []
    for ep in p_endpoints:
        comp = ep["component"]
        pin_name = ep["pin_name"]
        pin_pol = _determine_pin_polarity(pin_name)
        p_ep_audit.append({
            "ref_des": comp.ref_des,
            "part_number": comp.pn,
            "pin": pin_name,
            "pin_polarity": pin_pol,
            "polarity_match": (pin_pol != "N")
        })
        if pin_pol == "N":
            violations.append(RuleViolation(
                error_message=(
                    f"USB 差分對極性反接 (P/N Swap Fault)：正極 (P/DP) 網路 ({p_net_name}) "
                    f"誤連接至元件 {comp.ref_des} ({comp.pn}) 之負極 (N/DM) 引腳 [{pin_name}]！"
                ),
                recommendation=f"請交叉調換元件 {comp.ref_des} 上的差分對走線，確保 {p_net_name} 連接至正極引腳",
                severity="ERROR",
                evidence={
                    "p_net": p_net_name,
                    "faulty_component": comp.ref_des,
                    "faulty_pin": pin_name,
                    "expected_polarity": "P",
                    "actual_polarity": pin_pol,
                },
                target_nodes={
                    "components": [comp.ref_des],
                    "nets": [p_net_name]
                }
            ))

    # 4. 尋找負極 (N/DM) 夥伴網路
    partner_net_name = target_net.get("diff_pair_partner") or _infer_negative_partner_name(p_net_name)
    partner_net_id = graph_api._resolve_node_id(partner_net_name, "net:") if partner_net_name else ""
    if not partner_net_id or not graph_api._G.has_node(partner_net_id):
        if partner_net_name and graph_api._G.has_node(f"net:{partner_net_name}"):
            partner_net_id = f"net:{partner_net_name}"

    partner_node = graph_api._G.nodes[partner_net_id] if (partner_net_id and graph_api._G.has_node(partner_net_id)) else None

    if not partner_node:
        # 若 P 端未反接但缺少夥伴網路，報告缺少負極夥伴
        if not violations:
            violations.append(RuleViolation(
                error_message=f"USB 差分對缺少負極 (N/DM) 夥伴網路：正極網路 ({p_net_name}) 孤立存在，未配對到對應之負極走線。",
                recommendation="請檢查線路圖是否漏繪負極差分線或 Net Label 拼寫有誤，確保 USB 差分對成對繪製。",
                severity="ERROR",
                evidence={
                    "p_net": p_net_name,
                    "expected_partner": partner_net_name,
                    "partner_found": False
                },
                target_nodes={"nets": [p_net_name]}
            ))
        return violations

    n_net_name = str(partner_node.get("net_name") or partner_net_name)

    # 5. 端到端追蹤 N 端
    n_endpoints = graph_api.trace_differential_end_to_end(partner_node)
    for ep in n_endpoints:
        involved_components.add(ep["component"].ref_des)
        for pc in ep.get("passed_components", []):
            involved_components.add(pc.ref_des)

    if len(n_endpoints) == 0:
        violations.append(RuleViolation(
            error_message=f"USB 差分對負極網路 ({n_net_name}) 未連接至任何實體元件引腳，呈現完全懸空 (Floating) 狀態。",
            recommendation="請檢查線路圖是否有未繪製完成的 Net Label，或將未使用的差分訊號線連接至適當終端",
            severity="ERROR",
            evidence={"net_name": n_net_name, "floating": True},
            target_nodes={"nets": [n_net_name]}
        ))

    # [情境 B]: N 端實體引腳極性反接驗證
    n_ep_audit = []
    for ep in n_endpoints:
        comp = ep["component"]
        pin_name = ep["pin_name"]
        pin_pol = _determine_pin_polarity(pin_name)
        n_ep_audit.append({
            "ref_des": comp.ref_des,
            "part_number": comp.pn,
            "pin": pin_name,
            "pin_polarity": pin_pol,
            "polarity_match": (pin_pol != "P")
        })
        if pin_pol == "P":
            violations.append(RuleViolation(
                error_message=(
                    f"USB 差分對極性反接 (P/N Swap Fault)：負極 (N/DM) 網路 ({n_net_name}) "
                    f"誤連接至元件 {comp.ref_des} ({comp.pn}) 之正極 (P/DP) 引腳 [{pin_name}]！"
                ),
                recommendation=f"請交叉調換元件 {comp.ref_des} 上的差分對走線，確保 {n_net_name} 連接至負極引腳",
                severity="ERROR",
                evidence={
                    "p_net": p_net_name,
                    "n_net": n_net_name,
                    "faulty_component": comp.ref_des,
                    "faulty_pin": pin_name,
                    "expected_polarity": "N",
                    "actual_polarity": pin_pol,
                },
                target_nodes={
                    "components": [comp.ref_des],
                    "nets": [p_net_name, n_net_name]
                }
            ))

    # --------------------------------------------------------------------------
    # [情境 C]: P/N 夥伴網路拓撲對稱性驗證 (Differential Asymmetry Check)
    # --------------------------------------------------------------------------
    symmetry_result = graph_api.check_differential_pair_symmetry(target_net, n_net_name)
    if not symmetry_result["is_symmetric"]:
        for reason in symmetry_result["asymmetry_reasons"]:
            violations.append(RuleViolation(
                error_message=f"USB 差分對拓撲不對稱違規 ({p_net_name} ↔ {n_net_name})：{reason}",
                recommendation="請檢查差分對兩端之串聯電阻/電容容值、封裝與接地 TVS 防護規格，確保雙端硬體參數 100% 對稱",
                severity="ERROR",
                evidence={
                    "p_net": p_net_name,
                    "n_net": n_net_name,
                    "asymmetry_reasons": symmetry_result["asymmetry_reasons"],
                    "p_endpoints_count": len(p_endpoints),
                    "n_endpoints_count": len(n_endpoints)
                },
                target_nodes={
                    "components": sorted(list(involved_components)),
                    "nets": [p_net_name, n_net_name]
                }
            ))

    if violations:
        return violations

    # --------------------------------------------------------------------------
    # [合格判定]: 產出結構化 RulePass 審計歷程
    # --------------------------------------------------------------------------
    endpoint_comps_str = ", ".join(sorted(list(involved_components))) if involved_components else "端點IC"
    audit_summary = (
        f"USB 差分對 ({p_net_name} ↔ {n_net_name}) 通過雙端審計：端到端連接至 {endpoint_comps_str}，"
        f"正負極性吻合且 P/N 拓撲完全對稱。"
    )

    p_caps = [c.ref_des for c in symmetry_result.get("p_series_capacitors", [])]
    n_caps = [c.ref_des for c in symmetry_result.get("n_series_capacitors", [])]

    return RulePass(
        evidence={
            "checked_target": f"{p_net_name} ↔ {n_net_name}",
            "pair_type": "USB Differential Pair",
            "p_net": p_net_name,
            "n_net": n_net_name,
            "p_endpoints": p_ep_audit,
            "n_endpoints": n_ep_audit,
            "series_capacitors": {
                "p_caps": p_caps,
                "n_caps": n_caps,
                "symmetric": (p_caps == n_caps or len(p_caps) == len(n_caps))
            },
            "symmetry_check": {
                "is_symmetric": True,
                "endpoints_count_match": (len(p_endpoints) == len(n_endpoints))
            },
            "audit_summary": audit_summary
        },
        target_nodes={
            "components": sorted(list(involved_components)),
            "nets": [p_net_name, n_net_name]
        },
        message=f"USB 差分對 ({p_net_name} ↔ {n_net_name}) 審計合格"
    )
