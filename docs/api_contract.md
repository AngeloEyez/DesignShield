# API 規格與契約 (API Contract)

本文檔定義前端 (Vue 3) 與後端 (FastAPI) 之間的溝通介面與資料模型。

> [!IMPORTANT]
> **維護原則：給後續開發的 AI Agent**
> 任何針對 API Router 的增刪改（包含 Request/Response Schema、URL Path、Query Parameters），**務必同步更新此文件**，以確保前後端對接的單一事實來源 (Single Source of Truth) 不會產生分歧。

---

## 1. 任務管理與 DRC 分析流程 (Task & Analysis)

### 1.1 上傳電路檔並取得預先分析 (Upload & Pre-analyze)
* **Endpoint**: `POST /api/v1/tasks`
* **Content-Type**: `multipart/form-data`
* **Request Parameters**:
  * `file`: (File) `.zip` 或 `.7z` 壓縮檔
  * `project_name`: (String) 專案名稱
* **Response (200 OK)**:
```json
{
  "task_id": "c1f7b2e0-5d6a-4b3f-9e1a-8c2d3f4e5a6b",
  "project_name": "My_Motherboard",
  "status": "READY_FOR_RUN",
  "pre_analysis_summary": {
    "buses": ["I2C", "SPI"],
    "platforms": ["STM32"]
  },
  "recommended_rules": [
    {
      "id": "i2c_pull_up_existence",
      "name": "I2C 匯流排上拉電阻存在性檢查",
      "category": "Signal Integrity"
    }
  ]
}
```

### 1.2 確認規則並啟動正式分析 (Start Formal DRC)
* **Endpoint**: `POST /api/v1/tasks/{task_id}/run`
* **Content-Type**: `application/json`
* **Request Body**:
```json
{
  "selected_rule_ids": ["i2c_pull_up_existence", "power_capacitor_derating"]
}
```
* **Response (202 Accepted)**:
```json
{
  "task_id": "c1f7b2e0-5d6a-4b3f-9e1a-8c2d3f4e5a6b",
  "status": "PROCESSING",
  "message": "DRC 任務已進入 DBOS 執行佇列"
}
```

### 1.3 訂閱即時進度更新 (SSE Events)
* **Endpoint**: `GET /api/v1/tasks/{task_id}/events`
* **Content-Type**: `text/event-stream`
* **說明**: 前端透過 Server-Sent Events (SSE) 訂閱 `step_status` 的即時變化，用於 PrimeVue Timeline 渲染。若斷線重連，系統應透過 DBOS 紀錄回放歷史。
* **Event Stream Payload (範例)**:
```text
event: step_update
data: {"step_name": "PARSE_AND_GRAPH", "status": "COMPLETED", "timestamp": "2026-10-05T20:00:00Z", "log_message": "圖譜構建完成 (節點: 1240)"}

event: step_update
data: {"step_name": "LLM_RULE: sd_interface_mode_reasoning", "status": "PROCESSING", "timestamp": "2026-10-05T20:00:01Z", "log_message": "正在呼叫本地 LLM 進行語意分析..."}
```

### 1.4 取得最終 DRC 報告 (Get Report)
* **Endpoint**: `GET /api/v1/tasks/{task_id}/report`
* **Response (200 OK)**:
```json
{
  "task_id": "c1f7b2e0-5d6a-4b3f-9e1a-8c2d3f4e5a6b",
  "summary": {
    "total_rules": 2,
    "pass_count": 1,
    "fail_count": 1,
    "warning_count": 0
  },
  "violations": [
    {
      "rule_id": "power_capacitor_derating",
      "status": "FAIL",
      "target_component": "C1",
      "description": "電容耐壓降額不足",
      "suggestion_zh": "請將耐壓由 6.3V 更換為 10V 以上"
    }
  ]
}
```

### 1.5 匯出 DRC 報告 JSON (Export Report)
* **Endpoint**: `GET /api/v1/tasks/{task_id}/report/export`
* **Response (200 OK)**:
  * **Content-Type**: `application/json`
  * **Content-Disposition**: `attachment; filename="drc_report_{task_id}.json"`
  * 完整結構化審查報告 JSON 檔案串流。

## 2. 規則庫管理 (Patterns - GitOps File-based)

系統已全面單軌化採用 GitOps File-based YAML 架構，規則唯一事實來源 (SSOT) 位於 `patterns/` 目錄，廢除舊關聯式資料庫規則表。

### 2.1 取得完整 Pattern 規則庫與零件特規目錄樹 (Get Pattern Tree)
* **Endpoint**: `GET /api/v1/patterns/tree`
* **Response (200 OK)**:
```json
{
  "level1": [ ... ],
  "level2": [ ... ],
  "level3": [
    {
      "name": "power_capacitor_derating",
      "description": "電源濾波電容耐壓降額檢查",
      "category": "Power Domain",
      "_domain": "power",
      "severity": "Error",
      "check_logic": [{ "type": "topology_check" }]
    }
  ],
  "partdb": { "parts": [ ... ] },
  "tags": [ ... ]
}
```

### 2.2 熱重新載入與重新編譯規則庫快取 (Reload Patterns)
* **Endpoint**: `POST /api/v1/patterns/reload`
* **Response (200 OK)**:
```json
{
  "success": true,
  "message": "規則庫與 PartDB 重新載入並編譯成功",
  "compile_stats": {
    "level1_rules": 4,
    "level2_rules": 13,
    "level3_rules": 8,
    "partdb_parts": 2,
    "regex_compiled": 18
  }
}
```

## 3. 系統設定與運維管理 (System Settings & Operations)

### 3.1 取得所有系統設定 (Get All Settings)
* **Endpoint**: `GET /api/v1/settings`
* **Response (200 OK)**: `List[SettingResponse]` (包含 upload_retention_days, task_timeout_seconds, llm_config 等)

### 3.2 更新特定設定 (Update Setting)
* **Endpoint**: `PUT /api/v1/settings/{key}`
* **Content-Type**: `application/json`
* **Request Body**:
```json
{
  "value": { "days": 14 },
  "description": "暫存保留天數設定"
}
```

### 3.3 查詢儲存空間統計指標 (Storage Stats)
* **Endpoint**: `GET /api/v1/settings/storage-stats`
* **Response (200 OK)**:
```json
{
  "storage_root": "/app/storage",
  "uploads": { "file_count": 5, "total_bytes": 10485760 },
  "staging": { "file_count": 12, "total_bytes": 20971520 },
  "reports": { "file_count": 3, "total_bytes": 524288 },
  "total_files": 20,
  "total_bytes": 31981568,
  "total_mb": 30.5
}
```

### 3.4 觸發磁碟空間垃圾清理 (Trigger Storage Cleanup)
* **Endpoint**: `POST /api/v1/settings/cleanup`
* **Query Parameters**:
  * `retention_days`: (int, optional, 預設採用系統設定天數)
  * `dry_run`: (bool, optional, 預設 false)
  * `include_reports`: (bool, optional, 預設 false)
* **Response (200 OK)**:
```json
{
  "retention_days": 7,
  "dry_run": false,
  "deleted_files_count": 8,
  "freed_bytes": 15728640,
  "freed_mb": 15.0,
  "deleted_paths": ["/app/storage/staging/old_task_id"]
}
```
