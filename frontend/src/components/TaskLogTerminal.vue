<template>
  <div class="log-terminal-container">
    <!-- VS Code 終端頂部工具列 -->
    <LogToolbar
      :total-count="logs.length"
      :displayed-count="displayedLogs.length"
      :auto-scroll="autoScroll"
      :show-debug="showDebug"
      @update:auto-scroll="autoScroll = $event"
      @update:show-debug="showDebug = $event"
      @clear="clearLogs"
    />

    <!-- 即時日誌內容面板視窗 (VS Code 深色緊湊排版) -->
    <div ref="terminalBody" class="terminal-body">
      <div v-if="displayedLogs.length === 0" class="empty-logs">
        <i class="pi pi-spin pi-spinner mr-2" v-if="isWaiting"></i>
        <span>{{ emptyHint }}</span>
      </div>

      <LogLineItem
        v-for="log in displayedLogs"
        :key="log.id"
        :log="log"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * @file TaskLogTerminal.vue
 * @description VS Code 深色風格即時日誌視窗，支援 Debug 分級開關切換、雙標籤與詳細資料摺疊查看
 */

import { ref, computed, watch, nextTick } from 'vue'
import type { LogEntry } from '@/types/task'
import LogToolbar from './terminal/LogToolbar.vue'
import LogLineItem from './terminal/LogLineItem.vue'

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
// 面板預設顯示 info (即不顯示 debug)，可切換為 debug level。此切換開關只管 debug message 是否顯示。
const showDebug = ref<boolean>(false)

/**
 * 依 Debug 開關過濾顯示之日誌清單
 */
const displayedLogs = computed(() => {
  if (showDebug.value) {
    return props.logs
  }
  // 預設過濾掉 DEBUG 等級日誌，僅顯示 INFO, WARNING, ERROR 等
  return props.logs.filter((l) => (l.level || '').toUpperCase() !== 'DEBUG')
})

const emptyHint = computed(() => {
  if (props.logs.length === 0) {
    return '等待 SSE 即時日誌連線中...'
  }
  return '目前無符合層級之日誌 (開啟上方「Debug 模式」查看除錯細項)'
})

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

// 當顯示日誌更新時，自動捲動至底部
watch(
  () => displayedLogs.value.length,
  () => {
    if (autoScroll.value) {
      scrollToBottom()
    }
  }
)
</script>

<style scoped>
.log-terminal-container {
  display: flex;
  flex-direction: column;
  background-color: #1e1e1e;
  border-radius: 6px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25);
  border: 1px solid #333333;
  height: 100%;
  box-sizing: border-box;
  overflow: hidden;
}

.terminal-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  background-color: #1e1e1e;
  padding: 0.5rem 0.65rem;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
  font-size: 0.77rem;
  line-height: 1.45;
  color: #cccccc;
}

/* 自訂 VS Code 緊密捲軸樣式 */
.terminal-body::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

.terminal-body::-webkit-scrollbar-track {
  background: #1e1e1e;
}

.terminal-body::-webkit-scrollbar-thumb {
  background: #3c3c3c;
  border-radius: 4px;
}

.terminal-body::-webkit-scrollbar-thumb:hover {
  background: #555555;
}

.empty-logs {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 180px;
  color: #64748b;
  font-style: italic;
  font-size: 0.82rem;
}

.mr-2 {
  margin-right: 0.5rem;
}
</style>
