# 線路設計規則檢查系統 (Schematic DRC System) - DesignShield

本專案是一套專為硬體工程師設計的自動化「線路設計規則檢查系統」。系統解析 Cadence OrCAD XML，利用 NetworkX 構建圖譜，並結合傳統演算法與大語言模型 (本地 LLM)，自動檢測電路圖缺陷。

## 🚀 核心架構演進
本專案**已全面移除 Celery 與 Redis**，改採 **Postgres DBOS (Durable Execution)** 作為核心任務執行引擎，並全面導入**單軌化宣告式規則體系 (Single-Track Engine)**：
* **單軌化規則引擎 (100% IaC & snake_case)**：全系統統一小寫蛇形命名規範 (`snake_case`)，徹底廢除雙向相容映射表；所有 DRC 規則集中於 `patterns/rules/` 下之 YAML 與同目錄伴生腳本，主程式與工作流徹底解耦，零業務規則硬編碼。
* **伴生腳本體系升級 (同目錄、同檔名約定)**：Level 1~3 全面支援伴生 Python 腳本（Level 1 特徵解碼 `classify`、Level 2 拓撲演算法 `match`、Level 3 DRC 驗證 `execute`），並透過 `designshield.sdk` 安全沙盒隔離執行（AST 靜態審查 + 受限 Builtins + 5 秒逾時保護）。
* **混合評估三模式 (Hybrid DRC Modes)**：
  1. 宣告式拓撲斷言 (`topology_check`)：毫秒級極速執行。
  2. PartDB 伴生腳本 (`python_script`)：同目錄動態查表與電氣規範計算。
  3. LLM 語意邏輯推理 (`llm_agent`)：DBOS 非同步佇列排程，調用本地大模型進行介面模式與時序深度推理，具備專家規則優雅降級。
* **兩階段語意昇華與宣告式差分推導**：OrCAD XML 客觀屬性抽取，極性與夥伴推導由 YAML `pair_derivation` 完全驅動。
* **完全動態預先分析**：規則推薦 100% 由圖譜特徵與 YAML `trigger_conditions` 動態匹配，真實無硬編碼假保底。
* **原生斷點接續**：伺服器重啟可從中斷步驟無縫接續。
* **PrimeVue 視覺化進度**：透過 `step_status` 資料表與 Vue 3 Timeline 元件呈現。
* **彈性觀測性**：Langfuse 已整合至主要 Compose 檔中預設一併啟動（為 Optional 選用服務，具備完整容錯與優雅降級）。

## 📚 系統文件導覽 (Documentation)
詳細技術規格與維護手冊請參閱相關文件：
1. **[規則庫架構與治理開發手冊 (patterns/README.md)](patterns/README.md)**：三層規則體系、單軌小寫蛇形命名規範、同目錄伴生腳本開發指引與自動化校驗 SOP。
2. **[DRC 規則與 LLM 協作架構指南 (rule_engine_architecture.md)](docs/rule_engine_architecture.md)**：三層規則架構、Level 3 混合評估、宣告式推導與動態預先分析。
3. **[SDK 伴生腳本開發手冊 (designshield/sdk/README.md)](designshield/sdk/README.md)**：特規腳本開發規範、GraphAPI、PartDB 查表與沙盒安全性指南。
4. **[SDK 技術維護手冊 (designshield/sdk/MAINTENANCE.md)](designshield/sdk/MAINTENANCE.md)**：SDK 架構邊界、擴充 SOP 與維護守則。
5. **[API 規格與契約 (api_contract.md)](docs/api_contract.md)**：前後端溝通介面與資料模型。
6. **[產品規格書 (product_spec.md)](docs/product_spec.md)**：架構選型、DBOS 排程、本地 LLM 策略。
7. **[資料庫綱要 (database_schema.md)](docs/database_schema.md)**：PostgreSQL 表結構與 `step_status`。
8. **[分析管線 (pipeline_workflow.md)](docs/pipeline_workflow.md)**：雙軌執行路徑與 DBOS Workflow。
9. **[技術維護手冊 (maintenance_guide.md)](docs/maintenance_guide.md)**：微服務、備份與移轉。

## 💻 系統啟動指南 (Quick Start)

### 1. 建立環境設定檔 (`.env`)
```bash
# PowerShell (Windows):
Copy-Item .env.example .env

# Bash (Linux/macOS):
cp .env.example .env
```

---

### 2. 選擇運行模式 (開發模式 vs 生產模式)

系統支援兩種運行架構，請依據需求選擇：

| 模式 | 啟動指令 | 適用情境 | 修改程式碼生效方式 |
| :--- | :--- | :--- | :--- |
| **⚡ 極速開發模式<br>(Development Mode)** | `docker compose -f deploy/docker-compose.dev.yml up -d` | **日常功能開發、調試與介面修改** | **存檔即生效 (0.1 ~ 1 秒)**<br>• 後端掛載目錄自動熱重載 (`--reload`)<br>• 前端 Vite HMR 熱更新，免 build |
| **🏭 生產發布模式<br>(Production Mode)** | `docker compose -f deploy/docker-compose.yml up -d` | **正式部署、全面整合測試、效能測試** | 需執行 `up -d --build` 重新打包容器<br>• 前端 Nginx 高效靜態託管<br>• 獨立隔離環境 |

#### ⚡ 模式 A：極速開發模式 (推薦日常開發使用)
在此模式下，後端代碼目錄直接掛載進容器並啟用 Uvicorn 熱重載；前端改由 Vite 開發伺服器運行，支援毫秒級熱模組替換 (HMR)：
```bash
# 啟動開發環境 (首次會自動建立開發容器)
docker compose -f deploy/docker-compose.dev.yml up -d

# 日常開發：在 IDE 修改代碼並存檔 (Ctrl+S) 即自動生效，無需重新 build 或重啟！
# 停止開發環境：
docker compose -f deploy/docker-compose.dev.yml down
```

#### 🏭 模式 B：生產發布模式 (正式上線使用)
在此模式下，前端會進行完整的嚴格型別檢查 (`vue-tsc`) 與 Rollup 壓縮打包，並由 Nginx 進行靜態加速：
```bash
# 啟動生產環境
docker compose -f deploy/docker-compose.yml up -d

# 當有程式碼修改，需重新編譯建置映像檔時：
docker compose -f deploy/docker-compose.yml up -d --build backend frontend

# 停止生產環境：
docker compose -f deploy/docker-compose.yml down
```

---

### 服務端點與可選服務說明
* **前端 Web 介面 (Frontend)**: `http://${SERVER_HOST}:8080` (本機: `http://localhost:8080`)
* **後端 API 規格文件 (FastAPI)**: `http://${SERVER_HOST}:8000/docs` (本機: `http://localhost:8000/docs`)
* **核心資料庫 (PostgreSQL)**: `${SERVER_HOST}:5433` (本機: `localhost:5433`)
* **[Optional] 觀測儀表板 (Langfuse)**: `http://${SERVER_HOST}:3000` (本機: `http://localhost:3000`)
  > **註**：Langfuse 為選用 (Optional) 觀測服務，預設隨 compose 啟動。若部署環境硬體資源有限或不需 LLM 追蹤，可直接在 compose 檔案中將 `langfuse` 服務區塊註解或移除。後端系統內建自動容錯機制，未啟用 Langfuse 時完全不影響核心電路 DRC 檢測流程。

## ⚙️ 系統初始化與首次部署設定 (First-Time Setup Guide)

初次部署完成後，請依循以下步驟進行系統初始化與各服務串接：

### 1. 環境變數設定說明 (`.env`)
專案所有支援之系統環境變數、預設值、格式範例與詳細中文說明，請直接參閱 [`.env.example`](.env.example)。
建立 `.env` 檔案指令：
```bash
cp .env.example .env
```
> [!TIP]
> 亦可於系統啟動後，直接至前端 Web 介面「系統環境與參數設定 (`/settings`)」頁面進行視覺化配置，設定將自動雙向同步回寫至 `.env`。

---

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
     # 開發模式：
     docker compose -f deploy/docker-compose.dev.yml up -d --force-recreate backend

     # 生產模式：
     docker compose -f deploy/docker-compose.yml up -d --force-recreate backend
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

---

## 🔄 常用運維與除錯指令 (Operations & Logs)

### 1. 查看容器即時運行日誌 (View Logs)
由於 Compose 配置檔收納於 `deploy/` 目錄，在專案根目錄下需指定對應的 Compose 檔案，或直接使用 Docker 容器原生指令（推薦，不受目錄限制）：

#### 方式 A：Docker 原生容器指令（最便捷，不受目錄限制）
```bash
# 查看後端即時日誌 (開發模式 / 生產模式)
docker logs -f designshield-backend-dev    # 開發模式
docker logs -f designshield-backend        # 生產模式

# 查看前端即時日誌 (開發模式 / 生產模式)
docker logs -f designshield-frontend-dev   # 開發模式
docker logs -f designshield-frontend       # 生產模式
```

#### 方式 B：Docker Compose 指令（需指定對應配置檔）
```bash
# 開發模式 (Development)：
docker compose -f deploy/docker-compose.dev.yml logs -f backend
docker compose -f deploy/docker-compose.dev.yml logs -f frontend

# 生產模式 (Production)：
docker compose -f deploy/docker-compose.yml logs -f backend
docker compose -f deploy/docker-compose.yml logs -f frontend
```

### 2. 僅重啟既有服務 (未修改代碼，單純重啟行程)
```bash
# 開發模式：
docker compose -f deploy/docker-compose.dev.yml restart

# 生產模式：
docker compose -f deploy/docker-compose.yml restart
```

### 3. 套件依賴更新時重新建置 (Rebuild & Update Dependencies)
當修改了 `frontend/package.json` 或 `backend/requirements.txt` 需要重新安裝套件時：
```bash
# 開發模式（重新建置映像檔並重建匿名 node_modules Volume）：
docker compose -f deploy/docker-compose.dev.yml up -d --build -V

# 生產模式：
docker compose -f deploy/docker-compose.yml up -d --build

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
