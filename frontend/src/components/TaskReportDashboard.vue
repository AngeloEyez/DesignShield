<template>
  <div class="report-dashboard-container flex flex-col gap-5 mt-4 text-surface-200">
    <!-- 總結評分卡區塊 -->
    <div class="summary-cards-grid grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3.5">
      <div class="summary-card card-total bg-surface-card rounded-md p-4 flex items-center gap-3.5 shadow-sm border border-surface-border">
        <div class="card-icon text-2xl text-surface-400 shrink-0"><i class="pi pi-list-check"></i></div>
        <div class="card-data flex flex-col">
          <span class="card-label text-xs text-surface-400 mb-0.5">總檢查規則</span>
          <span class="card-number text-xl font-bold text-surface-900 dark:text-surface-0">{{ summary.total_rules_checked }}</span>
        </div>
      </div>

      <div class="summary-card card-pass bg-surface-card rounded-md p-4 flex items-center gap-3.5 shadow-sm border border-surface-border">
        <div class="card-icon text-2xl text-green-400 shrink-0"><i class="pi pi-check-circle"></i></div>
        <div class="card-data flex flex-col">
          <span class="card-label text-xs text-surface-400 mb-0.5">通過項目 (PASS)</span>
          <span class="card-number text-xl font-bold text-green-400">{{ summary.pass_count }}</span>
        </div>
      </div>

      <div class="summary-card card-fail bg-surface-card rounded-md p-4 flex items-center gap-3.5 shadow-sm border border-surface-border">
        <div class="card-icon text-2xl text-red-400 shrink-0"><i class="pi pi-times-circle"></i></div>
        <div class="card-data flex flex-col">
          <span class="card-label text-xs text-surface-400 mb-0.5">違規項目 (FAIL)</span>
          <span class="card-number text-xl font-bold text-red-400">{{ summary.fail_count }}</span>
        </div>
      </div>

      <div class="summary-card card-warning bg-surface-card rounded-md p-4 flex items-center gap-3.5 shadow-sm border border-surface-border">
        <div class="card-icon text-2xl text-amber-400 shrink-0"><i class="pi pi-exclamation-triangle"></i></div>
        <div class="card-data flex flex-col">
          <span class="card-label text-xs text-surface-400 mb-0.5">潛在風險 (WARN)</span>
          <span class="card-number text-xl font-bold text-amber-400">{{ summary.warning_count }}</span>
        </div>
      </div>

      <div class="summary-card card-rate bg-surface-card rounded-md p-4 flex items-center gap-3.5 shadow-sm border border-surface-border">
        <div class="card-icon text-2xl text-sky-400 shrink-0"><i class="pi pi-percentage"></i></div>
        <div class="card-data flex flex-col">
          <span class="card-label text-xs text-surface-400 mb-0.5">總體通過率</span>
          <span class="card-number text-xl font-bold text-primary">{{ summary.pass_rate_percentage }}%</span>
        </div>
      </div>
    </div>

    <!-- 分類通過分佈區塊 -->
    <div v-if="Object.keys(summary.by_category || {}).length > 0" class="category-breakdown-card bg-surface-card border border-surface-border rounded-md p-4 flex flex-col gap-2.5">
      <h4 class="sub-title m-0 text-sm font-bold text-surface-900 dark:text-surface-0 flex items-center">
        <i class="pi pi-chart-pie mr-2 text-primary"></i> 各類別規則檢查分佈 (Category Breakdown)
      </h4>
      <div class="category-pills flex flex-wrap gap-2">
        <div
          v-for="(stat, catName) in summary.by_category"
          :key="catName"
          class="category-pill flex items-center gap-2 p-2 px-3 rounded bg-surface-ground border border-surface-border text-xs"
        >
          <span class="cat-title font-medium text-surface-200">{{ catName }}</span>
          <span class="cat-stat-badge pass-badge text-[10px] px-1.5 py-0.5 rounded font-mono font-semibold bg-green-500/15 text-green-400 border border-green-500/30">PASS: {{ stat.pass }}</span>
          <span v-if="stat.fail > 0" class="cat-stat-badge fail-badge text-[10px] px-1.5 py-0.5 rounded font-mono font-semibold bg-red-500/15 text-red-400 border border-red-500/30">FAIL: {{ stat.fail }}</span>
          <span v-if="stat.warning > 0" class="cat-stat-badge warn-badge text-[10px] px-1.5 py-0.5 rounded font-mono font-semibold bg-amber-500/15 text-amber-400 border border-amber-500/30">WARN: {{ stat.warning }}</span>
        </div>
      </div>
    </div>

    <!-- 檢測項目與違規清單 -->
    <div class="violations-table-card bg-surface-card border border-surface-border rounded-md p-4 flex flex-col gap-4">
      <div class="table-header-row flex flex-col md:flex-row justify-between items-start md:items-center gap-3 pb-3 border-b border-surface-border">
        <div>
          <h3 class="card-title m-0 text-base font-bold text-surface-900 dark:text-surface-0 flex items-center">
            <i class="pi pi-shield mr-2 text-primary"></i> 詳細檢測結果與工程改善建議
          </h3>
          <p class="card-desc m-0 text-xs text-surface-400 mt-1">點選項目可查看電路節點詳細佐證資訊與 LLM 推理歷程</p>
        </div>

        <!-- 過濾按鈕列 -->
        <div class="filter-btn-group flex items-center gap-1.5 flex-wrap">
          <button
            v-for="filter in filters"
            :key="filter.key"
            class="filter-pill-btn px-2.5 py-1 text-xs rounded border cursor-pointer transition-colors"
            :class="currentFilter === filter.key ? 'bg-primary/20 border-primary text-primary-contrast dark:text-primary-300 font-semibold' : 'border-surface-border bg-surface-ground text-surface-400 hover:text-surface-100 hover:bg-surface-hover'"
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
      <div class="items-list flex flex-col gap-3">
        <div
          v-for="item in filteredItems"
          :key="item.item_id"
          class="violation-item p-3.5 rounded-md border bg-surface-ground/40 flex flex-col gap-2 transition-colors"
          :class="item.status === 'PASS' ? 'border-l-4 border-l-green-500 border-surface-border' : (item.status === 'FAIL' ? 'border-l-4 border-l-red-500 border-surface-border' : 'border-l-4 border-l-amber-500 border-surface-border')"
        >
          <div class="item-main-row flex justify-between items-center gap-2 flex-wrap">
            <div class="item-left flex items-center gap-2 flex-wrap text-xs">
              <span
                class="status-indicator-tag text-[10px] font-bold px-1.5 py-0.5 rounded"
                :class="item.status === 'PASS' ? 'bg-green-500/20 text-green-400' : (item.status === 'FAIL' ? 'bg-red-500/20 text-red-400' : 'bg-amber-500/20 text-amber-400')"
              >
                {{ item.status }}
              </span>
              <span class="severity-indicator-tag text-[10px] font-semibold px-1.5 py-0.5 rounded bg-surface-ground border border-surface-border text-surface-300">
                {{ item.severity }}
              </span>
              <span class="check-type-tag text-[10px] px-1.5 py-0.5 rounded bg-surface-card text-surface-400 border border-surface-border">{{ item.check_type }}</span>
              <span class="item-title font-semibold text-surface-900 dark:text-surface-0 text-xs">{{ item.rule_title }}</span>
              <span class="item-rule-id font-mono text-surface-400 text-xs">({{ item.rule_id }})</span>
            </div>

            <div class="item-right flex items-center">
              <button class="expand-btn flex items-center gap-1 text-xs text-primary hover:underline cursor-pointer bg-transparent border-0 p-1" @click="toggleExpand(item.item_id)">
                <i :class="expandedItems[item.item_id] ? 'pi pi-chevron-up' : 'pi pi-chevron-down'"></i>
                {{ expandedItems[item.item_id] ? '收合佐證' : '查看詳情' }}
              </button>
            </div>
          </div>

          <!-- 說明與工程建議 -->
          <div class="item-description-block text-xs text-surface-300 leading-relaxed flex flex-col gap-1">
            <p class="desc-text m-0">{{ item.description }}</p>
            <p v-if="item.comment" class="comment-text m-0 text-amber-300 flex items-center gap-1">
              <i class="pi pi-lightbulb text-amber-400"></i>
              <strong>工程改善建議：</strong>{{ item.comment }}
            </p>
          </div>

          <!-- 展開佐證區塊 -->
          <div v-if="expandedItems[item.item_id]" class="evidence-details-block mt-2 p-3 bg-surface-950 border border-surface-border rounded flex flex-col gap-2 text-xs">
            <div class="nodes-row flex items-center gap-2 flex-wrap">
              <span class="node-label text-surface-400 font-medium">相關元件:</span>
              <span class="node-tags flex items-center gap-1 flex-wrap">
                <span v-for="c in item.target_nodes.components" :key="c" class="code-chip text-[11px] font-mono px-1.5 py-0.5 rounded bg-surface-ground border border-surface-border text-sky-300">{{ c }}</span>
                <span v-if="!item.target_nodes.components.length" class="text-surface-500">無特定元件</span>
              </span>
              <span class="node-label text-surface-400 font-medium ml-3">相關網路:</span>
              <span class="node-tags flex items-center gap-1 flex-wrap">
                <span v-for="n in item.target_nodes.nets" :key="n" class="code-chip text-[11px] font-mono px-1.5 py-0.5 rounded bg-surface-ground border border-surface-border text-sky-300">{{ n }}</span>
                <span v-if="!item.target_nodes.nets.length" class="text-surface-500">無特定網路</span>
              </span>
            </div>

            <div class="raw-evidence flex flex-col gap-1">
              <span class="evidence-title text-[11px] font-semibold text-surface-400">詳細檢驗佐證 (Evidence Trail):</span>
              <pre class="json-code m-0 font-mono text-[11px] text-surface-300 bg-surface-ground p-2 rounded max-h-48 overflow-y-auto border border-surface-border leading-normal">{{ JSON.stringify(item.evidence_trail, null, 2) }}</pre>
            </div>
          </div>
        </div>

        <div v-if="filteredItems.length === 0" class="empty-items-notice p-8 text-center text-surface-400 flex flex-col items-center gap-2 text-xs">
          <i class="pi pi-inbox text-2xl text-surface-500"></i>
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
 * 匯出完整 JSON 報告
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
