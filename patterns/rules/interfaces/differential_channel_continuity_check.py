"""
================================================================================
差分通道導通與串聯元件完整性檢查腳本 (Differential Channel Continuity & Integrity Check)
DesignShield Level 3 DRC 伴生腳本
================================================================================

【業務邏輯 (Domain Logic)】
1. 檢驗標的：高速差分信號通道 (USB, PCIe, SATA, Ethernet 等)。
2. 判定邏輯：
   - 追蹤正負極差分網路到達的所有端點元件 (Endpoint IC / Connector) 與中間所有串聯元件 (pass-through components)。
   - 當兩端端點皆同時上件 (Both endpoints are mounted) 時，檢查中間所有串聯元件
     (包含但不限於 AC 耦合電容 AC caps、串聯電阻 series resistors、共模扼流圈 CMC 等)。
   - 確保中間所有串聯零件皆確實上件 (is_mounted == True)；若有任何串聯元件未上件，
     發出 CRITICAL / ERROR 告警，指出該元件未上件導致通道電氣開路。
   - 若兩端端點有任一端未上件，則視為該配置下未啟用的通道，安全合格或略過。
================================================================================
"""

import re
from typing import Dict, List, Any, Optional, Tuple, Union
from designshield.sdk import (
    RuleResult,
    RulePass,
    RuleViolation,
    RuleContext,
    GraphAPI,
    PartDB,
    TopologyGraphBuilder,
)


def _resolve_n_net_name(p_net_name: str, p_node: Any, graph_api: GraphAPI) -> Optional[str]:
    """解析正極網路對應之負極夥伴網路名稱"""
    partner_id = getattr(p_node, "diff_pair_partner", None) or (p_node.get("diff_pair_partner") if isinstance(p_node, dict) else None)
    if partner_id:
        return partner_id.replace("net:", "")

    # 若傳入之節點物件未帶 partner，嘗試自圖譜中直接獲取 net 節點屬性
    if graph_api._G.has_node(f"net:{p_net_name}"):
        g_node = graph_api._G.nodes[f"net:{p_net_name}"]
        partner_id = g_node.get("diff_pair_partner")
        if partner_id:
            return partner_id.replace("net:", "")

    # 正規表示式推導候選清單 (支援 USB 之 DP/DM、DDR/PCIe 之 DP/DN 等)
    candidates = []
    if re.search(r"(?i)_DP$", p_net_name):
        candidates.extend([re.sub(r"(?i)_DP$", "_DN", p_net_name), re.sub(r"(?i)_DP$", "_DM", p_net_name)])
    elif re.search(r"(?i)DP$", p_net_name):
        candidates.extend([re.sub(r"(?i)DP$", "DN", p_net_name), re.sub(r"(?i)DP$", "DM", p_net_name)])
    elif re.search(r"D\+$", p_net_name):
        candidates.append(re.sub(r"D\+$", "D-", p_net_name))
    elif re.search(r"_P$", p_net_name):
        candidates.append(re.sub(r"_P$", "_N", p_net_name))
    elif "_P_" in p_net_name:
        candidates.append(p_net_name.replace("_P_", "_N_"))
    elif "_DP_" in p_net_name:
        candidates.extend([p_net_name.replace("_DP_", "_DN_"), p_net_name.replace("_DP_", "_DM_")])

    for cand in candidates:
        if cand and (graph_api._G.has_node(cand) or graph_api._G.has_node(f"net:{cand}")):
            return cand
    return None


def _score_root_component(ep: Dict[str, Any]) -> int:
    """
    評估端點作為差分通道發散源端 (Root / Host / Master) 之權重分數
    分數愈高代表愈適合作為發散源端 (start_ref)：
      3: 主控晶片 / CPU 插座 / SoC (RefDes 為 U*, XU*, CPU*, SOC* 或類別為 IC / Processor / BGA / Socket)
      2: 板級外部入口連接器 (RefDes 為 TJ*, J* 或含有 Type-C / USB / Receptacle)
      1: 一般元件
      0: 記憶體插槽 / 子插槽 / 終端負載 (如 XMM*, DIMM*, SLOT*)
    """
    c = ep.get("component") if isinstance(ep, dict) else ep
    ref = str(getattr(c, "ref_des", None) or (c.get("ref_des") if isinstance(c, dict) else "") or ep.get("ref_des") or "").upper()
    cat = str(getattr(c, "category", None) or (c.get("category") if isinstance(c, dict) else "") or "").lower()
    pn = str(getattr(c, "pn", None) or getattr(c, "part_number", None) or (c.get("part_number") if isinstance(c, dict) else "") or (c.get("pn") if isinstance(c, dict) else "") or ep.get("part_number") or "").lower()

    # 記憶體插槽 (DIMM / Memory Slot) 通常為接收端負載，權重最低
    if ref.startswith("XMM") or "dimm" in pn or "udimm" in pn or "rdimm" in pn or "sodimm" in pn:
        return 0

    # 主控晶片 / CPU 插座 / Socket / IC
    if (
        ref.startswith("CPU") or ref.startswith("SOC") or
        ref.startswith("XU") or (ref.startswith("U") and not ref.startswith("USB")) or
        "socket" in pn or "lga" in pn or "bga" in pn or
        "processor" in cat or cat == "ic"
    ):
        return 3

    # 板端外接入口連接器 (如 TJ, J, Type-C)
    if ref.startswith("TJ") or (ref.startswith("J") and not ref.startswith("JP")) or "type-c" in pn or "typec" in pn or "receptacle" in pn:
        return 2

    return 1


def _format_channel_path_title(
    p_net_name: str,
    p_endpoints: List[Dict[str, Any]],
    n_endpoints: List[Dict[str, Any]],
    start_ref: Optional[str] = None,
    target_refs: Optional[List[str]] = None,
    end_ref: Optional[str] = None,
) -> str:
    """
    產生包含元件鏈路箭頭 (例如 TU1->R10->TJ1 或 XU1 -> XMM1, XMM2) 與差分通道名稱之完整標題。
    """
    # 提取途經穿透串聯元件序列 (按階層順序)
    pass_comps = []
    for ep in p_endpoints:
        for seg in ep.get("path_segments", []):
            pc = seg.get("pass_component")
            if pc and pc not in pass_comps:
                pass_comps.append(pc)

    if not pass_comps and n_endpoints:
        for ep in n_endpoints:
            for seg in ep.get("path_segments", []):
                pc = seg.get("pass_component")
                if pc and pc not in pass_comps:
                    pass_comps.append(pc)

    # 組合目標端點字串 (支援多目標逗號分隔)
    if target_refs:
        dst_str = ", ".join(target_refs)
    elif end_ref:
        dst_str = end_ref
    else:
        dst_str = ""

    # 組合路徑節點清單
    if start_ref and dst_str:
        if pass_comps:
            path_chain = f"{start_ref} -> {' -> '.join(pass_comps)} -> {dst_str}"
        else:
            path_chain = f"{start_ref} -> {dst_str}"
    elif start_ref:
        path_chain = f"{start_ref} -> {' -> '.join(pass_comps)}" if pass_comps else f"{start_ref} -> (懸空)"
    else:
        path_chain = p_net_name

    base_channel = re.sub(r"(?i)(?:_P|_DP|DP|D\+)$", "", p_net_name)
    clean_channel = re.sub(r"(?i)(?:_CMC|_C)$", "", base_channel)
    return f"{path_chain} ({clean_channel} 差分通道)"


def _build_differential_topology(
    channel_title: str,
    p_net_name: str,
    n_net_name: Optional[str],
    p_endpoints: List[Dict[str, Any]],
    n_endpoints: List[Dict[str, Any]],
    start_ref: Optional[str] = None,
    target_refs: Optional[List[str]] = None,
    end_ref: Optional[str] = None,
) -> Dict[str, Any]:
    """
    建構符合 UniversalTopologyData 契約之標準完整差分拓撲字典
    包含正負軌道、端點元件、途中所有穿透元件與完整的實體曼哈頓導線 connections
    支援直連 1 對多 (Multi-drop) 發散扇出連線
    """
    builder = TopologyGraphBuilder(title=channel_title, channel_type="differential")
    builder.add_rail("p_rail", f"正極軌道 ({p_net_name})", polarity="P")
    if n_net_name:
        builder.add_rail("n_rail", f"負極軌道 ({n_net_name})", polarity="N")

    def _populate_rail(
        rail_id: str,
        start_net: str,
        endpoints: List[Dict[str, Any]],
    ):
        if not start_net and not endpoints:
            return

        # 1. 收集該軌道的所有穿透元件段落 segments
        segments = []
        for ep in endpoints:
            segs = ep.get("path_segments", [])
            if segs and len(segs) > len(segments):
                segments = segs

        endpoints_by_net: Dict[str, List[Dict[str, Any]]] = {}
        for ep in endpoints:
            c = ep["component"] if "component" in ep else ep
            net = ep.get("connected_net") or (ep.get("terminal_net").net_name if ep.get("terminal_net") else start_net)
            endpoints_by_net.setdefault(net, []).append(ep)

            ref_des = getattr(c, "ref_des", None) or c.get("ref_des") or ep.get("ref_des")
            cat = getattr(c, "category", None) or c.get("category") or "IC"
            pn = getattr(c, "pn", None) or c.get("part_value") or c.get("part_number") or ""
            is_mounted = getattr(c, "is_mounted", True)
            bom = getattr(c, "bom", None) or c.get("bom")
            pin_num = ep.get("pin_number") or ep.get("pin") or "1"
            pin_name = ep.get("pin_name") or ep.get("pin") or pin_num

            builder.add_terminal(
                id=ref_des,
                ref_des=ref_des,
                category=cat,
                part_number=pn,
                is_mounted=bool(is_mounted),
                bom=bom,
                pins=[{"pin_number": pin_num, "pin_name": pin_name}]
            )

        # 2. 若無途中穿透元件 (直連差分通道)
        if not segments:
            if len(endpoints) >= 2:
                ep_map = {}
                for ep in endpoints:
                    c = ep["component"] if "component" in ep else ep
                    ref = getattr(c, "ref_des", None) or c.get("ref_des") or ep.get("ref_des")
                    if ref:
                        ep_map[ref] = ep

                # 確定源端 root_ref
                root_ref = start_ref if (start_ref and start_ref in ep_map) else None
                if not root_ref:
                    # 回退到 ep_map 第一個元件
                    root_ref = list(ep_map.keys())[0]

                ep_from = ep_map[root_ref]
                pin_from = ep_from.get("pin_number") or ep_from.get("pin") or "1"

                # 確定所有目標端點清單
                destination_refs = [r for r in (target_refs or list(ep_map.keys())) if r in ep_map and r != root_ref]
                if not destination_refs:
                    destination_refs = [r for r in ep_map.keys() if r != root_ref]

                # 向所有目標端點發散建立連線 (1 對多扇出)
                for dst_ref in destination_refs:
                    ep_to = ep_map[dst_ref]
                    pin_to = ep_to.get("pin_number") or ep_to.get("pin") or "1"
                    builder.add_connection(
                        net_name=start_net,
                        rail_id=rail_id,
                        from_node=root_ref,
                        from_pin=pin_from,
                        to_node=dst_ref,
                        to_pin=pin_to,
                        is_branch=False
                    )
            return

        # 3. 存在途中串聯穿透元件
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

        # 起始端點 -> 第一顆穿透元件連線
        first_seg = segments[0]
        start_eps = endpoints_by_net.get(first_seg["from_net"], [])
        if not start_eps and endpoints:
            start_eps = [endpoints[0]]
        for ep in start_eps:
            c = ep["component"] if "component" in ep else ep
            ref = getattr(c, "ref_des", None) or c.get("ref_des") or ep.get("ref_des")
            pin = ep.get("pin_number") or ep.get("pin") or "1"
            builder.add_connection(
                net_name=first_seg["from_net"],
                rail_id=rail_id,
                from_node=ref,
                from_pin=pin,
                to_node=first_seg["pass_component"],
                to_pin=first_seg.get("in_pin", "1")
            )

        # 串聯穿透元件之間連線
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

        # 最後一顆穿透元件 -> 終端端點連線
        last_seg = segments[-1]
        end_eps = endpoints_by_net.get(last_seg["to_net"], [])
        if not end_eps and len(endpoints) >= 2:
            end_eps = endpoints[1:]
        for ep in end_eps:
            c = ep["component"] if "component" in ep else ep
            ref = getattr(c, "ref_des", None) or c.get("ref_des") or ep.get("ref_des")
            pin = ep.get("pin_number") or ep.get("pin") or "1"
            builder.add_connection(
                net_name=last_seg["to_net"],
                rail_id=rail_id,
                from_node=last_seg["pass_component"],
                from_pin=last_seg.get("out_pin", "2"),
                to_node=ref,
                to_pin=pin
            )

    _populate_rail("p_rail", p_net_name, p_endpoints)
    if n_net_name:
        _populate_rail("n_rail", n_net_name, n_endpoints)

    return builder.to_dict()


def execute(
    context: RuleContext,
    graph_api: GraphAPI,
    part_db: PartDB,
    params: Dict[str, Any] = None
) -> Union[RulePass, RuleViolation, List[RuleViolation], RuleResult]:
    """
    差分通道導通與串聯元件完整性檢查核心入口
    """
    target = context.target
    p_net_name = str(target.get("net_name") or target.get("name") or target.get("_id", "").replace("net:", ""))
    n_net_name = _resolve_n_net_name(p_net_name, target, graph_api)

    # 1. 起點正規化 (Canonical Channel Root Net Selection)
    initial_p_endpoints = graph_api.trace_differential_end_to_end(f"net:{p_net_name}")
    target_net_has_device = any(
        ep.get("terminal_net") and ep["terminal_net"].net_name == p_net_name
        for ep in initial_p_endpoints
    )

    canonical_p_name = p_net_name
    if not target_net_has_device and len(initial_p_endpoints) > 0:
        # 優先尋找 Connector 端點 (板級入口) 作為標準起點
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
                canonical_p_name = conn_net_name
        elif initial_p_endpoints[0].get("terminal_net"):
            canonical_p_name = initial_p_endpoints[0]["terminal_net"].net_name

    if canonical_p_name != p_net_name:
        p_net_name = canonical_p_name
        p_node = graph_api._G.nodes[f"net:{p_net_name}"] if graph_api._G.has_node(f"net:{p_net_name}") else {"net_name": p_net_name}
        n_net_name = _resolve_n_net_name(p_net_name, p_node, graph_api)
        p_endpoints = graph_api.trace_differential_end_to_end(f"net:{p_net_name}")
        n_endpoints = graph_api.trace_differential_end_to_end(f"net:{n_net_name}") if n_net_name else []
    else:
        p_endpoints = initial_p_endpoints
        n_endpoints = graph_api.trace_differential_end_to_end(f"net:{n_net_name}") if n_net_name else []

    # 收集涵蓋網段
    covered_nets = list(set(
        [p_net_name] + ([n_net_name] if n_net_name else []) +
        [net for ep in p_endpoints for net in ep.get("covered_nets", [])] +
        [net for ep in n_endpoints for net in ep.get("covered_nets", [])]
    ))

    # 提取所有端點 RefDes 並依權重挑選發散源端 (start_ref) 與目標端點 (target_refs)
    unique_ep_refs: List[str] = []
    ep_by_ref: Dict[str, Dict[str, Any]] = {}
    for ep in (p_endpoints + n_endpoints):
        c = ep.get("component")
        ref = getattr(c, "ref_des", None) or (c.get("ref_des") if isinstance(c, dict) else None) or ep.get("ref_des")
        if ref and ref not in unique_ep_refs:
            unique_ep_refs.append(ref)
            ep_by_ref[ref] = ep

    # 依權重分數判定最佳源端 (如 CPU/Socket/IC 或外接連接器優先作為 start_ref)
    if len(unique_ep_refs) >= 2:
        best_root = max(unique_ep_refs, key=lambda r: _score_root_component(ep_by_ref[r]))
        start_ref = best_root
        target_refs = [r for r in unique_ep_refs if r != start_ref]
        end_ref = target_refs[0] if target_refs else None
    elif len(unique_ep_refs) == 1:
        start_ref = unique_ep_refs[0]
        target_refs = []
        end_ref = None
    else:
        start_ref = None
        target_refs = []
        end_ref = None

    # 產生全格式通道路徑鏈標題 (例如 TU1->R10->TJ1 或 XU1 -> XMM1, XMM2)
    channel_title = _format_channel_path_title(
        p_net_name=p_net_name,
        p_endpoints=p_endpoints,
        n_endpoints=n_endpoints,
        start_ref=start_ref,
        target_refs=target_refs,
        end_ref=end_ref,
    )

    # 預先建構標準完整雙軌拓撲視覺化資料 (含所有 connections)，確保無論任何返回分支皆有拓撲輸出
    topo_dict = _build_differential_topology(
        channel_title=channel_title,
        p_net_name=p_net_name,
        n_net_name=n_net_name,
        p_endpoints=p_endpoints,
        n_endpoints=n_endpoints,
        start_ref=start_ref,
        target_refs=target_refs,
        end_ref=end_ref,
    )

    # 端點數量不足 (例如單端懸空)，由極性/走線規則處理，此處安全略過並產出拓撲
    if len(p_endpoints) < 2:
        return RulePass(
            evidence={
                "channel_title": channel_title,
                "checked_target": channel_title,
                "covered_nets": covered_nets,
                "topology": topo_dict,
                "audit_summary": f"差分網路 {p_net_name} 連接之端點少於 2 個，不構成完整端到端通道。"
            },
            target_nodes={"nets": [p_net_name]}
        )

    # 提取兩端端點元件字典
    unique_endpoints: Dict[str, Any] = {}
    for ep in p_endpoints + n_endpoints:
        comp = ep["component"]
        unique_endpoints[comp.ref_des] = comp

    endpoint_names = list(unique_endpoints.keys())

    # 2. 判斷兩端端點是否皆同時上件
    all_endpoints_mounted = all(comp.is_mounted for comp in unique_endpoints.values())

    # 若兩端端點未同時上件 (例如設備未插上或主控未裝配)，安全通過並完整提供拓撲與未上件元件狀態
    if not all_endpoints_mounted:
        unmounted_ep_names = [comp.display_ref_des for comp in unique_endpoints.values() if not comp.is_mounted]
        return RulePass(
            evidence={
                "channel_title": channel_title,
                "checked_target": channel_title,
                "covered_nets": covered_nets,
                "topology": topo_dict,
                "audit_summary": (
                    f"差分通道端點元件 ({', '.join(unmounted_ep_names)}) 於當前 Config 下標註為未上件，"
                    "該通道未處於啟用工作狀態，安全略過導通性檢查。"
                )
            },
            target_nodes={"components": endpoint_names, "nets": covered_nets}
        )

    # 3. 兩端端點皆已上件：檢查中間所有途經串聯元件是否全部確實上件
    p_pass_comps = {c.ref_des: c for ep in p_endpoints for c in ep.get("pass_through_components", [])}
    n_pass_comps = {c.ref_des: c for ep in n_endpoints for c in ep.get("pass_through_components", [])}
    all_pass_comps = {**p_pass_comps, **n_pass_comps}

    violations: List[RuleViolation] = []

    for ref_des, comp in all_pass_comps.items():
        if not comp.is_mounted:
            err_msg = (
                f"差分通道 ({p_net_name} / {n_net_name or ''}) 兩端端點 ({channel_title}) 皆已上件，"
                f"但中間串聯元件 {comp.display_ref_des} ({comp.pn or comp.category}) 標註為未上件，"
                "導致高速訊號傳輸路徑電氣開路中斷！"
            )
            rec_msg = f"請將串聯元件 {comp.ref_des} 標註為上件 (I 或當前階段有效代碼)，以確保通道電氣導通。"
            violations.append(RuleViolation(
                error_message=err_msg,
                recommendation=rec_msg,
                severity="ERROR",
                evidence={
                    "channel_title": channel_title,
                    "faulty_component": comp.ref_des,
                    "component_type": comp.category,
                    "part_value": comp.pn,
                    "is_mounted": False,
                    "bom": comp.bom,
                    "covered_nets": covered_nets,
                    "topology": topo_dict,
                },
                target_nodes={
                    "components": [comp.ref_des] + endpoint_names,
                    "nets": [p_net_name] + ([n_net_name] if n_net_name else [])
                }
            ))

    if violations:
        return violations

    # 4. 若所有串聯元件皆確實上件，且兩端端點上件，判定 PASS
    pass_comps_desc = f"（途中串聯元件: {', '.join(all_pass_comps.keys())} 皆正常上件）" if all_pass_comps else "（直連差分通道）"
    return RulePass(
        evidence={
            "channel_title": channel_title,
            "checked_target": channel_title,
            "covered_nets": covered_nets,
            "audit_summary": f"差分通道兩端端點皆已上件，{pass_comps_desc}，電氣訊號完整導通。",
            "topology": topo_dict,
            "pass_through_components": list(all_pass_comps.keys()),
        },
        target_nodes={
            "components": endpoint_names + list(all_pass_comps.keys()),
            "nets": covered_nets
        },
        message=f"差分通道兩端皆已上件，串聯元件全數導通。"
    )
