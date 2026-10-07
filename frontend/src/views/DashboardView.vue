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
      <!-- 指標 1: 伺服器健康狀態 (含 FastAPI/DBOS, Database, LLM 燈號) -->
      <div class="stat-card health-stat-card">
        <div class="stat-icon-wrapper" :class="isHealthy ? 'bg-green-light' : 'bg-red-light'">
          <i class="pi pi-server" :class="isHealthy ? 'text-green' : 'text-danger'"></i>
        </div>
        <div class="stat-body">
          <div class="stat-header-row">
            <span class="stat-label">伺服器健康狀態</span>
            <span class="badge-mini" :class="isHealthy ? 'status-online' : 'status-danger'">
              <span class="pulse-indicator" :class="isHealthy ? 'pulse-green' : 'pulse-red'"></span>
              {{ isHealthy ? '健康運作' : '連線異常' }}
            </span>
          </div>

          <!-- 各元件燈號列表 (FASTAPI/DBOS, Database, LLM) -->
          <div class="health-lights-row">
            <div class="light-chip" :title="healthDetails.components?.api?.message || 'FastAPI / DBOS 引擎在線'">
              <span class="light-dot" :class="getLightDotClass(healthDetails.components?.api?.status)"></span>
              <span class="light-label">FastAPI/DBOS</span>
            </div>
            <div class="light-chip" :title="healthDetails.components?.database?.message || '資料庫連線正常'">
              <span class="light-dot" :class="getLightDotClass(healthDetails.components?.database?.status)"></span>
              <span class="light-label">Database</span>
            </div>
            <div class="light-chip" :title="healthDetails.components?.llm?.message || 'LLM 模型推理引擎'">
              <span class="light-dot" :class="getLightDotClass(healthDetails.components?.llm?.status)"></span>
              <span class="light-label">LLM</span>
            </div>
          </div>
          <span class="stat-hint">
            {{ healthDetails.components?.api?.message || '工作流引擎就緒' }} · {{ healthDetails.components?.database?.message || 'SQL正常' }} · {{ healthDetails.components?.llm?.label || 'LLM' }}: {{ healthDetails.components?.llm?.message || '就緒' }}
          </span>
        </div>
      </div>

      <!-- 指標 2: 儲存空間佔用 (含剩餘空間顯示與小型直條圖) -->
      <div class="stat-card storage-stat-card">
        <div class="stat-icon-wrapper bg-blue-light">
          <i class="pi pi-database text-blue"></i>
        </div>
        <div class="stat-body">
          <div class="stat-header-row">
            <span class="stat-label">儲存空間總佔用</span>
            <span class="badge-mini status-info" :title="storageBarTooltip">
              剩餘: {{ formattedDiskFree }}
            </span>
          </div>

          <div class="stat-value-row">
            <span class="stat-value">{{ storageStats.total_mb }} MB</span>
            <span class="stat-subtext">/ {{ storageStats.total_files }} 個檔案</span>
          </div>

          <!-- 小型圖形化直條圖 (直條進度圖) -->
          <div class="mini-bar-container" :title="storageBarTooltip">
            <div class="mini-bar-track">
              <!-- 已用空間直條 (以青藍色高亮呈現) -->
              <div
                class="mini-bar-fill bar-used"
                :style="{ width: diskUsedBarWidth + '%' }"
              ></div>
              <!-- 剩餘可用空間直條 (以深灰底色呈現剩餘) -->
              <div
                class="mini-bar-fill bar-free"
                :style="{ width: (100 - diskUsedBarWidth) + '%' }"
              ></div>
            </div>
            <div class="mini-bar-labels">
              <span class="bar-legend-item">
                <span class="legend-color legend-blue"></span>已用 {{ storageStats.disk_used_percent || 0 }}%
              </span>
              <span class="bar-legend-item">
                <span class="legend-color legend-green"></span>剩餘 {{ formattedDiskFree }}
              </span>
            </div>
          </div>

          <span class="stat-hint">
            上傳: {{ storageStats.uploads.file_count }} ({{ formatStorageMb(storageStats.uploads.total_bytes) }}) | 暫存: {{ storageStats.staging.file_count }} | 報告: {{ storageStats.reports.file_count }}
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
import type { StorageStats, ServerHealthDetails } from '@/types/settings'
import {
  fetchTasks,
  fetchStorageStats,
  checkServerHealth,
  fetchServerHealthDetails,
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

// 各伺服器元件健康度詳細資訊 (FastAPI/DBOS, Database, LLM 燈號)
const healthDetails = ref<ServerHealthDetails>({
  status: 'healthy',
  service: 'DesignShield',
  version: '0.1.0',
  components: {
    api: { status: 'healthy', label: 'FASTAPI / DBOS', message: '在線' },
    database: { status: 'healthy', label: 'Database', message: '正常' },
    llm: { status: 'healthy', label: 'LLM 推理', message: '已就緒' },
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

// 燈號顏色類別映射
const getLightDotClass = (status?: string): string => {
  switch (status) {
    case 'healthy':
      return 'dot-green'
    case 'warning':
    case 'degraded':
      return 'dot-amber'
    case 'error':
    case 'offline':
    case 'unhealthy':
      return 'dot-red'
    default:
      return 'dot-green'
  }
}

// 格式化主機剩餘可用磁碟空間
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

// 直條圖進度條已用百分比寬度
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

// 直條圖詳細提示資訊
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
    const [tasksRes, healthRes, storageRes, rulesRes, healthDetailsRes] = await Promise.allSettled([
      fetchTasks({ limit: 100 }),
      checkServerHealth(),
      fetchStorageStats(),
      fetchRules(),
      fetchServerHealthDetails ? fetchServerHealthDetails() : Promise.resolve(null),
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

    if (healthDetailsRes.status === 'fulfilled' && healthDetailsRes.value) {
      healthDetails.value = healthDetailsRes.value
      if (healthDetailsRes.value.status === 'unhealthy') {
        isHealthy.value = false
      }
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
  border-bottom: 1px solid var(--vscode-border, #333333);
  padding-bottom: 1.25rem;
}

.page-title {
  font-size: 1.45rem;
  font-weight: 700;
  color: var(--vscode-text-heading, #ffffff);
  margin: 0 0 0.35rem 0;
  display: flex;
  align-items: center;
}

.page-subtitle {
  font-size: 0.85rem;
  color: var(--vscode-text-muted, #858585);
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
  background-color: var(--vscode-bg-panel, #252526);
  border-radius: 6px;
  padding: 1.1rem;
  display: flex;
  align-items: flex-start;
  gap: 1rem;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.2);
  border: 1px solid var(--vscode-border, #333333);
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.stat-icon-wrapper {
  width: 42px;
  height: 42px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.25rem;
  flex-shrink: 0;
}

.bg-green-light { background-color: rgba(78, 201, 176, 0.15); }
.text-green { color: #4ec9b0; }

.bg-blue-light { background-color: rgba(0, 122, 204, 0.15); }
.text-blue { color: #38bdf8; }

.bg-purple-light { background-color: rgba(197, 134, 192, 0.15); }
.text-purple { color: #c586c0; }

.bg-cyan-light { background-color: rgba(78, 201, 176, 0.15); }
.text-cyan { color: #4ec9b0; }

.stat-body {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
}

.stat-label {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--vscode-text-muted, #858585);
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
  color: var(--vscode-text-heading, #ffffff);
}

.stat-subtext {
  font-size: 0.78rem;
  color: var(--vscode-text-muted, #858585);
}

.stat-hint {
  font-size: 0.72rem;
  color: var(--vscode-text-muted, #858585);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.badge-mini {
  font-size: 0.68rem;
  padding: 0.15rem 0.4rem;
  border-radius: 4px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
}

.status-online {
  background-color: rgba(78, 201, 176, 0.15);
  color: #4ec9b0;
}

.status-active {
  background-color: rgba(197, 134, 192, 0.15);
  color: #c586c0;
}

.status-danger {
  background-color: rgba(241, 76, 76, 0.15);
  color: #f14c4c;
}

.status-info {
  background-color: rgba(56, 189, 248, 0.15);
  color: #38bdf8;
}

/* 伺服器健康燈號與儲存直條圖樣式 */
.stat-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.3rem;
}

.pulse-indicator {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  display: inline-block;
  margin-right: 0.35rem;
}

.pulse-green {
  background-color: #4ec9b0;
  box-shadow: 0 0 6px #4ec9b0;
}

.pulse-red {
  background-color: #f14c4c;
  box-shadow: 0 0 6px #f14c4c;
}

.health-lights-row {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  margin: 0.2rem 0 0.35rem 0;
  flex-wrap: wrap;
}

.light-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  background-color: #1e1e1e;
  border: 1px solid #333333;
  padding: 0.12rem 0.4rem;
  border-radius: 12px;
  font-size: 0.7rem;
  color: #cccccc;
  cursor: default;
  transition: border-color 0.15s ease;
}

.light-chip:hover {
  border-color: #555555;
}

.light-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  display: inline-block;
}

.dot-green {
  background-color: #4ec9b0;
  box-shadow: 0 0 4px #4ec9b0;
}

.dot-amber {
  background-color: #e5c07b;
  box-shadow: 0 0 4px #e5c07b;
}

.dot-red {
  background-color: #f14c4c;
  box-shadow: 0 0 4px #f14c4c;
}

.light-label {
  font-weight: 500;
  font-size: 0.69rem;
}

/* 儲存空間直條圖 */
.mini-bar-container {
  margin: 0.2rem 0 0.35rem 0;
}

.mini-bar-track {
  height: 6px;
  background-color: #1e1e1e;
  border-radius: 3px;
  overflow: hidden;
  display: flex;
  border: 1px solid #333333;
}

.mini-bar-fill {
  height: 100%;
  transition: width 0.3s ease;
}

.bar-used {
  background: linear-gradient(90deg, #0284c7, #38bdf8);
}

.bar-free {
  background-color: #2a2d2e;
}

.mini-bar-labels {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 0.2rem;
  font-size: 0.68rem;
  color: var(--vscode-text-muted, #858585);
}

.bar-legend-item {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
}

.legend-color {
  width: 6px;
  height: 6px;
  border-radius: 2px;
  display: inline-block;
}

.legend-blue {
  background-color: #38bdf8;
}

.legend-green {
  background-color: #4ec9b0;
}

/* 任務列表區塊 */
.tasks-table-section {
  background-color: var(--vscode-bg-panel, #252526);
  border-radius: 6px;
  border: 1px solid var(--vscode-border, #333333);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.2);
  overflow: hidden;
}

.section-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.65rem 1rem;
  border-bottom: 1px solid var(--vscode-border, #333333);
  background-color: var(--vscode-bg-header, #2d2d2d);
  flex-wrap: wrap;
  gap: 0.75rem;
}

.tabs-nav {
  display: flex;
  gap: 0.4rem;
}

.tab-btn {
  background: transparent;
  border: none;
  font-size: 0.82rem;
  font-weight: 500;
  color: var(--vscode-text-secondary, #999999);
  padding: 0.4rem 0.75rem;
  border-radius: 4px;
  cursor: pointer;
  display: flex;
  align-items: center;
  transition: all 0.15s ease;
}

.tab-btn:hover {
  color: #ffffff;
  background-color: var(--vscode-bg-hover, #2a2d2e);
}

.tab-btn.active {
  color: #38bdf8;
  background-color: rgba(0, 122, 204, 0.2);
  font-weight: 600;
}

.tab-count {
  font-size: 0.7rem;
  background-color: rgba(255, 255, 255, 0.1);
  color: var(--vscode-text-main, #cccccc);
  padding: 0.08rem 0.35rem;
  border-radius: 9999px;
  margin-left: 0.4rem;
}

.type-filter {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.filter-label {
  font-size: 0.78rem;
  color: var(--vscode-text-muted, #858585);
}

.filter-select {
  font-size: 0.78rem;
  padding: 0.3rem 0.6rem;
  border: 1px solid var(--vscode-border, #333333);
  border-radius: 4px;
  background-color: var(--vscode-bg-input, #1e1e1e);
  color: var(--vscode-text-main, #cccccc);
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
  font-size: 0.82rem;
}

.compact-task-table th {
  background-color: var(--vscode-bg-header, #2d2d2d);
  color: var(--vscode-text-secondary, #999999);
  font-weight: 600;
  padding: 0.65rem 0.85rem;
  border-bottom: 1px solid var(--vscode-border, #333333);
}

.compact-task-table td {
  padding: 0.75rem 0.85rem;
  border-bottom: 1px solid var(--vscode-border, #333333);
  vertical-align: middle;
}

.task-row {
  cursor: pointer;
  transition: background-color 0.15s ease;
}

.task-row:hover {
  background-color: var(--vscode-bg-hover, #2a2d2e);
}

.project-name-cell {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.project-title {
  font-weight: 600;
  color: var(--vscode-text-heading, #ffffff);
}

.task-id-badge {
  font-size: 0.7rem;
  color: var(--vscode-text-muted, #858585);
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
  color: #38bdf8;
}

.badge-type {
  font-size: 0.7rem;
  font-weight: 600;
  padding: 0.15rem 0.45rem;
  border-radius: 4px;
}

.type-drc {
  background-color: rgba(0, 122, 204, 0.2);
  color: #38bdf8;
}

.type-extraction {
  background-color: rgba(245, 158, 11, 0.2);
  color: #f59e0b;
}

.type-datasheet {
  background-color: rgba(197, 134, 192, 0.2);
  color: #c586c0;
}

.summary-pills {
  display: flex;
  gap: 0.35rem;
  flex-wrap: wrap;
}

.pill {
  font-size: 0.7rem;
  background-color: var(--vscode-bg-header, #2d2d2d);
  color: var(--vscode-text-main, #cccccc);
  padding: 0.12rem 0.4rem;
  border-radius: 4px;
  font-weight: 500;
  border: 1px solid var(--vscode-border, #333333);
}

.pill-cyan {
  background-color: rgba(78, 201, 176, 0.15);
  color: #4ec9b0;
  border-color: rgba(78, 201, 176, 0.3);
}

.pill-indigo {
  background-color: rgba(0, 122, 204, 0.15);
  color: #38bdf8;
  border-color: rgba(0, 122, 204, 0.3);
}

.time-cell {
  color: var(--vscode-text-muted, #858585);
  font-size: 0.78rem;
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
  color: var(--vscode-text-muted, #858585);
}

.loading-icon,
.empty-icon {
  font-size: 2.2rem;
  margin-bottom: 0.75rem;
  color: var(--vscode-text-muted, #858585);
}

.empty-text {
  font-size: 0.9rem;
  margin-bottom: 1rem;
}
</style>
