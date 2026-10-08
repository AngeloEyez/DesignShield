<template>
  <div class="task-monitor-view">
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
    <div class="workspace-grid">
      <!-- 左側 1/4 寬度：Execution Timeline -->
      <aside class="timeline-column">
        <TaskTimeline
          :steps="steps"
          :overall-status="taskStatus"
          :selected-step-name="activeDrawerStep || undefined"
          @select-step="handleTimelineStepSelect"
        />
      </aside>

      <!-- 右側 3/4 寬度：Live Log 面板與滑動覆蓋抽屜 -->
      <main class="log-and-drawer-column">
        <!-- 抽屜折疊時的快捷提示橫幅 -->
        <transition name="fade">
          <div
            v-if="isDrawerMinimized && activeDrawerStep === 'RULE_SELECTION'"
            class="minimized-drawer-banner"
          >
            <div class="banner-content">
              <i class="pi pi-check-circle text-emerald mr-2"></i>
              <span>
                輕量預先分析完成！已根據電路拓撲推薦
                <strong class="text-cyan font-mono">{{ recommendedRules.length }}</strong>
                條最佳規則。
              </span>
            </div>
            <button class="banner-action-btn" @click="isDrawerMinimized = false">
              <i class="pi pi-external-link mr-1"></i> 展開規則選取視窗
            </button>
          </div>
        </transition>

        <!-- 底層常駐：即時日誌 Live Log 面板 -->
        <div class="terminal-wrapper">
          <TaskLogTerminal :logs="logs" @clear="handleClearLogs" />
        </div>

        <!-- 覆蓋抽屜背景遮罩 (Overlay Backdrop) -->
        <div
          v-if="activeDrawerStep && !isDrawerMinimized"
          class="drawer-backdrop"
          @click="handleBackdropClick"
        ></div>

        <!-- 滑動覆蓋抽屜 (Step Detail / 規則選取 Overlay Drawer) -->
        <div
          v-if="activeDrawerStep"
          class="step-overlay-drawer"
          :class="{
            'is-rule-step': activeDrawerStep === 'RULE_SELECTION',
            'is-minimized': isDrawerMinimized
          }"
        >
          <!-- 抽屜頂部標題與關閉按鈕 -->
          <div class="drawer-header">
            <div class="drawer-header-title">
              <i class="pi pi-compass text-cyan mr-2"></i>
              <span>{{ getDrawerTitle(activeDrawerStep) }}</span>
            </div>

            <div class="drawer-header-actions">
              <!-- 折疊/展開日誌檢視切換按鈕 -->
              <button
                class="drawer-toggle-btn"
                :title="isDrawerMinimized ? '展開選取面板' : '折疊以檢視底層執行日誌'"
                @click="isDrawerMinimized = !isDrawerMinimized"
              >
                <i :class="isDrawerMinimized ? 'pi pi-window-maximize' : 'pi pi-window-minimize'"></i>
                <span class="toggle-text">{{ isDrawerMinimized ? '展開面板' : '檢視底層日誌' }}</span>
              </button>

              <!-- 若為規則選取且等待中，需點擊確認按鈕才可關閉，否則顯示關閉按鈕 -->
              <button
                v-if="!isMandatoryRuleSelection"
                class="drawer-close-btn"
                title="關閉視窗 (ESC)"
                @click="closeDrawer"
              >
                <i class="pi pi-times"></i>
              </button>
              <span v-else class="mandatory-badge">
                <i class="pi pi-lock mr-1"></i> 請確認選取規則以繼續
              </span>
            </div>
          </div>

          <!-- 抽屜內容主體 -->
          <div class="drawer-body">
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
            <div v-if="activeDrawerStep === 'RULE_SELECTION'" class="drawer-step-content rule-step-content">
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
    <section v-if="taskReport" class="report-dashboard-section">
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

// 抽屜覆蓋控制 (目前選中呈現之 Step 名稱與折疊狀態)
const activeDrawerStep = ref<string | null>(null)
const isDrawerMinimized = ref<boolean>(false)

// 6 大步驟清單
const steps = ref<StepItem[]>([
  { step_name: 'UNPACK_AND_VALIDATE', status: 'PENDING', log_message: '等待檔案上傳與預檢...' },
  { step_name: 'PARSE_AND_GRAPH', status: 'PENDING', log_message: '等待圖譜構建與線路解析...' },
  { step_name: 'RULE_SELECTION', status: 'PENDING', log_message: '等待推薦與選取規則...' },
  { step_name: 'HEURISTIC_CHECK', status: 'PENDING', log_message: '等待傳統規則演算法比對...' },
  { step_name: 'LLM_REASONING', status: 'PENDING', log_message: '等待本地大模型語意推理...' },
  { step_name: 'GENERATE_REPORT', status: 'PENDING', log_message: '等待產出完整 DRC 報告...' },
])

// 即時 Log
const logs = ref<LogEntry[]>([])
let activeEventSource: EventSource | null = null

// Step 2 篩選與分頁狀態 (供子元件雙向綁定與單元測試相容)
const activeStep2Tab = ref<'components' | 'nets'>('components')
const compSearch = ref('')
const compCategoryFilter = ref('')
const compSubCategoryFilter = ref('')
const compRoleFilter = ref('')
const compElectricalFilter = ref<'all' | 'electrical' | 'non_electrical'>('all')
const compPage = ref(1)
const compPageSize = ref(20)

const netSearch = ref('')
const netTypeFilter = ref<'all' | 'power' | 'ground' | 'bus' | 'signal'>('all')
const netBusFilter = ref('')
const netPage = ref(1)
const netPageSize = ref(20)

/**
 * 鍵盤 ESC 關閉/折疊抽屜監聽
 */
const handleKeyDown = (e: KeyboardEvent) => {
  if (e.key === 'Escape' && activeDrawerStep.value) {
    if (!isMandatoryRuleSelection.value) {
      closeDrawer()
    } else {
      isDrawerMinimized.value = !isDrawerMinimized.value
    }
  }
}

onMounted(async () => {
  window.addEventListener('keydown', handleKeyDown)
  await loadAllRules()

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
  async (newId) => {
    if (newId && typeof newId === 'string' && newId !== currentTaskId.value) {
      await loadExistingTask(newId)
    }
  }
)

/**
 * 載入現存任務詳情
 */
const loadExistingTask = async (taskId: string) => {
  try {
    const taskInfo = await fetchTaskStatus(taskId)
    currentTaskId.value = taskInfo.task_id
    activeProjectName.value = taskInfo.project_name
    taskStatus.value = taskInfo.status
    hasUploadedFile.value = true

    if (taskInfo.pre_analysis_summary) {
      preSummary.value = taskInfo.pre_analysis_summary
    }

    if (taskInfo.steps && taskInfo.steps.length > 0) {
      syncStepsFromBackend(taskInfo.steps)
    }

    // 載入該任務所有持久化日誌 (真實執行紀錄，不填補未發生之假日誌)
    try {
      const logResp = await fetchTaskLogs(taskId)
      if (logResp && logResp.logs) {
        logs.value = logResp.logs
      }
    } catch (err) {
      console.warn('載入任務日誌失敗:', err)
    }

    // 載入額外圖譜與檔案詳細數據
    try {
      graphDetails.value = await fetchTaskGraphDetails(taskId)
    } catch {}
    try {
      archiveDetails.value = await fetchTaskArchiveDetails(taskId)
    } catch {}

    // 若已完成，載入報告
    if (taskInfo.status === 'COMPLETED') {
      fetchTaskReport(taskId).then((rep) => (taskReport.value = rep)).catch(() => {})
    }

    // 若執行中或待確認或預先分析中，連線 SSE
    if (
      taskInfo.status === 'PROCESSING' ||
      taskInfo.status === 'READY_FOR_RUN' ||
      taskInfo.status === 'PRE_ANALYZING'
    ) {
      connectSSE(taskId)
    }

    if (taskInfo.recommended_rules && taskInfo.recommended_rules.length > 0) {
      recommendedRules.value = taskInfo.recommended_rules
    }

    // 若處於 READY_FOR_RUN，自動彈出規則選取抽屜
    if (taskInfo.status === 'READY_FOR_RUN') {
      activeDrawerStep.value = 'RULE_SELECTION'
      isDrawerMinimized.value = false
    }
  } catch (err) {
    console.warn('載入現存任務失敗:', err)
  }
}

/**
 * 載入所有全域 DRC 規則庫
 */
const loadAllRules = async () => {
  try {
    const list = await fetchRules()
    if (list && list.length > 0) {
      allRules.value = list
    }
  } catch (err) {
    console.warn('載入規則庫失敗:', err)
  }
}

/**
 * 同步後端步驟狀態至前端 6 步驟列表
 */
const syncStepsFromBackend = (backendSteps: StepItem[]) => {
  for (const bStep of backendSteps) {
    const target = steps.value.find((s) => s.step_name === bStep.step_name)
    if (target) {
      target.status = bStep.status
      target.log_message = bStep.log_message
      target.started_at = bStep.started_at
      target.completed_at = bStep.completed_at
    }
  }
}

/**
 * 是否為不可略過的規則選取抽屜 (當前任務處於 READY_FOR_RUN 且未開始執行正式比對)
 */
const isMandatoryRuleSelection = computed(() => {
  return activeDrawerStep.value === 'RULE_SELECTION' && taskStatus.value === 'READY_FOR_RUN'
})

/**
 * 點擊抽屜背景遮罩
 */
const handleBackdropClick = () => {
  if (!isMandatoryRuleSelection.value) {
    closeDrawer()
  }
}

const closeDrawer = () => {
  activeDrawerStep.value = null
  isDrawerMinimized.value = false
}

const handleTimelineStepSelect = (stepName: string) => {
  activeDrawerStep.value = stepName
  isDrawerMinimized.value = false
}

/**
 * 處理上傳檔案提交 (立即取得 Task ID 並啟動背景非同步分析，實時監控)
 */
const handleUploadSubmit = async (payload: { file: File; projectName: string }) => {
  isUploading.value = true
  activeProjectName.value = payload.projectName

  try {
    const res = await uploadSchematic(payload.file, payload.projectName)
    const nowIso = new Date().toISOString()
    currentTaskId.value = res.task_id
    hasUploadedFile.value = true
    taskStatus.value = res.status || 'PRE_ANALYZING'
    activeDrawerStep.value = null
    isDrawerMinimized.value = false

    // 更新 URL Query
    router.replace({ query: { taskId: res.task_id } })

    // 若伺服器已直接回傳 READY_FOR_RUN (例如命中快取或同步測試情境)
    if (res.status === 'READY_FOR_RUN') {
      preSummary.value = res.pre_analysis_summary || preSummary.value
      recommendedRules.value = res.recommended_rules || []
      activeDrawerStep.value = 'RULE_SELECTION'

      const s1 = steps.value.find((s) => s.step_name === 'UNPACK_AND_VALIDATE')
      if (s1) {
        s1.status = 'COMPLETED'
        s1.started_at = nowIso
        s1.completed_at = nowIso
        s1.log_message = `解壓縮通過，確認合法 Cadence OrCAD 檔案結構 (${payload.file.name})`
      }
      const s2 = steps.value.find((s) => s.step_name === 'PARSE_AND_GRAPH')
      if (s2) {
        s2.status = 'COMPLETED'
        s2.started_at = nowIso
        s2.completed_at = nowIso
        s2.log_message = `圖譜構建完成 (元件節點: ${res.pre_analysis_summary?.component_count || 0}, 網路節點: ${res.pre_analysis_summary?.net_count || 0})`
      }
      const s3 = steps.value.find((s) => s.step_name === 'RULE_SELECTION')
      if (s3) {
        s3.status = 'PROCESSING'
        s3.started_at = nowIso
        s3.log_message = `已根據圖譜推薦 ${res.recommended_rules?.length || 0} 條最佳規則，等待使用者確認選取...`
      }
    } else {
      activeDrawerStep.value = null

      // Step 1: 伺服器解壓與預檢中 (PROCESSING)
      const s1 = steps.value.find((s) => s.step_name === 'UNPACK_AND_VALIDATE')
      if (s1) {
        s1.status = 'PROCESSING'
        s1.started_at = nowIso
        s1.completed_at = undefined
        s1.log_message = `伺服器成功接收上傳檔案 (${payload.file.name})，正在進行解壓與預檢...`
      }

      // 初始化其餘步驟為 PENDING
      for (let i = 1; i < steps.value.length; i++) {
        steps.value[i].status = 'PENDING'
        steps.value[i].started_at = undefined
        steps.value[i].completed_at = undefined
      }
    }

    // 清空歷史日誌
    logs.value = []

    // 即時建立 SSE 連線開始串流即時日誌與步驟更新
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

    // Step 3 完成
    const s3 = steps.value.find((s) => s.step_name === 'RULE_SELECTION')
    if (s3) {
      s3.status = 'COMPLETED'
      s3.completed_at = new Date().toISOString()
      s3.log_message = `已確認選取 ${selectedRuleIds.length} 條規則，正式啟動 DBOS 工作流`
    }

    // 關閉抽屜，露出 Live Log
    activeDrawerStep.value = null
    isDrawerMinimized.value = false

    // 開始監聽 SSE
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

      // 監聽 Step 3 轉換為 PROCESSING (預先分析完畢，進入規則選取)
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

      // 當由 PRE_ANALYZING 轉為 READY_FOR_RUN，自動彈出規則選取抽屜，並載入細節
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

// 抽屜呈現輔助
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
</script>

<style scoped>
.task-monitor-view {
  padding: 1rem 1.5rem;
  max-width: 1600px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  background-color: var(--vscode-bg-base, #1e1e1e);
  color: var(--vscode-text-main, #cccccc);
}

/* 雙欄主工作區：1/4 Timeline, 3/4 Main Area */
.workspace-grid {
  display: grid;
  grid-template-columns: 1fr 3fr;
  gap: 1rem;
  min-height: 580px;
}

.timeline-column {
  min-width: 0;
}

.log-and-drawer-column {
  position: relative;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

/* 終端機面板包裝 */
.terminal-wrapper {
  background-color: var(--vscode-bg-base, #1e1e1e);
  border-radius: 6px;
  display: flex;
  flex-direction: column;
  height: 100%;
  border: 1px solid var(--vscode-border, #333333);
  overflow: hidden;
}

/* 滑動覆蓋抽屜 (Overlay Drawer) */
.drawer-backdrop {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(2px);
  z-index: 20;
  border-radius: 6px;
}

.step-overlay-drawer {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: var(--vscode-bg-panel, #252526);
  border-radius: 6px;
  border: 1px solid var(--vscode-border-light, #3c3c3c);
  box-shadow: -4px 0 24px rgba(0, 0, 0, 0.5);
  z-index: 30;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  animation: slideInRight 0.22s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes slideInRight {
  from {
    transform: translateX(30px);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

.drawer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.35rem 0.85rem;
  min-height: 32px;
  background-color: var(--vscode-bg-header, #2d2d2d);
  border-bottom: 1px solid var(--vscode-border, #333333);
}

.drawer-header-title {
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--vscode-text-heading, #ffffff);
  display: flex;
  align-items: center;
}

.drawer-header-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.drawer-toggle-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  background-color: rgba(56, 189, 248, 0.12);
  border: 1px solid rgba(56, 189, 248, 0.3);
  color: #38bdf8;
  font-size: 0.72rem;
  padding: 0.15rem 0.45rem;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.drawer-toggle-btn:hover {
  background-color: rgba(56, 189, 248, 0.25);
  color: #ffffff;
}

.drawer-close-btn {
  background: transparent;
  border: none;
  font-size: 0.85rem;
  color: var(--vscode-text-muted, #858585);
  cursor: pointer;
  padding: 0.15rem 0.35rem;
  line-height: 1;
  border-radius: 4px;
}

.drawer-close-btn:hover {
  color: #ffffff;
  background-color: #3c3c3c;
}

.mandatory-badge {
  font-size: 0.7rem;
  font-weight: 600;
  color: #38bdf8;
  background-color: rgba(56, 189, 248, 0.15);
  padding: 0.1rem 0.4rem;
  border-radius: 4px;
}

/* 抽屜折疊狀態 */
.step-overlay-drawer.is-minimized {
  bottom: auto;
  height: 34px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.6);
  border-bottom: 2px solid var(--vscode-accent, #38bdf8);
}

.step-overlay-drawer.is-minimized .drawer-body {
  display: none;
}

/* 折疊時提示橫幅 */
.minimized-drawer-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: linear-gradient(90deg, rgba(16, 185, 129, 0.15), rgba(56, 189, 248, 0.15));
  border: 1px solid rgba(56, 189, 248, 0.35);
  border-radius: 6px;
  padding: 0.45rem 0.85rem;
  margin-bottom: 0.5rem;
}

.banner-content {
  display: flex;
  align-items: center;
  font-size: 0.8rem;
  color: var(--vscode-text-main, #cccccc);
}

.banner-action-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  background-color: #0284c7;
  color: #ffffff;
  border: none;
  font-size: 0.75rem;
  font-weight: 500;
  padding: 0.25rem 0.6rem;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.15s ease;
}

.banner-action-btn:hover {
  background-color: #0369a1;
}

.drawer-body {
  flex: 1;
  padding: 0.75rem 0.85rem;
  overflow-y: auto;
  background-color: var(--vscode-bg-base, #1e1e1e);
}

.step-overlay-drawer.is-rule-step .drawer-body {
  padding: 0.4rem 0.6rem;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.step-overlay-drawer.is-rule-step .rule-step-content {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

/* 報告區域 */
.report-dashboard-section {
  background-color: var(--vscode-bg-panel, #252526);
  border-radius: 6px;
  border: 1px solid var(--vscode-border, #333333);
  padding: 1.25rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}
</style>
