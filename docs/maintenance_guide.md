# 技術維護手冊 (Technical Maintenance & Operations Manual)

本文檔提供系統架構的微服務維護、容器 Port、備份策略及環境移轉指南。

---

## 1. 系統架構與微服務 (Microservices)

完全移除 Redis 與 Celery，採用 DBOS + Postgres 作為唯一依賴。

| 服務名稱 | 容器名稱 | 核心技術棧 | 職責與用途說明 |
| :--- | :--- | :--- | :--- |
| **前端應用** | `frontend` | Vue 3, Vite, PrimeVue | 提供 Web 儀表板與 Timeline 進度渲染。 |
| **後端與 DBOS 節點** | `backend-api` | FastAPI, DBOS, Python | 提供 REST API 並同時作為 DBOS Worker 處理長時間 DRC 任務。 |
| **資料庫** | `postgres` | PostgreSQL 16 | 儲存業務資料及 DBOS 原生可靠執行狀態 (Journal/State)。 |
| **觀測追蹤 (選用)**| `langfuse` | Langfuse | 透過 `observability` Profile 獨立啟動，追蹤 LLM Token 與效能。 |

## 2. Docker 連接埠與路徑

* **Frontend**: `80` (Prod) / `5173` (Dev)
* **Backend API**: `8000`
* **PostgreSQL**: `5432` (內部網路)
* **本地 LLM**: 外部網路指向 `http://192.168.1.5:8000/v1`
* **Langfuse**: `3000` (若啟動 Profile)

### 檔案暫存區 (TTL 由系統設定介面管理，預設 7 天)：
* `storage/uploads/`: 原始上傳
* `storage/staging/`: 解析中繼
* `storage/reports/`: JSON/PDF 報告輸出

## 3. 備份策略 (Backup Strategy)
系統狀態完全集中於 PostgreSQL (包含 DBOS 狀態)。
僅需針對 `postgres` 容器執行 `pg_dump`，與備份 `storage/` 實體檔案即可達成完整災難復原。

## 4. Langfuse 獨立部署 (Observability Profile)
考量資源限制，Langfuse 可透過 Docker Compose Profile 開啟：
`docker compose --profile observability up -d`
若未啟動，後端系統具有優雅降級 (Graceful Degradation) 能力，不影響主線路分析。
