<template>
  <div class="drawer-step-content flex flex-col gap-3">
    <!-- Step 4: 傳統演算法規則比對說明 -->
    <template v-if="stepName === 'HEURISTIC_CHECK'">
      <div class="info-box heuristic-box bg-surface-panel p-2.5 px-3 text-xs text-vscode-textMain border-l-2 border-l-primary leading-relaxed border border-surface-border rounded-r">
        <i class="pi pi-info-circle mr-1.5 text-primary"></i>
        傳統圖論演算法檢查包含：I2C 7-bit 地址唯一性、重設電路拓撲完整性、旁路電容就近佈局等確定性規則。
      </div>
    </template>

    <!-- Step 5: LLM 語意邏輯推理說明 -->
    <template v-else-if="stepName === 'LLM_REASONING'">
      <div class="info-box llm-box bg-surface-panel p-2.5 px-3 text-xs text-vscode-textMain border-l-2 border-l-primary leading-relaxed border border-surface-border rounded-r">
        <i class="pi pi-info-circle mr-1.5 text-primary"></i>
        本地大模型 (LLM) 推理結合電路拓撲上下文與 Datasheet 語意，驗證通訊介面工作模式合理性與引腳多工合理性。
      </div>
    </template>

    <!-- 步驟執行中 (PROCESSING) 專屬進度儀表板卡片 (完成後自動隱藏，僅保留該步驟結果詳情) -->
    <div
      v-if="stepItem?.status === 'PROCESSING'"
      class="step-progress-dashboard bg-surface-panel border border-primary/40 rounded p-3.5 flex flex-col gap-3 shadow-xs"
    >
      <!-- 進度儀表板標題列 -->
      <div class="progress-header flex items-center justify-between">
        <div class="flex items-center gap-2">
          <i class="pi pi-spin pi-spinner text-primary text-sm"></i>
          <span class="text-xs font-semibold text-vscode-textHeading">
            {{ stepName === 'HEURISTIC_CHECK' ? '傳統演算法比對進度' : 'LLM 語意推理進度' }}
          </span>
        </div>
        <span class="progress-counter-text font-mono text-xs font-medium text-primary">
          {{ progressDisplay }}
        </span>
      </div>

      <!-- PrimeVue 原生 ProgressBar -->
      <ProgressBar
        :value="progressPercent"
        :show-value="false"
        class="h-2 rounded overflow-hidden bg-surface-ground"
      />

      <!-- 目前確認中的規則資訊卡 -->
      <div
        v-if="currentRuleTitle"
        class="progress-rule-box bg-surface-ground/70 border border-surface-border rounded p-2 flex items-start gap-2 text-xs"
      >
        <i class="pi pi-search text-primary text-[11px] mt-0.5 shrink-0"></i>
        <div class="flex flex-col gap-0.5 min-w-0">
          <span class="text-[11px] text-vscode-textMuted">目前確認中規則:</span>
          <span class="current-rule-title font-medium text-vscode-textHeading break-all">
            {{ currentRuleTitle }}
          </span>
        </div>
      </div>
    </div>

    <!-- 狀態摘要卡片 (步驟完成後作為主要結果詳情展示，執行中則輔助呈現日誌) -->
    <div class="status-summary-card bg-surface-panel border border-surface-border rounded p-3 flex flex-col gap-1.5">
      <div class="summary-line flex items-center justify-between text-xs font-medium">
        <span class="text-vscode-textSecondary">
          {{ stepName === 'HEURISTIC_CHECK' ? '規則檢查狀態:' : 'LLM 推理狀態:' }}
        </span>
        <Tag
          :value="stepItem?.status || 'PENDING'"
          :severity="getStatusSeverity(stepItem?.status || 'PENDING')"
          class="text-[10px] px-1.5 py-0.2 rounded"
        />
      </div>
      <p class="summary-log text-xs text-vscode-textMuted m-0 break-all leading-normal font-mono">
        {{ stepItem?.log_message || (stepName === 'HEURISTIC_CHECK' ? '等待演算法規則比對...' : '等待呼叫本地大模型推理...') }}
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * @file StepCheckStatusDrawer.vue
 * @description TaskMonitorView 抽屜 Step 4（演算法比對）與 Step 5（LLM 語意推理）狀態卡片與動態進度儀表板 (雙主題適配)
 */

import { computed } from 'vue'
import Tag from 'primevue/tag'
import ProgressBar from 'primevue/progressbar'
import type { StepItem } from '@/types/task'

interface Props {
  stepName: 'HEURISTIC_CHECK' | 'LLM_REASONING'
  stepItem?: StepItem
}

const props = defineProps<Props>()

/**
 * 解析日誌中的 [X/Y] 計數與百分比
 */
const ruleProgress = computed(() => {
  const msg = props.stepItem?.log_message
  if (!msg) return null
  const match = msg.match(/\[(\d+)\/(\d+)\]/)
  if (!match) return null
  const current = parseInt(match[1], 10)
  const total = parseInt(match[2], 10)
  if (isNaN(current) || isNaN(total) || total <= 0) return null
  const percent = Math.min(100, Math.max(1, Math.round((current / total) * 100)))
  return { current, total, percent }
})

const progressPercent = computed(() => {
  if (props.stepItem?.status === 'COMPLETED') return 100
  if (ruleProgress.value) return ruleProgress.value.percent
  return props.stepItem?.status === 'PROCESSING' ? 15 : 0
})

const progressDisplay = computed(() => {
  if (ruleProgress.value) {
    return `第 ${ruleProgress.value.current} / ${ruleProgress.value.total} 項 (${ruleProgress.value.percent}%)`
  }
  return props.stepItem?.status === 'PROCESSING' ? '準備啟動比對...' : '等待中'
})

const currentRuleTitle = computed(() => {
  const msg = props.stepItem?.log_message
  if (!msg) return ''
  const match = msg.match(/「(.*?)」/)
  return match ? match[1] : ''
})

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
