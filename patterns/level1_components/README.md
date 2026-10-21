# DesignShield Level 1 元件分類規則開發手冊 (Component Rules Guide)

本手冊為 DesignShield 系統 **Level 1 元件靜態特徵分類 (Component Classification)** 之正式規格文件。
所有元件分類規則均儲存於 `patterns/level1_components/*.yaml`，以宣告式 YAML (IaC) 定義，支援在系統啟動時自動預熱編譯正規表達式快取，並於執行期提供高效能的毫秒級推論。

> [!TIP]
> 快速建立新規則：可直接複製官方標準範本 [`patterns/level1_components/_template.yaml`](file:///home/gaven/DesignShield/patterns/level1_components/_template.yaml)。所有以底線 `_` 開頭之檔案會被引擎自動略過。

---

## 1. 核心機制與設計哲學

1. **職責邊界 (Scope & Responsibility):**
   - 將線路圖解析出之原始靜態元數據 (RefDes、標稱值、描述、封裝、原廠料號、引腳數、BOM 狀態、CAD 自訂屬性) 映射為結構化的標準分類 (`category`、`sub_category`) 與基礎拓撲角色 (`component_role` / `functional_role`)。
   - 優先過濾非電氣件 (`NonElectrical`，如機構螺絲、螺絲孔、光學對位點、測試點)，確保後續 Level 2 與 Level 3 DRC 不受無關金屬實體干擾。
2. **優先權裁決機制 (Priority & First-Match Wins):**
   - 所有規則依 `priority` 由大到小 (降冪) 依序評估。
   - **首個完全命中 (First-Match) 的規則即為最終分類結果**，立即終止後續較低優先權規則的比對。
   - 優先級配置原則：
     - `980 ~ 999`: 非電氣件阻斷 (光學點、機構孔、測試點，最優先剔除)
     - `900 ~ 979`: 高階 IC、主控晶片 (MCU/CPU/SoC)、連接器
     - `800 ~ 899`: 專用主動/被動元件 (TVS、CMC、電晶體、電容、電阻)
     - `500 ~ 799`: 通用後備猜測規則 (如依 `U` 前綴猜測 IC)
3. **檔案存放規範:**
   - YAML 檔案必須**直接存放於 `patterns/level1_components/` 目錄第一層** (不支援子目錄)。
   - 單一 `.yaml` 檔案內可使用標準 YAML 分隔符號 `---` 宣告多個規則文件。

---

## 2. 規則根欄位綱要 (`ComponentRule`)

每一份規則文件的頂層結構如下：

| 欄位名稱 | 型別 | 必填 | 預設值 | 說明 |
| :--- | :--- | :---: | :---: | :--- |
| `name` | `string` | **是** | - | 唯一規則識別碼，必須符合小寫蛇形命名規範 `rule_<category>_<sub_category>[_<detail>]` |
| `description` | `string` | 否 | `""` | 規則說明與工程語意備註 (繁體中文) |
| `priority` | `integer` | **是** | - | 優先級整數 (數字愈大愈早評估，建議範圍 500 ~ 999) |
| `enabled` | `boolean` | 否 | `true` | 是否啟用該規則。設為 `false` 時引擎評估自動略過 |
| `matches` | `object` | **是** | - | 條件比對物件 (`MatchCondition`)，定義何種元件特徵視為命中 |
| `assigns` | `object` | **是** | - | 屬性賦值物件 (`AssignData`)，定義命中後指派之分類與角色 |
| `type` | `string` | 否 | `"pattern_match"` | 規則類型標記 |
| `script_path`| `string` | 否 | 同目錄同名 `.py` | 伴生 Python 腳本路徑，若存在則於比對成功後進入沙盒深度解碼 |

---

## 3. 通用條件比對語法 (`matches` / `MatchCondition`)

DesignShield 採用 **屬性鍵值運算子映射 (Key-Operator Map)** 架構，允許工程師針對任意標準屬性或 CAD 擴充屬性，靈活組合精確相等、正則表達式、集合包含、前後綴或數值區間比對。

### 3.1 邏輯組合樹 (`match_all` 與 `match_any`)

- `match_all: List[ConditionNode]`：**AND 邏輯**。列表中所有子條件都必須成立，整體才算命中。
- `match_any: List[ConditionNode]`：**OR 邏輯**。列表中只要有任一子條件成立，整體即算命中。
- **同層級多屬性隱式 AND**：在同一個物件內宣告的多個屬性條件，彼此之間視為 AND 關係。

```yaml
matches:
  match_all:
    - bom: "NOBOM"                 # 條件 1: 必須滿足 BOM=NOBOM
    - match_any:                   # 條件 2: 且以下特徵至少命中一項
        - description: { regex: "(?i)TEST" }
        - part_value: { regex: "(?i)PROBE" }
```

---

### 3.2 支援比對之元件屬性清單

在條件節點中，可以直接使用以下標準屬性名稱作為鍵 (Key)：

| 屬性名稱 (`attr_name`) | 型別 | 說明與範例 |
| :--- | :--- | :--- |
| `ref_des` | `string` | 元件位號，如 `R1`, `C12`, `U4`, `TP56` |
| `part_value` | `string` | 元件標稱值或型號，如 `10K`, `0.1uF`, `TEST_POINT_0` |
| `description` | `string` | 元件規格描述，如 `CAP,100nF,50V`, `RES,10K Ohm,1%` |
| `package` | `string` | 封裝型態或 PCB Footprint，如 `0402`, `SOIC-8`, `USBC` |
| `mfg_pn` | `string` | 製造商零件料號，如 `DLM0NSN900HY2D`, `STM32F405` |
| `mfg` | `string` | 製造商/原廠名稱，如 `MURATA`, `TI`, `SENSIRION` |
| `pins_count` | `integer`| 元件實體引腳總數量，如 `2`, `4`, `16`, `100` |
| `bom` | `string` | BOM 上件代碼，如 `NOBOM`, `I`, `NI`, `X`, `PROTO` (自動追溯 `raw_bom` 與 `user_props["BOM"]`) |
| `any_text` | `string` | **虛擬全文合成欄位**，引擎自動串接 `f"{part_value} {mfg_pn} {description} {package}"` |
| `props.<key>`<br>`user_props.<key>` | `any` | **任意 CAD/CIS 擴充屬性**。例如 `props.CCL: "N"`, `props.Side: "TOP"`, `props.Tolerance: "1%"` |

> [!NOTE]
> 若指定之屬性名稱非上述標準欄位，引擎會自動回退檢查 `comp_data["user_props"]` 中是否存在同名屬性。

---

### 3.3 運算子完整規格表 (Operators Specification)

每個屬性可指定為**運算子字典**，或使用**簡寫純值**。

| 運算子 (`op`) | 支援型別 | 說明與行為 | 範例語法 |
| :--- | :--- | :--- | :--- |
| `exact`<br>`eq` | `string`<br>`number` | **完全相等**。字串比對預設大小寫不敏感 (`case-insensitive`)；數值型自動以浮點數相等比對。 | `bom: { exact: "NOBOM" }`<br>`pins_count: { eq: 2 }` |
| `ne` | `string`<br>`number` | **不等於**。上述 `exact` 之反向。 | `bom: { ne: "X" }` |
| `regex` | `string` | **正規表達式比對** (`re.search`)。啟動時自動快取預編譯。推薦在正則中包含 `(?i)` 忽略大小寫。 | `description: { regex: "(?i)\\b(CAP|MLCC)\\b" }` |
| `prefix` | `string` | **前綴比對**。檢查屬性字串開頭是否與指定前綴相符 (預設大小寫不敏感)。 | `description: { prefix: "CAP," }`<br>`ref_des: { prefix: "R" }` |
| `suffix` | `string` | **後綴比對**。檢查屬性字串結尾是否與指定後綴相符 (預設大小寫不敏感)。 | `package: { suffix: "_SMD" }` |
| `in` | `list` | **集合包含**。屬性值只要等於列表中的任意一項即成立。 | `package: { in: ["0402", "0603", "0805"] }` |
| `not_in` | `list` | **集合排除**。屬性值不得存在於所列集合中。 | `bom: { not_in: ["X", "NI"] }` |
| `min`<br>`gte` | `number` | **數值下限 (大於等於)**。檢查屬性數值 $\ge$ 指定門檻。 | `pins_count: { min: 8 }`<br>`pins_count: { gte: 16 }` |
| `max`<br>`lte` | `number` | **數值上限 (小於等於)**。檢查屬性數值 $\le$ 指定門檻。 | `pins_count: { max: 4 }`<br>`pins_count: { lte: 2 }` |
| `exists` | `boolean` | **屬性是否存在且非空**。`true` 代表該屬性存在且值不為 `None`/空字串；`false` 代表不存在或為空。 | `props.CCL: { exists: true }` |
| `case_sensitive` | `boolean` | **大小寫敏感性開關** (預設 `false`)。可放置於運算子字典內覆寫預設行為。 | `ref_des: { exact: "u1", case_sensitive: true }` |

### 3.4 簡寫語法 (Syntactic Sugar)

為了讓 YAML 規則更簡潔優雅，支援以下簡寫：
1. **純值直接賦值 (等同 `exact` / `eq`):**
   ```yaml
   bom: "NOBOM"                 # 完全等同 bom: { exact: "NOBOM" }
   pins_count: 2                # 完全等同 pins_count: { eq: 2 }
   ```
2. **列表直接賦值 (等同 `in`):**
   ```yaml
   package: ["0402", "0603"]    # 完全等同 package: { in: ["0402", "0603"] }
   ```

---

## 4. 屬性指派規範 (`assigns` / `AssignData`)

當 `matches` 條件完全滿足時，引擎會將 `assigns` 區塊宣告的欄位寫入元件解析結果：

| 欄位名稱 | 型別 | 必填 | 允許值與規範 |
| :--- | :--- | :---: | :--- |
| `category` | `string` | **是** | 元件大類：`"IC"`, `"Passive"`, `"Discrete"`, `"Connector"`, `"NonElectrical"`, `"Electromechanical"` |
| `sub_category` | `string` | **是** | 具體子分類，例如：<br>• Passive: `Capacitor`, `Resistor`, `Inductor`, `Choke`, `FerriteBead`<br>• Discrete: `Diode`, `TVS`, `MOSFET`, `Crystal`<br>• IC: `Microcontroller`, `PowerIC`, `Memory`, `LevelShifter`, `InterfaceIC`, `Other`<br>• NonElectrical: `Fiducial`, `MountingHole`, `Mechanical`, `TestPoint`<br>• Connector: `Connector` |
| `component_role`<br>`functional_role` | `string` | 否 | 元件基礎拓撲角色 (預設 `"None"`，系統自動雙向同步)，例如：`"Bus_Master"`, `"Bus_Slave"`, `"Power_Source"`, `"Power_Sink"`, `"Level_Shifter"`, `"Common_Mode_Choke"`, `"Filter"`, `"Protection"`, `"Passive_Support"` |
| `is_electrical` | `boolean` | **是** | 是否具備電氣特性。`NonElectrical` 必須設為 `false`，電氣元件設為 `true` |
| `confidence` | `float` | **是** | 辨識信心度 ($0.0 \sim 1.0$)。若信心度低於 $0.6$ 且開啟 LLM 審核時，將進入待審查佇列 |

---

## 5. Level 1 伴生腳本規範 (`classify(context)`)

若單純的正則與運算子無法滿足複雜的料號解碼需求（例如從製造商料號解算非線性電容耐壓、封裝介質或阻值容差），可建立同目錄同檔名之伴生 Python 腳本（如 `rule_passive_resistor.py`）。

### 5.1 標準入口簽名
```python
from typing import Dict, Any

def classify(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Level 1 伴生腳本入口函式
    
    @param {Dict[str, Any]} context - 元件特徵上下文字典 (包含 ref_des, part_value, description, package, mfg_pn, pins_count, bom, user_props)
    @returns {Dict[str, Any]} 欲擴充或覆蓋之屬性字典
    """
    # 範例：從料號中提取耐壓
    mpn = context.get("mfg_pn", "")
    if "50V" in mpn:
        return {"voltage_v": 50.0}
    return {}
```

---

## 6. 精選實戰 YAML 範例

### 範例 A: 測試點 (TestPoint) 識別規則
要求 `BOM=NOBOM`，且描述或標稱值具備測點關鍵字：
```yaml
name: "rule_nonelectrical_test_point"
enabled: true
description: "測試點、測試探針、測試 Pad (TestPoint)"
priority: 987

matches:
  match_all:
    - bom: "NOBOM"
    - match_any:
        - description: { regex: "(?i)\\b(TEST|TESTPOINT|TEST[\\s_-]*POINT|PROBE)\\b" }
        - part_value: { regex: "(?i)\\b(TEST|TESTPOINT|TEST[\\s_-]*POINT|PROBE)\\b" }
        - any_text: { regex: "(?i)\\b(TEST|TESTPOINT|TEST[\\s_-]*POINT|PROBE|TEST\\s*PROBE|TEST\\s*PAD|TEST\\s*FOR|SIM\\s*TEST|TPC\\d+|DELTAL\\d*)\\b" }

assigns:
  category: "NonElectrical"
  sub_category: "TestPoint"
  functional_role: "None"
  is_electrical: false
  confidence: 0.95
```

### 範例 B: 貼片電容器 (Capacitor) 識別規則
涵蓋前綴精確比對、容值單位比對與 RefDes/引腳數組合：
```yaml
name: "rule_passive_capacitor"
enabled: true
description: "電容器 (Capacitor)"
priority: 850

matches:
  match_any:
    - description: { prefix: "CAP," }
    - any_text: { regex: "(?i)\\b(CAP|CAPACITOR|MLCC)\\b" }
    - part_value: { regex: "(?i)\\b\\d+(\\.\\d+)?(UF|NF|PF)\\b" }
    - match_all:
        - ref_des: { regex: "(?i)^(C|TC|PC)$" }
        - pins_count: { max: 2 }

assigns:
  category: "Passive"
  sub_category: "Capacitor"
  functional_role: "Passive_Support"
  is_electrical: true
  confidence: 0.85
```

### 範例 C: 主控晶片 (Microcontroller / SoC)
支援高引腳數門檻與複合關鍵字：
```yaml
name: "rule_ic_microcontroller"
enabled: true
description: "主控晶片 (MCU/SoC/CPU)"
priority: 900

matches:
  match_any:
    - match_all:
        - description: { prefix: "IC," }
        - any_text: { regex: "(?i)\\b(MCU|MICROCONTROLLER|STM32|ESP32|CPU|SOC|PROCESSOR|BRIDGE|INTEL)\\b" }
    - match_all:
        - pins_count: { min: 16 }
        - any_text: { regex: "(?i)\\b(MCU|PROCESSOR|SOC|BRIDGE|INTEL|CHIPSET)\\b" }

assigns:
  category: "IC"
  sub_category: "Microcontroller"
  functional_role: "Bus_Master"
  is_electrical: true
  confidence: 0.92
```

### 範例 D: CAD 擴充屬性精確匹配
使用 `props.<key>` 比對特定製造商屬性或 CCL 標籤：
```yaml
name: "rule_passive_special_resistor"
enabled: true
description: "特殊無鉛低阻值精密電阻"
priority: 842

matches:
  match_all:
    - ref_des: { prefix: "R" }
    - props.CCL: "Y"
    - props.Tolerance: { in: ["0.1%", "0.5%"] }

assigns:
  category: "Passive"
  sub_category: "Resistor"
  functional_role: "Precision_Resistor"
  is_electrical: true
  confidence: 0.95
```
