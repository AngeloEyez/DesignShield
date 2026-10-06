<template>
  <div class="task-timeline-container">
    <div class="timeline-header">
      <div class="header-left">
        <h3 class="section-title">
          <i class="pi pi-compass text-cyan mr-2"></i>
          DBOS 工作流執行歷程 (Durable Execution Timeline)
        </h3>
        <span class="timeline-subtitle">點擊步驟可於右側檢視詳細拓撲數據與分析進度</span>
      </div>
      <div class="header-right">
        <Tag :value="formatOverallStatus(overallStatus)" :severity="getOverallSeverity(overallStatus)" />
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
          <div class="step-header-row">
            <div class="step-name-col">
              <span class="step-title">{{ formatStepName(step.step_name) }}</span>
            </div>
            <div class="step-meta-col">
              <!-- 即時計時器 (完成即停止) -->
              <span class="step-timer-badge" :class="{ 'timer-running': step.status === 'PROCESSING' }">
                <i class="pi pi-clock mr-1"></i>
                {{ getStepDuration(step) }}
              </span>
              <Tag :value="formatStepStatus(step.status)" :severity="getStatusSeverity(step.status)" />
            </div>
          </div>

          <!-- 步驟即時日誌或摘要 -->
          <p class="step-log-message">
            {{ step.log_message || getStepDefaultHint(step.step_name) }}
          </p>

          <!-- 步驟進度條 (演算法比對與 LLM 推理) -->
          <div
            v-if="['HEURISTIC_CHECK', 'LLM_REASONING'].includes(step.step_name) && step.status !== 'PENDING'"
            class="step-progress-wrapper"
          >
            <div class="progress-bar-bg">
              <div
                class="progress-bar-fill"
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

withDefaults(defineProps<Props>(), {
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
  }, 200)
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
 * 計算各步驟之耗時（執行中動態跳秒，完成後固定在最終耗時）
 */
const getStepDuration = (step: StepItem): string => {
  if (step.status === 'PENDING') {
    return '0.0s'
  }

  const startMs = step.started_at ? Date.parse(step.started_at) : null
  const endMs = step.completed_at ? Date.parse(step.completed_at) : null

  if (step.status === 'PROCESSING') {
    if (!startMs) return '0.1s'
    const diffSec = Math.max(0.1, (nowTime.value - startMs) / 1000)
    return formatSeconds(diffSec)
  }

  // COMPLETED, FAILED, SKIPPED: 固定在最終結束時間
  if (startMs && endMs) {
    const diffSec = Math.max(0.1, (endMs - startMs) / 1000)
    return formatSeconds(diffSec)
  } else if (startMs) {
    // 降級展示最後時間
    return '0.5s'
  }

  return '0.0s'
}

const formatSeconds = (sec: number): string => {
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
  return '未開始'
}
</script>

<style scoped>
.task-timeline-container {
  background-color: #ffffff;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
}

.timeline-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1.25rem;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid #f1f5f9;
}

.section-title {
  font-size: 1rem;
  font-weight: 700;
  color: #0f172a;
  margin: 0 0 0.2rem 0;
  display: flex;
  align-items: center;
}

.timeline-subtitle {
  font-size: 0.75rem;
  color: #64748b;
}

/* 步驟清單 */
.timeline-steps-list {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.step-item-card {
  display: flex;
  gap: 0.85rem;
  padding: 0.5rem 0.65rem 0.75rem 0.65rem;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
  position: relative;
}

.step-item-card:hover {
  background-color: #f8fafc;
}

.step-item-card.is-active {
  background-color: #f0f9ff;
  border: 1px solid #bae6fd;
}

/* 連接節點與連線 */
.step-connector {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 24px;
  flex-shrink: 0;
}

.marker-circle {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.7rem;
  z-index: 2;
  transition: all 0.2s ease;
}

.marker-pending {
  background-color: #f1f5f9;
  color: #94a3b8;
  border: 1px solid #cbd5e1;
}

.marker-processing {
  background-color: #0284c7;
  color: #ffffff;
  box-shadow: 0 0 0 3px rgba(2, 132, 199, 0.2);
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
  background-color: #e2e8f0;
  margin: 4px 0;
  min-height: 38px;
}

/* 步驟內容 */
.step-card-content {
  flex: 1;
  min-width: 0;
}

.step-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.25rem;
  gap: 0.5rem;
}

.step-title {
  font-size: 0.85rem;
  font-weight: 600;
  color: #1e293b;
}

.step-meta-col {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.step-timer-badge {
  font-size: 0.72rem;
  font-family: monospace;
  background-color: #f1f5f9;
  color: #475569;
  padding: 0.15rem 0.4rem;
  border-radius: 4px;
  display: inline-flex;
  align-items: center;
  border: 1px solid #e2e8f0;
}

.step-timer-badge.timer-running {
  background-color: #e0f2fe;
  color: #0369a1;
  border-color: #bae6fd;
  font-weight: 600;
}

.step-log-message {
  font-size: 0.78rem;
  color: #64748b;
  margin: 0 0 0.35rem 0;
  line-height: 1.35;
  word-break: break-word;
}

/* 進度條 */
.step-progress-wrapper {
  margin-bottom: 0.35rem;
}

.progress-bar-bg {
  width: 100%;
  height: 5px;
  background-color: #e2e8f0;
  border-radius: 9999px;
  overflow: hidden;
}

.progress-bar-fill {
  height: 100%;
  background-color: #0284c7;
  border-radius: 9999px;
  transition: width 0.3s ease;
}

.progress-text {
  font-size: 0.68rem;
  color: #94a3b8;
  display: block;
  margin-top: 0.15rem;
}
</style>
