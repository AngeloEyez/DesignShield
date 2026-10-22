# DesignShield Level 3 DRC 設計規則驗證手冊 (Design Rule Check Guide)

本手冊為 DesignShield 系統 **Level 3 設計規則審計 (DRC Validation)** 之正式規格文件。
所有 DRC 規則均存放於 `patterns/level3_rules/` 目錄，以宣告式 YAML (IaC) 定義，並支援就近同檔名之 Python 伴生腳本執行深度拓撲與規格比對。

> [!TIP]
> 快速建立新 DRC 規則：可直接複製官方標準範本：
> - 規則定義範本：[`patterns/level3_rules/_template.yaml`](file:///home/gaven/DesignShield/patterns/level3_rules/_template.yaml)
> - 伴生腳本範本：[`patterns/level3_rules/_template.py`](file:///home/gaven/DesignShield/patterns/level3_rules/_template.py)
> 所有以底線 `_` 開頭之檔案會被引擎自動略過。

---

## 1. 核心機制與設計哲學

1. **職責邊界 (Scope & Responsibility):**
   - 針對電路網段 (`net`) 或元件節點 (`component`) 執行深度硬體規格驗證。
   - 涵蓋信號完整性 (Signal Integrity)、電源降額 (Power Derating)、短路防護 (Power-Ground Short)、差分極性 (P/N Swap)、差分通道導通性 (Differential Channel Continuity) 等關鍵硬體檢查。
2. **伴生腳本零寫死自動探索 (Zero-Hardcoding Companion Script Discovery):**
   - 規則 YAML 與其伴生 Python 腳本**同目錄同名成對存放**（例如 `pn_swap_check.yaml` 與 `pn_swap_check.py`）。
   - 執行引擎優先依檔案相對路徑推導同名腳本，YAML 中之 `script_path` 欄位**可直接省略**。資料夾重構或搬移時絕不斷線。
3. **真實資料審計原則 (Real-Data Audit Principle):**
   - 當規則或伴生腳本需要查詢 PartDB 零件規格但資料庫中無該料號時，**嚴禁偽造假資料或猜測引腳特性**。
   - 腳本應回傳 `RuleSkipped` 標記為資料缺失（UI 以灰色邊條提示），待工程師補充真實 PartDB 資料後重新審計。
4. **全自動遞迴探索 (Recursive Auto-Discovery):**
   - 引擎使用 `os.walk` 遞迴掃描 `patterns/level3_rules/` 下**所有子目錄**。
   - 工程師可自由依檢驗領域劃分子資料夾（如 `interfaces/`, `power/`, `safety/`, `high_speed/` 等），新規則與伴生腳本即放即用。

---

## 2. 目錄架構建議

官方推薦的一級子目錄組織架構如下：

```text
patterns/level3_rules/
├── _template.yaml          # 官方規則定義範本 (引擎自動略過)
├── _template.py            # 官方伴生腳本範本 (引擎自動略過)
├── tags.schema.json        # 規則標籤白名單 Schema
├── README.md               # 本開發手冊
├── interfaces/             # 介面協定與通訊匯流排 DRC
│   ├── differential_channel_continuity_check.yaml
│   ├── differential_channel_continuity_check.py
│   ├── i2c_pullup_existence.yaml
│   ├── i2c_pullup_existence.py
│   ├── i2c_stm32_dynamic.yaml
│   ├── i2c_stm32_dynamic.py
│   ├── level_shift_validation.yaml
│   ├── sd_interface_mode.yaml
│   ├── pn_swap_check.yaml
│   └── pn_swap_check.py
└── power/                  # 電源域、降額與去耦電容 DRC
    ├── decoupling_existence.yaml
    ├── power_derating.yaml
    ├── power_ground_short.yaml
    └── power_sequence_compatibility.yaml
```

---

## 3. 規則 YAML 綱要 (`Level3Rule`)

每個 Level 3 規則檔案包含以下頂層欄位：

| 欄位名稱 | 型別 | 必填 | 說明 |
| :--- | :--- | :---: | :--- |
| `name` | `string` | **是** | 規則唯一識別碼，必須符合小寫蛇形 (`snake_case`) |
| `enabled` | `boolean` | 否 | 是否啟用該規則 (預設 `true`) |
| `description` | `string` | 否 | 規則中文說明與工程檢驗目標 |
| `tags` | `list` | **是** | 規則標籤清單，每項標籤必須於 `tags.schema.json` 白名單中定義 |
| `severity` | `string` | **是** | 違規嚴重度：`"Fatal"`, `"Error"`, `"Warning"`, `"Info"` |
| `trigger_conditions` | `object` | **是** | 觸發比對條件，定義何種圖論節點觸發此規則審計 |
| `check_logic` | `list` | **是** | 檢驗邏輯步驟清單 (`python_script` 或 `topology_check`) |

---

## 4. 觸發條件 (`trigger_conditions`)

指定需受檢的目標節點類型 (`net` 或 `component`) 與屬性過濾條件：

```yaml
trigger_conditions:
  graph_match:
    attributes:
      type: "net"
      net_type: "Differential"
      diff_polarity: "P"
```

- 若 `type: "net"`：可指定 `net_type`、`diff_polarity`、`bus_type` 等由 Level 2 注入之屬性。
- 若 `type: "component"`：可指定 `sub_category`、`category` 等由 Level 1 注入之屬性。

---

## 5. 檢驗邏輯 (`check_logic`)

### 5.1 模式 A: Python 伴生腳本 (`type: python_script`, 推薦)

適用複雜動態邏輯、端到端通道穿透追蹤、PartDB 查表或電氣參數量測：

```yaml
check_logic:
  - type: "python_script"
    # script_path 可直接省略，系統自動就近尋找同名 .py 伴生腳本
```

伴生腳本入口函式規範：

```python
def execute(
    context: RuleContext,
    graph_api: GraphAPI,
    part_db: PartDB,
    params: Dict[str, Any] = None
) -> Union[List[RuleViolation], RulePass, RuleSkipped, RuleResult]:
```

- **合格 (PASS):** 回傳 `RulePass(message=..., evidence=...)`，提供審計歷程追溯。
- **違規 (FAIL):** 回傳 `[RuleViolation(error_message=..., recommendation=..., severity=..., evidence=...)]`。
- **缺失跳過 (SKIPPED):** 回傳 `RuleSkipped(message=..., evidence=...)`。

### 5.2 模式 B: 宣告式拓撲斷言 (`type: topology_check`)

適用單純靜態幾何或電氣規則，完全以 YAML 宣告：

```yaml
check_logic:
  - type: "topology_check"
    asserts:
      - condition: "capacitor_voltage_derating"
        node: "${context.target}"
        min_derating_ratio: 1.26
        error_message: "電容耐壓不足"
        recommendation: "建議選用額定耐壓較高之規格"
```

---

## 6. 本地校驗與快取重新編譯

每次新增或修改 Level 3 規則後，請執行統一校驗腳本：

```bash
# 執行規則 YAML、Tags 白名單與伴生腳本 AST 安全性審查
python3 scripts/validate_rules.py

# 呼叫 API 重新熱載入與快取預熱編譯
curl -X POST http://localhost:8000/api/v1/patterns/reload
```
