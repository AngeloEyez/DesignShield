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

1. **解析與圖譜建立 (Parsing & Graph Construction)**:
   * **輸入**: 讀取使用者上傳的 `netlist/XML (Cadence Capture)` 檔案。
   * **建模**: 使用 **`NetworkX`** 套件將線路圖轉換為數學圖譜 (Graph)。將電子零件 (Components) 或接腳 (Pins) 視為節點 (Nodes)，並將實體連線 (Nets) 視為邊 (Edges)。
2. **特徵提取 (Feature Extraction)**:
   * 走訪 NetworkX Graph，提取各節點的屬性 (如零件類型、電阻電容值、Pin 腳定義：Power, GND, Input, Output)。
   * 識別並分割出關鍵的子電路 (Sub-circuits，例如電源模組、通訊介面 I2C/SPI 等)。
3. **傳統規則比對 (Heuristic DRC)**:
   * 針對 NetworkX 圖譜執行圖論演算法，進行基礎 DRC (如：懸空腳位檢測、Output 接 Output 衝突、未連接電源/地線等)。
4. **LLM 邏輯推理 (LLM-Assisted Analysis)**:
   * 將提取出的子電路特徵、NetworkX 節點關係轉換為結構化 Prompt。
   * 透過 LiteLLM 呼叫模型，進行進階語意或設計邏輯檢查 (例如：「請根據此圖譜關係，判斷 I2C 總線的 Pull-up 電阻配置是否合理？」)。
5. **報告彙整 (Report Generation)**:
   * 整合傳統 DRC 與 LLM 推理的結果，標記違反規則的具體節點 (Node/Component Reference) 與建議，產生結構化報告。

## 4. Web UI 介面與功能模組 (Dashboard)

### 4.1 儀表板總覽 (Healthy Status & Overview)
* 顯示 API、Worker、DB 狀態。顯示當前排隊中的任務數量與預估等待時間。
* 整合 Langfuse 統計圖表 (Token 消耗、任務平均耗時)。

### 4.2 任務排程與狀態 (Task Queue & Status)
* 顯示當前處理中的單一任務 (Processing) 以及佇列中等待的任務列表 (Pending, 按 FIFO 排序)。

### 4.3 線路確認模組 (Schematic Validation & DRC)
1. **上傳線路 (Upload)**:
   * **嚴格限制輸入格式**: 僅支援 **`netlist/XML (Cadence Capture)`** 格式上傳。
2. **配置 (Configuration)**: 選擇要套用的 Rule 與 LLM 模型。
3. **即時確認 (Real-time Status)**: 透過 WebSocket/Polling 更新 Pipeline 的五大步驟進度。
4. **結果檢視 (Report)**: 檢視 DRC 違規項目，並提供報告下載。

### 4.4 規則庫維護 (Rule Library Management)
* 管理傳統參數規則與 LLM Prompt 規則 (CRUD 介面)。

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