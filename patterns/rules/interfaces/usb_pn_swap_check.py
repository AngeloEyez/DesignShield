"""
USB 差分對極性反接 (Pin Swap) 與拓撲不對稱性 (Asymmetry) 雙端合一檢查腳本

本腳本為 Level 3 DRC 伴生 Python 腳本，採「P 端主導雙端合一審計 (Unified Differential Inspection)」模型：
1. 檢驗標的：以正極 (P/DP) 網路為入口，自動解析關聯之負極 (N/DM) 夥伴網路。
2. 情境 A (端點正負極性反接 / Pin Swap Check):
   穿越串聯 AC 耦合電容或阻抗匹配電阻，追蹤 P/N 雙端到達的所有端點 IC / 連接器引腳名稱 (Pin Name)。
   若發現正極網路 (P/DP) 誤接至負極引腳 (N/DN) 或負極網路 (N/DM) 誤接至正極引腳，發出 ERROR 告警。
3. 情境 B (拓撲不對稱/懸空/錯位連線 / Differential Asymmetry Check):
   比對 P/N 雙端到達之端點元件數量、引腳配置及途經之 AC 耦合電容數量與容值。
   若發現單邊懸空 (Floating)、兩端連接不同 IC 或串聯電容不對稱，發出 ERROR 告警。
4. 結構化審計 (Evidence Trail) 與端到端鏈路輸出規範:
   本腳本落實「核心契約驅動」架構，【不論判定為 PASS 還是 FAIL，均保證輸出以下標準項目】：
   -------------------------------------------------------------------------------------------------
   【無論 PASS / FAIL 固定必須輸出之欄位清單 (Mandatory Contract Outputs)】:
   1. evidence["covered_nets"]: List[str]
      - 本差分通道所跨越之所有正負極子網段 (包含過 CMC / 電容前後的所有網段，如 USB8_USB20_P, USB8_USB20_CMC_P)。
      - 用途: 提供 Level 3 Runner 進行端到端物理通道靜默去重，避免同一通道因多個中繼網段重複受測。
   2. evidence["channel_title"]: str
      - 端到端通道識別標題 (如 "TJ1 ↔ TU2 ↔ P72 (USB8_USB20 差分通道)")。
   3. evidence["pair_type"]: str
      - 差分通道類別標註 (固定為 "USB Differential Channel")。
   4. evidence["p_net"] / evidence["n_net"]: str
      - 本差分通道之正極與負極主網段名稱。
   5. evidence["topology_flow"] / evidence["n_topology_flow"]: List[Dict]
      - 正極 (P) 與負極 (N) 之結構化拓撲流向階段清單 (包含 endpoints 階段與 pass_through 穿透階段)。
      - 用途: 提供前端 EvidenceDetailsBlock.vue 繪製「差分通道端到端鏈路拓撲」可視化流程。
      - 每個 device 必備包含: ref_des, pin, pin_name, pin_number, part_number, type。
   6. evidence["path_segments"] / evidence["n_path_segments"]: List[Dict]
      - 途經穿透元件段落明細 (包含 from_net, pass_component, in_pin, out_pin, to_net)。
   7. evidence["p_endpoints"] / evidence["n_endpoints"]: List[Dict]
      - 正負雙端到達之所有實體晶片與連接器端點引腳審計紀錄。
   8. evidence["pass_through_components"]: List[str]
      - 本差分通道途經之所有穿透元件代號清單 (如 ["TL1"])，供 UI 標籤展示。
   9. evidence["series_capacitors"]: Dict
      - P/N 雙端串聯 AC 耦合電容清單與對稱性判定。
   10. evidence["symmetry_check"]: Dict
      - 對稱性綜合結論 (is_symmetric, endpoints_count_match)。
   11. target_nodes["components"]: List[str]
      - 參與本通道的所有晶片、連接器與途經穿透元件清單。
   12. target_nodes["nets"]: List[str]
      - 本通道涉及之網段 (至少包含當前受測網段或全通道 covered_nets)。
   -------------------------------------------------------------------------------------------------
   【PASS 特有額外欄位】:
   - evidence["checked_target"]: 通道標題。
   - evidence["audit_summary"]: 結構化合格佐證說明文字。
   -------------------------------------------------------------------------------------------------
   【FAIL 特有額外欄位 (注入至 RuleViolation)】:
   - evidence["faulty_component"]: 發生違規之元件代號 (如 "TJ1")。
   - evidence["faulty_pin"]: 發生違規之邏輯引腳名稱 (如 "DP1")。
   - evidence["faulty_pin_number"]: 發生違規之實體引腳編號 (如 "A6")。
   - evidence["expected_polarity"]: 期望極性 ("P" 或 "N")。
   - evidence["actual_polarity"]: 實際引腳極性 ("P" 或 "N")。
   -------------------------------------------------------------------------------------------------
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

    使用精確詞邊界正規表示式，支援 DP1/DN1/DP2/DN2、SSTXP/N、D+/D- 等變形，
    並嚴格排除 PDN (Power Down)、VDDP、GND 等非差分引腳。
    """
    if not pin_name:
        return None

    pin_clean = str(pin_name).strip()
    pin_upper = pin_clean.upper()

    # 1. 安全排除清單：非差分引腳關鍵字（如 Power Down, 電源, 接地等）
    if re.search(r"(?i)\b(?:PDN|PWRDN|VDDP|VDD|VCC|GND|VSS|AGND|DGND|PGND)\b", pin_clean):
        return None
    if pin_upper.startswith("VDD") or pin_upper.startswith("VCC") or pin_upper.startswith("GND"):
        return None

    # 單純 "P" 或 "N" 引腳
    if pin_upper == "P":
        return "P"
    if pin_upper == "N":
        return "N"

    # 正極模式 (DP, DP1, DP2, D+, SSTXP, SSRXP, TXP, RXP, AUXP, IN+, OUT+)
    # 支援: DP1, DP2, USB_DP, SSTXP1, TX0_P, DP_CON 等
    p_regex = r"(?i)(?:^|[_/-])(?:DP\d*|D\+|SSTX\d*_?P\d*|SSRX\d*_?P\d*|TX\d*_?P\d*|RX\d*_?P\d*|AUXP|IN\+|OUT\+)(?:$|[_/-])"
    # 負極模式 (DM, DN, DN1, DN2, DM1, D-, SSTXN, SSRXN, TXN, RXN, AUXN, IN-, OUT-)
    n_regex = r"(?i)(?:^|[_/-])(?:DN\d*|DM\d*|D\-|SSTX\d*_?N\d*|SSRX\d*_?N\d*|TX\d*_?N\d*|RX\d*_?N\d*|AUXN|IN\-|OUT\-)(?:$|[_/-])"

    is_p = bool(re.search(p_regex, pin_clean))
    is_n = bool(re.search(n_regex, pin_clean))

    if is_p and not is_n:
        return "P"
    if is_n and not is_p:
        return "N"
    return None


def _determine_connector_pin_polarity_fallback(
    comp: Any,
    pin_number: str,
    part_db: Optional[PartDB] = None
) -> Optional[str]:
    """
    當連接器引腳名稱為純數字或 A6/A7 等無語意字串時，依據 PartDB 或 Type-C 國際規範推導極性

    雙層判定機制:
      1. 第一層: 查表 PartDB 連接器規格
      2. 第二層: USB Type-C Receptacle 國際標準腳位 (A6/B6=DP, A7/B7=DN, A2/B2=SSTXP, A3/B3=SSTXN, A11/B11=SSRXP, A10/B10=SSRXN)
    """
    if not pin_number:
        return None

    pnum_upper = str(pin_number).strip().upper()

    # 第一層: 嘗試查詢 PartDB 元件規格庫
    if part_db:
        pn = comp.get("pn") or comp.get("mfg_pn") or comp.get("part_number") or comp.get("part_value")
        mfg = comp.get("mfg") or comp.get("supplier")
        if pn:
            spec = part_db.query(pn=str(pn), mfg=str(mfg) if mfg else None)
            if spec and "pinout" in spec:
                pin_info = spec["pinout"].get(pnum_upper) or spec["pinout"].get(pin_number)
                if pin_info and isinstance(pin_info, dict):
                    pin_name_from_db = pin_info.get("name", "")
                    pol = _determine_pin_polarity(pin_name_from_db)
                    if pol:
                        return pol

    # 第二層: USB Type-C Receptacle 國際標準規範 (USB Type-C Spec Standard Pinout)
    cat = str(comp.get("category", "")).lower()
    sub = str(comp.get("sub_category", "")).lower()
    pkg = str(comp.get("package", "")).upper()
    val = str(comp.get("part_value", "")).upper()
    pn_str = str(comp.get("pn", "") or comp.get("mfg_pn", "")).upper()

    is_connector = "connector" in cat or "connector" in sub
    is_typec = any(tag in pkg or tag in val or tag in pn_str for tag in ["TYPE-C", "TYPE_C", "TYPEC", "USBC"])

    if is_connector and is_typec:
        # USB 2.0 High-Speed
        if pnum_upper in ["A6", "B6"]:
            return "P"
        if pnum_upper in ["A7", "B7"]:
            return "N"
        # USB 3.x SuperSpeed TX
        if pnum_upper in ["A2", "B2"]:
            return "P"
        if pnum_upper in ["A3", "B3"]:
            return "N"
        # USB 3.x SuperSpeed RX
        if pnum_upper in ["A11", "B11"]:
            return "P"
        if pnum_upper in ["A10", "B10"]:
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


def _build_topology_flow(endpoints: List[Dict[str, Any]], segments: List[Dict[str, Any]], start_net: str) -> List[Dict[str, Any]]:
    """
    依據端點與穿透元件段落，建構完整端到端拓撲流向 (Topology Flow Chain)
    格式: [
      { "stage": "endpoints", "net": "...", "devices": [...] },
      { "stage": "pass_through", "component": "...", "in_pin": "...", "out_pin": "...", "from_net": "...", "to_net": "..." },
      { "stage": "endpoints", "net": "...", "devices": [...] },
    ]
    """
    flow: List[Dict[str, Any]] = []
    if not segments:
        flow.append({
            "stage": "endpoints",
            "net": start_net,
            "devices": [
                {
                    "ref_des": ep["ref_des"],
                    "pin": ep.get("pin", ""),
                    "pin_name": ep.get("pin", ""),
                    "pin_number": ep.get("pin_number", ""),
                    "part_number": ep.get("part_number", ""),
                    "type": ep.get("component_type", "")
                }
                for ep in endpoints
            ]
        })
        return flow

    endpoints_by_net: Dict[str, List[Dict[str, Any]]] = {}
    for ep in endpoints:
        net = ep.get("connected_net") or start_net
        if net not in endpoints_by_net:
            endpoints_by_net[net] = []
        endpoints_by_net[net].append({
            "ref_des": ep["ref_des"],
            "pin": ep.get("pin", ""),
            "pin_name": ep.get("pin", ""),
            "pin_number": ep.get("pin_number", ""),
            "part_number": ep.get("part_number", ""),
            "type": ep.get("component_type", "")
        })

    visited_nets = set()
    for idx, seg in enumerate(segments):
        from_net = seg["from_net"]
        to_net = seg["to_net"]

        if from_net not in visited_nets:
            visited_nets.add(from_net)
            flow.append({
                "stage": "endpoints",
                "net": from_net,
                "devices": endpoints_by_net.get(from_net, [])
            })

        flow.append({
            "stage": "pass_through",
            "component": seg["pass_component"],
            "type": seg.get("pass_component_type", "Passive"),
            "in_pin": seg.get("in_pin", ""),
            "out_pin": seg.get("out_pin", ""),
            "from_net": from_net,
            "to_net": to_net,
        })

        if to_net not in visited_nets and (idx == len(segments) - 1 or segments[idx + 1]["from_net"] != to_net):
            visited_nets.add(to_net)
            flow.append({
                "stage": "endpoints",
                "net": to_net,
                "devices": endpoints_by_net.get(to_net, [])
            })

    return flow


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
        pin_number = ep.get("pin_number", "")
        pin_pol = _determine_pin_polarity(pin_name)
        if not pin_pol:
            pin_pol = _determine_connector_pin_polarity_fallback(comp, pin_number, part_db)

        pin_display = f"{pin_name} (Pin {pin_number})" if pin_number and pin_number != pin_name else pin_name
        term_net_name = ep["terminal_net"].net_name if ep.get("terminal_net") else ""
        comp_cat = str(comp.get("category") or comp.get("sub_category") or "")
        p_ep_audit.append({
            "ref_des": comp.ref_des,
            "part_number": comp.pn,
            "pin": pin_name,
            "pin_number": pin_number,
            "pin_polarity": pin_pol,
            "polarity_match": (pin_pol != "N"),
            "connected_net": term_net_name,
            "component_type": comp_cat,
        })
        if pin_pol == "N":
            violations.append(RuleViolation(
                error_message=(
                    f"USB 差分對極性反接 (P/N Swap Fault)：正極 (P/DP) 網路 ({p_net_name}) "
                    f"誤連接至元件 {comp.ref_des} ({comp.pn}) 之負極 (N/DM) 引腳 [{pin_display}]！"
                ),
                recommendation=f"請交叉調換元件 {comp.ref_des} 上的差分對走線，確保 {p_net_name} 連接至正極引腳",
                severity="ERROR",
                evidence={
                    "p_net": p_net_name,
                    "faulty_component": comp.ref_des,
                    "faulty_pin": pin_name,
                    "faulty_pin_number": pin_number,
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
        all_covered = [p_net_name]
        for ep in p_endpoints:
            all_covered.extend(ep.get("covered_nets", []))
        covered_nets = list(dict.fromkeys(all_covered))
        for v in violations:
            if isinstance(v.evidence, dict):
                v.evidence["covered_nets"] = covered_nets
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

    # [情境 A]: N 端實體引腳極性反接驗證
    n_ep_audit = []
    for ep in n_endpoints:
        comp = ep["component"]
        pin_name = ep["pin_name"]
        pin_number = ep.get("pin_number", "")
        pin_pol = _determine_pin_polarity(pin_name)
        if not pin_pol:
            pin_pol = _determine_connector_pin_polarity_fallback(comp, pin_number, part_db)

        pin_display = f"{pin_name} (Pin {pin_number})" if pin_number and pin_number != pin_name else pin_name
        term_net_name = ep["terminal_net"].net_name if ep.get("terminal_net") else ""
        comp_cat = str(comp.get("category") or comp.get("sub_category") or "")
        n_ep_audit.append({
            "ref_des": comp.ref_des,
            "part_number": comp.pn,
            "pin": pin_name,
            "pin_number": pin_number,
            "pin_polarity": pin_pol,
            "polarity_match": (pin_pol != "P"),
            "connected_net": term_net_name,
            "component_type": comp_cat,
        })
        if pin_pol == "P":
            violations.append(RuleViolation(
                error_message=(
                    f"USB 差分對極性反接 (P/N Swap Fault)：負極 (N/DM) 網路 ({n_net_name}) "
                    f"誤連接至元件 {comp.ref_des} ({comp.pn}) 之正極 (P/DP) 引腳 [{pin_display}]！"
                ),
                recommendation=f"請交叉調換元件 {comp.ref_des} 上的差分對走線，確保 {n_net_name} 連接至負極引腳",
                severity="ERROR",
                evidence={
                    "p_net": p_net_name,
                    "n_net": n_net_name,
                    "faulty_component": comp.ref_des,
                    "faulty_pin": pin_name,
                    "faulty_pin_number": pin_number,
                    "expected_polarity": "N",
                    "actual_polarity": pin_pol,
                },
                target_nodes={
                    "components": [comp.ref_des],
                    "nets": [p_net_name, n_net_name]
                }
            ))

    # --------------------------------------------------------------------------
    # [情境 B]: P/N 夥伴網路拓撲對稱性驗證 (Differential Asymmetry Check)
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

    # --------------------------------------------------------------------------
    # 產出結構化端到端通道拓撲與審計歷程 (無論合格或違規均具備完整鏈路拓撲)
    # --------------------------------------------------------------------------
    all_covered = [p_net_name]
    if partner_node:
        all_covered.append(n_net_name)
    for ep in p_endpoints + n_endpoints:
        all_covered.extend(ep.get("covered_nets", []))
    if symmetry_result and "covered_nets" in symmetry_result:
        all_covered.extend(symmetry_result.get("covered_nets", []))
    covered_nets = list(dict.fromkeys(all_covered))

    # 提取頭尾端點元件 (如 P72 ↔ TJ1)
    ep_comps = [ep["component"].ref_des for ep in p_endpoints if ep.get("component")]
    head_tail_str = " ↔ ".join(ep_comps) if ep_comps else "端點IC ↔ 連接器"

    # 推導主通道名稱 (例如 USB8_USB20_P -> USB8_USB20)
    base_channel = re.sub(r"(?i)(?:_P|_DP|DP|D\+)$", "", p_net_name)
    clean_channel = re.sub(r"(?i)(?:_CMC|_C)$", "", base_channel)
    channel_title = f"{head_tail_str} ({clean_channel} 差分通道)"

    # 途經穿透元件資訊 (如 TL1 共模扼流圈 / CMC)
    pass_comps = [c.ref_des for ep in p_endpoints for c in ep.get("pass_through_components", [])]
    pass_comps_unique = list(dict.fromkeys(pass_comps))
    pass_desc = f"（途經 {', '.join(pass_comps_unique)} 穿透元件）" if pass_comps_unique else ""

    p_caps = [c.ref_des for c in symmetry_result.get("p_series_capacitors", [])]
    n_caps = [c.ref_des for c in symmetry_result.get("n_series_capacitors", [])]

    p_segs = symmetry_result.get("p_path_segments", [])
    n_segs = symmetry_result.get("n_path_segments", [])
    p_flow = _build_topology_flow(p_ep_audit, p_segs, p_net_name)
    n_flow = _build_topology_flow(n_ep_audit, n_segs, n_net_name)

    # 包含途經穿透元件與端點元件之全通道元件清單
    all_channel_components = sorted(list(involved_components.union(set(pass_comps_unique))))

    # --------------------------------------------------------------------------
    # [核心契約宣告 - 不論 PASS 或 FAIL 均必須輸出的固定結構化欄位]
    # 提供前端 EvidenceDetailsBlock.vue 繪製鏈路拓撲與 Level 3 Runner 執行通道去重
    # --------------------------------------------------------------------------
    channel_evidence = {
        "channel_title": channel_title,
        "pair_type": "USB Differential Channel",
        "p_net": p_net_name,
        "n_net": n_net_name,
        "covered_nets": covered_nets,
        "path_segments": p_segs,
        "n_path_segments": n_segs,
        "topology_flow": p_flow,
        "n_topology_flow": n_flow,
        "p_endpoints": p_ep_audit,
        "n_endpoints": n_ep_audit,
        "pass_through_components": pass_comps_unique,
        "series_capacitors": {
            "p_caps": p_caps,
            "n_caps": n_caps,
            "symmetric": (p_caps == n_caps or len(p_caps) == len(n_caps))
        },
        "symmetry_check": {
            "is_symmetric": symmetry_result["is_symmetric"],
            "endpoints_count_match": (len(p_endpoints) == len(n_endpoints))
        }
    }

    if violations:
        for v in violations:
            if isinstance(v.evidence, dict):
                for k, val in channel_evidence.items():
                    if k not in v.evidence:
                        v.evidence[k] = val
        return violations

    # --------------------------------------------------------------------------
    # [合格判定]: 產出結構化 RulePass 端到端通道審計歷程
    # --------------------------------------------------------------------------
    audit_summary = (
        f"USB 差分通道 [{channel_title}] 通過雙端審計：端到端連接至 {head_tail_str}{pass_desc}，"
        f"各網段正負極性吻合且 P/N 拓撲完全對稱。"
    )

    pass_evidence = dict(channel_evidence)
    pass_evidence["checked_target"] = channel_title
    pass_evidence["audit_summary"] = audit_summary

    return RulePass(
        evidence=pass_evidence,
        target_nodes={
            "components": all_channel_components,
            "nets": covered_nets
        },
    )
