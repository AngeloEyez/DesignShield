# PartDB 通用零件穿透技術規格書 (PartDB Generic Pass-Through Specification)

## 1. 緣起與架構痛點 (Background & Problem Statement)

在硬體電路圖 (Schematic) 與網表 (Netlist) 中，一條端到端的邏輯功能鏈路（如 USB 3.0 / PCIe 高速差分對、I2C 匯流排）在實體佈局上經常被各種中繼元件切斷為多個中繼網段 (Net Segments)。

先前系統在 `GraphAPI.trace_differential_end_to_end` 中分別針對「2-pin 串聯被動元件」與「4-pin 共模扼流圈 (CMC)」實作了特化穿透邏輯。然而，隨著支援硬體介面增加，電路中會出現更多種類的穿透元件：
* **多通道被動排件:** 4-pin / 8-pin 排阻 (Resistor Pack, 如 RP1)、排容 (Cap Array)。
* **多腳位共模濾波器:** 8-pin 雙通道共模扼流圈、非標準腳位定義之 CMC。
* **主動電平轉換元件 (Level Shifters):** 如 TXS0108、LSF0102、PCA9306（跨電壓域穿透）。
* **訊號緩衝與中繼元件 (Redrivers / Buffers):** 單向訊號放大器，僅允許 A ➔ B 穿透，嚴禁逆流。
* **類比多工切換器 (Analog Switches / Mux):** 如 TS3USB221（1:2 切換開關）。

若為每一種元件都在 `GraphAPI` 內擴充專屬的 `if-elif` 判斷與引腳硬編碼，將會導致：
1. **API 無止境膨脹 (Code Bloat):** 核心圖譜庫充滿特定零件的引腳特徵。
2. **缺乏資料庫真相 (Lack of Truth Source):** 非標準零件的引腳接法無法隨電路規格書動態擴充。
3. **無向假設的致命漏洞 (Directional Leak):** 主動晶片具備單向性，若一律當作無向直通，將導致訊號逆流誤判。

因此，本規範正式定義 **「PartDB 通用零件穿透模型 (Generic Pass-Through Model)」**，將零件的引腳導通物理事實收斂於 PartDB，並透過 **分層混合架構** 與 **引擎預加載 (Pre-hydration)** 達成高擴充性、極致效能與零代碼硬編碼。

---

## 2. 系統架構分層與責任邊界 (Architectural Layering)

系統採「知識庫定義 ➔ 預加載注入 ➔ 演算法無狀態消費」三層模型：

```mermaid
flowchart TD
    A["PartDB 零件庫 (YAML)<br>定義 pass_through 引腳配對"] -->|啟動或解析時載入| B["PatternService / Level 1 引擎"]
    B -->|Pre-hydration 預加載| C["NetworkX 圖譜節點<br>(node.pass_through_mapping)"]
    
    D["Level 3 伴生腳本<br>(DRC Rule)"] -->|呼叫| E["GraphAPI 通用穿透演算法<br>(trace_end_to_end)"]
    C -->|O(1) 常數時間直接讀取| E
    
    subgraph Fallback 機制 (未登記 PartDB 時)
        F["標準 2-pin 被動件 (1⟷2)"]
        G["標準 4-pin CMC (1⟷4, 2⟷3)"]
    end
    E -.->|若節點無自帶屬性| Fallback
```

### 職責分工：
1. **PartDB 零件規格庫 (`patterns/partdb/data/*.yaml`):**
   * 作為零件物理真實特性的單一真實來源 (Single Source of Truth)。
   * 定義元件內部引腳映射、導通方向性、通道名稱與規格書出處 (`_meta`)。
2. **Level 1/2 模式引擎 (Pre-hydration 預加載):**
   * 解析線路圖或圖譜建置時，若元件料號匹配 PartDB，自動將穿透引腳映射解析為內部查表字典，注入節點屬性 `pass_through_mapping`。
3. **GraphAPI 穿透引擎 (`designshield.sdk.GraphAPI`):**
   * **零 PartDB 依賴:** 保持純粹圖論演算法，直接以 $O(1)$ 常數時間自節點屬性讀取引腳映射。
   * **分級安全守衛 (Graded Safety Guard):** 預設只穿透被動元件與 CMC；主動晶片即使有映射，也必須在呼叫端傳入 `allow_active=True` 時才予以穿透。
   * **向下相容兜底 (Graceful Fallback):** 未在 PartDB 登記的普通阻容或標準 CMC，自動退回標準 2-pin / 4-pin 拓撲預設。

---

## 3. PartDB Pass-Through 資料模型 (Schema Specification)

在 PartDB YAML 檔案中，新增頂層屬性 `pass_through`。

### 3.1 JSON Schema 結構定義 (`schema_pass_through.json`)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "PartDB Generic Pass-Through Specification Schema",
  "description": "零件穿透引腳導通關係與通道拓撲規格，供圖譜分析自動穿透",
  "type": "object",
  "required": ["type", "pin_pairs"],
  "properties": {
    "type": {
      "type": "string",
      "enum": ["passive", "active", "mux"],
      "description": "穿透元件物理類別：passive (被動無源直通), active (主動有源中繼/電平轉換), mux (多工切換開關)"
    },
    "description": {
      "type": "string",
      "description": "通道特性簡要說明"
    },
    "default_select": {
      "type": "string",
      "description": "當 type 為 mux 時，靜態拓撲預設選通之通道識別碼或群組"
    },
    "pin_pairs": {
      "type": "array",
      "description": "內部引腳穿透配對清單",
      "items": {
        "oneOf": [
          {
            "type": "array",
            "items": { "type": "string" },
            "minItems": 2,
            "maxItems": 2,
            "description": "極簡寫法：[in_pin, out_pin]，預設為 bidirectional 無向雙向直通"
          },
          {
            "type": "object",
            "required": ["pins"],
            "properties": {
              "pins": {
                "type": "array",
                "items": { "type": "string" },
                "minItems": 2,
                "maxItems": 2,
                "description": "引腳編號對 [端點1, 端點2]"
              },
              "direction": {
                "type": "string",
                "enum": ["bidirectional", "forward", "reverse"],
                "default": "bidirectional",
                "description": "傳輸方向：bidirectional (雙向可逆), forward (僅限 pins[0] ➔ pins[1]), reverse (僅限 pins[1] ➔ pins[0])"
              },
              "channel": {
                "type": "string",
                "description": "功能通道識別標籤 (例如 'CH1', 'DP', 'TX1', 'A-Port')"
              },
              "impedance_ohm": {
                "type": "number",
                "description": "元件導通電阻或特徵阻抗 (Ω)"
              }
            }
          }
        ]
      }
    },
    "_meta": {
      "type": "object",
      "required": ["evidence", "page", "excerpt"],
      "properties": {
        "evidence": { "type": "string", "description": "原廠 Datasheet 檔名" },
        "page": { "type": "integer", "description": "Datasheet 規格頁碼" },
        "excerpt": { "type": "string", "description": "規格書引腳描述摘錄" }
      }
    }
  }
}
```

---

## 4. 典型硬體元件定義範例 (Concrete YAML Examples)

### 範例 1: 標準 4-Pin 共模扼流圈 (Common Mode Choke)
檔案路徑: `patterns/partdb/data/ACM2012.yaml` (TDK 共模濾波器)

```yaml
pn: "ACM2012"
description: "Common Mode Choke for USB 2.0 / High-Speed Differential Lines"
category: "Passive"
sub_category: "Inductor"

pass_through:
  type: "passive"
  description: "雙差分線圈直通"
  pin_pairs:
    # 支援極簡寫法：直通繞組 Pin 1 ⟷ Pin 4 與 Pin 2 ⟷ Pin 3
    - pins: ["1", "4"]
      channel: "LINE1"
      direction: "bidirectional"
    - pins: ["2", "3"]
      channel: "LINE2"
      direction: "bidirectional"
  _meta:
    evidence: "ACM2012_Datasheet_Rev2.pdf"
    page: 2
    excerpt: "Pin 1-4: Line 1 coil; Pin 2-3: Line 2 coil. Direct common-mode attenuation."
```

---

### 範例 2: 8-Pin 四通道排阻 (Resistor Pack / Array)
檔案路徑: `patterns/partdb/data/EXB28V.yaml` (Panasonic 4-Isolated Resistor Array)

```yaml
pn: "EXB28V"
description: "Convex terminal type 4-isolated resistor network"
category: "Passive"
sub_category: "Resistor"

pass_through:
  type: "passive"
  description: "4 組獨立平行串阻"
  pin_pairs:
    # 支援極簡陣列語法
    - ["1", "8"] # R1
    - ["2", "7"] # R2
    - ["3", "6"] # R3
    - ["4", "5"] # R4
  _meta:
    evidence: "EXB28V_Series_Datasheet.pdf"
    page: 1
    excerpt: "Schematic: 4 independent isolated resistors between pins 1-8, 2-7, 3-6, 4-5."
```

---

### 範例 3: 雙向電平轉換器 (Bidirectional Level Shifter)
檔案路徑: `patterns/partdb/data/TXS0102.yaml` (TI 2-Bit Auto-Direction Voltage Translator)

```yaml
pn: "TXS0102"
description: "2-Bit Bidirectional Voltage-Level Translator with Auto-Direction Sensing"
category: "IC"
sub_category: "LevelShifter"

pass_through:
  type: "active"
  description: "A-Port 與 B-Port 雙向電平轉換通道"
  pin_pairs:
    - pins: ["A1", "B1"]
      channel: "CH1"
      direction: "bidirectional"
    - pins: ["A2", "B2"]
      channel: "CH2"
      direction: "bidirectional"
  _meta:
    evidence: "TXS0102_Datasheet_SCES641.pdf"
    page: 4
    excerpt: "Port A (VCCA) references to Port B (VCCB). Data paths A1-B1, A2-B2 are bidirectional."
```

---

### 範例 4: 單向緩衝放大器 (Unidirectional Buffer / Redriver)
檔案路徑: `patterns/partdb/data/SN74LVC1G125.yaml` (Single Bus Buffer Gate)

```yaml
pn: "SN74LVC1G125"
description: "Single Bus Buffer Gate With 3-State Output"
category: "IC"
sub_category: "InterfaceIC"

pass_through:
  type: "active"
  description: "單向訊號中繼緩衝 (A 輸入 ➔ Y 輸出，嚴禁反向穿透)"
  pin_pairs:
    - pins: ["A", "Y"]
      channel: "DATA_BUF"
      direction: "forward" # 訊號僅能由 Pin A 穿向 Pin Y
  _meta:
    evidence: "SN74LVC1G125_Datasheet.pdf"
    page: 3
    excerpt: "Input A drives Output Y when OE# is low. Unidirectional driver."
```

---

### 範例 5: 1:2 高速類比多工切換器 (Analog Mux / Switch)
檔案路徑: `patterns/partdb/data/TS3USB221.yaml` (High-Speed USB 2.0 1:2 Mux)

```yaml
pn: "TS3USB221"
description: "High-Speed USB 2.0 (480-Mbps) 1:2 Multiplexer Switch"
category: "IC"
sub_category: "Switch"

pass_through:
  type: "mux"
  default_select: "PORT1"
  description: "共用 COM 端切換至 PORT1 或 PORT2"
  pin_pairs:
    # 預設選通通道 1 (PORT1)
    - pins: ["COM1", "1D+"]
      channel: "PORT1_DP"
      direction: "bidirectional"
    - pins: ["COM2", "1D-"]
      channel: "PORT1_DM"
      direction: "bidirectional"
    # 備用切換通道 2 (PORT2)
    - pins: ["COM1", "2D+"]
      channel: "PORT2_DP"
      direction: "bidirectional"
    - pins: ["COM2", "2D-"]
      channel: "PORT2_DM"
      direction: "bidirectional"
  _meta:
    evidence: "TS3USB221_Datasheet.pdf"
    page: 6
    excerpt: "COM1, COM2 are common I/O pins multiplexed between 1D+/1D- and 2D+/2D-."
```

---

## 5. 圖譜預加載注入資料契約 (Pre-hydration Contract)

在電路圖由 XML 解析完成並建立 NetworkX 圖譜時，`ComponentEngine` / `TopologyEngine` 將 PartDB YAML 解析為輕量導通字典，直接寫入元件節點屬性：

```python
# 元件節點 cdata 結構
cdata = {
    "type": "component",
    "ref_des": "TL1",
    "category": "Passive",
    "sub_category": "Inductor",
    # 引擎注入之穿透映射表
    "pass_through_mapping": {
        "type": "passive",  # "passive" | "active" | "mux"
        # 依照引腳查對向引腳：{ in_pin: (out_pin, channel_tag, direction) }
        "pin_map": {
            "1": {"out_pin": "4", "channel": "LINE1", "direction": "bidirectional"},
            "4": {"out_pin": "1", "channel": "LINE1", "direction": "bidirectional"},
            "2": {"out_pin": "3", "channel": "LINE2", "direction": "bidirectional"},
            "3": {"out_pin": "2", "channel": "LINE2", "direction": "bidirectional"},
        }
    }
}
```

### 優勢：
1. **$O(1)$ 瞬時查表:** GraphAPI 追蹤演算法在遍歷到該節點時，只需 `cdata["pass_through_mapping"]["pin_map"].get(in_pin)` 即可取得出口引腳。
2. **記憶體極小開銷:** 僅佔數十 bytes 的記憶體字典，不需要在穿透循環中反覆讀取硬碟或解析 YAML。
3. **無狀態沙盒安全:** 沙盒內的 Python 腳本直接使用圖論資料，無須額外的檔案系統權限。

---

## 6. GraphAPI 通用穿透演算法設計 (Generic Algorithm Workflow)

```mermaid
flowchart TD
    Start["抵達鄰近元件 (neighbor_comp)"] --> SafetyCheck{"是否為非電氣件<br>或已造訪？"}
    SafetyCheck -->|是| Stop["跳過，不穿透"]
    SafetyCheck -->|否| ActiveGuard{"是否為主動 IC<br>(category == 'IC')？"}
    
    ActiveGuard -->|是且 allow_active == False| Terminal["視為終端節點 (Terminal IC)<br>記錄為端點，結束此分支"]
    ActiveGuard -->|否或 allow_active == True| HasHydrated{"節點是否有預加載之<br>pass_through_mapping？"}
    
    HasHydrated -->|有| LookupMap{"pin_map 中是否存在 in_pin<br>且方向符合？"}
    LookupMap -->|是| GetOutPin["取得對應 out_pin 與 channel"]
    LookupMap -->|否| Stop
    
    HasHydrated -->|無| Fallback{"Fallback 拓撲預設"}
    Fallback -->|2-Pin 被動件| Pin2Pass["直接穿越至另一引腳 (len==2)"]
    Fallback -->|4-Pin CMC 候選| Pin4CMC["預設直通 1⟷4, 2⟷3"]
    Fallback -->|其他元件| Terminal
    
    GetOutPin --> CheckNextNet{"目標網段是否為<br>Power 或 Ground？"}
    Pin2Pass --> CheckNextNet
    Pin4CMC --> CheckNextNet
    
    CheckNextNet -->|是 (連向供電/地)| Block["嚴禁穿透！視為旁路終端<br>(防對地電容/上拉電阻穿透)"]
    CheckNextNet -->|否 (一般訊號)| Enqueue["穿透成功！加入 queue<br>繼續追蹤下游網段"]
```

---

## 7. 驗證卡控規範 (Validation & Governance)

為防止無效或格式錯誤的穿透定義進入規則庫，統一校驗器 (`scripts/validate_rules.py`) 將執行：
1. **Schema 嚴格比對:** 所有包含 `pass_through` 的 YAML 檔案必須通過 `schema_pass_through.json` 檢驗。
2. **引腳配對合法性校驗:**
   - `pin_pairs` 中宣告的引腳必須成對，不可有單引腳懸空。
   - 同一引腳在同一 `type: passive` 元件中不可重複映射到不同引腳（避免被動元件非物理分叉）。
   - 當 `direction == "forward"` 時，明確標註單向性。
3. **溯源資訊必填 (`_meta`):**
   - 必須提供原廠 Datasheet 檔名與頁碼摘錄，確保硬體工程師在審查報表時隨時可查閱原廠引腳圖。
