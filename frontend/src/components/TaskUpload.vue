<template>
  <div class="task-upload-panel">
    <!-- VS Code 緊湊標題列 -->
    <div class="upload-panel-header">
      <div class="header-left">
        <i class="pi pi-file-import panel-icon text-cyan"></i>
        <span class="panel-title">上傳線路圖檔 (Schematic Upload)</span>
      </div>
      <div class="header-formats">
        <span class="format-badge">.zip</span>
        <span class="format-badge">.7z</span>
        <span class="format-badge">.xml</span>
      </div>
    </div>

    <!-- 緊湊表單主體 -->
    <div class="upload-panel-body">
      <!-- 專案名稱輸入列 -->
      <div class="form-row">
        <label class="compact-label">專案名稱</label>
        <div class="input-icon-wrapper">
          <i class="pi pi-folder input-icon"></i>
          <input
            v-model="projectName"
            type="text"
            class="text-input compact-text-input"
            placeholder="請輸入專案名稱 (例如: Carrier_Board_RevA)"
            :disabled="isUploading"
          />
        </div>
      </div>

      <!-- 緊湊型拖曳/選取檔案區域 -->
      <div
        class="compact-dropzone dropzone"
        :class="{ 'dropzone-active': isDragging, 'has-file': !!selectedFile }"
        @dragover.prevent="isDragging = true"
        @dragleave.prevent="isDragging = false"
        @drop.prevent="handleDrop"
        @click="triggerFileInput"
      >
        <input
          ref="fileInput"
          type="file"
          class="hidden-file-input"
          accept=".zip,.7z,.xml"
          @change="handleFileChange"
        />

        <div v-if="!selectedFile" class="dropzone-empty-content">
          <i class="pi pi-cloud-upload dropzone-icon"></i>
          <span class="dropzone-text">點擊或拖曳 Cadence OrCAD 電路圖檔案至此 (.zip, .7z, .xml)</span>
        </div>

        <div v-else class="selected-file-row">
          <div class="file-info-col">
            <i class="pi pi-file-check file-icon-ready"></i>
            <span class="file-name">{{ selectedFile.name }}</span>
            <span class="file-size">({{ formatFileSize(selectedFile.size) }})</span>
          </div>
          <button
            type="button"
            class="remove-file-btn"
            title="移除已選檔案"
            @click.stop="removeFile"
          >
            <i class="pi pi-times"></i>
          </button>
        </div>
      </div>

      <!-- 底部動作列 -->
      <div class="upload-action-row">
        <span class="upload-hint text-muted">
          <i class="pi pi-info-circle mr-1"></i>上傳後系統將自動啟動解壓縮、檔案結構預檢與圖譜特徵分析
        </span>
        <Button
          label="上傳並進行輕量預先分析"
          icon="pi pi-bolt"
          severity="primary"
          size="small"
          :loading="isUploading"
          :disabled="!selectedFile || !projectName.trim()"
          @click="submitUpload"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * @file TaskUpload.vue
 * @description 線路檔案上傳與專案資訊填寫元件 (VS Code 緊湊深色風格)
 */

import { ref } from 'vue'
import Button from 'primevue/button'

const emit = defineEmits<{
  (e: 'upload', payload: { file: File; projectName: string }): void
}>()

defineProps<{
  isUploading?: boolean
}>()

const projectName = ref<string>('My_Carrier_Board')
const selectedFile = ref<File | null>(null)
const isDragging = ref<boolean>(false)
const fileInput = ref<HTMLInputElement | null>(null)

/**
 * 觸發隱藏的檔案選擇器
 */
const triggerFileInput = () => {
  fileInput.value?.click()
}

/**
 * 處理原生檔案選擇變更
 * @param {Event} event Change 事件
 */
const handleFileChange = (event: Event) => {
  const target = event.target as HTMLInputElement
  if (target.files && target.files.length > 0) {
    selectedFile.value = target.files[0]
  }
}

/**
 * 處理拖曳放下檔案
 * @param {DragEvent} event Drop 事件
 */
const handleDrop = (event: DragEvent) => {
  isDragging.value = false
  if (event.dataTransfer && event.dataTransfer.files.length > 0) {
    selectedFile.value = event.dataTransfer.files[0]
  }
}

/**
 * 移除已選定的檔案
 */
const removeFile = () => {
  selectedFile.value = null
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

/**
 * 格式化檔案大小
 * @param {number} bytes 位元組數
 * @returns {string} 易讀字串
 */
const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`
}

/**
 * 提交上傳
 */
const submitUpload = () => {
  if (!selectedFile.value || !projectName.value.trim()) return
  emit('upload', {
    file: selectedFile.value,
    projectName: projectName.value.trim(),
  })
}
</script>

<style scoped>
.task-upload-panel {
  background-color: var(--vscode-bg-panel, #252526);
  border: 1px solid var(--vscode-border, #333333);
  border-radius: 6px;
  overflow: hidden;
}

/* 標題列 */
.upload-panel-header {
  background-color: var(--vscode-bg-header, #2d2d2d);
  border-bottom: 1px solid var(--vscode-border, #333333);
  padding: 0.5rem 0.85rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 0.45rem;
}

.panel-icon {
  font-size: 0.95rem;
}

.panel-title {
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--vscode-text-heading, #ffffff);
}

.header-formats {
  display: flex;
  gap: 0.35rem;
}

.format-badge {
  font-size: 0.7rem;
  font-family: monospace;
  background-color: var(--vscode-bg-base, #1e1e1e);
  color: var(--vscode-text-muted, #858585);
  border: 1px solid var(--vscode-border-light, #3c3c3c);
  padding: 0.1rem 0.35rem;
  border-radius: 3px;
}

/* 表單本體 */
.upload-panel-body {
  padding: 0.85rem;
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
}

.form-row {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.compact-label {
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--vscode-text-secondary, #999999);
}

.input-icon-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.input-icon {
  position: absolute;
  left: 0.65rem;
  color: var(--vscode-text-muted, #858585);
  font-size: 0.85rem;
  pointer-events: none;
}

.compact-text-input {
  width: 100%;
  padding: 0.45rem 0.65rem 0.45rem 2rem;
  background-color: var(--vscode-bg-base, #1e1e1e);
  border: 1px solid var(--vscode-border-light, #3c3c3c);
  border-radius: 4px;
  font-size: 0.82rem;
  color: var(--vscode-text-main, #cccccc);
  outline: none;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.compact-text-input:focus {
  border-color: var(--vscode-blue, #007acc);
  box-shadow: 0 0 0 1px var(--vscode-blue, #007acc);
}

.compact-text-input:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 緊湊型 Dropzone */
.compact-dropzone {
  background-color: var(--vscode-bg-base, #1e1e1e);
  border: 1px dashed var(--vscode-border-light, #3c3c3c);
  border-radius: 4px;
  padding: 0.75rem 1rem;
  cursor: pointer;
  transition: all 0.15s ease;
  min-height: 58px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.compact-dropzone:hover,
.compact-dropzone.dropzone-active {
  border-color: var(--vscode-blue, #007acc);
  background-color: #202b36;
}

.compact-dropzone.has-file {
  border-style: solid;
  border-color: #388a34;
  background-color: #172619;
}

.hidden-file-input {
  display: none;
}

.dropzone-empty-content {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}

.dropzone-icon {
  font-size: 1.25rem;
  color: var(--vscode-blue, #007acc);
}

.dropzone-text {
  font-size: 0.8rem;
  color: var(--vscode-text-muted, #858585);
}

/* 已選取檔案列 */
.selected-file-row {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.file-info-col {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.file-icon-ready {
  font-size: 1.1rem;
  color: #89d185;
}

.file-name {
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--vscode-text-heading, #ffffff);
}

.file-size {
  font-size: 0.75rem;
  color: var(--vscode-text-muted, #858585);
}

.remove-file-btn {
  background: transparent;
  border: none;
  color: var(--vscode-text-muted, #858585);
  cursor: pointer;
  padding: 0.25rem;
  border-radius: 3px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.12s ease;
}

.remove-file-btn:hover {
  color: var(--vscode-danger, #f14c4c);
  background-color: rgba(241, 76, 76, 0.15);
}

/* 底部動作列 */
.upload-action-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 0.25rem;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.upload-hint {
  font-size: 0.75rem;
  color: var(--vscode-text-muted, #858585);
  display: flex;
  align-items: center;
}

.text-cyan {
  color: #38bdf8;
}
</style>
