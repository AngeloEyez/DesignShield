<template>
  <header class="task-management-bar flex justify-between items-center bg-[#252526] rounded-md px-3 py-1 border border-[#333333] shadow-sm min-h-[32px] shrink-0 gap-3">
    <!-- 左側識別區：專案名稱 + 狀態 Tag + 任務 ID 極簡 Badge (單行同行) -->
    <div class="task-identity-col flex items-center gap-2.5 min-w-0">
      <div class="title-with-badge flex items-center gap-2 min-w-0">
        <h2 class="view-title m-0 text-xs font-bold text-white flex items-center truncate">
          <i class="pi pi-shield text-sky-400 mr-1.5 text-xs shrink-0"></i>
          <span class="truncate">{{ activeProjectName || '線路 DRC 任務檢測' }}</span>
        </h2>
        <Tag :value="formatStatus(taskStatus)" :severity="getStatusSeverity(taskStatus)" class="text-[9px] px-1 py-0.2 rounded shrink-0" />
      </div>

      <!-- 任務 ID 極簡 Badge (單行同行，帶複製按鈕) -->
      <div v-if="currentTaskId" class="task-id-row flex items-center gap-1.5 text-[11px] font-mono text-surface-400 bg-[#1e1e1e] px-2 py-0.5 rounded border border-[#333333] shrink-0">
        <span class="label text-[#858585] text-[10px]">ID:</span>
        <code class="task-id-code text-sky-400 font-mono text-[11px] truncate max-w-[140px]" :title="currentTaskId">{{ currentTaskId }}</code>
        <button
          class="copy-task-id-btn p-0.5 text-surface-400 hover:text-white bg-transparent border-0 cursor-pointer flex items-center justify-center transition-colors"
          title="複製任務 ID"
          @click="$emit('copy-task-id')"
        >
          <i class="pi pi-copy text-[10px]"></i>
        </button>
      </div>
    </div>

    <!-- 右側操作按鈕區 (極簡尺寸) -->
    <div class="task-actions-col flex items-center gap-1 shrink-0">
      <!-- 進行中狀態時的停止任務 (幽靈低調紅文字) -->
      <Button
        v-if="taskStatus === 'PROCESSING'"
        label="停止任務"
        icon="pi pi-stop-circle"
        text
        size="small"
        severity="danger"
        class="stop-task-btn text-[11px] py-0.5 px-1.5 text-rose-400 hover:text-rose-300 hover:bg-rose-500/10 h-6"
        :loading="isStopping"
        @click="$emit('stop-task')"
      />

      <!-- 核心主要動作：重新開始新任務 (幽靈文字按鈕) -->
      <Button
        label="新任務"
        icon="pi pi-plus"
        text
        size="small"
        severity="secondary"
        class="reset-task-btn text-[11px] py-0.5 px-1.5 text-[var(--vscode-text-main,#ccc)] hover:text-white hover:bg-[var(--vscode-bg-hover,#2a2d2e)] h-6"
        @click="$emit('reset-task')"
      />

      <!-- 次要與危險操作收納：... (More Options) 幽靈按鈕與選單 -->
      <Button
        icon="pi pi-ellipsis-v"
        text
        rounded
        size="small"
        severity="secondary"
        class="more-options-btn text-[var(--vscode-text-muted,#858585)] hover:text-white hover:bg-[var(--vscode-bg-hover,#2a2d2e)] w-6 h-6 p-0"
        title="更多操作"
        aria-haspopup="true"
        aria-controls="task_more_menu"
        @click="toggleMoreMenu"
      />
      <Menu id="task_more_menu" ref="moreMenuRef" :model="moreMenuItems" :popup="true" class="text-xs" />
    </div>
  </header>
</template>

<script setup lang="ts">
/**
 * @file TaskManagementBar.vue
 * @description TaskMonitorView 頂部任務控制與資訊管理列
 */

import { ref, computed } from 'vue'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import Menu from 'primevue/menu'

interface Props {
  activeProjectName?: string
  taskStatus?: string
  currentTaskId?: string
  isDeleting?: boolean
  isStopping?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  activeProjectName: '',
  taskStatus: 'PENDING',
  currentTaskId: '',
  isDeleting: false,
  isStopping: false,
})

const emit = defineEmits<{
  (e: 'copy-task-id'): void
  (e: 'delete-task'): void
  (e: 'stop-task'): void
  (e: 'reset-task'): void
  (e: 'reconnect-sse'): void
  (e: 'show-settings'): void
}>()

const moreMenuRef = ref()

const toggleMoreMenu = (event: Event) => {
  moreMenuRef.value?.toggle(event)
}

const moreMenuItems = computed(() => [
  {
    label: '重新連線 SSE',
    icon: 'pi pi-refresh',
    disabled: !props.currentTaskId,
    command: () => emit('reconnect-sse'),
  },
  {
    separator: true,
  },
  {
    label: '刪除當前任務',
    icon: 'pi pi-trash',
    class: 'text-rose-400 hover:text-rose-300',
    disabled: !props.currentTaskId || props.isDeleting,
    command: () => emit('delete-task'),
  },
])

const formatStatus = (status: string): string => {
  switch (status) {
    case 'COMPLETED':
      return '檢測完成'
    case 'PROCESSING':
      return '正在檢測'
    case 'PRE_ANALYZING':
      return '正在預先分析'
    case 'FAILED':
      return '檢測失敗'
    case 'READY_FOR_RUN':
      return '等待確認規則'
    case 'CANCELLED':
      return '已中止'
    default:
      return '待處理'
  }
}

const getStatusSeverity = (status: string): 'success' | 'info' | 'warn' | 'danger' | 'secondary' => {
  switch (status) {
    case 'COMPLETED':
      return 'success'
    case 'PROCESSING':
    case 'PRE_ANALYZING':
      return 'info'
    case 'READY_FOR_RUN':
      return 'warn'
    case 'FAILED':
      return 'danger'
    default:
      return 'secondary'
  }
}
</script>
