<template>
  <div class="dashboard-container flex flex-col min-h-screen bg-surface-ground text-vscode-textMain">
    <!-- 1. 頂部極簡單行頁頭列 (高 ~40px，1px 細邊界分隔，移除冗長副標) -->
    <header class="dashboard-header h-10 px-4 flex justify-between items-center border-b border-surface-border bg-surface-header shrink-0">
      <div class="header-left flex items-center gap-2 min-w-0">
        <i class="pi pi-th-large text-primary text-xs"></i>
        <h1 class="page-title text-sm font-semibold text-vscode-textHeading m-0 truncate">
          系統任務總覽儀表板
        </h1>
      </div>

      <div class="header-actions flex items-center gap-1.5">
        <Button
          v-tooltip.bottom="'重新整理儀表板數據'"
          icon="pi pi-refresh"
          severity="secondary"
          text
          size="small"
          class="w-7 h-7 !p-0"
          title="重新整理"
          :loading="isLoading"
          @click="loadDashboardData"
        />
        <Button
          label="新增 DRC 任務"
          icon="pi pi-plus"
          severity="primary"
          size="small"
          class="text-xs py-1 px-2.5 h-7"
          @click="navigateToNewTask"
        />
      </div>
    </header>

    <!-- 2. 緊湊單行數據橫條 (Compact Metric Strip，高 ~42px，divide-x 1px 細線分隔) -->
    <section class="stats-overview-grid grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 divide-y md:divide-y-0 md:divide-x divide-surface-border border-b border-surface-border bg-surface-panel shrink-0">
      <!-- 指標 1: 伺服器健康狀態 (含 FastAPI/DBOS, Database, LLM 燈號與狀態提示) -->
      <div class="stat-card health-stat-card px-3.5 py-2 flex items-center justify-between gap-2 min-w-0">
        <div class="flex items-center gap-2 min-w-0 flex-wrap">
          <span
            class="badge-mini text-[11px] font-medium inline-flex items-center gap-1.5 text-vscode-textHeading shrink-0"
            :class="isHealthy ? 'status-online' : 'status-danger text-vscode-danger'"
          >
            <span
              class="pulse-indicator w-1.5 h-1.5 rounded-full inline-block"
              :class="isHealthy ? 'pulse-green bg-vscode-green' : 'pulse-red bg-vscode-danger'"
            ></span>
            {{ isHealthy ? '健康運作' : '連線異常' }}
          </span>

          <!-- 各元件燈號列表 (FASTAPI/DBOS, Database, LLM) -->
          <div class="health-lights-row flex items-center gap-1 flex-wrap">
            <div
              v-tooltip.bottom="healthDetails.components?.api?.message || 'FastAPI / DBOS 引擎在線'"
              class="light-chip inline-flex items-center gap-1 bg-surface-ground border border-surface-border px-1.5 py-0.5 rounded text-[10px] text-vscode-textSecondary cursor-default"
              :title="healthDetails.components?.api?.message || 'FastAPI / DBOS 引擎在線'"
            >
              <span class="light-dot w-1.5 h-1.5 rounded-full inline-block" :class="getLightDotClass(healthDetails.components?.api?.status)"></span>
              <span class="light-label">FastAPI/DBOS</span>
            </div>
            <div
              v-tooltip.bottom="healthDetails.components?.database?.message || '資料庫連線正常'"
              class="light-chip inline-flex items-center gap-1 bg-surface-ground border border-surface-border px-1.5 py-0.5 rounded text-[10px] text-vscode-textSecondary cursor-default"
              :title="healthDetails.components?.database?.message || '資料庫連線正常'"
            >
              <span class="light-dot w-1.5 h-1.5 rounded-full inline-block" :class="getLightDotClass(healthDetails.components?.database?.status)"></span>
              <span class="light-label">Database</span>
            </div>
            <div
              v-tooltip.bottom="llmChipTooltip"
              class="light-chip inline-flex items-center gap-1 bg-surface-ground border border-surface-border px-1.5 py-0.5 rounded text-[10px] text-vscode-textSecondary cursor-default"
              :title="llmChipTooltip"
            >
              <span class="light-dot w-1.5 h-1.5 rounded-full inline-block" :class="getLightDotClass(healthDetails.components?.llm?.status)"></span>
              <span class="light-label">LLM</span>
            </div>
          </div>
        </div>

        <div
          v-tooltip.bottom="healthHintItems.map((item) => item.text).join(' · ')"
          class="stat-hint health-stat-hint text-[11px] text-vscode-textMuted truncate max-w-[180px] xl:max-w-[160px] shrink-0"
          :title="healthHintItems.map((item) => item.text).join(' · ')"
        >
          <template v-for="(item, idx) in healthHintItems" :key="idx">
            <span v-if="idx > 0" class="hint-separator text-vscode-textMuted mx-1"> · </span>
            <span :class="item.className">{{ item.text }}</span>
          </template>
        </div>
      </div>

      <!-- 指標 2: 儲存空間佔用 (單行整合數值與微型進度條，明細放 Tooltip) -->
      <div
        v-tooltip.bottom="`${storageBarTooltip} | 上傳: ${storageStats.uploads.file_count} (${formatStorageMb(storageStats.uploads.total_bytes)}) · 暫存: ${storageStats.staging.file_count} · 報告: ${storageStats.reports.file_count}`"
        class="stat-card storage-stat-card px-3.5 py-2 flex items-center justify-between gap-3 min-w-0"
      >
        <div class="flex items-center gap-2 min-w-0">
          <i class="pi pi-database text-vscode-textMuted text-xs shrink-0"></i>
          <span class="stat-label text-xs text-vscode-textSecondary shrink-0">儲存佔用</span>
          <span class="stat-value text-xs font-semibold text-vscode-textHeading font-mono">{{ storageStats.total_mb }} MB</span>
          <span class="stat-subtext text-[11px] text-vscode-textMuted truncate">({{ storageStats.total_files }} 檔)</span>
        </div>

        <div class="flex items-center gap-2 shrink-0">
          <div class="mini-bar-container w-16" :title="storageBarTooltip">
            <div class="mini-bar-track h-1.5 bg-surface-ground rounded-sm overflow-hidden flex border border-surface-border">
              <div
                class="mini-bar-fill bar-used bg-primary h-full transition-[width] duration-300"
                :style="{ width: diskUsedBarWidth + '%' }"
              ></div>
              <div
                class="mini-bar-fill bar-free bg-transparent h-full transition-[width] duration-300"
                :style="{ width: (100 - diskUsedBarWidth) + '%' }"
              ></div>
            </div>
          </div>
          <span class="badge-mini status-info text-[10px] text-vscode-textMuted font-mono">
            剩餘 {{ formattedDiskFree }}
          </span>
        </div>
      </div>

      <!-- 指標 3: DRC 規則庫規模 -->
      <div
        v-tooltip.bottom="`傳統演算法規則: ${heuristicRulesCount} 條 | 本地 LLM 語意規則: ${llmRulesCount} 條`"
        class="stat-card px-3.5 py-2 flex items-center justify-between gap-2 min-w-0"
      >
        <div class="flex items-center gap-2 min-w-0">
          <i class="pi pi-sliders-h text-vscode-textMuted text-xs shrink-0"></i>
          <span class="stat-label text-xs text-vscode-textSecondary">規則庫規模</span>
          <span class="stat-value text-xs font-semibold text-vscode-textHeading font-mono">{{ totalRulesCount }} 條</span>
        </div>
        <div class="flex items-center gap-1.5 text-[11px] text-vscode-textMuted shrink-0">
          <span class="badge-mini status-active px-1.5 py-0.5 rounded bg-surface-ground border border-surface-border text-vscode-textSecondary font-mono text-[10px]">
            {{ activeRulesCount }} 啟用
          </span>
          <span class="hidden sm:inline text-[10px]">演算法 {{ heuristicRulesCount }} · LLM {{ llmRulesCount }}</span>
        </div>
      </div>

      <!-- 指標 4: 任務狀態分佈 -->
      <div class="stat-card px-3.5 py-2 flex items-center justify-between gap-2 min-w-0">
        <div class="flex items-center gap-2 min-w-0">
          <i class="pi pi-list-check text-vscode-textMuted text-xs shrink-0"></i>
          <span class="stat-label text-xs text-vscode-textSecondary">任務佇列</span>
          <span class="stat-value text-xs font-semibold text-primary font-mono">{{ runningTasksCount }} 執行中</span>
          <span class="stat-subtext text-[11px] text-vscode-textMuted">/ {{ scheduledTasksCount }} 待排程</span>
        </div>
        <span class="stat-hint text-[11px] text-vscode-textMuted font-mono shrink-0">
          累計完成 {{ completedTasksCount }}
        </span>
      </div>
    </section>

    <!-- 3. 任務清單區塊 (1px 邊界直連，無外圍多餘留白與盒中盒) -->
    <section class="tasks-table-section flex-1 flex flex-col bg-surface-panel min-h-0">
      <!-- 狀態分頁與類型篩選工具列 (高 ~38px) -->
      <div class="section-toolbar flex justify-between items-center px-4 py-1.5 border-b border-surface-border bg-surface-header flex-wrap gap-2">
        <div class="tabs-nav flex gap-1">
          <button
            class="tab-btn border-0 text-xs px-2.5 py-1 rounded cursor-pointer flex items-center transition-colors"
            :class="currentTab === 'running' ? 'active text-vscode-textHeading bg-surface-active font-semibold' : 'bg-transparent text-vscode-textSecondary hover:text-vscode-textHeading hover:bg-surface-hover'"
            @click="currentTab = 'running'"
          >
            <i v-if="runningTasksCount > 0" class="pi pi-spin pi-spinner mr-1 text-[10px] text-primary"></i>
            正在進行中
            <span class="tab-count text-[10px] font-mono bg-surface-ground border border-surface-border text-vscode-textSecondary px-1.5 py-0.2 rounded ml-1.5">{{ runningTasksCount }}</span>
          </button>
          <button
            class="tab-btn border-0 text-xs px-2.5 py-1 rounded cursor-pointer flex items-center transition-colors"
            :class="currentTab === 'scheduled' ? 'active text-vscode-textHeading bg-surface-active font-semibold' : 'bg-transparent text-vscode-textSecondary hover:text-vscode-textHeading hover:bg-surface-hover'"
            @click="currentTab = 'scheduled'"
          >
            等待與排程
            <span class="tab-count text-[10px] font-mono bg-surface-ground border border-surface-border text-vscode-textSecondary px-1.5 py-0.2 rounded ml-1.5">{{ scheduledTasksCount }}</span>
          </button>
          <button
            class="tab-btn border-0 text-xs px-2.5 py-1 rounded cursor-pointer flex items-center transition-colors"
            :class="currentTab === 'completed' ? 'active text-vscode-textHeading bg-surface-active font-semibold' : 'bg-transparent text-vscode-textSecondary hover:text-vscode-textHeading hover:bg-surface-hover'"
            @click="currentTab = 'completed'"
          >
            最近完成 (10)
            <span class="tab-count text-[10px] font-mono bg-surface-ground border border-surface-border text-vscode-textSecondary px-1.5 py-0.2 rounded ml-1.5">{{ filteredCompletedTasks.length }}</span>
          </button>
          <button
            class="tab-btn border-0 text-xs px-2.5 py-1 rounded cursor-pointer flex items-center transition-colors"
            :class="currentTab === 'all' ? 'active text-vscode-textHeading bg-surface-active font-semibold' : 'bg-transparent text-vscode-textSecondary hover:text-vscode-textHeading hover:bg-surface-hover'"
            @click="currentTab = 'all'"
          >
            所有任務
            <span class="tab-count text-[10px] font-mono bg-surface-ground border border-surface-border text-vscode-textSecondary px-1.5 py-0.2 rounded ml-1.5">{{ allTasks.length }}</span>
          </button>
        </div>

        <div class="type-filter flex items-center gap-2">
          <Select
            v-model="selectedTypeFilter"
            :options="typeFilterOptions"
            option-label="label"
            option-value="value"
            size="small"
            class="filter-select text-xs min-w-[140px]"
          />
        </div>
      </div>

      <!-- 任務列表表格 (全面採用 PrimeVue DataTable) -->
      <div class="table-container flex-1 overflow-x-auto">
        <div v-if="isLoading" class="loading-state flex flex-col items-center justify-center py-14 px-6 text-vscode-textMuted">
          <i class="pi pi-spin pi-spinner loading-icon text-xl mb-2 text-vscode-textMuted"></i>
          <span class="text-xs">正在載入任務列表與系統指標...</span>
        </div>

        <div v-else-if="currentDisplayTasks.length === 0" class="empty-state flex flex-col items-center justify-center py-14 px-6 text-vscode-textMuted">
          <i class="pi pi-inbox empty-icon text-xl mb-2 text-vscode-textMuted"></i>
          <p class="empty-text text-xs mb-3">目前尚無符合此條件的任務</p>
          <Button
            label="立即建立新任務"
            icon="pi pi-plus"
            severity="primary"
            size="small"
            class="text-xs"
            @click="navigateToNewTask"
          />
        </div>

        <DataTable
          v-else
          :value="currentDisplayTasks"
          data-key="id"
          size="small"
          :row-class="() => 'task-row cursor-pointer transition-colors hover:bg-surface-hover'"
          class="compact-task-table w-full text-xs [&_td]:!py-2 [&_td]:!px-3.5 [&_th]:!py-2 [&_th]:!px-3.5 [&_th]:!bg-surface-header [&_th]:!text-vscode-textSecondary [&_th]:!font-medium"
          @row-click="(e) => navigateToTask(e.data.id)"
        >
          <Column header="專案名稱 / 任務 ID" style="width: 24%">
            <template #body="{ data: task }">
              <div class="project-name-cell flex items-center justify-between gap-2">
                <div class="flex flex-col gap-0.5 min-w-0">
                  <span class="project-title font-medium text-vscode-textHeading truncate">{{ task.project_name }}</span>
                  <div class="task-id-badge text-[10px] text-vscode-textMuted inline-flex items-center gap-1 font-mono" @click.stop="copyTaskId(task.id)">
                    <code>{{ task.id.substring(0, 12) }}...</code>
                    <i
                      v-tooltip.top="'複製完整 UUID'"
                      class="pi pi-copy copy-icon text-[10px] cursor-pointer opacity-70 hover:opacity-100 hover:text-primary"
                      title="複製完整 UUID"
                    ></i>
                  </div>
                </div>
              </div>
            </template>
          </Column>

          <Column header="任務類型" style="width: 12%">
            <template #body="{ data: task }">
              <span class="badge-type text-[10px] font-medium px-1.5 py-0.5 rounded border" :class="getTypeBadgeClass(task.task_type)">
                {{ formatTaskType(task.task_type) }}
              </span>
            </template>
          </Column>

          <Column header="狀態" style="width: 12%">
            <template #body="{ data: task }">
              <Tag :value="formatStatus(task.status)" :severity="getStatusSeverity(task.status)" class="text-[10px] px-1.5 py-0.5 font-medium" />
            </template>
          </Column>

          <Column header="拓撲特徵摘要" style="width: 26%">
            <template #body="{ data: task }">
              <div class="summary-pills flex gap-1 flex-wrap">
                <span v-if="task.pre_analysis_summary?.component_count" class="pill text-[10px] bg-surface-ground text-vscode-textSecondary px-1.5 py-0.5 rounded border border-surface-border font-mono">
                  {{ task.pre_analysis_summary.component_count }} 元件
                </span>
                <span v-if="task.pre_analysis_summary?.net_count" class="pill text-[10px] bg-surface-ground text-vscode-textSecondary px-1.5 py-0.5 rounded border border-surface-border font-mono">
                  {{ task.pre_analysis_summary.net_count }} 網路
                </span>
                <span
                  v-if="task.pre_analysis_summary?.buses?.length"
                  class="pill pill-cyan text-[10px] px-1.5 py-0.5 rounded border border-primary/30 bg-primary/10 text-primary font-mono"
                >
                  {{ task.pre_analysis_summary.buses.slice(0, 2).join(', ') }}
                </span>
                <span v-if="task.selected_rules?.length" class="pill pill-indigo text-[10px] px-1.5 py-0.5 rounded border border-surface-border bg-surface-ground text-vscode-textSecondary font-mono">
                  {{ task.selected_rules.length }} 規則
                </span>
                <span v-if="!task.pre_analysis_summary?.component_count" class="text-[11px] text-vscode-textMuted">
                  尚未解析
                </span>
              </div>
            </template>
          </Column>

          <Column header="建立時間" style="width: 14%">
            <template #body="{ data: task }">
              <div class="time-cell text-vscode-textMuted text-[11px] font-mono">
                <span>{{ formatDateTime(task.created_at) }}</span>
              </div>
            </template>
          </Column>

          <Column header="操作" style="width: 12%">
            <template #body="{ data: task }">
              <div class="actions-cell flex gap-0.5" @click.stop>
                <Button
                  v-tooltip.top="'進入任務檢測視圖'"
                  icon="pi pi-arrow-right"
                  severity="secondary"
                  size="small"
                  text
                  rounded
                  class="w-6 h-6 !p-0"
                  title="進入任務檢測視圖"
                  @click="navigateToTask(task.id)"
                />
                <Button
                  v-if="task.status === 'PROCESSING'"
                  v-tooltip.top="'中止此任務'"
                  icon="pi pi-stop-circle"
                  severity="warn"
                  size="small"
                  text
                  rounded
                  class="w-6 h-6 !p-0"
                  title="中止此任務"
                  @click="handleStopTask(task.id)"
                />
                <Button
                  v-tooltip.top="'刪除任務與關聯檔案'"
                  icon="pi pi-trash"
                  severity="danger"
                  size="small"
                  text
                  rounded
                  class="w-6 h-6 !p-0"
                  title="刪除任務與關聯檔案"
                  @click="handleDeleteTask(task.id)"
                />
              </div>
            </template>
          </Column>
        </DataTable>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
/**
 * @file DashboardView.vue
 * @description DesignShield 首頁總覽儀表板，採用 2026 1px Grid 零卡片佈局、40px 單行數據橫條與 PrimeVue DataTable
 */

import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import Select from 'primevue/select'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import type { TaskListItem } from '@/types/task'
import type { StorageStats, ServerHealthDetails } from '@/types/settings'
import { copyToClipboard } from '@/utils/clipboard'
import {
  fetchTasks,
  fetchStorageStats,
  checkServerHealth,
  fetchServerHealthDetails,
  fetchPatternTree,
  stopTask,
  deleteTask,
} from '@/services/api'

const router = useRouter()

// 載入狀態與數據
const isLoading = ref<boolean>(false)
const isHealthy = ref<boolean>(true)
const allTasks = ref<TaskListItem[]>([])
const currentTab = ref<'running' | 'scheduled' | 'completed' | 'all'>('running')
const selectedTypeFilter = ref<string>('ALL')

const typeFilterOptions = [
  { label: '全部類型 (All)', value: 'ALL' },
  { label: '線路 DRC 檢測', value: 'DRC' },
  { label: '規則提取 (擴充)', value: 'RULE_EXTRACTION' },
  { label: 'Datasheet 分析 (擴充)', value: 'DATASHEET_ANALYSIS' },
]

// 各伺服器元件健康度詳細資訊 (FastAPI/DBOS, Database, LLM 燈號)
const healthDetails = ref<ServerHealthDetails>({
  status: 'healthy',
  service: 'DesignShield',
  version: '0.1.0',
  components: {
    api: { status: 'healthy', label: 'FASTAPI / DBOS', message: '在線' },
    database: { status: 'healthy', label: 'Database', message: '正常' },
    llm: { status: 'healthy', label: '本地 LLM', provider: 'local', message: '已就緒' },
  },
})

// 規則庫與儲存指標
const totalRulesCount = ref<number>(0)
const activeRulesCount = ref<number>(0)
const heuristicRulesCount = ref<number>(0)
const llmRulesCount = ref<number>(0)

const storageStats = ref<StorageStats>({
  storage_root: './storage',
  uploads: { file_count: 0, total_bytes: 0 },
  staging: { file_count: 0, total_bytes: 0 },
  reports: { file_count: 0, total_bytes: 0 },
  total_files: 0,
  total_bytes: 0,
  total_mb: 0,
  disk_total_bytes: 0,
  disk_used_bytes: 0,
  disk_free_bytes: 0,
  disk_total_gb: 0,
  disk_used_gb: 0,
  disk_free_gb: 0,
  disk_used_percent: 0,
})

/**
 * 燈號顏色類別映射 (低飽和語義色)
 */
const getLightDotClass = (status?: string): string => {
  switch (status) {
    case 'healthy':
      return 'dot-green bg-vscode-green'
    case 'warning':
    case 'degraded':
      return 'dot-amber bg-vscode-yellow'
    case 'error':
    case 'offline':
    case 'unhealthy':
      return 'dot-red bg-vscode-danger'
    default:
      return 'dot-green bg-vscode-green'
  }
}

interface HealthHintItem {
  text: string
  className?: string
}

/**
 * 格式化 LiteLLM 服務提供商名稱為友善顯示字串
 */
const formatProviderName = (provider?: string, label?: string): string => {
  const p = (provider || '').toLowerCase().trim()
  if (p === 'gemini' || p === 'google') return 'Google Gemini'
  if (p === 'openai') return 'OpenAI'
  if (p === 'anthropic') return 'Anthropic'
  if (p === 'openrouter') return 'OpenRouter'
  if (p === 'groq') return 'Groq'
  if (p === 'deepseek') return 'DeepSeek'
  if (p === 'local') return '本地推理 (Local)'
  if (p) {
    return p.charAt(0).toUpperCase() + p.slice(1)
  }

  if (label) {
    if (/gemini/i.test(label)) return 'Google Gemini'
    if (/openai/i.test(label)) return 'OpenAI'
    if (/anthropic/i.test(label)) return 'Anthropic'
    if (/openrouter/i.test(label)) return 'OpenRouter'
    if (/groq/i.test(label)) return 'Groq'
    if (/deepseek/i.test(label)) return 'DeepSeek'
    if (/本地/i.test(label)) return '本地推理 (Local)'
    return label
  }

  return '本地推理 (Local)'
}

/**
 * 伺服器健康狀態說明項目：
 * 1. 正常項目的信息不顯示，如有異常再顯示異常狀況
 * 2. LLM 固定顯示目前採用的 provider；若有異常則附帶異常資訊
 */
const healthHintItems = computed<HealthHintItem[]>(() => {
  const items: HealthHintItem[] = []

  if (!isHealthy.value) {
    items.push({
      text: '伺服器連線異常，請確認後端服務運作狀態',
      className: 'hint-error text-vscode-danger font-medium',
    })
    return items
  }

  const apiComp = healthDetails.value?.components?.api
  const dbComp = healthDetails.value?.components?.database
  const llmComp = healthDetails.value?.components?.llm

  if (apiComp && apiComp.status !== 'healthy') {
    const msg =
      apiComp.message && !apiComp.message.includes('在線') && !apiComp.message.includes('就緒')
        ? apiComp.message
        : '連線異常'
    items.push({
      text: `FastAPI/DBOS: ${msg}`,
      className: 'hint-error text-vscode-danger font-medium',
    })
  }

  if (dbComp && dbComp.status !== 'healthy') {
    const msg = dbComp.message && !dbComp.message.includes('正常') ? dbComp.message : '連線中斷'
    items.push({
      text: `資料庫: ${msg}`,
      className: 'hint-error text-vscode-danger font-medium',
    })
  }

  const providerDisplay = formatProviderName(llmComp?.provider, llmComp?.label)
  if (llmComp && llmComp.status !== 'healthy') {
    const abnormalReason =
      llmComp.message &&
      !llmComp.message.includes('正常') &&
      !llmComp.message.includes('就緒') &&
      !llmComp.message.includes('已配置')
        ? llmComp.message
        : '異常'
    items.push({
      text: `LLM Provider: ${providerDisplay} (${abnormalReason})`,
      className: llmComp.status === 'warning' ? 'hint-warning text-vscode-yellow font-medium' : 'hint-error text-vscode-danger font-medium',
    })
  } else {
    items.push({
      text: `LLM Provider: ${providerDisplay}`,
      className: 'hint-normal text-vscode-textMuted',
    })
  }

  return items
})

const llmChipTooltip = computed(() => {
  const llmComp = healthDetails.value?.components?.llm
  const providerDisplay = formatProviderName(llmComp?.provider, llmComp?.label)
  const modelText = llmComp?.model ? ` | 模型: ${llmComp.model}` : ''
  const msgText = llmComp?.message ? ` | 狀態: ${llmComp.message}` : ''
  return `LLM 提供者: ${providerDisplay}${modelText}${msgText}`
})

const formattedDiskFree = computed(() => {
  if (storageStats.value.disk_free_gb && storageStats.value.disk_free_gb > 0) {
    return `${storageStats.value.disk_free_gb} GB`
  }
  if (storageStats.value.disk_free_bytes && storageStats.value.disk_free_bytes > 0) {
    const mb = Math.round(storageStats.value.disk_free_bytes / (1024 * 1024))
    return `${mb} MB`
  }
  return '充足'
})

const diskUsedBarWidth = computed(() => {
  if (storageStats.value.disk_used_percent !== undefined && storageStats.value.disk_used_percent > 0) {
    return Math.max(3, Math.min(97, storageStats.value.disk_used_percent))
  }
  const mb = storageStats.value.total_mb || 0
  if (mb > 0) {
    return Math.min(60, Math.max(5, Math.round(mb * 2)))
  }
  return 10
})

const storageBarTooltip = computed(() => {
  const free = formattedDiskFree.value
  const percent = storageStats.value.disk_used_percent || 0
  const totalGb = storageStats.value.disk_total_gb ? `${storageStats.value.disk_total_gb} GB` : '未知'
  return `主機磁碟總量: ${totalGb} | 佔用率: ${percent}% | 剩餘可用: ${free}`
})

const formatStorageMb = (bytes: number): string => {
  if (!bytes) return '0 B'
  const mb = bytes / (1024 * 1024)
  if (mb >= 1) {
    return `${mb.toFixed(1)} MB`
  }
  const kb = bytes / 1024
  return `${kb.toFixed(0)} KB`
}

/**
 * 載入 Dashboard 儀表板所有數據
 */
const loadDashboardData = async () => {
  isLoading.value = true
  try {
    const [tasksRes, healthRes, storageRes, patternsRes, healthDetailsRes] = await Promise.allSettled([
      fetchTasks({ limit: 100 }),
      checkServerHealth(),
      fetchStorageStats(),
      fetchPatternTree(),
      fetchServerHealthDetails ? fetchServerHealthDetails() : Promise.resolve(null),
    ])

    if (tasksRes.status === 'fulfilled') {
      allTasks.value = tasksRes.value.tasks || []
      if (
        runningTasksCount.value === 0 &&
        currentTab.value === 'running' &&
        allTasks.value.length > 0
      ) {
        currentTab.value = scheduledTasksCount.value > 0 ? 'scheduled' : 'completed'
      }
    }

    if (healthRes.status === 'fulfilled') {
      isHealthy.value = healthRes.value
    }

    if (healthDetailsRes.status === 'fulfilled' && healthDetailsRes.value) {
      healthDetails.value = healthDetailsRes.value
      if (healthDetailsRes.value.status === 'unhealthy') {
        isHealthy.value = false
      }
    }

    if (storageRes.status === 'fulfilled') {
      storageStats.value = storageRes.value
    }

    if (patternsRes.status === 'fulfilled' && patternsRes.value) {
      const l3 = patternsRes.value.level3 || []
      totalRulesCount.value = l3.length
      activeRulesCount.value = l3.filter((r) => r.is_active !== false).length
      heuristicRulesCount.value = l3.filter((r) => {
        const firstType = r.check_logic?.[0]?.type
        return firstType === 'topology_check' || firstType === 'python_script'
      }).length
      llmRulesCount.value = l3.filter((r) => {
        return r.check_logic?.[0]?.type === 'llm_agent'
      }).length
    }
  } catch (err) {
    console.error('載入儀表板資料失敗:', err)
  } finally {
    isLoading.value = false
  }
}

onMounted(() => {
  loadDashboardData()
})

const runningTasksCount = computed(() => {
  return allTasks.value.filter((t) => t.status === 'PROCESSING').length
})

const scheduledTasksCount = computed(() => {
  return allTasks.value.filter((t) => ['PENDING', 'READY_FOR_RUN'].includes(t.status)).length
})

const completedTasksCount = computed(() => {
  return allTasks.value.filter((t) => ['COMPLETED', 'FAILED', 'CANCELLED'].includes(t.status)).length
})

const filteredCompletedTasks = computed(() => {
  return allTasks.value
    .filter((t) => ['COMPLETED', 'FAILED', 'CANCELLED'].includes(t.status))
    .slice(0, 10)
})

const currentDisplayTasks = computed(() => {
  let list: TaskListItem[] = []

  if (currentTab.value === 'running') {
    list = allTasks.value.filter((t) => t.status === 'PROCESSING')
  } else if (currentTab.value === 'scheduled') {
    list = allTasks.value.filter((t) => ['PENDING', 'READY_FOR_RUN'].includes(t.status))
  } else if (currentTab.value === 'completed') {
    list = filteredCompletedTasks.value
  } else {
    list = allTasks.value
  }

  if (selectedTypeFilter.value !== 'ALL') {
    list = list.filter((t) => (t.task_type || 'DRC') === selectedTypeFilter.value)
  }

  return list
})

const navigateToNewTask = () => {
  router.push('/drc')
}

const navigateToTask = (taskId: string) => {
  router.push({ path: '/drc', query: { taskId } })
}

const copyTaskId = async (id: string) => {
  await copyToClipboard(id)
}

const handleStopTask = async (taskId: string) => {
  try {
    await stopTask(taskId)
    await loadDashboardData()
  } catch (err) {
    console.error('停止任務失敗:', err)
  }
}

const handleDeleteTask = async (taskId: string) => {
  if (!confirm('確定要刪除此任務與其所有暫存檔案嗎？此操作不可逆。')) {
    return
  }
  try {
    await deleteTask(taskId)
    allTasks.value = allTasks.value.filter((t) => t.id !== taskId)
  } catch (err) {
    console.error('刪除任務失敗:', err)
  }
}

const formatTaskType = (type?: string): string => {
  switch (type) {
    case 'RULE_EXTRACTION':
      return '規則提取'
    case 'DATASHEET_ANALYSIS':
      return 'Datasheet'
    default:
      return '線路 DRC'
  }
}

/**
 * 雙色低彩度分類標籤樣式 (主色藍灰 vs 中性暖灰)
 */
const getTypeBadgeClass = (type?: string): string => {
  switch (type) {
    case 'RULE_EXTRACTION':
    case 'DATASHEET_ANALYSIS':
      return 'type-extraction bg-surface-ground border-surface-border text-vscode-textSecondary'
    default:
      return 'type-drc bg-primary/10 border-primary/30 text-primary'
  }
}

const formatStatus = (status: string): string => {
  switch (status) {
    case 'PROCESSING':
      return '執行中'
    case 'READY_FOR_RUN':
      return '待選規則'
    case 'PENDING':
      return '排程中'
    case 'COMPLETED':
      return '已完成'
    case 'FAILED':
      return '失敗'
    case 'CANCELLED':
      return '已中止'
    default:
      return status
  }
}

const getStatusSeverity = (status: string) => {
  switch (status) {
    case 'COMPLETED':
      return 'success'
    case 'PROCESSING':
      return 'info'
    case 'READY_FOR_RUN':
      return 'warn'
    case 'FAILED':
      return 'danger'
    default:
      return 'secondary'
  }
}

const formatDateTime = (isoStr?: string): string => {
  if (!isoStr) return '-'
  try {
    const d = new Date(isoStr)
    return d.toLocaleString('zh-TW', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return isoStr
  }
}
</script>
