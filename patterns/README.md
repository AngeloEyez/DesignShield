# DesignShield 規則庫與 PartDB 知識庫維護手冊 (Rule Governance & GitOps SOP)

本目錄 (`patterns/`) 為 DesignShield 系統之硬體規則庫核心真相來源 (Single Source of Truth)，完全採用 **File-based YAML (IaC)** 進行 Git 版本控制與無狀態管理。

---

## 1. 目錄架構與層級職責 (Taxonomy)

| 目錄路徑 | 層級 | 核心職責 | 執行原則 |
| :--- | :--- | :--- | :--- |
| `components/` | **Level 1** | 單一零件靜態屬性辨識 (Metadata -> Category / Functional Role) | First-Match Wins (優先級高者優先) |
| `buses/`, `power/`, `signals/` | **Level 2** | 連線語意昇華 (Nets -> Bus/Power/Differential Pairs) 與角色覆寫 | 領域解耦、加權計分 (Confidence) |
| `rules/` | **Level 3** | DRC 設計規則驗證 (拓撲斷言、嚴重度判定、違規定位) | 平行無序、獨立評估、無優先級 |
| `partdb/` | **PartDB** | 原廠規格書結構化零件特規與 `_meta` 溯源資料庫 | 介面導向 (schema_*.json 驗證) |

---

## 2. Level 3 DRC 規則結構規範

所有 Level 3 規則存放於 `patterns/rules/<domain>/<rule_name>.yaml` (最大深度兩層)：

```yaml
name: "I2C_Pull_Up_Existence"           # 規則唯一識別名稱
description: "檢查 I2C 匯流排是否具備上拉電阻"  # 說明
tags: ["I2C", "Signal Integrity"]       # 標籤 (必須存在於 tags.schema.json 白名單)
severity: "Error"                      # 嚴重程度: Fatal | Error | Warning | Info

# 觸發條件 (命中的圖譜實例會被注入為 ${context.target} 並平行生成檢查任務)
trigger_conditions:
  graph_match:
    attributes:
      type: "net"
      bus_type: "I2C"

# 檢查邏輯 (支援 topology_check, python_script, llm_agent)
check_logic:
  - type: "topology_check"
    asserts:
      - condition: "has_pullup_resistor"
        node: "${context.target}"
        error_message: "I2C 匯流排 (${context.target.net_name}) 缺少上拉電阻"
```

---

## 3. PartDB 零件規格庫規範

PartDB 存放於 `patterns/partdb/data/<PartNumber>.yaml`，必須依據 `patterns/partdb/schema/` 下對應介面的 JSON Schema 撰寫：

```yaml
pn: "STM32F405"
description: "ARM Cortex-M4 MCU"

interfaces:
  I2C:
    requires_series_resistor: false
    forbid_gnd_capacitor: true
    pullup_range_ohms: [2000, 10000]
    _meta:
      evidence: "STM32F405_Datasheet_Rev4.pdf"
      page: 45
      excerpt: "Avoid external ground capacitors on SCL/SDA to prevent RC distortion."
```

---

## 4. GitOps 新增與維護標準作業流程 (SOP)

### A. 新增 Level 3 規則
1. 於 `patterns/rules/` 下之適當網域目錄（如 `interfaces/`, `power/`）建立 `.yaml` 檔案。
2. 檢查 `tags`：若使用新標籤，需先同步更新 `patterns/rules/tags.schema.json`。
3. 嚴格填寫 `name`, `tags`, `severity`, `trigger_conditions`, `check_logic`。
4. 本地端執行校驗指令：
   ```bash
   python scripts/validate_rules.py
   ```
5. 確認回傳退出碼 `0` (驗證通過) 後，提交 Git PR。

### B. 新增 IC 零件規格 (PartDB)
1. 於 `patterns/partdb/data/<PartNumber>.yaml` 建立檔案。
2. 填寫介面參數時，**必須填寫 `_meta` 溯源出處** (`evidence`, `page`, `excerpt`)。
3. 執行 `python scripts/validate_rules.py` 確保符合對應 `schema_<interface>.json`。
4. 提交 Git PR。
