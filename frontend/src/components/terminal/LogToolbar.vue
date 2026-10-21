<template>
  <div class="flex justify-between items-center px-3 py-1 min-h-[30px] bg-surface-header border-b border-surface-border text-vscode-textSecondary text-xs select-none">
    <div class="flex items-center gap-2">
      <div class="font-semibold text-vscode-textHeading flex items-center text-xs">
        <i class="pi pi-terminal text-primary mr-1.5 text-xs"></i>
        <span>即時執行終端日誌</span>
      </div>
      <span class="text-[11px] text-vscode-textMuted bg-surface-ground border border-surface-border px-1.5 py-0.2 rounded font-mono">
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
        v-tooltip.top="'切換是否顯示 Debug 等級日誌 (含子步驟與 LLM 查詢)'"
        class="terminal-btn debug-toggle-btn inline-flex items-center gap-1.5 px-2 py-0.5 text-[11px] rounded border transition-colors cursor-pointer"
        :class="showDebug ? 'bg-primary/15 border-primary/50 text-primary font-medium' : 'bg-surface-ground border-surface-border text-vscode-textMuted hover:text-vscode-textHeading'"
        @click="toggleDebug"
      >
        <i class="pi pi-code text-[10px]"></i>
        <span>Debug 模式</span>
        <span class="w-1.5 h-1.5 rounded-full inline-block transition-colors" :class="showDebug ? 'bg-primary' : 'bg-vscode-textMuted/40'"></span>
      </button>

      <!-- 自動捲動按鈕 -->
      <button
        type="button"
        v-tooltip.top="'切換日誌自動捲動至底部'"
        class="terminal-btn inline-flex items-center gap-1 px-2 py-0.5 text-[11px] rounded border transition-colors cursor-pointer"
        :class="autoScroll ? 'bg-primary/15 border-primary/50 text-primary font-medium' : 'bg-surface-ground border-surface-border text-vscode-textMuted hover:text-vscode-textHeading'"
        @click="toggleAutoScroll"
      >
        <i class="pi pi-arrow-down text-[10px]"></i>
        <span>自動捲動</span>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * @file LogToolbar.vue
 * @description 終端頂部工具列 (2026 雙主題版)，包含 Debug 開關、日誌計數與自動捲動控制
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
