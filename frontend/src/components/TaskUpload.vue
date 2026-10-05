<template>
  <div class="task-upload-card">
    <div class="upload-header">
      <h3 class="card-title">
        <i class="pi pi-cloud-upload mr-2"></i> 上傳線路圖檔 (Schematic Upload)
      </h3>
      <p class="card-desc">支援 Cadence OrCAD Capture XML 與包含 Netlist 之 .zip / .7z 壓縮檔</p>
    </div>

    <div class="form-group">
      <label class="form-label">專案名稱 (Project Name)</label>
      <input
        v-model="projectName"
        type="text"
        class="text-input"
        placeholder="例如: Server_Motherboard_RevA"
        :disabled="isUploading"
      />
    </div>

    <!-- 拖曳上傳區域 -->
    <div
      class="dropzone"
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
      <div v-if="!selectedFile" class="dropzone-placeholder">
        <i class="pi pi-file-arrow-up upload-icon"></i>
        <p class="dropzone-text">點擊或拖曳線路檔至此 (.zip, .7z, .xml)</p>
      </div>
      <div v-else class="selected-file-info">
        <i class="pi pi-file file-icon"></i>
        <div class="file-details">
          <span class="file-name">{{ selectedFile.name }}</span>
          <span class="file-size">{{ formatFileSize(selectedFile.size) }}</span>
        </div>
        <button class="remove-file-btn" @click.stop="removeFile">
          <i class="pi pi-times"></i>
        </button>
      </div>
    </div>

    <div class="upload-actions">
      <Button
        label="上傳並進行輕量預先分析"
        icon="pi pi-bolt"
        severity="primary"
        :loading="isUploading"
        :disabled="!selectedFile || !projectName.trim()"
        @click="submitUpload"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * @file TaskUpload.vue
 * @description 線路檔案上傳與專案資訊填寫元件
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
.task-upload-card {
  background: #ffffff;
  border-radius: 8px;
  padding: 1.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  border: 1px solid #e2e8f0;
}

.upload-header {
  margin-bottom: 1.25rem;
}

.card-title {
  margin: 0;
  font-size: 1.2rem;
  color: #0f172a;
  display: flex;
  align-items: center;
}

.card-desc {
  margin: 0.25rem 0 0 0;
  font-size: 0.85rem;
  color: #64748b;
}

.form-group {
  margin-bottom: 1rem;
}

.form-label {
  display: block;
  font-size: 0.85rem;
  font-weight: 600;
  color: #334155;
  margin-bottom: 0.35rem;
}

.text-input {
  width: 100%;
  padding: 0.5rem 0.75rem;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  font-size: 0.9rem;
  box-sizing: border-box;
  outline: none;
  transition: border-color 0.2s;
}

.text-input:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.dropzone {
  border: 2px dashed #cbd5e1;
  border-radius: 8px;
  padding: 1.75rem;
  text-align: center;
  cursor: pointer;
  background: #f8fafc;
  transition: all 0.2s;
}

.dropzone:hover,
.dropzone-active {
  border-color: #3b82f6;
  background: #eff6ff;
}

.has-file {
  border-style: solid;
  border-color: #93c5fd;
  background: #f0fdf4;
}

.hidden-file-input {
  display: none;
}

.upload-icon {
  font-size: 2.25rem;
  color: #64748b;
  margin-bottom: 0.5rem;
}

.dropzone-text {
  margin: 0;
  color: #475569;
  font-size: 0.9rem;
}

.selected-file-info {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.file-icon {
  font-size: 1.75rem;
  color: #10b981;
  margin-right: 0.75rem;
}

.file-details {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  flex: 1;
}

.file-name {
  font-weight: 600;
  color: #1e293b;
  font-size: 0.9rem;
}

.file-size {
  font-size: 0.75rem;
  color: #64748b;
}

.remove-file-btn {
  background: transparent;
  border: none;
  color: #94a3b8;
  cursor: pointer;
  padding: 0.4rem;
  border-radius: 4px;
}

.remove-file-btn:hover {
  color: #ef4444;
  background: #fee2e2;
}

.upload-actions {
  margin-top: 1.25rem;
  display: flex;
  justify-content: flex-end;
}
</style>
