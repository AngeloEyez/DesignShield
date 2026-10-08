<template>
  <div class="flex justify-between items-center px-3 py-1 min-h-[30px] bg-surface-900 border-b border-surface-border text-surface-300 text-xs select-none rounded-t-md">
    <div class="flex items-center gap-2">
      <div class="font-semibold text-surface-200 flex items-center text-xs">
        <i class="pi pi-terminal text-sky-400 mr-2"></i>
        <span>即時執行終端日誌 (Live Execution Log)</span>
      </div>
      <span class="text-[11px] text-surface-400 bg-surface-950 border border-surface-border px-1.5 py-0.5 rounded-full font-mono">
        {{ displayedCount }} 則日誌
        <template v-if="displayedCount !== totalCount">
          (已隱藏 {{ totalCount - displayedCount }} 則 Debug)
        </template>
      </span>
    </div>

    <div class="flex items-center gap-1.5">
      <!-- Debug 等級顯示切換開關 (預設關閉，此開關只管 debug message 是否顯示) -->
      <button
        type="button"
        class="terminal-btn debug-toggle-btn inline-flex items-center gap-1.5 px-2 py-0.5 text-xs rounded border transition-colors cursor-pointer"
        :class="showDebug ? 'bg-sky-950/70 border-sky-400 text-sky-300' : 'bg-surface-950 border-surface-border text-surface-400 hover:text-surface-100 hover:border-surface-600'"
        @click="toggleDebug"
        title="切換是否顯示 Debug 等級日誌 (含子步驟與 LLM 查詢)"
      >
        <i class="pi pi-code"></i>
        <span>Debug 模式</span>
        <span class="w-1.5 h-1.5 rounded-full inline-block transition-colors" :class="showDebug ? 'bg-sky-400 shadow-[0_0_5px_#38bdf8]' : 'bg-surface-600'"></span>
      </button>

      <!-- 自動捲動按鈕 -->
      <button
        type="button"
        class="terminal-btn inline-flex items-center px-2 py-0.5 text-xs rounded border transition-colors cursor-pointer"
        :class="autoScroll ? 'bg-primary/20 border-primary text-primary-contrast dark:text-primary-300' : 'bg-surface-950 border-surface-border text-surface-400 hover:text-surface-100 hover:border-surface-600'"
        @click="toggleAutoScroll"
        title="切換日誌自動捲動至底部"
      >
        <i class="pi pi-arrow-down mr-1"></i> 自動捲動
      </button>

      <!-- 清空按鈕 -->
      <button
        type="button"
        class="terminal-btn clear-btn inline-flex items-center px-2 py-0.5 text-xs rounded border border-surface-border bg-surface-950 text-surface-400 hover:text-red-400 hover:border-red-400 transition-colors cursor-pointer"
        @click="handleClear"
        title="清空目前終端日誌"
      >
        <i class="pi pi-trash mr-1"></i> 清空
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * @file LogToolbar.vue
 * @description VS Code 風格終端頂部工具列，包含 Debug 開關、日誌計數、自動捲動與清空控制
 */

interface Props {
  totalCount: number
  displayedCount: number
  autoScroll: boolean
  showDebug: boolean
}

const props = defineProps<Props>()

const emit = defineEmits<{
  (e: 'update:autoScroll', val: boolean): void
  (e: 'update:showDebug', val: boolean): void
  (e: 'clear'): void
}>()

const toggleDebug = () => {
  emit('update:showDebug', !props.showDebug)
}

const toggleAutoScroll = () => {
  emit('update:autoScroll', !props.autoScroll)
}

const handleClear = () => {
  emit('clear')
}
</script>
