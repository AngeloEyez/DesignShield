<template>
  <div v-if="visible" class="fixed inset-0 w-screen h-screen bg-black/65 backdrop-blur-sm flex items-center justify-center z-[999]" @click.self="handleClose">
    <div class="bg-surface-card border border-surface-border rounded-lg w-[680px] max-w-[90vw] max-h-[85vh] flex flex-col shadow-2xl overflow-hidden text-surface-200">
      <div class="flex items-center justify-between px-6 py-4 bg-surface-overlay border-b border-surface-border">
        <div class="flex items-center gap-2.5 text-primary">
          <i class="pi pi-cog text-lg"></i>
          <h3 class="m-0 text-base font-semibold text-surface-900 dark:text-surface-0">系統運維與參數設定 (System Settings & Ops)</h3>
        </div>
        <button class="close-btn bg-transparent border-0 text-surface-400 hover:text-surface-100 cursor-pointer p-1 text-base transition-colors" @click="handleClose">
          <i class="pi pi-times"></i>
        </button>
      </div>

      <div class="p-6 overflow-y-auto flex flex-col gap-4">
        <!-- 儲存空間健康指標與垃圾清理卡片 -->
        <div class="border border-surface-border rounded-md p-4 bg-surface-overlay">
          <div class="flex items-center gap-2 mb-3.5 text-primary">
            <i class="pi pi-database"></i>
            <h4 class="m-0 text-sm font-semibold text-surface-900 dark:text-surface-0">磁碟儲存空間監控與垃圾回收 (Storage & Garbage Collection)</h4>
          </div>
          <div class="grid grid-cols-2 sm:grid-cols-4 gap-2.5 mb-3.5">
            <div class="bg-surface-card border border-surface-border rounded p-2.5 flex flex-col items-center text-center">
              <span class="text-xs text-surface-400 mb-1">上傳暫存 (Uploads)</span>
              <span class="text-base font-bold text-surface-900 dark:text-surface-0">{{ storageStats.uploads.file_count }} 檔</span>
              <span class="text-[11px] text-surface-400 mt-0.5">{{ formatBytes(storageStats.uploads.total_bytes) }}</span>
            </div>
            <div class="bg-surface-card border border-surface-border rounded p-2.5 flex flex-col items-center text-center">
              <span class="text-xs text-surface-400 mb-1">解壓暫存 (Staging)</span>
              <span class="text-base font-bold text-surface-900 dark:text-surface-0">{{ storageStats.staging.file_count }} 檔</span>
              <span class="text-[11px] text-surface-400 mt-0.5">{{ formatBytes(storageStats.staging.total_bytes) }}</span>
            </div>
            <div class="bg-surface-card border border-surface-border rounded p-2.5 flex flex-col items-center text-center">
              <span class="text-xs text-surface-400 mb-1">報告存檔 (Reports)</span>
              <span class="text-base font-bold text-surface-900 dark:text-surface-0">{{ storageStats.reports.file_count }} 檔</span>
              <span class="text-[11px] text-surface-400 mt-0.5">{{ formatBytes(storageStats.reports.total_bytes) }}</span>
            </div>
            <div class="bg-primary/10 border border-primary/30 rounded p-2.5 flex flex-col items-center text-center">
              <span class="text-xs text-surface-400 mb-1">總空間佔用</span>
              <span class="text-base font-bold text-primary">{{ storageStats.total_mb }} MB</span>
              <span class="text-[11px] text-surface-400 mt-0.5">{{ storageStats.total_files }} 檔案總計</span>
            </div>
          </div>

          <div class="flex justify-end gap-2.5">
            <Button
              label="重新整理空間指標"
              icon="pi pi-refresh"
              severity="secondary"
              size="small"
              :loading="isLoadingStats"
              @click="loadStorageStats"
            />
            <Button
              label="立即清理過期暫存"
              icon="pi pi-trash"
              severity="danger"
              size="small"
              :loading="isCleaning"
              @click="triggerCleanup"
            />
          </div>
          <div v-if="cleanupMessage" class="mt-3 bg-teal-500/15 border border-teal-500/30 text-teal-300 rounded p-2 text-xs flex items-center gap-1.5">
            <i class="pi pi-check-circle"></i>
            <span>{{ cleanupMessage }}</span>
          </div>
        </div>

        <!-- 運維設定表單 -->
        <div class="border border-surface-border rounded-md p-4 bg-surface-overlay">
          <div class="flex items-center gap-2 mb-3.5 text-primary">
            <i class="pi pi-sliders-h"></i>
            <h4 class="m-0 text-sm font-semibold text-surface-900 dark:text-surface-0">執行與生命週期設定 (Execution & Lifecycle Settings)</h4>
          </div>

          <div class="mb-3.5 flex flex-col gap-1.5">
            <label class="text-xs font-semibold text-surface-700 dark:text-surface-300">暫存檔案保留天數 (Retention Days)</label>
            <input
              v-model.number="retentionDays"
              type="number"
              min="1"
              max="90"
              class="px-3 py-1.5 border border-surface-border bg-surface-ground text-surface-900 dark:text-surface-100 rounded text-sm focus:outline-none focus:border-primary transition-colors"
            />
            <small class="text-xs text-surface-400">超過此天數的 uploads 與 staging 檔案將自動被垃圾清理機制回收釋放空間。</small>
          </div>

          <div class="mb-3.5 flex flex-col gap-1.5">
            <label class="text-xs font-semibold text-surface-700 dark:text-surface-300">DRC 任務超時上限 (秒)</label>
            <input
              v-model.number="timeoutSeconds"
              type="number"
              min="60"
              max="7200"
              class="px-3 py-1.5 border border-surface-border bg-surface-ground text-surface-900 dark:text-surface-100 rounded text-sm focus:outline-none focus:border-primary transition-colors"
            />
            <small class="text-xs text-surface-400">DBOS 工作流程單一任務執行的最大等待時限。</small>
          </div>

          <div class="mb-3.5 flex flex-col gap-1.5">
            <label class="text-xs font-semibold text-surface-700 dark:text-surface-300">本地 LLM 推理伺服器 URL (OpenAI 相容協議)</label>
            <input
              v-model="llmApiBase"
              type="text"
              class="px-3 py-1.5 border border-surface-border bg-surface-ground text-surface-900 dark:text-surface-100 rounded text-sm focus:outline-none focus:border-primary transition-colors"
              placeholder="http://192.168.1.5:8000/v1"
            />
          </div>

          <div class="mb-1 flex flex-col gap-1.5">
            <label class="text-xs font-semibold text-surface-700 dark:text-surface-300">LLM 模型名稱 (Model Name)</label>
            <input
              v-model="llmModel"
              type="text"
              class="px-3 py-1.5 border border-surface-border bg-surface-ground text-surface-900 dark:text-surface-100 rounded text-sm focus:outline-none focus:border-primary transition-colors"
              placeholder="openai/local-model"
            />
          </div>
        </div>
      </div>

      <div class="flex items-center justify-between px-6 py-3.5 bg-surface-overlay border-t border-surface-border">
        <div class="text-xs">
          <span v-if="saveSuccess" class="text-teal-300 font-semibold flex items-center gap-1"><i class="pi pi-check"></i> 設定已成功儲存！</span>
        </div>
        <div class="flex gap-2.5">
          <Button label="關閉" severity="secondary" @click="handleClose" />
          <Button
            label="儲存設定"
            icon="pi pi-check"
            severity="primary"
            :loading="isSaving"
            @click="saveSettings"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * @file SystemSettingsModal.vue
 * @description 系統設定管理與磁碟空間垃圾回收對話框
 */

import { ref, watch, onMounted } from 'vue'
import Button from 'primevue/button'
import axios from 'axios'

const props = defineProps<{
  visible: boolean
}>()

const emit = defineEmits<{
  (e: 'update:visible', value: boolean): void
}>()

const retentionDays = ref<number>(7)
const timeoutSeconds = ref<number>(3600)
const llmApiBase = ref<string>('http://192.168.1.5:8000/v1')
const llmModel = ref<string>('local-llm')

const storageStats = ref({
  total_files: 0,
  total_bytes: 0,
  total_mb: 0.0,
  uploads: { file_count: 0, total_bytes: 0 },
  staging: { file_count: 0, total_bytes: 0 },
  reports: { file_count: 0, total_bytes: 0 }
})

const isLoadingStats = ref(false)
const isCleaning = ref(false)
const isSaving = ref(false)
const cleanupMessage = ref('')
const saveSuccess = ref(false)

const formatBytes = (bytes: number): string => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const loadStorageStats = async () => {
  isLoadingStats.value = true
  try {
    const res = await axios.get('/api/v1/settings/storage-stats')
    if (res.data) {
      storageStats.value = res.data
    }
  } catch (err) {
    console.error('Failed to load storage stats:', err)
  } finally {
    isLoadingStats.value = false
  }
}

const loadSettings = async () => {
  try {
    const res = await axios.get('/api/v1/settings')
    if (res.data && Array.isArray(res.data)) {
      for (const item of res.data) {
        if (item.key === 'upload_retention_days' && item.value?.days) {
          retentionDays.value = item.value.days
        } else if (item.key === 'task_timeout_seconds' && item.value?.seconds) {
          timeoutSeconds.value = item.value.seconds
        } else if (item.key === 'llm_config') {
          if (item.value?.api_base) llmApiBase.value = item.value.api_base
          if (item.value?.model) llmModel.value = item.value.model
        }
      }
    }
  } catch (err) {
    console.error('Failed to load settings:', err)
  }
}

const triggerCleanup = async () => {
  isCleaning.value = true
  cleanupMessage.value = ''
  try {
    const res = await axios.post(`/api/v1/settings/cleanup?retention_days=${retentionDays.value}`)
    if (res.data) {
      cleanupMessage.value = `清理完成！共釋放 ${res.data.freed_mb} MB 磁碟空間 (${res.data.deleted_files_count} 個項目)`
      await loadStorageStats()
    }
  } catch (err) {
    cleanupMessage.value = '清理執行失敗，請檢閱伺服器紀錄'
    console.error('Cleanup error:', err)
  } finally {
    isCleaning.value = false
  }
}

const saveSettings = async () => {
  isSaving.value = true
  saveSuccess.value = false
  try {
    await axios.put('/api/v1/settings/upload_retention_days', {
      value: { days: retentionDays.value },
      description: '暫存與已完成任務上傳檔案保留天數，逾期自動清理'
    })
    await axios.put('/api/v1/settings/task_timeout_seconds', {
      value: { seconds: timeoutSeconds.value },
      description: 'DRC 任務執行逾時上限 (秒)'
    })
    await axios.put('/api/v1/settings/llm_config', {
      value: {
        api_base: llmApiBase.value,
        model: llmModel.value,
        temperature: 0.1,
        max_tokens: 1024
      },
      description: '本地 LLM 推理伺服器連線與生成參數設定'
    })
    saveSuccess.value = true
    setTimeout(() => {
      saveSuccess.value = false
    }, 3000)
  } catch (err) {
    console.error('Failed to save settings:', err)
  } finally {
    isSaving.value = false
  }
}

const handleClose = () => {
  emit('update:visible', false)
}

watch(
  () => props.visible,
  (newVal) => {
    if (newVal) {
      loadSettings()
      loadStorageStats()
      cleanupMessage.value = ''
      saveSuccess.value = false
    }
  }
)

onMounted(() => {
  if (props.visible) {
    loadSettings()
    loadStorageStats()
  }
})
</script>
