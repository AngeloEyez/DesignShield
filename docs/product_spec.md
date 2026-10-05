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
    * **即時心跳與進度推播 (Heartbeat & Progress)**：Worker 執行過程透過 Redis Pub/Sub 推播細部進度（如當前檢查規則名稱、百分比），避免前端長時間無回應。

### 2.6 LLM 整合適配層 (LLM Integration Layer)
* **核心套件**: **LiteLLM** 作為統一的 API 網關 (Proxy) 與適配層。
* **優勢**: 絕不在業務程式碼中寫死特定廠商 SDK，支援多提供者無縫切換 (本地端模型、OpenAI、Gemini、Claude)，並提供統一的 Retry 與 Rate Limiting。

### 2.7 系統觀測性與除錯 (Comprehensive Observability)
* **全鏈路追蹤 (Langfuse)**:
  * 不僅用於監控 LLM 的 Token 與參數，**系統將全面採用 Langfuse 來追蹤整體執行流程**。
  * **追蹤範圍包含**: 一般 Python 函式執行耗時、資料庫查詢 (DB Queries)、向量檢索、外部 API 請求，以及微服務 (API Server to Celery Worker) 之間的呼叫歷程。
  * 透過 Langfuse 儀表板，可精準定位任務執行中的效能瓶頸（Latency）、錯誤率 (Error Rate) 與各節點的輸入/輸出數據 (I/O Payload)。

### 2.8 檔案與日誌生命週期管理 (Lifecycle & Garbage Collection)
* **檔案儲存與回收 (Garbage Collection)**:
  * 包含使用者上傳的 netlist 檔案、系統產生的中繼站暫存檔，以及最終輸出的 PDF/JSON 報告檔案。
  * 實作定期清理機制 (例如透過 Celery Beat 設定 Cron Job)，根據 TTL (Time-To-Live) 設定自動刪除過期檔案 (例如保留 7 天)，避免磁碟空間耗盡。
* **Log 檔案管理**:
  * 後端與 Worker 統一採用 `Loguru` 或 Python 內建 `logging` 進行日誌紀錄。
  * 實作 **Log Rotation (日誌輪轉)** 機制：依據檔案大小 (如 50MB) 或時間 (每日) 自動切割，並壓縮歸檔，保留固定天數後自動刪除。

## 3. 核心處理流程 (Schematic Analyzer Workflow)

系統後端將 `schematic-analyzer` 的工作流程解構並整合為以下標準化 Pipeline (由 Celery Worker 依序執行)：

1. **解封與格式預檢 (Archive Inspection & Parsing)**:
   * **輸入限制**: 僅接受 **`.zip` 或 `.7z` 壓縮檔案**。封裝內容必須包含：
     1. Cadence OrCAD Capture XML 檔案 (`*.xml`)。
     2. Netlist 檔案（可與 XML 同層或位於 `allegro/`、`netlist/` 等資料夾，包含 `pstxnet.dat`, `pstxprt.dat`, `pstchip.dat`）。
     3. 線路圖 PDF 檔案 (`*.pdf`，供工程師檢視與前端視覺化核對）。
   * **建模**: 使用 **`NetworkX`** 套件將線路圖轉換為數學圖譜 (Bipartite Graph，零件與 Net 為節點，Pin 為邊)。
2. **特徵提取與預先分析 (Feature Extraction & Subsystem Detection)**:
   * 走訪 NetworkX Graph，提取各節點的屬性 (如零件類型、電阻電容值、Pin 腳定義：Power, GND, Input, Output)。
   * 識別並分割出關鍵的子電路 (Sub-circuits，例如電源模組、通訊介面 I2C/SPI 等)。
3. **傳統規則比對 (Heuristic DRC)**:
   * 針對 NetworkX 圖譜執行圖論演算法，進行基礎 DRC (如：懸空腳位檢測、Output 接 Output 衝突、未連接電源/地線等)。
4. **LLM 邏輯推理 (LLM-Assisted Analysis)**:
   * 將提取出的子電路特徵、NetworkX 節點關係轉換為結構化 Prompt。
   * 透過 LiteLLM 呼叫模型，進行進階語意或設計邏輯檢查 (例如：「請根據此圖譜關係，判斷 I2C 總線的 Pull-up 電阻配置是否合理？」)。
5. **報告彙整 (Report Generation)**:
   * 整合傳統 DRC 與 LLM 推理的結果，產生標準化報告，詳細格式請參閱 [docs/report_schema.md](file:///z:/Programming/DesignShield/docs/report_schema.md)。
   * **報告必備欄位**: 規則類別 (Category)、規則標題 (Title)、描述 (Description)、確認節點 (Target Component/Net)、檢測狀態 (PASS/FAIL/WARNING/SKIP)、工程備註 (Comment, Optional)、程式確認 Log 或 LLM 歷程 Traces。
   * **總結儀表板 (Summary Dashboard)**: 檢測總數、通過率、違規分類統計與執行耗時。

## 4. Web UI 介面與功能模組 (Dashboard)

### 4.1 儀表板總覽 (Healthy Status & Overview)
* 顯示 API、Worker、DB 狀態。顯示當前排隊中的任務數量與預估等待時間。
* 整合 Langfuse 統計圖表 (Token 消耗、任務平均耗時)。

### 4.2 任務排程與狀態 (Task Queue & Status)
* 顯示當前處理中的單一任務 (Processing) 以及佇列中等待的任務列表 (Pending, 按 FIFO 排序)。
* 提供「取消任務」與「細部逾時設定」介面。

### 4.3 線路確認模組 (Schematic Validation & DRC)
1. **上傳線路 (Upload)**:
   * 嚴格限制為 `.zip` 或 `.7z` 壓縮包（含 XML、Netlist、PDF）。
2. **預先分析與規則建議 (Pre-analysis & Rule Recommendation)**:
   * 上傳後由系統快速掃描元件與 Net，分析線路用到哪些核心 IC、匯流排（I2C, SPI, UART, USB 等）與硬體平台。
   * 自動產生**建議規則清單 (Recommended Rule Set)**，在 UI 上以**樹狀圖 (Tree View)** 展開呈現各細項，供工程師自由勾選或增刪檢查項目。
3. **即時確認 (Real-time Status)**: 透過 WebSocket/SSE 更新 Pipeline 各步驟進度與當前規則名稱。
4. **結果檢視 (Report)**: 呈現 Summary Dashboard 與詳細違規列表，支援過濾、搜尋與報告匯出。

### 4.4 規則庫維護 (Rule Library Management)
* 管理傳統參數規則與 LLM Prompt 規則 (CRUD 介面)，包含完整的中文規則說明。

### 4.5 Datasheet 管理模組 (Phase 2 Placeholder)
* **介面佔位符**: 提供 PDF Datasheet 上傳介面。
* **未來功能預留**: 視覺上展示文件列表，但後端處理邏輯（如解析、提取 DRC Rule）將於下一階段實作。

## 5. 未來擴充與階段性規劃 (Future Roadmap)

1. **使用者認證與授權 (Authentication & Authorization)**:
   * **現階段**: 專注於單一環境的核心 DRC 分析流程，暫不實作多使用者登入 (JWT/OAuth) 與多租戶資料隔離 (Tenant Isolation)。
   * **未來規劃**: 由於系統已採用 Stateless API 與 PostgreSQL，未來對外開放或團隊協作時，可無縫擴充身份驗證中間件 (Middleware) 並於資料庫中加入 User/Tenant 關聯。
2. **Datasheet 模組與 RAG 整合 (Datasheet Retrieval-Augmented Generation)**:
   * **現階段**: UI 僅作 Placeholder 展示。
   * **未來規劃**: 實作 PDF 文件解析與向量資料庫 (Vector DB)。系統將能自動從 Datasheet 提取極限參數 (如耐壓、溫度範圍) 轉化為 DRC 規則。在執行 DRC 檢查時 (Step 4)，LLM 將能透過 RAG 動態查詢這些規格數據，進行更深度的降額 (Derating) 與電氣特性匹配檢查。