<template>
  <div class="task-upload-panel bg-[#252526] border border-[#333333] rounded-md overflow-hidden shadow-sm">
    <!-- VS Code 緊湊標題列 -->
    <div class="upload-panel-header bg-[#2d2d2d] border-b border-[#333333] px-3.5 py-2 flex justify-between items-center">
      <div class="header-left flex items-center gap-2">
        <i class="pi pi-file-import panel-icon text-sky-400 text-sm"></i>
        <span class="panel-title text-xs font-semibold text-white">上傳線路圖檔 (Schematic Upload)</span>
      </div>
      <div class="header-formats flex gap-1.5">
        <span class="format-badge text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#1e1e1e] text-[#858585] border border-[#333333]">.zip</span>
        <span class="format-badge text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#1e1e1e] text-[#858585] border border-[#333333]">.7z</span>
        <span class="format-badge text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#1e1e1e] text-[#858585] border border-[#333333]">.xml</span>
      </div>
    </div>

    <!-- 緊湊表單主體 -->
    <div class="upload-panel-body p-3.5 flex flex-col gap-3">
      <!-- 專案資訊列 (名稱與模式雙選) -->
      <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <!-- 專案名稱輸入列 -->
        <div class="form-row flex flex-col gap-1 sm:col-span-2">
          <label class="compact-label text-xs font-medium text-[#cccccc]">專案名稱</label>
          <div class="input-icon-wrapper relative flex items-center">
            <i class="pi pi-folder input-icon absolute left-2.5 text-[#858585] text-xs pointer-events-none"></i>
            <input
              v-model="projectName"
              type="text"
              class="text-input compact-text-input w-full pl-7 pr-3 py-1.5 text-xs rounded border border-[#333333] bg-[#1e1e1e] text-white placeholder:text-[#666666] focus:outline-none focus:border-[#007acc] transition-colors"
              placeholder="請輸入專案名稱 (例如: Carrier_Board_RevA)"
              :disabled="isUploading"
            />
          </div>
        </div>

        <!-- 模式雙選按鈕 (NPI / MP) -->
        <div class="form-row flex flex-col gap-1 sm:col-span-1">
          <label class="compact-label text-xs font-medium text-[#cccccc]">裝配階段模式</label>
          <SelectButton
            v-model="isMpMode"
            :options="modeOptions"
            optionLabel="label"
            optionValue="value"
            :allowEmpty="false"
            size="small"
            :disabled="isUploading"
            class="mode-selector text-xs"
          />
        </div>
      </div>

      <!-- 緊湊型拖曳/選取檔案區域 -->
      <div
        class="compact-dropzone dropzone border-2 border-dashed border-[#333333] hover:border-sky-400/60 rounded-md p-4 text-center cursor-pointer transition-colors bg-[#1e1e1e]"
        :class="{ 'dropzone-active border-sky-400 bg-sky-500/10': isDragging, 'has-file border-sky-400/40 bg-sky-500/5': !!selectedFile }"
        @dragover.prevent="isDragging = true"
        @dragleave.prevent="isDragging = false"
        @drop.prevent="handleDrop"
        @click="triggerFileInput"
      >
        <input
          ref="fileInput"
          type="file"
          class="hidden-file-input hidden"
          accept=".zip,.7z,.xml"
          @change="handleFileChange"
        />

        <div v-if="!selectedFile" class="dropzone-empty-content flex flex-col items-center justify-center gap-1.5 py-2">
          <i class="pi pi-cloud-upload dropzone-icon text-2xl text-sky-400"></i>
          <span class="dropzone-text text-xs text-[#858585]">點擊或拖曳 Cadence OrCAD 電路圖檔案至此 (.zip, .7z, .xml)</span>
        </div>

        <div v-else class="selected-file-row flex items-center justify-between px-2">
          <div class="file-info-col flex items-center gap-2 text-xs">
            <i class="pi pi-file-check file-icon-ready text-emerald-400 text-sm"></i>
            <span class="file-name font-medium text-white">{{ selectedFile.name }}</span>
            <span class="file-size text-[#858585] text-[11px]">({{ formatFileSize(selectedFile.size) }})</span>
          </div>
          <button
            type="button"
            class="remove-file-btn bg-transparent border-0 text-[#858585] hover:text-rose-400 cursor-pointer p-1 text-xs transition-colors"
            title="移除已選檔案"
            @click.stop="removeFile"
          >
            <i class="pi pi-times"></i>
          </button>
        </div>
      </div>

      <!-- 底部動作列 -->
      <div class="upload-action-row flex flex-col sm:flex-row justify-between sm:items-center gap-2 pt-1">
        <span class="upload-hint text-muted text-[11px] text-[#858585] flex items-center">
          <i class="pi pi-info-circle mr-1"></i>上傳後系統將自動啟動解壓縮、檔案結構預檢與圖譜特徵分析
        </span>
        <Button
          label="上傳並進行輕量預先分析"
          icon="pi pi-bolt"
          severity="primary"
          size="small"
          class="submit-upload-btn"
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
import SelectButton from 'primevue/selectbutton'

const emit = defineEmits<{
  (e: 'upload', payload: { file: File; projectName: string; isMpMode: boolean }): void
}>()

defineProps<{
  isUploading?: boolean
}>()

const projectName = ref<string>('My_Carrier_Board')
const isMpMode = ref<boolean>(false)
const modeOptions = [
  { label: 'NPI', value: false },
  { label: 'MP', value: true },
]
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
    isMpMode: isMpMode.value,
  })
}
</script>
