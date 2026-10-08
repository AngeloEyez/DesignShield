<template>
  <header class="task-management-bar">
    <div class="task-identity-col">
      <div class="title-with-badge">
        <h2 class="view-title">
          <i class="pi pi-shield text-cyan mr-2"></i>
          {{ activeProjectName || '線路 DRC 任務檢測' }}
        </h2>
        <Tag :value="formatStatus(taskStatus)" :severity="getStatusSeverity(taskStatus)" />
      </div>
      <div class="task-id-row">
        <span class="label">任務 ID:</span>
        <code class="task-id-code">{{ currentTaskId || '未建立 (請先上傳設計檔案)' }}</code>
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

    <div class="task-actions-col">
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

<style scoped>
.task-management-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background-color: var(--vscode-bg-panel, #252526);
  border-radius: 6px;
  padding: 0.85rem 1.25rem;
  border: 1px solid var(--vscode-border, #333333);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.25);
  flex-wrap: wrap;
  gap: 1rem;
}

.task-identity-col {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.title-with-badge {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.view-title {
  margin: 0;
  font-size: 1.15rem;
  font-weight: 700;
  color: var(--vscode-text-heading, #ffffff);
  display: flex;
  align-items: center;
}

.text-cyan {
  color: var(--vscode-cyan, #4ec9b0);
}

.task-id-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.82rem;
}

.label {
  color: var(--vscode-text-muted, #858585);
  font-weight: 500;
}

.task-id-code {
  background-color: var(--vscode-bg-input, #1e1e1e);
  color: #38bdf8;
  padding: 0.15rem 0.5rem;
  border-radius: 4px;
  font-family: monospace;
  font-size: 0.8rem;
  border: 1px solid var(--vscode-border, #333333);
}

.task-actions-col {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.mr-2 {
  margin-right: 0.5rem;
}
</style>
