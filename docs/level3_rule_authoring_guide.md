# DesignShield Level 3 DRC 規則與伴生腳本撰寫指南 (Level 3 DRC Authoring Guide)

## 1. 核心架構與設計哲學 (Core Principles)

DesignShield 的 Level 3 DRC（設計規則檢查）負責執行硬體線路的合規審查。在面對多 BOM 配置（BOM Options）與樣品/量產（Proto / MP）階段切換時，系統確立了以下最高原則：

### 1.1 雙軌解耦哲學：電氣拓撲 vs 零件裝配狀態
過去傳統的做法若在解析電路時直接將「不上件（NI/X）」的零件從圖譜中刪除，將導致嚴重的**審計盲區**（例如：原本為未上件保護晶片或佔位晶片 TU2，若走線正負極反接，會因元件被刪除而無法檢測；或是無法確認是否留有下拉電阻佔位）。

因此，DesignShield 採用**電氣拓撲（Physical Routing Netlist）與零件裝配狀態（Mounted State）雙軌解耦**：
1. **圖譜層永不破壞性刪點**：無論零件在當前 BOM Config 下是否上件，電氣原理圖圖譜永遠 100% 完整保留所有元件節點（Component Nodes）、接腳與網路走線邊（Edges）。
2. **裝配狀態下放至屬性與 SDK 介面**：子圖引擎（`create_config_subgraph`）會依據當前選取的 BOM Config 及 MP 模式，將零件的上件狀態精簡為核心屬性注入節點：
   - `comp.is_mounted: bool`（True 代表上件，False 代表不上件，提供極速布林判斷）
   - `comp.bom: str`（當前 Config 之正規化 BOM 縮寫代碼：`"I"`, `"X"`, `"P"`, `"M"`, `"NOBOM"`）
   - `comp.display_ref_des: str`（未上件依據 bom 代碼動態標記為 `[X]`, `[P]`, `[M]`，例如 `TU2 [X]`、`TU2 [P]`）
3. **規則自主裁量多重視角**：規則作者與 AI 伴生腳本可依據領域需求，自主決定以何種視角進行審查。

---

### 1.2 三種經典審查視角與業務場景

```
                  ┌────────────────────────────────────────┐
                  │ DesignShield Level 3 規則審查視角      │
                  └──────────────────┬─────────────────────┘
                                     │
      ┌──────────────────────────────┼──────────────────────────────┐
      ▼                              ▼                              ▼
【物理走線視角】               【電氣導通視角】               【預留/佔位視角】
 (Physical Routing)             (Electrical Continuity)        (Placeholder & Support)
 • 不論是否上件                 • 兩端端點皆上件時             • 檢查元件實體是否存在
 • 檢查差分極性反接             • 中間串聯元件必須全數上件     • 即使不上件亦判定合規
 • 反接一律 CRITICAL/ERROR      • 中間若有未上件報 ERROR       • 例如: 預留下拉/阻抗預留
 • 範例: TU2 未上件但反接       • 範例: AC Cap / CMC 缺失      • 範例: DFP/UFP Pull-down
```

1. **物理走線視角 (Physical Routing Perspective)**
   - **典型代表**：`pn_swap_check`（差分對極性反接檢查）。
   - **邏輯準則**：只要物理走線發生差分正負反接（例如 P 網路連至晶片的負極引腳 D1M/DN，或負極網路連至正極引腳 D1P/DP），**不論該元件當前是否有上件（包括標記為 NI 的 TU2）**，都屬於嚴重的 PCB 布線錯誤，必須一律判定為 **`CRITICAL / ERROR`**。
   - **UI 呈現**：在違規報告與證據鏈路中，將未上件元件標記為 `[X]`，並在錯誤訊息中明確告知：「此元件在當前 Config 下標註為未上件 [X]，但走線反接仍屬嚴重線路錯誤」。

2. **電氣導通視角 (Electrical Continuity Perspective)**
   - **典型代表**：`differential_channel_continuity_check`（差分通道導通與串聯元件完整性檢查）。
   - **邏輯準則**：
     - 若高速差分通道兩端端點（如 CPU Socket 與記憶體 DIMM 插槽、或主控 IC 與 Type-C 接頭）皆同時上件，則中間所有串聯穿透被動元件（AC 耦合電容、串聯電阻、共模扼流圈 CMC）必須全數存在且確實上件（`is_mounted == True`）。
     - 若中間任何串聯元件未上件，將導致訊號開路中斷，判定為 **`CRITICAL / ERROR`**。
     - 若通道兩端端點有任一端未上件（如選配插槽未插上），表示該通道在當前配置下未啟用，安全通過（`RulePass`）。

3. **預留/佔位符視角 (Placeholder & Support Perspective)**
   - **典型代表**：`pulldown_placeholder_check`（下拉電阻預留檢查）。
   - **邏輯準則**：部分硬體規範要求特定引腳必須預留下拉或上拉電阻焊盤（Footprint/Placeholder），以便後續調試或相容不同版本。此時只需確認電阻在電氣網絡上是否存在（`graph_api.has_placeholder`），即使零件標註為 `NI`（未上件），亦屬合規。

---

## 2. SDK 核心通道模型與 API 參考 (SDK Reference)

DesignShield SDK 已全面下沉高階通道抽象與拓撲生成能力，伴生腳本**不再需要手寫底層 BFS 遍歷或手動組裝拓撲連線**。

### 2.1 高階差分通道模型：`DifferentialChannel`
透過 `channel = graph_api.get_differential_channel(context.target)` 取得：

| 屬性 / 方法 | 型別 | 說明與範例 |
| :--- | :--- | :--- |
| `channel.title` | `str` | 通道完整路徑標題，含直連 1 對多扇出展開（如 `"XU1 -> XMM1, XMM2 (M_B_DDR1_DQS0 差分通道)"`） |
| `channel.p_net_name` / `n_net_name` | `str` | 規範化正極與負極主網段名稱（自動處理中繼網段起點正規化） |
| `channel.root_ref` | `str` | 源端元件 RefDes（依主控晶片/外部插座自動選定，如 `"XU1"`） |
| `channel.target_refs` | `List[str]` | 目標接收端 RefDes 清單（如 `['XMM1', 'XMM2']`） |
| `channel.endpoint_refs` | `List[str]` | 通道所有實體端點元件 RefDes（如 `['XU1', 'XMM1', 'XMM2']`） |
| `channel.pass_component_refs` | `List[str]` | 通道途中所有串聯穿透元件 RefDes（如 `['TL1', 'C1']`） |
| `channel.all_component_refs` | `List[str]` | 所有端點與穿透元件之聯集清單 |
| `channel.covered_nets` | `List[str]` | 該通道覆蓋的所有子網段名稱清單（供引擎跨網段去重） |
| `channel.is_continuous` | `bool` | **通道電氣導通狀態**（端點皆上件且無任何串聯元件未上件時為 True） |
| `channel.endpoints_mounted` | `bool` | 兩端端點是否皆已上件（是否處於啟用裝配狀態） |
| `channel.unmounted_pass_components` | `List` | 未上件之串聯穿透元件清單（造成開路中斷的元件） |
| `channel.unmounted_endpoints` | `List` | 未上件之端點元件清單 |
| `channel.to_topology()` | `Dict[str, Any]` | **一鍵輸出符合 UniversalTopologyData 規格的標準拓撲字典** |

---

### 2.2 高階單端通道模型：`SingleEndedChannel`
透過 `channel = graph_api.get_single_ended_channel(context.target)` 取得：
* `channel.pull_ups`：連接至合法電源軌之上拉電阻節點清單。
* `channel.pull_downs`：連接至基準接地之地線下拉電阻節點清單。
* `channel.shunts`：對地分流濾波元件（如去耦電容、TVS）。
* `channel.has_pullup` / `channel.has_pulldown` / `channel.has_shunt_cap`：極速布林判定。
* `channel.to_topology()`：輸出主訊號軌道與垂直分支（上拉至 VCC、下拉接地、接地分流）的拓撲。

---

### 2.3 差分極性與夥伴推導 API (`designshield.sdk.diff_pair`)

在撰寫特定高速差分檢查規則（如差分走線反接檢查 `pn_swap_check` 或極性配對規則）時：

```python
from designshield.sdk import (
    determine_diff_polarity,
    resolve_diff_pair_partner,
    resolve_diff_pair_candidates,
)
```

| 函式 | 說明與範例 |
| :--- | :--- |
| `determine_diff_polarity(name)` | 判定引腳或網路之差分極性（回傳 `"P"`, `"N"`, 或 `None`）。支援後綴（`_P/_N`, `+ / -`, `_DP/_DN`）、中綴（`_P_/_N_`, `_TXP_/_TXN_`）與前綴（`P_.../N_...`）。 |
| `resolve_diff_pair_partner(name, target_pol=None)` | 一對一推導差分夥伴名稱。若給定正極名稱，自動推導對應之負極名稱；給定負極名稱，自動推導正極名稱。支援自動大小寫適應。 |
| `resolve_diff_pair_candidates(name, target_pol=None)` | 回傳所有潛在可能的夥伴候選名稱清單（已排序），適用於在圖譜中嘗試多重搜尋對端網路。 |

> [!IMPORTANT]
> **AI 規則撰寫最佳實踐 (Rule Authoring Best Practice)**：
> 嚴禁在伴生腳本內手寫 `re.sub(r'_P$', '_N', ...)` 或自行判斷 `if '_P' in name:`！
> 差分命名邏輯一律呼叫 `resolve_diff_pair_partner()` 或依賴 `graph_api.get_differential_channel()`。這樣在硬體命名規格變更或新增 `_TXP/_TXN` 等變形時，全系統規則腳本能享有自動零修改升級能力。

> [!TIP]
> **宣告式擴充：`pair_derivation` 與 `partner_swap_rules` 的關係**：
> 當需要擴充新的差分命名變形時：
> - **`pair_derivation`** 是 Level 2 拓撲 YAML（如 `patterns/level2_topology/signals/600_differential_pair.yaml`）中的頂層功能配置區塊。
> - **`partner_swap_rules`** 則是其內部的正負互換映射矩陣（例如 `[["_TXP", "_TXN"], ["_P$", "_N$"]]`）。
> 開發者或領域專家若要新增命名規則，只需在 YAML 的 `partner_swap_rules` 列表中追加一行二元子字串映射，底層拓撲引擎與 SDK 自動即時生效，不需修改任何 Python 程式碼。詳細維護規範請參閱 [`designshield/sdk/MAINTENANCE.md`](file:///home/gaven/DesignShield/designshield/sdk/MAINTENANCE.md)。

---

## 3. Level 3 伴生腳本五階段標準架構 (5-Stage Pipeline)

所有伴生腳本必須遵循五階段標準流水線架構，確保程式碼具備高維護性與一致的證據鏈：

```python
"""
Level 3 伴生腳本五階段標準範本 (以差分通道導通為例)
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
    
    # --------------------------------------------------------------------------
    # Stage 1: 目標解析與高階通道模型載入 (Target Resolution & Channel Loading)
    # --------------------------------------------------------------------------
    channel: DifferentialChannel = graph_api.get_differential_channel(context.target)
    if not channel:
        return RuleResult.SKIPPED

    # --------------------------------------------------------------------------
    # Stage 2: 拓撲契約與去重網段讀取 (Topology & Deduplication Nets)
    # --------------------------------------------------------------------------
    channel_title = channel.title
    topo_dict = channel.to_topology()
    covered_nets = channel.covered_nets

    # --------------------------------------------------------------------------
    # Stage 3: 前置守衛與裝配狀態檢查 (Pre-flight Guards & Mounted Check)
    # --------------------------------------------------------------------------
    # 3.1 端點不足安全略過
    if len(channel.p_endpoints) < 2:
        return RulePass(
            evidence={
                "checked_target": channel_title,
                "topology": topo_dict,
                "audit_summary": f"差分網路 {channel.p_net_name} 連接端點不足 2 個，不構成完整通道。"
            },
            target_nodes={"nets": [channel.p_net_name]}
        )

    # 3.2 兩端端點未上件 (通道未啟用) 安全略過
    if not channel.endpoints_mounted:
        unm_names = [ep.get("ref_des") for ep in channel.unmounted_endpoints]
        return RulePass(
            evidence={
                "checked_target": channel_title,
                "topology": topo_dict,
                "audit_summary": f"通道端點 ({', '.join(filter(None, unm_names))}) 標註為未上件，該通道未啟用，安全略過。"
            },
            target_nodes={"components": channel.endpoint_refs, "nets": covered_nets}
        )

    # --------------------------------------------------------------------------
    # Stage 4: 核心領域規則檢驗 (Core Domain Inspection: 開路檢查)
    # --------------------------------------------------------------------------
    violations: List[RuleViolation] = []
    for comp in channel.unmounted_pass_components:
        ref_des = getattr(comp, "ref_des", None) or comp.get("ref_des")
        display_ref = getattr(comp, "display_ref_des", None) or ref_des
        violations.append(RuleViolation(
            error_message=f"差分通道兩端端點皆已上件，但中間串聯元件 {display_ref} 標註為未上件，導致電氣開路中斷！",
            recommendation=f"請將串聯元件 {ref_des} 標註為上件以確保電氣導通。",
            severity="ERROR",
            evidence={
                "channel_title": channel_title,
                "faulty_component": ref_des,
                "topology": topo_dict,
                "covered_nets": covered_nets,
            },
            target_nodes={
                "components": [ref_des] + channel.endpoint_refs,
                "nets": covered_nets
            }
        ))

    if violations:
        return violations

    # --------------------------------------------------------------------------
    # Stage 5: 統一結果封裝與合格證明回傳 (Result Packaging & RulePass)
    # --------------------------------------------------------------------------
    return RulePass(
        evidence={
            "checked_target": channel_title,
            "audit_summary": "差分通道兩端皆已上件，中間串聯元件全數正常上件，電氣訊號完整導通。",
            "topology": topo_dict,
            "pass_through_components": channel.pass_component_refs,
        },
        target_nodes={
            "components": channel.all_component_refs,
            "nets": covered_nets
        }
    )
```

---

## 4. UI 視覺化與報表規範 (UI Contract)

前端 UniversalCircuitTopologySvg 與報表依據以下規範呈現：

1. **報告表格與標籤 (TaskReportDashboard / EvidenceDetailsBlock)**:
   - 受測元件若 `is_mounted == False`，RefDes 後方會自動附帶動態狀態徽章（若為 `P` 顯示 `[P]`、若為 `M` 顯示 `[M]`、其餘未上件顯示 `[X]`，例如 `TU2 [X]`、`TU2 [P]`）。
   - 審計結論卡片會清楚列出該元件在當前 Config 下的 BOM 狀態（如 `X` / 未上件）。

2. **SVG 通用電路拓撲圖 (UniversalCircuitTopologySvg)**:
   - **未上件零件透明度**：未上件元件外框與本體採用 `65%` 透明度（`opacity-65`），維持清晰視覺可讀性。
   - **虛線標註**：未上件元件外框轉換為 `stroke-dasharray="3,3"` 虛線。
   - **動態裝配徽章**：元件名稱旁清楚顯示淡灰色 `[X]`、`[P]` 或 `[M]` 徽章，不使用紅色，一眼區分裝配狀態。
   - **線段座標與間距**：垂直線間距設定為 `20px`，橫向網段導線長度依 `net_name` 字元長度精準動態計算，避免文字重疊。

---

## 5. 實戰撰寫範例 (Implementation Examples)

* **差分通道導通與完整性檢查**：
  請參閱標準官方實作：[`patterns/rules/interfaces/differential_channel_continuity_check.py`](file:///home/gaven/DesignShield/patterns/rules/interfaces/differential_channel_continuity_check.py)。
* **差分對極性反接與對稱性檢查**：
  請參閱標準官方實作：[`patterns/level3_rules/interfaces/pn_swap_check.py`](file:///home/gaven/DesignShield/patterns/level3_rules/interfaces/pn_swap_check.py)。
