"""
================================================================================
DesignShield SDK 通道「網路圖」模型 (Channel Net-Graph Model)
================================================================================

職責:
1. 將單一極性軌道 (P 或 N) 的穿透元件段落建模為「網路為節點、穿透元件為邊」的網路圖，
   支援同階並聯元件 (如 0Ω 跳線 ∥ 共模扼流圈)、多段分叉匯流支路 (如 USB Hub ∥ Bypass 電阻鏈)、
   中途 tap 端點與單腳測試點 (TP*)。
2. 以「源端 (Source) → 終端 (Sink) 雙極拓撲位勢 (Bipolar Topological Potential)」重新定向所有段落，
   確保不論支路跳數長短，訊號流向恆為 Source → Sink 且無假死胡同 (Sink Hole)。
3. 依「已上件元件」子圖進行導通性分析 (並聯或多支路任一完整上件路徑導通即 PASS)，並指出斷路躍點。
4. 產出完整拓撲連線 (主幹 / 並聯分支 / 匯流支路 / 終端與測點)，供 TopologyGraphBuilder 建構 UniversalTopology。
================================================================================
"""

import re
from collections import deque
from typing import Any, Dict, List, Optional, Set, Tuple


def endpoint_ref(ep: Dict[str, Any]) -> str:
    """
    取得端點追蹤字典之元件 RefDes

    @param {Dict[str, Any]} ep - 端點追蹤審計字典
    @returns {str} 元件 RefDes，無法解析時回傳空字串
    """
    c = ep.get("component") if "component" in ep else ep
    ref = getattr(c, "ref_des", None) or (c.get("ref_des") if isinstance(c, dict) else None) or ep.get("ref_des")
    return str(ref or "")


def endpoint_net(ep: Dict[str, Any], default: str = "") -> str:
    """
    取得端點所連接之網路名稱

    @param {Dict[str, Any]} ep - 端點追蹤審計字典
    @param {str} default - 查無時之預設網路名稱
    @returns {str} 網路名稱
    """
    if ep.get("connected_net"):
        return str(ep["connected_net"])
    tn = ep.get("terminal_net")
    if tn is not None:
        name = getattr(tn, "net_name", None) or (tn.get("net_name") if isinstance(tn, dict) else None)
        if name:
            return str(name)
    return default


def is_test_point_component(comp_or_ep: Any) -> bool:
    """
    判定元件或端點是否為測試點 (TestPoint)

    嚴格採用 Level 1 零件分類所取得之 sub_category 判定 (sub_category == 'TestPoint')。

    @param {Any} comp_or_ep - 元件節點、字典或端點追蹤物件
    @returns {bool} 若為測試點則回傳 True
    """
    if not comp_or_ep:
        return False
    c = comp_or_ep.get("component") if isinstance(comp_or_ep, dict) and "component" in comp_or_ep else comp_or_ep
    sub = ""
    if isinstance(c, dict):
        sub = c.get("sub_category") or c.get("sub") or c.get("category") or ""
    else:
        sub = getattr(c, "sub_category", None) or getattr(c, "category", None) or ""
    if not sub and isinstance(comp_or_ep, dict):
        sub = comp_or_ep.get("sub_category") or comp_or_ep.get("sub") or comp_or_ep.get("category") or ""

    sub_norm = str(sub).strip().lower().replace("_", "")
    return sub_norm == "testpoint"


class RailNetGraph:
    """
    單一極性軌道之網路圖 (Net Graph of One Rail)

    Attributes:
        rail_id: 軌道 ID (p_rail / n_rail)
        start_net: 追蹤起點網路名稱 (找不到源端時的後備起點)
        root_ref: 源端元件 RefDes
        endpoints: 該軌道所有端點追蹤字典 (已將跨網中繼 IC 轉為穿透段落)
        segments: 以源端→終端雙極位勢重新定向後的穿透段落 (含中繼 IC 與 partdb_missing 虛擬段落)
        depth: 網路名稱 -> 距源端的躍點深度
        potential: 網路名稱 -> 雙極拓撲位勢 (用於精確定向多跳匯流支路)
        root_nets: 源端所在網路集合
        sink_nets: 目標終端所在網路集合
        endpoints_by_net: 網路名稱 -> 該網路上的端點清單
    """

    def __init__(
        self,
        rail_id: str,
        start_net: str,
        endpoints: List[Dict[str, Any]],
        segments: List[Dict[str, Any]],
        root_ref: Optional[str],
        partdb_missing: Optional[List[Dict[str, Any]]] = None,
        relay_refs: Optional[Set[str]] = None,
    ):
        self.rail_id = rail_id
        self.start_net = start_net
        self.root_ref = root_ref or ""
        self.relay_refs: Set[str] = set(relay_refs or set())

        # 1. 將跨接於本軌道兩條不同網路之間的中繼 IC (如 USB Hub KU100) 抽離為穿透段落
        filtered_eps, relay_segs = self._extract_inline_relay_segments(endpoints, start_net)
        self.endpoints = filtered_eps
        self.endpoints_by_net: Dict[str, List[Dict[str, Any]]] = {}
        for ep in self.endpoints:
            self.endpoints_by_net.setdefault(endpoint_net(ep, start_net), []).append(ep)

        raw_segments = self._dedup_segments(list(segments) + relay_segs)

        self.root_nets: List[str] = [
            net for net, eps in self.endpoints_by_net.items()
            if any(endpoint_ref(ep) == self.root_ref for ep in eps)
        ] or ([start_net] if start_net else [])

        # 目標終端網路 (非源端、非單腳測試點之真實終端所在網路)
        self.sink_nets: List[str] = [
            net for net, eps in self.endpoints_by_net.items()
            if net not in self.root_nets
            and any(
                endpoint_ref(ep) != self.root_ref and not is_test_point_component(ep)
                for ep in eps
            )
        ]

        self.depth, self.potential = self._compute_depth_and_potential(raw_segments)
        self.segments: List[Dict[str, Any]] = self._orient(raw_segments)
        self.segments.extend(self._build_missing_segments(partdb_missing or []))

    # ------------------------------------------------------------------ 建構
    def _extract_inline_relay_segments(
        self,
        endpoints: List[Dict[str, Any]],
        default_net: str,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        識別在同一極性軌道上連接 2 條不同網路的中繼晶片 (如 USB Hub KU100)，
        將其轉為穿透段落 (保留引腳名稱與編號)，避免其被誤判為終端端點。
        """
        by_ref: Dict[str, List[Dict[str, Any]]] = {}
        for ep in endpoints:
            ref = endpoint_ref(ep)
            if ref:
                by_ref.setdefault(ref, []).append(ep)

        # 若通道除了該元件外還有其他真實端點，且該元件在本軌道連接 >= 2 條不同網路 -> 視為中繼元件
        non_tp_refs = {r for r, eps in by_ref.items() if not is_test_point_component(eps[0])}
        kept_endpoints: List[Dict[str, Any]] = []
        relay_segments: List[Dict[str, Any]] = []

        for ep in endpoints:
            ref = endpoint_ref(ep)
            eps_for_ref = by_ref.get(ref, [])
            distinct_nets = list(dict.fromkeys(endpoint_net(e, default_net) for e in eps_for_ref))
            is_relay = (
                ref in self.relay_refs
                or (len(distinct_nets) >= 2 and len(non_tp_refs) >= 2 and ref != self.root_ref)
            )
            if not is_relay:
                kept_endpoints.append(ep)

        processed_relays: Set[str] = set()
        for ref, eps_for_ref in by_ref.items():
            distinct_nets = list(dict.fromkeys(endpoint_net(e, default_net) for e in eps_for_ref))
            is_relay = (
                ref in self.relay_refs
                or (len(distinct_nets) >= 2 and len(non_tp_refs) >= 2 and ref != self.root_ref)
            )
            if not is_relay or ref in processed_relays or len(distinct_nets) < 2:
                continue
            processed_relays.add(ref)
            self.relay_refs.add(ref)

            # 取第一條網路與第二條網路的端點紀錄建立穿透邊
            ep_a = next(e for e in eps_for_ref if endpoint_net(e, default_net) == distinct_nets[0])
            ep_b = next(e for e in eps_for_ref if endpoint_net(e, default_net) == distinct_nets[1])
            c = ep_a.get("component") if "component" in ep_a else ep_a
            cat = getattr(c, "category", None) or (c.get("category") if isinstance(c, dict) else None) or ep_a.get("component_type") or "IC"
            pn = getattr(c, "pn", None) or (c.get("part_number") if isinstance(c, dict) else None) or ep_a.get("part_number") or ""
            is_mounted = getattr(c, "is_mounted", True) if c else True
            if isinstance(c, dict) and "is_mounted" in c:
                is_mounted = bool(c["is_mounted"])
            elif "is_mounted" in ep_a:
                is_mounted = bool(ep_a["is_mounted"])
            bom = getattr(c, "bom", None) or (c.get("bom") if isinstance(c, dict) else None) or ep_a.get("bom")

            pin_a = str(ep_a.get("pin_number") or ep_a.get("pin") or "1")
            pin_a_name = str(ep_a.get("pin_name") or ep_a.get("pin") or pin_a)
            pin_b = str(ep_b.get("pin_number") or ep_b.get("pin") or "2")
            pin_b_name = str(ep_b.get("pin_name") or ep_b.get("pin") or pin_b)

            relay_segments.append({
                "from_net": distinct_nets[0],
                "to_net": distinct_nets[1],
                "pass_component": ref,
                "pass_component_type": str(cat or "IC"),
                "part_number": str(pn or ""),
                "in_pin": pin_a,
                "in_pin_name": pin_a_name,
                "out_pin": pin_b,
                "out_pin_name": pin_b_name,
                "is_mounted": bool(is_mounted),
                "bom": bom,
                "is_relay_ic": True,
            })

        return kept_endpoints, relay_segments

    @staticmethod
    def _dedup_segments(segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """去除重複段落 (依 元件 + 無向引腳對)，保留首見順序"""
        seen: Set[Tuple[str, Tuple[str, str]]] = set()
        unique: List[Dict[str, Any]] = []
        for seg in segments:
            comp = str(seg.get("pass_component"))
            p1, p2 = str(seg.get("in_pin")), str(seg.get("out_pin"))
            pin_pair = (p1, p2) if p1 <= p2 else (p2, p1)
            key = (comp, pin_pair)
            if key in seen:
                continue
            seen.add(key)
            unique.append(dict(seg))
        return unique

    def _compute_depth_and_potential(
        self,
        segments: List[Dict[str, Any]],
    ) -> Tuple[Dict[str, int], Dict[str, Tuple[int, int]]]:
        """
        計算每個網路距源端的深度 (dist_src) 與諧波電位拓撲位勢 (potential)

        以基爾霍夫電位定律 (Harmonic Electrical Potential) 計算各網路位勢:
          - 源端網路 (root_nets) 固定為 V = 0.0
          - 目標端點網路 (sink_nets) 透過單位電導連接至虛擬終端 V = 1.0
          - 其餘內部網路滿足諧波平均 V(u) = avg(V(neighbors))
        由諧波函數極值原理，無論平行匯流支路跳數差異多大 (如 1 跳 Bypass 電阻 vs 3 跳 USB Hub)，
        沿任意無迴路支路自源端流向匯合點與終端時，電位 V(n) 嚴格單調遞增；
        對懸空無終端支路則由次鍵 dist_src[n] 嚴格單調遞增。
        """
        adj: Dict[str, Set[str]] = {}
        for seg in segments:
            f, t = seg.get("from_net"), seg.get("to_net")
            if not f or not t or f == t:
                continue
            adj.setdefault(f, set()).add(t)
            adj.setdefault(t, set()).add(f)

        def _bfs(starts: List[str]) -> Dict[str, int]:
            dist: Dict[str, int] = {}
            q: deque = deque()
            for s in starts:
                if s not in dist:
                    dist[s] = 0
                    q.append(s)
            while q:
                cur = q.popleft()
                for nxt in sorted(adj.get(cur, ())):
                    if nxt not in dist:
                        dist[nxt] = dist[cur] + 1
                        q.append(nxt)
            return dist

        dist_src = _bfs(self.root_nets)
        for rn in self.root_nets:
            dist_src.setdefault(rn, 0)

        root_set = set(self.root_nets)
        sink_set = set(self.sink_nets)
        reachable_nets = sorted(dist_src.keys())

        voltage: Dict[str, float] = {
            n: (0.0 if n in root_set else 0.5) for n in reachable_nets
        }
        if sink_set:
            for _ in range(120):
                max_delta = 0.0
                for n in reachable_nets:
                    if n in root_set:
                        voltage[n] = 0.0
                        continue
                    nbrs = [nb for nb in adj.get(n, ()) if nb in voltage]
                    sink_pull = 1 if n in sink_set else 0
                    denom = len(nbrs) + sink_pull
                    if denom == 0:
                        continue
                    new_v = (sum(voltage[nb] for nb in nbrs) + (1.0 if sink_pull else 0.0)) / denom
                    delta = abs(new_v - voltage[n])
                    if delta > max_delta:
                        max_delta = delta
                    voltage[n] = new_v
                if max_delta < 1e-9:
                    break

        potential: Dict[str, Tuple[int, int]] = {}
        for net, ds in dist_src.items():
            if sink_set:
                potential[net] = (int(round(voltage.get(net, 0.0) * 1_000_000)), ds)
            else:
                potential[net] = (ds, ds)

        return dist_src, potential

    def _orient(self, segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """依雙極拓撲位勢重新定向段落 (potential 較小流向較大)；與源端不連通之孤立段落予以捨棄"""
        oriented: List[Dict[str, Any]] = []
        for seg in segments:
            fn, tn = seg.get("from_net"), seg.get("to_net")
            pf = self.potential.get(fn)
            pt = self.potential.get(tn)
            if pf is None and pt is None:
                continue
            new_seg = dict(seg)
            if (pf is None) or (pt is not None and pf > pt):
                new_seg["from_net"], new_seg["to_net"] = tn, fn
                new_seg["in_pin"], new_seg["out_pin"] = seg.get("out_pin"), seg.get("in_pin")
                if "in_pin_name" in seg or "out_pin_name" in seg:
                    new_seg["in_pin_name"], new_seg["out_pin_name"] = seg.get("out_pin_name"), seg.get("in_pin_name")
            oriented.append(new_seg)
        return oriented

    def _build_missing_segments(self, partdb_missing: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        為 PartDB 缺失之 4-pin 元件建立「僅供顯示」的虛擬段落

        依元件各引腳所接網路在本軌道的雙極位勢，取位勢最小引腳為入腳、最大引腳為出腳；
        此為純顯示用途 (partdb_missing=True)，不參與導通性判定，亦不代表引腳穿透配對。
        """
        result: List[Dict[str, Any]] = []
        for entry in partdb_missing:
            pins_on_rail = [
                (self.potential[net], pin, net)
                for pin, net in (entry.get("pin_nets") or {}).items()
                if net in self.potential
            ]
            if len(pins_on_rail) < 2:
                continue
            pins_on_rail.sort(key=lambda x: (x[0], x[1]))
            p_in, pin_in, net_in = pins_on_rail[0]
            p_out, pin_out, net_out = pins_on_rail[-1]
            if net_in == net_out:
                continue
            result.append({
                "from_net": net_in,
                "to_net": net_out,
                "pass_component": entry["ref_des"],
                "pass_component_type": "Common_Mode_Choke",
                "in_pin": pin_in,
                "out_pin": pin_out,
                "is_mounted": bool(entry.get("is_mounted", True)),
                "bom": entry.get("bom"),
                "partdb_missing": True,
            })
        return result

    # ------------------------------------------------------------------ 查詢
    def real_segments(self) -> List[Dict[str, Any]]:
        """回傳不含 PartDB 缺失虛擬段落之真實穿透段落"""
        return [s for s in self.segments if not s.get("partdb_missing")]

    def hop_groups(self) -> Dict[Tuple[str, str], List[Dict[str, Any]]]:
        """依 (from_net, to_net) 躍點分組之並聯穿透元件群 (保持首見順序)"""
        groups: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
        for seg in self.segments:
            groups.setdefault((seg["from_net"], seg["to_net"]), []).append(seg)
        return groups

    @staticmethod
    def pick_main(group: List[Dict[str, Any]]) -> Dict[str, Any]:
        """挑選並聯群主幹元件 (優先: 已上件且非缺 PartDB > 非缺 PartDB > 第一顆)"""
        for seg in group:
            if seg.get("is_mounted", True) and not seg.get("partdb_missing"):
                return seg
        for seg in group:
            if not seg.get("partdb_missing"):
                return seg
        return group[0]

    def tap_refs(self) -> Set[str]:
        """回傳掛在「仍有後續穿透元件」網路上的中途 tap 端點 RefDes 集合"""
        nets_with_consumers = {s["from_net"] for s in self.segments}
        refs: Set[str] = set()
        for net, eps in self.endpoints_by_net.items():
            if net in nets_with_consumers and net not in self.root_nets:
                refs.update(endpoint_ref(ep) for ep in eps if endpoint_ref(ep) != self.root_ref)
        return refs

    def branch_refs(self) -> Set[str]:
        """回傳在任一躍點中屬於「並聯分支」(非主幹) 的穿透元件 RefDes 集合"""
        refs: Set[str] = set()
        for group in self.hop_groups().values():
            main = self.pick_main(group)
            refs.update(s["pass_component"] for s in group if s is not main)
        return refs

    # ------------------------------------------------------------------ 拓撲連線
    def build_connections(self) -> List[Dict[str, Any]]:
        """
        產出本軌道完整拓撲連線 (主幹 / 並聯分支 / 匯流支路 / 終端與測點)

        規則 (以每個網路為單位):
          - 來源 (sources): 源端網路為「源端各引腳」，其餘網路為「流入該網路之穿透元件」。
          - 去向 (sinks): 由該網路流出之穿透元件 (consumers) + 掛在該網路上的非源端端點 (taps / 終端)。
          - 主幹來源 → 連至所有 consumers 與所有 taps；
          - 並聯分支來源 (not src_main):
            * 若該網路有 consumers，連至主幹 consumer (is_branch=True)；
            * 若該網路無 consumers (即直接連至終端如 J81)，則連至該網路之終端 tap (is_branch=True)，
              確保並聯 CMC (如 UL810/UL800) 右側輸出引腳完整連入終端網路，絕不斷線！

        Returns:
            List[Dict[str, Any]]: add_connection 參數字典清單
        """
        groups = self.hop_groups()
        main_of: Dict[Tuple[str, str], Dict[str, Any]] = {k: self.pick_main(v) for k, v in groups.items()}

        def is_main(seg: Dict[str, Any]) -> bool:
            return main_of[(seg["from_net"], seg["to_net"])] is seg

        conns: List[Dict[str, Any]] = []
        nets = sorted(self.potential.keys(), key=lambda n: (self.potential[n], n))
        for net in nets:
            drivers = [s for s in self.segments if s["to_net"] == net]
            consumers = [s for s in self.segments if s["from_net"] == net]
            taps = [ep for ep in self.endpoints_by_net.get(net, []) if endpoint_ref(ep) != self.root_ref]

            # 來源清單: (node_ref, out_pin, is_main_source)
            sources: List[Tuple[str, str, bool]] = []
            if net in self.root_nets:
                for ep in self.endpoints_by_net.get(net, []):
                    if endpoint_ref(ep) == self.root_ref:
                        sources.append((self.root_ref, str(ep.get("pin_number") or ep.get("pin") or "1"), True))
            has_root_source = bool(sources)
            if drivers:
                # 若有多條支路匯入同一網路 (如 Bypass KR135 與 Hub KR129 匯入 FUSBA1_USB20_P)，
                # 挑選最具代表性之已上件主幹 driver 為 primary_driver，其餘支路僅匯入主幹去向，避免產生重複交叉線
                main_drivers = [d for d in drivers if is_main(d)]
                primary_driver = self.pick_main(main_drivers) if main_drivers else self.pick_main(drivers)
                for d in drivers:
                    is_primary = (d is primary_driver) and not has_root_source
                    sources.append((d["pass_component"], str(d.get("out_pin") or "2"), is_primary))

            for src_ref, src_pin, src_main in sources:
                for c in consumers:
                    c_main = is_main(c)
                    if not src_main and not c_main:
                        continue
                    conns.append({
                        "net_name": net,
                        "rail_id": self.rail_id,
                        "from_node": src_ref,
                        "from_pin": src_pin,
                        "to_node": c["pass_component"],
                        "to_pin": str(c.get("in_pin") or "1"),
                        "is_branch": (not src_main) or (not c_main),
                    })
                if src_main:
                    for ep in taps:
                        conns.append({
                            "net_name": net,
                            "rail_id": self.rail_id,
                            "from_node": src_ref,
                            "from_pin": src_pin,
                            "to_node": endpoint_ref(ep),
                            "to_pin": str(ep.get("pin_number") or ep.get("pin") or "1"),
                            "is_branch": False,
                        })
                elif not consumers and taps:
                    # 並聯分支 (如 UL810/UL800) 直接匯入終端網路 (後方無其他串聯元件)：
                    # 連接至該網路的主目標端點引腳，確保右側引腳完整接線不懸空
                    non_tp_taps = [ep for ep in taps if not is_test_point_component(ep)]
                    target_ep = non_tp_taps[0] if non_tp_taps else taps[0]
                    conns.append({
                        "net_name": net,
                        "rail_id": self.rail_id,
                        "from_node": src_ref,
                        "from_pin": src_pin,
                        "to_node": endpoint_ref(target_ep),
                        "to_pin": str(target_ep.get("pin_number") or target_ep.get("pin") or "1"),
                        "is_branch": True,
                    })
        return conns

    # ------------------------------------------------------------------ 導通性
    def analyze_continuity(self, target_refs: List[str]) -> List[Dict[str, Any]]:
        """
        以「已上件元件」子圖分析源端到各目標端點之導通性 (並聯或多支路任一上件路徑導通即 PASS)

        @param {List[str]} target_refs - 需檢查之已上件目標端點 RefDes
        @returns {List[Dict[str, Any]]} 斷路清單，每筆含:
            rail_id、target_ref、from_net、to_net、candidates (該躍點全部並聯候選元件 RefDes)
        """
        parent: Dict[str, str] = {}

        def find(x: str) -> str:
            parent.setdefault(x, x)
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a: str, b: str) -> None:
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb

        real = self.real_segments()
        for seg in real:
            if seg.get("is_mounted", True):
                union(seg["from_net"], seg["to_net"])

        root_clusters = {find(n) for n in self.root_nets}
        adj_all: Dict[str, List[Dict[str, Any]]] = {}
        for seg in real:
            adj_all.setdefault(seg["from_net"], []).append(seg)

        groups = self.hop_groups()
        failures: List[Dict[str, Any]] = []
        for target_ref in target_refs:
            target_nets = [
                net for net, eps in self.endpoints_by_net.items()
                if any(endpoint_ref(ep) == target_ref for ep in eps)
            ]
            if not target_nets or any(find(tn) in root_clusters for tn in target_nets):
                continue

            broken_hop = self._find_first_broken_hop(target_nets[0], adj_all, find)
            if broken_hop is None:
                cands = [s["pass_component"] for s in self.segments if not s.get("is_mounted", True)]
                fn, tn = (self.root_nets[0] if self.root_nets else self.start_net), target_nets[0]
            else:
                fn, tn = broken_hop
                cands = [s["pass_component"] for s in groups.get((fn, tn), [])]

            failures.append({
                "rail_id": self.rail_id,
                "target_ref": target_ref,
                "from_net": fn,
                "to_net": tn,
                "candidates": list(dict.fromkeys(cands)),
            })
        return failures

    def _find_first_broken_hop(
        self,
        target_net: str,
        adj_all: Dict[str, List[Dict[str, Any]]],
        find_fn,
    ) -> Optional[Tuple[str, str]]:
        """在完整網路圖上由源端 BFS 至 target_net，回傳路徑上第一個未導通的 (from_net, to_net) 躍點"""
        prev: Dict[str, Tuple[str, Dict[str, Any]]] = {}
        visited: Set[str] = set(self.root_nets)
        queue: deque = deque(self.root_nets)
        while queue:
            cur = queue.popleft()
            if cur == target_net:
                break
            for seg in adj_all.get(cur, ()):
                nxt = seg["to_net"]
                if nxt not in visited:
                    visited.add(nxt)
                    prev[nxt] = (cur, seg)
                    queue.append(nxt)

        if target_net not in prev:
            return None

        path: List[Tuple[str, str]] = []
        node = target_net
        while node in prev:
            p_net, _ = prev[node]
            path.append((p_net, node))
            node = p_net
        path.reverse()

        for fn, tn in path:
            if find_fn(fn) != find_fn(tn):
                return (fn, tn)
        return path[0] if path else None
