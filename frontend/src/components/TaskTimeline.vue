<template>
  <div class="task-timeline-container">
    <div class="timeline-header">
      <div class="header-title-row">
        <h3 class="section-title">工作流執行歷程</h3>
        <Tag
          :value="formatOverallStatus(overallStatus)"
          :severity="getOverallSeverity(overallStatus)"
          class="overall-status-tag"
          :class="{ 'tag-pending': overallStatus === 'PENDING' }"
        />
      </div>
      <div class="header-timer-row">
        <span
          class="step-timer-text"
          :class="{ 'timer-running': overallStatus === 'PROCESSING' }"
          title="任務總執行時間"
        >
          <i class="pi pi-clock timer-clock-icon"></i>
          <span>{{ getTotalTaskDuration() }}</span>
        </span>
      </div>
    </div>

    <!-- 步驟時間軸清單 (6 大步驟) -->
    <div class="timeline-steps-list">
      <div
        v-for="(step, index) in steps"
        :key="step.step_name"
        class="step-item-card"
        :class="{
          'is-active': selectedStepName === step.step_name,
          'is-processing': step.status === 'PROCESSING',
          'is-completed': step.status === 'COMPLETED',
          'is-failed': step.status === 'FAILED',
        }"
        @click="handleStepClick(step.step_name)"
      >
        <!-- 左側節點圖示與連線 -->
        <div class="step-connector">
          <div class="marker-circle" :class="getMarkerClass(step.status)">
            <i :class="getStepIcon(step.status)"></i>
          </div>
          <div v-if="index < steps.length - 1" class="connecting-line"></div>
        </div>

        <!-- 右側步驟資訊卡片 -->
        <div class="step-card-content">
          <!-- 第 1 行：步驟標題（左）與狀態標籤（靠右對齊） -->
          <div class="step-title-row">
            <span class="step-title" :title="formatStepName(step.step_name)">
              {{ formatStepName(step.step_name) }}
            </span>
            <Tag
              :value="formatStepStatus(step.status)"
              :severity="getStatusSeverity(step.status)"
              class="step-status-tag"
              :class="{ 'tag-pending': step.status === 'PENDING' }"
            />
          </div>

          <!-- 第 2 行：即時計時器（純文字模式，靠右對齊，字級縮小） -->
          <div class="step-meta-row">
            <span class="step-timer-text" :class="{ 'timer-running': step.status === 'PROCESSING' }">
              <i class="pi pi-clock timer-clock-icon"></i>
              <span>{{ getStepDuration(step) }}</span>
            </span>
          </div>

          <!-- 第 3 行：詳細日誌訊息（預佔固定空間 2 行，防止高度上下跳動） -->
          <p class="step-log-message">
            {{ step.log_message || getStepDefaultHint(step.step_name) }}
          </p>

          <!-- 第 4 行：進度條（常駐顯示槽位，PENDING 顯示 0%，防止動態增高） -->
          <div
            v-if="['HEURISTIC_CHECK', 'LLM_REASONING'].includes(step.step_name)"
            class="step-progress-wrapper"
          >
            <div class="progress-bar-bg">
              <div
                class="progress-bar-fill"
                :class="{ 'fill-pending': step.status === 'PENDING' }"
                :style="{ width: getStepProgressPercent(step) + '%' }"
              ></div>
            </div>
            <span class="progress-text">{{ getStepProgressLabel(step) }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * @file TaskTimeline.vue
 * @description DBOS 6 大步驟時間軸元件，支援每個 Step 獨立即時計時器（完成停止）、進度條與點擊檢視
 */

import { ref, onMounted, onUnmounted } from 'vue'
import Tag from 'primevue/tag'
import type { StepItem, StepState } from '@/types/task'

interface Props {
  /** 步驟狀態列表 (共 6 步) */
  steps: StepItem[]
  /** 整體任務狀態 */
  overallStatus?: string
  /** 目前選中檢視之步驟名稱 */
  selectedStepName?: string
}

const props = withDefaults(defineProps<Props>(), {
  steps: () => [],
  overallStatus: 'PENDING',
  selectedStepName: '',
})

const emit = defineEmits<{
  (e: 'select-step', stepName: string): void
}>()

// 即時計時器時鐘更新
const nowTime = ref<number>(Date.now())
let timerInterval: any = null

onMounted(() => {
  timerInterval = setInterval(() => {
    nowTime.value = Date.now()
  }, 50)
})

onUnmounted(() => {
  if (timerInterval) clearInterval(timerInterval)
})

/**
 * 點擊步驟卡片
 */
const handleStepClick = (stepName: string) => {
  emit('select-step', stepName)
}

/**
 * 計算整個任務之總耗時
 * - 格式標準同卡片：小於 1 秒兩位小數、小於 1 分鐘一位小數、大於 1 分鐘分秒
 */
const getTotalTaskDuration = (): string => {
  if (props.overallStatus === 'PENDING') {
    return '0.00s'
  }

  // 尋找最早開始時間
  const startTimes = props.steps
    .map((s) => (s.started_at ? Date.parse(s.started_at) : null))
    .filter((t): t is number => t !== null && !isNaN(t))

  if (startTimes.length === 0) {
    return '0.00s'
  }

  const earliestStart = Math.min(...startTimes)

  // 若整體任務仍在執行中 (PROCESSING)
  if (props.overallStatus === 'PROCESSING') {
    const diffSec = Math.max(0.01, (nowTime.value - earliestStart) / 1000)
    return formatSeconds(diffSec)
  }

  // 任務已結束 (COMPLETED, FAILED, CANCELLED) 或中途狀態
  const endTimes = props.steps
    .map((s) => (s.completed_at ? Date.parse(s.completed_at) : null))
    .filter((t): t is number => t !== null && !isNaN(t))

  if (endTimes.length > 0) {
    const latestEnd = Math.max(...endTimes)
    const diffSec = Math.max(0.01, (latestEnd - earliestStart) / 1000)
    return formatSeconds(diffSec)
  }

  const diffSec = Math.max(0.01, (nowTime.value - earliestStart) / 1000)
  return formatSeconds(diffSec)
}

/**
 * 計算各步驟之耗時（執行中動態跳秒，完成後固定在最終耗時）
 * - 小於 1 秒：顯示兩位小數 (例如 0.25s, 0.00s)
 * - 小於 1 分鐘：顯示一位小數 (例如 1.5s, 45.2s)
 * - 大於 1 分鐘：維持現有格式 (例如 1m 23s)
 */
const getStepDuration = (step: StepItem): string => {
  if (step.status === 'PENDING') {
    return '0.00s'
  }

  const startMs = step.started_at ? Date.parse(step.started_at) : null
  const endMs = step.completed_at ? Date.parse(step.completed_at) : null

  if (step.status === 'PROCESSING') {
    if (!startMs) return '0.01s'
    const diffSec = Math.max(0.01, (nowTime.value - startMs) / 1000)
    return formatSeconds(diffSec)
  }

  // COMPLETED, FAILED, SKIPPED: 固定在最終結束時間
  if (startMs && endMs) {
    const diffSec = Math.max(0.01, (endMs - startMs) / 1000)
    return formatSeconds(diffSec)
  } else if (startMs) {
    // 降級展示最後時間
    return formatSeconds(0.5)
  }

  return '0.00s'
}

const formatSeconds = (sec: number): string => {
  if (sec < 1) {
    return `${sec.toFixed(2)}s`
  }
  if (sec < 60) {
    return `${sec.toFixed(1)}s`
  }
  const mins = Math.floor(sec / 60)
  const remainSec = (sec % 60).toFixed(0)
  return `${mins}m ${remainSec}s`
}

/**
 * 格式化步驟名稱為繁體中文 (含編號)
 */
const formatStepName = (stepName: string): string => {
  const mapping: Record<string, string> = {
    UNPACK_AND_VALIDATE: '1. 解壓縮與檔案格式預檢',
    PARSE_AND_GRAPH: '2. 圖譜構建與線路解析',
    RULE_SELECTION: '3. 規則推薦與選取',
    HEURISTIC_CHECK: '4. 傳統演算法規則比對',
    LLM_REASONING: '5. 本地大模型語意推理',
    GENERATE_REPORT: '6. 報告彙整與資源落地',
  }
  return mapping[stepName] || stepName
}

const formatStepStatus = (status: StepState): string => {
  switch (status) {
    case 'COMPLETED':
      return '已完成'
    case 'PROCESSING':
      return '進行中'
    case 'FAILED':
      return '失敗'
    case 'SKIPPED':
      return '略過'
    default:
      return '等待中'
  }
}

const formatOverallStatus = (status: string): string => {
  switch (status) {
    case 'COMPLETED':
      return '任務已完成'
    case 'PROCESSING':
      return '分析執行中'
    case 'READY_FOR_RUN':
      return '等待確認規則'
    case 'FAILED':
      return '任務失敗'
    case 'CANCELLED':
      return '已手動中止'
    default:
      return '等待開始'
  }
}

const getStatusSeverity = (status: StepState) => {
  switch (status) {
    case 'COMPLETED':
      return 'success'
    case 'PROCESSING':
      return 'info'
    case 'FAILED':
      return 'danger'
    case 'SKIPPED':
      return 'warn'
    default:
      return 'secondary'
  }
}

const getOverallSeverity = (status: string) => {
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

const getStepIcon = (status: StepState): string => {
  switch (status) {
    case 'COMPLETED':
      return 'pi pi-check'
    case 'PROCESSING':
      return 'pi pi-spin pi-spinner'
    case 'FAILED':
      return 'pi pi-times'
    default:
      return 'pi pi-circle'
  }
}

const getMarkerClass = (status: StepState): string => {
  switch (status) {
    case 'COMPLETED':
      return 'marker-completed'
    case 'PROCESSING':
      return 'marker-processing'
    case 'FAILED':
      return 'marker-failed'
    default:
      return 'marker-pending'
  }
}

const getStepDefaultHint = (stepName: string): string => {
  switch (stepName) {
    case 'UNPACK_AND_VALIDATE':
      return '等待檔案上傳與格式驗證...'
    case 'PARSE_AND_GRAPH':
      return '等待構建 NetworkX 電路圖譜...'
    case 'RULE_SELECTION':
      return '等待使用者選取欲檢驗之規則...'
    case 'HEURISTIC_CHECK':
      return '等待執行圖論啟發式規則比對...'
    case 'LLM_REASONING':
      return '等待呼叫本地大模型邏輯推理...'
    case 'GENERATE_REPORT':
      return '等待產出最終 DRC 違規報告...'
    default:
      return '等待步驟執行中...'
  }
}

const getStepProgressPercent = (step: StepItem): number => {
  if (step.status === 'COMPLETED') return 100
  if (step.status === 'PROCESSING') return 65
  return 0
}

const getStepProgressLabel = (step: StepItem): string => {
  if (step.status === 'COMPLETED') return '已處理完成: 100%'
  if (step.status === 'PROCESSING') return '正在分析比對項目中...'
  return '等待啟動比對/推理 (0%)'
}
</script>

<style scoped>
.task-timeline-container {
  background-color: var(--vscode-bg-panel, #252526);
  border-radius: 6px;
  border: 1px solid var(--vscode-border, #333333);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
  padding: 1rem 0.85rem;
  display: flex;
  flex-direction: column;
}

.timeline-header {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  margin-bottom: 0.85rem;
  padding-bottom: 0.6rem;
  border-bottom: 1px solid var(--vscode-border, #333333);
}

.header-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.35rem;
}

.section-title {
  font-size: 0.88rem;
  font-weight: 700;
  color: var(--vscode-text-heading, #ffffff);
  margin: 0;
  white-space: nowrap;
}

.header-timer-row {
  display: flex;
  align-items: center;
  justify-content: flex-end;
}

.overall-status-tag {
  font-size: 0.65rem !important;
  padding: 0.08rem 0.35rem !important;
  border-radius: 3px !important;
  font-weight: 500 !important;
  flex-shrink: 0;
}

.overall-status-tag.tag-pending {
  background-color: #333333 !important;
  color: #999999 !important;
  border: 1px solid #444444 !important;
}

/* 步驟清單 */
.timeline-steps-list {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.step-item-card {
  display: flex;
  gap: 0.75rem;
  padding: 0.5rem 0.5rem 0.65rem 0.5rem;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.15s ease;
  position: relative;
}

.step-item-card:hover {
  background-color: var(--vscode-bg-hover, #2a2d2e);
}

.step-item-card.is-active {
  background-color: rgba(0, 122, 204, 0.15);
  border: 1px solid var(--vscode-blue, #007acc);
}

/* 連接節點與連線 */
.step-connector {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 18px;
  flex-shrink: 0;
}

.marker-circle {
  width: 15px;
  height: 15px;
  margin-top: 1px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.52rem;
  z-index: 2;
  transition: all 0.2s ease;
}

.marker-pending {
  background-color: var(--vscode-bg-header, #2d2d2d);
  color: var(--vscode-text-muted, #858585);
  border: 1px solid var(--vscode-border-light, #3c3c3c);
}

.marker-processing {
  background-color: var(--vscode-blue, #007acc);
  color: #ffffff;
  box-shadow: 0 0 0 2px rgba(0, 122, 204, 0.3);
}

.marker-completed {
  background-color: #10b981;
  color: #ffffff;
}

.marker-failed {
  background-color: #ef4444;
  color: #ffffff;
}

.connecting-line {
  flex: 1;
  width: 2px;
  background-color: var(--vscode-border, #333333);
  margin: 3px 0;
  min-height: 38px;
}

/* 步驟內容 */
.step-card-content {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

/* 第 1 行：標題置左，狀態標籤靠右對齊 */
.step-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.35rem;
  margin-bottom: 0.2rem;
  min-width: 0;
}

.step-title {
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--vscode-text-main, #cccccc);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
  min-width: 0;
}

/* 狀態標籤縮小一級 */
:deep(.step-status-tag),
.step-status-tag {
  font-size: 0.65rem !important;
  padding: 0.08rem 0.35rem !important;
  border-radius: 3px !important;
  line-height: 1.15 !important;
  font-weight: 500 !important;
  flex-shrink: 0;
}

/* 「等待中」標籤改灰色 */
:deep(.step-status-tag.tag-pending),
.step-status-tag.tag-pending {
  background-color: #333333 !important;
  color: #999999 !important;
  border: 1px solid #444444 !important;
}

/* 第 2 行：計時器（純文字模式，靠右對齊，字級縮小） */
.step-meta-row {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  margin-bottom: 0.25rem;
}

.step-timer-text {
  font-size: 0.65rem;
  font-family: monospace;
  color: var(--vscode-text-muted, #858585);
  display: inline-flex;
  align-items: center;
  gap: 0.35rem; /* 時鐘圖標與數字之間保持適當間距 */
  line-height: 1.2;
}

.timer-clock-icon {
  font-size: 0.62rem;
  opacity: 0.85;
}

.step-timer-text.timer-running {
  color: #38bdf8;
  font-weight: 600;
}

/* 第 3 行：詳細日誌（預佔固定空間 2 行，防止動態增高） */
.step-log-message {
  font-size: 0.75rem;
  color: var(--vscode-text-muted, #858585);
  margin: 0 0 0.35rem 0;
  line-height: 1.35;
  height: 2.7em;
  min-height: 2.7em;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
  word-break: break-word;
}

/* 第 4 行：進度條（常駐顯示槽位） */
.step-progress-wrapper {
  margin-top: auto;
  min-height: 18px;
}

.progress-bar-bg {
  width: 100%;
  height: 4px;
  background-color: var(--vscode-bg-header, #2d2d2d);
  border-radius: 9999px;
  overflow: hidden;
}

.progress-bar-fill {
  height: 100%;
  background-color: var(--vscode-blue, #007acc);
  border-radius: 9999px;
  transition: width 0.3s ease;
}

.progress-bar-fill.fill-pending {
  background-color: transparent;
}

.progress-text {
  font-size: 0.65rem;
  color: var(--vscode-text-muted, #858585);
  display: block;
  margin-top: 0.12rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
