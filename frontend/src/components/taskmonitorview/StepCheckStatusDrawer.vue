<template>
  <div class="drawer-step-content">
    <!-- Step 4: 傳統演算法規則比對 -->
    <template v-if="stepName === 'HEURISTIC_CHECK'">
      <div class="info-box heuristic-box">
        <i class="pi pi-info-circle mr-2 text-blue"></i>
        傳統圖論演算法檢查包含：I2C 7-bit 地址唯一性、重設電路拓撲完整性、旁路電容就近佈局等確定性規則。
      </div>
      <h4 class="content-subtitle">比對進度與檢查項目</h4>
      <div class="status-summary-card">
        <div class="summary-line">
          <span>規則檢查狀態:</span>
          <Tag :value="stepItem?.status || 'PENDING'" :severity="getStatusSeverity(stepItem?.status || 'PENDING')" />
        </div>
        <p class="summary-log">
          {{ stepItem?.log_message || '等待演算法規則比對...' }}
        </p>
      </div>
    </template>

    <!-- Step 5: LLM 語意邏輯推理 -->
    <template v-else-if="stepName === 'LLM_REASONING'">
      <div class="info-box llm-box">
        <i class="pi pi-info-circle mr-2 text-purple"></i>
        本地大模型 (LLM) 推理結合電路拓撲上下文與 Datasheet 語意，驗證通訊介面工作模式合理性與引腳多工合理性。
      </div>
      <h4 class="content-subtitle">語意邏輯推理狀態</h4>
      <div class="status-summary-card">
        <div class="summary-line">
          <span>LLM 推理狀態:</span>
          <Tag :value="stepItem?.status || 'PENDING'" :severity="getStatusSeverity(stepItem?.status || 'PENDING')" />
        </div>
        <p class="summary-log">
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

<style scoped>
.drawer-step-content {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.info-box {
  background-color: var(--vscode-bg-panel, #252526);
  padding: 0.75rem 1rem;
  font-size: 0.82rem;
  color: var(--vscode-text-main, #cccccc);
  border-radius: 0 4px 4px 0;
  line-height: 1.5;
}

.heuristic-box {
  border-left: 3px solid var(--vscode-blue, #007acc);
}

.llm-box {
  border-left: 3px solid #c586c0;
}

.text-blue {
  color: #4fc1ff;
}

.text-purple {
  color: #c586c0;
}

.content-subtitle {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--vscode-text-heading, #ffffff);
  margin: 0.25rem 0 0 0;
}

.status-summary-card {
  background-color: var(--vscode-bg-panel, #252526);
  border: 1px solid var(--vscode-border, #333333);
  border-radius: 6px;
  padding: 0.85rem;
}

.summary-line {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.45rem;
  font-size: 0.82rem;
  font-weight: 600;
}

.summary-log {
  font-size: 0.78rem;
  color: var(--vscode-text-muted, #858585);
  margin: 0;
  word-break: break-all;
}
</style>
