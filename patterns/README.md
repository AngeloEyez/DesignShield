# DesignShield 規則庫架構與治理手冊 (Rule Governance & Developer Guide)

本目錄 (`patterns/`) 為 DesignShield 系統之硬體規則庫核心真相來源 (Single Source of Truth)，全面採用 **File-based YAML (IaC)** 進行 Git 版本控制與無狀態管理。

---

## 1. 目錄架構與層級職責 (Taxonomy)

| 目錄路徑 | 層級 | 核心職責 | 執行原則 | 快取與載入方式 | 伴生腳本支援 | 官方範本檔案 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `level1_components/` | **Level 1** | 單一零件靜態屬性辨識 (Metadata -> Category / Component Role) | First-Match Wins (優先級高者優先) | **全自動遞迴掃描** (啟動時 `re.compile`) | **支援** (`classify(context)`) | [`_template.yaml`](file:///home/gaven/DesignShield/patterns/level1_components/_template.yaml) |
| `level2_topology/` | **Level 2** | 連線語意昇華 (Nets -> Bus/Power/Differential Pairs) 與角色覆寫 | 領域解耦、加權計分 (Confidence) | **全自動遞迴掃描** (啟動時依 priority 排序) | **支援** (`match(context)`) | [`_template.yaml`](file:///home/gaven/DesignShield/patterns/level2_topology/_template.yaml) |
| `level3_rules/` | **Level 3** | DRC 設計規則驗證 (拓撲斷言、嚴重度判定、違規定位) | 平行無序、獨立評估、分流調度 | **全自動遞迴掃描** (`PatternService`) | **支援** (`execute(context, ...)`) | [`_template.yaml`](file:///home/gaven/DesignShield/patterns/level3_rules/_template.yaml)<br>[`_template.py`](file:///home/gaven/DesignShield/patterns/level3_rules/_template.py) |
| `partdb/` | **PartDB** | 原廠規格書結構化零件特規與 `_meta` 溯源資料庫 | 介面導向 (schema_*.json 驗證) | **全自動遞迴快取** (`PatternService`) | 不適用 | [`_template.yaml`](file:///home/gaven/DesignShield/patterns/partdb/_template.yaml) |

### 1.1 目錄存放位置、子目錄深度與掃描載入規範 (Directory Structure & Scanning Policy)

各層級之 YAML 檔案存放目錄名稱、是否允許自訂子目錄與深度支援規範如下表：

| 層級 / 模組 | 規定根目錄 | 子目錄與深度支援 | 掃描實作機制 | 規劃與存放規範 |
| :--- | :--- | :---: | :--- | :--- |
| **PartDB** | `patterns/partdb/data/` | **支援任意子目錄與深度**<br>（全自動遞迴） | `os.walk(data_dir)` | **自由規劃**：可依元件類別、製造商或專案自由分層建立子目錄（如 `ics/`、`passives/` 等），系統遞迴自動載入。 |
| **Level 3** (DRC 規則) | `patterns/level3_rules/` | **支援任意子目錄與深度**<br>（全自動遞迴） | `os.walk(rules_dir)` | **自由規劃**：可依檢驗領域自由建立子目錄（如 `power/`、`interfaces/` 等），系統與伴生腳本皆以遞迴方式自動探索。 |
| **Level 2** (拓撲規則) | `patterns/level2_topology/` | **支援任意子目錄與深度**<br>（全自動遞迴） | `os.walk(l2_dir)` | **自由規劃**：推薦依通訊、電源、信號劃分子目錄（如 `buses/`、`power/`、`signals/`），系統遞迴自動載入。 |
| **Level 1** (元件分類) | `patterns/level1_components/` | **支援任意子目錄與深度**<br>（全自動遞迴） | `os.walk(l1_dir)` | **自由規劃**：可依元件領域自由建立子目錄（如 `passives/`、`ics/`、`connectors/` 等），亦可直接存放於根目錄，系統遞迴自動載入。 |

> [!NOTE]
> 1. 所有層級中檔名以底線 `_` 開頭之檔案（例如 `_template.yaml`、`_template.py`）均被引擎與驗證腳本自動略過，不參與執行期評估。
> 2. Level 1、Level 2、Level 3 與 PartDB 四大模組均已全面實作全自動遞迴掃描 (`os.walk`)，工程師可自由依架構需要新增任意層級之領域子目錄。

### 1.2 各層級手冊索引與導讀 (Documentation Index)

為了維持架構清晰與好維護性，各層級具體的 YAML 參數規格與運算子語法採**領域拆分專屬手冊**管理：
* **[Level 1 元件分類規則手冊 (Component Rules Guide)](file:///home/gaven/DesignShield/patterns/level1_components/README.md)**：完整說明 `ComponentRule`、`MatchCondition` 屬性鍵值運算子映射 (`exact`, `ne`, `regex`, `prefix`, `suffix`, `in`, `not_in`, `min`/`max`, `exists`)、支援之標準屬性 (`ref_des`, `bom`, `part_value`, `pins_count` 等) 與 CAD 擴充屬性 (`props.<key>`)、`AssignData` 賦值規格與伴生腳本。
* **[Level 2 網路與拓撲規則手冊 (Topology Rules Guide)](file:///home/gaven/DesignShield/patterns/level2_topology/README.md)**：完整說明 `TopologyRule`、電源與接地軌識別、通訊匯流排協定定義 (`signals` 槽位)、差分對正負極性宣告式推導 (`pair_derivation`) 與元件拓撲角色動態覆寫 (`component_role_overrides`)。
* **[Level 3 DRC 設計規則驗證手冊 (Design Rule Check Guide)](file:///home/gaven/DesignShield/patterns/level3_rules/README.md)**：完整說明 `Level3Rule`、觸發條件 (`trigger_conditions`)、零寫死伴生腳本自動關聯機制、真實資料審計原則 (`RuleSkipped`)、Tags 白名單約束與端到端通道穿透去重。
* **[PartDB 零件規格庫手冊 (PartDB Guide)](file:///home/gaven/DesignShield/patterns/partdb/README.md)**：完整說明零件物理特規、`_meta` 原廠手冊頁碼佐證出處、供電軌與去耦電容約束、穿透引腳映射 (`pass_through.pin_pairs`) 與雙層檢索演算法。

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
| `interfaces/i2c_pullup_existence.yaml` | `i2c_pull_up_existence` | `python_script` | `interfaces/i2c_pullup_existence.py` (支援位號/阻值審計) |
| `interfaces/i2c_stm32_dynamic.yaml` | `i2c_stm32_dynamic` | `python_script` | `interfaces/i2c_stm32_dynamic.py` |
| `interfaces/usb_pn_swap_check.yaml` | `usb_pn_swap_check` | `python_script` | `interfaces/usb_pn_swap_check.py` (支援極性反接與對稱性審計) |
| `interfaces/differential_channel_continuity_check.yaml` | `differential_channel_continuity_check` | `python_script` | `interfaces/differential_channel_continuity_check.py` (支援端到端差分導通與開路審計) |
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
    * 規則 YAML: `patterns/level3_rules/interfaces/i2c_stm32_dynamic.yaml`
    * 伴生腳本: `patterns/level3_rules/interfaces/i2c_stm32_dynamic.py`
* **廢除孤立目錄:** 嚴禁將腳本放置於全域孤立目錄。
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

### 3.4 通用電路拓撲資料結構契約與建構器規範 (Universal Circuit Topology Contract & Builder)

為了讓前端能夠對任意硬體電路進行標準 EDA 原理圖風格的拓撲視覺化（包含差分信號、單根信號、上拉電阻至電源軌、接地濾波電容/TVS 等），DesignShield 實施**純圖論通用拓撲合約**，伴生腳本需在 `evidence["topology"]` 輸出符合 `UniversalTopologyData` 規格的資料結構。

推薦優先使用 SDK 提供的高階通道模型（`channel = graph_api.get_differential_channel(...)` 或 `graph_api.get_single_ended_channel(...)`），透過呼叫 `channel.to_topology()` 一鍵生成標準拓撲，大幅減少手動連線組裝的複雜度。若有特殊客製化拓撲需求，亦可直接使用底層流式建構器 `TopologyGraphBuilder`。

#### 1. 資料結構 Schema 定義

```typescript
interface UniversalTopologyData {
  title: string                          // 通道標題 (如 "TJ1 ↔ TU1 (USB 差分通道)")
  channel_type: 'single' | 'differential' | 'bus' // 信號類型
  rails: {
    id: string                           // 軌道 ID (如 "main", "p_rail", "n_rail", "scl")
    name: string                         // 顯示名稱 (如 "正極軌道 (P)")
    polarity?: 'P' | 'N' | null          // 極性標記
  }[]
  nodes: {
    id: string                           // 唯一識別 ID (通常為 ref_des)
    ref_des: string                      // 位號 (如 "TU1", "R1", "C1")
    category: string                     // 元件類型 ("IC" | "Connector" | "Resistor" | "Capacitor" | ...)
    role: 'terminal' | 'series' | 'pull_up' | 'pull_down' | 'shunt_ground' | 'bridge'
    part_number?: string                 // 零件型號 (可選)
    value?: string                       // 規格標稱值 (如 "4.7kΩ", "0.1µF")
    pins: {
      pin_number: string                 // 實體引腳編號 (如 "1", "2", "A6")
      pin_name?: string                  // 功能名稱 (如 "DP1", "SCL", "VCC")
      orientation?: 'left' | 'right' | 'top' | 'bottom' // 連線朝向
    }[]
  }[]
  connections: {
    net_name: string                     // 網段名稱 (如 "USB8_USB20_P")
    rail_id: string                      // 所屬軌道 ID
    from_node: string                    // 起點節點 ID
    from_pin: string                     // 起點引腳編號
    to_node: string                      // 終點節點 ID
    to_pin: string                       // 終點引腳編號
    is_branch?: boolean                  // 是否為垂直分支 (上拉/接地)
  }[]
  metadata?: Record<string, any>         // 補充數據 (如對稱性檢驗結果)
}
```

#### 2. 元件電氣角色 (`role`) 規範

| 角色 (`role`) | 適用元件情境 | 排版與幾何行為 | 電氣符號行為 |
| :--- | :--- | :--- | :--- |
| `terminal` | 核心 IC、主控晶片、外部連接器 (Connector) | 位於水平主幹首尾兩側，雙軌時垂直跨軌對齊 | 左右兩側邊界渲染微型實體 Port 方塊 |
| `series` | AC 耦合電容、串聯匹配電阻、共模扼流圈 (CMC) | 位於水平主幹中間，左右進出直通穿透 | 左右兩側邊界渲染 In/Out Port 方塊 |
| `pull_up` | I2C / RESET / 匯流排上拉電阻 | 位於信號線上方，垂直 T 型引出 | 頂部自動掛載 `▲ VCC` 電源電氣符號與電壓名稱 |
| `shunt_ground` | 旁路濾波電容、TVS 靜電保護二極體 | 位於信號線下方，垂直 T 型分流 | 底部自動掛載 `⏚ GND` 標準接地三橫線符號 |
| `pull_down` | 下拉電阻至地 | 位於信號線下方，垂直 T 型下拉 | 底部自動掛載 `⏚ GND` 標準接地三橫線符號 |

#### 3. 三大典型硬體電路實戰範例

##### 範例 A：高速差分通道 (以 USB 差分為例，穿透電容與連接器)

```python
from designshield.sdk import TopologyGraphBuilder

builder = TopologyGraphBuilder(title="TJ1 ↔ TU1 (USB 差分通道)", channel_type="differential")
builder.add_rail("p_rail", "正極軌道 (P)", polarity="P")
builder.add_rail("n_rail", "負極軌道 (N)", polarity="N")

# 1. 加入端點元件 (連接器與 IC)
builder.add_terminal("TJ1", "TJ1", category="Connector", pins=[
    {"pin_number": "B11", "pin_name": "SSRXP1"},
    {"pin_number": "B10", "pin_name": "SSRXN1"}
])
builder.add_terminal("TU1", "TU1", category="IC", pins=[
    {"pin_number": "N12", "pin_name": "PB_TX1_P"},
    {"pin_number": "N13", "pin_name": "PB_TX1_N"}
])

# 2. 加入穿透元件 (AC 耦合電容)
builder.add_series_component("TC13", "TC13", category="Capacitor", value="0.1µF", in_pin="2", out_pin="1")
builder.add_series_component("TC14", "TC14", category="Capacitor", value="0.1µF", in_pin="2", out_pin="1")

# 3. 建立網段連線
builder.add_connection("USB_P", "p_rail", "TJ1", "B11", "TC13", "2")
builder.add_connection("USB_P_C", "p_rail", "TC13", "1", "TU1", "N12")
builder.add_connection("USB_N", "n_rail", "TJ1", "B10", "TC14", "2")
builder.add_connection("USB_N_C", "n_rail", "TC14", "1", "TU1", "N13")

topology_dict = builder.to_dict()
```

##### 範例 B：單根信號上拉電阻 (以 I2C SCL 為例)

```python
from designshield.sdk import TopologyGraphBuilder

builder = TopologyGraphBuilder(title="I2C SCL 匯流排鏈路", channel_type="single")
builder.add_rail("main", "I2C SCL")

# 1. 加入主控 Master 與從屬 Slave 晶片
builder.add_terminal("U1", "U1", category="IC", pins=[{"pin_number": "10", "pin_name": "SCL"}])
builder.add_terminal("U2", "U2", category="IC", pins=[{"pin_number": "5", "pin_name": "SCL"}])

# 2. 加入垂直上拉電阻 (頂部自動連接 +3.3V)
builder.add_pull_up("R1", "R1", power_net="+3.3V", value="4.7kΩ")

# 3. 建立主幹連線與上拉分支 (is_branch=True 會精確打上實體交會焊點)
builder.add_connection("I2C_SCL", "main", "U1", "10", "U2", "5")
builder.add_connection("I2C_SCL", "main", "U1", "10", "R1", "1", is_branch=True)

topology_dict = builder.to_dict()
```

##### 範例 C：串聯電阻與旁路接地濾波 (以 RC 濾波 / TVS 靜電防護為例)

```python
from designshield.sdk import TopologyGraphBuilder

builder = TopologyGraphBuilder(title="信號輸入 RC 低通濾波鏈路", channel_type="single")
builder.add_rail("main", "SIG_IN")

# 1. 首尾端點
builder.add_terminal("J1", "J1", category="Connector")
builder.add_terminal("U1", "U1", category="IC")

# 2. 串聯電阻與垂直接地電容
builder.add_series_component("R1", "R1", category="Resistor", value="100Ω")
builder.add_shunt_ground("C1", "C1", category="Capacitor", value="100pF", gnd_net="GND")

# 3. 建立主幹與接地分流連線
builder.add_connection("SIG_RAW", "main", "J1", "1", "R1", "1")
builder.add_connection("SIG_FILTERED", "main", "R1", "2", "U1", "1")
builder.add_connection("SIG_FILTERED", "main", "R1", "2", "C1", "1", is_branch=True)

topology_dict = builder.to_dict()
```


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

建立 `patterns/level3_rules/<domain>/<rule_name>.yaml`。

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
      component_role: "Pull_up"         # 元件拓撲角色: "Pull_up", "Decoupling", "Series_Resistor" 等
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
建立 `patterns/level3_rules/power/usb_vbus_esd_protection.yaml`：

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
    # script_path 可直接省略，系統自動就近關聯同名伴生腳本
```

### 步驟 3: 選擇檢查模式與撰寫伴生腳本 (Companion Script SOP)

#### 模式選用準則 (Architecture Decision):
* **全面採用伴生 Python 腳本 (`python_script`，首選標準):**
  * 凡涉及**電路物理量量測** (阻值、電容耐壓、電壓推導)、**多節點與拓撲關聯追蹤** (如尋找上拉電阻連接至哪條供電軌)、**PartDB 規格書查表**，或**需要記錄詳細確認佐證資訊 (Evidence Trail)** 者，**100% 採用伴生 Python 腳本**。
* **靜態拓撲斷言 (`topology_check`，僅限極簡屬性):**
  * 僅限於**零計算、純單一節點布林屬性比對** (例如 `power_ground_short_fatal` 檢查節點是否同時具有 `is_power` 與 `is_ground`)。引擎已清理所有寫死的特化原語 (如 `has_pullup_resistor`)，未來不再為核心引擎擴充特定硬體特徵。

#### 伴生腳本範本 (以結構化審計佐證為例):
建立同目錄同名伴生腳本 `patterns/level3_rules/<domain>/<rule_name>.py`：

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

#### 3.3 端到端通道追蹤與靜默去重契約 (End-to-End Channel Tracing & Deduplication)
針對高速差分匯流排（如 USB、PCIe、Ethernet）或含串聯中繼元件之鏈路，為避免每個中繼網段（如 `USB8_USB20_P` 與穿透 CMC 後的 `USB8_USB20_CMC_P`）各自發出割裂且重複的檢查卡片，引擎提供端到端通道審計與契約驅動去重機制：

1. **端到端穿透能力 (`GraphAPI.trace_differential_end_to_end`):**
   * **2-pin 串聯被動元件穿透:** 自動穿越串聯阻尼電阻 (`Resistor`) 與交流耦合電容 (`Capacitor`)。
   * **4-pin 共模扼流圈 (CMC) 配對穿透:** 針對具備 4 根引腳之 CMC（如 TL1、FL1），依據差分線圈繞組自動進行引腳對應穿透（預設直通型 Pin 1 ⟷ Pin 4 與 Pin 2 ⟷ Pin 3，並預留 PartDB pin mapping 覆寫介面）。
   * **穿透安全性守衛:** 嚴禁穿透至 `is_power` 或 `is_ground` 網路（對地電容、上拉/下拉電阻絕不可穿越），並自動濾除非電氣件（螺絲孔、對位點），確保審計路徑忠實沿著實體訊號鏈行進。
2. **契約驅動之靜默去重 (Contract-Driven Opt-in Deduplication):**
   * **零業務硬編碼:** 核心引擎不寫死特定規則名稱，由伴生腳本在審計完成後自主於 `RulePass` 或 `RuleViolation` 中宣告 `covered_nets: List[str]`（包含本通道涵蓋之所有正負端中繼網段）。
   * **動態靜默略過:** Level 3 Runner 在執行期間動態將 `covered_nets` 納入已訪問集合，當後續中繼網段作為 target 觸發相同規則時，引擎將**靜默跳過**，確保同一條實體通道僅產出一筆完整審計報表。
   * **未宣告不受影響:** 未聲明 `covered_nets` 的常規規則（如單網段 I2C、電源軌規則）維持原運作模式，100% 向後相容。
3. **報表呈現標準:**
   * **卡片標題:** 展現通道頭尾核心節點與主通道名稱（例如 `P72 ↔ TJ1 (USB8_USB20 差分通道)`）。
   * **副標標註:** 標記途中穿透元件（例如 `途經 TL1 共模扼流圈 (CMC)`）。
   * **展開歷程:** 於 `evidence` 提供 `p_path_segments` 與 `n_path_segments`，前端自動渲染直觀的段落拓撲歷程徽章鏈。



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

---

## 6. 硬體語意圖譜重構與角色解耦規範 (Hardware Semantic Graph & Role Decoupling)

DesignShield 採用 **方案 A：正交領域與角色解耦架構**，徹底解決「元件拓撲角色」與「網路訊號特性」之間的語意混淆與過度設計問題。

### 6.1 節點屬性正交分工模型 (Orthogonal Node Attributes)

在知識圖譜（Knowledge Graph）中，元件節點與網路節點具有嚴格正交的屬性分工：

| 節點類型 | 核心屬性 | 允許數值範例 | 來源層級 | 職責與定義 |
| :--- | :--- | :--- | :--- | :--- |
| **Component** | `component_role` | `Pull_up`, `Pull_down`, `Series_Resistor`, `AC_Coupling_Capacitor`, `Decoupling`, `Bus_Master`, `Bus_Slave` | Level 1 初始辨識<br>Level 2 拓撲動態覆寫 | **元件在電路拓撲中的角色**。由 Level 1 依料號/數值指派基礎角色，再由 Level 2 根據連接之網路拓撲升級為專屬語意角色。 |
| **Net** | `net_type` | `Differential`, `Power`, `Ground`, `Signal`, `Clock`, `Reset` | Level 2 (signals/buses/power) | **網路物理與電氣傳輸特性**。正交互斥，純粹描述訊號之實體特性。 |
| **Net** | `bus_type` | `USB`, `I2C`, `SPI`, `UART`, `PCIe`, `None` | Level 2 (buses) | **通訊協定或匯流排標準**。指涉該網路屬於哪種匯流排領域。 |
| **Net** | `diff_polarity` | `P`, `N` | Level 2 (signals - 600_differential_pair) | **差分訊號極性**。正端 (`P`) 或負端 (`N`)。 |
| **Net** | `diff_partner` | 例如 `USB_D-`, `PCIE_TX_N` | Level 2 (signals - 600_differential_pair) | **配對差分網路名稱**。記錄其正負端配對之另一側網路。 |

> [!IMPORTANT]
> **Net 節點嚴禁包含 `functional_role` 或 `component_role`：**
> 網路節點（Net）純粹由 `net_type`（物理特性）與 `bus_type`（協定領域）定義，不再重複打上微觀的 functional role（如 `I2C_SDA` 或 `USB_DP`）。微觀引腳關係交由 Level 2 的比對槽位處理。

---

### 6.2 Level 2 元件角色動態覆寫 (`component_role_overrides`)

在 Level 2 規則中，透過宣告 `component_role_overrides`，可在匯流排或差分訊號成功匹配後，自動將相連的泛用被動元件提升至高階硬體語意角色：

```yaml
# 範例：600_differential_pair.yaml 差分對拓撲元件覆寫
component_role_overrides:
  # 1. 差分訊號走線上串聯之電容，升級為交流耦合電容
  - original_sub_category: "Capacitor"
    connected_to: "Signal"
    new_role: "AC_Coupling_Capacitor"
  # 2. 差分走線上串聯之電阻，升級為阻抗匹配串聯電阻
  - original_sub_category: "Resistor"
    connected_to: "Signal"
    new_role: "Series_Resistor"

# 範例：700_i2c.yaml 匯流排元件覆寫
component_role_overrides:
  # 上拉至供電軌之電阻，精確標記為 I2C 上拉電阻
  - original_sub_category: "Resistor"
    connected_to: "Power"
    new_role: "Pull_up"
```

* **引擎行為**：`TopologyPatternEngine` 在辨識出匯流排或訊號後，搜尋所有與其相連的元件；若元件之 `sub_category` 與連接對象符合條件，其 `component_role` 屬性會被升級為 `new_role`。
* **雙向相容保證**：後端資料模型與 GraphAPI 同時支援雙向相容（優先讀取 `component_role`，向後相容回退 `functional_role`），以確保平滑遷移。

---

### 6.3 規則比對槽位識別碼哲學 (Pattern Slot Key)

在 Level 2 的 YAML 規則中，`signals[*].role` 僅作為**內部比對的槽位識別碼 (Pattern Slot Key)**，用於電氣連接約束與關聯檢查：

* **匯流排規則（多訊號約束）**：例如 I2C 中的 `role: "SCL"` 與 `role: "SDA"`，供引擎識別哪些引腳必須同時存在或互聯。
* **單一訊號規則（Single Signal Pattern）**：例如電源致能（`role: "ENABLE"`）或單一差分線（`role: "P"` / `role: "N"`），`role` 僅為該組件在 YAML 內部的占位符號。
* **槽位不外洩原則**：`signals[*].role` 純粹在比對演算法期間發揮作用，**絕不會作為節點屬性洩漏或寫入圖譜之 Net 節點**。網路節點的識別屬性統一依據 `bus_type`、`net_type` 及推導結果。

---

### 6.4 差分對極性與夥伴網路宣告式推導 (`pair_derivation`)

為免除將特定硬體規則硬編碼在 Python 主程式中，差分訊號規則（`patterns/level2_topology/signals/600_differential_pair.yaml`）採用宣告式 `pair_derivation` 結構：

```yaml
pair_derivation:
  # 1. 極性判斷正則
  positive_pattern: '(?i)(?:_P(_|$)|AUXP(_|$)|_DP(_|$)|(?:_|\b)D\+(_|$))'
  negative_pattern: '(?i)(?:_N(_|$)|AUXN(_|$)|_DN(_|$)|(?:_|\b)D\-(_|$))'
  # 2. 夥伴網路名稱置換映射矩陣 (正端 ⟷ 負端)
  partner_swap_rules:
    - ["_DP", "_DN"]
    - ["_P", "_N"]
    - [".P", ".N"]
    - ["D+", "D-"]
    - ["+", "-"]
```

* **動態推導機制**：當 `net_type` 命中 `Differential` 時，`TopologyPatternEngine._derive_differential_properties()` 會讀取該規則的 `pair_derivation` 區塊，自動將正端與負端推導出 `diff_polarity`（`P` 或 `N`），並計算出對應的 `diff_partner` 網路名稱，儲存至圖譜節點中。
* **Level 3 DRC 簡約化**：在 Level 3 規則（例如 `usb_pn_swap_check`）中，只需以 `net_type: "Differential"` 與 `diff_polarity: "P"` 作為觸發條件，即可由正端主導並透過 `target.diff_partner` 同時獲取負端網路進行端到端審計，實現雙端合一檢查與乾淨去重。

