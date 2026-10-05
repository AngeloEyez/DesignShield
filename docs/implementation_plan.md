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
- [x] **環境建置**：初始化 FastAPI、Postgres (Docker)、Alembic、DBOS 框架與 Vue 3 (PrimeVue)。
- [x] **資料庫初始化**：實作 `drc_tasks`, `step_status`, `drc_rules` 的 SQLAlchemy Models 與 Alembic 遷移檔。
- [x] **DBOS 任務骨架**：建立一個基礎的 DBOS Workflow (Dummy Task)，能夠執行多個 Steps 並寫入 `step_status`。
- [x] **SSE 通道**：實作 FastAPI 的 `/api/v1/tasks/{task_id}/events` Endpoint，透過 DB 輪詢或 LISTEN/NOTIFY 推播進度。
- [x] **前端即時 UI**：實作 Vue 3 Timeline 元件與即時 Log Terminal 視窗，確保能順暢接收 SSE 並渲染進度。
- [x] **測試**：編寫整合測試，確保 DBOS 任務啟動後，SSE 能正確廣播每一步的 `step_status` 變更。

### 🧩 Phase 2: 上傳、解析與預先分析管線 (Upload & Pre-analysis Slice)
**目標**：基於 Phase 1 的持久化框架，實作真實的檔案上傳與解析流程，所有動作皆受 DBOS 追蹤。
- [x] **檔案處理**：實作 `.zip` 上傳與解壓縮的 DBOS Step。
- [x] **圖譜解析器**：實作 Cadence OrCAD XML Parser，轉換為 NetworkX 二分圖。
- [x] **預先分析**：掃描圖譜特徵 (IC, Buses)，產生建議規則清單。
- [x] **前端 UI**：完成「上傳介面」與「規則樹狀圖 (Tree UI)」，並將上傳/解析進度整合至 Phase 1 的 Log Console。
- [x] **測試**：使用 `backend/tests/fixtures/sch/cartern-sch-si-20260817.xml` 進行端到端 (E2E) 解析測試。

### 🧠 Phase 3: 重型 DRC 執行與 LLM 整合 (Formal DRC & LLM)
**目標**：實作真正的檢測邏輯、LLM 呼叫以及斷點接續。
- [x] **規則庫播種**：撰寫 `seeds.py` 注入預設 DRC 規則 (Heuristic & LLM)。
- [x] **演算法實作**：實作 Heuristic 圖論檢查規則 (I2C 地址衝突、電容耐壓降額、去耦電容、ESD 保護)。
- [x] **LLM 整合**：透過 LiteLLM 呼叫本地 `192.168.1.5:8000/v1` 進行邏輯推理，實作 Token/Rate limiting 管理與優雅降級。
- [x] **斷點接續驗證**：模擬伺服器當機，驗證 DBOS 能夠從 `step_status` 中斷點無縫接續，不重複發送 LLM Request。
- [x] **報告與 UI**：產出最終 JSON 報告，前端實作 DRC 報告 Dashboard。
- [x] **測試**：針對 Heuristic 與 Mock LLM 進行完整單元測試。

### ⚙️ Phase 4: 優化、系統設定與運維 (Optimization & Ops)
**目標**：收尾與維護功能。
- [x] **系統設定**：實作 `system_settings` 的 API 與前端 UI (調整保留天數、逾時、LLM 配置)。
- [x] **垃圾回收**：實作 `cleaner.py` 磁碟空間健康指標與過期檔案生命週期清理排程/手動觸發。
- [x] **Langfuse**：整合 Langfuse 觀測能力 (Docker compose profile 與 LiteLLM callback 容錯處理)。
- [x] **全端驗收**：執行全專案 E2E 驗收測試 (`test_e2e_workflow.py`)，驗證上傳至報告匯出之全流程。

---

## 2. 開發筆記與架構決策紀錄 (Dev Notes & ADR)

*(各 Phase 實作時，AI Agent 應於此處新增筆記)*

### Phase 0 決策紀錄
* **DBOS 取代 Celery**: 考量到 Checkpointing 與 Resume 的複雜度，決定捨棄 Celery/Redis，改採奠基於 Postgres 的 DBOS。這讓狀態管理變得單一且可靠。
* **Logging First**: 接受 User 建議，將 DBOS 狀態追蹤與 SSE Log Console 移至 Phase 1 優先實作，這樣後續的解壓縮、Parser 開發都能直接利用這套系統進行 Debug 觀測。

### Phase 1 實作筆記與決策紀錄
* **DBOS 測試環境持久化**: DBOS v3.2.0 的 SQLite 實作中，若使用 `sqlite:///:memory:` 會因 SingletonThreadPool 不支援連線池 kwargs (`pool_timeout`, `max_overflow`) 而拋出異常。解決方案為測試環境統一配置獨立的 SQLite 暫存檔（例如 `test_dbos.db`），生產環境則使用 PostgreSQL。
* **資料庫多連線隔離與 StaticPool**: 測試中的 FastAPI TestClient 跨執行緒執行，測試用 SQLite 引擎需使用 `check_same_thread=False` 與 SessionMaker 覆蓋，確保所有測試案例擁有獨立乾淨的 schema 與資料。
* **SSE 歷史狀態回放機制**: `/api/v1/tasks/{task_id}/events` 在前端連線建立初期，先查詢 `step_status` 表歷史所有步驟並推播一次，接著進入 300ms 輪詢迴圈僅推播有變更的狀態，並在終端狀態 (`COMPLETED`/`FAILED`) 廣播 `task_end` 後自動關閉連線，完美防範重複資料與記憶體洩漏。
* **測試覆蓋率**: Phase 1 後端單元測試覆蓋率達到 94%（19 個測試案例全數通過），前端 Vitest 測試覆蓋率達到 100%（5 個測試案例全數通過）。

### Phase 2 實作筆記與決策紀錄
* **Cadence OrCAD XML 串流解析**: OrCAD XML 檔案規模通常相當龐大（測試 fixture 檔案達 11MB、12.5 萬行）。傳統 `xml.etree.ElementTree.parse()` 全載入會消耗大量記憶體，改採 `ET.iterparse()` 串流迭代 `PartInst` 與 `Alias` 並呼叫 `elem.clear()`，解析時間降至 0.15 秒內。
* **二分異質圖 (Bipartite Graph) 模型與多重邊映射**: 線路中的多接腳 (如晶片的多支 GND 腳) 連接同一 Net 時，在無向簡單圖中會折疊為唯一邊；在 `parse_allegro_netlist` 統計中記錄全部 1156 個 pin 連線，並在 NetworkX 二分圖中穩定維護 548 節點與 886 條唯一連線拓撲。
* **匯流排正規表達式防護**: PCIE 與 USB 協定均使用 TXP/TXN 差分信號命名，透過將 PCIE 模式前置並提高 USB 命名精準度，避免了介面模式交叉誤判。
* **測試覆蓋率**: Phase 2 後端單元測試覆蓋率達到 91%（30 個測試案例全數通過），前端 Vitest 測試達到 100%（9 個測試案例全數通過）。
 
### Phase 3 實作筆記與決策紀錄
* **預設規則種子與系統自檢**: 系統啟動時透過 `backend/app/db/seeds.py` 檢查 `drc_rules` 資料表，若為空即自動灌入 4 條啟發式與 3 條 LLM 預設檢測規則，包含晶片位址防衝突、電容耐壓降額比率與 high-speed 差分端接檢查。
* **確定性啟發式演算法設計**:
  - `I2C Address Conflict`: 掃描二分圖中屬於同一 I2C Bus 的裝置節點，結合 `KNOWN_I2C_DEVICE_ADDRESSES` 與接腳拓撲，定位潛在重疊之裝置並標示等級為 ERROR。
  - `Capacitor Derating Check`: 解析電容 description (例如 `10V_X7R`) 與電源 net 額定電壓 (如 5V)，當耐壓低於 $V_{net} / 0.7$ 或甚至低於 $V_{net}$ 時，精準標記 WARNING 或 ERROR，並提供降額計算公式作為修復指引。
  - `Decoupling Capacitor & ESD Protection`: 檢查 IC 電源引腳 2-hop 範圍內是否存在 < 1uF 去耦電容，以及外部連接器 (USB/HDMI/RJ45) 訊號針腳是否有 TVS/ESD 保護晶片直連。
* **LLM 呼叫架構與離線優雅降級**:
  - 透過 LiteLLM 對接本地 `192.168.1.5:8000/v1` 的 OpenAI 相容 API。
  - 實現 `extract_interface_subgraph_context` 精準萃取子圖上下文 (Net, Pin, Type, Value)，避免龐大全圖塞爆 Context Window。
  - 當地端 LLM 服務離線、連線逾時或回應不可解析時，自動啟動「專家啟發式降級 (Heuristic Fallback)」備用檢查，確保任務永遠能平穩完成且不致拋出未捕獲崩潰。
* **DBOS 冪等性與中斷點接續 (Checkpoint & Resume)**:
  - 任務執行中，各 Step 開始前皆會先行檢查 `step_status` 中該步驟是否已為 `COMPLETED`。
  - 若已完成則直接重用現有結果或快速跳過，若先前的步驟崩潰中斷，伺服器重啟或重試時可從未完成步驟無縫接續，避免重疊執行重度 LLM 請求。
* **報告資料規格合規**:
  - 依據 `docs/report_schema.md` 規範產出結構化 JSON 與 DrcReport 紀錄。
  - 前端實作 `TaskReportDashboard.vue`，具備統計圖卡 (Total/Error/Warning/Info)、分類篩選、條目展開佐證 (Evidence & Suggestion) 與一鍵匯出功能。
* **測試覆蓋率**: Phase 3 後端單元測試覆蓋率達到 92%（43 個測試案例全數通過），前端 Vitest 測試達到 100%（12 個測試案例全數通過）。

### Phase 4 實作筆記與決策紀錄
* **磁碟儲存管理與生命週期垃圾回收 (Garbage Collection)**:
  - 實作 `backend/app/engine/cleaner.py`，支援遞迴計算 `uploads/`, `staging/`, `reports/` 之目錄容量與檔案數量。
  - 透過 `cleanup_expired_files(retention_days)` 比對檔案最後修改時間戳 `os.path.getmtime`，支援 `dry_run` 試算與正式清除過期上傳檔案與解壓暫存目錄。
  - 提供 `/api/v1/settings/storage-stats` 與 `/api/v1/settings/cleanup` 端點，讓系統運維人員可在前端儀表板即時掌握磁碟健康狀況並手動或自動回收資源。
* **動態系統參數管理 (System Settings)**:
  - 於 `backend/app/db/seeds.py` 注入預設 `upload_retention_days` (7 天)、`task_timeout_seconds` (3600 秒)、`llm_config` (本地推理端點) 與 `auto_cleanup_schedule`。
  - 支援透過 REST API 動態查詢與更新，前端提供 `SystemSettingsModal.vue` 互動介面。
* **Langfuse 觀測整合與容錯架構**:
  - 在 `deploy/docker-compose.yml` 中以 Docker Profile (`profiles: ["observability"]`) 宣告 Langfuse 服務，支援本機或正式環境選擇性啟動。
  - `llm.py` 動態偵測 `LANGFUSE_PUBLIC_KEY` 與 `LANGFUSE_SECRET_KEY`，存在時安全註冊 LiteLLM callbacks，缺失或無效時自動略過，確保核心 DRC 執行永遠零阻礙。
* **Pytest 測試環境與 DBOS 生命週期隔離陷阱**:
  - 當多個測試混合使用 FastAPI `TestClient` 與直接 Workflow 調用時，`TestClient` 結束時觸發的 FastAPI Lifespan 會呼叫 `shutdown_dbos()`。
  - 若直接 destroy DBOS 引擎，後續測試將遭遇 `DBOS Error: System database accessed before DBOS was launched`。
  - 解決方案：在 `backend/app/workflows/dbos_app.py` 中偵測 `PYTEST_CURRENT_TEST` 環境變數，於測試期間豁免每次 HTTP 請求關閉 DBOS，統一由 `conftest.py` 的 session-scoped fixture 管理全域生命週期。
* **端到端 (E2E) 整合驗收**:
  - `test_e2e_workflow.py` 完整模擬真實使用者情境：上傳真實 12.5 萬行 OrCAD XML -> 預先特徵分析 -> 規則選取 -> 啟動 DRC -> DBOS 雙軌執行 -> 報告產出與下載 -> 儲存空間指標查詢與清理。
* **測試覆蓋率**: Phase 4 完成後，後端 49 個單元與整合測試全數通過（覆蓋率達 91%），前端 16 個 Vitest 測試全數通過（覆蓋率達 100%），前端 TypeScript 編譯 (`vue-tsc && vite build`) 零警告成功通過。
