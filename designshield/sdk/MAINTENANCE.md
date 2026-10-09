# DesignShield SDK 技術維護與架構擴充手冊 (Architecture & Maintenance Guide)

本文件供 **AI 代理 (AI Agents)** 與 **核心架構維護團隊 (Maintainers)** 閱讀，明定 `designshield.sdk` 的設計哲學、內部模組邊界以及未來擴充時的硬性規範。

---

## 1. 系統定位與架構職責 (Architecture & Boundary)

`designshield.sdk` 定位為 **「規則引擎與動態腳本之間的唯一安全合約層 (Contract & Isolation Boundary)」**：

```
                ┌──────────────────────────────────────────────┐
                │        Level 3 DRC YAML 規則檔               │
                └──────────────────────┬───────────────────────┘
                                       │ script_path
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 伴生動態腳本 (patterns/rules/scripts/*.py)                                  │
│                                                                             │
│   import { RuleResult, RuleViolation, GraphAPI, PartDB }                    │
│   def execute(context, graph_api, part_db, params):                         │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ 呼叫 SDK 介面 (唯讀、受限)
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ designshield.sdk (安全與型別合約層)                                          │
│                                                                             │
│  [models.py]      [graph_api.py]       [part_db.py]      [sandbox.py]       │
│  • RuleViolation  • 唯讀拓撲查詢       • PartDB 查表     • AST 靜態審查     │
│  • ComponentNode  • 自動節點包裝       • YAML/JSON 快取  • 受限 Builtins    │
│  • NetNode                                               • 5s 超時保護      │
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
| `designshield/sdk/models.py` | 資料模型 | 定義 `RuleViolation`, `RuleResult`, `RuleContext`, `ComponentNode`, `NetNode`。 | 節點類別**必須繼承 `dict`**，維持字典存取與屬性存取的雙向相容。 |
| `designshield/sdk/graph_api.py` | 拓撲查詢 | 封裝 NetworkX 圖譜查詢，回傳包裝好的節點物件。 | **嚴禁暴露任何可變更圖譜的方法** (如 `add_node`, `remove_edge`)，確保唯讀。 |
| `designshield/sdk/part_db.py` | 規格查表 | 封裝晶片硬體特規查詢與結構化 `_meta` 溯源資料提取。 | 查表過程不得寫入檔案或連線外部網路，僅讀取本機快取與資料庫。 |
| `designshield/sdk/sandbox.py` | 安全沙盒 | 實作 `ASTSecurityValidator` 與 `SandboxedScriptRunner`。 | 採用嚴格白名單，新增允許匯入之模組必須經過安全評估。 |

---

## 3. 核心設計原則 (Core Design Principles)

### 原則一：唯讀不可變原則 (Read-Only Immutability)
動態腳本**絕對不可**變更電路圖譜結構或網路屬性。圖譜的變更與屬性標記（如 `is_bus`, `is_power`, `role_overrides`）屬於 Level 1/2 引擎的職責，Level 3 腳本僅負責**斷言 (Assert) 與報告違規 (Report Violation)**。

### 原則二：雙向存取相容原則 (Dual-Access Compatibility)
為了保證既有單元測試（使用字典存取 `node['part_value']`）與新版腳本（使用屬性存取 `node.pn`）均能無縫運行，所有由 `GraphAPI` 回傳的節點物件，**必須為 `ComponentNode` 或 `NetNode`**，其底層皆為 Python `dict` 的子類。

### 原則三：零外部相依原則 (Zero Heavy Dependencies)
SDK 必須保持極致輕量。沙盒防護一律使用 Python 內建的 `ast`、`builtins` 與 `concurrent.futures` 實作，**嚴禁隨意引入重量級第三方套件**，以確保在任何標準 Python 環境下均能直接載入。

---

## 4. 維護與擴充作業指南 (How-to Guide)

### 4.1 如何為 `GraphAPI` 新增拓撲查詢方法？
若硬體檢查需要新型態的電路特徵（例如「取得與差分對配對之負端網路」）：
1. 於 `designshield/sdk/graph_api.py` 的 `GraphAPI` 類別中新增方法。
2. 入參統一接受 `Union[NetNode, ComponentNode, Dict[str, Any], str]`，並使用 `self._resolve_node_id(node)` 解析節點 ID。
3. **回傳值必須自動包裝**：
   * 回傳元件時：使用 `ComponentNode(ndata)`。
   * 回傳網路時：使用 `NetNode(ndata)`。
4. 必須編寫標準 JSDoc/Docstring 格式註解與型別提示。
5. 於 `backend/tests/test_sdk_and_sandbox.py` 中新增對應的單元測試。

### 4.2 如何擴充 `ComponentNode` / `NetNode` 屬性？
1. 於 `designshield/sdk/models.py` 的對應類別下增加 `@property`。
2. 屬性實作需具備空值保底（防禦性程式設計），例如：
   ```python
   @property
   def package(self) -> str:
       """取得封裝型號"""
       return str(self.get("package") or self.get("pcb_footprint") or "")
   ```

### 4.3 如何擴充沙盒允許的標準模組白名單？
若領域專家撰寫腳本需要使用額外的 Python 官方標準模組（例如 `decimal` 計算高精度阻抗）：
1. 評估該模組是否具備潛在 I/O 或系統呼叫能力。
2. 於 `designshield/sdk/sandbox.py` 的 `ALLOWED_MODULES` 集合中加入該模組名稱（例如 `"decimal"`）。
3. 嚴禁將具備檔案操作或進程控制之模組（如 `os`, `sys`, `socket`, `subprocess`）加入白名單。

---

## 5. 品質與持續整合驗證規範 (CI/CD Verification)

任何對 `designshield.sdk` 的變更，必須滿足以下檢查方可提交：
1. **全套測試 100% 通過**：
   ```bash
   pytest backend/tests/test_sdk_and_sandbox.py
   pytest backend/tests/
   ```
2. **規則統一校驗通過**：
   ```bash
   python scripts/validate_rules.py
   ```
3. **繁體中文義務**：所有新增之 Docstring、註解與日誌必須使用繁體中文。
