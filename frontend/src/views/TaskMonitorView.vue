<template>
  <div class="task-monitor-view h-full flex flex-col p-2 md:p-2.5 gap-2 text-surface-200 overflow-hidden">
    <!-- 頂部任務控制與管理資訊列 (~32px 極簡高度) -->
    <TaskManagementBar
      :active-project-name="activeProjectName"
      :task-status="taskStatus"
      :current-task-id="currentTaskId"
      :is-deleting="isDeleting"
      :is-stopping="isStopping"
      @copy-task-id="copyTaskId"
      @delete-task="handleDeleteTask"
      @stop-task="handleStopCurrentTask"
      @reset-task="resetToNewTask"
      @reconnect-sse="reconnectSSE"
    />

    <!-- 單次上傳檔案區塊 (完成上傳後此區塊隱藏) -->
    <section v-if="!hasUploadedFile" class="upload-section-card upload-section-container shrink-0">
      <TaskUpload :is-uploading="isUploading" @upload="handleUploadSubmit" />
    </section>

    <!-- 中間主分析工作區：雙欄佈局 (Timeline + Detail 工作台)，自適應伸縮剩餘高度 (最大化時隱藏) -->
    <div
      v-show="consoleHeightMode !== 'maximized'"
      class="workspace-main-area workspace-grid flex-1 min-h-0 flex flex-col lg:flex-row gap-2 overflow-hidden"
    >
      <!-- 左側 Timeline 導航 (寬度 ~320px，高 100%) -->
      <aside class="timeline-column w-full lg:w-80 xl:w-88 flex flex-col h-full min-h-0 shrink-0">
        <TaskTimeline
          :steps="steps"
          :overall-status="taskStatus"
          :selected-step-name="activeDrawerStep || undefined"
          @select-step="handleTimelineStepSelect"
        />
      </aside>

      <!-- 右側 主步驟工作台 (flex-1 min-w-0，高 100%) -->
      <main class="main-workspace-column relative flex-1 min-w-0 flex flex-col h-full min-h-0 bg-surface-card rounded-md border border-surface-border overflow-hidden">
        <!-- 頂部工作區標頭列：顯示當前選中步驟標題與狀態 -->
        <div class="workspace-header flex justify-between items-center px-3 py-1.5 bg-surface-overlay border-b border-surface-border min-h-[32px] shrink-0">
          <div class="workspace-title text-xs font-semibold text-white flex items-center">
            <span>{{ getDrawerTitle(activeDrawerStep) }}</span>
            <span
              v-if="taskStatus === 'READY_FOR_RUN' && activeDrawerStep === 'RULE_SELECTION'"
              class="mandatory-badge ml-2 px-1.5 py-0.5 text-[10px] font-medium bg-amber-500/20 text-amber-300 border border-amber-500/40 rounded"
            >
              待確認規則
            </span>
          </div>

          <div class="workspace-header-actions flex items-center gap-2">
            <span class="text-[11px] text-surface-400 font-mono">
              Step {{ getStepIndex(activeDrawerStep) }} / 6
            </span>
            <button
              class="drawer-close-btn p-1 text-surface-400 hover:text-white rounded hover:bg-surface-hover/60 text-xs cursor-pointer border-0 bg-transparent flex items-center justify-center transition-colors"
              title="關閉步驟詳情面板"
              @click="closeDrawer"
            >
              <i class="pi pi-times"></i>
            </button>
          </div>
        </div>

        <!-- 主工作區本體 (無覆蓋層，獨立流暢滾動) -->
        <div
          v-if="activeDrawerStep"
          class="workspace-body step-overlay-drawer flex-1 min-h-0 bg-[var(--vscode-bg-base,#1e1e1e)] flex flex-col"
          :class="[
            activeDrawerStep === 'RULE_SELECTION' ? 'p-3 overflow-hidden is-rule-step' : 'p-3 overflow-y-auto',
          ]"
        >
          <!-- Step 1: 解壓縮與格式檢查詳細檔案 -->
          <Step1ArchiveDrawer
            v-if="activeDrawerStep === 'UNPACK_AND_VALIDATE'"
            :archive-details="archiveDetails"
            :archive-files-list="archiveFilesList"
          />

          <!-- Step 2: 解析線路與建構圖譜詳細統計 -->
          <Step2TopologyDrawer
            v-if="activeDrawerStep === 'PARSE_AND_GRAPH'"
            :graph-details="graphDetails"
            :pre-summary="preSummary"
            v-model:active-tab="activeStep2Tab"
            v-model:comp-search="compSearch"
            v-model:comp-category-filter="compCategoryFilter"
            v-model:comp-sub-category-filter="compSubCategoryFilter"
            v-model:comp-role-filter="compRoleFilter"
            v-model:comp-electrical-filter="compElectricalFilter"
            v-model:comp-page="compPage"
            v-model:comp-page-size="compPageSize"
            v-model:net-search="netSearch"
            v-model:net-type-filter="netTypeFilter"
            v-model:net-bus-filter="netBusFilter"
            v-model:net-page="netPage"
            v-model:net-page-size="netPageSize"
          />

          <!-- Step 3: 選擇規則 (規則庫樹狀選取窗口) -->
          <div v-if="activeDrawerStep === 'RULE_SELECTION'" class="drawer-step-content rule-step-content h-full">
            <RuleTreeSelector
              :summary="preSummary"
              :recommended-rules="recommendedRules"
              :is-submitting="isStartingRun"
              @run="handleStartRun"
            />
          </div>

          <!-- Step 4: 傳統演算法規則比對 -->
          <StepCheckStatusDrawer
            v-if="activeDrawerStep === 'HEURISTIC_CHECK'"
            step-name="HEURISTIC_CHECK"
            :step-item="steps.find((s) => s.step_name === 'HEURISTIC_CHECK')"
          />

          <!-- Step 5: LLM 語意邏輯推理 -->
          <StepCheckStatusDrawer
            v-if="activeDrawerStep === 'LLM_REASONING'"
            step-name="LLM_REASONING"
            :step-item="steps.find((s) => s.step_name === 'LLM_REASONING')"
          />

          <!-- Step 6: 報告彙整與落地 (完全融入主工作區) -->
          <div v-if="activeDrawerStep === 'GENERATE_REPORT'" class="step6-workspace-wrapper flex flex-col h-full">
            <!-- 任務已完成產出報告時直接在主工作區呈現完整 Report Dashboard -->
            <div v-if="taskReport" class="report-dashboard-section h-full flex flex-col">
              <TaskReportDashboard
                :task-id="currentTaskId"
                :summary="taskReport.summary"
                :violations="taskReport.violations"
              />
            </div>
            <!-- 未產生報告時呈現 Empty State -->
            <Step6ReportSummaryDrawer
              v-else
              :task-report="taskReport"
            />
          </div>
        </div>

        <!-- 尚未選擇步驟時的指引提示 -->
        <div
          v-else
          class="workspace-body-empty flex-1 min-h-0 bg-[var(--vscode-bg-base,#1e1e1e)] flex flex-col items-center justify-center text-surface-500 text-xs p-6"
        >
          <i class="pi pi-compass text-2xl mb-2 text-surface-600"></i>
          <span>請從左側點選步驟以檢視工作台詳情</span>
        </div>
      </main>
    </div>

    <!-- 最下方橫跨全寬 Log Console 面板 (緊貼視窗底部，三段式高度切換) -->
    <div
      class="bottom-console-dock border border-surface-border bg-[var(--vscode-bg-base,#1e1e1e)] rounded-md shrink-0 flex flex-col transition-all overflow-hidden"
      :class="[
        consoleHeightMode === 'collapsed' ? 'h-8' :
        consoleHeightMode === 'expanded' ? 'h-[200px]' : 'flex-1 min-h-0 h-full'
      ]"
    >
      <!-- 單一整合狀態工具列 (永遠可見，單擊切換 32/200px，雙擊切換 32/max) -->
      <div
        class="console-status-bar h-8 px-3 flex items-center justify-between text-xs cursor-pointer select-none hover:bg-surface-hover/50 text-surface-400"
        @click="handleStatusBarClick"
        @dblclick="handleStatusBarDblClick"
      >
        <!-- 左側與中央：終端圖示與最新日誌預覽 (含時間戳，單行模式展示) -->
        <div class="console-status-left flex-1 min-w-0 flex items-center gap-2 mr-3">
          <i class="pi pi-terminal text-sky-400 text-xs shrink-0" title="執行終端機"></i>

          <!-- 單行模式 (collapsed)：顯示最新一筆日誌 [時間戳] + 訊息 -->
          <template v-if="consoleHeightMode === 'collapsed'">
            <div v-if="latestLog" class="latest-log-preview truncate font-mono text-[11px] text-surface-400 flex items-center gap-1.5 min-w-0">
              <span class="log-dot w-1.5 h-1.5 rounded-full shrink-0" :class="getLogDotClass(latestLog.level)"></span>
              <span v-if="formatLogTime(latestLog)" class="log-timestamp text-surface-500 text-[10px] shrink-0 tabular-nums">
                [{{ formatLogTime(latestLog) }}]
              </span>
              <span class="log-message truncate text-surface-300">{{ latestLog.message }}</span>
            </div>
            <span v-else class="text-[11px] text-surface-500 italic">尚無日誌記錄</span>
          </template>
        </div>

        <!-- 右側：日誌計數標籤 (位於按鈕左側) + 按鈕群 (Debug/自動捲動/最大化/展開收合) -->
        <div class="console-status-right flex items-center gap-1.5 shrink-0" @click.stop @dblclick.stop>
          <!-- 日誌計數標籤 (放至右側按鈕的左邊) -->
          <span class="log-count-badge font-mono text-[10px] px-1.5 py-0.2 bg-surface-ground rounded border border-surface-border text-surface-400 mr-0.5">
            {{ displayedLogsCount }} 則日誌
            <template v-if="hiddenDebugCount > 0">
              (隱藏 {{ hiddenDebugCount }} 則 Debug)
            </template>
          </span>

          <!-- Debug 模式切換 (保留圖標，移除文字) -->
          <button
            type="button"
            class="debug-toggle-btn inline-flex items-center gap-1 px-1.5 py-0.5 text-xs rounded border transition-colors cursor-pointer"
            :class="showDebug ? 'bg-sky-500/15 border-sky-400/50 text-sky-300' : 'bg-[#1e1e1e] border-[#333333] text-surface-400 hover:text-white hover:border-[#555555]'"
            :title="`Debug 模式: ${showDebug ? '已開啟' : '已關閉'}`"
            @click="showDebug = !showDebug"
          >
            <i class="pi pi-code text-[11px]"></i>
            <span class="w-1.5 h-1.5 rounded-full inline-block transition-colors" :class="showDebug ? 'bg-sky-400' : 'bg-surface-600'"></span>
          </button>

          <!-- 自動捲動開關 (保留圖標，移除文字) -->
          <button
            type="button"
            class="autoscroll-toggle-btn inline-flex items-center px-1.5 py-0.5 text-xs rounded border transition-colors cursor-pointer"
            :class="autoScroll ? 'bg-sky-500/15 border-sky-400/50 text-sky-300' : 'bg-[#1e1e1e] border-[#333333] text-surface-400 hover:text-white hover:border-[#555555]'"
            :title="`自動捲動: ${autoScroll ? '已開啟' : '已關閉'}`"
            @click="autoScroll = !autoScroll"
          >
            <i class="pi pi-arrow-down text-[11px]"></i>
          </button>

          <!-- 最大化/還原按鈕 (全屏吃滿除標題列以下高度) -->
          <button
            class="console-maximize-btn bg-transparent border-0 text-surface-400 hover:text-white cursor-pointer p-1 text-xs"
            :title="consoleHeightMode === 'maximized' ? '還原為預設高度 (200px)' : '最大化日誌視窗 (全螢幕)'"
            @click="toggleMaximizeConsole"
          >
            <i :class="consoleHeightMode === 'maximized' ? 'pi pi-window-minimize' : 'pi pi-window-maximize'"></i>
          </button>

          <!-- 展開/收合切換箭頭 -->
          <button
            class="console-toggle-btn bg-transparent border-0 text-surface-400 hover:text-white cursor-pointer p-1 text-xs"
            :title="consoleHeightMode !== 'collapsed' ? '收合日誌面板 (32px)' : '展開日誌面板 (200px)'"
            @click="toggleConsole"
          >
            <i :class="consoleHeightMode !== 'collapsed' ? 'pi pi-chevron-down' : 'pi pi-chevron-up'"></i>
          </button>
        </div>
      </div>

      <!-- 展開日誌內容 (flex-1 min-h-0，無特殊底色與多餘內層邊框) -->
      <div v-show="consoleHeightMode !== 'collapsed'" class="console-body terminal-wrapper flex-1 min-h-0 p-1.5 bg-[var(--vscode-bg-base,#1e1e1e)] border-t border-surface-border/40 overflow-hidden">
        <TaskLogTerminal
          :logs="logs"
          :hide-toolbar="true"
          :show-debug="showDebug"
          :auto-scroll="autoScroll"
          @update:show-debug="showDebug = $event"
          @update:auto-scroll="autoScroll = $event"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * @file TaskMonitorView.vue
 * @description DesignShield DRC 檢測任務操作與即時監控視圖，整合 6 步驟時間軸、Live Log 與滑動覆蓋抽屜
 */

import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import TaskUpload from '@/components/TaskUpload.vue'
import RuleTreeSelector from '@/components/RuleTreeSelector.vue'
import TaskTimeline from '@/components/TaskTimeline.vue'
import TaskLogTerminal from '@/components/TaskLogTerminal.vue'
import TaskReportDashboard from '@/components/TaskReportDashboard.vue'
import TaskManagementBar from '@/components/taskmonitorview/TaskManagementBar.vue'
import Step1ArchiveDrawer from '@/components/taskmonitorview/Step1ArchiveDrawer.vue'
import Step2TopologyDrawer from '@/components/taskmonitorview/Step2TopologyDrawer.vue'
import StepCheckStatusDrawer from '@/components/taskmonitorview/StepCheckStatusDrawer.vue'
import Step6ReportSummaryDrawer from '@/components/taskmonitorview/Step6ReportSummaryDrawer.vue'
import type {
  StepItem,
  LogEntry,
  TaskSummary,
  RecommendedRuleItem,
  TaskGraphDetails,
  TaskArchiveDetails,
} from '@/types/task'
import {
  uploadSchematic,
  startTaskRun,
  subscribeTaskEvents,
  fetchTaskReport,
  fetchTaskStatus,
  fetchTaskLogs,
  stopTask,
  deleteTask,
  fetchTaskGraphDetails,
  fetchTaskArchiveDetails,
} from '@/services/api'

const route = useRoute()
const router = useRouter()

// 任務基本狀態
const currentTaskId = ref<string>('')
const activeProjectName = ref<string>('')
const taskStatus = ref<string>('PENDING')
const hasUploadedFile = ref<boolean>(false)
const isUploading = ref<boolean>(false)
const isStartingRun = ref<boolean>(false)
const isStopping = ref<boolean>(false)
const taskReport = ref<any>(null)

// 拓撲特徵與規則清單
const preSummary = ref<TaskSummary>({
  buses: [],
  platforms: [],
  component_count: 0,
  net_count: 0,
})
const recommendedRules = ref<RecommendedRuleItem[]>([])

// 詳細中繼與圖譜數據 (供 Step 1, 2 抽屜呈現)
const archiveDetails = ref<TaskArchiveDetails | null>(null)
const graphDetails = ref<TaskGraphDetails | null>(null)

// 抽屜內篩選與子頁籤狀態
const activeStep2Tab = ref<'components' | 'nets'>('components')
const compSearch = ref<string>('')
const compCategoryFilter = ref<string>('')
const compSubCategoryFilter = ref<string>('')
const compRoleFilter = ref<string>('')
const compElectricalFilter = ref<'all' | 'electrical' | 'non_electrical'>('all')
const compPage = ref<number>(1)
const compPageSize = ref<number>(20)
const netSearch = ref<string>('')
const netTypeFilter = ref<'all' | 'power' | 'ground' | 'bus' | 'signal'>('all')
const netBusFilter = ref<string>('')
const netPage = ref<number>(1)
const netPageSize = ref<number>(20)

// 主步驟工作台當前展示之步驟 (預設為 Step 1 UNPACK_AND_VALIDATE)
const activeDrawerStep = ref<string | null>('UNPACK_AND_VALIDATE')

// 步驟清單 (固定 6 大 DBOS 流程)
const steps = ref<StepItem[]>([
  { step_name: 'UNPACK_AND_VALIDATE', status: 'PENDING', log_message: '等待檔案上傳與預檢...' },
  { step_name: 'PARSE_AND_GRAPH', status: 'PENDING', log_message: '等待圖譜構建與線路解析...' },
  { step_name: 'RULE_SELECTION', status: 'PENDING', log_message: '等待推薦與選取規則...' },
  { step_name: 'HEURISTIC_CHECK', status: 'PENDING', log_message: '等待傳統規則演算法比對...' },
  { step_name: 'LLM_REASONING', status: 'PENDING', log_message: '等待本地大模型語意推理...' },
  { step_name: 'GENERATE_REPORT', status: 'PENDING', log_message: '等待產出完整 DRC 報告...' },
])

// 即時終端日誌與 Console 面板三段式高度模式 (收合 32px / 預設 200px / 最大化 400px)
const logs = ref<LogEntry[]>([])
type ConsoleHeightMode = 'collapsed' | 'expanded' | 'maximized'
const consoleHeightMode = ref<ConsoleHeightMode>('collapsed')

// 向後相容既有 isConsoleExpanded 屬性 (雙向計算)
const isConsoleExpanded = computed<boolean>({
  get: () => consoleHeightMode.value !== 'collapsed',
  set: (val: boolean) => {
    consoleHeightMode.value = val ? 'expanded' : 'collapsed'
  },
})

// 日誌過濾與捲動狀態 (由合併後的單一工具列控制)
const showDebug = ref<boolean>(false)
const autoScroll = ref<boolean>(true)

/**
 * 依 Debug 開關計算目前顯示之日誌筆數
 */
const displayedLogsCount = computed(() => {
  if (showDebug.value) return logs.value.length
  return logs.value.filter((l) => (l.level || '').toUpperCase() !== 'DEBUG').length
})

/**
 * 被隱藏之 Debug 日誌筆數
 */
const hiddenDebugCount = computed(() => {
  return logs.value.length - displayedLogsCount.value
})

let activeEventSource: { close: () => void } | null = null

let clickTimer: ReturnType<typeof setTimeout> | null = null

/**
 * 標題列單擊事件處理器：防抖判定單擊，切換 32px (collapsed) 與 200px (expanded)
 */
const handleStatusBarClick = () => {
  if (clickTimer) {
    clearTimeout(clickTimer)
    clickTimer = null
  }
  clickTimer = setTimeout(() => {
    if (consoleHeightMode.value === 'collapsed') {
      consoleHeightMode.value = 'expanded'
    } else {
      consoleHeightMode.value = 'collapsed'
    }
    clickTimer = null
  }, 220)
}

/**
 * 標題列雙擊事件處理器：立即取消單擊定時器，切換 32px (collapsed) 與全屏最大化 (maximized)
 */
const handleStatusBarDblClick = () => {
  if (clickTimer) {
    clearTimeout(clickTimer)
    clickTimer = null
  }
  if (consoleHeightMode.value === 'maximized') {
    consoleHeightMode.value = 'collapsed'
  } else {
    consoleHeightMode.value = 'maximized'
  }
}

/**
 * 格式化日誌時間戳記 (MM-DD HH:mm:ss 或 HH:mm:ss)
 * @param log 日誌項目物件
 * @returns 格式化時間字串
 */
const formatLogTime = (log?: LogEntry | null): string => {
  if (!log) return ''
  if (log.display_time) return log.display_time
  const raw = log.timestamp || ''
  if (!raw) return ''
  try {
    const d = new Date(raw)
    if (!isNaN(d.getTime())) {
      const m = String(d.getMonth() + 1).padStart(2, '0')
      const day = String(d.getDate()).padStart(2, '0')
      const h = String(d.getHours()).padStart(2, '0')
      const min = String(d.getMinutes()).padStart(2, '0')
      const s = String(d.getSeconds()).padStart(2, '0')
      return `${m}-${day} ${h}:${min}:${s}`
    }
  } catch {
    // 降級使用原始字串
  }
  return raw
}

/**
 * 切換底部 Console 展開與收合 (供展開按鈕直接調用)
 */
const toggleConsole = () => {
  if (consoleHeightMode.value === 'collapsed') {
    consoleHeightMode.value = 'expanded'
  } else {
    consoleHeightMode.value = 'collapsed'
  }
}

/**
 * 切換日誌視窗最大化與預設高度 (供最大化按鈕直接調用)
 */
const toggleMaximizeConsole = () => {
  if (consoleHeightMode.value === 'maximized') {
    consoleHeightMode.value = 'expanded'
  } else {
    consoleHeightMode.value = 'maximized'
  }
}

/**
 * 取得最新一筆日誌記錄
 */
const latestLog = computed(() => {
  return logs.value.length > 0 ? logs.value[logs.value.length - 1] : null
})

/**
 * 依日誌層級獲取對應圓點顏色 class
 */
const getLogDotClass = (level?: string): string => {
  switch (level?.toUpperCase()) {
    case 'ERROR':
      return 'bg-rose-500'
    case 'WARN':
    case 'WARNING':
      return 'bg-amber-500'
    case 'SUCCESS':
      return 'bg-emerald-500'
    default:
      return 'bg-sky-400'
  }
}

/**
 * 監聽時間軸步驟點擊，直接切換或開啟對應抽屜視窗
 */
const handleTimelineStepSelect = async (stepName: string) => {
  activeDrawerStep.value = stepName

  if (currentTaskId.value) {
    if (stepName === 'UNPACK_AND_VALIDATE' && !archiveDetails.value) {
      try {
        archiveDetails.value = await fetchTaskArchiveDetails(currentTaskId.value)
      } catch (err) {
        console.warn('載入解壓詳情失敗:', err)
      }
    } else if (stepName === 'PARSE_AND_GRAPH' && !graphDetails.value) {
      try {
        graphDetails.value = await fetchTaskGraphDetails(currentTaskId.value)
      } catch (err) {
        console.warn('載入圖譜拓撲詳情失敗:', err)
      }
    }
  }
}

/**
 * 關閉覆蓋抽屜 (使用者要看底層 Live Log 時直接點擊 X 或背景遮罩關閉)
 */
const closeDrawer = () => {
  activeDrawerStep.value = null
}

/**
 * 處理檔案上傳提交
 */
const handleUploadSubmit = async (payload: { file: File; projectName: string }) => {
  isUploading.value = true
  try {
    const res = await uploadSchematic(payload.file, payload.projectName)
    currentTaskId.value = res.task_id
    activeProjectName.value = res.project_name
    taskStatus.value = res.status
    hasUploadedFile.value = true

    router.replace({ query: { taskId: res.task_id } })

    if (res.pre_analysis_summary) {
      preSummary.value = res.pre_analysis_summary
    }
    if (res.recommended_rules) {
      recommendedRules.value = res.recommended_rules
    }

    if (res.status === 'READY_FOR_RUN') {
      const s1 = steps.value.find((s) => s.step_name === 'UNPACK_AND_VALIDATE')
      if (s1) s1.status = 'COMPLETED'
      const s2 = steps.value.find((s) => s.step_name === 'PARSE_AND_GRAPH')
      if (s2) s2.status = 'COMPLETED'
      const s3 = steps.value.find((s) => s.step_name === 'RULE_SELECTION')
      if (s3) s3.status = 'PROCESSING'

      activeDrawerStep.value = 'RULE_SELECTION'

      fetchTaskGraphDetails(res.task_id).then((g) => (graphDetails.value = g)).catch(() => {})
      fetchTaskArchiveDetails(res.task_id).then((a) => (archiveDetails.value = a)).catch(() => {})
    } else if (res.status === 'PRE_ANALYZING') {
      activeDrawerStep.value = null

      const s1 = steps.value.find((s) => s.step_name === 'UNPACK_AND_VALIDATE')
      if (s1) {
        s1.status = 'PROCESSING'
        s1.started_at = new Date().toISOString()
        s1.log_message = `伺服器成功接收上傳檔案 (${payload.file.name})，正在進行解壓與預檢...`
      }

      for (let i = 1; i < steps.value.length; i++) {
        steps.value[i].status = 'PENDING'
        steps.value[i].started_at = undefined
        steps.value[i].completed_at = undefined
      }
    }

    logs.value = []
    connectSSE(res.task_id)
  } catch (err: any) {
    console.error('上傳失敗:', err)
    const errDetail = err?.response?.data?.detail || err?.message || '請確認檔案格式是否正確。'
    alert(`上傳失敗: ${errDetail}`)
  } finally {
    isUploading.value = false
  }
}

/**
 * 確認規則並啟動正式 DRC 檢測 (Step 4 ~ Step 6)
 */
const handleStartRun = async (selectedRuleIds: string[]) => {
  if (!currentTaskId.value) return
  isStartingRun.value = true

  try {
    await startTaskRun(currentTaskId.value, selectedRuleIds)
    taskStatus.value = 'PROCESSING'

    const s3 = steps.value.find((s) => s.step_name === 'RULE_SELECTION')
    if (s3) {
      s3.status = 'COMPLETED'
      s3.completed_at = new Date().toISOString()
      s3.log_message = `已確認選取 ${selectedRuleIds.length} 條規則，正式啟動 DBOS 工作流`
    }

    const s4 = steps.value.find((s) => s.step_name === 'HEURISTIC_CHECK')
    if (s4) {
      s4.status = 'PROCESSING'
      s4.started_at = new Date().toISOString()
      s4.log_message = `正式啟動演算法規則比對 (選取 ${selectedRuleIds.length} 條規則)...`
    }

    activeDrawerStep.value = 'HEURISTIC_CHECK'
    connectSSE(currentTaskId.value)
  } catch (err) {
    console.error('啟動任務失敗:', err)
  } finally {
    isStartingRun.value = false
  }
}

/**
 * 建立 SSE 即時串流連線
 */
const connectSSE = (taskId: string) => {
  if (activeEventSource) {
    activeEventSource.close()
  }

  activeEventSource = subscribeTaskEvents(
    taskId,
    (updatedStep) => {
      const idx = steps.value.findIndex((s) => s.step_name === updatedStep.step_name)
      if (idx !== -1) {
        const effectiveStartedAt =
          updatedStep.started_at ||
          steps.value[idx].started_at ||
          (updatedStep.status === 'PROCESSING' ? new Date().toISOString() : undefined)

        steps.value[idx] = {
          ...steps.value[idx],
          status: updatedStep.status,
          log_message: updatedStep.log_message,
          started_at: effectiveStartedAt,
          completed_at:
            updatedStep.status === 'PROCESSING'
              ? undefined
              : updatedStep.completed_at || steps.value[idx].completed_at,
        }
      }

      if (updatedStep.status === 'PROCESSING') {
        activeDrawerStep.value = updatedStep.step_name
      }

      if (
        updatedStep.step_name === 'RULE_SELECTION' &&
        updatedStep.status === 'PROCESSING' &&
        taskStatus.value === 'PRE_ANALYZING'
      ) {
        taskStatus.value = 'READY_FOR_RUN'
        activeDrawerStep.value = 'RULE_SELECTION'
        isConsoleExpanded.value = false
        fetchTaskStatus(taskId)
          .then((info) => {
            if (info.pre_analysis_summary) preSummary.value = info.pre_analysis_summary
            if (info.recommended_rules) recommendedRules.value = info.recommended_rules
          })
          .catch(() => {})
        fetchTaskGraphDetails(taskId).then((g) => (graphDetails.value = g)).catch(() => {})
        fetchTaskArchiveDetails(taskId).then((a) => (archiveDetails.value = a)).catch(() => {})
      }
    },
    async (taskEndData) => {
      taskStatus.value = taskEndData.status || 'COMPLETED'
      if (taskStatus.value === 'COMPLETED') {
        activeDrawerStep.value = 'GENERATE_REPORT'
        isConsoleExpanded.value = false
        try {
          const report = await fetchTaskReport(taskId)
          taskReport.value = report
        } catch (e) {
          console.warn('載入報告失敗:', e)
        }
      }
    },
    (err) => {
      console.warn('SSE 連線異常:', err)
    },
    (newLog) => {
      const isDuplicate = logs.value.some((l) => l.id === newLog.id)
      if (!isDuplicate) {
        logs.value.push(newLog)
      }
    },
    async (statusData) => {
      const oldStatus = taskStatus.value
      taskStatus.value = statusData.status || taskStatus.value

      if (statusData.pre_analysis_summary) {
        preSummary.value = statusData.pre_analysis_summary
      }
      if (statusData.recommended_rules && statusData.recommended_rules.length > 0) {
        recommendedRules.value = statusData.recommended_rules
      }

      if (oldStatus === 'PRE_ANALYZING' && statusData.status === 'READY_FOR_RUN') {
        activeDrawerStep.value = 'RULE_SELECTION'
        isConsoleExpanded.value = false
        fetchTaskGraphDetails(taskId).then((g) => (graphDetails.value = g)).catch(() => {})
        fetchTaskArchiveDetails(taskId).then((a) => (archiveDetails.value = a)).catch(() => {})
      }
    }
  )
}

const reconnectSSE = () => {
  if (currentTaskId.value) {
    connectSSE(currentTaskId.value)
  }
}

const isDeleting = ref<boolean>(false)

const handleDeleteTask = async () => {
  if (!currentTaskId.value) return
  const confirmMsg = `確定要刪除當前任務「${activeProjectName.value || currentTaskId.value}」嗎？\n\n此操作將同步永久清理：\n• 伺服器磁碟上的原始上傳設計檔與解壓暫存目錄\n• 圖譜拓撲結構快取\n• 關聯的全部執行日誌與分析報告`
  if (!window.confirm(confirmMsg)) {
    return
  }

  isDeleting.value = true
  try {
    await deleteTask(currentTaskId.value)
    resetToNewTask()
  } catch (err: any) {
    console.error('刪除任務失敗:', err)
    const errDetail = err?.response?.data?.detail || err?.message || '未知錯誤'
    alert(`刪除任務失敗: ${errDetail}`)
  } finally {
    isDeleting.value = false
  }
}

const handleStopCurrentTask = async () => {
  if (!currentTaskId.value) return
  isStopping.value = true
  try {
    await stopTask(currentTaskId.value)
    taskStatus.value = 'CANCELLED'
    if (activeEventSource) activeEventSource.close()
  } catch (err) {
    console.error('停止任務失敗:', err)
  } finally {
    isStopping.value = false
  }
}

const resetToNewTask = () => {
  if (activeEventSource) activeEventSource.close()
  currentTaskId.value = ''
  activeProjectName.value = ''
  taskStatus.value = 'PENDING'
  hasUploadedFile.value = false
  taskReport.value = null
  activeDrawerStep.value = null
  logs.value = []
  steps.value = [
    { step_name: 'UNPACK_AND_VALIDATE', status: 'PENDING', log_message: '等待檔案上傳與預檢...' },
    { step_name: 'PARSE_AND_GRAPH', status: 'PENDING', log_message: '等待圖譜構建與線路解析...' },
    { step_name: 'RULE_SELECTION', status: 'PENDING', log_message: '等待推薦與選取規則...' },
    { step_name: 'HEURISTIC_CHECK', status: 'PENDING', log_message: '等待傳統規則演算法比對...' },
    { step_name: 'LLM_REASONING', status: 'PENDING', log_message: '等待本地大模型語意推理...' },
    { step_name: 'GENERATE_REPORT', status: 'PENDING', log_message: '等待產出完整 DRC 報告...' },
  ]
  router.replace({ query: {} })
}

const copyTaskId = async () => {
  if (currentTaskId.value) {
    await navigator.clipboard.writeText(currentTaskId.value)
  }
}

/**
 * 依步驟名稱取得對應標題
 * @param stepName 步驟名稱識別字
 * @returns 步驟完整繁體中文標題
 */
const getDrawerTitle = (stepName?: string | null): string => {
  switch (stepName) {
    case 'UNPACK_AND_VALIDATE':
      return '步驟 1: 解壓縮與檔案格式預檢詳情'
    case 'PARSE_AND_GRAPH':
      return '步驟 2: 線路圖譜拓撲與元件分析詳情'
    case 'RULE_SELECTION':
      return '步驟 3: DRC 檢驗規則推薦與選取'
    case 'HEURISTIC_CHECK':
      return '步驟 4: 傳統演算法規則比對'
    case 'LLM_REASONING':
      return '步驟 5: 本地大模型語意推理'
    case 'GENERATE_REPORT':
      return '步驟 6: DRC 報告彙整'
    default:
      return '步驟工作台'
  }
}

/**
 * 依步驟名稱取得步驟順序編號 (1 ~ 6)
 * @param stepName 步驟名稱識別字
 * @returns 1-based 步驟序號
 */
const getStepIndex = (stepName?: string | null): number => {
  switch (stepName) {
    case 'UNPACK_AND_VALIDATE':
      return 1
    case 'PARSE_AND_GRAPH':
      return 2
    case 'RULE_SELECTION':
      return 3
    case 'HEURISTIC_CHECK':
      return 4
    case 'LLM_REASONING':
      return 5
    case 'GENERATE_REPORT':
      return 6
    default:
      return 1
  }
}

const archiveFilesList = computed(() => {
  return archiveDetails.value?.files || []
})

const loadExistingTask = async (taskId: string) => {
  currentTaskId.value = taskId
  hasUploadedFile.value = true

  try {
    const statusData = await fetchTaskStatus(taskId)
    activeProjectName.value = statusData.project_name || taskId
    taskStatus.value = statusData.status || 'PROCESSING'
    if (statusData.steps && statusData.steps.length > 0) {
      steps.value = statusData.steps
    }
    if (statusData.pre_analysis_summary) {
      preSummary.value = statusData.pre_analysis_summary
    }
    if (statusData.recommended_rules) {
      recommendedRules.value = statusData.recommended_rules
    }

    if (!activeDrawerStep.value || activeDrawerStep.value === 'UNPACK_AND_VALIDATE') {
      if (taskStatus.value === 'READY_FOR_RUN') {
        activeDrawerStep.value = 'RULE_SELECTION'
        isConsoleExpanded.value = false
      } else if (taskStatus.value === 'COMPLETED') {
        activeDrawerStep.value = 'GENERATE_REPORT'
        isConsoleExpanded.value = false
      } else if (taskStatus.value === 'PROCESSING') {
        const runningStep = steps.value.find((s) => s.status === 'PROCESSING')
        activeDrawerStep.value = runningStep ? runningStep.step_name : 'HEURISTIC_CHECK'
      }
    }

    const logsData = await fetchTaskLogs(taskId)
    if (logsData.logs) {
      logs.value = logsData.logs
    }

    if (taskStatus.value === 'COMPLETED') {
      try {
        const report = await fetchTaskReport(taskId)
        taskReport.value = report
      } catch (e) {
        console.warn('載入既有任務報告失敗:', e)
      }
    }

    // 載入額外圖譜與檔案詳細數據
    await fetchTaskGraphDetails(taskId).then((res) => (graphDetails.value = res)).catch(() => {})
    await fetchTaskArchiveDetails(taskId).then((res) => (archiveDetails.value = res)).catch(() => {})

    if (['PROCESSING', 'READY_FOR_RUN', 'PRE_ANALYZING'].includes(taskStatus.value)) {
      connectSSE(taskId)
    }
  } catch (err) {
    console.error('載入既有任務失敗:', err)
  }
}

/**
 * 鍵盤快速鍵監聽 (ESC 鍵關閉抽屜視窗)
 */
const handleKeyDown = (event: KeyboardEvent) => {
  if (event.key === 'Escape' && activeDrawerStep.value) {
    closeDrawer()
  }
}

onMounted(async () => {
  window.addEventListener('keydown', handleKeyDown)
  const queryTaskId = route.query.taskId as string
  if (queryTaskId) {
    await loadExistingTask(queryTaskId)
  }
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyDown)
  if (activeEventSource) {
    activeEventSource.close()
  }
})

watch(
  () => route.query.taskId,
  (newId) => {
    if (newId && typeof newId === 'string' && newId !== currentTaskId.value) {
      loadExistingTask(newId)
    }
  }
)
</script>
