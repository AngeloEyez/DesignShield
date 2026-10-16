"""
================================================================================
USB 高速差分對極性反接 (Pin Swap) 與拓撲不對稱性 (Asymmetry) 雙端合一檢查腳本
(兼 DesignShield Level 3 DRC 伴生腳本標準範本 / Companion Script Reference Template)
================================================================================

【一、本規則業務範疇 (Rule Domain Scope)】
1. 檢驗範圍：僅針對 USB 高速差分信號（USB 2.0 D+/D- 與 USB 3.x/USB4 SuperSpeed TX/RX），
   不包含低速旁帶信號（如 SBU / AUX）。
2. 檢驗模型：採「P 端主導雙端合一審計 (Unified Differential Inspection)」：
   - 由正極 (P/DP) 網路觸發單一檢驗任務，腳本自動解析關聯之負極 (N/DM/DN) 夥伴網路。
   - 情境 A (端點引腳極性反接 / Pin Swap Check)：
     穿越串聯 AC 耦合電容、匹配電阻或共模扼流圈 (CMC)，追蹤 P/N 雙端到達的所有端點
     IC / 連接器引腳，若正極連至負極引腳或負極連至正極引腳，發出 ERROR 告警。
   - 情境 B (拓撲不對稱與懸空 / Differential Asymmetry Check)：
     比對 P/N 雙端到達之端點元件數量、引腳配置及串聯被動元件是否 100% 對稱。

================================================================================
【二、Level 3 伴生腳本標準架構：五階段流水線 (5-Stage Pipeline Template)】
後續 AI 或開發者撰寫新的 Level 3 伴生腳本時，請遵循本範本的五大標準階段：
  - Stage 1 [目標解析與前置守衛]: 從 context.target 提取受測節點，驗證前置條件並解析夥伴節點。
  - Stage 2 [拓撲展開與通道收集]: 呼叫 GraphAPI 展開電路拓撲，收集途經網段 (covered_nets) 與元件。
  - Stage 3 [核心領域規則檢驗]  : 執行電氣/連線/規格比對，將違規統一收集至 violations 清單（避免中途零散 return）。
  - Stage 4 [三層佐證資料建構]  : 呼叫獨立 Evidence 建構函式，組裝符合三層契約的 evidence 字典。
  - Stage 5 [統一結果封裝與回傳]: 呼叫統一封裝函式，回傳 List[RuleViolation]、RulePass 或 RuleResult.SKIPPED。

================================================================================
【三、三層回傳契約規範 (3-Tier Return Contract Specification)】
伴生腳本回傳之 RulePass / RuleViolation 物件，其資料結構分為以下三個層級：

  ┌────────────────────────────────────────────────────────────────────────────┐
  │ 【Tier 1：引擎必填核心契約 (Mandatory Engine Contract)】(所有腳本 100% 必備) │
  └────────────────────────────────────────────────────────────────────────────┘
  1. 入口函式簽名：
     `execute(context: RuleContext, graph_api: GraphAPI, part_db: PartDB, params: Dict[str, Any] = None)`
  2. 回傳型別：
     - 合格：`RulePass(evidence={...}, target_nodes={...}, message="...")`
     - 違規：`RuleViolation(...)` 或 `List[RuleViolation]`
     - 略過：`RuleResult.SKIPPED`
  3. `target_nodes` 結構 (供前端點擊高亮與節點定位)：
     `{"components": List[str], "nets": List[str]}`
  4. `evidence["checked_target"]`: str
     - 當前受測標的或通道的人類易讀識別名稱（RulePass 必備，若未填則由引擎自動補入節點 ID）。

  ┌────────────────────────────────────────────────────────────────────────────┐
  │ 【Tier 2：跨網段/通道去重契約 (Channel Deduplication Contract)】           │
  │ (凡會穿透串聯元件或同時檢驗成對網路的規則必備)                             │
  └────────────────────────────────────────────────────────────────────────────┘
  1. `evidence["covered_nets"]`: List[str]
     - 列出本次檢查已涵蓋的所有網段名稱（例如穿越 CMC/電容前後的子網段、以及配對的 N 端網段）。
     - 引擎行為：`Level3Engine` (level3_runner.py) 會在單次檢查完成後讀取此清單並註冊至
       `visited_channel_targets`，自動跳過同一物理通道後續子網段的重複觸發。
     - 注意：不論最終回傳 `RulePass` 或 `RuleViolation`，皆必須在 `evidence` 中包含 `covered_nets`！

  ┌────────────────────────────────────────────────────────────────────────────┐
  │ 【Tier 3：前端 UI 視覺化擴充契約 (UI Visualization Schema)】               │
  │ (由前端 EvidenceDetailsBlock.vue 自動識別渲染，依規則性質選用對應欄位)     │
  └────────────────────────────────────────────────────────────────────────────┘
  A. [通用審計結論卡片] (建議所有規則於 PASS 時填寫)：
     - `evidence["audit_summary"]`: str (顯示於綠色「量測審計結論」區塊)

  B. [差分/多段通道鏈路拓撲圖] (本腳本示範，適用於高速訊號/匯流排端到端追蹤規則)：
     - `evidence["channel_title"]`: str (通道標題)
     - `evidence["p_net"]` / `evidence["n_net"]`: str (正/負極主網段名稱)
     - `evidence["topology_flow"]` / `evidence["n_topology_flow"]`: List[Dict] (端點與穿透元件流向鏈)
     - `evidence["path_segments"]` / `evidence["n_path_segments"]`: List[Dict] (穿透段落明細)
     - `evidence["p_endpoints"]` / `evidence["n_endpoints"]`: List[Dict] (端點引腳審計明細)
     - `evidence["pass_through_components"]`: List[str] (途經穿透元件 RefDes 清單，顯示為 UI 標籤)
     - `evidence["symmetry_check"]`: Dict (`{"is_symmetric": bool, "endpoints_count_match": bool}`)

  C. [被動元件/電阻參數卡片] (適用於上拉/下拉電阻、串聯阻值檢查，如 i2c_pullup_existence.py)：
     - `evidence["resistors"]`: List[Dict]
       每個元素格式：`{"ref_des": str, "part_value": str, "resistance_ohm": float, "power_rail": str, "compliant": bool}`
================================================================================
"""

import re
from typing import Dict, List, Any, Union, Optional, Tuple
from designshield.sdk import (
    RuleResult,
    RulePass,
    RuleViolation,
    RuleContext,
    GraphAPI,
    PartDB,
    TopologyGraphBuilder,
)


# ==============================================================================
# SECTION 1: 領域知識與極性推導輔助函式 (Domain Helper Functions)
# ==============================================================================

def _determine_net_polarity(net_name: str, net_attr_polarity: Optional[str] = None) -> Optional[str]:
    """
    判定 USB 高速差分網路名稱之極性 (P: 正極, N: 負極, None: 無法判定)

    優先採用圖譜節點已標註之 `diff_polarity` 屬性；若無則使用僅針對 USB 2.0 與
    USB 3.x/USB4 SuperSpeed 信號之正規表示式進行推導（不包含 AUX 信號）。

    @param {str} net_name - 待判定的網路名稱
    @param {Optional[str]} net_attr_polarity - 圖譜節點上預先標註的極性屬性 ("P" 或 "N")
    @returns {Optional[str]} 推導出的極性字串 ("P"、"N" 或 None)
    """
    if net_attr_polarity in ["P", "N"]:
        return net_attr_polarity

    # 正極模式：涵蓋 USB 2.0 (DP, D+) 與 USB 3.x/4 SuperSpeed (SSTX_P, SSRX_P, TX_P, RX_P, _P)
    p_regex = r"(?i)(?:_DP\b|DP\b|D\+|SSTX.*_P|SSRX.*_P|TX.*_P|RX.*_P|_P$)"
    # 負極模式：涵蓋 USB 2.0 (DN, DM, D-) 與 USB 3.x/4 SuperSpeed (SSTX_N, SSRX_N, TX_N, RX_N, _N)
    n_regex = r"(?i)(?:_DN\b|_DM\b|DM\b|D\-|SSTX.*_N|SSRX.*_N|TX.*_N|RX.*_N|_N$)"

    if re.search(p_regex, net_name):
        return "P"
    if re.search(n_regex, net_name):
        return "N"
    return None


def _determine_pin_polarity(pin_name: str) -> Optional[str]:
    """
    判定元件實體引腳名稱之極性 (P: 正極, N: 負極, None: 無法判定)

    使用精確詞邊界正規表示式，支援 USB 2.0 (DP1/DN1/DP2/DN2/D+/D-) 與
    USB 3.x/4 SuperSpeed (SSTXP/N, SSRXP/N, TXP/N, RXP/N) 等變形，
    並嚴格排除 PDN (Power Down)、VDDP、GND 等非差分引腳，亦不納入 AUX 引腳。

    @param {str} pin_name - 元件引腳名稱
    @returns {Optional[str]} 推導出的引腳極性 ("P"、"N" 或 None)
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

    # 2. 單純 "P" 或 "N" 引腳
    if pin_upper == "P":
        return "P"
    if pin_upper == "N":
        return "N"

    # 3. USB 高速差分正極與負極模式（涵蓋 USB 2.0 DP/DN/DM、D1P/D1M/D2P/D2M 與 SuperSpeed SSTX/SSRX，不含 AUX）
    p_regex = r"(?i)(?:^|[_/-])(?:DP\d*|D\d*P\d*|D\+|SSTX\d*_?P\d*|SSRX\d*_?P\d*|TX\d*_?P\d*|RX\d*_?P\d*|IN\+|OUT\+)(?:$|[_/-])"
    n_regex = r"(?i)(?:^|[_/-])(?:DN\d*|DM\d*|D\d*N\d*|D\d*M\d*|D\-|SSTX\d*_?N\d*|SSRX\d*_?N\d*|TX\d*_?N\d*|RX\d*_?N\d*|IN\-|OUT\-)(?:$|[_/-])"

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
    當連接器引腳名稱為純數字或 A6/A7 等腳位代號時，依據 PartDB 或 USB Type-C 國際規範推導極性

    雙層判定機制：
      1. 第一層：查表 PartDB 連接器規格庫中的 `pinout` 映射。
      2. 第二層：USB Type-C Receptacle 國際標準高速差分腳位
         - USB 2.0 High-Speed: A6/B6 (Dp1/Dp2 = P), A7/B7 (Dn1/Dn2 = N)
         - USB 3.x/4 SuperSpeed TX: A2/B2 (SSTXp1/p2 = P), A3/B3 (SSTXn1/n2 = N)
         - USB 3.x/4 SuperSpeed RX: A11/B11 (SSRXp2/p1 = P), A10/B10 (SSRXn2/n1 = N)
         (註：不包含 A8/B8 SBU/AUX 旁帶腳位)

    @param {Any} comp - 元件節點資料物件或字典
    @param {str} pin_number - 實體腳位編號 (如 "A6", "B7")
    @param {Optional[PartDB]} part_db - 零件資料庫查詢實例
    @returns {Optional[str]} 推導出的引腳極性 ("P"、"N" 或 None)
    """
    if not pin_number:
        return None

    pnum_upper = str(pin_number).strip().upper()

    # 第一層：嘗試查詢 PartDB 元件規格庫
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

    # 第二層：USB Type-C Receptacle 國際標準高速差分腳位 (不含 SBU A8/B8)
    cat = str(comp.get("category", "")).lower()
    sub = str(comp.get("sub_category", "")).lower()
    pkg = str(comp.get("package", "")).upper()
    val = str(comp.get("part_value", "")).upper()
    pn_str = str(comp.get("pn", "") or comp.get("mfg_pn", "")).upper()

    is_connector = "connector" in cat or "connector" in sub
    is_typec = any(tag in pkg or tag in val or tag in pn_str for tag in ["TYPE-C", "TYPE_C", "TYPEC", "USBC"])

    if is_connector and is_typec:
        # USB 2.0 High-Speed (D+ / D-)
        if pnum_upper in ["A6", "B6"]:
            return "P"
        if pnum_upper in ["A7", "B7"]:
            return "N"
        # USB 3.x / USB4 SuperSpeed TX
        if pnum_upper in ["A2", "B2"]:
            return "P"
        if pnum_upper in ["A3", "B3"]:
            return "N"
        # USB 3.x / USB4 SuperSpeed RX
        if pnum_upper in ["A11", "B11"]:
            return "P"
        if pnum_upper in ["A10", "B10"]:
            return "N"

    return None


def _infer_negative_partner_name(p_net_name: str) -> Optional[str]:
    """
    由 USB 高速正極差分網路名稱推導對應之負極夥伴網路名稱（不包含 AUX）

    @param {str} p_net_name - 正極網路名稱
    @returns {Optional[str]} 推導出的負極網路名稱，若無法推導則回傳 None
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
    if "D+" in p_net_name:
        return p_net_name.replace("D+", "D-")
    return None


def _format_channel_title(p_net_name: str, p_endpoints: List[Dict[str, Any]]) -> Tuple[str, str]:
    """
    產生人類易讀的端到端差分通道標題與頭尾端點字串

    @param {str} p_net_name - 正極網路名稱 (如 "USB8_USB20_P")
    @param {List[Dict[str, Any]]} p_endpoints - 正極端到端追蹤結果清單
    @returns {Tuple[str, str]} (channel_title, head_tail_str)，如 ("P72 ↔ TJ1 (USB8_USB20 差分通道)", "P72 ↔ TJ1")
    """
    ep_comps = [ep["component"].ref_des for ep in p_endpoints if ep.get("component")]
    head_tail_str = " ↔ ".join(ep_comps) if ep_comps else "端點IC ↔ 連接器"

    base_channel = re.sub(r"(?i)(?:_P|_DP|DP|D\+)$", "", p_net_name)
    clean_channel = re.sub(r"(?i)(?:_CMC|_C)$", "", base_channel)
    channel_title = f"{head_tail_str} ({clean_channel} 差分通道)"
    return channel_title, head_tail_str


# ==============================================================================
# SECTION 2: 拓撲展開與核心規則檢驗子函式 (Topology & Auditing Sub-routines)
# ==============================================================================

def _resolve_negative_partner_node(
    graph_api: GraphAPI,
    target_net: Any,
    p_net_name: str
) -> Tuple[Optional[str], Optional[Any]]:
    """
    [Stage 1 輔助] 解析並取得圖譜中的負極 (N/DM/DN) 夥伴網路節點

    @param {GraphAPI} graph_api - SDK 圖譜查詢介面
    @param {Any} target_net - 觸發規則的正極網路節點
    @param {str} p_net_name - 正極網路名稱
    @returns {Tuple[Optional[str], Optional[Any]]} (期望或實際的負極網路名稱, 圖譜中的負極節點或 None)
    """
    partner_net_name = target_net.get("diff_pair_partner") or _infer_negative_partner_name(p_net_name)
    if not partner_net_name:
        return None, None

    partner_net_id = graph_api._resolve_node_id(partner_net_name, "net:")
    if not partner_net_id or not graph_api._G.has_node(partner_net_id):
        if graph_api._G.has_node(f"net:{partner_net_name}"):
            partner_net_id = f"net:{partner_net_name}"

    partner_node = (
        graph_api._G.nodes[partner_net_id]
        if (partner_net_id and graph_api._G.has_node(partner_net_id))
        else None
    )
    actual_n_name = str(partner_node.get("net_name") or partner_net_name) if partner_node else str(partner_net_name)
    return actual_n_name, partner_node


def _audit_single_polarity_endpoints(
    endpoints: List[Dict[str, Any]],
    net_name: str,
    expected_polarity: str,
    p_net_name: str,
    n_net_name: Optional[str],
    part_db: PartDB
) -> Tuple[List[Dict[str, Any]], List[RuleViolation]]:
    """
    [Stage 3 輔助] 審計單一極性鏈路 (P 端或 N 端) 的懸空狀態與端點引腳極性反接 (Pin Swap)

    @param {List[Dict[str, Any]]} endpoints - `trace_differential_end_to_end` 回傳的端點清單
    @param {str} net_name - 當前受審計的網路名稱
    @param {str} expected_polarity - 期望極性 ("P" 或 "N")
    @param {str} p_net_name - 正極主網路名稱
    @param {Optional[str]} n_net_name - 負極主網路名稱 (若存在)
    @param {PartDB} part_db - 零件規格庫查詢介面
    @returns {Tuple[List[Dict[str, Any]], List[RuleViolation]]} (端點審計紀錄清單, 發現的違規清單)
    """
    ep_audit: List[Dict[str, Any]] = []
    side_violations: List[RuleViolation] = []

    polarity_label = "正極" if expected_polarity == "P" else "負極"
    opposite_polarity = "N" if expected_polarity == "P" else "P"

    # 1. 檢查是否完全懸空 (Floating)
    if len(endpoints) == 0:
        side_violations.append(RuleViolation(
            error_message=f"USB 差分對{polarity_label}網路 ({net_name}) 未連接至任何實體元件引腳，呈現完全懸空 (Floating) 狀態。",
            recommendation="請檢查線路圖是否有未繪製完成的 Net Label，或將未使用的差分訊號線連接至適當終端",
            severity="ERROR",
            evidence={"net_name": net_name, "floating": True},
            target_nodes={"nets": [net_name]}
        ))
        return ep_audit, side_violations

    # 2. 逐一檢查到達端點的引腳極性是否反接
    for ep in endpoints:
        comp = ep["component"]
        pin_name = ep["pin_name"]
        pin_number = ep.get("pin_number", "")
        pin_pol = _determine_pin_polarity(pin_name)
        if not pin_pol:
            pin_pol = _determine_connector_pin_polarity_fallback(comp, pin_number, part_db)

        pin_display = f"{pin_name} (Pin {pin_number})" if pin_number and pin_number != pin_name else pin_name
        term_net_name = ep["terminal_net"].net_name if ep.get("terminal_net") else ""
        comp_cat = str(comp.get("category") or comp.get("sub_category") or "")
        is_mounted = getattr(comp, "is_mounted", True)
        if isinstance(comp, dict) and "is_mounted" in comp:
            is_mounted = bool(comp["is_mounted"])

        comp_bom = getattr(comp, "bom", "I")
        ep_audit.append({
            "ref_des": comp.ref_des,
            "part_number": comp.pn,
            "pin": pin_name,
            "pin_number": pin_number,
            "pin_polarity": pin_pol,
            "polarity_match": (pin_pol != opposite_polarity),
            "connected_net": term_net_name,
            "component_type": comp_cat,
            "is_mounted": is_mounted,
            "bom": comp_bom,
        })

        # 若引腳極性與網路極性相反，產生 Pin Swap 違規
        if pin_pol == opposite_polarity:
            tag = comp_bom if comp_bom in {"P", "M"} else "X"
            ref_label = getattr(comp, "display_ref_des", f"{comp.ref_des} [{tag}]" if not is_mounted else comp.ref_des)
            unmounted_note = f"（此元件在當前 Config 下標註為未上件 [{tag}]，但走線反接仍屬嚴重線路錯誤）" if not is_mounted else ""
            if expected_polarity == "P":
                err_msg = (
                    f"USB 差分對極性反接 (P/N Swap Fault)：正極 (P/DP) 網路 ({p_net_name}) "
                    f"誤連接至元件 {ref_label} ({comp.pn}) 之負極 (N/DM) 引腳 [{pin_display}]！{unmounted_note}"
                )
                rec_msg = f"請交叉調換元件 {comp.ref_des} 上的差分對走線，確保 {p_net_name} 連接至正極引腳"
                ev_dict = {
                    "p_net": p_net_name,
                    "faulty_component": comp.ref_des,
                    "faulty_pin": pin_name,
                    "faulty_pin_number": pin_number,
                    "expected_polarity": "P",
                    "actual_polarity": pin_pol,
                    "is_mounted": is_mounted,
                    "bom": comp_bom,
                }
                t_nets = [p_net_name]
            else:
                err_msg = (
                    f"USB 差分對極性反接 (P/N Swap Fault)：負極 (N/DM) 網路 ({n_net_name}) "
                    f"誤連接至元件 {ref_label} ({comp.pn}) 之正極 (P/DP) 引腳 [{pin_display}]！{unmounted_note}"
                )
                rec_msg = f"請交叉調換元件 {comp.ref_des} 上的差分對走線，確保 {n_net_name} 連接至負極引腳"
                ev_dict = {
                    "p_net": p_net_name,
                    "n_net": n_net_name,
                    "faulty_component": comp.ref_des,
                    "faulty_pin": pin_name,
                    "faulty_pin_number": pin_number,
                    "expected_polarity": "N",
                    "actual_polarity": pin_pol,
                    "is_mounted": is_mounted,
                    "bom": comp_bom,
                }
                t_nets = [p_net_name, n_net_name] if n_net_name else [p_net_name]

            side_violations.append(RuleViolation(
                error_message=err_msg,
                recommendation=rec_msg,
                severity="ERROR",
                evidence=ev_dict,
                target_nodes={
                    "components": [comp.ref_des],
                    "nets": t_nets
                }
            ))

    return ep_audit, side_violations


# ==============================================================================
# SECTION 3: 標準佐證與結果封裝建構器 (Evidence & Result Builders)
# ==============================================================================

def _build_channel_universal_topology(
    channel_title: str,
    p_net_name: str,
    n_net_name: str,
    p_endpoints: List[Dict[str, Any]],
    n_endpoints: List[Dict[str, Any]],
    p_segs: List[Dict[str, Any]],
    n_segs: List[Dict[str, Any]],
    symmetry_result: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    [Stage 4 通用拓撲建構函式] 建構符合 UniversalTopologyData 規格的標準電路拓撲圖

    @param {str} channel_title - 通道標題
    @param {str} p_net_name - 正極主網段名稱
    @param {str} n_net_name - 負極主網段名稱
    @param {List[Dict[str, Any]]} p_endpoints - 正極端點審計清單
    @param {List[Dict[str, Any]]} n_endpoints - 負極端點審計清單
    @param {List[Dict[str, Any]]} p_segs - 正極穿透段落清單
    @param {List[Dict[str, Any]]} n_segs - 負極穿透段落清單
    @param {Optional[Dict[str, Any]]} symmetry_result - 對稱性檢驗結果
    @returns {Dict[str, Any]} 符合 UniversalTopologyData 契約之標準拓撲字典
    """
    builder = TopologyGraphBuilder(title=channel_title, channel_type="differential")
    builder.add_rail("p_rail", f"正極軌道 ({p_net_name})", polarity="P")
    if n_net_name:
        builder.add_rail("n_rail", f"負極軌道 ({n_net_name})", polarity="N")

    def _populate_rail(
        rail_id: str,
        start_net: str,
        endpoints: List[Dict[str, Any]],
        segments: List[Dict[str, Any]]
    ):
        if not start_net and not endpoints:
            return

        endpoints_by_net: Dict[str, List[Dict[str, Any]]] = {}
        for ep in endpoints:
            net = ep.get("connected_net") or start_net
            endpoints_by_net.setdefault(net, []).append(ep)
            builder.add_terminal(
                id=ep["ref_des"],
                ref_des=ep["ref_des"],
                category=ep.get("component_type") or ep.get("type") or "IC",
                part_number=ep.get("part_number"),
                is_mounted=bool(ep.get("is_mounted", True)),
                bom=ep.get("bom"),
                pins=[{
                    "pin_number": ep.get("pin_number") or ep.get("pin") or "",
                    "pin_name": ep.get("pin") or ep.get("pin_name") or ""
                }]
            )

        if not segments:
            if len(endpoints) >= 2:
                builder.add_connection(
                    net_name=start_net,
                    rail_id=rail_id,
                    from_node=endpoints[0]["ref_des"],
                    from_pin=endpoints[0].get("pin_number") or endpoints[0].get("pin") or "1",
                    to_node=endpoints[1]["ref_des"],
                    to_pin=endpoints[1].get("pin_number") or endpoints[1].get("pin") or "1"
                )
            return

        for seg in segments:
            builder.add_series_component(
                id=seg["pass_component"],
                ref_des=seg["pass_component"],
                category=seg.get("pass_component_type", "Passive"),
                in_pin=seg.get("in_pin", "1"),
                out_pin=seg.get("out_pin", "2"),
                is_mounted=bool(seg.get("is_mounted", True)),
                bom=seg.get("bom")
            )

        # 1. 起始端點 -> 第一顆穿透元件
        first_seg = segments[0]
        start_eps = endpoints_by_net.get(first_seg["from_net"], [])
        if start_eps:
            for ep in start_eps:
                builder.add_connection(
                    net_name=first_seg["from_net"],
                    rail_id=rail_id,
                    from_node=ep["ref_des"],
                    from_pin=ep.get("pin_number") or ep.get("pin") or "1",
                    to_node=first_seg["pass_component"],
                    to_pin=first_seg.get("in_pin", "1")
                )

        # 2. 穿透元件串聯段落之間
        for i in range(len(segments) - 1):
            curr_seg = segments[i]
            next_seg = segments[i + 1]
            builder.add_connection(
                net_name=curr_seg["to_net"],
                rail_id=rail_id,
                from_node=curr_seg["pass_component"],
                from_pin=curr_seg.get("out_pin", "2"),
                to_node=next_seg["pass_component"],
                to_pin=next_seg.get("in_pin", "1")
            )

        # 3. 最後一顆穿透元件 -> 終端端點
        last_seg = segments[-1]
        end_eps = endpoints_by_net.get(last_seg["to_net"], [])
        if end_eps:
            for ep in end_eps:
                builder.add_connection(
                    net_name=last_seg["to_net"],
                    rail_id=rail_id,
                    from_node=last_seg["pass_component"],
                    from_pin=last_seg.get("out_pin", "2"),
                    to_node=ep["ref_des"],
                    to_pin=ep.get("pin_number") or ep.get("pin") or "1"
                )

    _populate_rail("p_rail", p_net_name, p_endpoints, p_segs)
    if n_net_name:
        _populate_rail("n_rail", n_net_name, n_endpoints, n_segs)

    if symmetry_result:
        builder.set_metadata({
            "is_symmetric": bool(symmetry_result.get("is_symmetric", False)),
            "endpoints_count_match": (len(p_endpoints) == len(n_endpoints))
        })

    return builder.to_dict()


def _build_channel_evidence(
    p_net_name: str,
    n_net_name: str,
    covered_nets: List[str],
    p_endpoints: List[Dict[str, Any]],
    n_endpoints: List[Dict[str, Any]],
    p_ep_audit: List[Dict[str, Any]],
    n_ep_audit: List[Dict[str, Any]],
    symmetry_result: Optional[Dict[str, Any]]
) -> Tuple[Dict[str, Any], str, str, List[str]]:
    """
    [Stage 4 核心函式] 統一建構符合「三層回傳契約」的結構化佐證字典 (Evidence Dictionary)

    將 Tier 1 (checked_target)、Tier 2 (covered_nets) 與 Tier 3 (UI 拓撲鏈路欄位) 集中於此處組裝，
    確保不論最終判定為 PASS 或 FAIL，回傳的佐證結構 100% 完整且一致。

    @param {str} p_net_name - 正極主網段名稱
    @param {str} n_net_name - 負極主網段名稱 (若缺失則為空字串)
    @param {List[str]} covered_nets - 本通道涵蓋的所有子網段清單 (Tier 2 去重契約)
    @param {List[Dict[str, Any]]} p_endpoints - 正極原始追蹤端點清單
    @param {List[Dict[str, Any]]} n_endpoints - 負極原始追蹤端點清單
    @param {List[Dict[str, Any]]} p_ep_audit - 正極端點極性審計紀錄
    @param {List[Dict[str, Any]]} n_ep_audit - 負極端點極性審計紀錄
    @param {Optional[Dict[str, Any]]} symmetry_result - 雙端對稱性檢驗結果字典
    @returns {Tuple[Dict[str, Any], str, str, List[str]]} (channel_evidence, channel_title, pass_desc, pass_comps_unique)
    """
    channel_title, _ = _format_channel_title(p_net_name, p_endpoints)

    # 提取途經穿透元件 (如共模扼流圈 CMC / AC 耦合電容)
    pass_comps = [c.ref_des for ep in p_endpoints for c in ep.get("pass_through_components", [])]
    pass_comps_unique = list(dict.fromkeys(pass_comps))
    pass_desc = f"（途經 {', '.join(pass_comps_unique)} 穿透元件）" if pass_comps_unique else ""

    if symmetry_result:
        p_caps = [c.ref_des for c in symmetry_result.get("p_series_capacitors", [])]
        n_caps = [c.ref_des for c in symmetry_result.get("n_series_capacitors", [])]
        p_segs = symmetry_result.get("p_path_segments", [])
        n_segs = symmetry_result.get("n_path_segments", [])
        is_sym = bool(symmetry_result.get("is_symmetric", False))
    else:
        p_caps = []
        n_caps = []
        p_segs = [seg for ep in p_endpoints for seg in ep.get("path_segments", [])]
        n_segs = []
        is_sym = False

    topology = _build_channel_universal_topology(
        channel_title=channel_title,
        p_net_name=p_net_name,
        n_net_name=n_net_name,
        p_endpoints=p_ep_audit,
        n_endpoints=n_ep_audit,
        p_segs=p_segs,
        n_segs=n_segs,
        symmetry_result=symmetry_result
    )

    channel_evidence: Dict[str, Any] = {
        # --- Tier 2: 跨網段通道去重契約 (Level3Engine 自動讀取去重) ---
        "covered_nets": covered_nets,
        # --- Tier 3: 前端 UniversalCircuitTopologySvg.vue 視覺化擴充契約 ---
        "channel_title": channel_title,
        "pair_type": "USB Differential Channel",
        "p_net": p_net_name,
        "n_net": n_net_name,
        "path_segments": p_segs,
        "n_path_segments": n_segs,
        "topology": topology,
        "p_endpoints": p_ep_audit,
        "n_endpoints": n_ep_audit,
        "pass_through_components": pass_comps_unique,
        "series_capacitors": {
            "p_caps": p_caps,
            "n_caps": n_caps,
            "symmetric": (p_caps == n_caps or len(p_caps) == len(n_caps))
        },
        "symmetry_check": {
            "is_symmetric": is_sym,
            "endpoints_count_match": (len(p_endpoints) == len(n_endpoints))
        }
    }

    return channel_evidence, channel_title, pass_desc, pass_comps_unique


def _package_rule_result(
    violations: List[RuleViolation],
    channel_evidence: Dict[str, Any],
    channel_title: str,
    head_tail_str: str,
    pass_desc: str,
    all_channel_components: List[str],
    covered_nets: List[str]
) -> Union[List[RuleViolation], RulePass]:
    """
    [Stage 5 核心函式] 統一封裝最終回傳結果 (RuleViolation 清單或 RulePass)

    消除中途提前 return 造成的欄位缺漏問題：
    - 若有任何違規：將 `channel_evidence` (含 `covered_nets` 與拓撲流向) 補齊至每筆 `RuleViolation.evidence`。
    - 若全數合格：補上 Tier 1 `checked_target` 與 Tier 3 `audit_summary`，回傳 `RulePass`。

    @param {List[RuleViolation]} violations - Stage 3 收集到的所有違規清單
    @param {Dict[str, Any]} channel_evidence - Stage 4 建構的基礎通道佐證字典
    @param {str} channel_title - 端到端通道識別標題
    @param {str} head_tail_str - 頭尾端點元件連接字串
    @param {str} pass_desc - 途經穿透元件描述字串
    @param {List[str]} all_channel_components - 通道涉及的所有元件 RefDes 清單
    @param {List[str]} covered_nets - 通道涵蓋的所有網段清單
    @returns {Union[List[RuleViolation], RulePass]} 最終標準化 DRC 執行結果
    """
    if violations:
        for v in violations:
            if isinstance(v.evidence, dict):
                for k, val in channel_evidence.items():
                    if k not in v.evidence:
                        v.evidence[k] = val
        return violations

    audit_summary = (
        f"USB 差分通道 [{channel_title}] 通過雙端審計：端到端連接至 {head_tail_str}{pass_desc}，"
        f"各網段正負極性吻合且 P/N 拓撲完全對稱。"
    )

    pass_evidence = dict(channel_evidence)
    # Tier 1: 引擎必填受測標的識別
    pass_evidence["checked_target"] = channel_title
    # Tier 3: 前端綠色審計結論卡片
    pass_evidence["audit_summary"] = audit_summary

    return RulePass(
        evidence=pass_evidence,
        target_nodes={
            "components": all_channel_components,
            "nets": covered_nets
        },
    )


# ==============================================================================
# SECTION 4: Level 3 伴生腳本標準入口函式 (Standard Entry Point)
# ==============================================================================

def execute(
    context: RuleContext,
    graph_api: GraphAPI,
    part_db: PartDB,
    params: Dict[str, Any] = None
) -> Union[List[RuleViolation], RulePass, RuleResult]:
    """
    執行 USB 高速差分對極性反接與拓撲不對稱雙端合一檢查 (Level 3 標準入口函式)

    本函式遵循「五階段標準流水線 (5-Stage Pipeline)」架構：
      - Stage 1: 目標解析與夥伴配對 (Target Extraction & Partner Resolution)
      - Stage 2: 拓撲展開與通道收集 (Topology Tracing & Channel Discovery)
      - Stage 3: 核心領域規則檢驗 (Core Domain Rule Auditing)
      - Stage 4: 三層佐證資料建構 (3-Tier Evidence Trail Construction)
      - Stage 5: 統一結果封裝與回傳 (Unified Result Packaging)

    @param {RuleContext} context - 執行期上下文 (`context.target` 為觸發之正極網路節點)
    @param {GraphAPI} graph_api - SDK 電路拓撲查詢介面
    @param {PartDB} part_db - SDK 零件規格庫查詢介面
    @param {Dict[str, Any]} params - 由規則 YAML 傳入的外部參數字典
    @returns {Union[List[RuleViolation], RulePass, RuleResult]} 違規報告清單或結構化合格證明物件
    """
    # --------------------------------------------------------------------------
    # [Stage 1]: 目標解析與夥伴配對 (Target Extraction & Partner Resolution)
    # --------------------------------------------------------------------------
    target_net = context.target
    if not target_net:
        return RuleResult.SKIPPED

    p_net_name = str(target_net.get("net_name") or target_net.get("name") or "")
    if not p_net_name:
        return RuleResult.SKIPPED

    expected_n_name, partner_node = _resolve_negative_partner_node(graph_api, target_net, p_net_name)
    n_net_name = str(partner_node.get("net_name") or expected_n_name) if partner_node else ""

    # --------------------------------------------------------------------------
    # [Stage 2]: 拓撲展開與通道收集 (Topology Tracing & Channel Discovery)
    # --------------------------------------------------------------------------
    # 2.0 端點起點正規化 (Canonical Channel Root Net Selection)
    # 檢查當前 target_net 是否為中繼網段（如 _C, _R 等被動元件間連線，本身無實體 IC/Connector 端點設備）。
    # 僅當當前網段自身無端點設備，且追蹤端點中發現 Connector（板級入口元件）或實體設備時：
    # 將起點重導向至 Connector/主端點網段，確保差分拓撲流向永遠由入口 (Connector) 單向流向晶片，
    # 杜絕中間中繼網段導致的虛擬 Endpoint 與拓撲折返錯位現象。
    initial_p_endpoints = graph_api.trace_differential_end_to_end(target_net)
    target_net_has_device = any(
        ep.get("terminal_net") and ep["terminal_net"].net_name == p_net_name
        for ep in initial_p_endpoints
    )

    canonical_target_net = target_net
    canonical_p_name = p_net_name
    orig_p_net_name = p_net_name

    if not target_net_has_device and len(initial_p_endpoints) > 0:
        # 優先尋找 Connector 端點
        connector_ep = None
        for ep in initial_p_endpoints:
            c = ep.get("component")
            if not c:
                continue
            cat = str(c.get("category") or c.get("sub_category") or "").lower()
            ref = str(c.ref_des or "").upper()
            if "connector" in cat or ref.startswith("TJ") or (ref.startswith("J") and not ref.startswith("JP")):
                connector_ep = ep
                break

        if connector_ep and connector_ep.get("terminal_net"):
            conn_net_name = connector_ep["terminal_net"].net_name
            if conn_net_name != p_net_name:
                conn_net_id = graph_api._resolve_node_id(conn_net_name, "net:")
                if conn_net_id and graph_api._G.has_node(conn_net_id):
                    canonical_target_net = graph_api._G.nodes[conn_net_id]
                    canonical_p_name = conn_net_name
        else:
            first_ep = initial_p_endpoints[0]
            if first_ep.get("terminal_net"):
                first_net_name = first_ep["terminal_net"].net_name
                first_net_id = graph_api._resolve_node_id(first_net_name, "net:")
                if first_net_id and graph_api._G.has_node(first_net_id):
                    canonical_target_net = graph_api._G.nodes[first_net_id]
                    canonical_p_name = first_net_name

    # 若發生起點正規化，重新解析夥伴節點與正負極網段名稱
    if canonical_p_name != p_net_name:
        p_net_name = canonical_p_name
        target_net = canonical_target_net
        expected_n_name, partner_node = _resolve_negative_partner_node(graph_api, target_net, p_net_name)
        n_net_name = str(partner_node.get("net_name") or expected_n_name) if partner_node else ""

    involved_components: set = set()

    # 2.1 展開正極 (P) 端到端鏈路（自動穿透串聯電容、匹配電阻與 4-pin CMC）
    p_endpoints = graph_api.trace_differential_end_to_end(target_net)
    for ep in p_endpoints:
        involved_components.add(ep["component"].ref_des)
        for pc in ep.get("passed_components", []):
            involved_components.add(pc.ref_des)

    # 2.2 若存在負極夥伴節點，展開負極 (N) 端到端鏈路並執行雙端對稱性分析
    n_endpoints: List[Dict[str, Any]] = []
    symmetry_result: Optional[Dict[str, Any]] = None
    if partner_node is not None:
        n_endpoints = graph_api.trace_differential_end_to_end(partner_node)
        for ep in n_endpoints:
            involved_components.add(ep["component"].ref_des)
            for pc in ep.get("passed_components", []):
                involved_components.add(pc.ref_des)
        symmetry_result = graph_api.check_differential_pair_symmetry(target_net, n_net_name)

    # 2.3 收集本物理通道跨越的所有子網段 (Tier 2: covered_nets 去重契約)
    all_covered: List[str] = [p_net_name, orig_p_net_name]
    if partner_node is not None and n_net_name:
        all_covered.append(n_net_name)
    for ep in p_endpoints + n_endpoints:
        all_covered.extend(ep.get("covered_nets", []))
    if symmetry_result and "covered_nets" in symmetry_result:
        all_covered.extend(symmetry_result.get("covered_nets", []))
    covered_nets = list(dict.fromkeys(all_covered))

    # --------------------------------------------------------------------------
    # [Stage 3]: 核心領域規則檢驗 (Core Domain Rule Auditing)
    # --------------------------------------------------------------------------
    violations: List[RuleViolation] = []

    # 3.1 審計正極 (P) 端點懸空與引腳極性反接 (Scenario A - P Side)
    p_ep_audit, p_violations = _audit_single_polarity_endpoints(
        endpoints=p_endpoints,
        net_name=p_net_name,
        expected_polarity="P",
        p_net_name=p_net_name,
        n_net_name=n_net_name or None,
        part_db=part_db
    )
    violations.extend(p_violations)

    # 3.2 審計負極 (N) 夥伴存在性、端點懸空與引腳極性反接 (Scenario A - N Side)
    n_ep_audit: List[Dict[str, Any]] = []
    if partner_node is None:
        # 若 P 端未發生極性反接但找不到負極夥伴，回報缺少負極夥伴網路
        if not violations:
            violations.append(RuleViolation(
                error_message=f"USB 差分對缺少負極 (N/DM) 夥伴網路：正極網路 ({p_net_name}) 孤立存在，未配對到對應之負極走線。",
                recommendation="請檢查線路圖是否漏繪負極差分線或 Net Label 拼寫有誤，確保 USB 差分對成對繪製。",
                severity="ERROR",
                evidence={
                    "p_net": p_net_name,
                    "expected_partner": expected_n_name,
                    "partner_found": False
                },
                target_nodes={"nets": [p_net_name]}
            ))
    else:
        n_ep_audit, n_violations = _audit_single_polarity_endpoints(
            endpoints=n_endpoints,
            net_name=n_net_name,
            expected_polarity="N",
            p_net_name=p_net_name,
            n_net_name=n_net_name,
            part_db=part_db
        )
        violations.extend(n_violations)

    # 3.3 審計 P/N 雙端拓撲對稱性 (Scenario B - Differential Asymmetry)
    if symmetry_result is not None and not symmetry_result["is_symmetric"]:
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
    # [Stage 4]: 三層佐證資料建構 (3-Tier Evidence Trail Construction)
    # --------------------------------------------------------------------------
    channel_evidence, channel_title, pass_desc, pass_comps_unique = _build_channel_evidence(
        p_net_name=p_net_name,
        n_net_name=n_net_name,
        covered_nets=covered_nets,
        p_endpoints=p_endpoints,
        n_endpoints=n_endpoints,
        p_ep_audit=p_ep_audit,
        n_ep_audit=n_ep_audit,
        symmetry_result=symmetry_result
    )
    _, head_tail_str = _format_channel_title(p_net_name, p_endpoints)
    all_channel_components = sorted(list(involved_components.union(set(pass_comps_unique))))

    # --------------------------------------------------------------------------
    # [Stage 5]: 統一結果封裝與回傳 (Unified Result Packaging)
    # --------------------------------------------------------------------------
    return _package_rule_result(
        violations=violations,
        channel_evidence=channel_evidence,
        channel_title=channel_title,
        head_tail_str=head_tail_str,
        pass_desc=pass_desc,
        all_channel_components=all_channel_components,
        covered_nets=covered_nets
    )
