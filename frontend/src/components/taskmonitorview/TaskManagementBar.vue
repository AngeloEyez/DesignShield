<template>
  <header class="task-management-bar flex justify-between items-center bg-surface-card rounded-md px-5 py-3.5 border border-surface-border shadow-sm flex-wrap gap-4">
    <div class="task-identity-col flex flex-col gap-1.5">
      <div class="title-with-badge flex items-center gap-3">
        <h2 class="view-title m-0 text-lg font-bold text-surface-900 dark:text-surface-0 flex items-center">
          <i class="pi pi-shield text-sky-400 mr-2"></i>
          {{ activeProjectName || '線路 DRC 任務檢測' }}
        </h2>
        <Tag :value="formatStatus(taskStatus)" :severity="getStatusSeverity(taskStatus)" />
      </div>
      <div class="task-id-row flex items-center gap-2 text-xs">
        <span class="label text-surface-400 font-medium">任務 ID:</span>
        <code class="task-id-code bg-surface-ground text-sky-400 px-2 py-0.5 rounded font-mono text-xs border border-surface-border">{{ currentTaskId || '未建立 (請先上傳設計檔案)' }}</code>
        <Button
          v-if="currentTaskId"
          icon="pi pi-copy"
          text
          rounded
          size="small"
          title="複製任務 ID"
          @click="$emit('copy-task-id')"
        />
      </div>
    </div>

    <div class="task-actions-col flex items-center gap-2 flex-wrap">
      <Button
        v-if="currentTaskId"
        label="刪除任務"
        icon="pi pi-trash"
        severity="danger"
        size="small"
        outlined
        :loading="isDeleting"
        @click="$emit('delete-task')"
      />
      <Button
        v-if="taskStatus === 'PROCESSING'"
        label="停止任務"
        icon="pi pi-stop-circle"
        severity="danger"
        size="small"
        :loading="isStopping"
        @click="$emit('stop-task')"
      />
      <Button
        label="重新開始新任務"
        icon="pi pi-plus"
        severity="secondary"
        size="small"
        @click="$emit('reset-task')"
      />
      <Button
        label="重新連線 SSE"
        icon="pi pi-refresh"
        severity="info"
        size="small"
        :disabled="!currentTaskId"
        @click="$emit('reconnect-sse')"
      />
    </div>
  </header>
</template>

<script setup lang="ts">
/**
 * @file TaskManagementBar.vue
 * @description TaskMonitorView 頂部任務控制與資訊管理列
 */

import Button from 'primevue/button'
import Tag from 'primevue/tag'

interface Props {
  activeProjectName?: string
  taskStatus?: string
  currentTaskId?: string
  isDeleting?: boolean
  isStopping?: boolean
}

withDefaults(defineProps<Props>(), {
  activeProjectName: '',
  taskStatus: 'PENDING',
  currentTaskId: '',
  isDeleting: false,
  isStopping: false,
})

defineEmits<{
  (e: 'copy-task-id'): void
  (e: 'delete-task'): void
  (e: 'stop-task'): void
  (e: 'reset-task'): void
  (e: 'reconnect-sse'): void
  (e: 'show-settings'): void
}>()

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
