<template>
  <div v-if="visible" class="settings-modal-backdrop" @click.self="handleClose">
    <div class="settings-modal-container">
      <div class="modal-header">
        <div class="header-title">
          <i class="pi pi-cog"></i>
          <h3>系統運維與參數設定 (System Settings & Ops)</h3>
        </div>
        <button class="close-btn" @click="handleClose">
          <i class="pi pi-times"></i>
        </button>
      </div>

      <div class="modal-body">
        <!-- 儲存空間健康指標與垃圾清理卡片 -->
        <div class="settings-card storage-card">
          <div class="card-title">
            <i class="pi pi-database"></i>
            <h4>磁碟儲存空間監控與垃圾回收 (Storage & Garbage Collection)</h4>
          </div>
          <div class="storage-metrics-grid">
            <div class="metric-box">
              <span class="metric-label">上傳暫存 (Uploads)</span>
              <span class="metric-value">{{ storageStats.uploads.file_count }} 檔</span>
              <span class="metric-sub">{{ formatBytes(storageStats.uploads.total_bytes) }}</span>
            </div>
            <div class="metric-box">
              <span class="metric-label">解壓暫存 (Staging)</span>
              <span class="metric-value">{{ storageStats.staging.file_count }} 檔</span>
              <span class="metric-sub">{{ formatBytes(storageStats.staging.total_bytes) }}</span>
            </div>
            <div class="metric-box">
              <span class="metric-label">報告存檔 (Reports)</span>
              <span class="metric-value">{{ storageStats.reports.file_count }} 檔</span>
              <span class="metric-sub">{{ formatBytes(storageStats.reports.total_bytes) }}</span>
            </div>
            <div class="metric-box highlight">
              <span class="metric-label">總空間佔用</span>
              <span class="metric-value">{{ storageStats.total_mb }} MB</span>
              <span class="metric-sub">{{ storageStats.total_files }} 檔案總計</span>
            </div>
          </div>

          <div class="cleanup-actions">
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
          <div v-if="cleanupMessage" class="cleanup-result-alert">
            <i class="pi pi-check-circle"></i>
            <span>{{ cleanupMessage }}</span>
          </div>
        </div>

        <!-- 運維設定表單 -->
        <div class="settings-card">
          <div class="card-title">
            <i class="pi pi-sliders-h"></i>
            <h4>執行與生命週期設定 (Execution & Lifecycle Settings)</h4>
          </div>

          <div class="form-group">
            <label>暫存檔案保留天數 (Retention Days)</label>
            <input
              v-model.number="retentionDays"
              type="number"
              min="1"
              max="90"
              class="form-input"
            />
            <small class="form-help">超過此天數的 uploads 與 staging 檔案將自動被垃圾清理機制回收釋放空間。</small>
          </div>

          <div class="form-group">
            <label>DRC 任務超時上限 (秒)</label>
            <input
              v-model.number="timeoutSeconds"
              type="number"
              min="60"
              max="7200"
              class="form-input"
            />
            <small class="form-help">DBOS 工作流程單一任務執行的最大等待時限。</small>
          </div>

          <div class="form-group">
            <label>本地 LLM 推理伺服器 URL (OpenAI 相容協議)</label>
            <input
              v-model="llmApiBase"
              type="text"
              class="form-input"
              placeholder="http://192.168.1.5:8000/v1"
            />
          </div>

          <div class="form-group">
            <label>LLM 模型名稱 (Model Name)</label>
            <input
              v-model="llmModel"
              type="text"
              class="form-input"
              placeholder="openai/local-model"
            />
          </div>
        </div>
      </div>

      <div class="modal-footer">
        <div class="footer-status">
          <span v-if="saveSuccess" class="status-success"><i class="pi pi-check"></i> 設定已成功儲存！</span>
        </div>
        <div class="footer-buttons">
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

<style scoped>
.settings-modal-backdrop {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(0, 0, 0, 0.65);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 999;
}

.settings-modal-container {
  background: var(--vscode-bg-panel, #252526);
  border: 1px solid var(--vscode-border, #333333);
  border-radius: 8px;
  width: 680px;
  max-width: 90vw;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);
  overflow: hidden;
  color: var(--vscode-text-main, #cccccc);
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 22px;
  background: var(--vscode-bg-header, #2d2d2d);
  border-bottom: 1px solid var(--vscode-border, #333333);
}

.header-title {
  display: flex;
  align-items: center;
  gap: 10px;
}

.header-title i {
  font-size: 1.25rem;
  color: #38bdf8;
}

.header-title h3 {
  margin: 0;
  font-size: 1.15rem;
  color: var(--vscode-text-heading, #ffffff);
}

.close-btn {
  background: transparent;
  border: none;
  font-size: 1rem;
  color: var(--vscode-text-muted, #858585);
  cursor: pointer;
  padding: 4px;
}

.close-btn:hover {
  color: var(--vscode-text-main, #cccccc);
}

.modal-body {
  padding: 20px 22px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.settings-card {
  border: 1px solid var(--vscode-border, #333333);
  border-radius: 6px;
  padding: 16px;
  background: var(--vscode-bg-header, #2d2d2d);
}

.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 14px;
}

.card-title i {
  color: #38bdf8;
}

.card-title h4 {
  margin: 0;
  font-size: 0.92rem;
  color: var(--vscode-text-heading, #ffffff);
}

.storage-metrics-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
  margin-bottom: 14px;
}

.metric-box {
  background: var(--vscode-bg-panel, #252526);
  border: 1px solid var(--vscode-border, #333333);
  border-radius: 4px;
  padding: 10px;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.metric-box.highlight {
  background: rgba(0, 122, 204, 0.15);
  border-color: rgba(0, 122, 204, 0.3);
}

.metric-label {
  font-size: 0.72rem;
  color: var(--vscode-text-muted, #858585);
  margin-bottom: 4px;
}

.metric-value {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--vscode-text-heading, #ffffff);
}

.metric-sub {
  font-size: 0.68rem;
  color: var(--vscode-text-muted, #858585);
  margin-top: 2px;
}

.cleanup-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.cleanup-result-alert {
  margin-top: 12px;
  background: rgba(78, 201, 176, 0.15);
  border: 1px solid rgba(78, 201, 176, 0.3);
  color: #4ec9b0;
  border-radius: 4px;
  padding: 8px 12px;
  font-size: 0.82rem;
  display: flex;
  align-items: center;
  gap: 6px;
}

.form-group {
  margin-bottom: 14px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-group label {
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--vscode-text-main, #cccccc);
}

.form-input {
  padding: 7px 10px;
  border: 1px solid var(--vscode-border, #333333);
  background-color: var(--vscode-bg-input, #1e1e1e);
  color: var(--vscode-text-main, #cccccc);
  border-radius: 4px;
  font-size: 0.85rem;
  outline: none;
  transition: border-color 0.2s;
}

.form-input:focus {
  border-color: var(--vscode-blue, #007acc);
  box-shadow: 0 0 0 2px rgba(0, 122, 204, 0.25);
}

.form-help {
  font-size: 0.72rem;
  color: var(--vscode-text-muted, #858585);
}

.modal-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 22px;
  background: var(--vscode-bg-header, #2d2d2d);
  border-top: 1px solid var(--vscode-border, #333333);
}

.footer-status {
  font-size: 0.82rem;
}

.status-success {
  color: #4ec9b0;
  font-weight: 600;
}

.footer-buttons {
  display: flex;
  gap: 10px;
}
</style>
