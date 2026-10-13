# DesignShield 規則庫架構與治理手冊 (Rule Governance & Developer Guide)

本目錄 (`patterns/`) 為 DesignShield 系統之硬體規則庫核心真相來源 (Single Source of Truth)，全面採用 **File-based YAML (IaC)** 進行 Git 版本控制與無狀態管理。

---

## 1. 目錄架構與層級職責 (Taxonomy)

| 目錄路徑 | 層級 | 核心職責 | 執行原則 | 快取與載入方式 | 伴生腳本支援 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `components/` | **Level 1** | 單一零件靜態屬性辨識 (Metadata -> Category / Functional Role) | First-Match Wins (優先級高者優先) | **記憶體預編譯快取** (啟動時 `re.compile`) | **支援** (`classify(context)`) |
| `buses/`, `power/`, `signals/` | **Level 2** | 連線語意昇華 (Nets -> Bus/Power/Differential Pairs) 與角色覆寫 | 領域解耦、加權計分 (Confidence) | **記憶體規則清單快取** (啟動時排序) | **支援** (`match(context)`) |
| `rules/` | **Level 3** | DRC 設計規則驗證 (拓撲斷言、嚴重度判定、違規定位) | 平行無序、獨立評估、分流調度 | **記憶體字典快取** (`PatternService`) | **支援** (`execute(context, ...)`) |
| `partdb/` | **PartDB** | 原廠規格書結構化零件特規與 `_meta` 溯源資料庫 | 介面導向 (schema_*.json 驗證) | **記憶體快取** (`PatternService`) | 不適用 |

---

## 2. 全系統單軌化與統一小寫蛇形命名規範 (Single-Track snake_case Policy)

### 2.1 廢除雙向相容與零業務硬編碼
* **單軌唯一識別 (Single Source of Truth):**
  * 徹底廢止舊版大寫短橫線代號（如 `RULE-BUS-I2C-PULLUP`）與雙向相容映射表 (`LEGACY_RULE_MAP`)。
  * 主程式、工作流引擎、資料庫種子與測試案例中**全面使用小寫蛇形 (`snake_case`) 作為規則的唯一識別碼**。
* **零業務硬編碼 (Zero Hardcoded Logic):**
  * 主程式核心 (`level3_runner.py`、`drc_workflow.py`、`pre_analyzer.py`) 不包含任何特定規則名稱或業務特徵的判斷邏輯。
  * 若刪除任何規則 YAML，主程式平穩運行且無任何程式碼殘留。

### 2.2 全層級規則命名標準

所有 YAML 檔案之 `name` 欄位必須通過正規表示式 `^[a-z0-9_]+$` 檢驗：

| 層級 | 命名格式 | 命名範例 | 說明 |
| :--- | :--- | :--- | :--- |
| **Level 1** | `rule_<category>_<sub_category>[_<detail>]` | `rule_ic_microcontroller`<br>`rule_passive_resistor`<br>`rule_discrete_tvs` | 元件特徵分類唯一標識 |
| **Level 2** | `<bus_or_signal_name>_<type>` | `i2c_bus`<br>`spi_bus`<br>`generic_power_rail`<br>`generic_gnd`<br>`generic_differential_pair` | 拓撲與網路群組識別 |
| **Level 3** | `<domain>_<target>_<action/expectation>` | `i2c_pull_up_existence`<br>`power_capacitor_derating`<br>`power_ground_short_fatal`<br>`sd_interface_mode_reasoning` | DRC 設計規則項目識別 |

#### Level 3 核心規則清單

| 實體檔案路徑 | 標準規則名稱 (`name`) | 檢查模式 (`type`) | 伴生腳本路徑 (同目錄同檔名) |
| :--- | :--- | :--- | :--- |
| 實體檔案路徑 | 標準規則名稱 (`name`) | 檢查模式 (`type`) | 伴生腳本路徑 (同目錄同檔名) |
| :--- | :--- | :--- | :--- |
| `interfaces/i2c_pullup_existence.yaml` | `i2c_pull_up_existence` | `python_script` | `interfaces/i2c_pullup_existence.py` (支援位號/阻值審計) |
| `interfaces/i2c_stm32_dynamic.yaml` | `i2c_stm32_dynamic` | `python_script` | `interfaces/i2c_stm32_dynamic.py` |
| `interfaces/usb_pn_swap_check.yaml` | `usb_pn_swap_check` | `python_script` | `interfaces/usb_pn_swap_check.py` |
| `interfaces/level_shift_validation.yaml` | `level_shift_logic_validation` | `llm_agent` | 無 (LLM 推理) |
| `interfaces/sd_interface_mode.yaml` | `sd_interface_mode_reasoning` | `llm_agent` | 無 (LLM 推理) |
| `power/decoupling_existence.yaml` | `ic_decoupling_capacitor_existence` | `topology_check` | 無 (純宣告式) |
| `power/power_derating.yaml` | `power_capacitor_derating` | `topology_check` | 無 (純宣告式) |
| `power/power_ground_short.yaml` | `power_ground_short_fatal` | `topology_check` | 無 (純宣告式) |
| `power/power_sequence_compatibility.yaml` | `power_sequence_compatibility` | `llm_agent` | 無 (LLM 推理) |

---

## 3. 伴生腳本規範 (Companion Script Architecture)

### 3.1 「同目錄、同檔名」儲存原則
* **就近存放原則:** 伴生腳本**必須**儲存於與所屬 YAML 檔案相同的目錄，且檔名必須相同（僅副檔名由 `.yaml` 變更為 `.py`）。
  * 範例:
    * 規則 YAML: `patterns/rules/interfaces/i2c_stm32_dynamic.yaml`
    * 伴生腳本: `patterns/rules/interfaces/i2c_stm32_dynamic.py`
* **廢除孤立目錄:** 嚴禁將腳本放置於全域孤立目錄（已徹底移除 `patterns/rules/scripts/`）。
* **自包含性:** 若 YAML 未顯式指定 `script_path`，引擎自動依「同目錄同檔名」約定尋找伴生腳本。

### 3.2 Level 1 ~ Level 3 伴生腳本職責與簽名

| 層級 | 伴生腳本核心職責 | 標準入口函式簽名 | 回傳型別與約定 |
| :--- | :--- | :--- | :--- |
| **Level 1** | **深度特徵解碼與數值計算**<br>正則初篩後，解碼非線性零件規格 (如從電阻電容料號提取介質/容差/耐壓) | `def classify(context: Dict[str, Any]) -> Dict[str, Any]` | 回傳欲覆蓋或擴充之屬性字典 (如 `{"capacitance_uf": 0.1, "voltage_v": 50}`) |
| **Level 2** | **動態拓撲演算法比對**<br>處理可變長度/迴圈路徑電路 (如梯形衰減器、多級 RC 濾波鏈) | `def match(context: Dict[str, Any]) -> bool` | 回傳 `True` (匹配成功) 或 `False` (不匹配) |
| **Level 3** | **動態特規計算、拓撲審計與 PartDB 校驗**<br>多變數公式計算、實體電阻/供電軌關聯追蹤、物理量門檻比對 | `def execute(context: RuleContext, graph_api: GraphAPI, part_db: PartDB, params: Dict[str, Any]) -> Union[List[RuleViolation], RulePass, RuleResult]` | 違規回傳 `List[RuleViolation]`；合規時回傳攜帶完整量測數據之 `RulePass` (或 `RuleResult.pass_with(...)` / `RuleResult.PASS`) |

### 3.3 沙盒隔離與安全原則
* 所有伴生腳本必須遵循 `designshield.sdk` 安全沙盒規範：
  * **禁止系統 I/O:** 嚴禁匯入 `os`, `sys`, `subprocess`, `socket`, `pathlib`, `open`, `eval`, `exec`。
  * **受限資源存取:** 僅允許透過 `GraphAPI` 與 `PartDB` 物件查詢電路圖拓撲與零件手冊規格。
  * **AST 自動審查:** 所有腳本在載入與執行前，必須通過 `ASTSecurityValidator` 靜態白名單審查。

---

## 4. 快取機制與生效方式 (Cache & Reload Lifecycle)

### 4.1 YAML 規則的記憶體快取
* **啟動時預編譯:** 應用程式啟動時，`PatternService` 將所有 YAML 規則載入記憶體，並預先編譯正則表示式 (`re.compile`)。
* **熱重載 API:** 當工程師或 AI 修改 YAML 後，無需重啟服務，呼叫熱重載 API 即可生效：
  ```bash
  curl -X POST http://localhost:8000/api/v1/patterns/reload
  ```
  該端點會先透過 `scripts/validate_rules.py` 嚴格檢驗所有規則；若全數合法，立即刷新記憶體快取並回傳重載統計資訊。

### 4.2 伴生 Python 腳本的即時讀取
* 伴生腳本在執行時由引擎即時從磁碟讀取源碼進行 AST 沙盒編譯與執行。
* **修改伴生 `.py` 腳本存檔後立即生效**，無需重新載入或重啟後端進程。

---

## 5. 規則開發完整流程 (Rule Authoring SOP)

當需要新增一條 DRC 規則時，請遵循標準作業流程：

### 步驟 1: 確認規範與命名
* 決定規則所屬領域（`interfaces/`, `power/`, `signals/`）。
* 取一個具備自解釋性的小寫蛇形名稱，例如 `usb_vbus_esd_protection`。

### 步驟 2: 撰寫 YAML 規則檔案與觸發條件 (`trigger_conditions`)

建立 `patterns/rules/<domain>/<rule_name>.yaml`。

#### 2.1 觸發條件核心機制與架構
* **無狀態目標查詢器:** Level 3 規則為平行無序執行，`trigger_conditions` 扮演圖譜（Knowledge Graph）的目標受測節點查詢器。
* **未命中即 SKIPPED:** 若電路圖中無任何節點滿足條件，規則直接判定為 `SKIPPED`，`error_message` 與 `recommendation` 保持為空，不佔用計算資源。
* **精準語意優先原則 (Zero-Regex Policy):** **強烈推薦優先使用 Level 2 建立的語意屬性標籤**（如 `bus_type: "USB"`, `diff_polarity: "P"`），徹底告別在 Level 3 規則中手寫冗長且易遺漏的 `net_name_regex`。

#### 2.2 `trigger_conditions` 完整支援參數字典

```yaml
trigger_conditions:
  graph_match:
    attributes:
      type: "net"                # 節點基本類型: "net" 或 "component"
      # --- 網路語意屬性 (由 Level 2 匯流排/差分/電源規則自動標記) ---
      bus_type: "USB"            # 匯流排類型: "USB", "I2C", "SPI", "UART", "CAN", "PCIe" 等
      net_type: "Differential"   # 網路電氣類型: "Differential", "Power", "Ground", "SingleEnded" 等
      diff_polarity: "P"         # 差分極性: "P" (正端/DP/TX+) 或 "N" (負端/DM/TX-)
      is_bus: true               # 布林標籤: 是否屬於匯流排網路 (true / false)
      is_power: true             # 布林標籤: 是否為供電軌 (true / false)
      is_ground: true            # 布林標籤: 是否為接地網路 (true / false)
      voltage_v: 3.3             # 標稱電壓數值 (如 3.3, 5.0, 1.8)
      # --- 元件特徵屬性 (由 Level 1 零件分類或 PartDB 標記) ---
      category: "IC"             # 元件大類: "IC", "Passive", "Discrete", "Connector" 等
      sub_category: "Capacitor"  # 元件子類: "Capacitor", "Resistor", "Microcontroller", "Diode" 等
      functional_role: "Pullup_Resistor" # 元件角色: "Pullup_Resistor", "Decoupling_Capacitor" 等
      is_electrical: true        # 布林標籤: 是否具備電氣特性 (true / false)
    # --- 降級相容名稱正則 (可選，僅在無 Level 2 語意時作為後備手段) ---
    net_name_regex: "(?i).*VBUS.*"
```

#### 2.3 常見典型觸發配置範例

* **範例 A: USB 差分對極性檢查 (純 Level 2 語意屬性，P端主導雙端合一審計):**
  ```yaml
  trigger_conditions:
    graph_match:
      attributes:
        type: "net"
        bus_type: "USB"
        net_type: "Differential"
        diff_polarity: "P"
  ```
* **範例 B: I2C 匯流排上拉電阻檢查 (純 Level 2 語意屬性):**
  ```yaml
  trigger_conditions:
    graph_match:
      attributes:
        type: "net"
        bus_type: "I2C"
  ```
* **範例 C: IC 電源去耦電容檢查 (Level 1 元件屬性):**
  ```yaml
  trigger_conditions:
    graph_match:
      attributes:
        type: "component"
        category: "IC"
        is_electrical: true
  ```
* **範例 D: 電源與接地直通短路致命檢查 (純屬性布林標籤):**
  ```yaml
  trigger_conditions:
    graph_match:
      attributes:
        type: "net"
        is_power: true
        is_ground: true
  ```

#### 2.4 完整 YAML 規則檔案範例
建立 `patterns/rules/power/usb_vbus_esd_protection.yaml`：

```yaml
name: "usb_vbus_esd_protection"
description: "USB VBUS 電源網路必須配置具備充分浪湧耐受之 TVS/ESD 保護元件"
tags: ["USB", "Power Domain", "ESD Protection", "Safety"]
severity: "Error"

trigger_conditions:
  graph_match:
    attributes:
      type: "net"
      bus_type: "USB"
      is_power: true

check_logic:
  - type: "python_script"
    script_path: "patterns/rules/power/usb_vbus_esd_protection.py"
```

### 步驟 3: 選擇檢查模式與撰寫伴生腳本 (Companion Script SOP)

#### 模式選用準則 (Architecture Decision):
* **全面採用伴生 Python 腳本 (`python_script`，首選標準):**
  * 凡涉及**電路物理量量測** (阻值、電容耐壓、電壓推導)、**多節點與拓撲關聯追蹤** (如尋找上拉電阻連接至哪條供電軌)、**PartDB 規格書查表**，或**需要記錄詳細確認佐證資訊 (Evidence Trail)** 者，**100% 採用伴生 Python 腳本**。
* **靜態拓撲斷言 (`topology_check`，僅限極簡屬性):**
  * 僅限於**零計算、純單一節點布林屬性比對** (例如 `power_ground_short_fatal` 檢查節點是否同時具有 `is_power` 與 `is_ground`)。引擎已清理所有寫死的特化原語 (如 `has_pullup_resistor`)，未來不再為核心引擎擴充特定硬體特徵。

#### 伴生腳本範本 (以結構化審計佐證為例):
建立同目錄同名伴生腳本 `patterns/rules/<domain>/<rule_name>.py`：

```python
"""I2C 上拉電阻電氣特規與審計伴生腳本範例"""
from typing import Dict, List, Any, Union
from designshield.sdk import (
    RuleResult,
    RulePass,
    RuleViolation,
    RuleContext,
    GraphAPI,
    PartDB,
)

def execute(
    context: RuleContext,
    graph_api: GraphAPI,
    part_db: PartDB,
    params: Dict[str, Any] = None
) -> Union[List[RuleViolation], RulePass, RuleResult]:
    target_net = context.target
    violations: List[RuleViolation] = []

    # 1. 透過 GraphAPI 查詢關聯元件與供電軌拓撲
    resistors = graph_api.get_pullup_resistors(target_net)
    if not resistors:
        return [RuleViolation(
            error_message=f"I2C 訊號線 ({target_net.net_name}) 缺少上拉電阻配置",
            recommendation="建議在 I2C 訊號線配置 2.2kΩ ~ 10kΩ 之上拉電阻至電源軌 (如 +3.3V)",
            severity="ERROR",
            evidence={"checked_target": target_net.net_name, "pullup_found": False},
            target_nodes={"components": [], "nets": [target_net.net_name]}
        )]

    # 2. 驗證阻值範圍與電源軌連接
    # 若有違規，加入 RuleViolation 物件...

    # 3. 若全數通過：回傳結構化 RulePass 物件，記錄詳細確認歷程 (Evidence Trail)
    return RulePass(
        evidence={
            "checked_target": target_net.net_name,
            "resistors": [
                {
                    "ref_des": r.ref_des,
                    "part_value": r.part_value,
                    "resistance_ohm": r.get("resistance_ohm"),
                    "power_rail": r.get("power_rail"),
                    "compliant": True
                }
                for r in resistors
            ],
            "spec_threshold": {"min_ohms": 1000, "max_ohms": 10000},
            "audit_summary": f"已確認 {target_net.net_name} 正確配置上拉電阻，符合電氣規範"
        },
        target_nodes={
            "components": [r.ref_des for r in resistors],
            "nets": [target_net.net_name]
        },
        message=f"{target_net.net_name} 上拉電阻檢驗合格"
    )
```

> **Level 3 DRC 契約與欄位規範：**
> * **未命中觸發節點：** 狀態設為 `SKIPPED`，`error_message` 與 `recommendation` 保持為空字串 `""`。
> * **規則 PASS：** 保持 `error_message` 為空字串 `""`，使用 `RulePass`（或 `RuleResult.pass_with(...)`）回傳詳細量測數值、元件位號與門檻比對之審計歷程 (`evidence`)。
> * **規則 FAIL：** `error_message` 必填明確違規原因，`recommendation` 提供工程改善建議（可選欄位），並於 `evidence` 記錄違規現場之測量數據。

### 步驟 4: 本機自動化校驗 (Mandatory)
在送出前執行統一校驗腳本：
```bash
backend/.venv/bin/python3 scripts/validate_rules.py
```
若有命名非小寫蛇形、未註冊標籤、AST 安全違規或簽名不符，校驗器將即時指出錯誤行號與原因。

### 步驟 5: 執行全套測試與熱重載
```bash
# 後端測試
backend/.venv/bin/pytest backend/tests/

# 前端測試 (含 ArchitectureGuard 零自訂 CSS 檢核)
npm --prefix frontend test

# 觸發熱重載
curl -X POST http://localhost:8000/api/v1/patterns/reload
```
