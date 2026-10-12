<template>
  <div class="flex justify-between items-center px-3 py-1 min-h-[30px] bg-[#252526] border-b border-[#333333] text-[#cccccc] text-xs select-none rounded-t-md">
    <div class="flex items-center gap-2">
      <div class="font-semibold text-white flex items-center text-xs">
        <i class="pi pi-terminal text-sky-400 mr-2"></i>
        <span>即時執行終端日誌 (Live Execution Log)</span>
      </div>
      <span class="text-[11px] text-[#858585] bg-[#1e1e1e] border border-[#333333] px-1.5 py-0.5 rounded-full font-mono">
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
        :class="showDebug ? 'bg-sky-500/20 border-sky-400 text-sky-300' : 'bg-[#1e1e1e] border-[#333333] text-[#858585] hover:text-white hover:border-[#555555]'"
        @click="toggleDebug"
        title="切換是否顯示 Debug 等級日誌 (含子步驟與 LLM 查詢)"
      >
        <i class="pi pi-code"></i>
        <span>Debug 模式</span>
        <span class="w-1.5 h-1.5 rounded-full inline-block transition-colors" :class="showDebug ? 'bg-sky-400 shadow-[0_0_5px_#38bdf8]' : 'bg-[#555555]'"></span>
      </button>

      <!-- 自動捲動按鈕 -->
      <button
        type="button"
        class="terminal-btn inline-flex items-center px-2 py-0.5 text-xs rounded border transition-colors cursor-pointer"
        :class="autoScroll ? 'bg-[#007acc]/20 border-[#007acc] text-white' : 'bg-[#1e1e1e] border-[#333333] text-[#858585] hover:text-white hover:border-[#555555]'"
        @click="toggleAutoScroll"
        title="切換日誌自動捲動至底部"
      >
        <i class="pi pi-arrow-down mr-1"></i> 自動捲動
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
}>()

const toggleDebug = () => {
  emit('update:showDebug', !props.showDebug)
}

const toggleAutoScroll = () => {
  emit('update:autoScroll', !props.autoScroll)
}
</script>
