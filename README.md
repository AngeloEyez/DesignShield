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
# 1. 建立設定檔
cp .env.example .env

# 2. 一鍵啟動所有服務 (Postgres, Backend, Frontend, Langfuse)
cd deploy
docker compose up -d
```

### 服務端點與可選服務說明
* **前端 Web 介面 (Frontend)**: `http://localhost:8080`
* **後端 API 規格文件 (FastAPI)**: `http://localhost:8000/docs`
* **核心資料庫 (PostgreSQL)**: `localhost:5433`
* **[Optional] 觀測儀表板 (Langfuse)**: `http://localhost:3000`
  > **註**：Langfuse 為選用 (Optional) 觀測服務，預設隨 `docker compose up -d` 啟動。若部署環境硬體資源有限或不需 LLM 追蹤，可直接在 `deploy/docker-compose.yml` 中將 `langfuse` 服務區塊註解或移除。後端系統內建自動容錯機制，未啟用 Langfuse 時完全不影響核心電路 DRC 檢測流程。

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
