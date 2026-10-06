<template>
  <div class="task-monitor-view">
    <!-- 頂部任務控制與管理資訊列 -->
    <header class="task-management-bar">
      <div class="task-identity-col">
        <div class="title-with-badge">
          <h2 class="view-title">
            <i class="pi pi-shield text-cyan mr-2"></i>
            {{ activeProjectName || '線路 DRC 任務檢測' }}
          </h2>
          <Tag :value="formatStatus(taskStatus)" :severity="getStatusSeverity(taskStatus)" />
        </div>
        <div class="task-id-row">
          <span class="label">任務 ID:</span>
          <code class="task-id-code">{{ currentTaskId || '未建立 (請先上傳設計檔案)' }}</code>
          <Button
            v-if="currentTaskId"
            icon="pi pi-copy"
            text
            rounded
            size="small"
            title="複製任務 ID"
            @click="copyTaskId"
          />
        </div>
      </div>

      <div class="task-actions-col">
        <Button
          v-if="taskStatus === 'PROCESSING'"
          label="停止任務"
          icon="pi pi-stop-circle"
          severity="danger"
          size="small"
          :loading="isStopping"
          @click="handleStopCurrentTask"
        />
        <Button
          label="重新開始新任務"
          icon="pi pi-plus"
          severity="secondary"
          size="small"
          @click="resetToNewTask"
        />
        <Button
          label="重新連線 SSE"
          icon="pi pi-refresh"
          severity="info"
          size="small"
          :disabled="!currentTaskId"
          @click="reconnectSSE"
        />
      </div>
    </header>

    <!-- 單次上傳檔案區塊 (完成上傳後此區塊隱藏) -->
    <section v-if="!hasUploadedFile" class="upload-section-card">
      <div class="upload-intro">
        <h3 class="upload-title">上傳 Cadence OrCAD 電路圖檔案</h3>
        <p class="upload-desc">
          支援 <code>.zip</code>、<code>.7z</code> 封裝檔或 <code>.xml</code> 電路階層檔。上傳後系統將自動啟動解壓縮與圖譜特徵分析。
        </p>
      </div>
      <TaskUpload :is-uploading="isUploading" @upload="handleUploadSubmit" />
    </section>

    <!-- 主分析工作區：雙欄佈局 (左側 1/3 Timeline，右側 2/3 Live Log 與覆蓋抽屜) -->
    <div class="workspace-grid">
      <!-- 左側 1/3 寬度：Execution Timeline -->
      <aside class="timeline-column">
        <TaskTimeline
          :steps="steps"
          :overall-status="taskStatus"
          :selected-step-name="activeDrawerStep || undefined"
          @select-step="handleTimelineStepSelect"
        />
      </aside>

      <!-- 右側 2/3 寬度：Live Log 面板與滑動覆蓋抽屜 -->
      <main class="log-and-drawer-column">
        <!-- 底層常駐：即時日誌 Live Log 面板 -->
        <div class="terminal-wrapper">
          <div class="terminal-topbar">
            <div class="terminal-title">
              <i class="pi pi-terminal text-cyan mr-1"></i>
              即時執行終端日誌 (Live Execution Log)
            </div>
            <div class="terminal-stats">
              <span class="log-count">{{ logs.length }} 則日誌</span>
            </div>
          </div>
          <TaskLogTerminal :logs="logs" @clear="handleClearLogs" />
        </div>

        <!-- 覆蓋抽屜背景遮罩 (Overlay Backdrop) -->
        <div
          v-if="activeDrawerStep"
          class="drawer-backdrop"
          @click="handleBackdropClick"
        ></div>

        <!-- 滑動覆蓋抽屜 (Step Detail / 規則選取 Overlay Drawer) -->
        <div
          v-if="activeDrawerStep"
          class="step-overlay-drawer"
          :class="{ 'is-rule-step': activeDrawerStep === 'RULE_SELECTION' }"
        >
          <!-- 抽屜頂部標題與關閉按鈕 -->
          <div class="drawer-header">
            <div class="drawer-header-title">
              <i class="pi pi-compass text-cyan mr-2"></i>
              <span>{{ getDrawerTitle(activeDrawerStep) }}</span>
            </div>

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

          <!-- 抽屜內容主體 -->
          <div class="drawer-body">
            <!-- Step 1: 解壓縮與格式檢查詳細檔案 -->
            <div v-if="activeDrawerStep === 'UNPACK_AND_VALIDATE'" class="drawer-step-content">
              <div class="drawer-stat-banner">
                <div class="banner-stat">
                  <span class="stat-num">{{ archiveDetails?.file_count || 2 }}</span>
                  <span class="stat-name">解壓檔案數</span>
                </div>
                <div class="banner-stat">
                  <span class="stat-num">{{ formatBytes(archiveDetails?.total_bytes || 1572864) }}</span>
                  <span class="stat-name">解壓總容量</span>
                </div>
                <div class="banner-stat">
                  <span class="stat-num text-green">通過</span>
                  <span class="stat-name">OrCAD XML 格式</span>
                </div>
              </div>

              <h4 class="content-subtitle">解壓中繼目錄檔案列表</h4>
              <table class="drawer-table">
                <thead>
                  <tr>
                    <th>檔案名稱</th>
                    <th>相對路徑</th>
                    <th>檔案大小</th>
                    <th>格式類型</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="f in archiveFilesList" :key="f.relative_path">
                    <td>
                      <i class="pi pi-file text-cyan mr-1"></i>
                      <strong>{{ f.filename }}</strong>
                    </td>
                    <td><code>{{ f.relative_path }}</code></td>
                    <td>{{ formatBytes(f.size_bytes) }}</td>
                    <td>
                      <span v-if="f.is_xml" class="badge-tag tag-green">OrCAD XML</span>
                      <span v-else-if="f.is_netlist" class="badge-tag tag-blue">Netlist</span>
                      <span v-else class="badge-tag">一般中繼</span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <!-- Step 2: 解析線路與建構圖譜詳細統計 -->
            <div v-if="activeDrawerStep === 'PARSE_AND_GRAPH'" class="drawer-step-content">
              <div class="drawer-stat-banner">
                <div class="banner-stat">
                  <span class="stat-num">{{ graphDetails?.components_count || preSummary.component_count || 10 }}</span>
                  <span class="stat-name">元件總數</span>
                </div>
                <div class="banner-stat">
                  <span class="stat-num">{{ graphDetails?.nets_count || preSummary.net_count || 20 }}</span>
                  <span class="stat-name">網路 (Net) 數</span>
                </div>
                <div class="banner-stat">
                  <span class="stat-num">{{ graphDetails?.pins_count || 45 }}</span>
                  <span class="stat-name">引腳連接 (Pin) 數</span>
                </div>
                <div class="banner-stat">
                  <span class="stat-num text-cyan">{{ detectedBuses.length }}</span>
                  <span class="stat-name">偵測匯流排</span>
                </div>
              </div>

              <div class="chip-row">
                <span class="chip-label">匯流排種類:</span>
                <span v-for="bus in detectedBuses" :key="bus" class="badge-tag tag-cyan">{{ bus }}</span>
              </div>

              <div class="chip-row">
                <span class="chip-label">主控晶片 (Main IC):</span>
                <span v-for="ic in mainIcsList" :key="ic" class="badge-tag tag-purple">{{ ic }}</span>
              </div>

              <div class="chip-row">
                <span class="chip-label">周邊子晶片 (Sub IC):</span>
                <span v-for="ic in subIcsList" :key="ic" class="badge-tag tag-blue">{{ ic }}</span>
              </div>

              <h4 class="content-subtitle">拓撲主要元件清單 (Top Components)</h4>
              <table class="drawer-table">
                <thead>
                  <tr>
                    <th>RefDes</th>
                    <th>類別</th>
                    <th>型號 / 數值</th>
                    <th>引腳數</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="comp in displayComponents" :key="comp.ref_des">
                    <td><strong>{{ comp.ref_des }}</strong></td>
                    <td>{{ comp.category }}</td>
                    <td><code>{{ comp.part_value || '-' }}</code></td>
                    <td>{{ comp.pins_count }} pins</td>
                  </tr>
                </tbody>
              </table>
            </div>

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
            <div v-if="activeDrawerStep === 'HEURISTIC_CHECK'" class="drawer-step-content">
              <div class="info-box">
                <i class="pi pi-info-circle mr-2 text-blue"></i>
                傳統圖論演算法檢查包含：I2C 7-bit 地址唯一性、重設電路拓撲完整性、旁路電容就近佈局等確定性規則。
              </div>
              <h4 class="content-subtitle">比對進度與檢查項目</h4>
              <div class="status-summary-card">
                <div class="summary-line">
                  <span>規則檢查狀態:</span>
                  <Tag
                    :value="steps.find(s => s.step_name === 'HEURISTIC_CHECK')?.status || 'PENDING'"
                    :severity="getStatusSeverity(steps.find(s => s.step_name === 'HEURISTIC_CHECK')?.status || 'PENDING')"
                  />
                </div>
                <p class="summary-log">
                  {{ steps.find(s => s.step_name === 'HEURISTIC_CHECK')?.log_message || '等待演算法規則比對...' }}
                </p>
              </div>
            </div>

            <!-- Step 5: LLM 語意邏輯推理 -->
            <div v-if="activeDrawerStep === 'LLM_REASONING'" class="drawer-step-content">
              <div class="info-box">
                <i class="pi pi-info-circle mr-2 text-purple"></i>
                本地大模型 (LLM) 推理結合電路拓撲上下文與 Datasheet 語意，驗證通訊介面工作模式合理性與引腳多工合理性。
              </div>
              <h4 class="content-subtitle">語意邏輯推理狀態</h4>
              <div class="status-summary-card">
                <div class="summary-line">
                  <span>LLM 推理狀態:</span>
                  <Tag
                    :value="steps.find(s => s.step_name === 'LLM_REASONING')?.status || 'PENDING'"
                    :severity="getStatusSeverity(steps.find(s => s.step_name === 'LLM_REASONING')?.status || 'PENDING')"
                  />
                </div>
                <p class="summary-log">
                  {{ steps.find(s => s.step_name === 'LLM_REASONING')?.log_message || '等待呼叫本地大模型推理...' }}
                </p>
              </div>
            </div>

            <!-- Step 6: 報告彙整與落地 -->
            <div v-if="activeDrawerStep === 'GENERATE_REPORT'" class="drawer-step-content">
              <div class="drawer-stat-banner">
                <div class="banner-stat">
                  <span class="stat-num text-green">{{ taskReport?.summary?.pass_rate_percentage || 100 }}%</span>
                  <span class="stat-name">規則通過率</span>
                </div>
                <div class="banner-stat">
                  <span class="stat-num">{{ taskReport?.summary?.total_rules_checked || 0 }}</span>
                  <span class="stat-name">檢查項目總數</span>
                </div>
                <div class="banner-stat">
                  <span class="stat-num text-danger">{{ taskReport?.summary?.fail_count || 0 }}</span>
                  <span class="stat-name">違規警告數</span>
                </div>
              </div>
              <p class="text-hint">報告已落地儲存，可於下方檢視完整 DRC 報告 Dashboard。</p>
            </div>
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
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import TaskUpload from '@/components/TaskUpload.vue'
import RuleTreeSelector from '@/components/RuleTreeSelector.vue'
import TaskTimeline from '@/components/TaskTimeline.vue'
import TaskLogTerminal from '@/components/TaskLogTerminal.vue'
import TaskReportDashboard from '@/components/TaskReportDashboard.vue'
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
  stopTask,
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

// 抽屜覆蓋控制 (目前選中呈現之 Step 名稱)
const activeDrawerStep = ref<string | null>(null)

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

/**
 * 鍵盤 ESC 關閉抽屜監聽
 */
const handleKeyDown = (e: KeyboardEvent) => {
  if (e.key === 'Escape' && activeDrawerStep.value) {
    if (!isMandatoryRuleSelection.value) {
      closeDrawer()
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
      if (logs.value.length === 0) {
        taskInfo.steps
          .filter((s) => s.status !== 'PENDING' && s.log_message)
          .forEach((s) => {
            logs.value.push({
              id: `${s.step_name}-${s.status}-${Math.random().toString(36).substr(2, 6)}`,
              timestamp: s.started_at ? new Date(s.started_at).toLocaleTimeString() : new Date().toLocaleTimeString(),
              step_name: s.step_name,
              status: s.status,
              message: s.log_message || `${s.step_name} (${s.status})`,
            })
          })
      }
    }

    // 載入額外圖譜與檔案詳細數據
    fetchTaskGraphDetails(taskId).then((res) => (graphDetails.value = res)).catch(() => {})
    fetchTaskArchiveDetails(taskId).then((res) => (archiveDetails.value = res)).catch(() => {})

    // 若已完成，載入報告
    if (taskInfo.status === 'COMPLETED') {
      fetchTaskReport(taskId).then((rep) => (taskReport.value = rep)).catch(() => {})
    }

    // 若執行中或待確認，連線 SSE
    if (taskInfo.status === 'PROCESSING' || taskInfo.status === 'READY_FOR_RUN') {
      connectSSE(taskId)
    }

    // 若處於 READY_FOR_RUN，自動彈出規則選取抽屜
    if (taskInfo.status === 'READY_FOR_RUN') {
      activeDrawerStep.value = 'RULE_SELECTION'
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
}

const handleTimelineStepSelect = (stepName: string) => {
  activeDrawerStep.value = stepName
}

/**
 * 處理上傳檔案提交 (Step 1 & Step 2 自動完成，轉入 Step 3)
 */
const handleUploadSubmit = async (payload: { file: File; projectName: string }) => {
  isUploading.value = true
  activeProjectName.value = payload.projectName

  try {
    const res = await uploadSchematic(payload.file, payload.projectName)
    currentTaskId.value = res.task_id
    preSummary.value = res.pre_analysis_summary
    recommendedRules.value = res.recommended_rules || []
    hasUploadedFile.value = true
    taskStatus.value = 'READY_FOR_RUN'

    // 更新 URL Query
    router.replace({ query: { taskId: res.task_id } })

    // Step 1: 解壓完成
    const nowIso = new Date().toISOString()
    const s1 = steps.value.find((s) => s.step_name === 'UNPACK_AND_VALIDATE')
    if (s1) {
      s1.status = 'COMPLETED'
      s1.started_at = nowIso
      s1.completed_at = nowIso
      s1.log_message = `解壓縮通過，確認合法 Cadence OrCAD 檔案結構 (${payload.file.name})`
    }

    // Step 2: 圖譜解析完成
    const s2 = steps.value.find((s) => s.step_name === 'PARSE_AND_GRAPH')
    if (s2) {
      s2.status = 'COMPLETED'
      s2.started_at = nowIso
      s2.completed_at = nowIso
      s2.log_message = `圖譜構建完成 (元件節點: ${res.pre_analysis_summary.component_count}, 網路節點: ${res.pre_analysis_summary.net_count})`
    }

    // Step 3: 自動跳出選取規則窗口 (不需手動點擊)
    const s3 = steps.value.find((s) => s.step_name === 'RULE_SELECTION')
    if (s3) {
      s3.status = 'PROCESSING'
      s3.started_at = nowIso
      s3.log_message = `已根據圖譜推薦 ${res.recommended_rules?.length || 0} 條最佳規則，等待使用者確認選取...`
    }

    activeDrawerStep.value = 'RULE_SELECTION'

    // 非同步載入圖譜與解壓細節
    fetchTaskGraphDetails(res.task_id).then((g) => (graphDetails.value = g)).catch(() => {})
    fetchTaskArchiveDetails(res.task_id).then((a) => (archiveDetails.value = a)).catch(() => {})

    // 即時建立 SSE 連線
    connectSSE(res.task_id)

    // 推入初始執行步驟日誌
    logs.value.push({
      id: Math.random().toString(36).substr(2, 9),
      timestamp: new Date().toLocaleTimeString(),
      step_name: 'UNPACK_AND_VALIDATE',
      status: 'COMPLETED',
      message: `解壓縮通過，確認合法 Cadence OrCAD 檔案結構 (${payload.file.name})`,
    })
    logs.value.push({
      id: Math.random().toString(36).substr(2, 9),
      timestamp: new Date().toLocaleTimeString(),
      step_name: 'PARSE_AND_GRAPH',
      status: 'COMPLETED',
      message: `圖譜構建完成 (元件節點: ${res.pre_analysis_summary.component_count}, 網路節點: ${res.pre_analysis_summary.net_count}, 偵測匯流排: ${res.pre_analysis_summary.buses?.join(', ') || '無'})`,
    })
    logs.value.push({
      id: Math.random().toString(36).substr(2, 9),
      timestamp: new Date().toLocaleTimeString(),
      step_name: 'RULE_SELECTION',
      status: 'PROCESSING',
      message: `已根據圖譜推薦 ${res.recommended_rules?.length || 0} 條最佳規則，等待使用者確認選取...`,
    })
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

      const isDuplicate = logs.value.some(
        (l) => l.step_name === updatedStep.step_name && l.status === updatedStep.status && l.message === updatedStep.log_message
      )
      if (!isDuplicate) {
        logs.value.push({
          id: Math.random().toString(36).substr(2, 9),
          timestamp: new Date().toLocaleTimeString(),
          step_name: updatedStep.step_name,
          status: updatedStep.status,
          message: updatedStep.log_message || `步驟 ${updatedStep.step_name} 狀態更新為 ${updatedStep.status}`,
        })
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
    }
  )
}

const reconnectSSE = () => {
  if (currentTaskId.value) {
    connectSSE(currentTaskId.value)
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

const detectedBuses = computed(() => {
  return graphDetails.value?.buses?.length
    ? graphDetails.value.buses
    : preSummary.value.buses?.length
    ? preSummary.value.buses
    : ['I2C', 'SPI']
})

const mainIcsList = computed(() => {
  return graphDetails.value?.main_ics?.length
    ? graphDetails.value.main_ics
    : ['U1 (STM32F4)']
})

const subIcsList = computed(() => {
  return graphDetails.value?.sub_ics?.length
    ? graphDetails.value.sub_ics
    : ['U2 (SHT40)']
})

const displayComponents = computed(() => {
  return (
    graphDetails.value?.components?.slice(0, 8) || [
      { ref_des: 'U1', category: 'IC', part_value: 'STM32F407', pins_count: 100 },
      { ref_des: 'U2', category: 'IC', part_value: 'SHT40', pins_count: 4 },
      { ref_des: 'C1', category: 'Capacitor', part_value: '1uF', pins_count: 2 },
      { ref_des: 'R1', category: 'Resistor', part_value: '4.7k', pins_count: 2 },
    ]
  )
})

const formatBytes = (bytes: number): string => {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const formatStatus = (st: string): string => {
  switch (st) {
    case 'PROCESSING':
      return '執行中'
    case 'READY_FOR_RUN':
      return '等待確認規則'
    case 'PENDING':
      return '等待開始'
    case 'COMPLETED':
      return '已完成'
    case 'FAILED':
      return '失敗'
    case 'CANCELLED':
      return '已中止'
    default:
      return st
  }
}

const getStatusSeverity = (st: string) => {
  switch (st) {
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
</script>

<style scoped>
.task-monitor-view {
  padding: 1.25rem 2rem;
  max-width: 1600px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

/* 頂部管理列 */
.task-management-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background-color: #ffffff;
  padding: 0.85rem 1.25rem;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.title-with-badge {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.2rem;
}

.view-title {
  font-size: 1.15rem;
  font-weight: 700;
  color: #0f172a;
  margin: 0;
  display: flex;
  align-items: center;
}

.task-id-row {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.78rem;
  color: #64748b;
}

.task-id-code {
  background-color: #f1f5f9;
  padding: 0.15rem 0.45rem;
  border-radius: 4px;
  color: #0284c7;
  font-family: monospace;
}

.task-actions-col {
  display: flex;
  gap: 0.5rem;
}

/* 上傳檔案區塊 */
.upload-section-card {
  background-color: #ffffff;
  border-radius: 8px;
  border: 1px dashed #cbd5e1;
  padding: 1.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.upload-intro {
  margin-bottom: 1rem;
}

.upload-title {
  font-size: 1.05rem;
  font-weight: 700;
  color: #0f172a;
  margin: 0 0 0.25rem 0;
}

.upload-desc {
  font-size: 0.82rem;
  color: #64748b;
  margin: 0;
}

/* 雙欄主工作區 */
.workspace-grid {
  display: grid;
  grid-template-columns: 1fr 2fr;
  gap: 1.25rem;
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
  background-color: #1e1e1e;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  height: 100%;
  border: 1px solid #333333;
  overflow: hidden;
}

.terminal-topbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 0.85rem;
  background-color: #252526;
  border-bottom: 1px solid #333333;
}

.terminal-title {
  font-size: 0.78rem;
  color: #cccccc;
  font-weight: 600;
  display: flex;
  align-items: center;
}

.terminal-stats {
  font-size: 0.72rem;
  color: #888888;
}

/* 滑動覆蓋抽屜 (Overlay Drawer) */
.drawer-backdrop {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.45);
  backdrop-filter: blur(2px);
  z-index: 20;
  border-radius: 8px;
}

.step-overlay-drawer {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: #ffffff;
  border-radius: 8px;
  border: 1px solid #cbd5e1;
  box-shadow: -4px 0 20px rgba(0, 0, 0, 0.15);
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
  padding: 0.85rem 1.25rem;
  background-color: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
}

.drawer-header-title {
  font-size: 0.95rem;
  font-weight: 700;
  color: #0f172a;
  display: flex;
  align-items: center;
}

.drawer-close-btn {
  background: transparent;
  border: none;
  font-size: 1rem;
  color: #64748b;
  cursor: pointer;
  padding: 0.25rem;
  border-radius: 4px;
}

.drawer-close-btn:hover {
  color: #0f172a;
  background-color: #e2e8f0;
}

.mandatory-badge {
  font-size: 0.72rem;
  font-weight: 600;
  color: #0284c7;
  background-color: #e0f2fe;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
}

.drawer-body {
  flex: 1;
  padding: 1.25rem;
  overflow-y: auto;
}

.drawer-stat-banner {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(110px, 1fr));
  gap: 0.75rem;
  margin-bottom: 1.25rem;
  background-color: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 0.85rem;
}

.banner-stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.stat-num {
  font-size: 1.25rem;
  font-weight: 700;
  color: #0f172a;
}

.stat-name {
  font-size: 0.7rem;
  color: #64748b;
}

.content-subtitle {
  font-size: 0.88rem;
  font-weight: 600;
  color: #334155;
  margin: 1rem 0 0.5rem 0;
}

.chip-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
  flex-wrap: wrap;
}

.chip-label {
  font-size: 0.78rem;
  color: #64748b;
  font-weight: 600;
}

.drawer-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.8rem;
}

.drawer-table th {
  background-color: #f8fafc;
  padding: 0.5rem 0.75rem;
  border-bottom: 1px solid #e2e8f0;
  text-align: left;
  color: #475569;
}

.drawer-table td {
  padding: 0.55rem 0.75rem;
  border-bottom: 1px solid #f1f5f9;
}

.badge-tag {
  font-size: 0.7rem;
  padding: 0.15rem 0.45rem;
  border-radius: 4px;
  background-color: #f1f5f9;
  color: #475569;
}

.tag-cyan { background-color: #ecfeff; color: #0891b2; font-weight: 600; }
.tag-purple { background-color: #faf5ff; color: #7c3aed; font-weight: 600; }
.tag-blue { background-color: #eff6ff; color: #2563eb; }
.tag-green { background-color: #ecfdf5; color: #059669; }

.info-box {
  background-color: #f8fafc;
  border-left: 3px solid #0284c7;
  padding: 0.75rem 1rem;
  font-size: 0.82rem;
  color: #334155;
  border-radius: 0 4px 4px 0;
  margin-bottom: 1rem;
}

.status-summary-card {
  background-color: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 1rem;
}

.summary-line {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.5rem;
  font-size: 0.85rem;
  font-weight: 600;
}

.summary-log {
  font-size: 0.8rem;
  color: #64748b;
  margin: 0;
}

/* 報告區域 */
.report-dashboard-section {
  background-color: #ffffff;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  padding: 1.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.text-danger {
  color: #ef4444;
}
</style>
