"""
================================================================================
DesignShield SDK 通道追蹤與高階拓撲抽象模組 (Channel & Topology Abstraction)
================================================================================

職責:
1. 提供 BaseChannel 抽象基類，封裝端點元件、穿透元件、源端/目標端與上件審計狀態。
2. 提供 DifferentialChannel 高階差分通道物件，內建正負雙軌夥伴解析、直連 1 對多扇出、
   開路檢測 (is_continuous)、極性反接 (has_pn_swap) 與一鍵拓撲生成 (to_topology())。
3. 提供 SingleEndedChannel 單端通道物件，支援單軌主幹、上拉/下拉與接地分流元件關聯。
================================================================================
"""

import re
from typing import Dict, List, Any, Optional, Tuple, Union
from designshield.sdk.topology import TopologyGraphBuilder


def _score_root_component(comp_or_ep: Any) -> int:
    """
    評估端點作為通道發散源端 (Root / Host / Master) 之權重分數

    分數愈高代表愈適合作為發散源端 (start_ref)：
      3: 主控晶片 / CPU 插座 / SoC (RefDes 為 U*, XU*, CPU*, SOC* 或類別為 IC / Processor / BGA / Socket)
      2: 板級外部入口連接器 (RefDes 為 TJ*, J* 或含有 Type-C / USB / Receptacle)
      1: 一般元件
      0: 記憶體插槽 / 子插槽 / 終端負載 (如 XMM*, DIMM*, SLOT*)

    @param {Any} comp_or_ep - 元件節點物件、字典或端點追蹤審計字典
    @returns {int} 權重分數 (0~3)
    """
    if not comp_or_ep:
        return 1

    if isinstance(comp_or_ep, dict) and "component" in comp_or_ep:
        c = comp_or_ep["component"]
    else:
        c = comp_or_ep

    ref = str(getattr(c, "ref_des", None) or (c.get("ref_des") if isinstance(c, dict) else "") or "").upper()
    cat = str(getattr(c, "category", None) or (c.get("category") if isinstance(c, dict) else "") or "").lower()
    pn = str(
        getattr(c, "pn", None) or
        getattr(c, "part_number", None) or
        (c.get("part_number") if isinstance(c, dict) else "") or
        (c.get("pn") if isinstance(c, dict) else "") or
        ""
    ).lower()

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


def _resolve_n_partner_name(p_net_name: str, p_node: Any, G: Any) -> Optional[str]:
    """
    解析正極差分網路對應之負極夥伴網路名稱

    雙層判定機制:
      1. 第一層：讀取節點中的 diff_pair_partner 屬性 (來自圖譜或 Level 2 分類標籤)。
      2. 第二層：正規表示式雙向推導候選 (支援 USB DP/DM、DDR/PCIe DP/DN、D+/D- 等)。

    @param {str} p_net_name - 正極網路名稱
    @param {Any} p_node - 正極網路節點資料
    @param {Any} G - NetworkX 圖譜實例
    @returns {Optional[str]} 負極網路名稱，若未查得則回傳 None
    """
    partner_id = getattr(p_node, "diff_pair_partner", None) or (p_node.get("diff_pair_partner") if isinstance(p_node, dict) else None)
    if partner_id:
        return partner_id.replace("net:", "")

    # 若未帶 partner，嘗試自圖譜中直接獲取 net 節點屬性
    if G.has_node(f"net:{p_net_name}"):
        g_node = G.nodes[f"net:{p_net_name}"]
        partner_id = g_node.get("diff_pair_partner")
        if partner_id:
            return partner_id.replace("net:", "")

    # 正規表示式推導候選清單
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
        if cand and (G.has_node(cand) or G.has_node(f"net:{cand}")):
            return cand
    return None


class BaseChannel:
    """
    通用通道抽象基類 (Base Channel Abstraction)

    封裝單一通道之端點元件、穿透元件、上件狀態與拓撲產出方法。
    """

    def __init__(
        self,
        name: str,
        channel_type: str = "single",
        endpoints: Optional[List[Dict[str, Any]]] = None,
        pass_components: Optional[List[Dict[str, Any]]] = None,
        covered_nets: Optional[List[str]] = None,
    ):
        self.name: str = name
        self.channel_type: str = channel_type
        self.endpoints: List[Dict[str, Any]] = endpoints or []
        self.pass_components: List[Dict[str, Any]] = pass_components or []
        self.covered_nets: List[str] = list(set(covered_nets or [name]))

        # 源端與目標端判定
        self.root: Optional[Dict[str, Any]] = None
        self.targets: List[Dict[str, Any]] = []
        self._organize_endpoints()

    def _organize_endpoints(self) -> None:
        """依權重識別發散源端 (root) 與目標端點列表 (targets)"""
        if not self.endpoints:
            self.root = None
            self.targets = []
            return

        if len(self.endpoints) == 1:
            self.root = self.endpoints[0]
            self.targets = []
            return

        # 挑選最高權重端點為源端
        best_root = max(self.endpoints, key=_score_root_component)
        self.root = best_root
        best_ref = getattr(best_root.get("component"), "ref_des", None) or best_root.get("ref_des")
        self.targets = [
            ep for ep in self.endpoints
            if (getattr(ep.get("component"), "ref_des", None) or ep.get("ref_des")) != best_ref
        ]

    @property
    def root_ref(self) -> Optional[str]:
        """源端元件 RefDes"""
        if not self.root:
            return None
        c = self.root.get("component") if "component" in self.root else self.root
        return getattr(c, "ref_des", None) or (c.get("ref_des") if isinstance(c, dict) else None) or self.root.get("ref_des")

    @property
    def target_refs(self) -> List[str]:
        """所有目標端點之 RefDes 清單"""
        refs = []
        for ep in self.targets:
            c = ep.get("component") if "component" in ep else ep
            ref = getattr(c, "ref_des", None) or (c.get("ref_des") if isinstance(c, dict) else None) or ep.get("ref_des")
            if ref and ref not in refs:
                refs.append(ref)
        return refs

    @property
    def endpoint_refs(self) -> List[str]:
        """所有端點元件之 RefDes 清單 (去重)"""
        refs = []
        for ep in self.endpoints:
            c = ep.get("component") if "component" in ep else ep
            ref = getattr(c, "ref_des", None) or (c.get("ref_des") if isinstance(c, dict) else None) or ep.get("ref_des")
            if ref and ref not in refs:
                refs.append(ref)
        return refs

    @property
    def pass_component_refs(self) -> List[str]:
        """途經之所有串聯穿透元件 RefDes 清單 (去重)"""
        refs = []
        for c in self.pass_components:
            ref = getattr(c, "ref_des", None) or (c.get("ref_des") if isinstance(c, dict) else None)
            if ref and ref not in refs:
                refs.append(ref)
        return refs

    @property
    def all_component_refs(self) -> List[str]:
        """通道關聯之所有元件 (端點 + 穿透) 之 RefDes 清單 (去重)"""
        return list(dict.fromkeys(self.endpoint_refs + self.pass_component_refs))

    @property
    def is_fully_mounted(self) -> bool:
        """判定通道上所有端點元件與串聯穿透元件是否皆已確實上件"""
        return self.endpoints_mounted and len(self.unmounted_pass_components) == 0

    @property
    def endpoints_mounted(self) -> bool:
        """判定通道兩端所有端點元件是否皆已上件 (是否處於啟用裝配狀態)"""
        if not self.endpoints:
            return False
        for ep in self.endpoints:
            c = ep.get("component") if "component" in ep else ep
            is_mounted = getattr(c, "is_mounted", True) if c else True
            if isinstance(c, dict) and "is_mounted" in c:
                is_mounted = c["is_mounted"]
            if not is_mounted:
                return False
        return True

    @property
    def unmounted_endpoints(self) -> List[Dict[str, Any]]:
        """回傳當前 Config 下未上件之端點元件清單"""
        unmounted = []
        for ep in self.endpoints:
            c = ep.get("component") if "component" in ep else ep
            is_mounted = getattr(c, "is_mounted", True) if c else True
            if isinstance(c, dict) and "is_mounted" in c:
                is_mounted = c["is_mounted"]
            if not is_mounted:
                unmounted.append(ep)
        return unmounted

    @property
    def unmounted_pass_components(self) -> List[Dict[str, Any]]:
        """回傳當前 Config 下未上件之串聯穿透元件清單 (導致通道電氣開路)"""
        unmounted = []
        for c in self.pass_components:
            is_mounted = getattr(c, "is_mounted", True) if c else True
            if isinstance(c, dict) and "is_mounted" in c:
                is_mounted = c["is_mounted"]
            if not is_mounted:
                unmounted.append(c)
        return unmounted

    @property
    def title(self) -> str:
        """產生人類易讀之通道完整路徑鏈標題 (如 XU1 -> XMM1, XMM2 (Channel))"""
        pass_refs = []
        for c in self.pass_components:
            ref = getattr(c, "ref_des", None) or (c.get("ref_des") if isinstance(c, dict) else None)
            if ref and ref not in pass_refs:
                pass_refs.append(ref)

        dst_str = ", ".join(self.target_refs) if self.target_refs else ""
        if self.root_ref and dst_str:
            if pass_refs:
                path_chain = f"{self.root_ref} -> {' -> '.join(pass_refs)} -> {dst_str}"
            else:
                path_chain = f"{self.root_ref} -> {dst_str}"
        elif self.root_ref:
            path_chain = f"{self.root_ref} -> {' -> '.join(pass_refs)}" if pass_refs else f"{self.root_ref} -> (懸空)"
        else:
            path_chain = self.name

        base_channel = re.sub(r"(?i)(?:_P|_DP|DP|D\+)$", "", self.name)
        clean_channel = re.sub(r"(?i)(?:_CMC|_C)$", "", base_channel)
        return f"{path_chain} ({clean_channel} 差分通道)" if self.channel_type == "differential" else f"{path_chain} ({clean_channel} 通道)"

    def to_topology(self) -> Dict[str, Any]:
        """
        產出符合 UniversalTopologyData 規格之完整拓撲字典
        子類應實作具體連線與軌道細節。
        """
        raise NotImplementedError("Subclasses must implement to_topology()")


class DifferentialChannel(BaseChannel):
    """
    高速差分雙軌通道高階模型 (Differential Dual-Rail Channel Model)

    支援正負極 (P/N) 網路夥伴解析、穿透元件串聯段落追蹤、直連多端點扇出 (Multi-drop)、
    開路狀態審計 (is_continuous) 與極性對稱性檢驗。
    """

    def __init__(
        self,
        p_net_name: str,
        n_net_name: Optional[str] = None,
        p_endpoints: Optional[List[Dict[str, Any]]] = None,
        n_endpoints: Optional[List[Dict[str, Any]]] = None,
        p_segments: Optional[List[Dict[str, Any]]] = None,
        n_segments: Optional[List[Dict[str, Any]]] = None,
        symmetry_result: Optional[Dict[str, Any]] = None,
    ):
        self.p_net_name: str = p_net_name
        self.n_net_name: Optional[str] = n_net_name
        self.p_endpoints: List[Dict[str, Any]] = p_endpoints or []
        self.n_endpoints: List[Dict[str, Any]] = n_endpoints or []
        self.p_segments: List[Dict[str, Any]] = p_segments or []
        self.n_segments: List[Dict[str, Any]] = n_segments or []
        self.symmetry_result: Optional[Dict[str, Any]] = symmetry_result

        # 合併正負端點元件為統一端點表
        combined_endpoints = self._merge_endpoints(self.p_endpoints, self.n_endpoints)

        # 提取途中所有穿透元件
        combined_pass_comps = self._extract_pass_components(self.p_endpoints, self.n_endpoints, self.p_segments)

        # 收集涵蓋的所有子網段
        all_nets = [p_net_name] + ([n_net_name] if n_net_name else [])
        for ep in self.p_endpoints + self.n_endpoints:
            all_nets.extend(ep.get("covered_nets", []))

        super().__init__(
            name=p_net_name,
            channel_type="differential",
            endpoints=combined_endpoints,
            pass_components=combined_pass_comps,
            covered_nets=list(dict.fromkeys(all_nets)),
        )

    @staticmethod
    def _merge_endpoints(p_eps: List[Dict[str, Any]], n_eps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """合併正負端點為不重複之端點清單 (保持順序)"""
        merged: List[Dict[str, Any]] = []
        seen_refs = set()
        for ep in p_eps + n_eps:
            c = ep.get("component") if "component" in ep else ep
            ref = getattr(c, "ref_des", None) or (c.get("ref_des") if isinstance(c, dict) else None) or ep.get("ref_des")
            if ref and ref not in seen_refs:
                seen_refs.add(ref)
                merged.append(ep)
        return merged

    @staticmethod
    def _extract_pass_components(
        p_eps: List[Dict[str, Any]],
        n_eps: List[Dict[str, Any]],
        p_segs: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """提取途中所有穿透元件之物件字典"""
        comps: Dict[str, Any] = {}
        # 1. 優先從 endpoints 內之 pass_through_components 提取完整 ComponentNode
        for ep in p_eps + n_eps:
            for c in ep.get("pass_through_components", []):
                ref = getattr(c, "ref_des", None) or (c.get("ref_des") if isinstance(c, dict) else None)
                if ref and ref not in comps:
                    comps[ref] = c

        # 2. 若有未涵蓋者從 path_segments 補充提取
        for seg in p_segs:
            ref = seg.get("pass_component")
            if ref and ref not in comps:
                comps[ref] = {
                    "ref_des": ref,
                    "category": seg.get("pass_component_type", "Passive"),
                    "is_mounted": seg.get("is_mounted", True),
                    "bom": seg.get("bom"),
                    "pn": seg.get("part_number") or seg.get("pass_component_type"),
                }

        return list(comps.values())

    @property
    def is_continuous(self) -> bool:
        """
        差分通道導通性判定:
        若兩端端點皆已裝配上件，且中間無任何串聯元件未上件，則判定導通為 True。
        """
        return self.endpoints_mounted and len(self.unmounted_pass_components) == 0

    @property
    def is_symmetric(self) -> bool:
        """判定差分正負軌道串聯被動元件是否具備電氣與封裝對稱性"""
        if self.symmetry_result:
            return bool(self.symmetry_result.get("is_symmetric", True))
        return len(self.p_segments) == len(self.n_segments)

    def to_topology(self) -> Dict[str, Any]:
        """
        建構標準 UniversalTopology 拓撲字典
        包含 P/N 雙軌、終端節點、途中串聯元件、1 對多扇出導線與實體電氣焊點。
        """
        builder = TopologyGraphBuilder(title=self.title, channel_type="differential")
        builder.add_rail("p_rail", f"正極軌道 ({self.p_net_name})", polarity="P")
        if self.n_net_name:
            builder.add_rail("n_rail", f"負極軌道 ({self.n_net_name})", polarity="N")

        def _populate_rail(
            rail_id: str,
            start_net: str,
            endpoints: List[Dict[str, Any]],
            segments: List[Dict[str, Any]],
        ):
            if not start_net and not endpoints:
                return

            endpoints_by_net: Dict[str, List[Dict[str, Any]]] = {}
            for ep in endpoints:
                c = ep.get("component") if "component" in ep else ep
                net = ep.get("connected_net") or (ep.get("terminal_net").net_name if ep.get("terminal_net") else start_net)
                endpoints_by_net.setdefault(net, []).append(ep)

                ref_des = getattr(c, "ref_des", None) or (c.get("ref_des") if isinstance(c, dict) else None) or ep.get("ref_des")
                cat = getattr(c, "category", None) or (c.get("category") if isinstance(c, dict) else None) or "IC"
                pn = getattr(c, "pn", None) or (c.get("part_value") if isinstance(c, dict) else None) or (c.get("part_number") if isinstance(c, dict) else None) or ""
                is_mounted = getattr(c, "is_mounted", True) if c else True
                if isinstance(c, dict) and "is_mounted" in c:
                    is_mounted = c["is_mounted"]
                bom = getattr(c, "bom", None) or (c.get("bom") if isinstance(c, dict) else None)
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

            # 2. 直連通道 (無途中穿透元件)
            if not segments:
                if len(endpoints) >= 2:
                    ep_map = {}
                    for ep in endpoints:
                        c = ep.get("component") if "component" in ep else ep
                        ref = getattr(c, "ref_des", None) or (c.get("ref_des") if isinstance(c, dict) else None) or ep.get("ref_des")
                        if ref:
                            ep_map[ref] = ep

                    # 確定源端 root_ref
                    root_ref = self.root_ref if (self.root_ref and self.root_ref in ep_map) else list(ep_map.keys())[0]
                    ep_from = ep_map[root_ref]
                    pin_from = ep_from.get("pin_number") or ep_from.get("pin") or "1"

                    # 確定所有目標端點清單
                    destination_refs = [r for r in (self.target_refs or list(ep_map.keys())) if r in ep_map and r != root_ref]
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
                c = ep.get("component") if "component" in ep else ep
                ref = getattr(c, "ref_des", None) or (c.get("ref_des") if isinstance(c, dict) else None) or ep.get("ref_des")
                pin = ep.get("pin_number") or ep.get("pin") or "1"
                builder.add_connection(
                    net_name=first_seg["from_net"],
                    rail_id=rail_id,
                    from_node=ref,
                    from_pin=pin,
                    to_node=first_seg["pass_component"],
                    to_pin=first_seg.get("in_pin", "1")
                )

            # 穿透元件串聯段落之間
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

            # 最後一顆穿透元件 -> 終端端點連線 (支援多終端並聯)
            last_seg = segments[-1]
            end_eps = endpoints_by_net.get(last_seg["to_net"], [])
            if not end_eps and len(endpoints) >= 2:
                end_eps = endpoints[1:]
            for ep in end_eps:
                c = ep.get("component") if "component" in ep else ep
                ref = getattr(c, "ref_des", None) or (c.get("ref_des") if isinstance(c, dict) else None) or ep.get("ref_des")
                pin = ep.get("pin_number") or ep.get("pin") or "1"
                builder.add_connection(
                    net_name=last_seg["to_net"],
                    rail_id=rail_id,
                    from_node=last_seg["pass_component"],
                    from_pin=last_seg.get("out_pin", "2"),
                    to_node=ref,
                    to_pin=pin
                )

        p_segs = self.p_segments
        if not p_segs:
            for ep in self.p_endpoints:
                segs = ep.get("path_segments", [])
                if segs and len(segs) > len(p_segs):
                    p_segs = segs

        n_segs = self.n_segments
        if not n_segs:
            for ep in self.n_endpoints:
                segs = ep.get("path_segments", [])
                if segs and len(segs) > len(n_segs):
                    n_segs = segs

        _populate_rail("p_rail", self.p_net_name, self.p_endpoints, p_segs)
        if self.n_net_name:
            _populate_rail("n_rail", self.n_net_name, self.n_endpoints, n_segs)

        return builder.to_dict()


class SingleEndedChannel(BaseChannel):
    """
    單端訊號與匯流排通道高階模型 (Single-Ended & Bus Channel Model)

    支援單軌端到端直通追蹤、上拉至 VCC 電阻、下拉接地電阻與對地分流電容/TVS 拓撲。
    """

    def __init__(
        self,
        net_name: str,
        endpoints: Optional[List[Dict[str, Any]]] = None,
        pass_components: Optional[List[Dict[str, Any]]] = None,
        pull_ups: Optional[List[Dict[str, Any]]] = None,
        pull_downs: Optional[List[Dict[str, Any]]] = None,
        shunts: Optional[List[Dict[str, Any]]] = None,
        covered_nets: Optional[List[str]] = None,
    ):
        super().__init__(
            name=net_name,
            channel_type="single",
            endpoints=endpoints,
            pass_components=pass_components,
            covered_nets=covered_nets,
        )
        self.pull_ups: List[Dict[str, Any]] = pull_ups or []
        self.pull_downs: List[Dict[str, Any]] = pull_downs or []
        self.shunts: List[Dict[str, Any]] = shunts or []

    @property
    def has_pullup(self) -> bool:
        """判定該通道是否具備上拉電阻"""
        return len(self.pull_ups) > 0

    @property
    def has_pulldown(self) -> bool:
        """判定該通道是否具備下拉電阻"""
        return len(self.pull_downs) > 0

    @property
    def has_shunt_cap(self) -> bool:
        """判定該通道是否具備對地分流電容"""
        return any(s.get("category") == "Capacitor" or s.get("sub_category") == "Capacitor" for s in self.shunts)

    def to_topology(self) -> Dict[str, Any]:
        """建構標準 UniversalTopology 拓撲字典 (含單軌主幹與垂直支路)"""
        builder = TopologyGraphBuilder(title=self.title, channel_type="single")
        builder.add_rail("main", f"主訊號軌道 ({self.name})")

        # 1. 加入主幹端點元件
        for ep in self.endpoints:
            c = ep.get("component") if "component" in ep else ep
            ref = getattr(c, "ref_des", None) or (c.get("ref_des") if isinstance(c, dict) else None) or ep.get("ref_des")
            cat = getattr(c, "category", None) or (c.get("category") if isinstance(c, dict) else None) or "IC"
            pn = getattr(c, "pn", None) or (c.get("part_value") if isinstance(c, dict) else None) or ""
            is_mounted = getattr(c, "is_mounted", True) if c else True
            if isinstance(c, dict) and "is_mounted" in c:
                is_mounted = c["is_mounted"]
            bom = getattr(c, "bom", None) or (c.get("bom") if isinstance(c, dict) else None)
            pin_num = ep.get("pin_number") or ep.get("pin") or "1"
            pin_name = ep.get("pin_name") or ep.get("pin") or pin_num

            builder.add_terminal(
                id=ref,
                ref_des=ref,
                category=cat,
                part_number=pn,
                is_mounted=bool(is_mounted),
                bom=bom,
                pins=[{"pin_number": pin_num, "pin_name": pin_name}]
            )

        # 2. 直連多端點扇出
        if len(self.endpoints) >= 2 and not self.pass_components:
            root_ref = self.root_ref or self.endpoints[0]["ref_des"]
            root_ep = next((ep for ep in self.endpoints if (ep.get("ref_des") or getattr(ep.get("component"), "ref_des", None)) == root_ref), self.endpoints[0])
            pin_from = root_ep.get("pin_number") or root_ep.get("pin") or "1"

            for ep in self.endpoints:
                dst_ref = ep.get("ref_des") or getattr(ep.get("component"), "ref_des", None)
                if dst_ref and dst_ref != root_ref:
                    pin_to = ep.get("pin_number") or ep.get("pin") or "1"
                    builder.add_connection(
                        net_name=self.name,
                        rail_id="main",
                        from_node=root_ref,
                        from_pin=pin_from,
                        to_node=dst_ref,
                        to_pin=pin_to,
                        is_branch=False
                    )

        # 3. 串聯穿透元件
        for pc in self.pass_components:
            ref = getattr(pc, "ref_des", None) or pc.get("ref_des")
            builder.add_series_component(
                id=ref,
                ref_des=ref,
                category=getattr(pc, "category", "Passive") or "Passive",
                is_mounted=getattr(pc, "is_mounted", True),
                bom=getattr(pc, "bom", None)
            )

        # 4. 上拉、下拉與接地支路
        for pu in self.pull_ups:
            ref = getattr(pu, "ref_des", None) or (pu.get("ref_des") if isinstance(pu, dict) else None)
            pwr = pu.get("power_rail") if isinstance(pu, dict) else getattr(pu, "power_rail", "+VCC")
            val = getattr(pu, "part_value", None) or (pu.get("part_value") if isinstance(pu, dict) else None)
            builder.add_pull_up(
                id=ref,
                ref_des=ref,
                power_net=pwr or "+VCC",
                value=val,
            )

        for pd in self.pull_downs:
            ref = getattr(pd, "ref_des", None) or (pd.get("ref_des") if isinstance(pd, dict) else None)
            val = getattr(pd, "part_value", None) or (pd.get("part_value") if isinstance(pd, dict) else None)
            builder.add_shunt_ground(
                id=ref,
                ref_des=ref,
                category="Resistor",
                value=val,
                gnd_net="GND",
            )

        for sh in self.shunts:
            ref = getattr(sh, "ref_des", None) or (sh.get("ref_des") if isinstance(sh, dict) else None)
            cat = getattr(sh, "category", "Capacitor") or (sh.get("category") if isinstance(sh, dict) else "Capacitor")
            val = getattr(sh, "part_value", None) or (sh.get("part_value") if isinstance(sh, dict) else None)
            builder.add_shunt_ground(
                id=ref,
                ref_des=ref,
                category=cat,
                value=val,
                gnd_net="GND",
            )

        return builder.to_dict()
