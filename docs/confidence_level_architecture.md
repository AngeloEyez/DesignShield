# Level 1~3 通用信心度分級架構與判定門檻規範 (Universal Confidence Level Architecture Specification)

## 1. 架構背景與設計目標 (Background & Objectives)

在硬體語意圖譜（Hardware Semantic Knowledge Graph）的構建與自動化設計規則檢查（DRC）流程中，不同層級對訊號與元件的識別具備相依性：
- **Level 1**：解析原理圖與網表，執行元件初步分類與引腳建立。
- **Level 2**：透過拓撲模式引擎（`TopologyPatternEngine`）比對電源、接地、差分訊號與通訊匯流排，將物理與協定屬性打上圖譜節點。
- **Level 3**：根據圖譜節點屬性觸發端到端檢驗（如極性反接、上拉電阻缺失、電容對稱性等）。

### 歷史痛點 (Historical Pain Points)
過去各層級對「信心度（Confidence）」的定義缺乏統一分級與門檻管制：
1. **弱特徵越級污染**：部分總線規則（如舊版 `730_usb_typec.yaml`）允許單純以 `_DP` 結尾的網路獲得 0.2 信心度，但引擎只要比對成功即直接打上 `bus_type = "USB"`。
2. **跨總線誤判連鎖反應**：非 USB 的差分線（如 DDR 的 `M_A_DDR2_DQS4_DP`、PCIe 走線）因結尾帶有 `_DP`，被誤冠上 `bus_type = "USB"`，進而觸發 Level 3 `pn_swap_check` 進行檢驗，造成偽檢驗與報表雜訊。
3. **規則間標準不齊**：不同匯流排規則（I2C, SPI, JTAG, USB, UART）對「網路名稱」與「引腳名稱」賦予的信心度差異懸殊，缺乏統一的模型指導。

為此，DesignShield 建立 **Level 1~3 全局通用信心度分級模型 (Universal Confidence Tier Model)**。

---

## 2. 通用信心度分級模型 (Universal Confidence Tier Model)

| 信心度區間 | 語意等級 (Tier) | 定義與情境 | Level 1 判定行為 | Level 2 拓撲/總線行為 | Level 3 DRC 觸發行為 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **0.80 ~ 1.00** | **High**<br>(確定性物理鐵證) | 具備原理圖明確符號（如 Power/GND Symbol）、全稱精確相符（`VCC3V3`, `GND`）、或標準原廠完整料號前綴。 | 確定識別，直接定案，絕不落入 LLM。 | 確定識別，直接賦予屬性與類型。 | 完整信任，標準執行 DRC。 |
| **0.60 ~ 0.79** | **Medium-High**<br>(強特徵) | 網路名稱明確包含標準協定關鍵字（如 `TCP0_RT_SSTX0_P`, `I2C1_SDA`），或元件標註與多引腳完全吻合。 | 確定識別，直接定案。 | 達到確定性門檻（$\ge 0.6$），直接賦予類型，無需模糊審查。 | 完整信任，標準執行 DRC。 |
| **0.40 ~ 0.59** | **Medium**<br>(中等特徵 / 單一引腳 / 協定前綴) | • 網路名稱具備協定標籤（0.50）<br>• IC 原廠引腳命名吻合（0.40） | 模糊元件，若停用 LLM 則走啟發保底。 | **總線最低判定門檻（0.40）**：<br>達到此門檻方可賦予 `is_bus` 與 `bus_type`。 | 可設定 `min_confidence`，低於門檻不予觸發。 |
| **0.20 ~ 0.39** | **Low**<br>(弱特徵 / 泛用後綴) | 泛用型後綴或縮寫（如 `_DP`, `_DM`, `_P`, `_N`, `INT`, `CS`），極易與其他匯流排（如 DDR, PCIe）衝突。 | 絕不單獨採納。 | **嚴格禁止單獨指派總線**！<br>僅可作為輔助特徵（需與其他特徵相加達 $\ge 0.40$）。 | **嚴禁單獨觸發協定級 Level 3 檢查**。 |
| **0.00 ~ 0.19** | **Noise**<br>(極弱特徵 / 雜訊) | 模糊字串微弱匹配。 | 忽略。 | 忽略。 | 忽略。 |

---

## 3. 各層級規範與判定機制實作 (Implementation Details)

### 3.1 Level 1：元件與初始電氣網路
- **模糊元件門檻**：`0.60`
  - 元件分類器評估結果信心度 $< 0.60$ 且為具備電氣特性的主動元件時，標記為 `Ambiguous Component`，送交 LLM Fallback 或保底策略處理。
- **物理鐵證優先**：
  - 連接 Power Symbol / Ground Symbol 之網路賦予信心度 `1.00`。

### 3.2 Level 2：網路與拓撲匯流排引擎 (`TopologyPatternEngine`)
- **總線最低判定門檻**：`DEFAULT_BUS_MIN_CONFIDENCE = 0.40`
  - 當規則類別為 `Communication` 時，該網路獲得的最高信心度必須 $\ge 0.40$ 才能被寫入 `is_bus = True` 與 `bus_type = "..."`。
  - 低於 `0.40` 之弱特徵（如 0.2 的單純後綴）將被引擎記錄並跳過，防止對其他介面造成語意污染。
- **規則層級覆寫支援**：
  - YAML 規則模型 (`TopologyRule`) 支援可選欄位 `min_confidence`。若特定規則有特殊判定需求，可在 YAML 中自訂覆寫門檻（例如 `min_confidence: 0.30` 或 `0.50`）。
- **匯流排 YAML 訊號標準三段式結構**：
  所有 Communication 類別的規則（如 `700_i2c`, `710_spi`, `720_jtag`, `730_usb_typec`, `740_uart`）均應遵循標準分級：
  - **情境 A (0.50 ~ 0.60)**：網路名稱帶有標準協定前綴（如 `USB_.*DP`, `I2C.*SCL`, `SPI.*MOSI`）。
  - **情境 B (0.40)**：IC 原廠引腳命名（Pin Name，如 `DP`, `SCL`, `MOSI`）。
  - **情境 C (0.10 ~ 0.20)**：泛用後綴（如 `_DP`, `_DM`）或弱命名；**若容易造成跨領域誤判（如差分線 _DP 與 DDR 衝突），應予以註解或加入負向排除正則**。

### 3.3 Level 3：DRC 規則檢驗引擎 (`Level3Engine`)
- **乾淨的受測標的**：
  由於 Level 2 總線門檻有效阻絕了弱特徵誤標，Level 3 規則在 `trigger_conditions` 宣告 `bus_type: "USB"` 時，能 100% 確保受測網路均為合法 USB 訊號，不再受 DDR/PCIe 差分線干擾。
- **P 端主導雙端合一審計**：
  搭配 `diff_polarity: "P"`，差分對僅由正端觸發一次，負端由腳本牽引，並利用 `covered_nets` 實現通道級靜默去重。

---

## 4. 規則撰寫指南與範例 (Authoring Guidelines)

### 4.1 匯流排規則 YAML 範例 (`patterns/level2_topology/buses/`)
```yaml
name: "example_bus"
category: "Communication"
priority: 700
# min_confidence: 0.40  # 可選，預設採用引擎之 0.40

signals:
  - role: "BUS_DATA"
    required: true
    group_key: true
    matches:
      match_any:
        # 情境 A (高信心度 0.50): 明確協定標籤之網路名稱
        - match_all:
            - net_name_regex: "(?i)EXAMPLE.*DATA"
          confidence_contribution: 0.50

        # 情境 B (中信心度 0.40): IC 原廠標準引腳名稱
        - match_all:
            - pin_name_regex: "(?i)DATA"
          confidence_contribution: 0.40

        # 情境 C (弱特徵 0.20): 輔助弱比對（需配合負向排除，避免誤判）
        - match_all:
            - net_name_regex: "(?i)^(?!.*(?:DDR|PCIE|MIPI)).*_DATA$"
          confidence_contribution: 0.20
```

### 4.2 負向排除模式 (Negative Lookahead Regex)
當訊號特徵無法避免與其他領域命名重疊時，推薦使用正規表示式負向前瞻進行排除：
```regex
(?i)^(?!.*(?:DDR|PCIE|PCI|LAN|ETH|MIPI|LVDS)).*(?:_DP\b|D\+)$
```
