# DesignShield SDK 技術維護與架構擴充手冊 (Architecture & Maintenance Guide)

本文件供 **AI 代理 (AI Agents)** 與 **核心架構維護團隊 (Maintainers)** 閱讀，明定 `designshield.sdk` 的設計哲學、內部模組邊界以及未來擴充時的硬性規範。

---

## 1. 系統定位與架構職責 (Architecture & Boundary)

`designshield.sdk` 定位為 **「規則引擎與動態腳本之間的唯一安全合約層 (Contract & Isolation Boundary)」**：

```
                ┌──────────────────────────────────────────────┐
                │        Level 3 DRC YAML 規則檔               │
                └──────────────────────┬───────────────────────┘
                                       │ 綁定同目錄同檔名伴生腳本
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 伴生動態腳本 (patterns/rules/<domain>/*.py)                                 │
│                                                                             │
│   from designshield.sdk import DifferentialChannel, GraphAPI, PartDB        │
│   def execute(context, graph_api, part_db, params):                         │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ 呼叫 SDK 介面 (唯讀、受限、高階抽象)
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ designshield.sdk (安全、型別與通道抽象合約層)                               │
│                                                                             │
│  [channel.py]     [graph_api.py]       [models.py]       [part_db.py]       │
│  • BaseChannel    • 唯讀拓撲查詢       • RuleViolation   • PartDB 查表      │
│  • Differential   • 起點正規化         • ComponentNode   • YAML 快取        │
│  • SingleEnded    • 自動節點包裝       • NetNode                            │
│  • to_topology()                                         [sandbox.py]       │
│  [topology.py]                                           • AST 靜態審查     │
│  • UniversalTopologyBuilder                              • 5s 超時保護      │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ 內部轉譯為底層呼叫
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 後端核心引擎 (Backend Core Engines)                                         │
│ • NetworkX Graph (原始拓撲圖譜)                                             │
│ • PatternService (記憶體規則庫與快取)                                       │
│ • DBOS Workflow (Durable 任務調度與持久化)                                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. 模組組織與職責分配

| 檔案路徑 | 模組名稱 | 核心職責 | 擴充限制與禁忌 |
| :--- | :--- | :--- | :--- |
| `designshield/sdk/channel.py` | **通道模型與高階拓撲** | 提供 `BaseChannel`、`DifferentialChannel`、`SingleEndedChannel`。封裝源端權重評估、雙軌夥伴推導、直連 1 對多發散扇出 (Multi-drop)、穿透段落開路檢測 (`is_continuous`) 與一鍵拓撲輸出 (`to_topology`)。 | 通道模型為純無狀態抽象，資料來源必須全數來自 `GraphAPI`，嚴禁自行進行檔案 I/O 或修改圖譜。 |
| `designshield/sdk/diff_pair.py` | **差分極性與夥伴推導核心 (Single Source of Truth)** | 提供 `DifferentialPairResolver`、`determine_diff_polarity`、`resolve_diff_pair_partner`、`resolve_diff_pair_candidates`。集中管理所有差分命名對稱正則轉換矩陣。 | 供 Level 2 拓撲引擎、Level 3 規則、SDK 通道模型共用。嚴禁在其他業務模組私自手寫正則推導差分極性或夥伴。 |
| `designshield/sdk/graph_api.py` | **拓撲查詢介面** | 封裝 NetworkX 圖譜查詢，提供 `get_differential_channel`、`get_single_ended_channel`，並回傳包裝好的節點物件。 | **嚴禁暴露任何可變更圖譜的方法** (如 `add_node`, `remove_edge`)，確保 100% 唯讀。 |
| `designshield/sdk/models.py` | **資料模型與契約** | 定義 `RuleViolation`, `RulePass`, `RuleResult`, `RuleContext`, `ComponentNode`, `NetNode`。 | 節點類別**必須繼承 `dict`**，維持字典存取與屬性存取的雙向相容。 |
| `designshield/sdk/topology.py` | **通用拓撲建造者** | 實作 `TopologyGraphBuilder`，負責產生符合前端 UniversalCircuitTopologySvg 契約之標準拓撲字典。 | 必須維持節點與引腳合併原則，同一個 RefDes 在多個軌道時應合併 Pins 而非重複建立節點。 |
| `designshield/sdk/part_db.py` | **規格查表** | 封裝晶片硬體特規查詢與結構化 `_meta` 溯源資料提取。 | 查表過程不得寫入檔案或連線外部網路，僅讀取本機快取與資料庫。 |
| `designshield/sdk/sandbox.py` | **安全沙盒** | 實作 `ASTSecurityValidator` 與 `SandboxedScriptRunner`。 | 採用嚴格白名單，新增允許匯入之模組必須經過安全評估。 |

---

## 3. 核心設計原則 (Core Design Principles)

### 原則一：唯讀不可變原則 (Read-Only Immutability)
動態腳本與通道模型**絕對不可**變更電路圖譜結構或網路屬性。圖譜的變更與屬性標記（如 `is_bus`, `is_power`, `role_overrides`）屬於 Level 1/2 引擎的職責，Level 3 腳本僅負責**斷言 (Assert) 與報告違規 (Report Violation)**。

### 原則二：雙向存取相容原則 (Dual-Access Compatibility)
為了保證既有單元測試（使用字典存取 `node['part_value']`）與新版腳本（使用屬性存取 `node.pn`）均能無縫運行，所有由 `GraphAPI` 回傳的節點物件，**必須為 `ComponentNode` 或 `NetNode`**，其底層皆為 Python `dict` 的子類。

### 原則三：高階抽象下沉與領域去重 (High-Level Channel Abstraction)
通道追蹤、正負軌配對、直連 1 對多發散扇出、多端點逗號展開標題、串聯段落拓撲建立，**一律下沉至 `channel.py` 核心模型中實作**。伴生腳本只負責設定規則閾值與產出特定錯誤文案，嚴禁在個別腳本中重複撰寫私有拓撲與引腳繪製邏輯。

### 原則四：零外部相依原則 (Zero Heavy Dependencies)
SDK 必須保持極致輕量。沙盒防護一律使用 Python 內建的 `ast`、`builtins` 與 `concurrent.futures` 實作，**嚴禁隨意引入重量級第三方套件**，以確保在任何標準 Python 環境下均能直接載入。

---

## 4. 維護與擴充作業指南 (How-to Guide)

### 4.1 如何為 `GraphAPI` 新增拓撲查詢方法？
若硬體檢查需要新型態的電路特徵：
1. 於 `designshield/sdk/graph_api.py` 的 `GraphAPI` 類別中新增方法。
2. 入參統一接受 `Union[NetNode, ComponentNode, Dict[str, Any], str]`，並使用 `self._resolve_node_id(node)` 解析節點 ID。
3. **回傳值必須自動包裝**：
   * 回傳元件時：使用 `ComponentNode(ndata)`。
   * 回傳網路時：使用 `NetNode(ndata)`。
4. 必須編寫標準 JSDoc/Docstring 格式繁體中文註解與型別提示。
5. 於 `backend/tests/test_sdk_channel.py` 或 `test_sdk_and_sandbox.py` 中新增對應的單元測試。

### 4.2 如何擴充 `DifferentialChannel` 或 `SingleEndedChannel`？
若未來有新型高速通道（如 PAM4 四電平差分、多相供電 Multiphase VRM 通道）：
1. 於 `designshield/sdk/channel.py` 繼承 `BaseChannel` 建立對應子類。
2. 實作 `to_topology() -> Dict[str, Any]`，確保輸出之 JSON 結構完全符合 `UniversalTopologyData` 規範。
3. 擴充 `BaseChannel` 之通用計算屬性（如 `is_continuous`, `unmounted_pass_components`）。
4. 在 `GraphAPI` 新增對應之工廠方法（如 `get_multiphase_channel()`）。
5. 於 `designshield/sdk/__init__.py` 匯出新類別。

### 4.3 源端啟發式權重評估規範 (`_score_root_component`)
當差分通道為直連或多端點並聯（Multi-drop）時，SDK 依下列權重分數挑選發散源端 (`start_ref / root_ref`)：
* **3 分 (主控晶片 / CPU 插槽 / SoC)**：RefDes 為 `CPU*`, `SOC*`, `XU*`, `U*` (排除 USB 晶片)，或品名/類別包含 `socket`, `lga`, `bga`, `processor`, `ic`。
* **2 分 (板級外部連接器)**：RefDes 為 `TJ*`, `J*`，或型號包含 `type-c`, `typec`, `receptacle`。
* **1 分 (一般元件)**。
* **0 分 (記憶體插槽 / 子插槽 / 終端負載)**：RefDes 為 `XMM*`，或型號包含 `dimm`, `udimm`, `rdimm`, `sodimm`。
* **發散拓撲規則**：源端元件向所有目標端點（`target_refs`）分別建立獨立的 `is_branch=False` 連線，避免終端之間互相回串。

### 4.4 如何擴充差分對命名規則？(Differential Pair Naming Expansion)
為了避免高速差分命名配對正則分散在各檢查腳本導致維護噩夢，DesignShield 建立了**雙層擴充機制**：

1. **宣告式 YAML 規則擴充 (推薦領域專家使用)**：
   * 在 `backend/app/engine/pattern_engine/rules/600_differential_pair.yaml` 的 `partner_swap_rules` 列表中直接新增正則配對（不需修改 Python 代碼）：
   ```yaml
   partner_swap_rules:
     - name: "custom_diff_pair"
       pattern_p: '^(.*)_CUSTOM_P(.*)$'
       pattern_n: '^(.*)_CUSTOM_N(.*)$'
   ```
   * Level 2 拓撲引擎會在分析時自動呼叫 `DifferentialPairResolver.from_yaml_rules()`，將此定義注入圖譜節點標記。

2. **SDK 內建轉換矩陣擴充 (核心硬體標準)**：
   * 若該命名為跨專案通用的硬體標準（如 EDA 原理圖、PCIe、SATA、USB、SAS 等常用變形），直接在 `designshield/sdk/diff_pair.py` 的 `DEFAULT_PARTNER_SWAP_RULES` 新增元組：
   ```python
   PartnerSwapRule(
       pattern_p=re.compile(r"^(.*)_CUSTOM_P(_.*)?$", re.IGNORECASE),
       pattern_n=re.compile(r"^(.*)_CUSTOM_N(_.*)?$", re.IGNORECASE),
       name="custom_pair",
   )
   ```
   * 內建支援自動雙向推導（正推負、負推正、大小寫自適應）。

3. **執行期動態註冊 (測試或自訂腳本)**：
   * 可透過 `DifferentialPairResolver.register_rule(pattern_p, pattern_n, name)` 在特定測試環境或腳本中動態註冊。

---

## 5. 品質與持續整合驗證規範 (CI/CD Verification)

每次修改 SDK 代碼或擴充通道模型後，必須在本地執行全套測試確認 100% 通過：
```bash
# 1. 執行 SDK 專屬通道測試
backend/.venv/bin/pytest backend/tests/test_sdk_channel.py -v

# 2. 執行後端全套測試 (157+ 項)
backend/.venv/bin/pytest backend/tests

# 3. 執行前端全套測試 (104+ 項，包含 0 行自訂 CSS 守護測試)
npm --prefix frontend run test
```
