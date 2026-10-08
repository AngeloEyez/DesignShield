<template>
  <div class="task-monitor-view p-4 md:p-6 max-w-[1600px] mx-auto flex flex-col gap-4 text-surface-200">
    <!-- 頂部任務控制與管理資訊列 -->
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
    <section v-if="!hasUploadedFile" class="upload-section-card upload-section-container">
      <TaskUpload :is-uploading="isUploading" @upload="handleUploadSubmit" />
    </section>

    <!-- 主分析工作區：雙欄佈局 (左側 1/4 Timeline，右側 3/4 Live Log 與覆蓋抽屜) -->
    <div class="workspace-grid grid grid-cols-1 lg:grid-cols-4 gap-4 min-h-[580px]">
      <!-- 左側 1/4 寬度：Execution Timeline -->
      <aside class="timeline-column min-w-0 col-span-1">
        <TaskTimeline
          :steps="steps"
          :overall-status="taskStatus"
          :selected-step-name="activeDrawerStep || undefined"
          @select-step="handleTimelineStepSelect"
        />
      </aside>

      <!-- 右側 3/4 寬度：Live Log 面板與滑動覆蓋抽屜 -->
      <main class="log-and-drawer-column relative flex flex-col col-span-1 lg:col-span-3 min-w-0 min-h-[580px]">
        <!-- 抽屜折疊時的快捷提示橫幅 -->
        <transition name="fade">
          <div
            v-if="isDrawerMinimized && activeDrawerStep === 'RULE_SELECTION'"
            class="minimized-drawer-banner flex items-center justify-between p-2 px-3.5 mb-2 rounded-md bg-gradient-to-r from-emerald-500/15 to-sky-500/15 border border-sky-400/35 text-xs text-surface-200"
          >
            <div class="banner-content flex items-center gap-2">
              <i class="pi pi-check-circle text-emerald-400"></i>
              <span>
                輕量預先分析完成！已根據電路拓撲推薦
                <strong class="text-sky-400 font-mono">{{ recommendedRules.length }}</strong>
                條最佳規則。
              </span>
            </div>
            <button class="banner-action-btn inline-flex items-center gap-1 bg-sky-600 hover:bg-sky-700 text-white text-xs font-medium px-2.5 py-1 rounded cursor-pointer transition-colors border-0" @click="isDrawerMinimized = false">
              <i class="pi pi-external-link mr-1"></i> 展開規則選取視窗
            </button>
          </div>
        </transition>

        <!-- 底層常駐：即時日誌 Live Log 面板 -->
        <div class="terminal-wrapper flex-1 min-h-0 h-full">
          <TaskLogTerminal :logs="logs" @clear="handleClearLogs" />
        </div>

        <!-- 覆蓋抽屜背景遮罩 (Overlay Backdrop) -->
        <div
          v-if="activeDrawerStep && !isDrawerMinimized"
          class="drawer-backdrop absolute inset-0 bg-black/60 backdrop-blur-[2px] z-20 rounded-md"
          @click="handleBackdropClick"
        ></div>

        <!-- 滑動覆蓋抽屜 (Step Detail / 規則選取 Overlay Drawer) -->
        <div
          v-if="activeDrawerStep"
          class="step-overlay-drawer absolute inset-0 bg-surface-card rounded-md border border-surface-border shadow-2xl z-30 flex flex-col overflow-hidden"
          :class="{
            'is-rule-step': activeDrawerStep === 'RULE_SELECTION',
            'is-minimized hidden': isDrawerMinimized
          }"
        >
          <!-- 抽屜頂部標題與關閉按鈕 -->
          <div class="drawer-header flex justify-between items-center px-3.5 py-1.5 min-h-[32px] bg-surface-overlay border-b border-surface-border">
            <div class="drawer-header-title text-xs font-semibold text-surface-900 dark:text-surface-0 flex items-center">
              <i class="pi pi-compass text-sky-400 mr-2"></i>
              <span>{{ getDrawerTitle(activeDrawerStep) }}</span>
            </div>

            <div class="drawer-header-actions flex items-center gap-2">
              <!-- 折疊/展開日誌檢視切換按鈕 -->
              <button
                class="drawer-toggle-btn inline-flex items-center gap-1.5 bg-sky-500/10 border border-sky-500/30 text-sky-400 hover:bg-sky-500/20 text-xs px-2 py-0.5 rounded cursor-pointer transition-colors"
                :title="isDrawerMinimized ? '展開選取面板' : '折疊以檢視底層執行日誌'"
                @click="isDrawerMinimized = !isDrawerMinimized"
              >
                <i :class="isDrawerMinimized ? 'pi pi-window-maximize' : 'pi pi-window-minimize'"></i>
                <span class="toggle-text">{{ isDrawerMinimized ? '展開面板' : '檢視底層日誌' }}</span>
              </button>

              <!-- 若為規則選取且等待中，需點擊確認按鈕才可關閉，否則顯示關閉按鈕 -->
              <button
                v-if="!isMandatoryRuleSelection"
                class="drawer-close-btn bg-transparent border-0 text-surface-400 hover:text-surface-100 cursor-pointer p-1 text-xs leading-none rounded"
                title="關閉視窗 (ESC)"
                @click="closeDrawer"
              >
                <i class="pi pi-times"></i>
              </button>
              <span v-else class="mandatory-badge text-[11px] font-semibold text-amber-300 bg-amber-500/15 border border-amber-500/30 px-2 py-0.5 rounded flex items-center">
                <i class="pi pi-lock mr-1"></i> 請確認選取規則以繼續
              </span>
            </div>
          </div>

          <!-- 抽屜內容主體 -->
          <div class="drawer-body flex-1 p-3.5 overflow-y-auto bg-surface-ground">
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
                :all-rules="allRules"
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

            <!-- Step 6: 報告彙整與落地 -->
            <Step6ReportSummaryDrawer
              v-if="activeDrawerStep === 'GENERATE_REPORT'"
              :task-report="taskReport"
            />
          </div>
        </div>
      </main>
    </div>

    <!-- 步驟完成後的 DRC 報告 Dashboard -->
    <section v-if="taskReport" class="report-dashboard-section bg-surface-card rounded-md border border-surface-border p-5 shadow-sm">
      <TaskReportDashboard
        :task-id="currentTaskId"
        :summary="taskReport.summary"
        :violations="taskReport.violations"
      />
    </section>
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
import type { DrcRuleItem } from '@/types/rule'
import {
  uploadSchematic,
  startTaskRun,
  subscribeTaskEvents,
  fetchTaskReport,
  fetchRules,
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
const allRules = ref<DrcRuleItem[]>([])

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

// 抽屜顯示控制 (點擊步驟時間軸或上傳完成自動觸發)
const activeDrawerStep = ref<string | null>(null)
// 抽屜折疊/最小化狀態 (供使用者在規則推薦等待時折疊檢視底層 Live Log)
const isDrawerMinimized = ref<boolean>(false)

// 是否處於強制規則選取狀態 (當 READY_FOR_RUN 且抽屜為 RULE_SELECTION 時，關閉抽屜需透過折疊或確認)
const isMandatoryRuleSelection = computed(() => {
  return taskStatus.value === 'READY_FOR_RUN' && activeDrawerStep.value === 'RULE_SELECTION'
})

// 步驟清單 (固定 6 大 DBOS 流程)
const steps = ref<StepItem[]>([
  { step_name: 'UNPACK_AND_VALIDATE', status: 'PENDING', log_message: '等待檔案上傳與預檢...' },
  { step_name: 'PARSE_AND_GRAPH', status: 'PENDING', log_message: '等待圖譜構建與線路解析...' },
  { step_name: 'RULE_SELECTION', status: 'PENDING', log_message: '等待推薦與選取規則...' },
  { step_name: 'HEURISTIC_CHECK', status: 'PENDING', log_message: '等待傳統規則演算法比對...' },
  { step_name: 'LLM_REASONING', status: 'PENDING', log_message: '等待本地大模型語意推理...' },
  { step_name: 'GENERATE_REPORT', status: 'PENDING', log_message: '等待產出完整 DRC 報告...' },
])

// 即時終端日誌
const logs = ref<LogEntry[]>([])
let activeEventSource: { close: () => void } | null = null

/**
 * 監聽時間軸步驟點擊，開啟對應抽屜視窗
 */
const handleTimelineStepSelect = async (stepName: string) => {
  activeDrawerStep.value = stepName
  isDrawerMinimized.value = false

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
 * 關閉覆蓋抽屜
 */
const closeDrawer = () => {
  activeDrawerStep.value = null
  isDrawerMinimized.value = false
}

/**
 * 點擊背景遮罩關閉 (若非強制選取狀態)
 */
const handleBackdropClick = () => {
  if (!isMandatoryRuleSelection.value) {
    closeDrawer()
  } else {
    // 若為強制選取，點擊遮罩改為自動折疊抽屜，讓使用者看 Live Log
    isDrawerMinimized.value = true
  }
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
      isDrawerMinimized.value = false

      fetchTaskGraphDetails(res.task_id).then((g) => (graphDetails.value = g)).catch(() => {})
      fetchTaskArchiveDetails(res.task_id).then((a) => (archiveDetails.value = a)).catch(() => {})
    } else if (res.status === 'PRE_ANALYZING') {
      activeDrawerStep.value = null
      isDrawerMinimized.value = false

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

    activeDrawerStep.value = null
    isDrawerMinimized.value = false
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
        steps.value[idx] = {
          ...steps.value[idx],
          status: updatedStep.status,
          log_message: updatedStep.log_message,
          started_at: updatedStep.started_at || steps.value[idx].started_at,
          completed_at: updatedStep.completed_at || steps.value[idx].completed_at,
        }
      }

      if (
        updatedStep.step_name === 'RULE_SELECTION' &&
        updatedStep.status === 'PROCESSING' &&
        taskStatus.value === 'PRE_ANALYZING'
      ) {
        taskStatus.value = 'READY_FOR_RUN'
        activeDrawerStep.value = 'RULE_SELECTION'
        isDrawerMinimized.value = false
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
        isDrawerMinimized.value = false
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
  isDrawerMinimized.value = false
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

const handleClearLogs = () => {
  logs.value = []
}

const copyTaskId = async () => {
  if (currentTaskId.value) {
    await navigator.clipboard.writeText(currentTaskId.value)
  }
}

const getDrawerTitle = (stepName: string): string => {
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
      return '步驟詳情'
  }
}

const archiveFilesList = computed(() => {
  return (
    archiveDetails.value?.files || [
      {
        filename: 'circuit_schematic.xml',
        relative_path: 'circuit_schematic.xml',
        size_bytes: 1048576,
        is_xml: true,
        is_netlist: false,
      },
      {
        filename: 'allegro_netlist.dat',
        relative_path: 'allegro_netlist.dat',
        size_bytes: 524288,
        is_xml: false,
        is_netlist: true,
      },
    ]
  )
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

    if (taskStatus.value === 'READY_FOR_RUN') {
      activeDrawerStep.value = 'RULE_SELECTION'
      isDrawerMinimized.value = false
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

onMounted(async () => {
  try {
    const rules = await fetchRules()
    allRules.value = rules
  } catch (err) {
    console.warn('載入規則清單失敗:', err)
  }

  const queryTaskId = route.query.taskId as string
  if (queryTaskId) {
    await loadExistingTask(queryTaskId)
  }
})

onUnmounted(() => {
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
