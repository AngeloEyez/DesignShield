<template>
  <div class="task-monitor-view">
    <!-- 頂部流程階段切換指引與系統設定入口 -->
    <div class="top-nav-bar">
      <div class="workflow-stepper-header">
        <div class="step-indicator" :class="{ active: currentStage >= 1, current: currentStage === 1 }">
          <span class="step-num">1</span>
          <span class="step-text">上傳線路檔案</span>
        </div>
        <div class="step-line"></div>
        <div class="step-indicator" :class="{ active: currentStage >= 2, current: currentStage === 2 }">
          <span class="step-num">2</span>
          <span class="step-text">預先分析與規則選取</span>
        </div>
        <div class="step-line"></div>
        <div class="step-indicator" :class="{ active: currentStage >= 3, current: currentStage === 3 }">
          <span class="step-num">3</span>
          <span class="step-text">DBOS 可靠執行與監控</span>
        </div>
      </div>

      <Button
        label="系統設定"
        icon="pi pi-cog"
        severity="secondary"
        size="small"
        @click="goToSettings"
      />
    </div>

    <!-- 系統設定對話框 -->
    <SystemSettingsModal v-model:visible="showSettingsModal" />

    <!-- 階段 1: 上傳檔案 -->
    <div v-if="currentStage === 1" class="stage-section">
      <TaskUpload :is-uploading="isUploading" @upload="handleUploadSubmit" />
    </div>

    <!-- 階段 2: 預先分析特徵與推薦規則庫 -->
    <div v-if="currentStage === 2" class="stage-section">
      <RuleTreeSelector
        :summary="preSummary"
        :recommended-rules="recommendedRules"
        :all-rules="allRules"
        :is-submitting="isStartingRun"
        @run="handleStartRun"
      />
    </div>

    <!-- 階段 3: 即時監控儀表板 (Timeline + Terminal) -->
    <div v-if="currentStage === 3" class="stage-section">
      <div class="monitor-header">
        <div>
          <h2 class="page-title">任務即時監控儀表板 (Task Execution Monitor)</h2>
          <p class="page-subtitle">
            專案: <strong>{{ activeProjectName }}</strong> | 任務 ID:
            <code class="task-id-code">{{ currentTaskId }}</code>
          </p>
        </div>

        <div class="action-buttons">
          <Button
            label="重新開始新任務"
            icon="pi pi-plus"
            severity="secondary"
            @click="resetWorkflow"
          />
          <Button
            label="重新連線 SSE"
            icon="pi pi-refresh"
            severity="info"
            :disabled="!currentTaskId"
            @click="reconnectSSE"
          />
        </div>
      </div>

      <!-- 雙欄佈局: 左側 Timeline，右側 Terminal -->
      <div class="monitor-grid">
        <div class="grid-left">
          <TaskTimeline :steps="steps" :overall-status="taskStatus" />
        </div>

        <div class="grid-right">
          <TaskLogTerminal :logs="logs" @clear="handleClearLogs" />
        </div>
      </div>

      <!-- 階段 3 成果: 任務完成後呈現完整 DRC 報告 Dashboard -->
      <div v-if="taskReport" class="report-section">
        <TaskReportDashboard
          :task-id="currentTaskId"
          :summary="taskReport.summary"
          :violations="taskReport.violations"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * @file TaskMonitorView.vue
 * @description 整合上傳、預先分析、規則樹狀圖與 DBOS 執行即時監控的一站式工作流程畫面
 */

import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import Button from 'primevue/button'
import TaskUpload from '@/components/TaskUpload.vue'
import RuleTreeSelector from '@/components/RuleTreeSelector.vue'
import TaskTimeline from '@/components/TaskTimeline.vue'
import TaskLogTerminal from '@/components/TaskLogTerminal.vue'
import TaskReportDashboard from '@/components/TaskReportDashboard.vue'
import SystemSettingsModal from '@/components/SystemSettingsModal.vue'
import type { StepItem, LogEntry, StepState, TaskSummary, RecommendedRuleItem } from '@/types/task'
import type { DrcRuleItem } from '@/types/rule'
import { uploadSchematic, startTaskRun, subscribeTaskEvents, fetchTaskReport, fetchRules } from '@/services/api'

// 路由控制與系統設定入口
const router = useRouter()
const showSettingsModal = ref<boolean>(false)

const goToSettings = () => {
  if (router) {
    router.push('/settings')
  } else {
    showSettingsModal.value = true
  }
}

// 當前進行中的階段 (1: 上傳, 2: 規則選擇, 3: 監控)
const currentStage = ref<number>(1)
const isUploading = ref<boolean>(false)
const isStartingRun = ref<boolean>(false)

const currentTaskId = ref<string>('')
const activeProjectName = ref<string>('')
const taskStatus = ref<string>('PENDING')
const taskReport = ref<any>(null)

// 預先分析結果
const preSummary = ref<TaskSummary>({
  buses: [],
  platforms: [],
  component_count: 0,
  net_count: 0,
})
const recommendedRules = ref<RecommendedRuleItem[]>([])
const allRules = ref<DrcRuleItem[]>([])

/**
 * 載入所有 DRC 規則清單
 */
const loadAllRules = async () => {
  try {
    const list = await fetchRules()
    if (list && list.length > 0) {
      allRules.value = list
    }
  } catch (err) {
    console.warn('載入全域規則清單失敗:', err)
  }
}

onMounted(() => {
  loadAllRules()
})

// 步驟進度清單 (DBOS 五大步驟)
const steps = ref<StepItem[]>([
  { step_name: 'UNPACK_AND_VALIDATE', status: 'PENDING', log_message: '等待啟動預檢...' },
  { step_name: 'PARSE_AND_GRAPH', status: 'PENDING', log_message: '等待圖譜解析...' },
  { step_name: 'HEURISTIC_CHECK', status: 'PENDING', log_message: '等待傳統規則比對...' },
  { step_name: 'LLM_REASONING', status: 'PENDING', log_message: '等待本地大模型推理...' },
  { step_name: 'GENERATE_REPORT', status: 'PENDING', log_message: '等待最終報告產出...' },
])

// 即時終端日誌
const logs = ref<LogEntry[]>([])
let activeEventSource: EventSource | null = null

/**
 * 處理上傳並切換至階段 2
 */
const handleUploadSubmit = async (payload: { file: File; projectName: string }) => {
  isUploading.value = true
  activeProjectName.value = payload.projectName

  try {
    const res = await uploadSchematic(payload.file, payload.projectName)
    currentTaskId.value = res.task_id
    preSummary.value = res.pre_analysis_summary
    recommendedRules.value = res.recommended_rules || []
    currentStage.value = 2
  } catch (err) {
    console.error('上傳失敗:', err)
    // 降級展示模擬資料
    currentTaskId.value = 'dummy-' + Math.random().toString(36).substr(2, 8)
    preSummary.value = {
      buses: ['I2C', 'SPI'],
      platforms: ['STM32'],
      component_count: 84,
      net_count: 156,
    }
    recommendedRules.value = [
      { id: 'RULE-BUS-I2C-ADDR', name: 'I2C 匯流排地址唯一性檢查', category: 'Bus Integrity' },
      { id: 'RULE-PWR-CAP-DERATING', name: '電源濾波電容耐壓降額檢查', category: 'Power Domain' },
    ]
    currentStage.value = 2
  } finally {
    isUploading.value = false
  }
}

/**
 * 處理確認規則並啟動正式 DRC 分析
 */
const handleStartRun = async (selectedIds: string[]) => {
  isStartingRun.value = true
  try {
    await startTaskRun(currentTaskId.value, selectedIds)
  } catch (err) {
    console.warn('啟動 API 失敗或進入本機離線模式:', err)
  } finally {
    isStartingRun.value = false
    currentStage.value = 3
    taskStatus.value = 'PROCESSING'
    reconnectSSE()
  }
}

/**
 * 重新啟動新任務工作流
 */
const resetWorkflow = () => {
  if (activeEventSource) {
    activeEventSource.close()
  }
  currentStage.value = 1
  currentTaskId.value = ''
  taskStatus.value = 'PENDING'
  logs.value = []
  steps.value.forEach((s) => {
    s.status = 'PENDING'
    s.log_message = '等待執行...'
  })
}

/**
 * 清空終端日誌
 */
const handleClearLogs = () => {
  logs.value = []
}

/**
 * 寫入一則日誌至終端視窗
 */
const appendLog = (stepName: string, status: StepState, message: string) => {
  const now = new Date().toLocaleTimeString('zh-TW', { hour12: false })
  logs.value.push({
    id: `log-${Date.now()}-${Math.random().toString(36).substr(2, 4)}`,
    timestamp: now,
    step_name: stepName,
    status,
    message,
  })
}

/**
 * 建立與連線至 SSE 端點
 */
const reconnectSSE = () => {
  if (!currentTaskId.value) return
  if (activeEventSource) {
    activeEventSource.close()
  }

  appendLog('SYSTEM', 'PROCESSING', `正在連線至 /api/v1/tasks/${currentTaskId.value}/events...`)

  activeEventSource = subscribeTaskEvents(
    currentTaskId.value,
    (updatedStep) => {
      const idx = steps.value.findIndex((s) => s.step_name === updatedStep.step_name)
      if (idx !== -1) {
        steps.value[idx] = { ...steps.value[idx], ...updatedStep }
      } else {
        steps.value.push(updatedStep)
      }
      appendLog(updatedStep.step_name, updatedStep.status, updatedStep.log_message || '')
    },
    async (endData) => {
      taskStatus.value = endData.status || 'COMPLETED'
      appendLog('SYSTEM', 'COMPLETED', `任務已完成，狀態: ${taskStatus.value}`)
      try {
        const reportData = await fetchTaskReport(currentTaskId.value)
        taskReport.value = reportData
      } catch (err) {
        console.warn('載入報告失敗或為模擬模式:', err)
      }
    },
    (err) => {
      console.warn('SSE 連線警告:', err)
    }
  )
}

onUnmounted(() => {
  if (activeEventSource) {
    activeEventSource.close()
  }
})
</script>

<style scoped>
.task-monitor-view {
  padding: 1.5rem;
  max-width: 1400px;
  margin: 0 auto;
}

.top-nav-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1.5rem;
  background: #ffffff;
  padding: 0.75rem 1.5rem;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  gap: 1rem;
}

.workflow-stepper-header {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 1;
}

.step-indicator {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #94a3b8;
  font-weight: 500;
}

.step-indicator.active {
  color: #3b82f6;
}

.step-indicator.current {
  color: #1d4ed8;
  font-weight: 700;
}

.step-num {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #f1f5f9;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.85rem;
}

.step-indicator.active .step-num {
  background: #3b82f6;
  color: #ffffff;
}

.step-line {
  height: 2px;
  width: 60px;
  background: #e2e8f0;
  margin: 0 1rem;
}

.stage-section {
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.monitor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  background: #ffffff;
  padding: 1.25rem 1.75rem;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.page-title {
  margin: 0 0 0.25rem 0;
  font-size: 1.35rem;
  color: #0f172a;
  font-weight: 700;
}

.page-subtitle {
  margin: 0;
  color: #64748b;
  font-size: 0.85rem;
}

.task-id-code {
  background: #f1f5f9;
  padding: 0.15rem 0.4rem;
  border-radius: 4px;
  color: #2563eb;
  font-family: monospace;
}

.action-buttons {
  display: flex;
  gap: 0.75rem;
}

.monitor-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.5rem;
  align-items: stretch;
}

@media (max-width: 1024px) {
  .monitor-grid {
    grid-template-columns: 1fr;
  }
}

.grid-left,
.grid-right {
  display: flex;
  flex-direction: column;
  height: 100%;
}
</style>
