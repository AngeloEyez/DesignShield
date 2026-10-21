# 線路分析處理管線與圖譜規範 (Pipeline Workflow & Graph Model)

本文檔定義系統後端基於 Postgres DBOS (Durable Execution) 的處理管線流程以及 NetworkX 圖譜資料模型。

---

## 1. NetworkX 圖譜資料模型標準 (Graph Data Model Contract)
系統將線路圖結構化為二分異質圖 (Bipartite Heterogeneous Graph)，包含 Component 與 Net 節點，以及 Pin 邊。

### 1.1 多 BOM Config 與裝配標註圖譜 (Multi-BOM Config & Mounting-Annotated Graph)
1. **BOM Config 正規化**：系統解析 OrCAD XML 元件之 BOM 屬性，支援單一與逗號分隔多組配置（如 `I,X,P,I,I`），提取全域 $N$ 組 BOM Config。
2. **雙軌拓撲與無損分析**：在建構 NetworkX 基礎圖譜時，完整保留所有節點與拓撲邊；透過 `create_config_subgraph(G, config_index, is_mp_mode)` 動態標註元件之 `is_mounted` (布林值) 與 `bom` 代碼。
3. **BOMSLOT 替代料置換機制**：
   - **識別**：Part Reference 包含 `=` 且屬性 `Function`（不區分大小寫）等於 `"BOMSLOT"` 的替代料（如 `J41=Z2`）。
   - **動態置換**：在某 Config 下若基準件（`J41`）不上件（`X`, `NI`）且替代料上件（`I`, `P`, `M`, `NOBOM`），則將替代料規格覆蓋至基準件，且基準件繼承替代料的上件狀態。
   - **孤立節點防護**：完成驗證置換後，系統會自元件字典與圖譜中完全移除原始 BOMSLOT 替代節點，防止產生無連線孤立節點。
   - **衝突檢驗與錯誤累積**：包含基準件缺失、同 Config 同時上件衝突、多 BOMSLOT 競爭上件衝突。檢查時不中斷、累積所有錯誤日誌後再終止流程報錯。

## 2. 雙軌執行路徑 (Dual-Execution Path)

### 2.1 輕量預先分析 (Lightweight Pre-analysis)
* **目的**：避免阻礙後續排隊的重型任務 (Head-of-line blocking)。
* **流程**：使用者上傳檔案後，立即執行輕量的壓縮檔預檢與基本特徵掃描 (如偵測 I2C, SPI, 平台 IC)，並回傳「建議規則清單」供前端樹狀圖渲染。

### 2.2 重型 DRC 任務 (Heavy DRC Workflow via DBOS)
使用者確認規則後，提交正式任務交由 DBOS 引擎以可靠執行模式處理。

```mermaid
flowchart TD
    Submit["提交 DRC 任務 (API)"] --> Init["啟動即時寫入 Step 4 PROCESSING"]
    Init --> DBOS_Queue["進入 DBOS 工作流程"]
    
    subgraph DBOS_Workflow ["DBOS 可靠執行工作流"]
        Step1["步驟 1: 解壓與驗證 (快取命中)"] --> Step2["步驟 2: 解析與建圖 (快取命中)"]
        Step2 --> Step4["步驟 4: 傳統規則比對 (Heuristic)\n規則級非同步 progress_callback 與協程讓渡"]
        Step4 --> Step5["步驟 5: LLM 邏輯推理\n非同步推理與即時進度回呼"]
        Step5 --> Step6["步驟 6: 報告彙整與落地"]
    end
    
    DBOS_Queue --> Step1
    Step4 -.->|即時規則進度 (SSE)| DB["step_status 資料表 / 前端 UI 計時器流暢跳秒"]
    Step5 -.->|調用本地 LLM| LocalLLM["http://192.168.1.5:8000/v1"]
    Step5 -.->|即時規則進度 (SSE)| DB
    Step6 -.->|寫入報告| DB
```

### 2.3 細粒度非同步進度推播與事件迴圈讓渡 (Fine-Grained Async & Event Loop Yielding)
為避免長時間密集圖論比對與沙盒腳本運算造成主執行緒事件迴圈飢餓 (Event Loop Starvation)：
1. **即時狀態宣告**：在 API `start_task_run` 觸發當下，即刻在資料庫中寫入 `HEURISTIC_CHECK` 為 `PROCESSING` 與真實啟動時間戳，使 SSE 連線初次同步時立即啟動前端計時器跳秒，徹底杜絕時間停頓問題。
2. **協程主動讓渡 (Coroutine Yielding)**：在 Step 4 與 Step 5 的各規則迭代循環中，均插入 `await asyncio.sleep(0)`，將 CPU 控制權定期讓渡給 FastAPI asyncio 事件迴圈，保證 SSE 串流能以毫秒級即時推播當前進度（如 `[1/12] 正在比對傳統演算法規則「...」`）。
3. **前端進度儀表板動態切換**：前端工作流歷程時間軸 (TaskTimeline) 移除卡片底部微進度條，改由 Step 4/Step 5 Detail 抽屜 (StepCheckStatusDrawer) 於 `PROCESSING` 期間顯示包含 PrimeVue ProgressBar、目前確認中規則標籤與項目計數的完整進度卡片；步驟完成 (`COMPLETED`) 後自動隱藏進度條，僅保留結果詳情。

### 2.4 原生斷點接續 (DBOS Checkpointing)
因採用 DBOS，每完成一個步驟或呼叫外部 API (如 LLM)，DBOS 皆會原生持久化狀態至 PostgreSQL。
若伺服器當機或意外重啟，DBOS 啟動後會自動從最後完成的步驟 (Step) 接續執行，無需手動編寫複雜的 Checkpoint/Resume 邏輯，徹底實現零 Token 浪費與高穩定性。
