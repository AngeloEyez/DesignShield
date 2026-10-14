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

import { ref, computed, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'
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

/** 待執行的自動捲動標記 (當容器處於隱藏狀態如 clientHeight === 0 時暫存) */
const pendingScrollToBottom = ref<boolean>(false)

/** 標記是否為系統程式碼觸發的捲動，避免捲動事件誤判為使用者手動滾動 */
let isProgrammaticScroll = false

/** 監控容器尺寸變更之 ResizeObserver 實例 */
let resizeObserver: ResizeObserver | null = null

const currentAutoScroll = computed(() => {
  return props.autoScroll !== undefined ? props.autoScroll : internalAutoScroll.value
})

const currentShowDebug = computed(() => {
  return props.showDebug !== undefined ? props.showDebug : internalShowDebug.value
})

/**
 * 處理自動捲動開關變更
 * @param {boolean} val 目標開關狀態
 */
const handleAutoScrollChange = (val: boolean) => {
  internalAutoScroll.value = val
  emit('update:autoScroll', val)
  if (val) {
    scrollToBottom()
  }
}

/**
 * 處理 Debug 顯示模式切換
 * @param {boolean} val 目標開關狀態
 */
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
 * @param {boolean} [smooth=false] 是否啟用平滑捲動 (預設 false 使用 instant 定位，避免大量日誌湧入時動畫卡頓)
 */
const scrollToBottom = (smooth = false) => {
  nextTick(() => {
    if (!terminalBody.value) return
    const el = terminalBody.value

    // 若容器處於不可見狀態 (例如父層收合在單行模式，clientHeight === 0)，暫存待補捲動標記
    if (el.clientHeight === 0) {
      pendingScrollToBottom.value = true
      return
    }

    pendingScrollToBottom.value = false
    isProgrammaticScroll = true

    if (smooth && typeof el.scrollTo === 'function') {
      el.scrollTo({
        top: el.scrollHeight,
        behavior: 'smooth',
      })
    } else {
      el.scrollTop = el.scrollHeight
    }
  })
}

/**
 * 監聽日誌容器捲動事件
 * 智慧判定使用者意圖：
 * 1. 若使用者主動向上捲動離開底部超過 30px，暫停自動捲動以利閱讀歷史紀錄
 * 2. 若使用者手動滾回最底部 (10px 內)，自動恢復自動捲動
 */
const handleScroll = () => {
  if (!terminalBody.value) return

  // 若為系統自動捲動所引發的捲動事件，直接重設標記並略過判定
  if (isProgrammaticScroll) {
    isProgrammaticScroll = false
    return
  }

  const { scrollTop, scrollHeight, clientHeight } = terminalBody.value
  const distanceFromBottom = scrollHeight - scrollTop - clientHeight

  if (distanceFromBottom > 30) {
    // 使用者往上滾動，關閉自動捲動
    if (currentAutoScroll.value) {
      internalAutoScroll.value = false
      emit('update:autoScroll', false)
    }
  } else if (distanceFromBottom <= 10) {
    // 使用者手動滾回底部，恢復自動捲動
    if (!currentAutoScroll.value) {
      internalAutoScroll.value = true
      emit('update:autoScroll', true)
    }
  }
}

/**
 * 初始化容器尺寸變更監聽器
 * 當面板從單行收合模式展開 (高度從 0 變為可見)、或單行展開詳細內容造成高度改變時，精確觸發自動捲動
 */
const initResizeObserver = () => {
  if (typeof ResizeObserver === 'undefined') return
  if (!terminalBody.value) return

  resizeObserver = new ResizeObserver((entries) => {
    for (const entry of entries) {
      const { height } = entry.contentRect
      if (height > 0) {
        if (pendingScrollToBottom.value || currentAutoScroll.value) {
          scrollToBottom()
        }
      }
    }
  })

  resizeObserver.observe(terminalBody.value)
}

// 當顯示日誌數量更新時，若開啟自動捲動則捲動至底部
watch(
  () => displayedLogs.value.length,
  () => {
    if (currentAutoScroll.value) {
      scrollToBottom()
    }
  }
)

// 當日誌原始清單長度變更時
watch(
  () => props.logs.length,
  () => {
    if (currentAutoScroll.value) {
      scrollToBottom()
    }
  }
)

// 當外部或內部切換開啟自動捲動時，立即觸發滾動至底部
watch(currentAutoScroll, (val) => {
  if (val) {
    scrollToBottom()
  }
})

// 當 Debug 顯示狀態切換時，若開啟自動捲動則校正捲動至底部
watch(currentShowDebug, () => {
  if (currentAutoScroll.value) {
    scrollToBottom()
  }
})

onMounted(() => {
  if (terminalBody.value) {
    terminalBody.value.addEventListener('scroll', handleScroll, { passive: true })
    initResizeObserver()
    if (currentAutoScroll.value) {
      scrollToBottom()
    }
  }
})

onBeforeUnmount(() => {
  if (terminalBody.value) {
    terminalBody.value.removeEventListener('scroll', handleScroll)
  }
  if (resizeObserver) {
    resizeObserver.disconnect()
    resizeObserver = null
  }
})

// 暴露 scrollToBottom 供父元件主動調用
defineExpose({
  scrollToBottom,
})
</script>
