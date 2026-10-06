<template>
  <div class="log-terminal-container">
    <div class="terminal-header">
      <div class="header-left">
        <h3 class="section-title">
          <i class="pi pi-align-left mr-2"></i>
          即時執行日誌 (Live Execution Log)
        </h3>
      </div>
      <div class="header-right">
        <span class="log-count">{{ logs.length }} 則日誌</span>
        <button
          type="button"
          class="terminal-btn"
          @click="toggleAutoScroll"
          :class="{ active: autoScroll }"
          title="切換日誌自動捲動"
        >
          <i class="pi pi-arrow-down mr-1"></i> 自動捲動
        </button>
        <button
          type="button"
          class="terminal-btn"
          @click="clearLogs"
          title="清空目前日誌"
        >
          <i class="pi pi-trash mr-1"></i> 清空
        </button>
      </div>
    </div>

    <!-- 即時日誌內容面板視窗 -->
    <div ref="terminalBody" class="terminal-body">
      <div v-if="logs.length === 0" class="empty-logs">
        <i class="pi pi-spin pi-spinner mr-2" v-if="isWaiting"></i>
        <span>等待 SSE 即時日誌連線中...</span>
      </div>

      <div
        v-for="log in logs"
        :key="log.id"
        class="log-line"
      >
        <span class="log-timestamp">[{{ log.timestamp }}]</span>
        <span class="log-step" :class="getStepClass(log.step_name)">
          [{{ log.step_name }}]
        </span>
        <span class="log-status" :class="getStatusClass(log.status)">
          {{ log.status }}
        </span>
        <span class="log-message">{{ log.message }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * @file TaskLogTerminal.vue
 * @description 一致面板風格即時日誌視窗，高度自適應左側工作歷程，支援 SSE 串流渲染與自動捲動
 */

import { ref, watch, nextTick } from 'vue'
import type { LogEntry, StepState } from '@/types/task'

interface Props {
  /** 即時日誌清單 */
  logs: LogEntry[]
  /** 是否處於等待中 */
  isWaiting?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  logs: () => [],
  isWaiting: false,
})

const emit = defineEmits<{
  (e: 'clear'): void
}>()

const terminalBody = ref<HTMLElement | null>(null)
const autoScroll = ref<boolean>(true)

/**
 * 切換自動捲動狀態
 */
const toggleAutoScroll = () => {
  autoScroll.value = !autoScroll.value
  if (autoScroll.value) {
    scrollToBottom()
  }
}

/**
 * 清空日誌視窗
 */
const clearLogs = () => {
  emit('clear')
}

/**
 * 捲動至日誌面板底部
 */
const scrollToBottom = () => {
  nextTick(() => {
    if (terminalBody.value) {
      terminalBody.value.scrollTop = terminalBody.value.scrollHeight
    }
  })
}

// 當日誌更新時，自動捲動至底部
watch(
  () => props.logs.length,
  () => {
    if (autoScroll.value) {
      scrollToBottom()
    }
  }
)

/**
 * 依步驟名稱取得 CSS class 標籤顏色
 * @param {string} stepName 步驟名稱
 * @returns {string} class 名稱
 */
const getStepClass = (stepName: string): string => {
  if (stepName.includes('UNPACK')) return 'step-unpack'
  if (stepName.includes('PARSE')) return 'step-parse'
  if (stepName.includes('HEURISTIC')) return 'step-heuristic'
  if (stepName.includes('LLM')) return 'step-llm'
  return 'step-report'
}

/**
 * 依狀態取得文字顏色
 * @param {StepState} status 狀態字串
 * @returns {string} class 名稱
 */
const getStatusClass = (status: StepState): string => {
  switch (status) {
    case 'COMPLETED':
      return 'status-completed'
    case 'PROCESSING':
      return 'status-processing'
    case 'FAILED':
      return 'status-failed'
    default:
      return 'status-pending'
  }
}
</script>

<style scoped>
.log-terminal-container {
  display: flex;
  flex-direction: column;
  background-color: #ffffff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  border: 1px solid #e2e8f0;
  padding: 1.5rem;
  height: 100%;
  box-sizing: border-box;
}

.terminal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  border-bottom: 1px solid #f1f5f9;
  padding-bottom: 0.75rem;
}

.header-left {
  display: flex;
  align-items: center;
}

.section-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: #1e293b;
  margin: 0;
  display: flex;
  align-items: center;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}

.log-count {
  font-size: 0.8rem;
  color: #64748b;
  background: #f1f5f9;
  padding: 0.2rem 0.5rem;
  border-radius: 9999px;
  font-weight: 500;
}

.terminal-btn {
  background: #ffffff;
  border: 1px solid #cbd5e1;
  color: #475569;
  font-size: 0.8rem;
  padding: 0.35rem 0.65rem;
  border-radius: 6px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  transition: all 0.2s;
  font-weight: 500;
}

.terminal-btn:hover {
  background: #f8fafc;
  border-color: #94a3b8;
  color: #1e293b;
}

.terminal-btn.active {
  background: #eff6ff;
  border-color: #3b82f6;
  color: #2563eb;
  font-weight: 600;
}

.terminal-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  background-color: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 0.85rem 1rem;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
  font-size: 0.85rem;
  line-height: 1.6;
}

.empty-logs {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 200px;
  color: #94a3b8;
  font-style: italic;
  font-size: 0.9rem;
}

.log-line {
  display: flex;
  gap: 0.5rem;
  align-items: baseline;
  word-break: break-word;
  margin-bottom: 0.35rem;
  padding: 0.15rem 0.35rem;
  border-radius: 4px;
  transition: background-color 0.12s;
}

.log-line:hover {
  background-color: #f1f5f9;
}

.log-timestamp {
  color: #94a3b8;
  font-size: 0.78rem;
  flex-shrink: 0;
  font-variant-numeric: tabular-nums;
}

.log-step {
  font-weight: 600;
  font-size: 0.78rem;
  flex-shrink: 0;
}

.step-unpack {
  color: #0284c7;
  background: #e0f2fe;
  padding: 0.1rem 0.35rem;
  border-radius: 4px;
}

.step-parse {
  color: #7c3aed;
  background: #ede9fe;
  padding: 0.1rem 0.35rem;
  border-radius: 4px;
}

.step-heuristic {
  color: #b45309;
  background: #fef3c7;
  padding: 0.1rem 0.35rem;
  border-radius: 4px;
}

.step-llm {
  color: #be185d;
  background: #fce7f3;
  padding: 0.1rem 0.35rem;
  border-radius: 4px;
}

.step-report {
  color: #047857;
  background: #d1fae5;
  padding: 0.1rem 0.35rem;
  border-radius: 4px;
}

.log-status {
  padding: 0.1rem 0.35rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
  flex-shrink: 0;
}

.status-completed {
  background: #dcfce7;
  color: #15803d;
}

.status-processing {
  background: #dbeafe;
  color: #1d4ed8;
}

.status-failed {
  background: #fee2e2;
  color: #b91c1c;
}

.status-pending {
  background: #f1f5f9;
  color: #64748b;
}

.log-message {
  color: #1e293b;
  font-weight: 400;
}

.mr-1 {
  margin-right: 0.25rem;
}

.mr-2 {
  margin-right: 0.5rem;
}
</style>
