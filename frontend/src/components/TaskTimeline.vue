<template>
  <div class="task-timeline-container bg-surface-panel border-b border-surface-border px-3 py-1.5 flex items-center gap-3 overflow-x-auto shrink-0 select-none">
    <!-- 左側標題與總執行時間 (保留測試選擇器 .timeline-header / .section-title / .step-timer-text) -->
    <div class="timeline-header flex items-center gap-2 pr-3 border-r border-surface-border shrink-0">
      <h3 class="section-title text-[11px] font-medium text-vscode-textSecondary m-0 whitespace-nowrap">工作流執行歷程</h3>
      <span
        v-tooltip.bottom="'任務總執行時間（所有機器流程實際耗時總和）'"
        class="step-timer-text font-mono text-[11px] text-vscode-textMuted flex items-center shrink-0"
        :class="{ 'timer-running text-primary font-semibold': isTaskActive }"
        title="任務總執行時間（所有流程實際耗時總和）"
      >
        <i class="pi pi-clock timer-clock-icon mr-1 text-[10px]"></i>
        <span>{{ totalTaskDuration }}</span>
      </span>
    </div>

    <!-- 橫向輕量步驟進度條 (Horizontal Stepper Bar，高 ~32px) -->
    <div class="timeline-steps-list flex items-center gap-1.5 flex-1 min-w-0">
      <div
        v-for="step in steps"
        :key="step.step_name"
        v-tooltip.bottom="step.log_message || getStepDefaultHint(step.step_name)"
        class="step-item-card relative flex items-center gap-2 px-2.5 py-1 rounded border transition-colors cursor-pointer shrink-0 overflow-hidden"
        :class="[
          step.status === 'PENDING'
            ? 'opacity-75 bg-surface-ground border-surface-border hover:bg-surface-hover'
            : 'bg-surface-ground border-surface-border hover:bg-surface-hover',
          {
            'is-active !border-primary bg-primary/10': selectedStepName === step.step_name,
            'is-processing border-primary/50 bg-primary/5': step.status === 'PROCESSING',
            'is-completed border-emerald-500/50 bg-emerald-500/[0.06]': step.status === 'COMPLETED',
            'is-failed border-red-500/50 bg-red-500/[0.06]': step.status === 'FAILED',
          }
        ]"
        :title="step.status === 'PENDING' ? '點擊檢視此步驟說明與待執行狀態' : '點擊檢視此步驟詳情'"
        @click="handleStepClick(step)"
      >
        <!-- 節點狀態小圖示 -->
        <div class="step-connector flex items-center shrink-0">
          <div class="marker-circle w-4 h-4 rounded-full flex items-center justify-center text-[9px] shrink-0" :class="getMarkerClass(step.status)">
            <i :class="getStepIcon(step.status)"></i>
          </div>
        </div>

        <!-- 步驟名稱與計時器同行顯示 -->
        <div class="step-card-content flex items-center gap-2 min-w-0">
          <div class="step-title-row flex items-center gap-2">
            <span class="step-title text-xs font-medium text-vscode-textHeading whitespace-nowrap" :title="formatStepName(step.step_name)">
              {{ formatStepName(step.step_name) }}
            </span>
            <span
              class="step-timer-text font-mono text-[10px] text-vscode-textMuted flex items-center shrink-0"
              :class="{ 'timer-running text-primary font-semibold': step.status === 'PROCESSING' }"
            >
              <span>{{ stepDurations[step.step_name] || '0.00s' }}</span>
            </span>
          </div>

          <!-- 隱藏的日誌與步驟資訊節點 (供無障礙與單元測試讀取) -->
          <span class="step-log-message sr-only">
            {{ step.log_message || getStepDefaultHint(step.step_name) }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * @file TaskTimeline.vue
 * @description DBOS 6 大步驟橫向輕量進度條 (Horizontal Stepper Bar)，支援每個 Step 獨立即時計時器、底部微進度條與懸浮提示
 */

import { ref, computed, onMounted, onUnmounted } from 'vue'
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

// 即時計時器時鐘更新 (每 50ms 遞增，驅動 PROCESSING 步驟流暢跳秒)
const timerTick = ref<number>(Date.now())
const mountedTime = ref<number>(Date.now())
let timerInterval: any = null

onMounted(() => {
  mountedTime.value = Date.now()
  timerTick.value = Date.now()
  timerInterval = setInterval(() => {
    timerTick.value = Date.now()
  }, 50)
})

onUnmounted(() => {
  if (timerInterval) clearInterval(timerInterval)
})

/** 各步驟進入 PROCESSING 狀態時的基準時間戳快取 (防止伺服器與客戶端時鐘偏差產生負數定格) */
const localProcessingStartMap = new Map<string, number>()

/**
 * 點擊步驟卡片
 */
const handleStepClick = (step: StepItem) => {
  emit('select-step', step.step_name)
}

/**
 * 是否有任何步驟正在執行中（驅動計時器跳秒與高亮樣式）
 */
const isTaskActive = computed(() => {
  return (
    props.overallStatus === 'PROCESSING' ||
    props.overallStatus === 'PRE_ANALYZING' ||
    props.steps.some((s) => s.status === 'PROCESSING')
  )
})

/** 機器自動化分析步驟清單 (排除步驟 3 人工停頓等待) */
const MACHINE_STEPS = [
  'UNPACK_AND_VALIDATE',
  'PARSE_AND_GRAPH',
  'HEURISTIC_CHECK',
  'LLM_REASONING',
  'GENERATE_REPORT',
]

/**
 * 計算單一步驟實際秒數
 * @param step 步驟狀態資料項目
 * @param currentMs 當前本地毫秒時戳
 * @returns 步驟執行秒數數值
 */
const calculateStepDurationSeconds = (step: StepItem, currentMs: number): number => {
  if (step.status === 'PENDING') {
    return 0
  }

  if (step.step_name === 'RULE_SELECTION' && (!step.started_at || !step.completed_at)) {
    return step.status === 'COMPLETED' ? 0.08 : 0
  }

  const startMs = step.started_at ? Date.parse(step.started_at) : null
  const endMs = step.completed_at ? Date.parse(step.completed_at) : null

  if (step.status === 'PROCESSING') {
    if (!localProcessingStartMap.has(step.step_name)) {
      if (startMs && startMs <= currentMs + 100) {
        localProcessingStartMap.set(step.step_name, startMs)
      } else {
        localProcessingStartMap.set(step.step_name, currentMs)
      }
    }
    const baseStart = localProcessingStartMap.get(step.step_name) || currentMs
    const diffSec = (currentMs - baseStart) / 1000
    return Math.max(0.01, diffSec)
  }

  if (localProcessingStartMap.has(step.step_name)) {
    localProcessingStartMap.delete(step.step_name)
  }

  if (startMs && endMs) {
    return Math.max(0.01, (endMs - startMs) / 1000)
  } else if (startMs) {
    return 0.5
  }

  return 0
}

/**
 * 格式化單一步驟之耗時字串
 */
const formatStepDuration = (step: StepItem, currentMs: number): string => {
  if (step.status === 'PENDING') {
    return '0.00s'
  }
  if (step.step_name === 'RULE_SELECTION') {
    if (step.status === 'PROCESSING') return '推薦完畢'
    if (!step.started_at || !step.completed_at) return '0.08s'
  }
  const startMs = step.started_at ? Date.parse(step.started_at) : null
  const endMs = step.completed_at ? Date.parse(step.completed_at) : null

  if (step.status === 'COMPLETED' && !startMs && !endMs) {
    return '—'
  }

  const sec = calculateStepDurationSeconds(step, currentMs)
  return formatSeconds(sec)
}

/**
 * 響應式各步驟耗時字典
 */
const stepDurations = computed<Record<string, string>>(() => {
  const currentMs = timerTick.value
  const res: Record<string, string> = {}
  for (const step of props.steps) {
    res[step.step_name] = formatStepDuration(step, currentMs)
  }
  return res
})

/**
 * 響應式任務總執行時間
 */
const totalTaskDuration = computed<string>(() => {
  if (props.overallStatus === 'PENDING') {
    return '0.00s'
  }
  const currentMs = timerTick.value
  const totalSec = props.steps
    .filter((s) => MACHINE_STEPS.includes(s.step_name))
    .reduce((sum, s) => sum + calculateStepDurationSeconds(s, currentMs), 0)
  return formatSeconds(totalSec)
})

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

const getStepIcon = (status: StepState): string => {
  switch (status) {
    case 'COMPLETED':
      return 'pi pi-check text-[10px] font-bold'
    case 'PROCESSING':
      return 'pi pi-spin pi-spinner text-[9px]'
    case 'FAILED':
      return 'pi pi-times text-[10px] font-bold'
    default:
      return 'pi pi-circle text-[8px]'
  }
}

const getMarkerClass = (status: StepState): string => {
  switch (status) {
    case 'COMPLETED':
      return 'bg-emerald-500 text-white font-bold shadow-xs'
    case 'PROCESSING':
      return 'bg-primary/20 text-primary border border-primary/50'
    case 'FAILED':
      return 'bg-red-500 text-white font-bold shadow-xs'
    default:
      return 'bg-surface-ground text-vscode-textMuted border border-surface-border'
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
</script>
