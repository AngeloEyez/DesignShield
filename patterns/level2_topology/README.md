# DesignShield Level 2 網路與匯流排拓撲規則開發手冊 (Topology Rules Guide)

本手冊為 DesignShield 系統 **Level 2 網路與拓撲特徵識別 (Network & Topology Classification)** 之正式規格文件。
所有拓撲規則均存放於 `patterns/level2_topology/` 目錄，以宣告式 YAML (IaC) 定義，支援在系統啟動時自動預熱編譯正規表達式快取，並於圖論分析階段為全圖網段注入語意標籤。

> [!TIP]
> 快速建立新拓撲規則：可直接複製官方標準範本 [`patterns/level2_topology/_template.yaml`](file:///home/gaven/DesignShield/patterns/level2_topology/_template.yaml)。所有以底線 `_` 開頭之檔案會被引擎自動略過。

---

## 1. 核心機制與設計哲學

1. **職責邊界 (Scope & Responsibility):**
   - 依據網段名稱 (`net_name`)、連接晶片/連接器之引腳名稱 (`pin_name`) 與周邊元件角色，識別出：
     - **電源與接地軌 (Power & Ground Rails):** 如 `+3.3V`, `VDD_IO`, `GND`, `AGND`。
     - **通訊匯流排協定 (Bus Protocols):** 如 `I2C`, `SPI`, `UART`, `USB_TypeC`, `JTAG`。
     - **功能與控制訊號 (Functional Signals):** 如 `Differential Pair` (差分對), `Power Control`, `Clock`, `LED`, `GPIO`。
   - 識別結果直接標註於圖論節點之 `net_type`, `bus_type`, `power_rail`, `diff_polarity` 等屬性，作為後續 Level 3 DRC 檢驗的主要依據。
2. **多維度解耦匹配 (Multi-Domain Decoupled Matching):**
   - 引擎評估網段時，針對接地 (GND)、電源 (PWR)、通訊匯流排 (BUS) 與功能訊號 (SIG) 四大領域獨立評估最佳規則，彼此解耦互不搶佔。
3. **全自動遞迴探索 (Recursive Auto-Discovery):**
   - 引擎使用 `os.walk` 遞迴掃描 `patterns/level2_topology/` 下**所有子目錄**。
   - 工程師可自由依功能領域劃分子資料夾（如 `buses/`, `power/`, `signals/`, `rf/`, `automotive/` 等），新目錄與新 YAML 檔案即放即用，無須手動註冊。
4. **命名規範與範本忽略:**
   - 規則名稱 `name` 必須符合小寫蛇形命名規範 (`snake_case`，如 `i2c_bus`, `generic_power_rail`)。
   - 以底線 `_` 開頭的檔案（如 `_template.yaml`）會被引擎自動略過。

---

## 2. 目錄架構建議

官方推薦的一級子目錄組織架構如下：

```text
patterns/level2_topology/
├── _template.yaml          # 官方超級範本 (引擎自動略過)
├── README.md               # 本開發手冊
├── buses/                  # 通訊匯流排協定
│   ├── 700_i2c.yaml
│   ├── 710_spi.yaml
│   ├── 720_jtag.yaml
│   ├── 730_typec.yaml
│   ├── 730_usb2.yaml
│   ├── 735_usb3_superspeed.yaml
│   └── 740_uart.yaml
├── power/                  # 電源與接地軌規則
│   ├── 900_generic_power.yaml
│   └── 950_generic_gnd.yaml
└── signals/                # 差分對與功能控制訊號
    ├── 500_power_control.yaml
    ├── 510_clock_crystal.yaml
    ├── 520_led_status.yaml
    ├── 530_analog_sense.yaml
    ├── 540_gpio.yaml
    └── 600_differential_pair.yaml
```

---

## 3. 規則 YAML 綱要 (`TopologyRule`)

每個 Level 2 規則檔案包含以下頂層欄位：

| 欄位名稱 | 型別 | 必填 | 說明 |
| :--- | :--- | :---: | :--- |
| `name` | `string` | **是** | 規則唯一識別碼，必須符合小寫蛇形 (`snake_case`) |
| `bus_type` | `string` | 否 | 匯流排協定類型 (當 `category == 'Bus'` 時明文指定，如 `I2C`, `SPI`, `USB2`, `USB3`, `TYPEC`, `UART`, `JTAG`) |
| `enabled` | `boolean` | 否 | 是否啟用該規則 (預設 `true`) |
| `category` | `string` | **是** | 拓撲分類領域，**必須於 `category.schema.json` 白名單中定義** (如 `Bus`, `Power`, `GND`, `Differential`, `Control`, `Clock`, `Analog`) |
| `priority` | `integer` | **是** | 優先權整數 (數字愈大愈早評估，降冪排序) |
| `signals` | `list` | **是** | 該拓撲領域定義之各訊號角色比對條件清單 |
| `component_role_overrides` | `list` | 否 | 拓撲元件角色動態覆寫清單 (將相連被動元件升級為高階語意角色) |
| `pair_derivation` | `object` | 否 | 差分對正負極性推導規則 (僅受 `category: "Differential"` 驅動) |
| `extra_fields` | `object` | 否 | 額外欄位推論規則 (如電壓提取 `parse_voltage_from_name` 或覆寫 `bus_type`) |

### 3.1 優先級配置原則 (Priority Guidelines)

- `900 ~ 999`: 電源與接地軌 (Generic Power / GND，全圖最優先鎖定)
- `700 ~ 899`: 專用通訊匯流排 (USB, PCIe, I2C, SPI)
- `500 ~ 699`: 差分對推導與功能控制訊號 (Differential, Clock, Reset, Power Enable)

---

## 4. 訊號角色的條件比對 (`signals`)

每個訊號物件定義一個特定的訊號角色 (如 `SCL`, `SDA`, `CLK`, `TX`, `RX`)：

```yaml
signals:
  - role: "SCL"                       # 訊號角色代碼
    required: true                    # 是否為成立該拓撲之必備訊號 (若必備訊號缺失則匯流排不成立)
    group_key: true                   # 是否作為匯流排群組分群金鑰 (避免不同通道交叉混淆)
    matches:
      match_any:                      # OR 條件清單
        - match_all:                  # AND 條件分支
            - pin_name_regex: "(?i)SCL(K)?"
            - net_name_regex: "(?i)(I2C|IIC|SMBUS|SML).*SCL"
        - match_all:
            - pin_name_regex: "(?i)SCL(K)?"
```

### 支援的比對屬性

- `pin_name_regex`: IC / 連接器端點引腳名稱正規表示式 (例如 `(?i)SCL|SCLK`, `(?i)DP1|DP2`)。
- `net_name_regex`: 網路線路名稱正規表示式 (例如 `(?i)^\\+?3V3`, `(?i)USB.*_DP`)。

---

## 5. 規則參數在整體程式邏輯中的角色與影響 (Parameter Execution Roles & Runtime Impact)

Level 2 規則並非單純的文字比對，而是深度驅動後端三大引擎（`TopologyPatternEngine`、`NetClassifier`、`Level3Engine`）與前端抽屜的核心設定檔。以下詳細解析各參數在運行時的具體邏輯作用：

### 5.1 `name` (規則識別碼)
- **程式碼角色**: 規則的全域唯一小寫蛇形識別碼（如 `i2c_bus`, `usb2_bus`, `typec_bus`, `generic_gnd`）。
- **具體影響**:
  1. **證據鏈審計追蹤**: 當網路命中規則時，引擎會自動在圖譜節點的 `evidence` 清單中注入 `bus_rule:<name>` 或 `rule:<name>`，供 Step 2 抽屜與調試日誌精確還原命中歷程。

### 5.2 `bus_type` (匯流排協定類型)
- **程式碼角色**: 標註於圖譜節點之通訊協定識別標籤（如 `I2C`, `SPI`, `USB2`, `USB3`, `TYPEC`, `UART`, `JTAG`）。
- **具體影響**:
  1. **明文定義寫入**: 當網路命中 `category == "Bus"` 規則時，引擎直接將此欄位寫入節點之 `net_data["bus_type"]` 屬性中，免除模糊字串推導，維持最高可維護性。
  2. **驅動下游 Level 3 DRC**: 下游規則（如 `pn_swap_check.yaml`）以 `bus_type: ["USB2", "USB3"]` 進行精確快篩觸發。

### 5.3 `category` (拓撲分類領域，受 `category.schema.json` 約束)
- **程式碼角色**: 系統之**「領域路由器 (Domain Router)」**。
- **具體影響**:
  1. **正交領域分流與互斥**: 
     - `category == "Power"` $\rightarrow$ 驅動供電軌路由，標註 `is_power = True`。
     - `category == "GND"` $\rightarrow$ 驅動接地軌路由，標註 `is_ground = True`。
     - `category == "Bus"` $\rightarrow$ 驅動通訊匯流排路由，要求所有必備訊號 (`required: true`) 命中，標註 `is_bus = True`。
     - `category in ["Differential", "Control", "Clock", "Analog"]` $\rightarrow$ 驅動功能訊號路由。
  2. **實體屬性寫入**: 當命中功能訊號時，引擎直接執行 `net_data["net_type"] = rule.category`。
  3. **驅動專屬引擎**: 當且僅當 `category == "Differential"` 時，引擎才會觸發 `_derive_differential_properties()` 進行正負極性推導。
  4. **單一真實來源 (SSOT)**: 所有 category 必須登記於 `patterns/level2_topology/category.schema.json`，並透過 API `GET /api/v1/patterns/level2-categories` 供前後端動態載入。

### 5.3 `priority` (執行優先級)
- **程式碼角色**: 降冪排序評估佇列的優先權數值。
- **具體影響**:
  - 數值愈高愈早執行（如電源 900+ 最先鎖定）。
  - 在同一領域內實施**「搶先獨占 (Preemptive Exclusivity)」**：高優先級規則命中後，低優先級同領域規則直接被跳過（如 Priority 730 的 USB 命中後，Priority 700 的規則不再評估該網路）。

### 5.4 `signals[*].role` (內部槽位代碼)
- **程式碼角色**: 僅作為規則內部比對的**「槽位識別碼 (Pattern Slot Key)」**（如 `SCL`, `SDA`, `USB_DP`, `Differential_Pair`）。
- **具體影響**:
  - **槽位不外洩原則**: 此值純粹在比對演算法期間發揮作用，**絕不**寫入圖譜之 Net 節點，維持網路屬性與微觀角色的徹底解耦。

### 5.5 `signals[*].required` 與 `group_key`
- **程式碼角色**: 匯流排完整性約束與分群鍵。
- **具體影響**:
  - `required: true` 要求該訊號角色必須在該電路拓撲中存在，否則匯流排不成立。
  - `group_key: true` 代表該訊號線可作為實體匯流排通道的分群依據（例如 USB_DP 與 USB_DM 依相同通道後綴分群）。

### 5.6 `signals[*].matches` (確定性條件比對)
- **程式碼角色**: 宣告式特徵匹配條件。
- **具體影響**:
  - `match_any`: 只要任一分支成立即命中（邏輯 OR）。
  - `match_all`: 該分支內所有條件必須同時成立（邏輯 AND）。
  - 全面採用 100% 確定性匹配，移除舊版浮點數 `confidence_contribution` 加權累計機制。引腳與網路名稱正則均嚴格收斂至協定專屬特徵，避免跨協定污染。

### 5.8 `component_role_overrides` (元件拓撲角色動態覆寫)
- **程式碼角色**: 拓撲後處理觸發器。
- **具體影響**:
  - 當該網路成功識別後，引擎自動搜尋所有相連的被動元件（如電容、電阻）；若其原本角色與連接條件相符，自動將元件升級為高階硬體語意角色（例如串聯在差分線上的電容升級為 `AC_Coupling_Capacitor`，上拉至電源軌的電阻升級為 `Pull_up`）。

### 5.9 `pair_derivation` (差分極性與夥伴推導)
- **程式碼角色**: 差分物理特性推導模型（僅在 `category == "Differential"` 生效）。
- **具體影響**:
  - 讀取 `positive_pattern` 與 `negative_pattern`，為網路節點打上 `diff_polarity: "P"` 或 `"N"`。
  - 執行 `partner_swap_rules` 字串置換矩陣，以 $O(1)$ 時間複雜度計算出配對夥伴網路名稱並寫入 `diff_pair_partner`，供下游 Level 3 執行端到端差分審計。

### 5.10 `extra_fields` (動態欄位注入)
- **程式碼角色**: 執行期動態運算與欄位注入。
- **具體影響**:
  - 若設定 `infer_strategy: "parse_voltage_from_name"`，引擎會自動從網路名稱（如 `+1.8V_AUX`, `VCC3P3`）中解析出數值電壓（`1.8`、`3.3`），注入節點的 `operating_voltage` 屬性。

---

## 6. 差分對推導語法 (`pair_derivation`)

為免除將特定硬體規則硬編碼在 Python 主程式中，差分訊號規則（如 `600_differential_pair.yaml`）支援宣告式極性與對偶推導：

```yaml
pair_derivation:
  positive_pattern: '(?i)(?:_P(_|$)|AUXP(_|$)|_DP(_|$)|(?:_|\b)D\+(_|$))'
  negative_pattern: '(?i)(?:_N(_|$)|AUXN(_|$)|_DN(_|$)|(?:_|\b)D\-(_|$))'
  partner_swap_rules:
    - ["_P_", "_N_"]
    - ["_P$", "_N$"]
    - ["_DP_", "_DN_"]
    - ["_DP$", "_DN$"]
    - ["D+$", "D-$"]
```

1. **極性辨識:** 自動依 `positive_pattern` 與 `negative_pattern` 判定差分極性 (`P` 或 `N`)。
2. **夥伴置換推導:** 透過 `partner_swap_rules` 置換正負端後綴，產出互補夥伴網路名稱儲存至圖譜。

---

## 7. 本地校驗與快取重新編譯

每次新增或修改 Level 2 規則後，請執行統一校驗腳本：

```bash
# 執行規則語法與正規表示式校驗 (同時驗證 category.schema.json 白名單)
python3 scripts/validate_rules.py

# 呼叫 API 重新熱載入與快取預熱編譯
curl -X POST http://localhost:8000/api/v1/patterns/reload
```
