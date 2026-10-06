<template>
  <div class="terminal-toolbar">
    <div class="toolbar-left">
      <div class="terminal-title">
        <i class="pi pi-terminal text-cyan mr-2"></i>
        <span>即時執行終端日誌 (Live Execution Log)</span>
      </div>
      <span class="log-count">
        {{ displayedCount }} 則日誌
        <template v-if="displayedCount !== totalCount">
          (已隱藏 {{ totalCount - displayedCount }} 則 Debug)
        </template>
      </span>
    </div>

    <div class="toolbar-right">
      <!-- Debug 等級顯示切換開關 (預設關閉，此開關只管 debug message 是否顯示) -->
      <button
        type="button"
        class="terminal-btn debug-toggle-btn"
        :class="{ active: showDebug }"
        @click="toggleDebug"
        title="切換是否顯示 Debug 等級日誌 (含子步驟與 LLM 查詢)"
      >
        <i class="pi pi-code mr-1"></i>
        <span>Debug 模式</span>
        <span class="toggle-indicator" :class="{ 'is-on': showDebug }"></span>
      </button>

      <!-- 自動捲動按鈕 -->
      <button
        type="button"
        class="terminal-btn"
        :class="{ active: autoScroll }"
        @click="toggleAutoScroll"
        title="切換日誌自動捲動至底部"
      >
        <i class="pi pi-arrow-down mr-1"></i> 自動捲動
      </button>

      <!-- 清空按鈕 -->
      <button
        type="button"
        class="terminal-btn clear-btn"
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

<style scoped>
.terminal-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.45rem 0.85rem;
  background-color: #252526;
  border-bottom: 1px solid #333333;
  color: #cccccc;
  font-size: 0.8rem;
  user-select: none;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 0.65rem;
}

.terminal-title {
  font-weight: 600;
  color: #e2e8f0;
  display: flex;
  align-items: center;
  font-size: 0.82rem;
}

.text-cyan {
  color: #38bdf8;
}

.log-count {
  font-size: 0.72rem;
  color: #94a3b8;
  background-color: #1e1e1e;
  border: 1px solid #333333;
  padding: 0.15rem 0.45rem;
  border-radius: 10px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.terminal-btn {
  background: #1e1e1e;
  border: 1px solid #3c3c3c;
  color: #cccccc;
  font-size: 0.75rem;
  padding: 0.25rem 0.6rem;
  border-radius: 4px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  transition: all 0.15s ease;
  font-weight: 500;
  font-family: inherit;
}

.terminal-btn:hover {
  background: #2d2d2d;
  border-color: #555555;
  color: #ffffff;
}

.terminal-btn.active {
  background: #094771;
  border-color: #007acc;
  color: #ffffff;
}

.debug-toggle-btn {
  gap: 0.35rem;
}

.debug-toggle-btn.active {
  background: #1e3a5f;
  border-color: #38bdf8;
  color: #38bdf8;
}

.toggle-indicator {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #555555;
  display: inline-block;
  transition: background-color 0.2s;
}

.toggle-indicator.is-on {
  background: #38bdf8;
  box-shadow: 0 0 5px #38bdf8;
}

.clear-btn:hover {
  border-color: #f87171;
  color: #f87171;
}

.mr-1 {
  margin-right: 0.25rem;
}

.mr-2 {
  margin-right: 0.5rem;
}
</style>
