"""
================================================================================
差分通道導通與串聯元件完整性檢查腳本 (Differential Channel Continuity & Integrity Check)
DesignShield Level 3 DRC 伴生腳本 (基於 SDK 通道高階抽象重構)
================================================================================

【業務邏輯 (Domain Logic)】
1. 檢驗標的：高速差分信號通道 (USB, PCIe, SATA, Ethernet, DDR 等)。
2. 判定邏輯：
   - 運用 SDK DifferentialChannel 追蹤正負極通道到達的所有端點元件與串聯穿透元件。
   - 當兩端端點皆同時上件 (Both endpoints are mounted) 時，檢查中間所有串聯元件
     (包含但不限於 AC 耦合電容、串聯電阻、共模扼流圈 CMC 等)。
   - 確保中間所有串聯零件皆確實上件 (is_mounted == True)；若有任何串聯元件未上件，
     發出 ERROR 告警，指出該元件未上件導致通道電氣開路。
   - 若兩端端點有任一端未上件，則視為該配置下未啟用的通道，安全合格或略過。
================================================================================
"""

from typing import Dict, List, Any, Union
from designshield.sdk import (
    RuleResult,
    RulePass,
    RuleViolation,
    RuleContext,
    GraphAPI,
    PartDB,
    DifferentialChannel,
)


def execute(
    context: RuleContext,
    graph_api: GraphAPI,
    part_db: PartDB,
    params: Dict[str, Any] = None
) -> Union[RulePass, RuleViolation, List[RuleViolation], RuleResult]:
    """
    差分通道導通與串聯元件完整性檢查核心入口

    運用 SDK 高階 DifferentialChannel 模型，自動追蹤正負極通道、串聯穿透元件與端點裝配狀態。
    """
    channel: DifferentialChannel = graph_api.get_differential_channel(context.target)
    if not channel:
        return RuleResult.SKIPPED

    channel_title = channel.title
    topo_dict = channel.to_topology()
    covered_nets = channel.covered_nets

    # 1. 端點數量不足 (例如單端懸空)，由極性/走線規則處理，此處安全略過並產出拓撲
    if len(channel.p_endpoints) < 2:
        return RulePass(
            evidence={
                "channel_title": channel_title,
                "checked_target": channel_title,
                "covered_nets": covered_nets,
                "topology": topo_dict,
                "audit_summary": f"差分網路 {channel.p_net_name} 連接之端點少於 2 個，不構成完整端到端通道。"
            },
            target_nodes={"nets": [channel.p_net_name]}
        )

    # 2. 判斷兩端端點是否皆同時上件
    if not channel.endpoints_mounted:
        unmounted_ep_names = [
            getattr(ep.get("component"), "display_ref_des", None) or
            getattr(ep.get("component"), "ref_des", None) or
            ep.get("ref_des")
            for ep in channel.unmounted_endpoints
        ]
        return RulePass(
            evidence={
                "channel_title": channel_title,
                "checked_target": channel_title,
                "covered_nets": covered_nets,
                "topology": topo_dict,
                "audit_summary": (
                    f"差分通道端點元件 ({', '.join(filter(None, unmounted_ep_names))}) 於當前 Config 下標註為未上件，"
                    "該通道未處於啟用工作狀態，安全略過導通性檢查。"
                )
            },
            target_nodes={"components": channel.endpoint_refs, "nets": covered_nets}
        )

    # 3. 兩端端點皆已上件：檢查中間所有途經串聯元件是否全部確實上件
    violations: List[RuleViolation] = []
    for comp in channel.unmounted_pass_components:
        ref_des = getattr(comp, "ref_des", None) or comp.get("ref_des")
        cat = getattr(comp, "category", None) or comp.get("category", "Passive")
        pn = getattr(comp, "pn", None) or comp.get("pn") or comp.get("part_number") or cat
        bom = getattr(comp, "bom", None) or comp.get("bom")
        if hasattr(comp, "display_ref_des"):
            display_ref = comp.display_ref_des
        else:
            tag = bom if bom in {"P", "M"} else "X"
            display_ref = f"{ref_des} [{tag}]"

        err_msg = (
            f"差分通道 ({channel.p_net_name} / {channel.n_net_name or ''}) 兩端端點 ({channel_title}) 皆已上件，"
            f"但中間串聯元件 {display_ref} ({pn}) 標註為未上件，"
            "導致高速訊號傳輸路徑電氣開路中斷！"
        )
        rec_msg = f"請將串聯元件 {ref_des} 標註為上件 (I 或當前階段有效代碼)，以確保通道電氣導通。"
        violations.append(RuleViolation(
            error_message=err_msg,
            recommendation=rec_msg,
            severity="ERROR",
            evidence={
                "channel_title": channel_title,
                "faulty_component": ref_des,
                "component_type": cat,
                "part_value": pn,
                "is_mounted": False,
                "bom": bom,
                "covered_nets": covered_nets,
                "topology": topo_dict,
            },
            target_nodes={
                "components": [ref_des] + channel.endpoint_refs,
                "nets": [channel.p_net_name] + ([channel.n_net_name] if channel.n_net_name else [])
            }
        ))

    if violations:
        return violations

    # 4. 若所有串聯元件皆確實上件，且兩端端點上件，判定 PASS
    pass_comps_desc = f"（途中串聯元件: {', '.join(channel.pass_component_refs)} 皆正常上件）" if channel.pass_component_refs else "（直連差分通道）"
    return RulePass(
        evidence={
            "channel_title": channel_title,
            "checked_target": channel_title,
            "covered_nets": covered_nets,
            "audit_summary": f"差分通道兩端端點皆已上件，{pass_comps_desc}，電氣訊號完整導通。",
            "topology": topo_dict,
            "pass_through_components": channel.pass_component_refs,
        },
        target_nodes={
            "components": channel.all_component_refs,
            "nets": covered_nets
        },
        message="差分通道兩端皆已上件，串聯元件全數導通。"
    )
