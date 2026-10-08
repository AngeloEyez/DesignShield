<template>
  <div class="flex flex-col bg-surface-950 rounded-md shadow-lg border border-surface-border h-full box-border overflow-hidden">
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
    <div ref="terminalBody" class="terminal-body flex-1 min-h-0 overflow-y-auto overflow-x-hidden bg-surface-950 p-2 font-mono text-xs leading-relaxed text-surface-200">
      <div v-if="displayedLogs.length === 0" class="flex items-center justify-center h-full min-h-[180px] text-surface-500 italic text-xs">
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
