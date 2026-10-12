<template>
  <div class="flex flex-col bg-transparent h-full box-border overflow-hidden">
    <!-- VS Code 終端頂部工具列 (當由父層自訂單一工具列時可隱藏) -->
    <LogToolbar
      v-if="!hideToolbar"
      :total-count="logs.length"
      :displayed-count="displayedLogs.length"
      :auto-scroll="currentAutoScroll"
      :show-debug="currentShowDebug"
      @update:auto-scroll="handleAutoScrollChange"
      @update:show-debug="handleShowDebugChange"
      @clear="clearLogs"
    />

    <!-- 即時日誌內容面板視窗 (無多餘內層邊框與特殊底色，直接融入工作台) -->
    <div ref="terminalBody" class="terminal-body flex-1 min-h-0 overflow-y-auto overflow-x-hidden bg-transparent p-2 font-mono text-xs text-surface-200">
      <div v-if="displayedLogs.length === 0" class="flex items-center justify-center h-full min-h-[160px] text-surface-500 italic text-xs">
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
 * @description VS Code 風格即時日誌視窗，支援 Debug 分級開關切換、雙標籤與詳細資料查看，無多餘底色容器
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
  /** 是否隱藏內置工具列 (由外部容器自訂單一工具列時開啟) */
  hideToolbar?: boolean
  /** 外部控制的 Debug 模式開關 (可選) */
  showDebug?: boolean
  /** 外部控制的自動捲動開關 (可選) */
  autoScroll?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  logs: () => [],
  isWaiting: false,
  hideToolbar: false,
  showDebug: undefined,
  autoScroll: undefined,
})

const emit = defineEmits<{
  (e: 'clear'): void
  (e: 'update:showDebug', val: boolean): void
  (e: 'update:autoScroll', val: boolean): void
}>()

const terminalBody = ref<HTMLElement | null>(null)
const internalAutoScroll = ref<boolean>(true)
const internalShowDebug = ref<boolean>(false)

const currentAutoScroll = computed(() => {
  return props.autoScroll !== undefined ? props.autoScroll : internalAutoScroll.value
})

const currentShowDebug = computed(() => {
  return props.showDebug !== undefined ? props.showDebug : internalShowDebug.value
})

const handleAutoScrollChange = (val: boolean) => {
  internalAutoScroll.value = val
  emit('update:autoScroll', val)
}

const handleShowDebugChange = (val: boolean) => {
  internalShowDebug.value = val
  emit('update:showDebug', val)
}

/**
 * 依 Debug 開關過濾顯示之日誌清單
 */
const displayedLogs = computed(() => {
  if (currentShowDebug.value) {
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
    if (currentAutoScroll.value) {
      scrollToBottom()
    }
  }
)
</script>
