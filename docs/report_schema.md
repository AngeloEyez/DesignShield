# DRC 報告資料規格標準 (DRC Report Output Contract)

本文檔定義線路設計規則檢查系統 (Schematic DRC System) 產出的最終分析報告資料規格。此規格適用於後端 Report Generation 模組輸出、PostgreSQL 落地儲存以及前端 PrimeVue Dashboard 渲染。

## 1. 總結儀表板 (Summary Dashboard Schema)

```json
{
  "task_id": "c1f7b822-491a-4d4b-9e45-817e94a87e21",
  "project_name": "MainBoard_RevA",
  "created_at": "2026-10-05T16:00:00Z",
  "completed_at": "2026-10-05T16:02:15Z",
  "total_execution_time_seconds": 135.2,
  "summary": {
    "total_rules_checked": 42,
    "pass_count": 35,
    "fail_count": 4,
    "warning_count": 2,
    "skip_count": 1,
    "pass_rate_percentage": 83.33,
    "by_category": {
      "Bus Integrity": { "pass": 12, "fail": 2, "warning": 0 },
      "Power Domain": { "pass": 10, "fail": 1, "warning": 1 },
      "Pin Connection": { "pass": 8, "fail": 1, "warning": 0 },
      "Passive Component": { "pass": 5, "fail": 0, "warning": 1 }
    }
  }
}
```

## 2. 單一檢測項目資料規格 (Check Item / Violation Schema)

每條套用的規則，不論最終是 `PASS`、`FAIL` 或 `WARNING`，皆會產出一筆對應紀錄：

| 欄位名稱 | 型別 | 必填 | 說明 |
| :--- | :--- | :---: | :--- |
| `item_id` | String (UUID) | 是 | 單一檢測結果唯一識別碼 |
| `rule_id` | String | 是 | 對應規格庫的 Rule ID（例如 `RULE-BUS-I2C-001`） |
| `rule_category` | String | 是 | 規則類別（如 `Bus Integrity`、`Power Domain`、`Pin Connection`） |
| `rule_title` | String | 是 | 人類易讀的中文規則標題（如 `I2C 匯流排地址唯一性檢查`） |
| `check_type` | Enum | 是 | 檢測方式：`HEURISTIC`（純程式圖論演算法）或 `LLM`（語意邏輯推理） |
| `status` | Enum | 是 | 檢測狀態：`PASS`、`FAIL`、`WARNING`、`SKIPPED`、`ERROR` |
| `severity` | Enum | 是 | 嚴重度等級：`CRITICAL`、`HIGH`、`MEDIUM`、`LOW`、`INFO` |
| `target_nodes` | Object | 是 | 受確認的電路節點清單（包含 components 與 nets） |
| `description` | String | 是 | 檢測結果的詳細說明與違規原因陳述 |
| `comment` | String | 否 | 工程建議、修正方針或備註事項（Optional） |
| `evidence_trail` | Object | 是 | 檢驗佐證：包含程式比對日誌、數值計算結果或 LLM 推理歷程與 Langfuse Trace ID |

### 完整單項 JSON 範例 (FAIL 案例)
```json
{
  "item_id": "v-7d9a8e21-001",
  "rule_id": "RULE-BUS-I2C-001",
  "rule_category": "Bus Integrity",
  "rule_title": "I2C 匯流排地址唯一性檢查",
  "check_type": "HEURISTIC",
  "status": "FAIL",
  "severity": "CRITICAL",
  "target_nodes": {
    "components": ["U6", "U16"],
    "nets": ["I2C_SCL", "I2C_SDA"],
    "page_indices": [2, 4]
  },
  "description": "在同一組 I2C 匯流排上發現兩顆元件 (U6, U16) 之 7-bit 實體位址衝突（均為 0x44）。此兩顆晶片型號皆為 SHT40-AD1B-R2，將導致 I2C 通訊定址失敗。",
  "comment": "建議將其中一顆更換為不同地址後綴的封裝型號（例如 SHT40-BD1B 地址為 0x45），或將其中一顆遷移至另一組未佔用的 I2C 介面。",
  "evidence_trail": {
    "bus_name": "I2C_BUS_0",
    "detected_devices": [
      { "ref": "U5", "mpn": "BQ27220", "address": "0x55" },
      { "ref": "U6", "mpn": "SHT40-AD1B-R2", "address": "0x44" },
      { "ref": "U14", "mpn": "PCF8563M/TR", "address": "0x51" },
      { "ref": "U15", "mpn": "LSM6DS3TR-C", "address": "0x6A" },
      { "ref": "U16", "mpn": "SHT40-AD1B-R2", "address": "0x44" }
    ],
    "collision_address": "0x44",
    "trace_source": "algorithmic_connectivity_matcher",
    "execution_time_ms": 14.5
  }
}
```

### 完整單項 JSON 範例 (LLM PASS 案例)
```json
{
  "item_id": "v-7d9a8e21-002",
  "rule_id": "RULE-LLM-SD-MODE",
  "rule_category": "Interface Mode",
  "rule_title": "MicroSD 介面工作模式合理性確認",
  "check_type": "LLM",
  "status": "PASS",
  "severity": "INFO",
  "target_nodes": {
    "components": ["J2", "U1"],
    "nets": ["SD_MOSI", "SD_CLK", "SD_CS", "GPIO8"],
    "page_indices": [3]
  },
  "description": "MicroSD 卡槽 J2 之 D1/D2/D3 僅接至 ESD 保護二極體未進主控，D0/CLK/CMD 正確連接至主控 SPI 腳位 (MOSI, CLK, GPIO8)，符合標準 SPI 模式設計意圖。",
  "comment": "介面已降額配置為 SPI 模式，速率受限於 SPI Clock，若未來需要高傳輸頻寬建議補齊 4-bit SDIO 走線。",
  "evidence_trail": {
    "llm_provider": "litellm/gemini-2.5-pro",
    "langfuse_trace_id": "lf-tr-902318491823",
    "llm_reasoning_summary": "已比對 J2 的 8 支引腳連線關係，D1~D3 確實無到達 U1 之網路路徑，僅 D0 與控制訊號直連，CS 訊號受 GPIO8 驅動，確認為故意設計之 1-bit SPI 模式。",
    "execution_time_ms": 2840.0
  }
}
```
