# DesignShield Level 3 DRC 規則與伴生腳本撰寫指南 (Level 3 DRC Authoring Guide)

## 1. 核心架構與設計哲學 (Core Principles)

DesignShield 的 Level 3 DRC（設計規則檢查）負責執行硬體線路的合規審查。在面對多 BOM 配置（BOM Options）與樣品/量產（Proto / MP）階段切換時，系統確立了以下最高原則：

### 1.1 雙軌解耦哲學：電氣拓撲 vs 零件裝配狀態
過去傳統的做法若在解析電路時直接將「不上件（NI/X）」的零件從圖譜中刪除，將導致嚴重的**審計盲區**（例如：原本為未上件保護晶片或佔位晶片 TU2，若走線正負極反接，會因元件被刪除而無法檢測；或是無法確認是否留有下拉電阻佔位）。

因此，DesignShield 採用**電氣拓撲（Physical Routing Netlist）與零件裝配狀態（Mounted State）雙軌解耦**：
1. **圖譜層永不破壞性刪點**：無論零件在當前 BOM Config 下是否上件，電氣原理圖圖譜永遠 100% 完整保留所有元件節點（Component Nodes）、接腳與網路走線邊（Edges）。
2. **裝配狀態下放至屬性與 SDK 介面**：子圖引擎（`create_config_subgraph`）會依據當前選取的 BOM Config 及 MP 模式，將零件的上件狀態精簡為雙核心屬性注入節點：
   - `comp.is_mounted: bool`（True 代表上件，False 代表不上件，提供極速布林判斷）
   - `comp.bom: str`（當前 Config 之正規化 BOM 縮寫代碼：`"I"`, `"X"`, `"P"`, `"M"`, `"NOBOM"`）
   - `comp.raw_bom: str`（原始完整 BOM 字串，如 `"I,X,P,I,I"`）
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
   - **典型代表**：`usb_pn_swap_check`（差分對極性反接檢查）。
   - **邏輯準則**：只要物理走線發生差分正負反接（例如 P 網路連至晶片的負極引腳 D1M/DN，或負極網路連至正極引腳 D1P/DP），**不論該元件當前是否有上件（包括標記為 NI 的 TU2）**，都屬於嚴重的 PCB 布線錯誤，必須一律判定為 **`CRITICAL / ERROR`**。
   - **UI 呈現**：在違規報告與證據鏈路中，將未上件元件標記為 `[X]`，並在錯誤訊息中明確告知：「此元件在當前 Config 下標註為未上件 [X]，但走線反接仍屬嚴重線路錯誤」。

2. **電氣導通視角 (Electrical Continuity Perspective)**
   - **典型代表**：`differential_channel_continuity_check`（差分通道導通與串聯元件完整性檢查）。
   - **邏輯準則**：
     - 若高速差分通道兩端端點（Endpoints，如 CPU 與 Type-C 接頭）皆同時上件，則中間所有串聯穿透被動元件（AC 耦合電容、串聯電阻、共模扼流圈 CMC）必須全數存在且確實上件（`is_mounted == True`）。
     - 若中間任何串聯元件未上件，將導致訊號開路中斷，判定為 **`CRITICAL / ERROR`**。
     - 若通道兩端端點有任一端未上件（如選配子卡未裝配），表示該通道在當前配置下未啟用，安全通過（`RulePass`）。

3. **預留/佔位符視角 (Placeholder & Support Perspective)**
   - **典型代表**：`pulldown_placeholder_check`（下拉電阻預留檢查）。
   - **邏輯準則**：部分硬體規範要求特定引腳必須預留下拉或上拉電阻焊盤（Footprint/Placeholder），以便後續調試或相容不同版本。此時只需確認電阻在電氣網絡上是否存在（`graph_api.has_placeholder`），即使零件標註為 `NI`（未上件），亦屬合規。

---

## 2. SDK 核心資料模型與 API 參考 (SDK Reference)

所有 Level 3 伴生腳本皆在沙盒環境中執行，由系統自動注入 `context: RuleContext`, `graph_api: GraphAPI`, `part_db: PartDB`。

### 2.1 `ComponentNode` 屬性與方法
當您透過 `graph_api` 取得元件節點時，節點已被封裝為 `ComponentNode`（或具備等價屬性的資料物件）：

| 屬性 / 方法 | 型別 | 說明 | 範例值 |
| :--- | :--- | :--- | :--- |
| `comp.ref_des` | `str` | 元件原始位號 | `"TU2"` |
| `comp.display_ref_des` | `str` | 具備裝配狀態的動態顯示位號（未上件依狀態自帶 `[X]`/`[P]`/`[M]`） | `"TU2 [X]"`, `"TU2 [P]"` 或 `"U1"` |
| `comp.is_mounted` | `bool` | 當前配置與 MP 模式下是否上件（**最常使用，極速布林判斷**） | `True` / `False` |
| `comp.bom` | `str` | 當前 Config 之正規化 BOM 縮寫代碼 | `"I"`, `"X"`, `"P"`, `"M"`, `"NOBOM"` |
| `comp.raw_bom` | `str` | 原始未展開之 BOM 設定字串 | `"I,X,P,I,I"` |
| `comp.category` | `str` | 元件主類別 | `"IC"`, `"Passive"`, `"Connector"` |
| `comp.functional_role` | `str` | 元件功能角色 | `"AC_Coupling_Capacitor"`, `"Common_Mode_Choke"` |

---

### 2.2 `GraphAPI` 關鍵方法

#### (1) 上件狀態查詢
```python
# 1. 查詢特定位號或節點是否上件
if not graph_api.is_mounted("TU2"):
    print("TU2 未上件")

# 2. 獲取當前圖譜中所有未上件元件清單
unmounted_list = graph_api.get_unmounted_components()
for comp in unmounted_list:
    print(f"未上件: {comp.display_ref_des}")
```

#### (2) 佔位符 / 預留件檢測
```python
# 檢查特定網絡上是否存在指定角色之預留元件 (不論是否上件)
has_pd = graph_api.has_placeholder(net_name="USB_CC1", role="Pull_down")
```

#### (3) 端到端通道追蹤 (End-to-End Tracing)
`graph_api.trace_differential_end_to_end(net_name: str) -> List[Dict]`
追蹤差分網路穿透所有串聯被動元件後的端點清單。回傳的字典結構中：
- `ep["component"]`: 端點之 `ComponentNode`（具備 `is_mounted`）
- `ep["path_segments"]`: 途經段落明細，每個段落皆包含 `"is_mounted": bool`
- `ep["pass_through_components"]`: 途中穿透之被動元件清單（每個元件皆具備 `is_mounted`）

---

## 3. Level 3 伴生腳本五階段標準架構 (5-Stage Pipeline)

所有伴生腳本必須遵循五階段標準流水線架構，確保程式碼具備高維護性與一致的證據鏈：

```python
"""
伴生腳本五階段標準範本
"""
from typing import Dict, List, Any, Union
from designshield.sdk import (
    RuleResult,
    RulePass,
    RuleViolation,
    RuleContext,
    GraphAPI,
    PartDB,
    TopologyGraphBuilder,
)

def execute(
    context: RuleContext,
    graph_api: GraphAPI,
    part_db: PartDB,
    params: Dict[str, Any] = None
) -> Union[RulePass, RuleViolation, List[RuleViolation], RuleResult]:
    
    # --------------------------------------------------------------------------
    # Stage 1: 目標解析與前置守衛 (Target Resolution & Pre-flight Guard)
    # --------------------------------------------------------------------------
    target = context.target
    net_name = str(target.get("net_name") or target.get("name") or "")
    if not net_name:
        return RuleResult.SKIPPED

    # --------------------------------------------------------------------------
    # Stage 2: 拓撲展開與通道收集 (Topology Expansion & Covered Nets)
    # --------------------------------------------------------------------------
    endpoints = graph_api.trace_differential_end_to_end(f"net:{net_name}")
    covered_nets = [net_name] + [n for ep in endpoints for n in ep.get("covered_nets", [])]

    # --------------------------------------------------------------------------
    # Stage 3: 核心領域規則檢驗 (Core Domain Inspection)
    # --------------------------------------------------------------------------
    violations: List[RuleViolation] = []

    for ep in endpoints:
        comp = ep["component"]
        # 依據規則性質自主運用 comp.is_mounted
        if not comp.is_mounted:
            # 視角 A: 若為走線極性反接，照常檢查反接，反接時報 ERROR
            # 視角 B: 若為通道導通性，記錄未上件或跳過
            pass

    # --------------------------------------------------------------------------
    # Stage 4: 三層佐證與拓撲建構 (Evidence & Topology Construction)
    # --------------------------------------------------------------------------
    builder = TopologyGraphBuilder(title=f"{net_name} 鏈路審計", channel_type="differential")
    # 將 is_mounted 忠實傳入 TopologyGraphBuilder
    for ep in endpoints:
        builder.add_terminal(
            id=ep["component"].ref_des,
            ref_des=ep["component"].ref_des,
            category=ep["component"].category,
            is_mounted=ep["component"].is_mounted,
            pins=[{"pin_number": ep.get("pin_number", "1"), "pin_name": ep.get("pin_name", "")}]
        )
    topo_dict = builder.to_dict()

    # --------------------------------------------------------------------------
    # Stage 5: 統一結果封裝與回傳 (Result Packaging)
    # --------------------------------------------------------------------------
    if violations:
        for v in violations:
            v.evidence["topology"] = topo_dict
            v.evidence["covered_nets"] = covered_nets
        return violations

    return RulePass(
        evidence={
            "checked_target": f"{net_name} 傳輸通道",
            "covered_nets": covered_nets,
            "audit_summary": "差分線路審查合格，極性與導通性完全符合規範。",
            "topology": topo_dict,
        },
        target_nodes={"nets": covered_nets}
    )
```

---

## 4. UI 視覺化與報表規範 (UI Contract)

為了使工程師在審查報告時能一眼識別零件裝配狀態：

1. **報告表格與標籤 (TaskReportDashboard / EvidenceDetailsBlock)**:
   - 受測元件若 `is_mounted == False`，RefDes 後方會自動附帶動態狀態徽章（若為 `P` 顯示 `[P]`、若為 `M` 顯示 `[M]`、其餘未上件顯示 `[X]`，例如 `TU2 [X]`、`TU2 [P]`）。
   - 審計結論卡片會清楚列出該元件在當前 Config 下的 BOM 狀態（如 `X` / 未上件）。

2. **SVG 通用電路拓撲圖 (UniversalCircuitTopologySvg)**:
   - **淡化處理**：未上件元件外框與本體採用 `opacity-30` (30% 透明度) 效果。
   - **虛線標註**：外框由原本的實線轉換為 `stroke-dasharray="3,3"` 虛線。
   - **動態裝配徽章**：元件名稱旁清楚顯示淡灰色 `[X]`、`[P]` 或 `[M]` 徽章，不使用紅色，一眼區分裝配狀態。

---

## 5. 實戰撰寫範例 (Implementation Examples)

### 範例 A: 差分對極性檢查 (走線視角，未上件仍需抓反接)
參見完整的官方實作：[patterns/rules/interfaces/usb_pn_swap_check.py](file:///home/gaven/DesignShield/patterns/rules/interfaces/usb_pn_swap_check.py)
重點程式碼：
```python
# 遍歷所有端點（不論 comp.is_mounted 是否為 True）
for ep in p_endpoints:
    comp = ep["component"]
    pin_polarity = _determine_pin_polarity(ep["pin_name"])
    
    # 若正極網路接到負極引腳 (N)，即刻觸發違規
    if pin_polarity == "N":
        is_mounted = comp.is_mounted
        unmounted_tag = " [X]" if not is_mounted else ""
        unmounted_note = "（此元件在當前 Config 下標註為未上件 [X]，但走線反接仍屬嚴重線路錯誤）" if not is_mounted else ""
        
        violations.append(RuleViolation(
            error_message=f"USB 差分對極性反接：正極網路誤連接至元件 {comp.ref_des}{unmounted_tag} 之負極引腳 [{ep['pin_name']}]！{unmounted_note}",
            severity="ERROR",
            evidence={"is_mounted": is_mounted, "faulty_component": comp.ref_des}
        ))
```

### 範例 B: 差分通道完整性檢查 (電氣導通視角，中間開路報 ERROR)
參見完整的官方實作：[patterns/rules/interfaces/differential_channel_continuity_check.py](file:///home/gaven/DesignShield/patterns/rules/interfaces/differential_channel_continuity_check.py)
重點程式碼：
```python
# 1. 兩端端點若未全部上件，代表通道未啟用，安全略過
if not all(ep["component"].is_mounted for ep in endpoints):
    return RulePass(evidence={"audit_summary": "端點元件標註為未上件，該通道未處於啟用工作狀態，安全略過。"})

# 2. 兩端端點皆已上件：檢查中間所有串聯元件 (AC caps, CMC, series resistors)
for comp in pass_through_components:
    if not comp.is_mounted:
        violations.append(RuleViolation(
            error_message=f"差分通道兩端端點皆已上件，但途中串聯元件 {comp.display_ref_des} 標註為未上件，導致高速訊號開路中斷！",
            severity="ERROR",
            evidence={"faulty_component": comp.ref_des, "is_mounted": False}
        ))
```
