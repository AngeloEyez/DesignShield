# 產品規格書：線路設計規則檢查系統 (Schematic DRC System)

## 1. 產品概述

本專案旨在開發一套自動化的「線路設計規則檢查系統」(Schematic Design Rule Check System)。系統參考並整合 `schematic-analyzer` 的核心工作流程，提供硬體工程師一個直觀的 Web 介面，以自動化分析電路圖 (Schematics)，找出潛在的設計缺陷與規則違反 (DRC Violations)。系統結合大語言模型 (LLM) 輔助分析，採用圖譜分析技術 (Graph Analysis)，並基於 Postgres DBOS (Durable Execution) 確保任務的可靠性與斷點接續。

## 2. 系統架構與技術選型

### 2.1 整體架構 (Monorepo)
* **儲存庫管理**: 採用單一儲存庫 (Monorepo) 架構，統一管理前端、後端 API、DBOS 任務工作節點以及共用模組。
* **模組化設計**: 各個套件獨立，透過統一的介面和 Logging 機制溝通。

### 2.2 前端 (Frontend)
* **框架**: Vue.js 3 + TypeScript
* **UI 元件庫**: PrimeVue v4 (以 Dashboard 模式呈現)
* **狀態管理**: Pinia

### 2.3 後端 (Backend & API)
* **API 框架**: FastAPI (Python) - 提供高效能、非同步 RESTful API。
* **架構原則**: 無狀態 API (Stateless API)，資料一律落地至資料庫或儲存空間。此設計確保了未來擴充至多伺服器或加入認證授權機制時的平滑過渡。

### 2.4 資料庫與可靠執行 (Database & Durable Execution)
* **資料庫選型**: **PostgreSQL**。
  * 作為系統核心儲存，包含任務、規則、報告等業務資料。
* **可靠執行引擎**: **DBOS (Durable Execution)**
  * **完全移除 Celery 與 Redis**：改採用奠基於 Postgres 的 DBOS 框架處理非同步與長時間運行的 DRC 任務。
  * **原生斷點接續 (Checkpointing & Resume)**：DBOS 原生支援狀態持久化，當伺服器意外重啟時，任務能從上次中斷的步驟 (Step) 自動無縫接續，不需手動處理複雜的狀態機。
  * **進度追蹤 (`step_status` table)**：透過 DBOS 的自訂狀態表記錄執行進度，前端 Vue 3 可透過 FastAPI 輪詢或 SSE 取得狀態，並利用 PrimeVue 的 Timeline 或 Steps 元件視覺化呈現。
  * **雙軌執行路徑 (Dual-Execution Path)**：
    * **輕量預先分析 (Lightweight Pre-analysis)**：在上傳階段同步或以極短非同步執行，快速解析元件特徵，避免阻礙後續排隊任務 (Head-of-line blocking)。
    * **重型 DRC 任務 (Heavy DRC Workflow)**：交由 DBOS 排隊執行，包含耗時的圖譜構建、傳統啟發式規則比對與 LLM 推理。

### 2.5 LLM 整合與本地部署 (LLM Integration Layer)
* **核心套件**: **LiteLLM** 作為統一的 API 網關 (Proxy) 與適配層。
* **本地 LLM 優先**: 系統針對企業內部安全性與隱私，優先整合本地部署的 LLM。
  * **端點設定**: 使用 OpenAI API 格式指向本地伺服器 (例：`http://192.168.1.5:8000/v1`)，API Key 留空。
  * **吞吐量考量**: 考量本地 LLM 的併發處理能力限制，輕量分析與重型任務必須妥善分離，避免 API 擁塞。

### 2.6 系統觀測性與除錯 (Comprehensive Observability)
* **全鏈路追蹤 (Langfuse)**:
  * 系統全面採用 Langfuse 追蹤整體執行流程，包含 Python 函式耗時、DB 查詢、外部 API 請求。
  * **獨立部署設定檔 (Observability Profile)**: 考量小型團隊 (5-20 人) 資源，Langfuse 將定義為獨立的 Docker Compose Profile (`observability`)，可按需啟動 (On-demand)。
  * **優雅降級 (Graceful Degradation)**: 後端程式碼必須實作容錯機制，當 Langfuse 服務未啟動時，系統仍能正常運行，不會阻斷核心 DRC 分析。

### 2.7 檔案與日誌生命週期管理 (Lifecycle & Garbage Collection)
* **非寫死原則 (Configurable Retention via .env & UI)**:
  * 所有檔案保留天數不由代碼寫死，由 `.env` 提供預設值並同步至資料庫。
  * 支援透過 Web UI 調整與套用生效。
* **垃圾回收 (Garbage Collection)**:
  * 任務完成後，上傳的壓縮包與產出的報告 **預設保留 7 天**。
  * 差異化執行產生的中繼檔案，依過期策略定期由排程清除。

## 3. 核心處理流程 (Schematic Analyzer Workflow)

1. **解封與格式預檢**: 接受 `.zip`/`.7z`，包含 XML 與 Netlist。
2. **輕量預先分析 (Pre-analysis)**: 快速掃描元件與匯流排，回傳推薦規則 (由 Web UI 呈現樹狀圖)。
3. **DBOS 可靠執行 (Heavy DRC Workflow)**:
   * **圖譜構建**: NetworkX 構建二分圖。
   * **傳統規則比對 (Heuristic DRC)**。
   * **LLM 邏輯推理**: 呼叫本地 LLM (`http://192.168.1.5:8000/v1`)。
   * 以上步驟皆受 DBOS 保護，中斷可自動接續。
4. **報告彙整與資源清理**: 產出 JSON/PDF 報告，清理暫存中繼檔。

## 4. Web UI 介面與功能模組 (Dashboard)

### 4.1 儀表板總覽 (Healthy Status & Overview)
* 顯示 API、DBOS Worker、DB 狀態。
* 顯示當前排隊中的任務與 Langfuse 統計(若啟用)。

### 4.2 任務排程與進度 (Task Queue & Timeline)
* 採用 PrimeVue Timeline / Steps 元件，視覺化展示 DBOS `step_status` 表的進度。
* 提供「取消任務」、「細部逾時設定」介面。

### 4.3 線路確認模組 (Schematic Validation & DRC)
1. **上傳線路 (Upload)**: `.zip` / `.7z` 支援。
2. **預先分析與規則建議**: UI 呈現樹狀圖，供勾選規則。
3. **進度與狀態 (Status)**:
   * 透過 SSE 或輪詢查詢 API，獲取 DBOS `step_status` 變化，以 Timeline 動態更新。
   * 若任務斷線重連，依 DBOS 原生紀錄重新回放狀態。
4. **結果檢視**: 呈現違規列表與報告匯出。

### 4.4 規則庫維護 (Rule Library Management)
* CRUD 傳統與 LLM 規則。

### 4.5 系統維護與設定模組 (System Settings)
* **檔案保留週期設定**: 調整 `upload_retention_days` 等參數。
* **即時套用**: 調整後寫入資料庫並觸發排程器重新讀取。

## 5. 規則引擎與 LLM 協作架構 (Rule Engine Architecture)
本系統將寫死於程式碼內的演算法抽出，升級為由 YAML 驅動的泛用規則引擎，並結合 LLM 作為深度排查助手。詳細架構與設計邏輯請參見：[DRC 規則定義與 LLM 協作架構指南 (Rule Definition & LLM Copilot Architecture)](./rule_engine_architecture.md)。

## 6. 未來擴充與階段性規劃 (Future Roadmap)
* 多使用者認證與授權 (Authentication & Authorization)。
* Datasheet 解析與 RAG 整合。
