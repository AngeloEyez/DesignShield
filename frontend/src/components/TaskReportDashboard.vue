<template>
  <div class="report-dashboard-container">
    <!-- 總結評分卡區塊 -->
    <div class="summary-cards-grid">
      <div class="summary-card card-total">
        <div class="card-icon"><i class="pi pi-list-check"></i></div>
        <div class="card-data">
          <span class="card-label">總檢查規則</span>
          <span class="card-number">{{ summary.total_rules_checked }}</span>
        </div>
      </div>

      <div class="summary-card card-pass">
        <div class="card-icon"><i class="pi pi-check-circle"></i></div>
        <div class="card-data">
          <span class="card-label">通過項目 (PASS)</span>
          <span class="card-number text-success">{{ summary.pass_count }}</span>
        </div>
      </div>

      <div class="summary-card card-fail">
        <div class="card-icon"><i class="pi pi-times-circle"></i></div>
        <div class="card-data">
          <span class="card-label">違規項目 (FAIL)</span>
          <span class="card-number text-danger">{{ summary.fail_count }}</span>
        </div>
      </div>

      <div class="summary-card card-warning">
        <div class="card-icon"><i class="pi pi-exclamation-triangle"></i></div>
        <div class="card-data">
          <span class="card-label">潛在風險 (WARN)</span>
          <span class="card-number text-warning">{{ summary.warning_count }}</span>
        </div>
      </div>

      <div class="summary-card card-rate">
        <div class="card-icon"><i class="pi pi-percentage"></i></div>
        <div class="card-data">
          <span class="card-label">總體通過率</span>
          <span class="card-number text-primary">{{ summary.pass_rate_percentage }}%</span>
        </div>
      </div>
    </div>

    <!-- 分類通過分佈區塊 -->
    <div v-if="Object.keys(summary.by_category || {}).length > 0" class="category-breakdown-card">
      <h4 class="sub-title"><i class="pi pi-chart-pie mr-2"></i> 各類別規則檢查分佈 (Category Breakdown)</h4>
      <div class="category-pills">
        <div
          v-for="(stat, catName) in summary.by_category"
          :key="catName"
          class="category-pill"
        >
          <span class="cat-title">{{ catName }}</span>
          <span class="cat-stat-badge pass-badge">PASS: {{ stat.pass }}</span>
          <span v-if="stat.fail > 0" class="cat-stat-badge fail-badge">FAIL: {{ stat.fail }}</span>
          <span v-if="stat.warning > 0" class="cat-stat-badge warn-badge">WARN: {{ stat.warning }}</span>
        </div>
      </div>
    </div>

    <!-- 檢測項目與違規清單 -->
    <div class="violations-table-card">
      <div class="table-header-row">
        <div>
          <h3 class="card-title"><i class="pi pi-shield mr-2"></i> 詳細檢測結果與工程改善建議</h3>
          <p class="card-desc">點選項目可查看電路節點詳細佐證資訊與 LLM 推理歷程</p>
        </div>

        <!-- 過濾按鈕列 -->
        <div class="filter-btn-group">
          <button
            v-for="filter in filters"
            :key="filter.key"
            class="filter-pill-btn"
            :class="{ active: currentFilter === filter.key }"
            @click="currentFilter = filter.key"
          >
            {{ filter.label }}
          </button>
          <Button
            label="匯出 JSON 報告"
            icon="pi pi-download"
            size="small"
            severity="secondary"
            @click="exportJsonReport"
          />
        </div>
      </div>

      <!-- 檢驗清單 -->
      <div class="items-list">
        <div
          v-for="item in filteredItems"
          :key="item.item_id"
          class="violation-item"
          :class="`border-${item.status.toLowerCase()}`"
        >
          <div class="item-main-row">
            <div class="item-left">
              <span class="status-indicator-tag" :class="`tag-${item.status.toLowerCase()}`">
                {{ item.status }}
              </span>
              <span class="severity-indicator-tag" :class="`severity-${item.severity.toLowerCase()}`">
                {{ item.severity }}
              </span>
              <span class="check-type-tag">{{ item.check_type }}</span>
              <span class="item-title">{{ item.rule_title }}</span>
              <span class="item-rule-id">({{ item.rule_id }})</span>
            </div>

            <div class="item-right">
              <button class="expand-btn" @click="toggleExpand(item.item_id)">
                <i :class="expandedItems[item.item_id] ? 'pi pi-chevron-up' : 'pi pi-chevron-down'"></i>
                {{ expandedItems[item.item_id] ? '收合佐證' : '查看詳情' }}
              </button>
            </div>
          </div>

          <!-- 說明與工程建議 -->
          <div class="item-description-block">
            <p class="desc-text">{{ item.description }}</p>
            <p v-if="item.comment" class="comment-text">
              <i class="pi pi-lightbulb mr-1 text-warning"></i>
              <strong>工程改善建議：</strong>{{ item.comment }}
            </p>
          </div>

          <!-- 展開佐證區塊 -->
          <div v-if="expandedItems[item.item_id]" class="evidence-details-block">
            <div class="nodes-row">
              <span class="node-label">相關元件:</span>
              <span class="node-tags">
                <span v-for="c in item.target_nodes.components" :key="c" class="code-chip">{{ c }}</span>
                <span v-if="!item.target_nodes.components.length" class="text-muted">無特定元件</span>
              </span>
              <span class="node-label ml-3">相關網路:</span>
              <span class="node-tags">
                <span v-for="n in item.target_nodes.nets" :key="n" class="code-chip">{{ n }}</span>
                <span v-if="!item.target_nodes.nets.length" class="text-muted">無特定網路</span>
              </span>
            </div>

            <div class="raw-evidence">
              <span class="evidence-title">詳細檢驗佐證 (Evidence Trail):</span>
              <pre class="json-code">{{ JSON.stringify(item.evidence_trail, null, 2) }}</pre>
            </div>
          </div>
        </div>

        <div v-if="filteredItems.length === 0" class="empty-items-notice">
          <i class="pi pi-inbox text-muted"></i>
          <span>目前過濾條件下無任何項目</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * @file TaskReportDashboard.vue
 * @description 符合 docs/report_schema.md 標準之 DRC 最終檢測報告視覺化 Dashboard 元件
 */

import { ref, computed } from 'vue'
import Button from 'primevue/button'

export interface TargetNodes {
  components: string[]
  nets: string[]
  page_indices?: number[]
}

export interface ViolationItem {
  item_id: string
  rule_id: string
  rule_category: string
  rule_title: string
  check_type: 'HEURISTIC' | 'LLM'
  status: 'PASS' | 'FAIL' | 'WARNING' | 'SKIPPED' | 'ERROR'
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO'
  target_nodes: TargetNodes
  description: string
  comment?: string
  evidence_trail: Record<string, any>
}

export interface ReportSummary {
  total_rules_checked: number
  pass_count: number
  fail_count: number
  warning_count: number
  skip_count: number
  pass_rate_percentage: number
  by_category: Record<string, { pass: number; fail: number; warning: number }>
}

interface Props {
  taskId: string
  summary: ReportSummary
  violations: ViolationItem[]
}

const props = withDefaults(defineProps<Props>(), {
  taskId: '',
  summary: () => ({
    total_rules_checked: 0,
    pass_count: 0,
    fail_count: 0,
    warning_count: 0,
    skip_count: 0,
    pass_rate_percentage: 0.0,
    by_category: {},
  }),
  violations: () => [],
})

const currentFilter = ref<string>('ALL')
const expandedItems = ref<Record<string, boolean>>({})

const filters = [
  { key: 'ALL', label: '全部項目' },
  { key: 'FAIL', label: '違規項目 (FAIL)' },
  { key: 'WARNING', label: '潛在風險 (WARN)' },
  { key: 'PASS', label: '通過項目 (PASS)' },
  { key: 'LLM', label: '本地 LLM 推理' },
  { key: 'HEURISTIC', label: '傳統圖論演算法' },
]

/**
 * 依當前選定條件篩選項目
 */
const filteredItems = computed(() => {
  if (currentFilter.value === 'ALL') return props.violations
  if (currentFilter.value === 'FAIL') return props.violations.filter((v) => v.status === 'FAIL')
  if (currentFilter.value === 'WARNING')
    return props.violations.filter((v) => v.status === 'WARNING')
  if (currentFilter.value === 'PASS') return props.violations.filter((v) => v.status === 'PASS')
  if (currentFilter.value === 'LLM') return props.violations.filter((v) => v.check_type === 'LLM')
  if (currentFilter.value === 'HEURISTIC')
    return props.violations.filter((v) => v.check_type === 'HEURISTIC')
  return props.violations
})

/**
 * 切換項目詳情展開狀態
 * @param {string} itemId 項目 ID
 */
const toggleExpand = (itemId: string) => {
  expandedItems.value[itemId] = !expandedItems.value[itemId]
}

/**
 * 匯出 JSON 報告檔
 */
const exportJsonReport = () => {
  const dataStr =
    'data:text/json;charset=utf-8,' +
    encodeURIComponent(
      JSON.stringify(
        {
          task_id: props.taskId,
          summary: props.summary,
          violations: props.violations,
        },
        null,
        2
      )
    )
  const downloadAnchor = document.createElement('a')
  downloadAnchor.setAttribute('href', dataStr)
  downloadAnchor.setAttribute('download', `drc_report_${props.taskId || 'export'}.json`)
  document.body.appendChild(downloadAnchor)
  downloadAnchor.click()
  downloadAnchor.remove()
}
</script>

<style scoped>
.report-dashboard-container {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  margin-top: 1rem;
}

.summary-cards-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 0.85rem;
}

@media (max-width: 1024px) {
  .summary-cards-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

.summary-card {
  background: var(--vscode-bg-panel, #252526);
  border-radius: 6px;
  padding: 1rem 0.85rem;
  display: flex;
  align-items: center;
  gap: 0.85rem;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.2);
  border: 1px solid var(--vscode-border, #333333);
}

.card-icon {
  font-size: 1.6rem;
  color: var(--vscode-text-muted, #858585);
}

.card-data {
  display: flex;
  flex-direction: column;
}

.card-label {
  font-size: 0.75rem;
  color: var(--vscode-text-muted, #858585);
  font-weight: 500;
}

.card-number {
  font-size: 1.4rem;
  font-weight: 700;
  color: var(--vscode-text-heading, #ffffff);
}

.text-success {
  color: #4ec9b0;
}

.text-danger {
  color: #f14c4c;
}

.text-warning {
  color: #f59e0b;
}

.text-primary {
  color: #38bdf8;
}

.category-breakdown-card {
  background: var(--vscode-bg-panel, #252526);
  border-radius: 6px;
  padding: 1.1rem;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.2);
  border: 1px solid var(--vscode-border, #333333);
}

.sub-title {
  margin: 0 0 0.85rem 0;
  font-size: 0.95rem;
  color: var(--vscode-text-heading, #ffffff);
  display: flex;
  align-items: center;
}

.category-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 0.65rem;
}

.category-pill {
  background: var(--vscode-bg-header, #2d2d2d);
  border: 1px solid var(--vscode-border, #333333);
  border-radius: 4px;
  padding: 0.4rem 0.65rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.cat-title {
  font-weight: 600;
  font-size: 0.82rem;
  color: var(--vscode-text-main, #cccccc);
}

.cat-stat-badge {
  font-size: 0.7rem;
  padding: 0.08rem 0.35rem;
  border-radius: 3px;
}

.pass-badge {
  background: rgba(78, 201, 176, 0.15);
  color: #4ec9b0;
}

.fail-badge {
  background: rgba(241, 76, 76, 0.15);
  color: #f14c4c;
}

.warn-badge {
  background: rgba(245, 158, 11, 0.15);
  color: #f59e0b;
}

.violations-table-card {
  background: var(--vscode-bg-panel, #252526);
  border-radius: 6px;
  padding: 1.25rem;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.2);
  border: 1px solid var(--vscode-border, #333333);
}

.table-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.1rem;
  flex-wrap: wrap;
  gap: 1rem;
}

.card-title {
  margin: 0;
  font-size: 1.1rem;
  color: var(--vscode-text-heading, #ffffff);
}

.card-desc {
  margin: 0.25rem 0 0 0;
  font-size: 0.8rem;
  color: var(--vscode-text-muted, #858585);
}

.filter-btn-group {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.filter-pill-btn {
  background: var(--vscode-bg-header, #2d2d2d);
  border: 1px solid var(--vscode-border, #333333);
  color: var(--vscode-text-secondary, #999999);
  padding: 0.3rem 0.6rem;
  border-radius: 4px;
  font-size: 0.78rem;
  cursor: pointer;
  transition: all 0.15s;
}

.filter-pill-btn:hover {
  background: var(--vscode-bg-hover, #2a2d2e);
  color: #ffffff;
}

.filter-pill-btn.active {
  background: var(--vscode-blue, #007acc);
  color: #ffffff;
  border-color: var(--vscode-blue, #007acc);
}

.items-list {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
}

.violation-item {
  border: 1px solid var(--vscode-border, #333333);
  border-left-width: 4px;
  border-radius: 4px;
  padding: 0.85rem;
  background: var(--vscode-bg-panel, #252526);
  transition: background-color 0.15s;
}

.violation-item:hover {
  background-color: var(--vscode-bg-hover, #2a2d2e);
}

.border-fail {
  border-left-color: #f14c4c;
}

.border-warning {
  border-left-color: #f59e0b;
}

.border-pass {
  border-left-color: #4ec9b0;
}

.item-main-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.4rem;
}

.item-left {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.status-indicator-tag {
  font-size: 0.72rem;
  font-weight: 700;
  padding: 0.12rem 0.4rem;
  border-radius: 3px;
}

.tag-fail {
  background: rgba(241, 76, 76, 0.2);
  color: #f14c4c;
}

.tag-warning {
  background: rgba(245, 158, 11, 0.2);
  color: #f59e0b;
}

.tag-pass {
  background: rgba(78, 201, 176, 0.2);
  color: #4ec9b0;
}

.severity-indicator-tag {
  font-size: 0.68rem;
  font-weight: 600;
  padding: 0.08rem 0.32rem;
  border-radius: 3px;
  border: 1px solid;
}

.severity-critical {
  color: #f87171;
  border-color: #b91c1c;
  background: rgba(185, 28, 28, 0.2);
}

.severity-high {
  color: #fb923c;
  border-color: #c2410c;
  background: rgba(194, 65, 12, 0.2);
}

.severity-medium {
  color: #fbbf24;
  border-color: #b45309;
  background: rgba(180, 83, 9, 0.2);
}

.severity-info {
  color: var(--vscode-text-muted, #858585);
  border-color: var(--vscode-border-light, #3c3c3c);
  background: var(--vscode-bg-header, #2d2d2d);
}

.check-type-tag {
  font-size: 0.68rem;
  background: rgba(197, 134, 192, 0.15);
  color: #c586c0;
  padding: 0.08rem 0.35rem;
  border-radius: 3px;
  font-weight: 600;
}

.item-title {
  font-weight: 600;
  font-size: 0.88rem;
  color: var(--vscode-text-main, #cccccc);
}

.item-rule-id {
  font-size: 0.75rem;
  color: var(--vscode-text-muted, #858585);
  font-family: monospace;
}

.expand-btn {
  background: transparent;
  border: none;
  color: #38bdf8;
  font-size: 0.78rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 0.3rem;
}

.expand-btn:hover {
  text-decoration: underline;
}

.item-description-block {
  margin: 0.4rem 0 0 0;
  font-size: 0.82rem;
  line-height: 1.45;
}

.desc-text {
  margin: 0 0 0.4rem 0;
  color: var(--vscode-text-secondary, #999999);
}

.comment-text {
  margin: 0;
  color: #38bdf8;
  background: var(--vscode-bg-header, #2d2d2d);
  padding: 0.35rem 0.55rem;
  border-radius: 3px;
  border: 1px solid var(--vscode-border, #333333);
}

.evidence-details-block {
  margin-top: 0.75rem;
  padding-top: 0.75rem;
  border-top: 1px dashed var(--vscode-border, #333333);
  font-size: 0.8rem;
}

.nodes-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 0.4rem;
}

.node-label {
  font-weight: 600;
  color: var(--vscode-text-muted, #858585);
}

.code-chip {
  background: var(--vscode-bg-input, #1e1e1e);
  padding: 0.12rem 0.35rem;
  border-radius: 3px;
  font-family: monospace;
  color: #38bdf8;
  border: 1px solid var(--vscode-border, #333333);
}

.raw-evidence {
  margin-top: 0.4rem;
}

.evidence-title {
  display: block;
  font-weight: 600;
  color: var(--vscode-text-muted, #858585);
  margin-bottom: 0.25rem;
}

.json-code {
  background: #1e1e1e;
  color: #4ec9b0;
  padding: 0.65rem;
  border-radius: 4px;
  overflow-x: auto;
  font-size: 0.75rem;
  margin: 0;
  border: 1px solid var(--vscode-border, #333333);
}

.empty-items-notice {
  text-align: center;
  padding: 2.5rem;
  color: var(--vscode-text-muted, #858585);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
}

.ml-3 {
  margin-left: 1rem;
}
</style>
