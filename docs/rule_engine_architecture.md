# DRC 規則定義與 LLM 協作架構指南 (Rule Definition & LLM Copilot Architecture)

## 1. 緣起與目標
本文件紀錄了 DesignShield 系統在規則引擎 (Rule Engine) 重構與 AI 代理化 (Agentic Architecture) 的核心設計藍圖。
原始的 DesignShield 依賴寫死於 Python (`classifier.py`, `heuristic.py`) 的正則表達式與圖論演算法，雖具備高效能，但缺乏領域專家 (Domain Expert) 維護的彈性。

因此，系統引入 **Pattern Engine** 與 **LLM Copilot** 的雙軌協作機制，達到「效能、可維護性、智能化」三者的平衡。

## 2. LLM 協作邏輯：雙軌制 (Dual-Track Architecture)
系統採用 **「以 DBOS 硬規則為主幹，以 LLM Agent 為智能 Exception Handler」** 的設計模式：
1. **DBOS 主幹 (高速與確定性):** 絕大多數的標準設計 (如明確的 I2C、穩定的電源降額) 由 Pattern Engine 進行本地快速圖譜比對，秒級得出確定性結論。
2. **LLM 備援與互動 (LLM Fallback & Copilot):** 
   - 當系統遇到「無明確規格」、「非標準命名」或圖譜特徵低於信心閥值 (Confidence < 0.6) 時，才喚醒 LLM。
   - LLM 被賦予一組 CLI/API 工具，允許其像 `schematic-analyzer` 一樣，**主動去 NetworkX 圖譜中搜索證據** (例如: 追蹤特定引腳、過濾 Net 名稱)，進行動態深入探索與推理。

## 3. 規則儲存策略：純檔案式 YAML (File-based YAML)
為了兼顧 LLM 讀取能力與人類可維護性，捨棄資料庫，將所有規則 (Patterns) 抽離為硬碟上的 YAML 檔案，並交由 Git 進行版本控制。

**採用 File-based YAML 的優勢:**
* **IaC (Infrastructure as Code):** 規則變更與程式碼版本掛鉤，隨時可 Rollback。
* **豐富註解 (Rich Comments):** 允許領域專家在 YAML 中撰寫大量註解，這不僅幫助工程團隊交接，更能作為 LLM 在動態探索時的強大 Context (上下文)。
* **無狀態 (Stateless):** 後端啟動時直接載入記憶體，免除 DB I/O。

## 4. Pattern YAML 的分類與實體結構設計 (Rule Taxonomy)

為了達到「邏輯縝密」與「實作解耦」，Pattern YAML 嚴格區分為三大層次，並且**拆分成三個獨立的資料夾**以強制解耦，便於多人並行維護：

### Level 1: 零件辨識規範 (`patterns/components/`)
* **職責:** 定義如何透過元件的靜態屬性 (Metadata) 識別出單一零件的類別與角色。注意：本階段只給予**靜態預設角色** (例如 MCU 預設為 Bus_Master)，若零件在特定電路中有特殊角色 (如分壓電阻)，將留待 Level 2 圖譜拓撲分析時覆寫升級。
* **引擎運作邏輯 (First-Match Wins):**
  1. Parser 啟動時讀取所有規則，並依 `priority` (數字越大優先級越高) 降冪排序。
  2. 針對電路圖中的每個零件，由上而下評估 `matches` 條件樹。
  3. 遇到第一個命中 (Evaluate == True) 的規則，立刻套用 `assigns` 分類並跳出 (阻斷後續判斷)。
  4. **Fallback 與 LLM 介入機制:** 若遍歷所有規則皆未命中，引擎將預設返回 `category: Unknown` 與 `confidence: 0.1`。外部呼叫者 (如 `classifier.py`) 在發現零件 `confidence < 0.6` 時，會主動收集這些未知零件並批次發送給 LLM 進行智慧推論。
* **YAML 參數字典 (Schema Reference):**
  * `name` (字串, **必填**): 規則名稱。規範命名為 `rule_<category>_<sub_category>`，例如 `rule_ic_microcontroller`。
  * `description` (字串, 選擇性): 給領域專家與 LLM 閱讀的規則說明註解。
  * `priority` (整數, **必填**): 優先權 (數字越大越先執行)。
    * `900~999`: 絕對特徵 (如明確的機構件或測試點)。
    * `700~899`: 標準前綴與精準特徵匹配。
    * `400~699`: 模糊正則或複合關鍵字比對。
    * `100~399`: 廣泛的字首猜測 (如只憑 `R` 開頭判斷)。
    * **[注意] 優先級允許重複 (Duplicate Priorities):** 系統完全接受多個規則擁有相同的 `priority`。當兩個規則優先級相同時，Parser 會依據檔案載入順序或字母排序來決定誰先執行。因此，**對於彼此互斥 (Mutually Exclusive) 的規則 (例如 MCU 和 電阻)，給予相同的 priority 是完全安全且被鼓勵的**，因為先判斷誰都不影響結果。只有在存在「交集」時 (例如 TVS 也是一種二極體)，才需要特地將 TVS 的 priority 設得比 Diode 高。
    * **[設計模式] 檔名即優先級 (Self-documenting Filenames):** 為了極大化開發者體驗 (DX)，強烈建議 YAML 檔名以該檔案所涵蓋的「最低優先級區間」開頭。例如 `980_non_electrical.yaml` (處理 980~999)、`800_passive_discrete.yaml`。這讓檔案總管的排序自然符合程式的執行順序。
  * `matches` (物件, **必填**): 條件樹。根節點支援 `match_any` (OR) 或 `match_all` (AND)，允許無限巢狀遞迴。其下的葉節點 (Leaf node) 支援以下比對條件：
    * `ref_prefix` (字串): 零件編號開頭字串，例如 `"PU"`, `"R"`。
    * `description_prefix` (字串): 描述開頭字串，例如 `"IC,"`, `"RES,"`。
    * `description_regex` (字串): 描述的正則表達式。
    * `value_regex` (字串): 零件數值的正則表達式。
    * `package_regex` (字串): 封裝/Footprint 的正則表達式。
    * `pin_count_min` / `pin_count_max` (整數): 引腳數量範圍限制。
    * `any_text_regex` (字串): **最常用的模糊搜尋**。Parser 會將 Value, MPN, Description, Package 合併為一條大字串後進行比對，完全相容舊版 `classifier.py` 邏輯。
  * `assigns` (物件, **必填**): 若條件命中，欲賦予該零件的屬性。
    * `category` (字串, **必填**): 主實體類別。必須為以下之一：
      * `IC` (積體電路), `Passive` (被動元件), `Discrete` (分離式主動元件), `Connector` (連接器), `Electromechanical` (機電元件如開關), `NonElectrical` (非電氣機構件)。
    * `sub_category` (字串, **必填**): 實體次分類。**開放擴充但需集中註冊**，避免名詞碎片化 (例如不可同時存在 MCU 與 SoC)。現有註冊清單：
      * IC 類: `Microcontroller`, `PowerIC`, `Memory`, `LevelShifter`, `InterfaceIC`, `Other`
      * 被動類: `Resistor`, `Capacitor`, `Inductor`, `FerriteBead`, `Fuse`
      * 分離類: `Diode`, `TVS`, `MOSFET`, `Crystal`
      * 非電氣: `Fiducial` (對位點), `MountingHole` (螺絲孔), `Mechanical` (散熱片/標籤), `TestPoint` (測試點)
    * `functional_role` (字串, **必填**): 預設邏輯角色。這代表零件對網路/電源的拓撲行為。**嚴格白名單制 (不可隨意擴充)**，以確保 DRC 演算法的穩定性：
      * `Bus_Master`: 匯流排控制端，主動發起訊號 (如 MCU)。
      * `Bus_Slave`: 匯流排受控端，被動接收訊號 (如 Sensor, EEPROM)。
      * `Power_Source`: 產生或轉換電源的源頭 (如 LDO, Buck)。
      * `Protection`: 保護網路免受靜電或過流損害 (如 TVS, Fuse)。
      * `Filter`: 濾除高頻雜訊或穩定電壓 (如 電容, 磁珠)。
      * `Passive_Support`: 一般支撐性元件 (如 上拉/下拉電阻、分壓電阻)。
      * `None`: 訊號穿越或不明確角色 (如 Connector 或未知的 IC)。
    * `is_electrical` (布林, **必填**): 是否為電氣元件。非電氣件在後續圖譜分析中會被隔離，避免干擾連線判定。
    * `confidence` (浮點數, **必填**): `0.0` ~ `1.0`。代表判定準確度，作為是否喚醒 LLM 的基準閥值。指引如下：
      * `0.95 ~ 1.0`: **絕對確定** (多維度特徵吻合，如明確的機構件或完整的規格描述)。
      * `0.80 ~ 0.94`: **具強烈特徵** (如 CAD 標準前綴 `RES,` 搭配合理引腳數)。
      * `0.60 ~ 0.79`: **模糊或單一特徵** (如僅靠單字 `TVS` 或單純 RefDes 字首猜測)。
      * `< 0.60`: **系統判定不可靠**。外部系統會攔截這些元件，強制將其批次送入 LLM 進行複判與救援。
* **Schema 範例 (Recursive Nested Logic):**
  ```yaml
  name: "rule_ic_microcontroller"
  description: "辨識主控晶片 (MCU/SoC/CPU)"
  priority: 900
  
  matches:
    match_any:
      # 條件 A: 描述有明確的 IC 前綴，且任意文字包含特定關鍵字
      - match_all:
          - description_prefix: "IC,"
          - any_text_regex: "(?i)\\b(MCU|MICROCONTROLLER|STM32|ESP32|CPU|SOC|PROCESSOR)\\b"
      # 條件 B: 沒有 IC 前綴，但是引腳數多，且包含關鍵字
      - match_all:
          - pin_count_min: 20
          - any_text_regex: "(?i)\\b(PROCESSOR|SOC)\\b"
  
  assigns:
    category: "IC"
    sub_category: "Microcontroller"
    functional_role: "Bus_Master"
    is_electrical: true
    confidence: 0.92
  ```

### Level 2: 網路、匯流排與功能訊號辨識規範 (`patterns/power/`, `patterns/buses/` 與 `patterns/signals/`)
* **職責:** 將原始的實體連線 (Nets) 昇華為邏輯實體 (Logical Entities，如 I2C1 匯流排實例、3.3V 電源軌、USB 差分對、電源使能訊號)。
* **三大規則目錄職責劃分 (Taxonomy & Shallow Directories):**
  1. **`patterns/power/` (Priority 900~999)**: 全域電源軌與接地網路。透過實體 Symbol 鐵證與正則提取電壓值 (`operating_voltage`)。
  2. **`patterns/buses/` (Priority 700~899)**: 多線標準通訊匯流排。依賴多訊號分組 (`group_key`) 與必備訊號 (`required`) 檢查成團，動態生成邏輯匯流排實例。
  3. **`patterns/signals/` (Priority 500~699)**: 單線功能訊號與差分對。涵蓋電源控制 (Power Control)、時脈晶振 (Clock & Crystal)、狀態指示 (LED & Status)、類比偵測 (Analog Sense)、泛用 GPIO 以及高速/測試差分對 (Differential Pairs)。
* **三合一解析引擎架構 (Triple Engine Architecture):**
  1. **`PowerPattern`**: 處理供電與地線。單一網路，依賴實體 Symbol 綁定與正則電壓數值萃取 (Voltage Extraction)。
  2. **`BusPattern`**: 處理多線介面與通訊匯流排。依賴多條訊號線的「分組匹配 (group_key)」與「必備訊號 (Required Signals)」檢查，將成員訊號成團並實例化 (如 `i2c_1`, `spi_flash`)。
  3. **`SignalPattern`**: 處理單線功能控制線與差分對。支援語意分類、極性自動識別 (`diff_polarity`: P/N) 與夥伴網路名稱 (`diff_pair_partner`) 自動推導。
* **引腳輔助辨識 (Pin-Name Anchoring):** 
  為了防範工程師隨意命名 Net (例如將 I2C 接在 `GPIO_1`)，Pattern 不僅比對網路名稱 (`net_patterns`)，也比對該 Net 所連接的 IC 兩端引腳名稱 (`pin_patterns`)。只要實體引腳名稱 (如 `SDA`, `TX`) 吻合，即視為有效證據，大幅減少幻覺與誤判。
* **動態角色覆寫 (Dynamic Role Override):**
  在 Level 1 中，被動元件皆預設為 `Passive_Support`。Level 2 引擎在成功將 Net 分類成團後，會依據 YAML 的 `role_overrides` 設定，將掛載其上的被動元件升級為具體的拓撲角色 (例如 `Pull_up` 上拉電阻、`Pull_down` 下拉電阻、`AC_Coupling_Capacitor` 交流耦合電容、`Decoupling` 去耦電容)，以利 Level 3 (DRC) 直接取用。
* **Schema 範例 (`BusPattern`):**
  ```yaml
  name: "I2C"
  category: "Communication"
  priority: 700 # 讓 I3C 等更高頻的專用協定 (如 priority 750) 優先執行並消耗訊號
  
  signals:
    - role: "SCL"
      required: true
      group_key: true
      matches:
        match_any:
          # 情境 A：極度明確的 Net 命名 (高信心度)。支援 I2C3, I2CA 等後綴
          - match_all:
              - net_name_regex: "(?i)I2C[a-zA-Z0-9_]*.*(?:SCL|SCK|SCLK|CLK)"
            confidence_contribution: 0.5
            
          # 情境 B：模糊的 Net 命名，但 IC 原廠腳位給了 I2C 鐵證 (中高信心度)
          - match_all:
              - net_name_regex: "(?i)^(?:SCL|SCK|SCLK|CLK)$"
              - pin_name_regex: "(?i)I2C[a-zA-Z0-9_]*"
            confidence_contribution: 0.4
            
          # 情境 C：模糊的 Net 與模糊的 Pin (極低信心度，易觸發 LLM 複判)
          - match_all:
              - net_name_regex: "(?i)^(?:SCL|SCK|SCLK|CLK)$"
              - pin_name_regex: "(?i)^(?:SCL|SCK|SCLK|CLK)$"
            confidence_contribution: 0.1
            
    - role: "SDA"
      required: true
      group_key: true
      matches:
        match_any:
          - match_all:
              - net_name_regex: "(?i)I2C[a-zA-Z0-9_]*.*(?:SDA|SDAT|SDATA|DAT)"
            confidence_contribution: 0.5
          - match_all:
              - net_name_regex: "(?i)^(?:SDA|SDAT|SDATA|DAT)$"
              - pin_name_regex: "(?i)I2C[a-zA-Z0-9_]*"
            confidence_contribution: 0.4
          - match_all:
              - net_name_regex: "(?i)^(?:SDA|SDAT|SDATA|DAT)$"
              - pin_name_regex: "(?i)^(?:SDA|SDAT|SDATA|DAT)$"
            confidence_contribution: 0.1

    - role: "INT"
      # 中斷訊號為選擇性 (非必須)
      required: false
      group_key: true
      matches:
        match_any:
          # 明確帶有 I2C 前綴的中斷線 (支援 INT, INT#, IRQ 等)
          - match_all:
              - net_name_regex: "(?i)I2C[a-zA-Z0-9_]*.*(?:INT#?|IRQ|ALERT)"
            confidence_contribution: 0.2
          # 泛用的中斷線
          - match_all:
              - net_name_regex: "(?i)(?:INT#?|IRQ|ALERT)$"
            confidence_contribution: 0.1
  
  role_overrides:
    # 拓撲邏輯判斷 (Topology-based Override)
    # 若電阻一端接 I2C 訊號，另一端接 Power 類別的網路，則精確升級為 Pull_up
    - original_sub_category: "Resistor"
      connected_to: "PowerRail"
      new_role: "Pull_up"
      
    # 若電阻兩端都接在訊號網路上 (無電源/GND)，判定為串阻
    - original_sub_category: "Resistor"
      connected_to: "Signal"
      new_role: "Series_Resistor"
  ```
* **Schema 範例 (`PowerPattern`):**
  電源網路在系統中不再為個別電壓 (如 3.3V, 5V) 建立專屬規則，而是採用 **單一泛用的 PowerPattern**，透過尋找實體 Power Symbol 或正則關鍵字來確認網路身分，並動態萃取電壓值。
  ```yaml
  name: "Generic_Power_Rail"
  category: "Power"
  priority: 900 # 電源網路必須優先於通訊匯流排執行
  
  signals:
    - role: "VCC"
      required: true
      group_key: false
      matches:
        match_any:
          # 情境 A (最精準)：在解析 XML 時，明確發現此 Net 連接到 Power Symbol
          - match_all:
              - is_power_symbol_connected: true
            confidence_contribution: 0.9
          # 情境 B (退一步)：OrCAD/Cadence 未匯出 Symbol 屬性，但 Net 名稱高度吻合電源前綴
          - match_all:
              - net_name_regex: "(?i)^(?:VCC|VDD|VBUS|VIN|VBAT|VREG|VOUT|VSYS)"
            confidence_contribution: 0.7
          # 情境 C：名稱是純電壓格式 (如 +3.3V, 5V_CORE, 3P3V, 1p85V, +12V_PCM)
          - match_all:
              - net_name_regex: "(?i)^\\+?\\d+(?:\\.\\d+|[VP]\\d+)?V?(?:_.*)?$"
            confidence_contribution: 0.7
            
  extra_fields:
    # 電源網路的公稱電壓值，供 Level 3 (DRC) 計算電容降額使用
    operating_voltage:
      # type: float 代表引擎在萃取出字串 (如 "3.3" 或 "1P85") 後，
      # 會自動將其轉型為浮點數 (3.3 / 1.85)，讓後續的 DRC 規則能直接拿來做數學運算 (如耐壓 > 電壓 * 1.5)
      type: float
      source: "infer"
      infer_strategy: "parse_voltage_from_name" # 透過引擎內建的 extract_operating_voltage_from_net 演算法動態求值
  ```

  **地線網路 (GND)** 同樣採用泛用設計，且不需推算電壓，直接賦予靜態 0.0V：
  ```yaml
  name: "Generic_GND"
  category: "Power"
  priority: 950
  
  signals:
    - role: "GND"
      required: true
      group_key: false
      matches:
        match_any:
          - match_all:
              - is_ground_symbol_connected: true
            confidence_contribution: 0.9
          - match_all:
              - net_name_regex: "(?i)^(?:GND|AGND|DGND|PGND|VSS)"
            confidence_contribution: 0.7

  extra_fields:
    operating_voltage:
      type: float
      source: "static"
      value: 0.0
  ```

* **Schema 範例 (`SignalPattern` / 差分對與功能訊號):**
  功能訊號規範定義單線控制訊號與高速/SI差分對。以下以 `600_differential_pair.yaml` 為例：
  ```yaml
  name: "Generic_Differential_Pair"
  category: "Signal"
  priority: 600 # 高於一般功能訊號 (500~590)，但低於具體匯流排 (700+)
  
  signals:
    - role: "DIFF_PAIR"
      required: true
      group_key: false
      matches:
        match_any:
          # 情境 A: 標準差分結尾 (_P/_N, _DP/_DN, _TXP/_TXN 等)
          - match_all:
              - net_name_regex: "(?i)[_\\.](?:[PD]|[NMD])(?:_C|_R|_DL\\d+)?$"
            confidence_contribution: 0.85
          # 情境 B: 包含 DIFF/PAIR 命名關鍵字
          - match_all:
              - net_name_regex: "(?i)(?:DIFF|PAIR)[a-zA-Z0-9_]*"
            confidence_contribution: 0.80
  
  role_overrides:
    # 差分對上若串聯電容，精確判定為 AC 耦合電容
    - original_sub_category: "Capacitor"
      connected_to: "Signal"
      new_role: "AC_Coupling_Capacitor"
  ```

* **差分訊號推導模型與 DRC 價值 (Differential Pair Modeling & DRC Impact):**
  1. **極性與夥伴自動推導 (Polarity & Partner Derivation):**
     - 當網路命中差分訊號規則時，Topology Engine 自動調用 `_derive_differential_properties(net_name)`：
       - `diff_polarity`: 自動判定為 `"P"` (正端) 或 `"N"` (負端)。
       - `diff_pair_partner`: 自動推導對應的互補夥伴 Net 名稱（例如 `TCP0_TX1_P` 的夥伴為 `TCP0_TX1_N`；`USB_DP` 的夥伴為 `USB_DM`）。
  2. **協定前綴分流與匯流排標籤保留 (Protocol Tagging vs. General SI):**
     - **協定差分線**: 帶有通訊協定前綴 (如 `TCP0_*`, `USB_*`, `PCIE_*`) 的高速線，保留專屬匯流排標籤 (`bus_type="USB"`, `net_type="Differential"`, `functional_role="High_Speed_Differential"`)。
     - **純板級 SI 測試對**: 無特定協定前綴之板級測試線 (如 `L1_TOP_MS_1_P_C`)，歸類為通用差分訊號 (`net_type="Differential"`, `functional_role="Differential_Pair"`, `bus_type=None`)。
  3. **對後續 Level 3 DRC 的核心價值 (Why DRC Needs Differential Tags):**
     - **AC 耦合電容對稱性檢查 (AC Coupling Symmetry):** 高速差分線路 (如 PCIe/USB/SATA) 要求 P/N 兩端串聯電容之容值 (Capacitance)、額定耐壓與封裝大小必須 100% 相同。圖譜節點預先建立 `diff_pair_partner` 後，DRC 引擎可以以 **$O(1)$ 常數時間** 直接查詢配對網路的電容，無需在全圖進行 $O(N)$ 拓撲搜尋。
     - **終端電阻跨接檢查 (100Ω Termination Resistor):** 檢查 P 與 N 兩端是否正確跨接差分終端匹配電阻。
     - **TVS/ESD 防護對稱性 (Protection Symmetry):** 確保差分線兩端具有對稱的保護二極體規格與接地路徑。

* **實體符號提取與物理鐵證 (Physical Symbol Extraction & Anchoring):**
  在步驟 1 (解析 OrCAD XML) 提取全域 `<Global>` 標籤時，系統不採用粗暴的一刀切，而是**同時結合符號名稱 (`symbolName` 如 VCC/GND 系列) 與網路名稱命名特徵進行雙重識別**：
  1. **接地符號分流:** `symbolName` 包含 `GND`, `EARTH`, `0` 或網路名稱符合接地前綴者，納入 `ground_symbol_nets`，圖譜節點賦予 `is_ground_symbol_connected: true`。
  2. **電源符號分流:** `symbolName` 包含 `VCC`, `VDD`, `POWER`, `BAR`, `ARROW`, `CIRCLE` 或網路名稱符合電源前綴者，納入 `power_symbol_nets`，圖譜節點賦予 `is_power_symbol_connected: true`。
  3. **正則命名擴充:** Level 1/2 之電源正則全面支援包含小數點的標準電壓命名 (如 `+1.8V`, `+3.3V`, `1.8V`)、`P` 表記 (如 `+1P35V`, `3P3V`) 及專用軌道前綴 (`PW_VCC`)。
  4. **非電氣/特殊符號隔離:** `NC` (未連接) 或單純散熱墊標記 (`EXPOSED THERMAL PAD`) 若無接地符號或電源符號掛載，絕不被強制附加上電氣屬性。

* **執行順序、領域解耦與非排他多標籤機制 (Execution Order, Decoupling & Multi-labeling):**
  Level 2 引擎執行時，針對單一網路的模式匹配採用 **「功能領域解耦 (Domain Decoupling)」**，打破過去全局 First-Match Wins (一旦命中即 `break` 阻斷後續全部規則) 的限制：
  1. **四大特徵領域解耦獨立比對:**
     - **接地領域 (Ground Domain, 優先級 950+):** 評估 `Generic_GND` 等接地規則。
     - **電源軌領域 (Power Rail Domain, 優先級 900~949):** 評估 `Generic_Power_Rail` 等供電規則，萃取 `operating_voltage`。
     - **通訊匯流排領域 (Bus Domain, 優先級 700~899):** 評估 `I2C`, `SPI`, `JTAG`, `USB_TypeC`, `UART` 等匯流排成團規則。
     - **功能訊號與差分對領域 (Signal Domain, 優先級 500~699):** 評估 `Power_Control`, `Clock_Crystal`, `LED_Status`, `Analog_Sense`, `GPIO` 及 `Differential_Pair` 等規則。
     每個網路在各個領域內分別比對一次最高優先級規則，但跨領域之間**互不阻斷、屬性不互斥覆蓋**。
  2. **忠實反映實體拓撲原則 (Physical Fidelity & Short-Circuit Preservation):**
     若電路設計中一條網路確實同時接了電源符號與接地符號 (例如 OrCAD 線路上同時掛載了 VCC 符號與 GND 符號，屬於典型的嚴重短路異常)：
     - **圖譜屬性:** 節點將同時完整保留 `is_power: true` 與 `is_ground: true`，且各自的推論欄位 (如 `operating_voltage`) 完整保留，**絕不在圖譜建置階段預設抹煞任何物理事實**。
     - **語意多標籤 (Multi-label Semantic Tagging):** 節點同時標註 `net_types: ["Power", "Ground"]` 與 `functional_roles: ["Power_Rail", "Reference_Ground"]`，主要語意型態標記為 `net_type: "Power_GND_Conflict"` 與 `functional_role: "Power_Ground_Short"`。
     - **架構優勢:** 徹底確保圖譜資料模型的客觀真實性，將短路違規的判定與告警完全交由 Level 3 (DRC) 專門規則處理，達成零漏報。

* **Level 2 參數列舉字典 (Taxonomy):**
  為了防止名詞發散，Level 2 的關鍵參數採用嚴格白名單：
  * `category` (Pattern 類別): `Communication` (通訊與介面), `Power` (電源), `Signal` (控制與功能訊號), `RF` (射頻), `Analog` (類比訊號)
  * `bus_type` (匯流排類型): `I2C`, `SPI`, `JTAG`, `USB`, `UART`, `None`。
  * `role` (訊號角色): 由 Pattern 自定義但需維持慣例，如 `SCL`, `SDA`, `SCK`, `MOSI`, `MISO`, `TCK`, `TMS`, `TX`, `RX`, `VCC`, `GND`, `DIFF_PAIR`, `PWR_EN`, `CLK_OSC`。
  * `connected_to` (連線特徵): 用於覆寫判定。允許值：`PowerRail` (電源網路), `GND` (地線), `Signal` (其他一般訊號線), `Any` (不拘)。
  * `new_role` (覆寫後的新角色): 
    * 電阻類：`Pull_up` (上拉), `Pull_down` (下拉), `Series_Resistor` (串接匹配), `Voltage_Divider` (分壓)。
    * 電容類：`Decoupling` (去耦/旁路), `Filter_Capacitor` (濾波/旁路), `AC_Coupling_Capacitor` (交流耦合), `Bootstrap` (自舉)。

* **規則檔案維護與註解規範 (Comment & Maintenance Standards):**
  - **IaC 豐富註解義務:** 任何新增或擴充之 Level 1 / Level 2 YAML 檔案，**必須附帶詳細繁體中文註解**，標明：
    1. 規則涵蓋的業界標準協定或訊號範圍。
    2. 典型電路圖命名範例 (如 `_P/_N`, `EN_*`, `TCK`)。
    3. 拓撲角色覆寫之硬體原理。
    4. 下游 Level 3 DRC 檢查的相依性與目的。
  - **檔名優先級排序:** 檔名以三位數優先級區間開頭 (如 `500_power_control.yaml`, `600_differential_pair.yaml`, `710_spi.yaml`)，確保目錄檢索時即反映執行順序。

* **信心度加總與 LLM 漸進式探勘 (Progressive Discovery):**
  Level 2 引擎採用 **「加分制」**，在成功將 Net 成團或分類後，會將所有命中訊號的 `confidence_contribution` 加總 (上限 1.0)，作為最終信心度。
  * **LLM 觸發閥值 (< 0.6)**：若總信心度低於 0.6，代表圖譜拼湊的證據太弱，或者該網路為完全未知的自訂特殊訊號。
  * 遇到上述情況，系統將收集未識別網路 (Ambiguous Nets)，交由 LLM Agent 攜帶 Graph 查詢工具主動下探尋找，釐清實體腳位與連線後，動態產出 `custom_pattern.yaml` 重新觸發引擎審查。

### Level 3: 設計規則驗證規範 (DRC) (`patterns/rules/`)
* **職責:** 接收 Level 2 產出的高階邏輯物件 (如 `is_bus`, `bus_type`, `is_power`, 動態 `Pull_up` 角色)，執行硬體「合規 / 違規」的設計規則檢查 (Design Rule Check, DRC)。

* **架構決策 (Architecture Decisions):**
  1. **扁平化目錄與標籤註冊表 (Shallow Directory & Tag Registry):**
     * **儲存規範:** 嚴格限制實體資料夾深度最多兩層 (僅作為最高階領域劃分，例如 `rules/power/`, `rules/interfaces/`)，禁止無限制的深層樹狀結構。
     * **標籤管理 (Tags):** 詳細分類完全依賴 Tags。系統將維護一份全域的 `tags.schema.json` 作為白名單，透過 CI/CD 驗證確保 Tag 的正確性，防止名詞碎片化。前端可依此動態生成目錄樹供使用者檢索。
  2. **實例化與上下文注入 (Context Injection):**
     * **Level 2 建立實例 vs Level 3 注入:** 
       * **Level 2 (建立):** 實例的「分群與建立」發生在 Level 2。Level 2 引擎會掃描圖譜，將屬於同一組 I2C 的訊號線集結，在圖譜中實際建立出 `i2c_1`, `i2c_2`, `i2c_3` 這三個獨立的匯流排實例 (Node)。
       * **Level 3 (注入):** Level 3 的 `trigger_conditions` 僅作為「查詢器」。當 Trigger 在圖中找到這 3 組 I2C 時，不會在單一任務中執行迴圈，而是**自動平行生成 3 個獨立的 Rule Task**。引擎會將精確的實例指標 (如 `i2c_1`) 動態注入給 `$context.target`，使得撰寫規則時只需專注於單一對象的斷言。
  3. **混合式評估架構 (Hybrid Mode):**
     * 採「效能分級與沙盒隔離」。同步極速執行 YAML 的拓撲檢查；將 Python / LLM 檢查排入非同步 Queue 中執行。Python 腳本將受限於 GraphAPI (SDK Sandbox)，禁止直接存取底層檔案系統以確保安全。

* **YAML 參數字典 (Schema & Allowed Options):**
  * `name` (字串, **必填**): 規則名稱，須具備全域唯一性 (可做為報表 ID)。
  * `tags` (字串陣列, **必填**): 必須存在於 `tags.schema.json` 中 (例: `["I2C", "Signal Integrity"]`)。
  * `severity` (字串, **必填**): 違規嚴重度。允許值：`Fatal`, `Error`, `Warning`, `Info`。
  * `trigger_conditions` (物件, **必填**): 觸發條件 (滿足其一即可加入檢查排程)
    * `graph_match`: 匹配圖譜屬性 (例: `attributes: {is_bus: true, bus_type: "I2C"}`)。
    * `bom_match`: 匹配 BOM 表零件 (例: `mfg_pn: "LSF0102*"`，支援正則或萬用字元)。
  * `check_logic` (物件, **必填**): 檢查邏輯定義
    * `type` (字串, **必填**): 允許值為 `topology_check` (YAML靜態)、`python_script` (沙盒腳本)、`llm_agent` (LLM智慧化)。

* **完整 YAML 架構範例 (涵蓋 3 種 Hybrid 模式):**

```yaml
name: "I2C_Pull_Up_Existence"
tags: ["I2C", "Signal Integrity"]
severity: "Error"

# --- 觸發條件 ---
trigger_conditions:
  graph_match:
    attributes:
      is_bus: true
      bus_type: "I2C"

# --- 檢查邏輯 ---
check_logic:
  # 【模式 1】 Declarative (靜態 YAML 拓撲檢查)
  type: "topology_check"
  asserts:
    # context.target 已由 Level 3 引擎注入為特定的實例 (如 i2c_1)
    - condition: "has_neighbor"
      node: "${context.target}"
      with_role: "Pull_up"
      min_count: 2
      error_message: "I2C 匯流排 (${context.target.name}) 缺少上拉電阻"
      
    - condition: "is_connected_to_category"
      node: "${context.target.neighbors(role='Pull_up')}"
      target_category: "Power"
      error_message: "I2C 上拉電阻 (${context.node.name}) 未連接至電源軌"
      
  # ----------------------------------------------------
  # 【模式 2 預留】 Python Script (受限沙盒的程式化逃生門)
  # type: "python_script"
  # script_path: "scripts/drc/i2c_capacitance_calc.py"
  # params:
  #   max_pf: 400
  
  # ----------------------------------------------------
  # 【模式 3 預留】 LLM Agent (智能化逃生門)
  # type: "llm_agent"
  # agent_prompt: >
  #   請調閱掛載於 ${context.target.name} 上的 Master IC (${context.target.master_ic.pn}) 之規格書。
  #   1. 確認其 I2C 引腳是否內部整合上拉電阻。
  #   2. 若大於 10k ohm 則通過 (PASS)，否則發出違反通知 (FAIL)。
```


### Level 3: 邊角情境與設計哲學 (Edge Cases & Design Philosophy)
在架構討論中，我們針對 Level 3 執行時的常見邊角情境確立了以下原則：

1. **違規回報與修復 (Remediation vs. Reporting):**
   * **職責邊界:** DRC 工具的職責僅止於「找出錯誤並解釋原因」。系統**不**負責提供結構化的自動修復步驟 (Auto-fix)。
   * **報告規範:** 每一條規則被觸發時，只要判定為 FAIL，必須提供精確的 `fail_reason`（例如：明確指出是「缺少上拉電阻」還是「上拉電阻阻值不對」），以及違規發生的圖譜節點 (Node ID)，以利人類工程師快速定位與手動修改。

2. **規則相依性 (Rule Dependency):**
   * **無狀態與完全獨立 (Independent & Stateless):** 所有 Level 3 規則皆設計為**平行且獨立執行**。我們**不**在 YAML 中實作規則依賴 (如 `depends_on`)。
   * **解耦優於雜訊控制:** 即使規則之間有因果關聯（例如：「缺少電阻」導致後續的「電阻值計算」也跟著失敗），系統也接受這兩條規則各自發出報錯。這能最大化引擎的多執行緒效能，並讓每條規則的 YAML 保持極致簡潔，將因果判斷的責任交還給工程師。

3. **豁免機制 (Waivers):**
   * **v1 暫不實作:** 將人工豁免（False Positives 標記）列為 Future Work。初期的目標是建立穩固的基礎檢查流程。

4. **電源-接地短路檢測 (Power-to-Ground Short Detection):**
   * **圖譜忠實呈現 vs. DRC 致命判定:** Level 1/2 引擎嚴格秉持客觀記錄原則，當線路上同時接了 Power 與 Ground 符號時，不進行預設互斥修正，而是讓節點同時具備 `is_power: true` 與 `is_ground: true` (或 `net_type: "Power_GND_Conflict"`)。
   * **Level 3 零漏報觸發:** Level 3 DRC 設有最高嚴重等級 (`severity: "Fatal"`) 之短路違規規則，只要匹配到雙重屬性節點，立即向工程師報告致命短路，精準防止硬體燒燬。

### Level 3 進階架構：PartDB 驅動的動態規則組合 (PartDB-Driven Dynamic Rules)

針對不同廠牌 Master IC 對通訊匯流排 (如 I2C, USB) 與電源具有迥異的硬體配置要求，為了避免「規則無窮爆炸」與「超級模版過度肥大」，我們導入了 **PartDB 驅動的動態組合架構**：

#### 1. 職責分離：通用底線 (YAML) vs. IC 特規 (Python + PartDB)
我們將檢查邏輯拆分為兩個層次，彼此並存且互不干擾：
* **通用底線 (Generic Baseline, 純 YAML):**
  負責檢查「不論哪顆 IC 都必須遵守的物理底線」。例如：I2C 匯流排**絕對必須**具備上拉電阻（不論阻值多少）。這類規則由極速的宣告式 YAML 執行。
* **IC 特規 (Part-specific Rules, Python Script):**
  負責檢查「依賴於特定 IC 型號的進階電氣要求」。例如：這顆 STM32 的上拉電阻必須介於 2k~10k 之間，且嚴禁連接對地電容。這由 Python Script 查表執行。

#### 2. 獨立的零件規格庫 (PartDB) 作為真相來源
* **避免將 IC 規格寫死在 DRC 規則中：**
  系統維護一個獨立的零件規格庫 (PartDB，本地 DB 或外部 API)。資料來源為事先解析並結構化的 Datasheet 數據。
  *(範例 PartDB 紀錄：`{"pn": "STM32F4", "i2c_req": {"pullup_range": [2000, 10000], "forbid_gnd_cap": true, "series_resistor": false}}`)*

#### 3. 決定性的動態邏輯 (Deterministic Assembly without LLM)
* **澄清：這不是 AI 生成**
  這裡的「動態組裝」**100% 依賴固定的 Python 程式碼規範**，完全沒有 LLM 參與。Python 腳本讀取 PartDB 返回的 JSON 字典，用標準的 `if-else` 決定要呼叫哪些 GraphAPI 檢查。這是決定性 (Deterministic)、極速且好維護的固定邏輯。

#### 4. PartDB 的實體儲存策略 (Storage & DB Engine)
考量到「穩定、精簡、好備份、邏輯正確」以及未來「AI 自動填寫」的需求，我們確立了以下架構決策：
* **獨立的 File-based YAML DB:** 
  我們**不使用** SQLite 或 PostgreSQL，且捨棄了傳統的 JSON，全面採用 **YAML** 格式。這能原生支援 `#` 註解，讓 AI 或人類在建檔時能留下除錯脈絡，且完美享受 Git 版本控制 (GitOps) 的好處。
* **統一存放於 `patterns/partdb/`:**
  將 PartDB 視為「規則引擎邏輯的一部分」。備份時只需將 `patterns/` 打包，即可將「檢查邏輯 + 零件參數真相」完整攜帶到另一個系統中。

#### 5. Schema 擴展與文件化規範 (Schema Governance & Documentation)
一旦引入 PartDB，Schema 與 Python Code 就形成了強耦合。為了防止 Schema 混亂、並確保未來的 AI (Copilot) 能精準知道如何填寫這些欄位，我們確立了以下規範：

1. **介面導向，漸進擴充 (Interface-Oriented):**
   擴充以「硬體介面」為單位，初期只定義 `schema_i2c.json`，所有廠牌的 I2C 特規都共用此 Schema 與同一支 `i2c_dynamic_checker.py`。
2. **強制具備 AI 導向的說明文件 (AI-Targeted Guidelines):**
   Schema 必須配備說明文件，**做為未來 AI 填寫 PartDB 的 Prompt 依據**，指導 AI 該去 Datasheet 的哪個章節抓取什麼特徵。
3. **嚴格版本控制 (Strict Validation):**
   不允許隨意新增未經驗證的自訂欄位。必須走「改 Schema -> 改 Code -> 改說明文件」的正規流程。
4. **溯源證據結構化 (Structured Evidence for UI & Reports):**
   資料來源 (Datasheet 檔名與頁碼) **不能只寫在 `#` 註解裡**。因為註解在 YAML 解析後會消失，無法傳遞給前端 Web UI 或 DRC 報表。因此，Schema 必須強制包含結構化的 `_meta` 區塊，用以儲存資料出處。

#### 6. 實作範例：複合式 Level 3 規則與 YAML 結構化 PartDB

**【A. 以「單一 IC」為單位的 YAML PartDB 組織】 (`patterns/partdb/data/STM32F405.yaml`)**
一顆 IC 的所有硬體特規皆收斂於同一個 YAML 檔案內。利用 YAML 結構化的 `evidence` 欄位，未來在 Web UI 上可以輕易呈現「這條特規是依據哪份文件的哪一頁制定的」，甚至讓 DRC 報表直接附上規格書截圖連結。

```yaml
pn: "STM32F405"

interfaces:
  I2C:
    # 這是給工程師看的除錯脈絡，解析後會被丟棄
    # 注意：F4 系列在 High-speed 模式下 I/O 內部架構不同，強烈禁止加電容
    requires_series_resistor: false
    forbid_gnd_capacitor: true
    pullup_range_ohms: [2000, 10000]
    
    # 這是結構化的溯源資料，會跟著 Violation 一起拋出到 DRC 報告與 Web UI
    _meta:
      evidence: "STM32F405_Datasheet_Rev4.pdf"
      page: 45
      excerpt: "In Fast-mode Plus, the capacitive load must not exceed 100pF. Avoid external ground capacitors on SCL/SDA."
      
  USB:
    requires_esd_protection: true
    differential_impedance_ohms: 90
    _meta:
      evidence: "AN4879_USB_Hardware_Guidelines.pdf"
      page: 12
```

**【B. 複合式 Check Logic (Composite Rule)】 (`patterns/rules/interfaces/i2c_compliance.yaml`)**
引擎會先執行極速的靜態 `topology_check` 保障物理底線，接著再執行 `python_script` 進行 PartDB 動態查表。任何一個步驟失敗，都會匯集到同一個 Rule 報表中。
*(注意：Level 3 規則之間**完全平行無序**，刻意不引入 `priority` 機制，以保證最大化的多執行緒效能與架構解耦。)*

```yaml
name: "I2C_Universal_Compliance"
tags: ["I2C", "PartDB", "Compliance"]
severity: "Error"

trigger_conditions:
  graph_match:
    attributes:
      is_bus: true
      bus_type: "I2C"

check_logic:
  # 步驟 1: 保障底線 (I2C 絕對要有 Pull-up)
  - type: "topology_check"
    asserts:
      - condition: "has_neighbor"
        node: "${context.target}"
        with_role: "Pull_up"
        min_count: 2
        error_message: "I2C 匯流排缺少基本的上拉電阻"

  # 步驟 2: 動態特規檢查 (去 YAML PartDB 查表)
  - type: "python_script"
    script_path: "scripts/drc/i2c_dynamic_checker.py"
```

```python
# scripts/drc/i2c_dynamic_checker.py
from designshield.sdk import RuleResult, RuleViolation, GraphAPI, PartDB

def execute(context, graph_api: GraphAPI, part_db: PartDB, params):
    bus = context.target
    master_ic = graph_api.get_master_device(bus)
    violations = []
    
    # 1. 讀取 patterns/partdb/data/<pn>.yaml 的 I2C 區塊
    ic_specs = part_db.query(pn=master_ic.pn, interface="I2C")
    if not ic_specs:
        return RuleResult.PASS 
        
    evidence_meta = ic_specs.get("_meta", {})
    
    # 2. 決定性的動態檢查，並將 _meta 注入到 Violation 報告中
    if ic_specs.get("requires_series_resistor", False):
        if not graph_api.has_component_in_series(bus, component_type="Resistor"):
             violations.append(RuleViolation(
                 message=f"IC {master_ic.pn} 規格書明定 I2C 需要串聯電阻。",
                 evidence=evidence_meta
             ))
             
    if "pullup_range_ohms" in ic_specs:
        pullup_range = ic_specs["pullup_range_ohms"]
        for res in graph_api.get_pullup_resistors(bus):
            if not (pullup_range[0] <= res.value <= pullup_range[1]):
                violations.append(RuleViolation(
                    message=f"上拉電阻 ({res.value}Ω) 不在規範 {pullup_range} 內。",
                    evidence=evidence_meta
                ))

    return violations if violations else RuleResult.PASS
```

#### 5. PartDB 的 Schema 擴展策略 (Schema Extension Strategy)
一旦引入 PartDB 與 Python 查表，JSON 資料結構 (Schema) 與 Python 檢查碼之間就形成了強耦合。為了防止 Schema 混亂與維護噩夢，我們確立了以下開發原則：

* **介面導向，漸進擴充 (Interface-Oriented, Progressive Expansion):**
  我們**不**試圖在初期定義一個能包山包海的「萬能 IC Schema」。
  擴充是以「硬體介面 (Interface/Bus)」為單位。例如：初期只定義 `schema_i2c.json`，讓所有廠牌的 I2C 特規都收斂到這份 Schema 內，並共用同一支 `i2c_dynamic_checker.py`。未來遇到新介面 (如 USB) 時，再獨立開發 `schema_usb.json` 與對應的 checker 程式。
  
* **嚴格限制與版本控制 (Strict JSON Schema Validation):**
  PartDB 的資料輸入必須受到嚴格的 JSON Schema 驗證。我們**不允許**工程師在 JSON 中隨意新增自由欄位 (Schemaless)。
  若某顆新 IC 帶來了前所未見的特規 (例如：限制 I2C 總寄生電容 < 400pF)，開發流程必須是：
  1. 升級定義檔 `schema_i2c.json`，新增 `max_bus_capacitance_pf` 欄位。
  2. 同步更新 `i2c_dynamic_checker.py`，加入對此新欄位的 GraphAPI 運算邏輯。
  3. 通過 CI/CD 測試後，方可將該 IC 的資料寫入 PartDB。
  這種做法確保了 Python 引擎永遠能 100% 正確解析並執行 PartDB 中的每一項規範，避免靜默失效 (Silent Failures)。

---

## 5. 規則庫管理與工作流 (Rule Management & GitOps Workflow)

隨著系統將所有的 Level 1~3 規則以及 PartDB 知識庫皆轉換為 File-based YAML，我們需要一套高效率且具備嚴格防呆機制的管理流程，以應對未來人類專家與 AI Agent 共同協作的場景。

### 1. 管理介面定位：唯讀檢視器 + GitOps (Read-only Viewer + GitOps)
* **拒絕造輪子:** 我們**不**在系統中開發複雜的 CRUD (新增/修改/刪除) Web UI 來編輯 YAML。這會耗費巨大成本且難以做到 VSCode 的編輯體驗。
* **開發 Web UI Viewer (Rule Catalog):** Web UI 的定位僅作為「視覺化呈現 (Visualization)」。負責將 Git Repository 中的 YAML 規則與 PartDB 資料，渲染成漂亮的可搜尋目錄、Tag 過濾面板與拓撲圖預覽。
* **維持 Git 為唯一真相:** 所有規則的增刪改查，皆回歸到開發者最熟悉的程式碼編輯器 (IDE) 進行，並透過 Git PR (Pull Request) 流程來執行審查 (Review)。未來的 AI Agent 也將直接以發送 PR 的形式來貢獻 PartDB 資料。

### 2. 嚴格的統一驗證機制 (Unified Validation Script)
為了防堵「格式錯誤的 YAML (如拼字錯誤、必填欄位遺漏)」進入系統，我們實行以下卡控機制：
* **單一驗證腳本 (`scripts/validate_rules.py`):** 
  開發一支統一的 Python 腳本，負責執行：
  1. 校驗所有 Level 1~3 的 Pattern YAML 是否符合基礎格式。
  2. 校驗 `patterns/partdb/data/*.yaml` 是否完全符合 `patterns/partdb/schema/*.json` 所定義的格式要求。
* **本地與 CI/CD 雙重防線:**
  * **本地執行 (Local):** 工程師或 AI Agent 在修改完 YAML 後，必須在本地呼叫此腳本進行校驗。
  * **自動化 CI/CD:** 將同一支驗證腳本綁定於 Git Repository 的 CI/CD 流程 (如 GitHub Actions)。任何 PR 在 Merge 前都必須通過該腳本的檢查，否則自動阻擋。

### 3. 提供清晰的貢獻指引 (`patterns/README.md`)
由於 `patterns/` 目錄將是人類專家與 AI Agent 頻繁協作的重鎮，我們必須在該目錄下維護一份極度清晰的 `README.md`。內容必須涵蓋：
* 各資料夾 (Level 1~3, partdb) 的職責定義。
* 新增一條規則或是新增一顆 IC 資料的**標準作業流程 (SOP)**。
* 如何在本地端執行 `scripts/validate_rules.py` 來驗證修改。
* 此文件不僅給人類工程師看，更是未來 AI Agent 進行自動化維護時的**最高行為準則 (System Prompt)**。
