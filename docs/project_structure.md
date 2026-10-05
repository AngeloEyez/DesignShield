# 專案結構與文件策略 (Project Structure)

## 1. 專案資料夾結構規劃 (Monorepo)

採用前後端分離，後端以 FastAPI + DBOS 結合。

```text
schematic-drc-system/
├── docs/                       # 專案文件
├── frontend/                   # Vue 3 前端
│   ├── src/
│   │   ├── components/         # PrimeVue 元件
│   │   └── views/
│   └── tests/                  # 前端隔離測試
├── backend/                    # FastAPI + DBOS 後端
│   ├── app/
│   │   ├── api/                # REST 路由
│   │   ├── models/             # SQLAlchemy ORM
│   │   ├── workflows/          # DBOS 任務工作流 (取代原有的 celery worker)
│   │   └── engine/             # 核心 DRC 演算法與 LLM 處理
│   └── tests/                  # 後端隔離測試
├── deploy/                     # Docker 部署 (不包含 Redis/Celery)
│   ├── docker-compose.yml      # 定義 Postgres, Backend, Frontend (可選 observability profile)
└── README.md
```

## 2. 結構設計重點
* **DBOS 工作流**: 將原有的 Celery task 改為 DBOS Workflow 定義於 `backend/app/workflows/` 中。
* **零依賴中介**: 徹底移除 Celery 與 Redis，簡化維運。
* **本地 LLM 整合**: 程式碼需支援向本地端點 (`192.168.1.5:8000/v1`) 發送請求。
* **Langfuse 解耦**: 透過條件啟動或例外捕獲，確保 observability 模組斷線不影響主業務。
