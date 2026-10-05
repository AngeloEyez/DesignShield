<template>
  <div class="log-terminal-container">
    <div class="terminal-header">
      <div class="header-left">
        <span class="terminal-dots">
          <span class="dot dot-red"></span>
          <span class="dot dot-yellow"></span>
          <span class="dot dot-green"></span>
        </span>
        <span class="terminal-title">
          <i class="pi pi-code mr-1"></i> 即時執行日誌終端 (Live Execution Log Console)
        </span>
      </div>
      <div class="header-right">
        <span class="log-count">{{ logs.length }} 則日誌</span>
        <button class="terminal-btn" @click="toggleAutoScroll" :class="{ active: autoScroll }">
          <i class="pi pi-arrow-down mr-1"></i> 自動捲動
        </button>
        <button class="terminal-btn" @click="clearLogs">
          <i class="pi pi-trash mr-1"></i> 清空
        </button>
      </div>
    </div>

    <!-- 終端日誌內容視窗 -->
    <div ref="terminalBody" class="terminal-body">
      <div v-if="logs.length === 0" class="empty-logs">
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
 * @description 黑色終端風格即時日誌視窗，支援 SSE 串流渲染與自動捲動
 */

import { ref, watch, nextTick } from 'vue'
import type { LogEntry, StepState } from '@/types/task'

interface Props {
  /** 即時日誌清單 */
  logs: LogEntry[]
}

const props = withDefaults(defineProps<Props>(), {
  logs: () => [],
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
 * 捲動至終端機底部
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
  background-color: #0f172a;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
  border: 1px solid #1e293b;
  height: 400px;
}

.terminal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background-color: #1e293b;
  padding: 0.6rem 1rem;
  border-bottom: 1px solid #334155;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.terminal-dots {
  display: flex;
  gap: 0.4rem;
}

.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.dot-red {
  background-color: #ef4444;
}

.dot-yellow {
  background-color: #f59e0b;
}

.dot-green {
  background-color: #10b981;
}

.terminal-title {
  color: #e2e8f0;
  font-size: 0.875rem;
  font-weight: 500;
  font-family: monospace;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.log-count {
  font-size: 0.75rem;
  color: #94a3b8;
  margin-right: 0.5rem;
}

.terminal-btn {
  background: transparent;
  border: 1px solid #475569;
  color: #cbd5e1;
  font-size: 0.75rem;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  transition: all 0.2s;
}

.terminal-btn:hover {
  background: #334155;
  color: #ffffff;
}

.terminal-btn.active {
  background: #2563eb;
  border-color: #3b82f6;
  color: #ffffff;
}

.terminal-body {
  flex: 1;
  overflow-y: auto;
  padding: 0.75rem 1rem;
  font-family: 'JetBrains Mono', 'Fira Code', Consolas, monospace;
  font-size: 0.85rem;
  line-height: 1.6;
}

.empty-logs {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #64748b;
  font-style: italic;
}

.log-line {
  display: flex;
  gap: 0.5rem;
  align-items: baseline;
  word-break: break-word;
  margin-bottom: 0.25rem;
}

.log-timestamp {
  color: #64748b;
  flex-shrink: 0;
}

.log-step {
  font-weight: 600;
  flex-shrink: 0;
}

.step-unpack {
  color: #38bdf8;
}

.step-parse {
  color: #a78bfa;
}

.step-heuristic {
  color: #fbbf24;
}

.step-llm {
  color: #f472b6;
}

.step-report {
  color: #34d399;
}

.log-status {
  padding: 0 0.35rem;
  border-radius: 3px;
  font-size: 0.75rem;
  font-weight: 600;
  flex-shrink: 0;
}

.status-completed {
  background: rgba(16, 185, 129, 0.2);
  color: #34d399;
}

.status-processing {
  background: rgba(59, 130, 246, 0.2);
  color: #60a5fa;
}

.status-failed {
  background: rgba(239, 68, 68, 0.2);
  color: #f87171;
}

.status-pending {
  background: rgba(148, 163, 184, 0.2);
  color: #94a3b8;
}

.log-message {
  color: #f1f5f9;
}
</style>
