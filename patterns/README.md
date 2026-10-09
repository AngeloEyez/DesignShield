# DesignShield 規則庫架構與治理手冊 (Rule Governance & Specification)

本目錄 (`patterns/`) 為 DesignShield 系統之硬體規則庫核心真相來源 (Single Source of Truth)，完全採用 **File-based YAML (IaC)** 進行 Git 版本控制與無狀態管理。

---

## 1. 目錄架構與層級職責 (Taxonomy)

| 目錄路徑 | 層級 | 核心職責 | 執行原則 | 快取與載入方式 |
| :--- | :--- | :--- | :--- | :--- |
| `components/` | **Level 1** | 單一零件靜態屬性辨識 (Metadata -> Category / Functional Role) | First-Match Wins (優先級高者優先) | **記憶體預編譯快取** (啟動時 `re.compile`) |
| `buses/`, `power/`, `signals/` | **Level 2** | 連線語意昇華 (Nets -> Bus/Power/Differential Pairs) 與角色覆寫 | 領域解耦、加權計分 (Confidence) | **記憶體規則清單快取** (啟動時排序) |
| `rules/` | **Level 3** | DRC 設計規則驗證 (拓撲斷言、嚴重度判定、違規定位) | 平行無序、獨立評估、分流調度 | **記憶體字典快取** (`PatternService`) |
| `rules/scripts/` | **伴生腳本** | IC 特規複雜電氣計算與動態查表 | 受限沙盒隔離執行 (AST 審查 + 5s 逾時) | **即時磁碟讀檔** (即改即生效) |
| `partdb/` | **PartDB** | 原廠規格書結構化零件特規與 `_meta` 溯源資料庫 | 介面導向 (schema_*.json 驗證) | **記憶體快取** (`PatternService`) |

---

## 2. 引擎快取機制與生效方式 (Cache & Reload Lifecycle)

### 2.1 YAML 規則的記憶體快取 (Level 1, Level 2, Level 3)
* **預載入與預編譯 (Warmup & Compilation):**
  * 為確保分析電路圖時達到毫秒級極速響應，Level 1、Level 2 與 Level 3 的 YAML 規則在**應用程式啟動時**由 `PatternService`、`ComponentPatternEngine` 與 `TopologyPatternEngine` 一次性載入記憶體，並完成正規表達式的預編譯 (`re.compile`) 與優先順序排序。
  * **在執行 DRC 分析任務時，系統直接讀取記憶體快取，不會每次請求重新讀取磁碟上的 YAML 檔案**。
* **修改 YAML 後的生效方式:**
  * 當工程師或 AI 新增、修改或刪除 `.yaml` 規則後，**不需重啟後端服務**即可生效。
  * **熱重載 API (Hot Reload):**
    發送 HTTP 請求觸發熱重載與重新編譯：
    ```bash
    curl -X POST http://localhost:8000/api/v1/patterns/reload
    ```
    該端點會先以 `validate_all_rules()` 進行語法與 Tags 嚴格校驗；校驗通過後，自動重新整理所有層級的記憶體快取並重新編譯正則表達式。
  * **備用方式:** 重啟後端容器或進程 (`docker compose restart backend`)。

### 2.2 YAML 伴生 Python 腳本的即時讀取 (`patterns/rules/scripts/*.py`)
* **即時檔案讀取 (Live Dynamic Reading):**
  * Level 3 執行引擎 (`Level3Engine`) 在評估 `type: "python_script"` 步驟時，透過內部方法 `_run_python_script` **每次執行時即時從磁碟讀取腳本內容** (`with open(full_path, "r", encoding="utf-8") as f: source_code = f.read()`)。
  * 讀取後交由 `designshield.sdk.SandboxedScriptRunner` 進行靜態 AST 審查與沙盒隔離執行。
* **修改伴生腳本後的生效方式:**
  * **修改伴生 `.py` 腳本無需重新載入，亦無需重啟服務**。只要存檔，下次執行 DRC 任務時即刻以最新程式碼運行。

---

## 3. 零硬編碼雙向相容架構 (Zero-Hardcoding & Bidirectional Compatibility)

### 3.1 核心定義與解耦原則
* **零硬編碼 (Zero-Hardcoding):**
  * 後端核心、DBOS 工作流程 (`drc_workflow.py`)、預先分析器 (`pre_analyzer.py`) 中**嚴禁硬編碼任何特定業務規則 ID、正則特徵或業務判斷保底**。
  * 所有的觸發條件、拓撲斷言、LLM Prompt 與降級摘要，100% 宣告於 YAML 中。
  * 若刪除任何規則 YAML，主程式與工作流仍能平穩運行，**在主程式碼中不留任何業務殘留**；電路圖無匹配特徵時，如實回傳空清單 `[]`，嚴禁偽造假資料保底。
* **雙向相容 (Bidirectional Compatibility):**
  * 新版 Level 3 規範全面採用具備自解釋性的語意化命名（如 `Power_Capacitor_Derating`）。
  * 為了保護既有 API 客戶端、舊版前端、資料庫種子資料與既有單元測試，`Level3Engine` 維護了雙向別名映射表 (`LEGACY_RULE_MAP`)。
  * **輸入相容 (Input Resolution):** 呼叫端傳入新名稱或舊代號（如 `RULE-PWR-CAP-DERATING`），引擎皆能智慧解析並執行該規則。
  * **輸出回溯 (Output Preservation):** 若呼叫端以舊代號請求，產出的違規報告 (`finding["rule_id"]`) 將忠實保留使用該舊代號；若以新名稱請求，則輸出新名稱。達成對外零破壞性變更 (Zero Breaking Changes)。

---

## 4. 各層級規則命名規範 (Naming & Identifier Specifications)

為確保人類工程師與 AI Agent 後續擴充規則庫時具備一致的標準，請嚴格遵守以下命名規範：

### 4.1 Level 1 元件辨識規則規範 (`patterns/components/`)
* **存放位置:** `patterns/components/<最低優先級>_<類別群組>.yaml`
* **檔名規範:**
  * 格式: `<priority_min>_<group_name>.yaml` (小寫蛇形命名 `snake_case`)
  * 範例: `980_non_electrical.yaml`, `900_integrated_circuits.yaml`, `800_passive_discrete.yaml`
* **規則名稱 / ID 規範 (`name`):**
  * 格式: `rule_<category>_<sub_category>[_<detail>]`
  * 全小寫蛇形命名 (`snake_case`)
  * 範例:
    * `rule_ic_microcontroller`
    * `rule_passive_resistor`
    * `rule_discrete_tvs`
    * `rule_non_electrical_fiducial`

### 4.2 Level 2 網路拓撲規則規範 (`patterns/power/`, `buses/`, `signals/`)
* **存放位置:**
  * 電源與地線: `patterns/power/<priority>_<name>.yaml`
  * 通訊匯流排: `patterns/buses/<priority>_<name>.yaml`
  * 功能與差分訊號: `patterns/signals/<priority>_<name>.yaml`
* **檔名規範:**
  * 格式: `<priority>_<snake_case_name>.yaml`
  * 範例: `900_generic_power.yaml`, `950_generic_gnd.yaml`, `700_i2c.yaml`, `600_differential_pair.yaml`
* **規則名稱 / ID 規範 (`name`):**
  * 格式: 大駝峰底線命名 (`UpperCamel_Snake_Case`)
  * 範例:
    * `Generic_Power_Rail`
    * `Generic_GND`
    * `I2C_Bus`
    * `Generic_Differential_Pair`

### 4.3 Level 3 DRC 設計規則規範 (`patterns/rules/`)
* **存放位置:**
  * 必須存放於最高階領域子目錄中 (深度嚴格限制兩層): `patterns/rules/<domain>/<rule_name>.yaml`
  * 允許的領域目錄範例: `interfaces/`, `power/`, `signals/`
* **檔名規範:**
  * 格式: `<snake_case_name>.yaml`
  * 範例: `i2c_pullup_existence.yaml`, `power_derating.yaml`, `sd_interface_mode.yaml`
* **標準規則名稱 / 規範 ID (`name`):**
  * 格式: **大駝峰底線命名 (`UpperCamel_Snake_Case`)**，必須具備全域唯一性。
  * 命名結構: `[實體或協定標的]_[檢查對象]_[預期狀態或動名詞]`
  * 範例對照表:

| 實體檔案路徑 | 新版標準規則名稱 (`name`) | 舊版相容代號 (Legacy ID) | 檢查模式 (`type`) |
| :--- | :--- | :--- | :--- |
| `interfaces/i2c_pullup_existence.yaml` | `I2C_Pull_Up_Existence` | `RULE-BUS-I2C-PULLUP` | `topology_check` |
| `interfaces/i2c_stm32_dynamic.yaml` | `I2C_PartDB_Dynamic_Compliance` | `RULE-BUS-I2C-STM32` | `python_script` |
| `interfaces/sd_interface_mode.yaml` | `SD_Interface_Mode_Reasoning` | `RULE-LLM-SD-MODE` | `llm_agent` |
| `interfaces/level_shift_validation.yaml` | `Level_Shift_Logic_Validation` | `RULE-LLM-LEVEL-SHIFT` | `llm_agent` |
| `power/power_derating.yaml` | `Power_Capacitor_Derating` | `RULE-PWR-CAP-DERATING` | `topology_check` |
| `power/power_ground_short.yaml` | `Power_Ground_Short_Fatal` | `RULE-PWR-GND-SHORT` | `topology_check` |
| `power/decoupling_existence.yaml` | `IC_Decoupling_Capacitor_Existence` | `RULE-PWR-DECOUPLING` | `topology_check` |
| `power/power_sequence_compatibility.yaml`| `Power_Sequence_Compatibility` | `RULE-LLM-POWER-SEQUENCE` | `llm_agent` |

---

## 5. Level 3 規則 YAML 完整欄位規格

所有 Level 3 規則必須包含以下 5 個必填頂層欄位：

```yaml
name: "SD_Interface_Mode_Reasoning"      # [必填] 規則唯一識別名稱 (UpperCamel_Snake)
description: "MicroSD 介面工作模式合理性確認" # [推薦] 人類與 LLM 易讀之中文說明
tags: ["Signal Integrity", "Bus Integrity"] # [必填] 必須存在於 tags.schema.json 白名單
severity: "Warning"                      # [必填] 嚴重度: Fatal | Error | Warning | Info

# --- [必填] 觸發條件 (決定在哪些圖譜節點上執行此規則) ---
trigger_conditions:
  graph_match:
    attributes:
      type: "net"
    net_name_regex: "(?i).*SD_.*"        # 支援正規表達式篩選特定網路

# --- [必填] 檢查邏輯 (支援 topology_check / python_script / llm_agent) ---
check_logic:
  # 模式 1: 宣告式拓撲斷言
  # type: "topology_check"
  # asserts:
  #   - condition: "has_pullup_resistor"
  #     node: "${context.target}"
  #     error_message: "缺少上拉電阻"

  # 模式 2: PartDB 沙盒伴生腳本
  # type: "python_script"
  # script_path: "patterns/rules/scripts/i2c_dynamic_checker.py"

  # 模式 3: LLM Agent 語意邏輯推理
  type: "llm_agent"
  profile: "BALANCED"                    # FAST (極速關閉思考) | BALANCED (預設) | DEEP (極致深思)
  context_extraction:
    keyword: "SD"                        # 子圖上下文抽取關鍵字
  agent_prompt: >
    分析 MicroSD 介面連線關係: ${context.subgraph}
    判斷其為 1-bit SPI 模式還是 4-bit SDIO 模式，評估其設計意圖與引腳合理性。
  fallback_summary:                      # LLM 服務離線時之專家規則安全降級定義
    description: "MicroSD 卡槽 J2 之連線經專家規則降級審查通過。"
    comment: "介面配置合理。"
    reasoning_summary: "專家啟發式特徵比對通過。"
```

---

## 6. AI Agent 與工程師新增規則檢核清單 (Rule Authoring Checklist)

當 AI Agent 或工程師新增規則時，請依序執行以下步驟：

1. **命名檢查:**
   - [ ] 檔名是否為語意化小寫蛇形命名 (`snake_case.yaml`)？
   - [ ] `name` 是否為大駝峰底線命名 (`UpperCamel_Snake_Case`) 且具備自解釋性？
2. **標籤註冊 (Tags Registry):**
   - [ ] `tags` 清單中的每個標籤是否已在 `patterns/rules/tags.schema.json` 中註冊？
   - [ ] 若使用新標籤，是否已先更新 `tags.schema.json`？
3. **伴生腳本規範 (若使用 `python_script`):**
   - [ ] 腳本檔案是否放置於 `patterns/rules/scripts/<name>.py`？
   - [ ] 腳本是否實作 `def execute(context, graph_api, part_db, params=None)`？
   - [ ] 腳本是否遵循沙盒白名單，未引入 `os`, `sys`, `subprocess` 等危險模組？
4. **本機校驗:**
   - [ ] 執行統一校驗腳本並確認回傳代碼為 0：
     ```bash
     backend/.venv/bin/python3 scripts/validate_rules.py
     ```
5. **熱重載生效:**
   - [ ] 若修改了 `.yaml` 規則，發送 `POST /api/v1/patterns/reload` 觸發重新編譯；若僅修改伴生 `.py` 腳本則直接生效。
