# 產品規格書：線路設計規則檢查系統 (Schematic DRC System)

## 1. 產品概述

本專案旨在開發一套自動化的「線路設計規則檢查系統」(Schematic Design Rule Check System)。系統參考並整合 `schematic-analyzer` 的核心工作流程，提供硬體工程師一個直觀的 Web 介面，以自動化分析電路圖 (Schematics)，找出潛在的設計缺陷與規則違反 (DRC Violations)。系統結合大語言模型 (LLM) 輔助分析，採用圖譜分析技術 (Graph Analysis)，並基於資源限制設計了嚴謹的排隊機制，確保系統穩定運行。

## 2. 系統架構與技術選型

### 2.1 整體架構 (Monorepo)
* **儲存庫管理**: 採用單一儲存庫 (Monorepo) 架構，統一管理前端、後端 API、異步任務 Worker 以及共用模組。
* **模組化設計**: 各個套件獨立，透過統一的介面和 Logging 機制溝通。

### 2.2 前端 (Frontend)
* **框架**: Vue.js 3 + TypeScript
* **UI 元件庫**: PrimeVue v4 (以 Dashboard 模式呈現)
* **狀態管理**: Pinia

### 2.3 後端 (Backend & API)
* **API 框架**: FastAPI (Python) - 提供高效能、非同步 RESTful API。
* **架構原則**: 無狀態 API (Stateless API)，資料一律落地至資料庫或儲存空間。此設計確保了未來擴充至多伺服器或加入認證授權機制時的平滑過渡。

### 2.4 資料庫 (Database)
* **關聯式資料庫選型**: **PostgreSQL**。
  * **考量與維護性**: 考量到任務佇列狀態、複雜的 Rule Library 關聯與未來擴充性，PostgreSQL 較 SQLite 更為穩健。為保持「好維護」的原則，將採用 Docker 容器化部署 PostgreSQL，並搭配 SQLAlchemy 等 ORM 工具進行資料庫結構遷移 (Alembic) 與管理，降低直接操作 SQL 的維護成本。

### 2.5 任務調度與排程 (Task Scheduling & Workers)
* **任務佇列**: Redis 作為 Message Broker。
* **任務執行器**: Celery (Python)。
* **資源限制與排程策略 (Crucial)**: 
  * 考量運算資源有限（特別是進行 Graph 解析與 LLM 推理時），Celery Worker 限制為 **同一時間僅執行單一任務 (Concurrency = 1)**。
  * 採用 **嚴格的 FIFO (First-In, First-Out) 排隊機制**。當系統正處理任務時，新提交的任務將進入 Redis 佇列等待，避免同時載入過多電路圖導致記憶體溢出 (OOM)。
  * **細部動作異常防護與逾時控制 (Granular Robustness & Timeouts)**:
    * 避免全任務死線：任務大小不一，不採用單一的全域任務逾時，而是針對**單一步驟動作與單一 API 呼叫**進行細顆粒度逾時控制。
    * **單一步驟運算上限 (Action Timeout)**：例如圖譜構建、特徵比對單項動作逾時，預設為 60 秒（可在 UI 系統設定調整）。
    * **單一 LLM 請求上限 (LLM Request Timeout)**：單次模型呼叫逾時預設為 45 秒（可在 UI 調整），配合最多 2 次重試；若失敗則標記該項規則為逾時錯誤，不中斷其餘檢測。
    * **任務主動取消 (Task Revocation)**：支援在 Web UI 即時取消佇列中或正在執行的任務，Worker 收到訊號後立即中止並釋放佇列與 Redis 鎖。
    * **即時心跳、日誌流與進度推播 (Real-time Heartbeat & Log Streaming)**:
      * **全鏈路日誌流**: Worker 於每一細項步驟、圖譜快取載入、每條規則檢測開始/結束、LLM 呼叫前後，均透過 Redis Pub/Sub 推播結構化 Log 事件至前端 WebSocket/SSE，讓工程師能即時掌握秒級內部進度。
      * **差異化執行專屬即時回報**: 若任務為斷點續跑，系統立即回報專屬 Log（如：圖譜快取載入耗時、已完成/已略過規則清單與統計、剩餘待驗證規則清單），使用者可明確看到「跳過哪些已跑項目、正在接續哪些新項目」。
      * **斷線重連歷史回放 (Log Replay)**: Log 除即時廣播外，同步批量落地至資料庫 `drc_tasks.execution_logs`。若使用者刷新瀏覽器或切換頁面後重新進入，系統自動重播完整的歷史 Log，杜絕資訊落差。
  * **檢查點持久化與斷點接續 (Checkpointing & Resume)**:
    * **細粒度檢查點 (Rule-Level Checkpoint)**：Worker 執行檢測時，每完成一條規則（無論 Heuristic 或 LLM），立即將單項檢查結果寫入資料庫的 `checkpoint_data` 欄位並更新已完成清單 (`completed_rule_ids`)。
    * **意外重啟復原 (Crash Recovery & Resume)**：伺服器或 Worker 異常重啟後，系統自動辨識中斷任務。接續重跑時直接讀取 Checkpoint，**從上次斷開的規則無縫接續**，絕不重頭跑起。
    * **差異化執行 (Differential Execution)**：
      * 直接自硬碟快取 `/app/storage/graphs/{task_id}.pickle` 反序列化圖譜，跳過 XML/Netlist 重複解析建圖。
      * 動態計算剩餘規則：`remaining_rules = selected_rules - completed_rules`，僅對剩餘規則進行比對。
      * **零 Token 浪費**：已完成的 LLM 規則絕不重複發送請求，大幅降低 API 成本與等待時間。

### 2.6 LLM 整合適配層 (LLM Integration Layer)
* **核心套件**: **LiteLLM** 作為統一的 API 網關 (Proxy) 與適配層。
* **優勢**: 絕不在業務程式碼中寫死特定廠商 SDK，支援多提供者無縫切換 (本地端模型、OpenAI、Gemini、Claude)，並提供統一的 Retry 與 Rate Limiting。

### 2.7 系統觀測性與除錯 (Comprehensive Observability)
* **全鏈路追蹤 (Langfuse)**:
  * 不僅用於監控 LLM 的 Token 與參數，**系統將全面採用 Langfuse 來追蹤整體執行流程**。
  * **追蹤範圍包含**: 一般 Python 函式執行耗時、資料庫查詢 (DB Queries)、向量檢索、外部 API 請求，以及微服務 (API Server to Celery Worker) 之間的呼叫歷程。
  * 透過 Langfuse 儀表板，可精準定位任務執行中的效能瓶頸（Latency）、錯誤率 (Error Rate) 與各節點的輸入/輸出數據 (I/O Payload)。

### 2.8 檔案與日誌生命週期管理 (Lifecycle & Garbage Collection)
* **非寫死原則 (Configurable Retention via .env & UI)**:
  * **所有檔案與暫存資料的保留天數絕不寫死在代碼中**。系統啟動時由 `.env` 提供預設值，並同步於資料庫 `system_settings` 中管理。
  * 提供 Web UI 系統設定介面供管理員隨時調整保留天數，並支援「套用重啟/熱重載」機制使設定立即生效。
* **檔案儲存與回收 (Garbage Collection)**:
  * **上傳檔案與最終報告 (Uploads & Reports)**：任務完成後，使用者上傳之原始壓縮包 (`storage/uploads/`) 與最終產出之報告檔案 (`storage/reports/`) **預設保留 7 天**（天數可於環境變數 `UPLOAD_RETENTION_DAYS` 與 `REPORT_RETENTION_DAYS` 自訂），逾期由 Celery Beat 定期清除。
  * **解壓剖析中繼目錄 (`storage/staging/<task_id>/`)**：任務正式完成或失敗結案後，**立即確實清除解壓檔案**；若任務異常中斷，中繼檔至多保留至指定除錯期限（預設 24 小時）後自動回收，避免大量 XML 佔用磁碟。
  * **圖譜快取目錄 (`storage/graphs/{task_id}.pickle`)**：供差異化執行與斷點接續使用的二進位中繼圖譜檔，隨任務生命週期保留或依獨立 TTL (`GRAPH_CACHE_RETENTION_DAYS`) 清理。
* **Log 檔案管理**:
  * 後端與 Worker 統一採用 `Loguru` 或 Python 內建 `logging` 進行日誌紀錄。
  * 實作 **Log Rotation (日誌輪轉)** 機制：依據檔案大小 (如 50MB) 或時間 (每日) 自動切割，並壓縮歸檔，保留天數透過設定管理（預設 14 天）。

## 3. 核心處理流程 (Schematic Analyzer Workflow)

系統後端將 `schematic-analyzer` 的工作流程解構並整合為以下標準化 Pipeline (由 Celery Worker 依序執行)：

1. **解封與格式預檢 (Archive Inspection & Parsing)**:
   * **輸入限制**: 僅接受 **`.zip` 或 `.7z` 壓縮檔案**。封裝內容必須包含：
     1. Cadence OrCAD Capture XML 檔案 (`*.xml`)。
     2. Netlist 檔案（可與 XML 同層或位於 `allegro/`、`netlist/` 等資料夾，包含 `pstxnet.dat`, `pstxprt.dat`, `pstchip.dat`）。
   * **建模與圖譜快取**: 使用 **`NetworkX`** 套件將線路圖轉換為數學圖譜 (Bipartite Graph，零件與 Net 為節點，Pin 為邊)。建圖完成後立即序列化落地至 `/app/storage/graphs/{task_id}.pickle` 快取，以支援中斷重啟後的秒級反序列化接續。
2. **特徵提取與預先分析 (Feature Extraction & Subsystem Detection)**:
   * 走訪 NetworkX Graph，提取各節點的屬性 (如零件類型、電阻電容值、Pin 腳定義：Power, GND, Input, Output)。
   * 識別並分割出關鍵的子電路 (Sub-circuits，例如電源模組、通訊介面 I2C/SPI 等)。
3. **傳統規則比對 (Heuristic DRC)**:
   * 針對 NetworkX 圖譜執行圖論演算法，進行基礎 DRC (如：懸空腳位檢測、Output 接 Output 衝突、未連接電源/地線等)。
   * **逐條持久化**: 每條規則檢測完畢，立即將檢驗結果 (PASS/FAIL/WARNING) 寫入 `drc_tasks.checkpoint_data`，確保進度即時固化。
4. **LLM 邏輯推理 (LLM-Assisted Analysis)**:
   * 依據規則定義的 `context_extractor` 僅萃取局部子圖 (Subgraph) 節點關係，轉換為結構化 Prompt。
   * 透過 LiteLLM 呼叫模型，進行進階語意或設計邏輯檢查 (例如：「請根據此圖譜關係，判斷 I2C 總線的 Pull-up 電阻配置是否合理？」)。
   * **差異化略過與檢查點更新**: 若為重啟接續任務，自動跳過已完成的 LLM 規則，不重複呼叫；新完成的規則立即更新至檢查點資料庫。
5. **報告彙整與資源清理 (Report Synthesis & Immediate Cleanup)**:
   * 整合先前的檢查點暫存與本次執行的結果，產生標準化報告，詳細格式請參閱 [docs/report_schema.md](file:///home/gaven/DesignShield/docs/report_schema.md)。
   * **報告必備欄位**: 規則類別 (Category)、規則標題 (Title)、描述 (Description)、確認節點 (Target Component/Net)、檢測狀態 (PASS/FAIL/WARNING/SKIP)、工程備註 (Comment, Optional)、程式確認 Log 或 LLM 歷程 Traces。
   * **總結儀表板 (Summary Dashboard)**: 檢測總數、通過率、違規分類統計與執行耗時。
   * **即時垃圾清理**: 報告產出並寫入資料庫後，**立即清除本任務在 `/app/storage/staging/{task_id}/` 下的解壓縮原始 XML 與 Netlist 中繼檔**，釋放磁碟空間。上傳原始壓縮檔與最終報告則進入 7 天生命週期管理。

## 4. Web UI 介面與功能模組 (Dashboard)

### 4.1 儀表板總覽 (Healthy Status & Overview)
* 顯示 API、Worker、DB 狀態。顯示當前排隊中的任務數量與預估等待時間。
* 整合 Langfuse 統計圖表 (Token 消耗、任務平均耗時)。

### 4.2 任務排程與狀態 (Task Queue & Status)
* 顯示當前處理中的單一任務 (Processing) 以及佇列中等待的任務列表 (Pending, 按 FIFO 排序)。
* 提供「取消任務」、「細部逾時設定」介面。
* **中斷任務復原按鈕**: 當系統偵測到因重啟中斷的任務時，顯示「斷點接續分析 (Resume)」按鈕，供工程師手動觸發差異化接續。

### 4.3 線路確認模組 (Schematic Validation & DRC)
1. **上傳線路 (Upload)**:
   * 嚴格限制為 `.zip` 或 `.7z` 壓縮包（含 XML、Netlist 檔案，不需包含 PDF）。
2. **預先分析與規則建議 (Pre-analysis & Rule Recommendation)**:
   * 上傳後由系統快速掃描元件與 Net，分析線路用到哪些核心 IC、匯流排（I2C, SPI, UART, USB 等）與硬體平台。
   * 自動產生**建議規則清單 (Recommended Rule Set)**，在 UI 上以**樹狀圖 (Tree View)** 展開呈現各細項，供工程師自由勾選或增刪檢查項目。
3. **即時確認與日誌終端 (Real-time Status & Log Console)**:
   * **進度指示與狀態徽章 (Progress & Badges)**: 顯示全流程進度條 (0-100%)、當前執行步驟 Badge（如 `[步驟 3/5: LLM 語意邏輯審查]`）以及目前正執行的規則名稱。
   * **差異化執行指示標籤 (Differential Badge)**: 若為斷點接續任務，顯示醒目紫色徽章 `[差異化接續中]`，即時呈現「已略過 completed_rules: 15 項，剩餘 remaining_rules: 27 項」。
   * **嵌入式即時終端 (Real-time Log Console)**:
     * 整合 PrimeVue Terminal / 日誌視窗元件，透過 WebSocket 接收秒級結構化日誌串流。
     * **日誌分級著色**: `INFO` (藍)、`SUCCESS` (綠)、`WARN` (黃)、`ERROR` (紅)、`RESUME` (紫)。
     * **互動控制**: 支援自動滾動開關 (Auto-scroll toggle)、關鍵字搜尋、步驟過濾 (Filter by Step) 以及一鍵複製與匯出日誌。
     * **斷線無縫重連**: 頁面重新整理或網路斷線重連後，自動請求歷史日誌進行全量回放 (Replay)。
4. **結果檢視 (Report)**: 呈現 Summary Dashboard 與詳細違規列表，支援過濾、搜尋與報告匯出。

### 4.4 規則庫維護 (Rule Library Management)
* 管理傳統參數規則與 LLM Prompt 規則 (CRUD 介面)，包含完整的中文規則說明。

### 4.5 Datasheet 管理模組 (Phase 2 Placeholder)
* **介面佔位符**: 提供 PDF Datasheet 上傳介面。
* **未來功能預留**: 視覺上展示文件列表，但後端處理邏輯（如解析、提取 DRC Rule）將於下一階段實作。

### 4.6 系統維護與設定模組 (System Settings & Maintenance)
* **檔案保留週期設定 (File Retention Management)**:
  * 視覺化調整上傳原始檔保留天數 (`upload_retention_days`，預設 7 天)。
  * 調整 DRC 分析報告保留天數 (`report_retention_days`，預設 7 天)。
  * 調整圖譜快取保留天數 (`graph_cache_retention_days`，預設 7 天)。
  * 調整中繼解壓暫存清理門檻 (`staging_cleanup_hours`，預設 24 小時)。
* **運算與模型逾時設定 (Timeout Management)**:
  * 調整單一步驟運算上限 (預設 60 秒) 與單一 LLM 請求上限 (預設 45 秒)。
* **套用與重啟生效 (Apply & Reload)**:
  * 提供「儲存並套用」按鈕，將新設定寫入資料庫 `system_settings`，並發布重載訊號至 Celery Beat 排程器，使清理排程與系統參數立即生效，無需重啟容器。

## 5. 未來擴充與階段性規劃 (Future Roadmap)

1. **使用者認證與授權 (Authentication & Authorization)**:
   * **現階段**: 專注於單一環境的核心 DRC 分析流程，暫不實作多使用者登入 (JWT/OAuth) 與多租戶資料隔離 (Tenant Isolation)。
   * **未來規劃**: 由於系統已採用 Stateless API 與 PostgreSQL，未來對外開放或團隊協作時，可無縫擴充身份驗證中間件 (Middleware) 並於資料庫中加入 User/Tenant 關聯。
2. **Datasheet 模組與 RAG 整合 (Datasheet Retrieval-Augmented Generation)**:
   * **現階段**: UI 僅作 Placeholder 展示。
   * **未來規劃**: 實作 PDF 文件解析與向量資料庫 (Vector DB)。系統將能自動從 Datasheet 提取極限參數 (如耐壓、溫度範圍) 轉化為 DRC 規則。在執行 DRC 檢查時 (Step 4)，LLM 將能透過 RAG 動態查詢這些規格數據，進行更深度的降額 (Derating) 與電氣特性匹配檢查。