# 線路設計規則檢查系統 (Schematic DRC System) - DesignShield

本專案是一套專為硬體工程師設計的自動化「線路設計規則檢查系統」。系統解析 Cadence OrCAD XML，利用 NetworkX 構建圖譜，並結合傳統演算法與大語言模型 (本地 LLM)，自動檢測電路圖缺陷。

## 🚀 核心架構演進
本專案**已全面移除 Celery 與 Redis**，改採 **Postgres DBOS (Durable Execution)** 作為核心任務執行引擎。
* **原生斷點接續**：伺服器重啟可從中斷步驟無縫接續。
* **PrimeVue 視覺化進度**：透過 `step_status` 資料表與 Vue 3 Timeline 元件呈現。
* **雙軌執行**：區分「輕量預先分析」與「重型 DBOS DRC 分析」，避免阻塞。
* **本地 LLM 優先**：支援對接本地 `192.168.1.5:8000/v1` 的 LLM 服務。
* **彈性觀測性**：Langfuse 以獨立 `observability` Profile 按需啟動，支援優雅降級。

## 📚 系統文件導覽 (Documentation)
詳細技術規格與維護手冊請參閱 `docs/` 目錄：
1. **[產品規格書 (product_spec.md)](docs/product_spec.md)**：架構選型、DBOS 排程、本地 LLM 策略。
2. **[資料庫綱要 (database_schema.md)](docs/database_schema.md)**：PostgreSQL 表結構與 `step_status`。
3. **[分析管線 (pipeline_workflow.md)](docs/pipeline_workflow.md)**：雙軌執行路徑與 DBOS Workflow。
4. **[技術維護手冊 (maintenance_guide.md)](docs/maintenance_guide.md)**：微服務、備份與移轉。
5. **[專案結構 (project_structure.md)](docs/project_structure.md)**：目錄配置與隔離策略。

## 💻 啟動指南
```bash
# 1. 建立設定檔
cp .env.example .env

# 2. 啟動核心服務 (Postgres, Backend, Frontend)
cd deploy
docker compose up -d

# 3. 啟動 Langfuse 觀測服務 (選用)
docker compose --profile observability up -d
```
