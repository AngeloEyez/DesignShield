<template>
  <div class="task-timeline-container bg-surface-card rounded-md border border-surface-border shadow-sm p-4 flex flex-col">
    <div class="timeline-header flex flex-col gap-1 mb-3.5 pb-2.5 border-b border-surface-border">
      <div class="header-title-row flex items-center justify-between gap-1.5">
        <h3 class="section-title text-sm font-bold text-surface-900 dark:text-surface-0 m-0 whitespace-nowrap">工作流執行歷程</h3>
        <Tag
          :value="formatOverallStatus(overallStatus)"
          :severity="getOverallSeverity(overallStatus)"
          class="overall-status-tag text-[10px] px-1.5 py-0.5 rounded font-medium shrink-0"
          :class="{ 'tag-pending bg-surface-ground text-surface-400 border border-surface-border': overallStatus === 'PENDING' }"
        />
      </div>
      <div class="header-timer-row flex items-center justify-end">
        <span
          class="step-timer-text font-mono text-xs text-surface-400 flex items-center"
          :class="{ 'timer-running text-primary font-semibold': isTaskActive }"
          title="任務總執行時間（所有流程實際耗時總和）"
        >
          <i class="pi pi-clock timer-clock-icon mr-1 text-[11px]"></i>
          <span>{{ getTotalTaskDuration() }}</span>
        </span>
      </div>
    </div>

    <!-- 步驟時間軸清單 (6 大步驟) -->
    <div class="timeline-steps-list flex flex-col gap-2">
      <div
        v-for="(step, index) in steps"
        :key="step.step_name"
        class="step-item-card flex gap-3 p-2.5 rounded-md border border-surface-border bg-surface-ground/40 cursor-pointer transition-colors hover:bg-surface-ground"
        :class="{
          'is-active border-primary bg-primary/5': selectedStepName === step.step_name,
          'is-processing border-sky-500/40 bg-sky-500/5': step.status === 'PROCESSING',
          'is-completed border-green-500/30': step.status === 'COMPLETED',
          'is-failed border-red-500/30': step.status === 'FAILED',
        }"
        @click="handleStepClick(step.step_name)"
      >
        <!-- 左側節點圖示與連線 -->
        <div class="step-connector flex flex-col items-center relative">
          <div class="marker-circle w-6 h-6 rounded-full flex items-center justify-center text-xs shrink-0 z-10" :class="getMarkerClass(step.status)">
            <i :class="getStepIcon(step.status)"></i>
          </div>
          <div v-if="index < steps.length - 1" class="connecting-line absolute top-6 bottom-[-10px] w-0.5 bg-surface-border"></div>
        </div>

        <!-- 右側步驟資訊卡片 -->
        <div class="step-card-content flex-1 flex flex-col gap-1 min-w-0">
          <!-- 第 1 行：步驟標題（左）與狀態標籤（靠右對齊） -->
          <div class="step-title-row flex items-center justify-between gap-2">
            <span class="step-title text-xs font-semibold text-surface-900 dark:text-surface-0 truncate" :title="formatStepName(step.step_name)">
              {{ formatStepName(step.step_name) }}
            </span>
            <Tag
              :value="formatStepStatus(step.status)"
              :severity="getStatusSeverity(step.status)"
              class="step-status-tag text-[10px] px-1.5 py-0.5 rounded font-medium shrink-0"
              :class="{ 'tag-pending bg-surface-ground text-surface-400 border border-surface-border': step.status === 'PENDING' }"
            />
          </div>

          <!-- 第 2 行：即時計時器（純文字模式，靠右對齊，字級縮小） -->
          <div class="step-meta-row flex justify-end text-[11px]">
            <span class="step-timer-text font-mono text-xs text-surface-400 flex items-center" :class="{ 'timer-running text-primary font-semibold': step.status === 'PROCESSING' }">
              <i class="pi pi-clock timer-clock-icon mr-1 text-[11px]"></i>
              <span>{{ getStepDuration(step) }}</span>
            </span>
          </div>

          <!-- 第 3 行：詳細日誌訊息（預佔固定空間 2 行，防止高度上下跳動） -->
          <p class="step-log-message text-[11px] text-surface-400 m-0 line-clamp-2 min-h-[1.75rem] leading-tight">
            {{ step.log_message || getStepDefaultHint(step.step_name) }}
          </p>

          <!-- 第 4 行：進度條（常駐顯示槽位，PENDING 顯示 0%，防止動態增高） -->
          <div
            v-if="['HEURISTIC_CHECK', 'LLM_REASONING'].includes(step.step_name)"
            class="step-progress-wrapper flex flex-col gap-1 mt-1"
          >
            <div class="progress-bar-bg w-full h-1 bg-surface-800 rounded-full overflow-hidden">
              <div
                class="progress-bar-fill h-full bg-primary transition-all duration-300"
                :class="{ 'fill-pending bg-surface-700': step.status === 'PENDING' }"
                :style="{ width: getStepProgressPercent(step) + '%' }"
              ></div>
            </div>
            <span class="progress-text text-[10px] text-surface-400 text-right">{{ getStepProgressLabel(step) }}</span>
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

import { ref, computed, onMounted, onUnmounted } from 'vue'
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
 * 是否有任何步驟正在執行中（驅動計時器跳秒與高亮樣式）
 */
const isTaskActive = computed(() => {
  return (
    props.overallStatus === 'PROCESSING' ||
    props.overallStatus === 'PRE_ANALYZING' ||
    props.steps.some((s) => s.status === 'PROCESSING')
  )
})

/**
 * 取得單一步驟的實際耗時數值（秒數）
 */
const getStepDurationSeconds = (step: StepItem): number => {
  if (step.status === 'PENDING') {
    return 0
  }

  const startMs = step.started_at ? Date.parse(step.started_at) : null
  const endMs = step.completed_at ? Date.parse(step.completed_at) : null

  if (step.status === 'PROCESSING') {
    if (!startMs) return 0.01
    return Math.max(0.01, (nowTime.value - startMs) / 1000)
  }

  // COMPLETED, FAILED, SKIPPED: 固定在最終結束時間
  if (startMs && endMs) {
    return Math.max(0.01, (endMs - startMs) / 1000)
  } else if (startMs) {
    // 降級展示最後時間
    return 0.5
  }

  return 0
}

/**
 * 計算各步驟之耗時格式化字串
 */
const getStepDuration = (step: StepItem): string => {
  if (step.status === 'PENDING') {
    return '0.00s'
  }
  const startMs = step.started_at ? Date.parse(step.started_at) : null
  const endMs = step.completed_at ? Date.parse(step.completed_at) : null

  // 歷史舊任務若完全無時間記錄，顯示佔位符避免 0.00s 視覺破綻
  if (step.status === 'COMPLETED' && !startMs && !endMs) {
    return '—'
  }

  const sec = getStepDurationSeconds(step)
  return formatSeconds(sec)
}

/**
 * 計算整個任務之總耗時
 * - 嚴格為所有流程步驟實際耗時之累加總和，確保與各卡片時間自洽，杜絕總時間小於單一步驟或加總的異常
 */
const getTotalTaskDuration = (): string => {
  if (props.overallStatus === 'PENDING') {
    return '0.00s'
  }

  const totalSec = props.steps.reduce((sum, s) => sum + getStepDurationSeconds(s), 0)
  return formatSeconds(totalSec)
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
      return 'bg-green-500/20 text-green-400 border border-green-500/40'
    case 'PROCESSING':
      return 'bg-sky-500/20 text-sky-400 border border-sky-500/40 animate-pulse'
    case 'FAILED':
      return 'bg-red-500/20 text-red-400 border border-red-500/40'
    default:
      return 'bg-surface-800 text-surface-500 border border-surface-700'
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

const parseRuleProgress = (message?: string): { current: number; total: number; percent: number } | null => {
  if (!message) return null
  const match = message.match(/\[(\d+)\/(\d+)\]/)
  if (!match) return null
  const current = parseInt(match[1], 10)
  const total = parseInt(match[2], 10)
  if (isNaN(current) || isNaN(total) || total <= 0) return null
  const percent = Math.min(100, Math.max(1, Math.round((current / total) * 100)))
  return { current, total, percent }
}

const getStepProgressPercent = (step: StepItem): number => {
  if (step.status === 'COMPLETED') return 100
  if (step.status === 'PROCESSING') {
    const prog = parseRuleProgress(step.log_message)
    if (prog) return prog.percent
    return 40
  }
  return 0
}

const getStepProgressLabel = (step: StepItem): string => {
  if (step.status === 'COMPLETED') return '已處理完成: 100%'
  if (step.status === 'PROCESSING') {
    const prog = parseRuleProgress(step.log_message)
    if (prog) return `進行中: 第 ${prog.current}/${prog.total} 項 (${prog.percent}%)`
    return '正在分析比對項目中...'
  }
  return '等待啟動比對/推理 (0%)'
}
</script>
