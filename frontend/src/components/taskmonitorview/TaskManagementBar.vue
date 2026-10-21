<template>
  <header class="task-management-bar flex justify-between items-center bg-surface-header px-3.5 py-1.5 border-b border-surface-border min-h-[36px] shrink-0 gap-3">
    <!-- 左側識別區：專案名稱 + 狀態 Tag + 任務 ID 極簡 Badge (單行同行) -->
    <div class="task-identity-col flex items-center gap-2.5 min-w-0">
      <div class="title-with-badge flex items-center gap-2 min-w-0">
        <h2 class="view-title m-0 text-xs font-semibold text-vscode-textHeading flex items-center truncate">
          <i class="pi pi-shield text-primary mr-1.5 text-xs shrink-0"></i>
          <span class="truncate">{{ activeProjectName || '線路 DRC 任務檢測' }}</span>
        </h2>
        <Tag :value="formatStatus(taskStatus)" :severity="getStatusSeverity(taskStatus)" class="text-[9px] px-1.5 py-0.2 rounded shrink-0" />
      </div>

      <!-- 任務 ID 極簡 Badge (單行同行，帶複製按鈕) -->
      <div v-if="currentTaskId" class="task-id-row flex items-center gap-1.5 text-[11px] font-mono text-vscode-textMuted bg-surface-ground px-2 py-0.5 rounded border border-surface-border shrink-0">
        <span class="label text-vscode-textMuted text-[10px]">ID:</span>
        <code class="task-id-code text-primary font-mono text-[11px] truncate max-w-[140px]" :title="currentTaskId">{{ currentTaskId }}</code>
        <button
          v-tooltip.bottom="'複製任務 ID'"
          class="copy-task-id-btn p-0.5 text-vscode-textMuted hover:text-vscode-textHeading bg-transparent border-0 cursor-pointer flex items-center justify-center transition-colors"
          title="複製任務 ID"
          @click="$emit('copy-task-id')"
        >
          <i class="pi pi-copy text-[10px]"></i>
        </button>
      </div>
    </div>

    <!-- 右側操作按鈕區 (極簡圖示與核心動作) -->
    <div class="task-actions-col flex items-center gap-1 shrink-0">
      <!-- 進行中狀態時的停止任務 -->
      <Button
        v-if="taskStatus === 'PROCESSING'"
        v-tooltip.bottom="'停止當前執行中的任務'"
        label="停止任務"
        icon="pi pi-stop-circle"
        text
        size="small"
        severity="danger"
        class="stop-task-btn text-[11px] py-0.5 px-1.5 h-6"
        :loading="isStopping"
        @click="$emit('stop-task')"
      />

      <!-- 核心動作：重新開始新任務 -->
      <Button
        v-tooltip.bottom="'建立新 DRC 檢測任務'"
        label="新任務"
        icon="pi pi-plus"
        text
        size="small"
        severity="secondary"
        class="reset-task-btn text-[11px] py-0.5 px-1.5 text-vscode-textMain hover:text-vscode-textHeading hover:bg-surface-hover h-6"
        @click="$emit('reset-task')"
      />

      <!-- 次要與危險操作收納：... (More Options) -->
      <Button
        v-tooltip.bottom="'更多操作'"
        icon="pi pi-ellipsis-v"
        text
        rounded
        size="small"
        severity="secondary"
        class="more-options-btn text-vscode-textMuted hover:text-vscode-textHeading hover:bg-surface-hover w-6 h-6 p-0"
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
 * @description TaskMonitorView 頂部任務控制與資訊管理列 (1px 邊界直連、雙主題適配)
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
    class: 'text-vscode-danger',
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
