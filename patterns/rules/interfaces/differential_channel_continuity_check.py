"""
================================================================================
差分通道導通與串聯元件完整性檢查腳本 (Differential Channel Continuity & Integrity Check)
DesignShield Level 3 DRC 伴生腳本 (基於 SDK 通道高階抽象重構)
================================================================================

【業務邏輯 (Domain Logic)】
1. 檢驗標的：高速差分信號通道 (USB, PCIe, SATA, Ethernet, DDR 等)。
2. 判定邏輯 (網路圖、支援並聯穿透元件)：
   - 運用 SDK DifferentialChannel 將通道建模為「網路為節點、穿透元件為邊」的網路圖，
     並以源端 (Host，如 U4) 為基準逐極性 (P/N)、逐「已上件目標端點」判定導通性。
   - 同一躍點 (hop) 的並聯元件 (如 0Ω 跳線 ∥ 共模扼流圈 CMC) 只要任一顆已上件即視為導通；
     僅當某躍點「所有並聯候選皆未上件」時才發出 ERROR，指出該躍點斷路。
   - 源端未上件或所有目標端點皆未上件，視為該配置下未啟用的通道，安全合格 (略過)。
3. PartDB 缺失處理 (嚴禁猜測引腳配對)：
   - 若通道上「已上件」的 4-pin 穿透元件查無 PartDB 規格，導通性未知，回傳 SKIPPED，
     並附上缺失清單 (missing_partdb) 供使用者手動補齊 PartDB。
   - 「未上件」元件不可能導通，直接忽略其穿透配對，僅於拓撲以虛線方塊標示。
================================================================================
"""

from typing import Dict, List, Any, Union
from designshield.sdk import (
    RuleResult,
    RulePass,
    RuleSkipped,
    RuleViolation,
    RuleContext,
    GraphAPI,
    PartDB,
    DifferentialChannel,
)


def _display_ref(comp: Any, ref_des: str) -> str:
    """取得元件顯示名稱 (未上件加註 [X] / [P] / [M] 標記)"""
    if hasattr(comp, "display_ref_des"):
        return comp.display_ref_des
    bom = getattr(comp, "bom", None) or (comp.get("bom") if isinstance(comp, dict) else None)
    tag = bom if bom in {"P", "M"} else "X"
    return f"{ref_des} [{tag}]"


def execute(
    context: RuleContext,
    graph_api: GraphAPI,
    part_db: PartDB,
    params: Dict[str, Any] = None
) -> Union[RulePass, RuleSkipped, RuleViolation, List[RuleViolation], RuleResult]:
    """
    差分通道導通與串聯元件完整性檢查核心入口

    運用 SDK 高階 DifferentialChannel 模型，自動追蹤正負極通道、並聯穿透元件與端點裝配狀態。
    """
    channel: DifferentialChannel = graph_api.get_differential_channel(context.target)
    if not channel:
        return RuleResult.SKIPPED

    channel_title = channel.title
    topo_dict = channel.to_topology()
    covered_nets = channel.covered_nets
    missing_partdb = [
        {
            "ref_des": m["ref_des"],
            "mfg": m.get("mfg", ""),
            "pn": m.get("pn", ""),
            "is_mounted": m.get("is_mounted", True),
        }
        for m in channel.partdb_missing
    ]
    base_evidence: Dict[str, Any] = {
        "channel_title": channel_title,
        "checked_target": channel_title,
        "covered_nets": covered_nets,
        "topology": topo_dict,
        "missing_partdb": missing_partdb,
    }

    # 1. 已上件之 4-pin 穿透元件查無 PartDB：導通性未知，SKIPPED (請使用者手動補齊 PartDB)
    mounted_missing = channel.partdb_missing_mounted
    if mounted_missing:
        refs = [m["ref_des"] for m in mounted_missing]
        parts = ", ".join(f"{m.get('mfg') or '?'}_{m.get('pn') or '?'}" for m in mounted_missing)
        return RuleSkipped(
            reason=(
                f"通道穿透元件 {', '.join(refs)} 已上件，但 PartDB 查無料號 ({parts}) 之穿透引腳規格，"
                "無法判定導通性。請至 PartDB 補齊該料號後重新檢測。"
            ),
            evidence=base_evidence,
            target_nodes={"components": refs + channel.endpoint_refs, "nets": covered_nets},
        )

    # 2. 端點數量不足 (例如單端懸空)，由極性/走線規則處理，此處安全略過並產出拓撲
    if len(channel.p_endpoints) < 2:
        return RulePass(
            evidence={
                **base_evidence,
                "audit_summary": f"差分網路 {channel.p_net_name} 連接之端點少於 2 個，不構成完整端到端通道。"
            },
            target_nodes={"nets": [channel.p_net_name]}
        )

    # 3. 導通性分析 (網路圖；並聯任一上件即導通)
    analysis = channel.analyze_continuity()

    def _endpoint_names(refs: List[str]) -> List[str]:
        names = []
        for ep in channel.endpoints:
            comp = ep.get("component")
            ref = getattr(comp, "ref_des", None) or ep.get("ref_des")
            if ref in refs:
                names.append(getattr(comp, "display_ref_des", None) or ref)
        return list(dict.fromkeys(names))

    if not analysis["root_mounted"] or not analysis["active_targets"]:
        inactive_refs = ([analysis["root_ref"]] if not analysis["root_mounted"] else []) + analysis["inactive_targets"]
        names = _endpoint_names(inactive_refs)
        return RulePass(
            evidence={
                **base_evidence,
                "audit_summary": (
                    f"差分通道端點元件 ({', '.join(filter(None, names))}) 於當前 Config 下標註為未上件，"
                    "該通道未處於啟用工作狀態，安全略過導通性檢查。"
                )
            },
            target_nodes={"components": channel.endpoint_refs, "nets": covered_nets}
        )

    # 4. 已上件目標端點存在斷路：依「全部並聯候選皆未上件」之躍點產生違規 (相同候選組合只報一次)
    comp_by_ref = {
        (getattr(c, "ref_des", None) or c.get("ref_des")): c for c in channel.pass_components
    }
    violations: List[RuleViolation] = []
    reported = set()
    for failure in analysis["failures"]:
        key = frozenset(failure["candidates"])
        if key in reported:
            continue
        reported.add(key)

        cands = failure["candidates"]
        comps = [comp_by_ref.get(r, {"ref_des": r}) for r in cands]
        displays = [_display_ref(c, r) for c, r in zip(comps, cands)]
        first = comps[0]
        first_ref = cands[0]
        cat = getattr(first, "category", None) or (first.get("category") if isinstance(first, dict) else None) or "Passive"
        pn = (
            getattr(first, "pn", None) or (first.get("pn") if isinstance(first, dict) else None)
            or (first.get("part_number") if isinstance(first, dict) else None) or cat
        )
        bom = getattr(first, "bom", None) or (first.get("bom") if isinstance(first, dict) else None)

        parallel_note = "，且無任何已上件之並聯導通元件" if len(cands) > 1 else ""
        err_msg = (
            f"差分通道 ({channel.p_net_name} / {channel.n_net_name or ''}) 兩端端點 ({channel_title}) 皆已上件，"
            f"但 {failure['from_net']} → {failure['to_net']} 之串聯元件 {', '.join(displays)} ({pn}) 標註為未上件"
            f"{parallel_note}，導致高速訊號傳輸路徑電氣開路中斷！"
        )
        rec_msg = (
            f"請將 {' 或 '.join(cands)} 其中之一標註為上件 (I 或當前階段有效代碼)，以確保通道電氣導通。"
            if len(cands) > 1 else
            f"請將串聯元件 {first_ref} 標註為上件 (I 或當前階段有效代碼)，以確保通道電氣導通。"
        )
        violations.append(RuleViolation(
            error_message=err_msg,
            recommendation=rec_msg,
            severity="ERROR",
            evidence={
                **base_evidence,
                "faulty_component": first_ref,
                "faulty_components": cands,
                "component_type": cat,
                "part_value": pn,
                "is_mounted": False,
                "bom": bom,
                "broken_hop": {"rail_id": failure["rail_id"], "from_net": failure["from_net"], "to_net": failure["to_net"]},
                "unreachable_target": failure["target_ref"],
            },
            target_nodes={
                "components": cands + channel.endpoint_refs,
                "nets": [channel.p_net_name] + ([channel.n_net_name] if channel.n_net_name else [])
            }
        ))

    if violations:
        return violations

    # 5. 所有已上件目標端點皆有已上件元件構成之連通路徑，判定 PASS
    pass_comps_desc = (
        f"（途中穿透元件: {', '.join(channel.pass_component_refs)}；並聯元件任一上件即導通）"
        if channel.pass_component_refs else "（直連差分通道）"
    )
    inactive_note = ""
    if analysis["inactive_targets"]:
        inactive_note = f" 未上件目標端點 ({', '.join(_endpoint_names(analysis['inactive_targets']))}) 已略過。"
    return RulePass(
        evidence={
            **base_evidence,
            "audit_summary": f"差分通道兩端端點皆已上件，{pass_comps_desc}，電氣訊號完整導通。{inactive_note}",
            "pass_through_components": channel.pass_component_refs,
        },
        target_nodes={
            "components": channel.all_component_refs,
            "nets": covered_nets
        },
        message="差分通道兩端皆已上件，串聯元件全數導通。"
    )
