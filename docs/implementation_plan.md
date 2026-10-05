# 開發實作計畫與筆記 (Implementation Plan & Dev Notes)

這是一份活文件 (Living Document)。它包含了整個系統的「實作分期計畫 (Phases)」與「開發筆記 (ADR / Dev Notes)」。
**給 AI Agent 的指示**：在實作過程中，每完成一個階段，請將 Checklist 打勾，並於下方的「開發筆記」區塊記錄遇到的技術問題、架構決策或環境設定陷阱，確保知識傳承。

---

## 1. 實作計畫 (Implementation Phases)

### ✅ Phase 0: 專案規格與架構確認 (Completed)
- [x] 確立 DBOS (Durable Execution) 架構，移除 Celery/Redis。
- [x] 完成 Database Schema 規劃 (包含 `step_status` 進度追蹤)。
- [x] 確立雙軌執行與 SSE 即時進度推播機制。
- [x] 制定 API 契約 (`docs/api_contract.md`)。

### 🚀 Phase 1: 基礎核心與即時觀測平台 (DBOS, Logging & SSE)
**目標**：優先打造「堅不可摧的任務持久化管理與日誌傳遞系統」，將其作為後續所有功能的 Debug 基礎。
- [ ] **環境建置**：初始化 FastAPI、Postgres (Docker)、Alembic、DBOS 框架與 Vue 3 (PrimeVue)。
- [ ] **資料庫初始化**：實作 `drc_tasks`, `step_status`, `drc_rules` 的 SQLAlchemy Models 與 Alembic 遷移檔。
- [ ] **DBOS 任務骨架**：建立一個基礎的 DBOS Workflow (Dummy Task)，能夠執行多個 Steps 並寫入 `step_status`。
- [ ] **SSE 通道**：實作 FastAPI 的 `/api/v1/tasks/{task_id}/events` Endpoint，透過 DB 輪詢或 LISTEN/NOTIFY 推播進度。
- [ ] **前端即時 UI**：實作 Vue 3 Timeline 元件與即時 Log Terminal 視窗，確保能順暢接收 SSE 並渲染進度。
- [ ] **測試**：編寫整合測試，確保 DBOS 任務啟動後，SSE 能正確廣播每一步的 `step_status` 變更。

### 🧩 Phase 2: 上傳、解析與預先分析管線 (Upload & Pre-analysis Slice)
**目標**：基於 Phase 1 的持久化框架，實作真實的檔案上傳與解析流程，所有動作皆受 DBOS 追蹤。
- [ ] **檔案處理**：實作 `.zip` 上傳與解壓縮的 DBOS Step。
- [ ] **圖譜解析器**：實作 Cadence OrCAD XML Parser，轉換為 NetworkX 二分圖。
- [ ] **預先分析**：掃描圖譜特徵 (IC, Buses)，產生建議規則清單。
- [ ] **前端 UI**：完成「上傳介面」與「規則樹狀圖 (Tree UI)」，並將上傳/解析進度整合至 Phase 1 的 Log Console。
- [ ] **測試**：使用 `backend/tests/fixtures/sch/cartern-sch-si-20260817.xml` 進行端到端 (E2E) 解析測試。

### 🧠 Phase 3: 重型 DRC 執行與 LLM 整合 (Formal DRC & LLM)
**目標**：實作真正的檢測邏輯、LLM 呼叫以及斷點接續。
- [ ] **規則庫播種**：撰寫 `seeds.py` 注入預設 DRC 規則 (Heuristic & LLM)。
- [ ] **演算法實作**：實作 Heuristic 圖論檢查規則。
- [ ] **LLM 整合**：透過 LiteLLM 呼叫本地 `192.168.1.5:8000/v1` 進行邏輯推理，實作 Token/Rate limiting 管理。
- [ ] **斷點接續驗證**：模擬伺服器當機，驗證 DBOS 能夠從 `step_status` 中斷點無縫接續，不重複發送 LLM Request。
- [ ] **報告與 UI**：產出最終 JSON 報告，前端實作 DRC 報告 Dashboard。
- [ ] **測試**：針對 Heuristic 與 Mock LLM 進行完整單元測試。

### ⚙️ Phase 4: 優化、系統設定與運維 (Optimization & Ops)
**目標**：收尾與維護功能。
- [ ] **系統設定**：實作 `system_settings` 的 API 與前端 UI (調整保留天數、逾時)。
- [ ] **垃圾回收**：實作定時清理 `storage/` 暫存區的排程。
- [ ] **Langfuse**：整合 Langfuse 觀測能力 (可選 Profile 容錯處理)。
- [ ] **全端驗收**：執行全專案 E2E 驗收測試。

---

## 2. 開發筆記與架構決策紀錄 (Dev Notes & ADR)

*(各 Phase 實作時，AI Agent 應於此處新增筆記)*

### Phase 0 決策紀錄
* **DBOS 取代 Celery**: 考量到 Checkpointing 與 Resume 的複雜度，決定捨棄 Celery/Redis，改採奠基於 Postgres 的 DBOS。這讓狀態管理變得單一且可靠。
* **Logging First**: 接受 User 建議，將 DBOS 狀態追蹤與 SSE Log Console 移至 Phase 1 優先實作，這樣後續的解壓縮、Parser 開發都能直接利用這套系統進行 Debug 觀測。
