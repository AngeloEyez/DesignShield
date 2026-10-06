# 線路設計規則檢查系統 (Schematic DRC System) - DesignShield

本專案是一套專為硬體工程師設計的自動化「線路設計規則檢查系統」。系統解析 Cadence OrCAD XML，利用 NetworkX 構建圖譜，並結合傳統演算法與大語言模型 (本地 LLM)，自動檢測電路圖缺陷。

## 🚀 核心架構演進
本專案**已全面移除 Celery 與 Redis**，改採 **Postgres DBOS (Durable Execution)** 作為核心任務執行引擎。
* **原生斷點接續**：伺服器重啟可從中斷步驟無縫接續。
* **PrimeVue 視覺化進度**：透過 `step_status` 資料表與 Vue 3 Timeline 元件呈現。
* **雙軌執行**：區分「輕量預先分析」與「重型 DBOS DRC 分析」，避免阻塞。
* **本地 LLM 優先**：支援對接本地 `192.168.1.5:8000/v1` 的 LLM 服務。
* **彈性觀測性**：Langfuse 已整合至主要 Compose 檔中預設一併啟動（為 Optional 選用服務，具備完整容錯與優雅降級）。

## 📚 系統文件導覽 (Documentation)
詳細技術規格與維護手冊請參閱 `docs/` 目錄：
1. **[產品規格書 (product_spec.md)](docs/product_spec.md)**：架構選型、DBOS 排程、本地 LLM 策略。
2. **[資料庫綱要 (database_schema.md)](docs/database_schema.md)**：PostgreSQL 表結構與 `step_status`。
3. **[分析管線 (pipeline_workflow.md)](docs/pipeline_workflow.md)**：雙軌執行路徑與 DBOS Workflow。
4. **[技術維護手冊 (maintenance_guide.md)](docs/maintenance_guide.md)**：微服務、備份與移轉。
5. **[專案結構 (project_structure.md)](docs/project_structure.md)**：目錄配置與隔離策略。
6. **[開發實作計畫 (implementation_plan.md)](docs/implementation_plan.md)**：Phase 拆分與活文件開發筆記。

## 💻 啟動指南 (Quick Start)
```bash
# 1. 建立設定檔 (複製環境變數範例檔)
# PowerShell (Windows):
Copy-Item .env.example .env

# Bash (Linux/macOS):
cp .env.example .env

# 2. 一鍵啟動所有服務 (Postgres, Backend, Frontend, Langfuse)
cd deploy
docker compose up -d
```

### 服務端點與可選服務說明
* **前端 Web 介面 (Frontend)**: `http://${SERVER_HOST}:8080` (本機: `http://localhost:8080`)
* **後端 API 規格文件 (FastAPI)**: `http://${SERVER_HOST}:8000/docs` (本機: `http://localhost:8000/docs`)
* **核心資料庫 (PostgreSQL)**: `${SERVER_HOST}:5433` (本機: `localhost:5433`)
* **[Optional] 觀測儀表板 (Langfuse)**: `http://${SERVER_HOST}:3000` (本機: `http://localhost:3000`)
  > **註**：Langfuse 為選用 (Optional) 觀測服務，預設隨 `docker compose up -d` 啟動。若部署環境硬體資源有限或不需 LLM 追蹤，可直接在 `deploy/docker-compose.yml` 中將 `langfuse` 服務區塊註解或移除。後端系統內建自動容錯機制，未啟用 Langfuse 時完全不影響核心電路 DRC 檢測流程。

## ⚙️ 系統初始化與首次部署設定 (First-Time Setup Guide)

初次部署（`docker compose up -d`）完成後，請依循以下步驟進行系統初始化與各服務串接：

### 1. 環境變數設定說明 (`.env`)
專案提供完整之範例設定檔 [`.env.example`](.env.example)。建立 `.env` 後，可針對環境進行調整：

| 環境變數名稱 | 預設值 | 說明 |
| :--- | :--- | :--- |
| **`SERVER_HOST`** | `192.168.1.16` | **核心伺服器主機 IP 或網域**。全域集中設定，供 Langfuse 認證跳轉 (`NEXTAUTH_URL`) 及對外服務識別使用。換機器或改網段僅需修改此變數。 |
| **`FRONTEND_PORT`** | `8080` | 前端 Web 介面對外映射連接埠。 |
| **`POSTGRES_USER`** | `designshield` | PostgreSQL 核心資料庫使用者名稱。 |
| **`POSTGRES_PASSWORD`**| `shield_secret_2026` | PostgreSQL 核心資料庫連線密碼。 |
| **`POSTGRES_DB`** | `designshield_db` | 資料庫名稱（儲存 DRC 規則庫、任務進度與 DBOS 執行狀態）。 |
| **`POSTGRES_HOST_PORT`**| `5433` | PostgreSQL 對外暴露之主機埠號（預設 5433 避免與主機現有 5432 衝突）。 |
| **`DATABASE_URL`** | `postgresql://...` | 後端 SQLAlchemy 資料庫連線字串。 |
| **`DBOS_SYSTEM_DATABASE_URL`** | `postgresql://...` | DBOS Durable Execution 引擎系統狀態資料庫連線字串。 |
| **`LOCAL_LLM_URL`** | `http://192.168.1.5:8000/v1` | 本地 LLM 推理伺服器 API 端點（相容 OpenAI 協定）。 |
| **`LOCAL_LLM_MODEL`**| `openai/qwen` | 本地 LLM 呼叫的模型識別名稱。 |
| **`LOCAL_LLM_API_KEY`**| `EMPTY` | 本地 LLM 認證金鑰（本地 vLLM/Ollama 通常填 `EMPTY` 即可）。 |
| **`UPLOAD_RETENTION_DAYS`** | `7` | 上傳暫存檔案保存天數，逾期將被系統定期垃圾回收釋放空間。 |
| **`LANGFUSE_PUBLIC_KEY`** | *(留空)* | Langfuse 專案 Public Key（取得方式見下方串接步驟）。 |
| **`LANGFUSE_SECRET_KEY`** | *(留空)* | Langfuse 專案 Secret Key（取得方式見下方串接步驟）。 |
| **`LANGFUSE_HOST`** | `http://localhost:3000` | Langfuse 服務位址（Compose 容器內部預設自動路由至 `http://langfuse:3000`）。 |
| **`LANGFUSE_NEXTAUTH_URL`** | `http://${SERVER_HOST}:3000` | Langfuse 儀表板 NextAuth 跳轉網址，預設自動套用 `${SERVER_HOST}`。 |

---

### 2. Langfuse 帳號註冊與金鑰取得（與 DesignShield 串接）
Langfuse 官方映像檔預設**無固定預設帳號與密碼**，初次啟動時採用「首次自註冊」模式：

1. **開啟 Langfuse 儀表板**：
   - 瀏覽器開啟 `http://${SERVER_HOST}:3000`（或本機 `http://localhost:3000`）。
2. **註冊初始管理員帳號**：
   - 在登入畫面點選 **"Sign Up"** 進行註冊。
   - 輸入任意管理員 Email 與自訂密碼。**系統中第一位註冊的使用者自動成為最高權限管理員**。
3. **建立專案 (Project)**：
   - 登入後依照精靈建立 Organization（例如：`DesignShield-Org`）。
   - 新增 Project（例如：`DesignShield`）。
4. **生成 API Key**：
   - 點擊左下角齒輪圖示 **Settings** -> 進入 **API Keys** 分頁。
   - 點擊 **"Create new API keys"**。
   - 複製產生的金鑰資訊：
     - **Public Key**: `pk-lf-...`
     - **Secret Key**: `sk-lf-...`
5. **回填至 DesignShield 系統**：
   - **方式一（推薦：設定檔持久化）**：
     將取得的金鑰填入根目錄 `.env` 檔案中：
     ```ini
     LANGFUSE_PUBLIC_KEY=pk-lf-xxxxxxxxxxxxxxxx
     LANGFUSE_SECRET_KEY=sk-lf-xxxxxxxxxxxxxxxx
     ```
     接著重啟後端服務使其生效：
     ```bash
     cd deploy
     docker compose up -d --force-recreate backend
     ```
   - **方式二（前端設定視窗即時調整）**：
     開啟前端 Web 介面 (`http://${SERVER_HOST}:8080`)，點擊右上角「**系統運維與參數設定**」齒輪圖示，即可檢視與即時儲存系統執行參數與本地 LLM 連線設定。

---

### 3. 首次部署驗證檢查清單 (Health Checklist)
完成上述步驟後，請依序驗證各核心模組運作正常：

- [ ] **前端頁面載入**：瀏覽器造訪 `http://${SERVER_HOST}:8080`，確認可正常顯示線路圖上傳卡片與規則樹狀選單。
- [ ] **後端 API 與自動資料庫初始化**：造訪 `http://${SERVER_HOST}:8000/health`，應回傳 `{"status":"healthy", ...}`；造訪 `http://${SERVER_HOST}:8000/docs` 可查閱完整 OpenAPI 文件。
- [ ] **本地 LLM 網路可達性**：確認伺服器主機能夠連通 `LOCAL_LLM_URL`（例如在主機測試 `curl http://192.168.1.5:8000/v1/models`）。
- [ ] **資料庫存取（選用）**：若需透過 GUI 工具 (如 DBeaver / DataGrip) 管理資料庫，連線至主機 `${SERVER_HOST}`，連接埠 `5433`，帳密依 `.env` 設定即可連入。

## 🧪 測試執行 (Testing)
```bash
# 後端測試與覆蓋率 (包含單元測試與 E2E 整合測試)
cd backend
.venv/bin/pytest tests -v --cov=app

# 前端 Vitest 單元測試與型別檢查
cd frontend
npm test
npm run build
```
