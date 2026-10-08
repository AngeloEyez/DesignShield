# 專案最高原則 (Project Core Principles)

## 1. 語言與文件溝通規範
- 產生回應、撰寫文件、撰寫註解永遠使用繁體中文，包含但不侷限於 Task.md、Implementation Plan.md、Walkthrough.md、commit/PR message。
- 對程式碼都要增加人類易讀的註解；對於新增的 function，務必加入 JSDoc / Docstring 標準格式註解。
- 如果有新建、修改、刪除 API，務必同步更新 API 說明文件。對於產品架構、技術變更調整，也須同步維護 docs/ 內的相關文件以及 README.md 的內容。

## 2. 前端 UI 與架構規範 (Zero-Custom-CSS Policy)
- **嚴禁在任何 `.vue` 檔案中加入 `<style>` 或 `<style scoped>` 標籤**：
  - 本專案已全面達成「0 行自訂 CSS」重構，所有樣式均由 Tailwind CSS 與 PrimeVue v4 Aura 設計令牌管理。
  - 此規則由單元測試 `tests/ArchitectureGuard.test.ts` 自動把關，任何違規將導致測試失敗。
- **優先採用 PrimeVue v4 原生元件**：
  - 各種互動與介面展示（按鈕、彈窗、抽屜、狀態標籤、下拉選單、表格、提示框等），必須優先採用 PrimeVue v4 官方元件（如 `Button`, `Dialog`, `Drawer`, `Tag`, `DataTable`, `Select`, `InputText`, `Popover`, `Toast` 等）及其官方提供的屬性（如 `severity`, `size`, `variant`）。
  - 嚴禁自行用原生 HTML 標籤手寫 CSS 重複造輪子。
- **佈局與客製樣式一律使用 Tailwind CSS 原子類**：
  - 佈局（Flexbox、Grid）、邊距（`p-*`, `m-*`, `gap-*`）、字型、深色模式適應、過渡動效一律在 template class 中直接組合 Tailwind 工具類。
  - 色彩與主題變數善用 PrimeVue 設計語義或全域令牌（如 `bg-surface-ground`, `border-surface-border`, `text-surface-400`, `bg-emerald-500/15` 等）。
- **嚴格保留既有測試選擇器**：
  - 在重構或增修 template 時，必須保留既有單元測試所依賴的語意 class 名稱（如 `.tab-btn`, `.task-row`, `.health-lights-row` 等），避免測試選擇器斷裂。

## 3. 架構品質與安全規範
- 程式碼按照功能結構做適當拆分，避免單一檔案過大；對於超過 1000 行的檔案，必須評估拆分組件或模組的可能性。目標是好維護、好管理、LLM 友善。
- 建立高覆蓋率的單元測試，確保每個階段的程式碼開發品質。
- 密碼和 API Key 一律使用環境變數，不可寫死在程式碼中。
- 每次提交前必須在本地執行全套測試（前端 `npm run test`，後端 pytest），確認 100% 通過才可進行 commit。