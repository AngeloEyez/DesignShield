<template>
  <div class="drawer-step-content flex flex-col gap-4">
    <!-- Step 4: 傳統演算法規則比對 -->
    <template v-if="stepName === 'HEURISTIC_CHECK'">
      <div class="info-box heuristic-box bg-surface-card p-3 px-4 text-xs text-surface-200 rounded-r border-l-4 border-l-blue-500 leading-relaxed">
        <i class="pi pi-info-circle mr-2 text-sky-400"></i>
        傳統圖論演算法檢查包含：I2C 7-bit 地址唯一性、重設電路拓撲完整性、旁路電容就近佈局等確定性規則。
      </div>
      <h4 class="content-subtitle text-xs font-semibold text-surface-900 dark:text-surface-0 m-0">比對進度與檢查項目</h4>
      <div class="status-summary-card bg-surface-card border border-surface-border rounded-md p-3.5 flex flex-col gap-2">
        <div class="summary-line flex items-center justify-between text-xs font-semibold">
          <span class="text-surface-300">規則檢查狀態:</span>
          <Tag :value="stepItem?.status || 'PENDING'" :severity="getStatusSeverity(stepItem?.status || 'PENDING')" />
        </div>
        <p class="summary-log text-xs text-surface-400 m-0 break-all leading-normal">
          {{ stepItem?.log_message || '等待演算法規則比對...' }}
        </p>
      </div>
    </template>

    <!-- Step 5: LLM 語意邏輯推理 -->
    <template v-else-if="stepName === 'LLM_REASONING'">
      <div class="info-box llm-box bg-surface-card p-3 px-4 text-xs text-surface-200 rounded-r border-l-4 border-l-purple-400 leading-relaxed">
        <i class="pi pi-info-circle mr-2 text-purple-400"></i>
        本地大模型 (LLM) 推理結合電路拓撲上下文與 Datasheet 語意，驗證通訊介面工作模式合理性與引腳多工合理性。
      </div>
      <h4 class="content-subtitle text-xs font-semibold text-surface-900 dark:text-surface-0 m-0">語意邏輯推理狀態</h4>
      <div class="status-summary-card bg-surface-card border border-surface-border rounded-md p-3.5 flex flex-col gap-2">
        <div class="summary-line flex items-center justify-between text-xs font-semibold">
          <span class="text-surface-300">LLM 推理狀態:</span>
          <Tag :value="stepItem?.status || 'PENDING'" :severity="getStatusSeverity(stepItem?.status || 'PENDING')" />
        </div>
        <p class="summary-log text-xs text-surface-400 m-0 break-all leading-normal">
          {{ stepItem?.log_message || '等待呼叫本地大模型推理...' }}
        </p>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
/**
 * @file StepCheckStatusDrawer.vue
 * @description TaskMonitorView 抽屜 Step 4（演算法比對）與 Step 5（LLM 語意推理）狀態卡片
 */

import Tag from 'primevue/tag'
import type { StepItem } from '@/types/task'

interface Props {
  stepName: 'HEURISTIC_CHECK' | 'LLM_REASONING'
  stepItem?: StepItem
}

defineProps<Props>()

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
