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
│   ├── 730_usb_typec.yaml
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
| `enabled` | `boolean` | 否 | 是否啟用該規則 (預設 `true`) |
| `category` | `string` | **是** | 拓撲分類領域 (如 `Communication`, `Power`, `Signal`) |
| `priority` | `integer` | **是** | 優先權整數 (數字愈大愈早評估，降冪排序) |
| `signals` | `list` | **是** | 該拓撲領域定義之各訊號角色比對條件清單 |
| `pair_derivation` | `object` | 否 | 差分對正負極性推導規則 (差分信號專用) |

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
      match_any:                      # OR 條件清單 (各分支計算信心加分)
        - match_all:                  # AND 條件分支
            - pin_name_regex: "(?i)SCL(K)?"
            - net_name_regex: "(?i)(I2C|IIC|SMBUS|SML).*SCL"
          confidence_contribution: 0.5 # 命中時貢獻之信心權重 (預設 0.3)
        - match_all:
            - pin_name_regex: "(?i)SCL(K)?"
          confidence_contribution: 0.3
```

### 支援的比對屬性

- `pin_name_regex`: IC / 連接器端點引腳名稱正規表示式 (例如 `(?i)SCL|SCLK`, `(?i)DP1|DP2`)。
- `net_name_regex`: 網路線路名稱正規表示式 (例如 `(?i)^\\+?3V3`, `(?i)USB.*_DP`)。
- `confidence_contribution`: 命中該分支時對該訊號角色的累積信心得分。

---

## 5. 差分對推導語法 (`pair_derivation`)

為免除將特定硬體規則硬編碼在 Python 主程式中，差分訊號規則（如 `600_differential_pair.yaml`）支援宣告式極性與對偶推導：

```yaml
pair_derivation:
  p_suffix: ["_P", "_DP", "+"]
  n_suffix: ["_N", "_DN", "-"]
  rules:
    - suffix_pattern: "(.*)_(P|DP|\\+)$"
      replace_target: "\\1"
```

1. **極性辨識:** 自動依 `p_suffix` 與 `n_suffix` 判定差分極性 (`P` 或 `N`)。
2. **基底名稱提取:** 透過 `rules` 將後綴去除，產出對偶配對之群組基底名稱 (Base Net Name)。
3. **對偶配對:** 引擎自動在同一對偶基底名稱下尋找成對之 `P` 與 `N` 網路，並建立關聯。

---

## 6. 本地校驗與快取重新編譯

每次新增或修改 Level 2 規則後，請執行統一校驗腳本：

```bash
# 執行規則語法與正規表示式校驗
python3 scripts/validate_rules.py

# 呼叫 API 重新熱載入與快取預熱編譯
curl -X POST http://localhost:8000/api/v1/patterns/reload
```
