<template>
  <div class="dashboard-container">
    <!-- 頂部頁頭資訊與主要操作 -->
    <header class="dashboard-header">
      <div class="header-left">
        <h1 class="page-title">
          <i class="pi pi-th-large text-cyan mr-2"></i>
          系統任務總覽儀表板 (Mission Dashboard)
        </h1>
        <p class="page-subtitle">
          實時監控所有 DRC 線路檢測與分析任務、系統伺服器健康狀況與儲存磁碟佔用指標。
        </p>
      </div>

      <div class="header-actions">
        <Button
          label="重新整理"
          icon="pi pi-refresh"
          severity="secondary"
          size="small"
          :loading="isLoading"
          @click="loadDashboardData"
        />
        <Button
          label="新增 DRC 任務"
          icon="pi pi-plus"
          severity="primary"
          size="small"
          @click="navigateToNewTask"
        />
      </div>
    </header>

    <!-- 系統健康度與關鍵指標卡片列 -->
    <section class="stats-overview-grid">
      <!-- 指標 1: 伺服器健康狀態 -->
      <div class="stat-card">
        <div class="stat-icon-wrapper bg-green-light">
          <i class="pi pi-server text-green"></i>
        </div>
        <div class="stat-body">
          <span class="stat-label">伺服器健康狀態</span>
          <div class="stat-value-row">
            <span class="stat-value text-green">{{ isHealthy ? '健康運作' : '連線異常' }}</span>
            <span class="badge-mini status-online">FastAPI / DBOS</span>
          </div>
          <span class="stat-hint">耐久執行工作流引擎正常就緒</span>
        </div>
      </div>

      <!-- 指標 2: 儲存空間佔用 -->
      <div class="stat-card">
        <div class="stat-icon-wrapper bg-blue-light">
          <i class="pi pi-database text-blue"></i>
        </div>
        <div class="stat-body">
          <span class="stat-label">儲存空間總佔用</span>
          <div class="stat-value-row">
            <span class="stat-value">{{ storageStats.total_mb }} MB</span>
            <span class="stat-subtext">{{ storageStats.total_files }} 個檔案</span>
          </div>
          <span class="stat-hint">
            上傳: {{ storageStats.uploads.file_count }} | 暫存: {{ storageStats.staging.file_count }} | 報告: {{ storageStats.reports.file_count }}
          </span>
        </div>
      </div>

      <!-- 指標 3: DRC 規則庫規模 -->
      <div class="stat-card">
        <div class="stat-icon-wrapper bg-purple-light">
          <i class="pi pi-sliders-h text-purple"></i>
        </div>
        <div class="stat-body">
          <span class="stat-label">規則庫規模</span>
          <div class="stat-value-row">
            <span class="stat-value">{{ totalRulesCount }} 條</span>
            <span class="badge-mini status-active">{{ activeRulesCount }} 條啟用中</span>
          </div>
          <span class="stat-hint">
            傳統演算法: {{ heuristicRulesCount }} | 本地 LLM: {{ llmRulesCount }}
          </span>
        </div>
      </div>

      <!-- 指標 4: 任務狀態分佈 -->
      <div class="stat-card">
        <div class="stat-icon-wrapper bg-cyan-light">
          <i class="pi pi-list-check text-cyan"></i>
        </div>
        <div class="stat-body">
          <span class="stat-label">進行中與已排程任務</span>
          <div class="stat-value-row">
            <span class="stat-value text-cyan">{{ runningTasksCount }} 執行中</span>
            <span class="stat-subtext">/ {{ scheduledTasksCount }} 等待排程</span>
          </div>
          <span class="stat-hint">累計完成檢測: {{ completedTasksCount }} 筆</span>
        </div>
      </div>
    </section>

    <!-- 任務清單區塊 (含狀態分頁 Tab) -->
    <section class="tasks-table-section">
      <div class="section-toolbar">
        <div class="tabs-nav">
          <button
            class="tab-btn"
            :class="{ active: currentTab === 'running' }"
            @click="currentTab = 'running'"
          >
            <i class="pi pi-spin pi-spinner mr-1" v-if="runningTasksCount > 0"></i>
            正在進行中
            <span class="tab-count">{{ runningTasksCount }}</span>
          </button>
          <button
            class="tab-btn"
            :class="{ active: currentTab === 'scheduled' }"
            @click="currentTab = 'scheduled'"
          >
            等待與排程
            <span class="tab-count">{{ scheduledTasksCount }}</span>
          </button>
          <button
            class="tab-btn"
            :class="{ active: currentTab === 'completed' }"
            @click="currentTab = 'completed'"
          >
            已完成與歷史紀錄 (最近 10 筆)
            <span class="tab-count">{{ filteredCompletedTasks.length }}</span>
          </button>
          <button
            class="tab-btn"
            :class="{ active: currentTab === 'all' }"
            @click="currentTab = 'all'"
          >
            所有任務
            <span class="tab-count">{{ allTasks.length }}</span>
          </button>
        </div>

        <div class="type-filter">
          <span class="filter-label">任務類型:</span>
          <select v-model="selectedTypeFilter" class="filter-select">
            <option value="ALL">全部類型 (All)</option>
            <option value="DRC">線路 DRC 檢測</option>
            <option value="RULE_EXTRACTION">規則提取 (擴充)</option>
            <option value="DATASHEET_ANALYSIS">Datasheet 分析 (擴充)</option>
          </select>
        </div>
      </div>

      <!-- 任務列表表格 -->
      <div class="table-container">
        <div v-if="isLoading" class="loading-state">
          <i class="pi pi-spin pi-spinner loading-icon"></i>
          <span>正在載入任務列表與系統指標...</span>
        </div>

        <div v-else-if="currentDisplayTasks.length === 0" class="empty-state">
          <i class="pi pi-inbox empty-icon"></i>
          <p class="empty-text">目前尚無符合此條件的任務</p>
          <Button
            label="立即建立新任務"
            icon="pi pi-plus"
            severity="primary"
            size="small"
            @click="navigateToNewTask"
          />
        </div>

        <table v-else class="compact-task-table">
          <thead>
            <tr>
              <th style="width: 24%">專案名稱 / 任務 ID</th>
              <th style="width: 13%">任務類型</th>
              <th style="width: 14%">狀態</th>
              <th style="width: 22%">拓撲特徵摘要</th>
              <th style="width: 15%">建立時間</th>
              <th style="width: 12%">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="task in currentDisplayTasks"
              :key="task.id"
              class="task-row"
              @click="navigateToTask(task.id)"
            >
              <td>
                <div class="project-name-cell">
                  <span class="project-title">{{ task.project_name }}</span>
                  <div class="task-id-badge" @click.stop="copyTaskId(task.id)">
                    <code>{{ task.id.substring(0, 16) }}...</code>
                    <i class="pi pi-copy copy-icon" title="複製完整 UUID"></i>
                  </div>
                </div>
              </td>
              <td>
                <span class="badge-type" :class="getTypeBadgeClass(task.task_type)">
                  {{ formatTaskType(task.task_type) }}
                </span>
              </td>
              <td>
                <Tag :value="formatStatus(task.status)" :severity="getStatusSeverity(task.status)" />
              </td>
              <td>
                <div class="summary-pills">
                  <span v-if="task.pre_analysis_summary?.component_count" class="pill">
                    {{ task.pre_analysis_summary.component_count }} 元件
                  </span>
                  <span v-if="task.pre_analysis_summary?.net_count" class="pill">
                    {{ task.pre_analysis_summary.net_count }} 網路
                  </span>
                  <span
                    v-if="task.pre_analysis_summary?.buses?.length"
                    class="pill pill-cyan"
                  >
                    {{ task.pre_analysis_summary.buses.slice(0, 2).join(', ') }}
                  </span>
                  <span v-if="task.selected_rules?.length" class="pill pill-indigo">
                    {{ task.selected_rules.length }} 規則
                  </span>
                  <span v-if="!task.pre_analysis_summary?.component_count" class="text-muted">
                    尚未解析
                  </span>
                </div>
              </td>
              <td>
                <div class="time-cell">
                  <span>{{ formatDateTime(task.created_at) }}</span>
                </div>
              </td>
              <td>
                <div class="actions-cell" @click.stop>
                  <Button
                    icon="pi pi-arrow-right"
                    severity="info"
                    size="small"
                    text
                    rounded
                    title="進入任務檢測視圖"
                    @click="navigateToTask(task.id)"
                  />
                  <Button
                    v-if="task.status === 'PROCESSING'"
                    icon="pi pi-stop-circle"
                    severity="warn"
                    size="small"
                    text
                    rounded
                    title="中止此任務"
                    @click="handleStopTask(task.id)"
                  />
                  <Button
                    icon="pi pi-trash"
                    severity="danger"
                    size="small"
                    text
                    rounded
                    title="刪除任務與關聯檔案"
                    @click="handleDeleteTask(task.id)"
                  />
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
/**
 * @file DashboardView.vue
 * @description DesignShield 首頁總覽儀表板，提供任務分類導航、系統健康狀態與儲存佔用統計
 */

import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import type { TaskListItem } from '@/types/task'
import type { StorageStats } from '@/types/settings'
import {
  fetchTasks,
  fetchStorageStats,
  checkServerHealth,
  fetchRules,
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
})

/**
 * 載入 Dashboard 儀表板所有數據
 */
const loadDashboardData = async () => {
  isLoading.value = true
  try {
    const [tasksRes, healthRes, storageRes, rulesRes] = await Promise.allSettled([
      fetchTasks({ limit: 100 }),
      checkServerHealth(),
      fetchStorageStats(),
      fetchRules(),
    ])

    if (tasksRes.status === 'fulfilled') {
      allTasks.value = tasksRes.value.tasks || []
      // 若目前進行中無任務且有等待或完成任務，預設切換至有任務的標籤
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

    if (storageRes.status === 'fulfilled') {
      storageStats.value = storageRes.value
    }

    if (rulesRes.status === 'fulfilled') {
      const rules = rulesRes.value || []
      totalRulesCount.value = rules.length
      activeRulesCount.value = rules.filter((r) => r.is_active).length
      heuristicRulesCount.value = rules.filter((r) => r.check_type === 'HEURISTIC').length
      llmRulesCount.value = rules.filter((r) => r.check_type === 'LLM').length
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

// 計算不同狀態數量
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
    .slice(0, 10) // 顯示最近 10 筆已完成/已結束任務
})

/**
 * 依據 Tab 與類型篩選後的任務清單
 */
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

// 導航控制
const navigateToNewTask = () => {
  router.push('/drc')
}

const navigateToTask = (taskId: string) => {
  router.push({ path: '/drc', query: { taskId } })
}

const copyTaskId = async (id: string) => {
  try {
    await navigator.clipboard.writeText(id)
  } catch {
    // 忽略剪貼簿錯誤
  }
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

// 格式化輔助函式
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

const getTypeBadgeClass = (type?: string): string => {
  switch (type) {
    case 'RULE_EXTRACTION':
      return 'type-extraction'
    case 'DATASHEET_ANALYSIS':
      return 'type-datasheet'
    default:
      return 'type-drc'
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

<style scoped>
.dashboard-container {
  padding: 1.5rem 2rem;
  max-width: 1500px;
  margin: 0 auto;
}

/* 頁頭 */
.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1.5rem;
  border-bottom: 1px solid #e2e8f0;
  padding-bottom: 1.25rem;
}

.page-title {
  font-size: 1.45rem;
  font-weight: 700;
  color: #0f172a;
  margin: 0 0 0.35rem 0;
  display: flex;
  align-items: center;
}

.page-subtitle {
  font-size: 0.875rem;
  color: #64748b;
  margin: 0;
}

.header-actions {
  display: flex;
  gap: 0.75rem;
}

/* 關鍵指標卡片網格 */
.stats-overview-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 1.25rem;
  margin-bottom: 1.75rem;
}

.stat-card {
  background-color: #ffffff;
  border-radius: 8px;
  padding: 1.25rem;
  display: flex;
  align-items: flex-start;
  gap: 1rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  border: 1px solid #e2e8f0;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.08);
}

.stat-icon-wrapper {
  width: 44px;
  height: 44px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.3rem;
  flex-shrink: 0;
}

.bg-green-light { background-color: #ecfdf5; }
.text-green { color: #059669; }

.bg-blue-light { background-color: #eff6ff; }
.text-blue { color: #2563eb; }

.bg-purple-light { background-color: #faf5ff; }
.text-purple { color: #7c3aed; }

.bg-cyan-light { background-color: #ecfeff; }
.text-cyan { color: #0891b2; }

.stat-body {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
}

.stat-label {
  font-size: 0.78rem;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  margin-bottom: 0.25rem;
}

.stat-value-row {
  display: flex;
  align-items: baseline;
  gap: 0.5rem;
  margin-bottom: 0.3rem;
}

.stat-value {
  font-size: 1.35rem;
  font-weight: 700;
  color: #0f172a;
}

.stat-subtext {
  font-size: 0.8rem;
  color: #64748b;
}

.stat-hint {
  font-size: 0.72rem;
  color: #94a3b8;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.badge-mini {
  font-size: 0.68rem;
  padding: 0.15rem 0.4rem;
  border-radius: 4px;
  font-weight: 600;
}

.status-online {
  background-color: #d1fae5;
  color: #065f46;
}

.status-active {
  background-color: #f3e8ff;
  color: #6b21a8;
}

/* 任務列表區塊 */
.tasks-table-section {
  background-color: #ffffff;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  overflow: hidden;
}

.section-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1.25rem;
  border-bottom: 1px solid #e2e8f0;
  background-color: #f8fafc;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.tabs-nav {
  display: flex;
  gap: 0.5rem;
}

.tab-btn {
  background: transparent;
  border: none;
  font-size: 0.85rem;
  font-weight: 500;
  color: #64748b;
  padding: 0.45rem 0.85rem;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  transition: all 0.15s ease;
}

.tab-btn:hover {
  color: #0f172a;
  background-color: #f1f5f9;
}

.tab-btn.active {
  color: #0284c7;
  background-color: #e0f2fe;
  font-weight: 600;
}

.tab-count {
  font-size: 0.72rem;
  background-color: rgba(0, 0, 0, 0.08);
  padding: 0.1rem 0.4rem;
  border-radius: 9999px;
  margin-left: 0.4rem;
}

.type-filter {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.filter-label {
  font-size: 0.8rem;
  color: #64748b;
}

.filter-select {
  font-size: 0.8rem;
  padding: 0.35rem 0.65rem;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  background-color: #ffffff;
  color: #334155;
  outline: none;
}

/* 表格樣式 */
.table-container {
  overflow-x: auto;
}

.compact-task-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
  font-size: 0.85rem;
}

.compact-task-table th {
  background-color: #f8fafc;
  color: #475569;
  font-weight: 600;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid #e2e8f0;
}

.compact-task-table td {
  padding: 0.85rem 1rem;
  border-bottom: 1px solid #f1f5f9;
  vertical-align: middle;
}

.task-row {
  cursor: pointer;
  transition: background-color 0.15s ease;
}

.task-row:hover {
  background-color: #f8fafc;
}

.project-name-cell {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.project-title {
  font-weight: 600;
  color: #0f172a;
}

.task-id-badge {
  font-size: 0.72rem;
  color: #64748b;
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
}

.copy-icon {
  font-size: 0.7rem;
  cursor: pointer;
  opacity: 0.7;
}

.copy-icon:hover {
  opacity: 1;
  color: #0284c7;
}

.badge-type {
  font-size: 0.72rem;
  font-weight: 600;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
}

.type-drc {
  background-color: #e0f2fe;
  color: #0369a1;
}

.type-extraction {
  background-color: #fef3c7;
  color: #b45309;
}

.type-datasheet {
  background-color: #f3e8ff;
  color: #7e22ce;
}

.summary-pills {
  display: flex;
  gap: 0.35rem;
  flex-wrap: wrap;
}

.pill {
  font-size: 0.72rem;
  background-color: #f1f5f9;
  color: #475569;
  padding: 0.15rem 0.45rem;
  border-radius: 4px;
  font-weight: 500;
}

.pill-cyan {
  background-color: #ecfeff;
  color: #0e7490;
}

.pill-indigo {
  background-color: #e0e7ff;
  color: #4338ca;
}

.time-cell {
  color: #64748b;
  font-size: 0.8rem;
}

.actions-cell {
  display: flex;
  gap: 0.25rem;
}

/* 載入與空狀態 */
.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem 2rem;
  color: #64748b;
}

.loading-icon,
.empty-icon {
  font-size: 2.2rem;
  margin-bottom: 0.75rem;
  color: #94a3b8;
}

.empty-text {
  font-size: 0.95rem;
  margin-bottom: 1rem;
}
</style>
