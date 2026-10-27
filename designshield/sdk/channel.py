"""
================================================================================
DesignShield SDK 通道追蹤與高階拓撲抽象模組 (Channel & Topology Abstraction)
================================================================================

職責:
1. 提供 BaseChannel 抽象基類，封裝端點元件、穿透元件、源端/目標端與上件審計狀態。
2. 提供 DifferentialChannel 高階差分通道物件，內建正負雙軌夥伴解析、直連 1 對多扇出、
   中繼晶片 (Hub/Mux) 識別、單腳測試點 (TP*) 分離、開路檢測 (is_continuous) 與一鍵拓撲生成 (to_topology())。
3. 提供 SingleEndedChannel 單端通道物件，支援單軌主幹、上拉/下拉與接地分流元件關聯。
================================================================================
"""

import re
from typing import Dict, List, Any, Optional, Set, Tuple, Union
from designshield.sdk.topology import TopologyGraphBuilder
from designshield.sdk.channel_graph import (
    RailNetGraph,
    endpoint_ref,
    endpoint_net,
    is_test_point_component,
)


def _extract_ref_number(ref: str) -> int:
    """提取元件位號中的數字序號 (如 U4 -> 4, U78 -> 78)，用於同級晶片排序"""
    m = re.search(r"(\d+)", ref or "")
    return int(m.group(1)) if m else 999999


def _score_root_component(comp_or_ep: Any, branch_out_degree: int = 0) -> Tuple[int, int, int, int, int]:
    """
    評估端點作為通道發散源端 (Root / Host / Master) 之多維度優先權重 Tuple

    嚴格落實硬體工程慣例:
      1. 非測試點永遠優先於單腳測試點 (TP*)
      2. 元件角色階層 (role_tier):
         - 5: CPU Socket / 主處理器座 (XU*, CPU*, SOC*, Socket_LGA)
         - 4: 核心主控晶片 (標準 U\\d+ 命名之 IC，如 U4 PCH)
         - 3: 子系統/週邊 IC (如 VU*, LU*, KU* 或其他 IC)
         - 2: 一般非連接器元件
         - 1: 板級外部連接器 (J*, TJ*, P*, CN*, CON*)
         - 0: 記憶體插槽 / 擴充槽負載 (XMM*, DIMM*, SLOT*)
      3. 分叉源頭度數 (branch_out_degree): 位於 1-to-N 分叉根部之端點優先於末梢葉節點
      4. 上件狀態 (is_mounted): 已上件 (1) 優先於未上件 (0)
      5. 晶片序號 (-ref_num): 同級核心 IC 中編號較小之主控 (如 U4) 優先於週邊 IC (如 U78)

    @param {Any} comp_or_ep - 元件節點物件、字典或端點追蹤審計字典
    @param {int} branch_out_degree - 該端點所在網路連接之非並聯穿透支路數
    @returns {Tuple[int, int, int, int, int]} 可直接比較大小之權重 Tuple
    """
    if not comp_or_ep:
        return (0, 0, 0, 0, 0)

    c = comp_or_ep.get("component") if isinstance(comp_or_ep, dict) and "component" in comp_or_ep else comp_or_ep

    ref = str(
        getattr(c, "ref_des", None)
        or (c.get("ref_des") if isinstance(c, dict) else "")
        or (comp_or_ep.get("ref_des") if isinstance(comp_or_ep, dict) else "")
        or ""
    ).upper()
    cat = str(
        getattr(c, "category", None)
        or (c.get("category") if isinstance(c, dict) else "")
        or (comp_or_ep.get("component_type") if isinstance(comp_or_ep, dict) else "")
        or ""
    ).lower()
    pn = str(
        getattr(c, "pn", None)
        or getattr(c, "part_number", None)
        or (c.get("part_number") if isinstance(c, dict) else "")
        or (c.get("pn") if isinstance(c, dict) else "")
        or (comp_or_ep.get("part_number") if isinstance(comp_or_ep, dict) else "")
        or ""
    ).lower()

    is_mounted = getattr(c, "is_mounted", True) if c else True
    if isinstance(c, dict) and "is_mounted" in c:
        is_mounted = bool(c["is_mounted"])
    elif isinstance(comp_or_ep, dict) and "is_mounted" in comp_or_ep:
        is_mounted = bool(comp_or_ep["is_mounted"])

    non_tp = 0 if is_test_point_component(comp_or_ep) else 1

    # 判定角色階層 role_tier
    is_connector_ref = bool(re.match(r"^(?:J|TJ|P|CN|CON|XMM)\d*", ref)) and not ref.startswith("XU")
    if ref.startswith("XMM") or "dimm" in pn or "udimm" in pn or "rdimm" in pn or "sodimm" in pn:
        role_tier = 0
    elif ref.startswith(("XU", "CPU", "SOC")) or "socket" in pn or "lga" in pn or "processor" in cat:
        role_tier = 5
    elif is_connector_ref or ("connector" in cat and not ref.startswith("XU")):
        role_tier = 1
    elif cat == "ic" or (ref.startswith("U") and not ref.startswith("USB")) or "bga" in pn:
        if re.match(r"^U\d+$", ref):
            role_tier = 4
        else:
            role_tier = 3
    else:
        role_tier = 2

    ref_num = _extract_ref_number(ref)
    return (non_tp, role_tier, int(branch_out_degree), 1 if is_mounted else 0, -ref_num)


def _resolve_n_partner_name(p_net_name: str, p_node: Any, G: Any) -> Optional[str]:
    """
    解析正極差分網路對應之負極夥伴網路名稱

    優先自圖譜節點屬性 (diff_pair_partner) 取得；
    若無則透過 SDK diff_pair 核心推導器產出候選名稱並驗證圖譜存在性。

    @param {str} p_net_name - 正極網路名稱
    @param {Any} p_node - 正極網路節點資料
    @param {Any} G - NetworkX 圖譜實例
    @returns {Optional[str]} 負極網路名稱，若未查得則回傳 None
    """
    from designshield.sdk.diff_pair import resolve_diff_pair_candidates

    partner_id = getattr(p_node, "diff_pair_partner", None) or (p_node.get("diff_pair_partner") if isinstance(p_node, dict) else None)
    if partner_id:
        return partner_id.replace("net:", "")

    if G.has_node(f"net:{p_net_name}"):
        g_node = G.nodes[f"net:{p_net_name}"]
        partner_id = g_node.get("diff_pair_partner")
        if partner_id:
            return partner_id.replace("net:", "")

    candidates = resolve_diff_pair_candidates(p_net_name, "N")
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
        net_branch_degrees: Optional[Dict[str, int]] = None,
    ):
        self.name: str = name
        self.channel_type: str = channel_type
        self.endpoints: List[Dict[str, Any]] = endpoints or []
        self.pass_components: List[Dict[str, Any]] = pass_components or []
        self.covered_nets: List[str] = list(dict.fromkeys(covered_nets or [name]))
        self._net_branch_degrees: Dict[str, int] = net_branch_degrees or {}

        # 源端與目標端判定
        self.root: Optional[Dict[str, Any]] = None
        self.targets: List[Dict[str, Any]] = []
        self._organize_endpoints()

    def _organize_endpoints(self) -> None:
        """依綜合權重識別發散源端 (root) 與目標端點列表 (targets)"""
        if not self.endpoints:
            self.root = None
            self.targets = []
            return

        if len(self.endpoints) == 1:
            self.root = self.endpoints[0]
            self.targets = []
            return

        def _ep_key(ep: Dict[str, Any]) -> Tuple[int, int, int, int, int]:
            net = endpoint_net(ep, self.name)
            deg = self._net_branch_degrees.get(net, 0)
            return _score_root_component(ep, branch_out_degree=deg)

        best_root = max(self.endpoints, key=_ep_key)
        self.root = best_root
        best_ref = endpoint_ref(best_root)
        raw_targets = [
            ep for ep in self.endpoints
            if endpoint_ref(ep) != best_ref
        ]

        # 目標端點排序：非測試點優先 > 已上件優先 > 外部連接器 (Connector) 優先為第一主終點
        def _target_sort_key( idx_ep: Tuple[int, Dict[str, Any]]) -> Tuple[int, int, int, int]:
            idx, ep = idx_ep
            c = ep.get("component") if isinstance(ep, dict) and "component" in ep else ep
            ref = endpoint_ref(ep).upper()
            cat = str(
                getattr(c, "category", None)
                or (c.get("category") if isinstance(c, dict) else "")
                or (ep.get("component_type") if isinstance(ep, dict) else "")
                or ""
            ).lower()
            is_mounted = getattr(c, "is_mounted", True) if c else True
            if isinstance(c, dict) and "is_mounted" in c:
                is_mounted = bool(c["is_mounted"])
            elif isinstance(ep, dict) and "is_mounted" in ep:
                is_mounted = bool(ep["is_mounted"])

            is_tp = 1 if is_test_point_component(ep) else 0
            is_conn = 1 if (re.match(r"^(?:J|TJ|P|CN|CON)\d*", ref) or "connector" in cat) and not ref.startswith("XU") else 0
            return (is_tp, 0 if is_mounted else 1, 0 if is_conn else 1, idx)

        self.targets = [ep for _, ep in sorted(enumerate(raw_targets), key=_target_sort_key)]

    @property
    def root_ref(self) -> Optional[str]:
        """源端元件 RefDes"""
        if not self.root:
            return None
        return endpoint_ref(self.root) or None

    @property
    def target_refs(self) -> List[str]:
        """所有目標端點之 RefDes 清單"""
        refs = []
        for ep in self.targets:
            ref = endpoint_ref(ep)
            if ref and ref not in refs:
                refs.append(ref)
        return refs

    @property
    def endpoint_refs(self) -> List[str]:
        """所有端點元件之 RefDes 清單 (去重)"""
        refs = []
        for ep in self.endpoints:
            ref = endpoint_ref(ep)
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
        """判定通道兩端所有主要端點元件 (排除單腳測試點) 是否皆已上件"""
        if not self.endpoints:
            return False
        non_tp = [ep for ep in self.endpoints if not is_test_point_component(ep)]
        check_list = non_tp if non_tp else self.endpoints
        for ep in check_list:
            c = ep.get("component") if "component" in ep else ep
            is_mounted = getattr(c, "is_mounted", True) if c else True
            if isinstance(c, dict) and "is_mounted" in c:
                is_mounted = c["is_mounted"]
            elif "is_mounted" in ep:
                is_mounted = ep["is_mounted"]
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
            elif "is_mounted" in ep:
                is_mounted = ep["is_mounted"]
            if not is_mounted:
                unmounted.append(ep)
        return unmounted

    @property
    def unmounted_pass_components(self) -> List[Dict[str, Any]]:
        """回傳當前 Config 下未上件之串聯穿透元件清單"""
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
        """產生人類易讀之通道完整路徑鏈標題 (如 U4 -> UR810 -> UR811 -> J81 (Channel))"""
        pass_refs = []
        for c in self.pass_components:
            ref = getattr(c, "ref_des", None) or (c.get("ref_des") if isinstance(c, dict) else None)
            if ref and ref not in pass_refs:
                pass_refs.append(ref)

        # 目標端點排序：主要終端 (Connector / IC) 排前，測試點 (TP*) 排後
        non_tp_targets = [r for r in self.target_refs if not re.match(r"^(?:TP|TTP|CTP)\d+", r.upper())]
        tp_targets = [r for r in self.target_refs if re.match(r"^(?:TP|TTP|CTP)\d+", r.upper())]
        ordered_targets = non_tp_targets + tp_targets

        dst_str = ", ".join(ordered_targets) if ordered_targets else ""
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
        """產出符合 UniversalTopologyData 規格之完整拓撲字典"""
        raise NotImplementedError("Subclasses must implement to_topology()")


class DifferentialChannel(BaseChannel):
    """
    高速差分雙軌通道高階模型 (Differential Dual-Rail Channel Model)

    支援正負極 (P/N) 網路夥伴解析、穿透元件串聯段落追蹤、中繼晶片 (Hub/Mux) 轉換、
    單腳測試點 (TP*) 標記、直連多端點扇出 (Multi-drop)、開路狀態審計與極性對稱性檢驗。
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
        partdb_missing: Optional[List[Dict[str, Any]]] = None,
    ):
        self.p_net_name: str = p_net_name
        self.n_net_name: Optional[str] = n_net_name
        self.p_endpoints: List[Dict[str, Any]] = p_endpoints or []
        self.n_endpoints: List[Dict[str, Any]] = n_endpoints or []
        self.p_segments: List[Dict[str, Any]] = p_segments or self._collect_all_segments(self.p_endpoints)
        self.n_segments: List[Dict[str, Any]] = n_segments or self._collect_all_segments(self.n_endpoints)
        self.symmetry_result: Optional[Dict[str, Any]] = symmetry_result
        self.partdb_missing: List[Dict[str, Any]] = partdb_missing or []

        # 1. 偵測在單一軌道上跨接 2 條不同網路的中繼 IC (如 USB Hub KU100)
        self.relay_refs: Set[str] = self._detect_inline_relay_refs(self.p_endpoints, self.p_net_name)

        # 2. 合併正負端點元件為統一端點表 (排除已識別為中繼穿透之 relay_refs)
        combined_endpoints = [
            ep for ep in self._merge_endpoints(self.p_endpoints, self.n_endpoints)
            if endpoint_ref(ep) not in self.relay_refs
        ]

        # 3. 提取途中所有穿透元件 (包含中繼晶片)
        combined_pass_comps = self._extract_pass_components(
            self.p_endpoints,
            self.n_endpoints,
            self.p_segments + self.n_segments,
            self.relay_refs,
        )

        # 4. 計算 P 軌各網路連接之非並聯分支度數 (供識別 1-to-N 分叉根部端點如 U4)
        net_branch_degrees = self._compute_net_branch_degrees(self.p_segments)

        # 5. 收集涵蓋的所有子網段
        all_nets = [p_net_name] + ([n_net_name] if n_net_name else [])
        for ep in self.p_endpoints + self.n_endpoints:
            all_nets.extend(ep.get("covered_nets", []))
        for seg in self.p_segments + self.n_segments:
            if seg.get("from_net"):
                all_nets.append(seg["from_net"])
            if seg.get("to_net"):
                all_nets.append(seg["to_net"])

        super().__init__(
            name=p_net_name,
            channel_type="differential",
            endpoints=combined_endpoints,
            pass_components=combined_pass_comps,
            covered_nets=list(dict.fromkeys(all_nets)),
            net_branch_degrees=net_branch_degrees,
        )

    @staticmethod
    def _collect_all_segments(endpoints: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """從所有端點收集完整 path_segments (去重)"""
        collected: List[Dict[str, Any]] = []
        seen = set()
        for ep in endpoints:
            for seg in ep.get("path_segments", []):
                key = (
                    seg.get("from_net"),
                    seg.get("pass_component"),
                    str(seg.get("in_pin")),
                    str(seg.get("out_pin")),
                    seg.get("to_net"),
                )
                if key not in seen:
                    seen.add(key)
                    collected.append(seg)
        return collected

    @staticmethod
    def _detect_inline_relay_refs(p_eps: List[Dict[str, Any]], default_net: str) -> Set[str]:
        """識別在同一極性軌道上連接 >= 2 條不同網路的中繼晶片 RefDes (如 USB Hub KU100)"""
        by_ref: Dict[str, List[Dict[str, Any]]] = {}
        for ep in p_eps:
            ref = endpoint_ref(ep)
            if ref:
                by_ref.setdefault(ref, []).append(ep)

        non_tp_refs = {r for r, eps in by_ref.items() if not is_test_point_component(eps[0])}
        relays: Set[str] = set()
        if len(non_tp_refs) < 2:
            return relays

        for ref, eps in by_ref.items():
            nets = list(dict.fromkeys(endpoint_net(e, default_net) for e in eps))
            if len(nets) >= 2:
                relays.add(ref)
        return relays

    @staticmethod
    def _compute_net_branch_degrees(segments: List[Dict[str, Any]]) -> Dict[str, int]:
        """計算每個網路連往多少個不同的相鄰網路 (用於判斷 1-to-N 分叉源頭)"""
        neighbors_by_net: Dict[str, Set[str]] = {}
        for seg in segments:
            fn, tn = seg.get("from_net"), seg.get("to_net")
            if fn and tn:
                neighbors_by_net.setdefault(fn, set()).add(tn)
                neighbors_by_net.setdefault(tn, set()).add(fn)
        return {net: len(nbrs) for net, nbrs in neighbors_by_net.items()}

    @staticmethod
    def _merge_endpoints(p_eps: List[Dict[str, Any]], n_eps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """合併正負端點為不重複之端點清單 (保持順序)"""
        merged: List[Dict[str, Any]] = []
        seen_refs = set()
        for ep in p_eps + n_eps:
            ref = endpoint_ref(ep)
            if ref and ref not in seen_refs:
                seen_refs.add(ref)
                merged.append(ep)
        return merged

    @staticmethod
    def _extract_pass_components(
        p_eps: List[Dict[str, Any]],
        n_eps: List[Dict[str, Any]],
        p_segs: List[Dict[str, Any]],
        relay_refs: Optional[Set[str]] = None,
    ) -> List[Dict[str, Any]]:
        """提取途中所有穿透元件之物件字典 (包含中繼晶片)"""
        comps: Dict[str, Any] = {}
        for ep in p_eps + n_eps:
            for c in ep.get("pass_through_components", []):
                ref = getattr(c, "ref_des", None) or (c.get("ref_des") if isinstance(c, dict) else None)
                if ref and ref not in comps:
                    comps[ref] = c

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

        if relay_refs:
            for ep in p_eps + n_eps:
                ref = endpoint_ref(ep)
                if ref in relay_refs and ref not in comps:
                    c = ep.get("component") if "component" in ep else ep
                    comps[ref] = c

        return list(comps.values())

    @property
    def is_continuous(self) -> bool:
        """
        差分通道導通性判定 (支援並聯穿透元件與多支路匯流):
        源端已上件、至少一個已上件主要目標端點，且每個已上件目標在 P/N 兩軌皆存在「已上件元件」構成的連通路徑。
        """
        analysis = self.analyze_continuity()
        return bool(analysis["root_mounted"] and not analysis["failures"])

    @property
    def partdb_missing_mounted(self) -> List[Dict[str, Any]]:
        """回傳「已上件」且查無 PartDB 之穿透元件 (這類元件導通性未知，規則應 SKIPPED)"""
        return [m for m in self.partdb_missing if m.get("is_mounted", True)]

    def _rail_graphs(self) -> Dict[str, RailNetGraph]:
        """建構 P/N 雙軌之網路圖 (以源端→終端雙極位勢定向，含並聯元件、中繼 IC 與 PartDB 缺失虛擬段落)"""
        cached = getattr(self, "_rail_graph_cache", None)
        if cached is not None:
            return cached

        graphs: Dict[str, RailNetGraph] = {
            "p_rail": RailNetGraph(
                "p_rail",
                self.p_net_name,
                self.p_endpoints,
                self.p_segments,
                self.root_ref,
                self.partdb_missing,
                self.relay_refs,
            )
        }
        if self.n_net_name:
            graphs["n_rail"] = RailNetGraph(
                "n_rail",
                self.n_net_name,
                self.n_endpoints,
                self.n_segments,
                self.root_ref,
                self.partdb_missing,
                self.relay_refs,
            )
        self._rail_graph_cache = graphs
        return graphs

    def analyze_continuity(self) -> Dict[str, Any]:
        """
        導通性分析 (並聯或多支路元件任一完整路徑上件即導通；排除附屬單腳測試點 TP*)
        """
        mounted_by_ref: Dict[str, bool] = {}
        tp_refs: Set[str] = set()
        for ep in self.endpoints:
            ref = endpoint_ref(ep)
            c = ep.get("component") if "component" in ep else ep
            is_mounted = getattr(c, "is_mounted", True) if c else True
            if isinstance(c, dict) and "is_mounted" in c:
                is_mounted = c["is_mounted"]
            elif "is_mounted" in ep:
                is_mounted = ep["is_mounted"]
            mounted_by_ref[ref] = bool(is_mounted)
            if is_test_point_component(ep):
                tp_refs.add(ref)

        root_ref = self.root_ref or ""
        root_mounted = mounted_by_ref.get(root_ref, True)

        # 若通道存在非測試點之真實目標端點 (IC / Connector)，則排除附屬測試點 TP*
        all_target_refs = [r for r in mounted_by_ref if r != root_ref]
        non_tp_targets = [r for r in all_target_refs if r not in tp_refs]
        effective_targets = non_tp_targets if non_tp_targets else all_target_refs

        active = [r for r in effective_targets if mounted_by_ref[r]]
        inactive = [r for r in effective_targets if not mounted_by_ref[r]]

        failures: List[Dict[str, Any]] = []
        if root_mounted and active:
            for graph in self._rail_graphs().values():
                failures.extend(graph.analyze_continuity(active))

        return {
            "root_ref": root_ref,
            "root_mounted": root_mounted,
            "active_targets": active,
            "inactive_targets": inactive,
            "failures": failures,
        }

    @property
    def is_symmetric(self) -> bool:
        """判定差分正負軌道串聯被動元件是否具備電氣與封裝對稱性"""
        if self.symmetry_result:
            return bool(self.symmetry_result.get("is_symmetric", True))
        return len(self.p_segments) == len(self.n_segments)

    def to_topology(self) -> Dict[str, Any]:
        """
        建構標準 UniversalTopology 拓撲字典
        包含 P/N 雙軌、終端節點、中繼晶片、單腳測試點、途中串聯與並聯元件、扇出導線。
        """
        builder = TopologyGraphBuilder(title=self.title, channel_type="differential")
        tap_refs: Set[str] = set()
        branch_refs: Set[str] = set()
        missing_refs: Set[str] = set()
        test_point_refs: Set[str] = set()
        relay_pin_names: Dict[Tuple[str, str], str] = {}

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

            graph = self._rail_graphs()[rail_id]

            # 1. 加入端點元件 (已排除中繼 IC `graph.relay_refs`)
            for ep in graph.endpoints:
                c = ep.get("component") if "component" in ep else ep
                ref_des = endpoint_ref(ep)
                cat = getattr(c, "category", None) or (c.get("category") if isinstance(c, dict) else None) or ep.get("component_type") or "IC"
                pn = (
                    getattr(c, "pn", None)
                    or (c.get("part_value") if isinstance(c, dict) else None)
                    or (c.get("part_number") if isinstance(c, dict) else None)
                    or ep.get("part_number")
                    or ""
                )
                is_mounted = getattr(c, "is_mounted", True) if c else True
                if isinstance(c, dict) and "is_mounted" in c:
                    is_mounted = c["is_mounted"]
                elif "is_mounted" in ep:
                    is_mounted = ep["is_mounted"]
                bom = getattr(c, "bom", None) or (c.get("bom") if isinstance(c, dict) else None) or ep.get("bom")
                pin_num = str(ep.get("pin_number") or ep.get("pin") or "1")
                pin_name = str(ep.get("pin_name") or ep.get("pin") or pin_num)

                if is_test_point_component(ep):
                    test_point_refs.add(ref_des)

                builder.add_terminal(
                    id=ref_des,
                    ref_des=ref_des,
                    category=cat,
                    part_number=pn,
                    is_mounted=bool(is_mounted),
                    bom=bom,
                    pins=[{"pin_number": pin_num, "pin_name": pin_name}],
                )

            # 2. 直連通道 (無途中穿透元件且無缺失 PartDB 元件)
            if not graph.segments:
                if len(graph.endpoints) >= 2:
                    ep_map: Dict[str, List[Dict[str, Any]]] = {}
                    for ep in graph.endpoints:
                        ref = endpoint_ref(ep)
                        if ref:
                            ep_map.setdefault(ref, []).append(ep)

                    root_ref = self.root_ref if (self.root_ref and self.root_ref in ep_map) else list(ep_map.keys())[0]
                    ep_from = ep_map[root_ref][0]
                    pin_from = str(ep_from.get("pin_number") or ep_from.get("pin") or "1")

                    destination_refs = [r for r in (self.target_refs or list(ep_map.keys())) if r in ep_map and r != root_ref]
                    if not destination_refs:
                        destination_refs = [r for r in ep_map.keys() if r != root_ref]

                    for dst_ref in destination_refs:
                        for ep_to in ep_map[dst_ref]:
                            pin_to = str(ep_to.get("pin_number") or ep_to.get("pin") or "1")
                            builder.add_connection(
                                net_name=start_net,
                                rail_id=rail_id,
                                from_node=root_ref,
                                from_pin=pin_from,
                                to_node=dst_ref,
                                to_pin=pin_to,
                                is_branch=False,
                            )
                return

            # 3. 存在穿透元件或中繼晶片 -> 由網路圖建構完整節點與連線
            tap_refs.update(graph.tap_refs())
            branch_refs.update(graph.branch_refs())
            for seg in graph.segments:
                comp_ref = seg["pass_component"]
                in_p = str(seg.get("in_pin", "1"))
                out_p = str(seg.get("out_pin", "2"))
                if seg.get("in_pin_name"):
                    relay_pin_names[(comp_ref, in_p)] = str(seg["in_pin_name"])
                if seg.get("out_pin_name"):
                    relay_pin_names[(comp_ref, out_p)] = str(seg["out_pin_name"])

                builder.add_series_component(
                    id=comp_ref,
                    ref_des=comp_ref,
                    category=seg.get("pass_component_type", "Passive"),
                    in_pin=in_p,
                    out_pin=out_p,
                    is_mounted=bool(seg.get("is_mounted", True)),
                    bom=seg.get("bom"),
                    value=seg.get("part_number"),
                )
                if seg.get("partdb_missing"):
                    missing_refs.add(comp_ref)
            for conn in graph.build_connections():
                builder.add_connection(**conn)

        _populate_rail("p_rail", self.p_net_name, self.p_endpoints, self.p_segments)
        if self.n_net_name:
            _populate_rail("n_rail", self.n_net_name, self.n_endpoints, self.n_segments)

        topo = builder.to_dict()
        # 判斷是否整個通道僅由測試點組成 (如阻抗測試線 CTP20 -> CTP19)
        all_terminals = [n for n in topo.get("nodes", []) if n.get("role") == "terminal"]
        only_test_points = bool(all_terminals) and all(n.get("ref_des") in test_point_refs for n in all_terminals)

        for node in topo.get("nodes", []):
            ref = node.get("ref_des")
            # 補回中繼 IC (如 KU100) 的引腳名稱 (如 UFP_DP / DFP1_DP)
            if ref in self.relay_refs:
                for p in node.get("pins", []):
                    p_num = str(p.get("pin_number") or "")
                    if (ref, p_num) in relay_pin_names:
                        p["pin_name"] = relay_pin_names[(ref, p_num)]
            if ref in branch_refs or ref in missing_refs:
                node["lane"] = "branch"
            elif ref in tap_refs:
                node["lane"] = "tap"
            if ref in missing_refs:
                node["partdb_missing"] = True
            if ref in test_point_refs:
                node["is_test_point"] = True
                if not only_test_points:
                    node["lane"] = "tap"

        topo.setdefault("metadata", {})["partdb_missing"] = [
            {"ref_des": m["ref_des"], "mfg": m.get("mfg", ""), "pn": m.get("pn", ""), "is_mounted": m.get("is_mounted", True)}
            for m in self.partdb_missing
        ]
        return topo


class SingleEndedChannel(BaseChannel):
    """
    單端訊號與匯流排通道高階模型 (Single-Ended & Bus Channel Model)
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

        for ep in self.endpoints:
            c = ep.get("component") if "component" in ep else ep
            ref = endpoint_ref(ep)
            cat = getattr(c, "category", None) or (c.get("category") if isinstance(c, dict) else None) or "IC"
            pn = getattr(c, "pn", None) or (c.get("part_value") if isinstance(c, dict) else None) or ""
            is_mounted = getattr(c, "is_mounted", True) if c else True
            if isinstance(c, dict) and "is_mounted" in c:
                is_mounted = c["is_mounted"]
            bom = getattr(c, "bom", None) or (c.get("bom") if isinstance(c, dict) else None)
            pin_num = str(ep.get("pin_number") or ep.get("pin") or "1")
            pin_name = str(ep.get("pin_name") or ep.get("pin") or pin_num)

            builder.add_terminal(
                id=ref,
                ref_des=ref,
                category=cat,
                part_number=pn,
                is_mounted=bool(is_mounted),
                bom=bom,
                pins=[{"pin_number": pin_num, "pin_name": pin_name}],
            )

        if len(self.endpoints) >= 2 and not self.pass_components:
            root_ref = self.root_ref or endpoint_ref(self.endpoints[0])
            root_ep = next((ep for ep in self.endpoints if endpoint_ref(ep) == root_ref), self.endpoints[0])
            pin_from = str(root_ep.get("pin_number") or root_ep.get("pin") or "1")

            for ep in self.endpoints:
                dst_ref = endpoint_ref(ep)
                if dst_ref and dst_ref != root_ref:
                    pin_to = str(ep.get("pin_number") or ep.get("pin") or "1")
                    builder.add_connection(
                        net_name=self.name,
                        rail_id="main",
                        from_node=root_ref,
                        from_pin=pin_from,
                        to_node=dst_ref,
                        to_pin=pin_to,
                        is_branch=False,
                    )

        for pc in self.pass_components:
            ref = getattr(pc, "ref_des", None) or pc.get("ref_des")
            builder.add_series_component(
                id=ref,
                ref_des=ref,
                category=getattr(pc, "category", "Passive") or "Passive",
                is_mounted=getattr(pc, "is_mounted", True),
                bom=getattr(pc, "bom", None),
            )

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
