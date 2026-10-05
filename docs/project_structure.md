# 專案結構與文件策略 (Project Structure & Documentation Strategy)

## 1. 給 AI Agent 的文件架構策略 (AI-Friendly Documentation)

為了讓 AI Agent (如 Cursor, GitHub Copilot, 或對話式 LLM) 能最高效地協助開發，我們將文件分為「高階策略」與「實作細節」兩層，並放置於 `docs/` 目錄下：

### 1.1 高階指導文件 (High-Level Context)

* **`project_structure.md` (本文件)**: 專案目錄結構總覽與文件策略。AI 在建立新檔案或尋找現有邏輯時的首要參考點。
* **`product_spec.md` (已完成)**: 專案總覽、架構選型、核心需求、功能清單。AI 需要理解「整體目標」時參考。

### 1.2 實作細節文件 (Implementation Details - 待撰寫)

為了避免單一文件過於龐大，實作細節必須獨立成以下檔案：

* **`database_schema.md`**:

  * **內容**: PostgreSQL 的資料表結構、關聯圖 (ERD 概念)、欄位型態、索引設計。

  * **AI 應用時機**: 開發 SQLAlchemy Models、Alembic 遷移檔、CRUD 操作時。

* **`api_contract.md`**:

  * **內容**: FastAPI 提供的 Endpoints、Request/Response JSON 格式 (Pydantic schemas 規劃)、WebSocket 溝通格式。

  * **AI 應用時機**: 開發後端 Router 或前端 Axios API 封裝、狀態同步時。

* **`pipeline_workflow.md`**:

  * **內容**: 詳述那 5 個步驟 (Parsing -> Feature -> Heuristic DRC -> LLM -> Report) 的具體資料流。包含 NetworkX 的圖譜結構定義 (Node/Edge 的 attributes)。

  * **AI 應用時機**: 開發 Celery Worker 內部邏輯、撰寫 LLM Prompt 組合器時。

## 2. 專案資料夾結構規劃 (Monorepo Directory Structure)

採用前後端分離的單一儲存庫 (Monorepo) 架構，後端與 Celery Worker 共用核心領域邏輯與資料庫模型，以降低維護成本。

```
schematic-drc-system/
├── docs/                       # 專案文件目錄
│   ├── project_structure.md    # 🌟 本文件：專案結構與文件導覽
│   ├── product_spec.md         # 產品規格書
│   ├── database_schema.md      # (待撰寫) 資料庫架構
│   ├── api_contract.md         # (待撰寫) API 規格
│   └── pipeline_workflow.md    # (待撰寫) DRC 分析流程細節
│
├── frontend/                   # 前端專案 (Vue 3 + Vite)
│   ├── package.json
│   ├── src/
│   │   ├── api/                # 後端 API 呼叫封裝 (Axios)
│   │   ├── components/         # 共用 UI 元件 (PrimeVue 封裝)
│   │   └── views/              # 主要頁面
│   └── ...
│
├── backend/                    # 後端專案 (FastAPI + Celery 共用 codebase)
│   ├── pyproject.toml          # 使用 Poetry 管理依賴，確保套件版本隔離
│   ├── alembic.ini             # 資料庫遷移配置
│   ├── alembic/                # 資料庫遷移腳本目錄
│   ├── app/                    # 核心程式碼
│   │   ├── main.py             # FastAPI 進入點
│   │   ├── core/               # 全域配置 (Config, LiteLLM 初始化, Langfuse 設定)
│   │   ├── api/                # REST API Routers (Endpoints)
│   │   ├── db/                 # 資料庫連線配置 (Database Session)
│   │   ├── models/             # SQLAlchemy ORM 資料表模型
│   │   ├── schemas/            # Pydantic 驗證模型 (Request/Response)
│   │   ├── crud/               # 基礎資料庫操作邏輯
│   │   ├── worker/             # Celery 相關配置與任務註冊
│   │   │   ├── celery_app.py   # Celery 實例
│   │   │   └── tasks.py        # 異步任務定義
│   │   └── engine/             # 核心分析引擎 (業務邏輯與第三方套件封裝)
│   │       ├── parser/         # Netlist 解析器 (Cadence XML to Python Dict)
│   │       ├── graph/          # 圖譜處理邏輯 (封裝 NetworkX 套件的呼叫)
│   │       ├── heuristic/      # 傳統 DRC 規則演算法
│   │       ├── llm/            # LiteLLM Prompt 組合與呼叫
│   │       └── datasheet/      # (Phase 2) 封裝 Marker 等 PDF 解析/RAG 套件
│
├── deploy/                     # 部署與基礎設施設定
│   ├── docker-compose.yml      # 一鍵啟動 DB, Redis, API, Worker, UI
│   ├── Dockerfile.frontend
│   ├── Dockerfile.backend      # 主 API 與一般任務的環境
│   └── Dockerfile.heavy_worker # (Phase 2) 專門給 Marker 等重型套件使用的獨立環境
│
├── .gitignore
└── README.md                   # 開發者啟動指南
```

### 2.1 結構設計亮點說明

1. **`backend/app/engine/` 的獨立性**: 將核心的分析邏輯 (圖譜解析、LLM、DRC) 從 API 路由中徹底抽離。這樣不但方便單元測試 (Unit Testing)，未來 Celery Worker 呼叫時也能直接引入這些純函數 (Pure functions)，不會與 HTTP Request 綁定。

2. **Backend 內部共用**: Celery Worker 與 FastAPI 共用 `backend/` 目錄。這在 Python 開發中是標準作法，因為 Worker 任務執行完畢後通常需要呼叫 `models` 與 `crud` 將寫回同一個資料庫。

3. **基礎設施解耦**: 所有跟環境相關的設定 (Postgres, Redis, Langfuse API keys) 皆透過環境變數 (`.env`) 傳遞至 `core/`，確保系統隨時可容器化部署。

## 3. 套件依賴與基礎設施隔離策略 (Dependencies & Infrastructure Isolation)

針對套件更新與基礎設施維護，本專案採取以下策略以確保穩定性：

### 3.1 基礎設施容器化 (Docker-First Approach)

系統依賴的外部服務（如 PostgreSQL 資料庫、Redis 訊息佇列）**絕對不會直接安裝在開發機或伺服器主機上**，而是統一透過 `deploy/docker-compose.yml` 管理。

* **優勢**: 若要更新 PostgreSQL 版本（例如從 v14 升級至 v16），只需修改 `docker-compose.yml` 中的 Image tag 並重新啟動，完全不會影響到後端 Python 程式碼，確保隔離性與無痛升級。

### 3.2 第三方套件封裝與管理 (Package Management)

像 `NetworkX` (圖譜運算) 或 `Marker` (PDF 轉 Markdown) 這種第三方套件，會遵循以下規範：

1. **依賴鎖定**: 後端建議使用 **Poetry** (取代傳統的 `requirements.txt`) 來管理套件。Poetry 會產生 `poetry.lock` 檔，嚴格鎖定所有套件與其子依賴的版本。這樣可以確保「只要沒有主動升級，程式碼永遠不會因為第三方套件偷偷更新而損壞」。

2. **資料夾歸屬 (Adapter Pattern)**:

   * 第三方套件本身是安裝在 Python 虛擬環境或 Docker 映像檔中，**不需要**在我們的專案目錄中為它們建立資料夾。

   * 但是，我們**操作這些套件的程式碼**必須被封裝在特定的目錄中。例如，所有呼叫 `NetworkX` 的程式碼都會被限制在 `backend/app/engine/graph/` 內；所有呼叫 `Marker` 的程式碼都會集中在 `backend/app/engine/datasheet/` 內。

   * **優勢**: 如果未來我們想把 `NetworkX` 換成效能更好的 `igraph`，或是把 `Marker` 換成其他 PDF 解析工具，我們只需要修改該特定資料夾內的邏輯，其餘系統 (API, Worker, 其他 Engine) 完全不需要改動。

### 3.3 重型套件的未來隔離策略 (Heavy Dependency Isolation)

一般來說，FastAPI 和 Celery Worker 可以共用同一個 `Dockerfile.backend` 環境。
但如果像是 `Marker` 這類套件引入了龐大的機器學習依賴 (如 PyTorch、CUDA 驅動) 或需要極大記憶體，我們會採取以下進階隔離：

* **獨立 Worker 容器**: 在 `deploy/` 中建立一個專屬的 `Dockerfile.heavy_worker`，只安裝處理 PDF 需要的龐大套件，並讓它訂閱專門的 Redis 佇列 (例如 `pdf_tasks` queue)。

* **效益**: 這樣主後端 API 依然輕量且能快速部署更新，只有處理 Datasheet 時才會動用到重型容器，徹底實踐「不同套件互不干擾」的微服務理念。