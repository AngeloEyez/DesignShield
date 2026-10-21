<template>
  <div v-if="visible" class="fixed inset-0 w-screen h-screen bg-black/50 backdrop-blur-sm flex items-center justify-center z-[999]" @click.self="handleClose">
    <div class="bg-surface-panel border border-surface-border rounded-lg w-[640px] max-w-[90vw] max-h-[85vh] flex flex-col shadow-xl overflow-hidden text-surface-0">
      <div class="flex items-center justify-between px-4 py-3 bg-surface-card border-b border-surface-border">
        <div class="flex items-center gap-2 text-primary-400">
          <i class="pi pi-cog text-sm"></i>
          <h3 class="m-0 text-sm font-semibold text-surface-0">系統運維與參數設定 (System Settings & Ops)</h3>
        </div>
        <button type="button" class="close-btn bg-transparent border-0 text-surface-400 hover:text-surface-0 cursor-pointer p-1 text-sm transition-colors" @click="handleClose">
          <i class="pi pi-times"></i>
        </button>
      </div>

      <div class="p-4 overflow-y-auto flex flex-col gap-3">
        <!-- 儲存空間健康指標與垃圾清理 (緊湊單列橫條) -->
        <div class="border border-surface-border rounded bg-surface-card overflow-hidden">
          <div class="flex items-center justify-between px-3 py-2 border-b border-surface-border">
            <div class="flex items-center gap-1.5 text-primary-400">
              <i class="pi pi-database text-xs"></i>
              <h4 class="m-0 text-xs font-semibold text-surface-0">磁碟儲存空間監控與垃圾回收 (Storage & Garbage Collection)</h4>
            </div>
            <div class="flex items-center gap-1.5">
              <Button
                v-tooltip.top="'重新整理空間指標'"
                icon="pi pi-refresh"
                severity="secondary"
                size="small"
                outlined
                class="!w-6 !h-6 !p-0"
                :loading="isLoadingStats"
                @click="loadStorageStats"
              >
                <i class="pi pi-refresh text-xs"></i>
                <span class="sr-only">重新整理空間指標</span>
              </Button>
              <Button
                v-tooltip.top="'立即清理過期暫存'"
                icon="pi pi-trash"
                severity="danger"
                size="small"
                outlined
                class="!w-6 !h-6 !p-0"
                :loading="isCleaning"
                @click="triggerCleanup"
              >
                <i class="pi pi-trash text-xs"></i>
                <span class="sr-only">立即清理過期暫存</span>
              </Button>
            </div>
          </div>

          <div class="grid grid-cols-2 sm:grid-cols-4 divide-x divide-surface-border bg-surface-panel">
            <div class="px-3 py-2 flex flex-col">
              <span class="text-[11px] text-surface-400">上傳暫存 (Uploads)</span>
              <span class="text-xs font-semibold text-surface-0 font-mono mt-0.5">{{ storageStats.uploads.file_count }} 檔 ({{ formatBytes(storageStats.uploads.total_bytes) }})</span>
            </div>
            <div class="px-3 py-2 flex flex-col">
              <span class="text-[11px] text-surface-400">解壓暫存 (Staging)</span>
              <span class="text-xs font-semibold text-surface-0 font-mono mt-0.5">{{ storageStats.staging.file_count }} 檔 ({{ formatBytes(storageStats.staging.total_bytes) }})</span>
            </div>
            <div class="px-3 py-2 flex flex-col">
              <span class="text-[11px] text-surface-400">報告存檔 (Reports)</span>
              <span class="text-xs font-semibold text-surface-0 font-mono mt-0.5">{{ storageStats.reports.file_count }} 檔 ({{ formatBytes(storageStats.reports.total_bytes) }})</span>
            </div>
            <div class="px-3 py-2 flex flex-col bg-primary-500/5">
              <span class="text-[11px] text-surface-400">總空間佔用</span>
              <span class="text-xs font-semibold text-primary-400 font-mono mt-0.5">{{ storageStats.total_mb }} MB ({{ storageStats.total_files }} 檔)</span>
            </div>
          </div>

          <div v-if="cleanupMessage" class="px-3 py-1.5 bg-emerald-500/10 border-t border-emerald-500/30 text-emerald-500 text-xs flex items-center gap-1.5">
            <i class="pi pi-check-circle text-xs"></i>
            <span>{{ cleanupMessage }}</span>
          </div>
        </div>

        <!-- 運維設定表單 (1px divide-y 緊湊清單) -->
        <div class="border border-surface-border rounded bg-surface-card divide-y divide-surface-border">
          <div class="flex items-center gap-1.5 px-3 py-2 text-primary-400">
            <i class="pi pi-sliders-h text-xs"></i>
            <h4 class="m-0 text-xs font-semibold text-surface-0">執行與生命週期設定 (Execution & Lifecycle Settings)</h4>
          </div>

          <div class="px-3 py-2 flex items-center justify-between gap-3 bg-surface-panel">
            <div class="flex flex-col min-w-0">
              <label class="text-xs font-semibold text-surface-0">暫存檔案保留天數 (Retention Days)</label>
              <small class="text-[11px] text-surface-400 truncate">超過此天數的 uploads 與 staging 檔案將自動回收釋放空間。</small>
            </div>
            <input
              v-model.number="retentionDays"
              type="number"
              min="1"
              max="90"
              class="w-24 px-2.5 py-1 border border-surface-border bg-surface-ground text-surface-0 rounded text-xs font-mono focus:outline-none focus:border-primary-500"
            />
          </div>

          <div class="px-3 py-2 flex items-center justify-between gap-3 bg-surface-panel">
            <div class="flex flex-col min-w-0">
              <label class="text-xs font-semibold text-surface-0">DRC 任務超時上限 (秒)</label>
              <small class="text-[11px] text-surface-400 truncate">DBOS 工作流程單一任務執行的最大等待時限。</small>
            </div>
            <input
              v-model.number="timeoutSeconds"
              type="number"
              min="60"
              max="7200"
              class="w-24 px-2.5 py-1 border border-surface-border bg-surface-ground text-surface-0 rounded text-xs font-mono focus:outline-none focus:border-primary-500"
            />
          </div>

          <div class="px-3 py-2 flex items-center justify-between gap-3 bg-surface-panel">
            <label class="text-xs font-semibold text-surface-0 shrink-0">本地 LLM 推理伺服器 URL</label>
            <input
              v-model="llmApiBase"
              type="text"
              class="w-64 px-2.5 py-1 border border-surface-border bg-surface-ground text-surface-0 rounded text-xs font-mono focus:outline-none focus:border-primary-500"
              placeholder="http://192.168.1.5:8000/v1"
            />
          </div>

          <div class="px-3 py-2 flex items-center justify-between gap-3 bg-surface-panel">
            <label class="text-xs font-semibold text-surface-0 shrink-0">LLM 模型名稱 (Model Name)</label>
            <input
              v-model="llmModel"
              type="text"
              class="w-64 px-2.5 py-1 border border-surface-border bg-surface-ground text-surface-0 rounded text-xs font-mono focus:outline-none focus:border-primary-500"
              placeholder="openai/local-model"
            />
          </div>
        </div>

        <!-- 介面外觀與主題偏好設定 -->
        <div class="border border-surface-border rounded px-3 py-2.5 bg-surface-panel flex items-center justify-between gap-3">
          <div class="flex flex-col gap-0.5">
            <span class="text-xs font-semibold text-surface-0 flex items-center gap-1.5">
              <i class="pi pi-palette text-primary-400 text-xs"></i>
              <span>主題模式 (Theme Mode)</span>
            </span>
            <span class="text-[11px] text-surface-400">即時切換淺色 (Light) 或深色 (Dark) 雙主題風格。</span>
          </div>
          <div class="flex items-center gap-1.5">
            <Button
              label="淺色模式"
              icon="pi pi-sun"
              size="small"
              class="!py-1 !px-2.5 !text-xs"
              :severity="theme === 'light' ? 'primary' : 'secondary'"
              :variant="theme === 'light' ? undefined : 'outlined'"
              @click="setTheme('light')"
            />
            <Button
              label="深色模式"
              icon="pi pi-moon"
              size="small"
              class="!py-1 !px-2.5 !text-xs"
              :severity="theme === 'dark' ? 'primary' : 'secondary'"
              :variant="theme === 'dark' ? undefined : 'outlined'"
              @click="setTheme('dark')"
            />
          </div>
        </div>
      </div>

      <div class="flex items-center justify-between px-4 py-2.5 bg-surface-card border-t border-surface-border">
        <div class="text-xs">
          <span v-if="saveSuccess" class="text-emerald-500 font-semibold flex items-center gap-1"><i class="pi pi-check"></i> 設定已成功儲存！</span>
        </div>
        <div class="flex gap-2">
          <Button label="關閉" severity="secondary" size="small" outlined @click="handleClose" />
          <Button
            label="儲存設定"
            icon="pi pi-check"
            severity="primary"
            size="small"
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
 * @description 系統設定管理與磁碟空間垃圾回收對話框 (2026 雙主題緊湊版)
 */

import { ref, watch, onMounted } from 'vue'
import Button from 'primevue/button'
import axios from 'axios'
import { useTheme } from '@/composables/useTheme'

const { theme, setTheme } = useTheme()

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
