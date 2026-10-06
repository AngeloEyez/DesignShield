# Schematic-Analyzer Skill 工作邏輯與機制解析

本文件整理了 `Ref/schematic-analyzer` 專案中針對原理圖 (Schematic) 進行分析的系統工作邏輯，涵蓋零件 (Component) 與網路 (Net) 的圖譜建立機制、外部規則 (Pattern) 格式，以及自動與 LLM 互動的審查邏輯。

---

## 1. 建立零件圖譜 (Component Graph) 的必要欄位與判斷邏輯

在解析 KiCad 或 Cadence 原理圖建立零件圖譜時，系統提取並記錄以下必要欄位以供後續的 Rule 審查：

*   **`reference` (零件序號):** 例如 `U1`, `R10`, `J2`。用來區分主動與被動元件 (如 R, C, L 開頭通常判定為被動元件)。
*   **`value` (零件數值/型號):** 例如 `10k`, `STM32F405`, `DNP`。
*   **`lib_id` (符號庫):** 原理圖庫中元件的定義名稱。
*   **`pins` (引腳清單):** 元件所有的引腳名稱與編號。
*   **`nets` (連接網路清單):** 該元件連接到的所有 Net 名稱。
*   **`dnp` (是否上件):** 透過 flag 或屬性標示，判定該零件是否為不打件 (Do Not Populate) 狀態。

### 判斷與分類邏輯
零件圖譜建立**完全採用確定性的 Python CLI 解析 (基於 `kicad-cli` 或 Cadence netlist 解析)**，**不依賴 LLM 發送請求來萃取**。
分類邏輯 (`role_classifier.py` 與 `component_rules.py`)：
1.  **結構化計分 (Core Ranker):** 依據引腳數量 (`pin_count`) 和網路數量 (`net_count`) 加總進行基礎排序，找出核心控制器 (MCU/SoC)。
2.  **正則表達式比對:** 將 `value`, `lib_id`, `pins`, `nets` 透過正則表達式比對預先定義好的 YAML Rule (如尋找是否有 `VDD`/`GND` 引腳，以及對應的特定 `net_name` 組合)。
3.  **分數累加:** 符合特徵則加分，超過 `min_score` 門檻則判定賦予對應的角色 (Role) (例如 `Power IC` 或 `Connector`)。

### 採用 LLM 的協同提示詞 (Prompting Strategy)
當 LLM 作為代理 (Agent) 調用此 CLI 工具遇到結構證據不足以確認角色時，系統要求 LLM 遵循以下 `SCHEMATIC_STRATEGY.md` 提示詞原則升級查詢，而非盲目猜測：
> **Escalation Order Prompt Logic:**
> 1. Structural evidence from the schematic (先看連接狀態)
> 2. `mcp__pcbparts__jlc_search` (使用 MCP 查詢零件手冊規格)
> 3. Invoke `/ee-datasheet-master <datasheet_path> "<question>"` (透過專屬子代理分析規格書引腳定義)
> 4. **Iron Rule:** Re-ground the conclusion back to the schematic evidence. (必須將手冊定義的引腳用途與原理圖中實際連接的 Net 名稱作比對，才能做出結論，不能只憑手冊猜測其工作模式。)

---

## 2. 建立 Net 圖譜 (Net Graph) 的必要欄位與判斷邏輯

針對電路網路 (Net) 建立的圖譜，必要欄位包括：

*   **`net_name` (網路名稱):** 完整的階層名稱 (例如 `/SCH_TOP/I2C1_SDA`)。
*   **`connected_refs` (相連元件):** 連接到該 Net 的所有零件 reference 清單。
*   **`connected_pins` (相連引腳):** 紀錄哪個零件的哪個引腳連上了這個 Net。
*   **`net_code` / `net_type`:** 網路內部編號與型態。

### 判斷與拓撲邏輯
建立過程同樣是透過 Python 解析 Netlist 產生的拓撲圖。後續審查時，依據以下網路特徵判斷實際用途：
*   **Bus/Power Rail:** Net 連接了多個主動 IC 元件。
*   **過濾/上拉下拉 (Local Signal):** Net 只連接了一個 IC 和幾個被動元件 (R/C/L)。
*   **供電選擇/隔離:** Net 穿過二極體 (Diode)。
*   **未連線 (NC/Unconnected):** 引腳或 Net 無其他連接端。

### 採用 LLM 的協同提示詞 (Prompting Strategy)
LLM 閱讀 CLI 輸出的 JSON 資料時，被嚴格約束必須遵守以下提示詞原則來判讀網路：
> **Reading Strategy Prompt Logic:**
> - **Physical Identity ≠ Functional Identity**: 不可僅憑 Connector 上的引腳名稱來判斷匯流排模式。
> - **Trace both endpoints**: 必須追蹤 Net 的兩端。如果一條訊號線沒有連接到 Controller (核心控制端)，則該功能並未被啟用。
> - **Negative Evidence**: 沒連上的線 (未連線/懸空) 和連上的線一樣重要，它代表的是設備的運行模式 (Operating mode) 縮減，而不是設計缺失，嚴禁 LLM 腦補補齊未連接的訊號。

---

## 3. 規則格式 (Pattern YAML) 詳細說明

本 Skill 透過載入自定義的 YAML 檔案 (`pattern_loader.py`) 進行匯流排與子系統偵測，格式定義如下：

```yaml
name: "I2C"                    # (字串) 子系統或 Pattern 名稱，如 "I2C", "SPI"
category: bus                  # (字串) 類別，如 bus, interface, power, tree
description: "I2C interface"   # (字串) 給人類與 LLM 閱讀的用途描述

signals:                       # (陣列) 構成該子系統所必須具備的訊號清單
  - role: scl                  # (字串) 該訊號在子系統中的角色 (例如 I2C 的 scl)
    patterns:                  # (字串陣列) Python 正則表達式，用於配對 net_name (例如 "(?i)^SCL$")
      - "(?i)^SCL$"
      - "(?i)^GPIO0$"
    required: true             # (布林) 是否為必備訊號。若為 true 且未匹配到，則整個 Bus 不成立 (預設: true)
    group_key: true            # (布林) 群組識別鍵。若為 true，會從 net_name 擷取字首/字尾 (例如擷取 I2C_1_SDA 中的 "I2C_1")，藉此把屬於同一個 Bus 實體的多條訊號歸綁在一起 (預設: false)

controller:                    # (物件, 選擇性) 控制器辨識設定
  detect_by: core_component    # 辨識方式。如 "core_component" 代表直接指派系統偵測出分數最高的 MCU 作為控制器。

participants:                  # (物件, 選擇性) 參與者過濾規則
  filter:                      # (陣列)
    - reference_prefix: ["R", "C", "L", "D", "TP"]  # 排除掉被動元件、測試點，只留下真正的 IC 參與者
  exclude_controller: true     # (布林) 在參與者清單中是否要隱藏(排除)控制器本身

extra_fields:                  # (物件, 選擇性) 額外的擴充資料欄位
  field_name:
    type: string
    source: static             # 來源可為 static 或 infer
    default: "value"
```

---

## 4. 規則比對審查邏輯 (Pattern Matching Logic)

CLI 中的 `subsystem_detector.py` 負責載入上述 YAML 進行自動審查，處理流程與判讀情況如下：

1.  **訊號配對 (Step 1: Signal Matching)**
    遍歷圖譜中所有的 `net_name`，與 YAML 中 `signals[].patterns` 進行正則表達式驗證。將成功匹配的 Net 依照其 `role` (如 `sda`, `scl`) 進行分類。
2.  **訊號分組 (Step 2: Signal Grouping)**
    如果某個 `role` 設定了 `group_key: true`，程式會分析匹配的 `net_name` (例如 `SPI2_MOSI`)，擷取出共通前綴/後綴群組 ID (`SPI2`)。接著會去其他的 role 候選清單中尋找同樣帶有 `SPI2` 標籤的 `MISO`, `CLK` 訊號，將它們綁定成單一一個實體 (Instance)。如果沒有 `group_key`，則視為單一預設群組。
3.  **必備檢查 (Step 3: Required Check)**
    對於每一個分組，檢查其是否具備了所有標記為 `required: true` 的訊號。若發生缺失 (例如有 I2C_SDA 卻找不到 I2C_SCL)，則判定該實體無效並丟棄。
4.  **參與者搜索 (Step 4: Participant Discovery)**
    針對成功成團的訊號群組，透過 Connectivity 圖譜反向尋找連接在這些 Net 上的所有零件。套用 `participants.filter` 規則，剔除掉 R/C/L 被動元件，留下來的就是掛載在該 Bus 上的有效 IC 裝置。
5.  **信心指數計算 (Step 5: Calculate Confidence)**
    最終化審查結果，給予 `0.0 ~ 1.0` 的信心度分數。必備訊號完全具備會給予基礎分，若尋獲的有效 IC 參與者數量大於等於 2 甚至 4 個，會額外提高信心分數，確認這是一條真實有效的匯流排。

### 採用 LLM 的動態規則產生提示 (Dynamic Pattern Strategy)
當使用者詢問特定匯流排拓撲，但內建的 Pattern 抓取不到時，LLM 代理的行為準則 (Prompt) 指示：
1. **不要宣告「找不到」:** 內建的 regex (如 `(?i)I2C.*SDA`) 可能不符合該專案的命名常規 (例如設計師把 I2C 接在 `GPIO0` 且命名為 `GPIO0`)。
2. **手動探勘:** LLM 必須先下達 `query --net --match` 或是直接搜尋相關 Component 的引腳，找出專案實際使用的精確 `net_name`。
3. **動態撰寫 Custom YAML:** 依據上述查出來的實際名稱，LLM 必須建立一個暫時的 `custom_pattern.yaml` 檔案，將確切的 net_name (或精確的正則) 寫入 `signals[].patterns` 內。
4. **重新驗證:** LLM 再次下達 `query --pattern /tmp/custom_pattern.yaml` 指令，利用系統強大的參與者與群組分組邏輯來找出所有裝置並回報給使用者。
