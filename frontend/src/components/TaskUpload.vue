<template>
  <div class="task-upload-panel bg-surface-panel overflow-hidden">
    <!-- 緊湊標題列 -->
    <div class="upload-panel-header bg-surface-header border-b border-surface-border px-4 py-2.5 flex justify-between items-center">
      <div class="header-left flex items-center gap-2">
        <i class="pi pi-file-import panel-icon text-primary text-sm"></i>
        <span class="panel-title text-sm font-semibold text-vscode-textHeading">上傳線路圖檔 (Schematic Upload)</span>
      </div>
      <div class="header-formats flex gap-1">
        <span class="format-badge text-[10px] font-mono px-1.5 py-0.2 rounded bg-surface-ground text-vscode-textMuted border border-surface-border">.zip</span>
        <span class="format-badge text-[10px] font-mono px-1.5 py-0.2 rounded bg-surface-ground text-vscode-textMuted border border-surface-border">.7z</span>
        <span class="format-badge text-[10px] font-mono px-1.5 py-0.2 rounded bg-surface-ground text-vscode-textMuted border border-surface-border">.xml</span>
      </div>
    </div>

    <!-- 聚焦表單主體 (p-4 flex flex-col gap-3.5) -->
    <div class="upload-panel-body p-4 flex flex-col gap-3.5">
      <!-- 專案資訊列 (名稱與模式雙選) -->
      <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <!-- 專案名稱輸入列 (採用 PrimeVue InputText) -->
        <div class="form-row flex flex-col gap-1 sm:col-span-2">
          <label class="compact-label text-xs font-medium text-vscode-textSecondary">專案名稱</label>
          <IconField class="w-full">
            <InputIcon class="pi pi-folder text-vscode-textMuted text-xs" />
            <InputText
              v-model="projectName"
              type="text"
              size="small"
              class="text-input compact-text-input w-full text-xs"
              placeholder="請輸入專案名稱 (例如: Carrier_Board_RevA)"
              :disabled="isUploading"
            />
          </IconField>
        </div>

        <!-- 模式雙選按鈕 (NPI / MP) -->
        <div class="form-row flex flex-col gap-1 sm:col-span-1">
          <label class="compact-label text-xs font-medium text-vscode-textSecondary">裝配階段模式</label>
          <SelectButton
            v-model="isMpMode"
            :options="modeOptions"
            option-label="label"
            option-value="value"
            :allow-empty="false"
            size="small"
            :disabled="isUploading"
            class="mode-selector text-xs"
          />
        </div>
      </div>

      <!-- 拖曳/選取檔案區域 -->
      <div
        class="compact-dropzone dropzone border border-dashed border-surface-borderLight hover:border-primary rounded-lg p-4 text-center cursor-pointer transition-colors bg-surface-ground"
        :class="{ 'dropzone-active border-primary bg-primary/10': isDragging, 'has-file border-primary/50 bg-primary/5': !!selectedFile }"
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

        <div v-if="!selectedFile" class="dropzone-empty-content flex items-center justify-center gap-2 py-1">
          <i class="pi pi-cloud-upload dropzone-icon text-base text-primary"></i>
          <span class="dropzone-text text-xs text-vscode-textMuted">點擊或拖曳 Cadence OrCAD 電路圖檔案至此 (.zip, .7z, .xml)</span>
        </div>

        <div v-else class="selected-file-row flex items-center justify-between px-2">
          <div class="file-info-col flex items-center gap-2 text-xs">
            <i class="pi pi-file-check file-icon-ready text-vscode-green text-xs"></i>
            <span class="file-name font-medium text-vscode-textHeading">{{ selectedFile.name }}</span>
            <span class="file-size text-vscode-textMuted text-[11px] font-mono">({{ formatFileSize(selectedFile.size) }})</span>
          </div>
          <button
            v-tooltip.top="'移除已選檔案'"
            type="button"
            class="remove-file-btn bg-transparent border-0 text-vscode-textMuted hover:text-vscode-danger cursor-pointer p-1 text-xs transition-colors"
            title="移除已選檔案"
            @click.stop="removeFile"
          >
            <i class="pi pi-times"></i>
          </button>
        </div>
      </div>

      <!-- 底部動作列 -->
      <div class="upload-action-row flex flex-col sm:flex-row justify-between sm:items-center gap-2">
        <span class="upload-hint text-muted text-[11px] text-vscode-textMuted flex items-center">
          <i class="pi pi-info-circle mr-1"></i>上傳後系統將自動啟動解壓縮、檔案結構預檢與圖譜特徵分析
        </span>
        <Button
          label="上傳並進行輕量預先分析"
          icon="pi pi-bolt"
          severity="primary"
          size="small"
          class="submit-upload-btn text-xs"
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
 * @description 線路檔案上傳與專案資訊填寫元件 (雙主題適配與 PrimeVue InputText 緊湊版)
 */

import { ref } from 'vue'
import Button from 'primevue/button'
import SelectButton from 'primevue/selectbutton'
import InputText from 'primevue/inputtext'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'

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

const triggerFileInput = () => {
  fileInput.value?.click()
}

const handleFileChange = (event: Event) => {
  const target = event.target as HTMLInputElement
  if (target.files && target.files.length > 0) {
    selectedFile.value = target.files[0]
  }
}

const handleDrop = (event: DragEvent) => {
  isDragging.value = false
  if (event.dataTransfer && event.dataTransfer.files.length > 0) {
    selectedFile.value = event.dataTransfer.files[0]
  }
}

const removeFile = () => {
  selectedFile.value = null
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`
}

const submitUpload = () => {
  if (!selectedFile.value || !projectName.value.trim()) return
  emit('upload', {
    file: selectedFile.value,
    projectName: projectName.value.trim(),
    isMpMode: isMpMode.value,
  })
}
</script>
