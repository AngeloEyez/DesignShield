<template>
  <div class="settings-page-container">
    <!-- 頂部頁頭導航與動作列 -->
    <div class="settings-header">
      <div class="header-left">
        <Button
          label="返回 DRC 檢測"
          icon="pi pi-arrow-left"
          severity="secondary"
          size="small"
          class="back-btn"
          @click="goBack"
        />
        <div class="header-titles">
          <h1 class="page-title">
            <i class="pi pi-cog text-primary mr-2"></i>
            系統環境與參數設定 (System Settings)
          </h1>
          <p class="page-subtitle">
            直接綁定至系統 <code>.env</code> 設定檔，支援網路主機、本地 LLM、Langfuse 觀測與磁碟垃圾清理管理。
          </p>
        </div>
      </div>

      <div class="header-actions">
        <Button
          label="重設未儲存變更"
          icon="pi pi-undo"
          severity="secondary"
          :disabled="!hasUnsavedChanges || isSaving"
          @click="resetChanges"
        />
        <Button
          label="儲存設定"
          icon="pi pi-save"
          severity="primary"
          :loading="isSaving"
          :disabled="!hasUnsavedChanges"
          @click="saveSettings"
        />
        <Button
          label="重啟服務器"
          icon="pi pi-power-off"
          severity="danger"
          :loading="isRestarting"
          @click="confirmRestartServer"
        />
      </div>
    </div>

    <!-- 需重啟伺服器之警示提示橫幅 -->
    <div v-if="restartPromptVisible" class="alert-banner warning-banner">
      <div class="alert-content">
        <i class="pi pi-exclamation-triangle alert-icon"></i>
        <div>
          <div class="alert-title">系統提示：部分設定變更需要重新啟動伺服器才能完全生效</div>
          <div class="alert-desc">
            受影響的設定項目包含：<strong>{{ pendingRestartReasons.join(', ') }}</strong>。
            您可以點擊右側按鈕立即安全重啟後端服務。
          </div>
        </div>
      </div>
      <Button
        label="立即重啟服務器"
        icon="pi pi-refresh"
        severity="warn"
        size="small"
        :loading="isRestarting"
        @click="confirmRestartServer"
      />
    </div>

    <!-- 儲存成功通知橫幅 -->
    <div v-if="saveSuccessMessage" class="alert-banner success-banner">
      <div class="alert-content">
        <i class="pi pi-check-circle alert-icon"></i>
        <span>{{ saveSuccessMessage }}</span>
      </div>
      <button class="banner-close" @click="saveSuccessMessage = ''">
        <i class="pi pi-times"></i>
      </button>
    </div>

    <!-- 磁碟儲存空間監控與垃圾清理卡片 -->
    <div class="settings-card storage-card">
      <div class="card-header">
        <div class="card-title">
          <i class="pi pi-database text-indigo mr-2"></i>
          <h3>磁碟儲存空間監控與垃圾回收 (Storage & Garbage Collection)</h3>
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
      </div>

      <div class="storage-metrics-grid">
        <div class="metric-box">
          <span class="metric-label">上傳原始封裝 (Uploads)</span>
          <span class="metric-value">{{ storageStats.uploads.file_count }} 檔</span>
          <span class="metric-sub">{{ formatBytes(storageStats.uploads.total_bytes) }}</span>
        </div>
        <div class="metric-box">
          <span class="metric-label">解壓中繼暫存 (Staging)</span>
          <span class="metric-value">{{ storageStats.staging.file_count }} 檔</span>
          <span class="metric-sub">{{ formatBytes(storageStats.staging.total_bytes) }}</span>
        </div>
        <div class="metric-box">
          <span class="metric-label">DRC 檢查報告 (Reports)</span>
          <span class="metric-value">{{ storageStats.reports.file_count }} 檔</span>
          <span class="metric-sub">{{ formatBytes(storageStats.reports.total_bytes) }}</span>
        </div>
        <div class="metric-box highlight">
          <span class="metric-label">總磁碟佔用</span>
          <span class="metric-value">{{ storageStats.total_mb }} MB</span>
          <span class="metric-sub">{{ storageStats.total_files }} 個檔案總計</span>
        </div>
      </div>

      <div v-if="cleanupMessage" class="cleanup-alert">
        <i class="pi pi-info-circle mr-1"></i>
        <span>{{ cleanupMessage }}</span>
      </div>
    </div>

    <!-- 設定分類切換標籤 -->
    <div class="category-tabs">
      <button
        class="tab-btn"
        :class="{ active: selectedCategory === 'all' }"
        @click="selectedCategory = 'all'"
      >
        <i class="pi pi-list mr-1"></i>
        全部設定 ({{ envItems.length }})
      </button>
      <button
        v-for="cat in categories"
        :key="cat.id"
        class="tab-btn"
        :class="{ active: selectedCategory === cat.id }"
        @click="selectedCategory = cat.id"
      >
        <i :class="cat.icon + ' mr-1'"></i>
        {{ cat.name }} ({{ getCategoryItems(cat.id).length }})
      </button>
    </div>

    <!-- 設定項目列表卡片 -->
    <div class="settings-content-grid">
      <div
        v-for="cat in displayCategories"
        :key="cat.id"
        class="category-group-card"
      >
        <div class="group-header">
          <i :class="cat.icon" class="group-icon"></i>
          <h3>{{ cat.name }}</h3>
          <span class="env-source-tag">綁定至 .env 檔案</span>
        </div>

        <!-- LiteLLM 服務提供商快捷切換橫幅 (Gemini / OpenRouter / 本地 / OpenAI 等) -->
        <div v-if="cat.id === 'llm'" class="provider-switch-banner">
          <div class="provider-switch-header">
            <span class="provider-switch-title">
              <i class="pi pi-sparkles text-primary mr-1"></i>
              切換 LiteLLM 服務提供者 (Provider)：
            </span>
            <span class="provider-switch-hint">點選後自動載入該服務推薦模型與預設端點設定</span>
          </div>
          <div class="provider-chips-grid">
            <button
              v-for="p in supportedProviders"
              :key="p.id"
              type="button"
              class="provider-badge-btn"
              :class="{ active: currentProvider === p.id }"
              @click="selectProvider(p.id)"
            >
              <i :class="p.icon" class="mr-1"></i>
              <span class="provider-name">{{ p.name }}</span>
              <span class="provider-tag">{{ p.tag }}</span>
            </button>
          </div>
        </div>

        <div class="settings-items-list">
          <div
            v-for="item in getCategoryItems(cat.id)"
            :key="item.key"
            class="setting-item-row"
            :class="{ changed: isItemChanged(item.key) }"
          >
            <!-- 左側標籤與說明 -->
            <div class="setting-item-meta">
              <div class="meta-title-row">
                <span class="item-label">{{ item.label }}</span>
                <code class="env-key-badge">{{ item.key }}</code>
                <span v-if="item.requires_restart" class="badge-restart">
                  <i class="pi pi-refresh"></i> 需重啟生效
                </span>
                <span v-else class="badge-dynamic">
                  <i class="pi pi-bolt"></i> 動態生效
                </span>
                <span v-if="isItemChanged(item.key)" class="badge-modified">
                  已修改
                </span>
              </div>
              <p class="item-description">{{ item.description }}</p>
              <div v-if="item.example" class="item-example-box">
                <span class="example-label">範例格式：</span>
                <code>{{ item.example }}</code>
              </div>
            </div>

            <!-- 右側輸入控制項 -->
            <div class="setting-item-control">
              <!-- 若為 LITELLM_PROVIDER，提供下拉切換選單 -->
              <div v-if="item.key === 'LITELLM_PROVIDER'" class="input-wrapper">
                <select
                  v-model="formValues[item.key]"
                  class="setting-input provider-select"
                  @change="selectProvider(formValues[item.key])"
                >
                  <option v-for="p in supportedProviders" :key="p.id" :value="p.id">
                    {{ p.name }} ({{ p.tag }}) - provider: {{ p.id }}
                  </option>
                </select>
              </div>

              <!-- 若為 LOCAL_LLM_MODEL，提供即時向伺服器查詢下拉選單並同時支援手動輸入 -->
              <div v-else-if="item.key === 'LOCAL_LLM_MODEL'" class="model-select-wrapper">
                <div class="input-wrapper">
                  <input
                    v-model="formValues[item.key]"
                    type="text"
                    class="setting-input model-input"
                    list="llm-model-options"
                    :placeholder="item.default || item.example || '可直接輸入或自下拉選單選擇'"
                    @input="handleInput(item.key)"
                  />
                  <datalist id="llm-model-options">
                    <option v-for="m in availableLlmModels" :key="m" :value="m">{{ m }}</option>
                  </datalist>
                  <button
                    type="button"
                    class="btn-fetch-models"
                    :title="isFetchingModels ? '正在向伺服器查詢可用模型...' : '即時向伺服器查詢可用模型清單'"
                    :disabled="isFetchingModels"
                    @click="queryLlmModels(true)"
                  >
                    <i :class="isFetchingModels ? 'pi pi-spin pi-spinner' : 'pi pi-refresh'"></i>
                    <span>{{ isFetchingModels ? '查詢中...' : '重新整理' }}</span>
                  </button>
                </div>

                <!-- 下拉選單選擇器 -->
                <div class="model-dropdown-row">
                  <label class="model-dropdown-label" for="llm-model-select">
                    <i class="pi pi-list mr-1"></i>
                    下拉選單：
                  </label>
                  <select
                    id="llm-model-select"
                    class="model-select"
                    :disabled="isFetchingModels"
                    @change="onModelSelectChange($event)"
                  >
                    <option value="" disabled :selected="!availableLlmModels.includes(formValues[item.key])">
                      {{ availableLlmModels.length > 0 ? `-- 點擊展開可選模型 (共 ${availableLlmModels.length} 個) --` : '-- 尚無模型或點擊右上方重新整理查詢 --' }}
                    </option>
                    <option
                      v-for="m in availableLlmModels"
                      :key="m"
                      :value="m"
                      :selected="formValues[item.key] === m"
                    >
                      {{ m }}
                    </option>
                  </select>
                </div>

                <!-- 可用模型快速標籤 (Chips) -->
                <div v-if="availableLlmModels.length > 0" class="model-chips-list">
                  <span class="chips-label">可用模型：</span>
                  <span
                    v-for="m in availableLlmModels"
                    :key="m"
                    class="model-chip"
                    :class="{ active: formValues[item.key] === m }"
                    @click="applyModel(m)"
                  >
                    {{ m }}
                    <i v-if="formValues[item.key] === m" class="pi pi-check ml-1"></i>
                  </span>
                </div>

                <!-- 查詢狀態提示 -->
                <div v-if="llmModelStatusMessage" class="model-status-hint" :class="{ error: !llmModelStatusSuccess }">
                  <i :class="llmModelStatusSuccess ? 'pi pi-check-circle text-success' : 'pi pi-info-circle text-muted'" class="mr-1"></i>
                  <span>{{ llmModelStatusMessage }}</span>
                </div>
              </div>

              <!-- 一般設定項目輸入控制項 -->
              <div v-else class="input-wrapper">
                <input
                  v-if="!item.is_secret || visibleSecrets[item.key]"
                  v-model="formValues[item.key]"
                  type="text"
                  class="setting-input"
                  :placeholder="item.default || item.example || '請輸入設定值'"
                  @input="handleInput(item.key)"
                  @blur="item.key === 'LOCAL_LLM_URL' ? queryLlmModels(false) : null"
                />
                <input
                  v-else
                  v-model="formValues[item.key]"
                  type="password"
                  class="setting-input"
                  :placeholder="item.default || item.example || '請輸入設定值'"
                  @input="handleInput(item.key)"
                />
                <button
                  v-if="item.is_secret"
                  type="button"
                  class="btn-toggle-secret"
                  :title="visibleSecrets[item.key] ? '隱藏金鑰' : '顯示金鑰'"
                  @click="toggleSecret(item.key)"
                >
                  <i :class="visibleSecrets[item.key] ? 'pi pi-eye-slash' : 'pi pi-eye'"></i>
                </button>
              </div>

              <div v-if="isItemChanged(item.key)" class="original-val-hint">
                原設定值：<code>{{ originalValues[item.key] || '(空值)' }}</code>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 底部固定儲存浮動列 (當有未儲存變更時浮現) -->
    <div v-if="hasUnsavedChanges" class="floating-save-bar">
      <div class="save-bar-info">
        <i class="pi pi-info-circle text-primary mr-2"></i>
        <span>您有 <strong>{{ changedKeysCount }}</strong> 個設定項目尚未儲存至 <code>.env</code></span>
      </div>
      <div class="save-bar-actions">
        <Button label="放棄變更" severity="secondary" size="small" @click="resetChanges" />
        <Button
          label="立即儲存設定"
          icon="pi pi-check"
          severity="primary"
          size="small"
          :loading="isSaving"
          @click="saveSettings"
        />
      </div>
    </div>

    <!-- 重啟確認對話框 -->
    <div v-if="showRestartConfirm" class="modal-backdrop" @click.self="showRestartConfirm = false">
      <div class="modal-dialog">
        <div class="dialog-header">
          <i class="pi pi-power-off text-danger mr-2"></i>
          <h3>確認重啟伺服器？</h3>
        </div>
        <div class="dialog-body">
          <p>您即將發送指令重新啟動 DesignShield 後端伺服器服務。</p>
          <p class="text-secondary text-sm">
            重啟期間 API 連線將暫時中斷約 5~10 秒，頁面會自動監測連線狀況並在服務恢復時自動重新連線。
          </p>
        </div>
        <div class="dialog-footer">
          <Button label="取消" severity="secondary" @click="showRestartConfirm = false" />
          <Button
            label="確定重啟"
            icon="pi pi-check"
            severity="danger"
            :loading="isRestarting"
            @click="executeRestart"
          />
        </div>
      </div>
    </div>

    <!-- 重啟中連線輪詢等待覆蓋遮罩 -->
    <div v-if="isReconnecting" class="reconnect-overlay">
      <div class="reconnect-box">
        <div class="spinner-icon">
          <i class="pi pi-spin pi-spinner"></i>
        </div>
        <h3>伺服器正在重新啟動中...</h3>
        <p class="reconnect-desc">
          已發送重啟訊號，正在偵測服務健康狀態 (已等待 {{ reconnectTimer }} 秒)...
        </p>
        <div class="ping-status">
          <i class="pi pi-circle-fill ping-dot"></i>
          <span>正在探測端點：<code>http://192.168.1.16:8000/health</code></span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * @file SettingsView.vue
 * @description 系統環境與參數設定頁面，完整綁定 .env 檔案並提供重啟服務器功能
 */

import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import Button from 'primevue/button'
import {
  fetchEnvSettings,
  updateEnvSettings,
  restartServer,
  fetchStorageStats,
  triggerStorageCleanup,
  checkServerHealth,
  fetchAvailableLlmModels,
} from '@/services/api'
import type { EnvSettingItem, EnvCategory, StorageStats } from '@/types/settings'

const router = useRouter()

// 資料狀態
const envItems = ref<EnvSettingItem[]>([])
const categories = ref<EnvCategory[]>([])
const formValues = ref<Record<string, string>>({})
const originalValues = ref<Record<string, string>>({})
const visibleSecrets = ref<Record<string, boolean>>({})

// LLM 可用模型即時查詢狀態
const availableLlmModels = ref<string[]>([])
const isFetchingModels = ref<boolean>(false)
const llmModelStatusMessage = ref<string>('')
const llmModelStatusSuccess = ref<boolean>(true)

// 分類切換
const selectedCategory = ref<string>('all')

// 載入與動作狀態
const isLoading = ref<boolean>(false)
const isSaving = ref<boolean>(false)
const isRestarting = ref<boolean>(false)
const isReconnecting = ref<boolean>(false)
const reconnectTimer = ref<number>(0)
let reconnectInterval: any = null

const showRestartConfirm = ref<boolean>(false)
const saveSuccessMessage = ref<string>('')
const restartPromptVisible = ref<boolean>(false)
const pendingRestartReasons = ref<string[]>([])

// 磁碟空間狀態
const storageStats = ref<StorageStats>({
  total_files: 0,
  total_bytes: 0,
  total_mb: 0.0,
  uploads: { file_count: 0, total_bytes: 0 },
  staging: { file_count: 0, total_bytes: 0 },
  reports: { file_count: 0, total_bytes: 0 },
})
const isLoadingStats = ref<boolean>(false)
const isCleaning = ref<boolean>(false)
const cleanupMessage = ref<string>('')

// 計算屬性：是否有尚未儲存的變更
const hasUnsavedChanges = computed(() => {
  for (const k of Object.keys(formValues.value)) {
    if (formValues.value[k] !== originalValues.value[k]) {
      return true
    }
  }
  return false
})

const changedKeysCount = computed(() => {
  let count = 0
  for (const k of Object.keys(formValues.value)) {
    if (formValues.value[k] !== originalValues.value[k]) {
      count++
    }
  }
  return count
})

const isItemChanged = (key: string): boolean => {
  return formValues.value[key] !== originalValues.value[key]
}

const displayCategories = computed(() => {
  if (selectedCategory.value === 'all') {
    return categories.value
  }
  return categories.value.filter((c) => c.id === selectedCategory.value)
})

const getCategoryItems = (catId: string): EnvSettingItem[] => {
  return envItems.value.filter((item) => item.category === catId)
}

const toggleSecret = (key: string) => {
  visibleSecrets.value[key] = !visibleSecrets.value[key]
}

const handleInput = (_key: string) => {
  // 自動追蹤變更
}

const formatBytes = (bytes: number): string => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

// 支援之 LiteLLM 服務提供者定義
interface LlmProviderOption {
  id: string
  name: string
  tag: string
  icon: string
  defaultUrl: string
  defaultModel: string
  keyHint: string
}

const supportedProviders: LlmProviderOption[] = [
  {
    id: 'local',
    name: '本地推理',
    tag: 'vLLM / Ollama',
    icon: 'pi pi-server',
    defaultUrl: 'http://192.168.1.5:8000/v1',
    defaultModel: 'openai/qwen',
    keyHint: '本地端點未啟用鑑權填 EMPTY 即可'
  },
  {
    id: 'gemini',
    name: 'Google Gemini',
    tag: 'AI Studio',
    icon: 'pi pi-bolt',
    defaultUrl: 'https://generativelanguage.googleapis.com',
    defaultModel: 'gemini/gemini-2.5-flash',
    keyHint: '請填入 Google AI Studio API Key (AIzaSy...)'
  },
  {
    id: 'openrouter',
    name: 'OpenRouter',
    tag: '聚合網關',
    icon: 'pi pi-globe',
    defaultUrl: 'https://openrouter.ai/api/v1',
    defaultModel: 'openrouter/google/gemini-2.5-flash',
    keyHint: '請填入 OpenRouter API Key (sk-or-v1-...)'
  },
  {
    id: 'openai',
    name: 'OpenAI 官方',
    tag: 'GPT-4o',
    icon: 'pi pi-microchip',
    defaultUrl: 'https://api.openai.com/v1',
    defaultModel: 'openai/gpt-4o',
    keyHint: '請填入 OpenAI API Key (sk-proj-...)'
  },
  {
    id: 'anthropic',
    name: 'Anthropic',
    tag: 'Claude 3.5',
    icon: 'pi pi-comments',
    defaultUrl: 'https://api.anthropic.com',
    defaultModel: 'anthropic/claude-3-5-sonnet-20241022',
    keyHint: '請填入 Anthropic API Key (sk-ant-...)'
  },
  {
    id: 'groq',
    name: 'Groq',
    tag: '極速推理',
    icon: 'pi pi-forward',
    defaultUrl: 'https://api.groq.com/openai/v1',
    defaultModel: 'groq/llama-3.3-70b-versatile',
    keyHint: '請填入 Groq API Key (gsk_...)'
  },
  {
    id: 'deepseek',
    name: 'DeepSeek',
    tag: '官方 API',
    icon: 'pi pi-search',
    defaultUrl: 'https://api.deepseek.com/v1',
    defaultModel: 'deepseek/deepseek-chat',
    keyHint: '請填入 DeepSeek API Key (sk-...)'
  },
]

const currentProvider = computed(() => {
  if (formValues.value['LITELLM_PROVIDER']) {
    return formValues.value['LITELLM_PROVIDER'].toLowerCase()
  }
  const model = (formValues.value['LOCAL_LLM_MODEL'] || '').toLowerCase()
  if (model.startsWith('gemini/')) return 'gemini'
  if (model.startsWith('openrouter/')) return 'openrouter'
  if (model.startsWith('anthropic/') || model.startsWith('claude')) return 'anthropic'
  if (model.startsWith('groq/')) return 'groq'
  if (model.startsWith('deepseek/')) return 'deepseek'
  return 'local'
})

const selectProvider = (providerId: string) => {
  if (!providerId) return
  formValues.value['LITELLM_PROVIDER'] = providerId
  handleInput('LITELLM_PROVIDER')

  const providerDef = supportedProviders.find((p) => p.id === providerId)
  if (providerDef) {
    const curUrl = formValues.value['LOCAL_LLM_URL'] || ''
    const isOtherDefault = supportedProviders.some((p) => p.defaultUrl === curUrl)
    if (!curUrl || isOtherDefault || (providerId === 'gemini' && curUrl.includes('192.168.1.5'))) {
      formValues.value['LOCAL_LLM_URL'] = providerDef.defaultUrl
      handleInput('LOCAL_LLM_URL')
    }

    formValues.value['LOCAL_LLM_MODEL'] = providerDef.defaultModel
    handleInput('LOCAL_LLM_MODEL')

    queryLlmModels(true, providerId)
  }
}

// 載入 .env 設定資料
const loadEnvSettings = async () => {
  isLoading.value = true
  try {
    const data = await fetchEnvSettings()
    envItems.value = data.items
    categories.value = data.categories

    const forms: Record<string, string> = {}
    const origs: Record<string, string> = {}
    for (const item of data.items) {
      forms[item.key] = item.value !== null && item.value !== undefined ? String(item.value) : ''
      origs[item.key] = forms[item.key]
    }
    formValues.value = forms
    originalValues.value = origs

    // 自動向 LiteLLM 服務查詢可用模型列表
    queryLlmModels(false)
  } catch (err) {
    console.error('Failed to load env settings:', err)
  } finally {
    isLoading.value = false
  }
}

// 即時向 LiteLLM 伺服器端點或 Provider 查詢可用模型
const queryLlmModels = async (manual = false, forceProvider?: string) => {
  const p = forceProvider || currentProvider.value
  const url = formValues.value['LOCAL_LLM_URL'] || ''
  let key = formValues.value['LOCAL_LLM_API_KEY'] || ''
  if (p === 'gemini' && formValues.value['GEMINI_API_KEY']) {
    key = formValues.value['GEMINI_API_KEY']
  } else if (p === 'openrouter' && formValues.value['OPENROUTER_API_KEY']) {
    key = formValues.value['OPENROUTER_API_KEY']
  }

  isFetchingModels.value = true
  if (manual) {
    const provName = supportedProviders.find((sp) => sp.id === p)?.name || p
    llmModelStatusMessage.value = `正在查詢 ${provName} 可用模型清單...`
  }

  try {
    const res = await fetchAvailableLlmModels(p, url, key)
    if (res && res.success && Array.isArray(res.models) && res.models.length > 0) {
      availableLlmModels.value = res.models
      llmModelStatusSuccess.value = true
      llmModelStatusMessage.value = res.message || `成功取得 ${res.models.length} 個可用模型`
    } else {
      llmModelStatusSuccess.value = false
      llmModelStatusMessage.value = res?.message || '未能取得模型清單，支援手動輸入模型名稱'
    }
  } catch (err: any) {
    llmModelStatusSuccess.value = false
    llmModelStatusMessage.value = '連線至模型伺服器端點失敗，支援手動輸入模型名稱'
  } finally {
    isFetchingModels.value = false
  }
}

const onModelSelectChange = (event: Event) => {
  const target = event.target as HTMLSelectElement
  if (target && target.value) {
    formValues.value['LOCAL_LLM_MODEL'] = target.value
    handleInput('LOCAL_LLM_MODEL')
  }
}

const applyModel = (modelName: string) => {
  formValues.value['LOCAL_LLM_MODEL'] = modelName
  handleInput('LOCAL_LLM_MODEL')
}

// 載入磁碟空間指標
const loadStorageStats = async () => {
  isLoadingStats.value = true
  try {
    const data = await fetchStorageStats()
    if (data) {
      storageStats.value = data
    }
  } catch (err) {
    console.error('Failed to load storage stats:', err)
  } finally {
    isLoadingStats.value = false
  }
}

// 觸發磁碟空間清理
const triggerCleanup = async () => {
  isCleaning.value = true
  cleanupMessage.value = ''
  try {
    const res = await triggerStorageCleanup()
    if (res) {
      cleanupMessage.value = `清理成功！已釋放 ${res.freed_mb} MB 空間，刪除 ${res.deleted_files_count} 個過期暫存檔案。`
      await loadStorageStats()
    }
  } catch (err) {
    cleanupMessage.value = '清理失敗，請檢閱後端日誌。'
    console.error('Cleanup error:', err)
  } finally {
    isCleaning.value = false
  }
}

// 放棄變更並還原
const resetChanges = () => {
  formValues.value = { ...originalValues.value }
}

// 儲存設定至 .env
const saveSettings = async () => {
  isSaving.value = true
  saveSuccessMessage.value = ''

  try {
    const payload: Record<string, any> = {}
    for (const k of Object.keys(formValues.value)) {
      if (formValues.value[k] !== originalValues.value[k]) {
        payload[k] = formValues.value[k]
      }
    }

    if (Object.keys(payload).length === 0) {
      isSaving.value = false
      return
    }

    const res = await updateEnvSettings(payload)
    if (res.success) {
      originalValues.value = { ...formValues.value }
      saveSuccessMessage.value = res.message || '設定已成功儲存至 .env 檔案！'

      if (res.requires_restart) {
        restartPromptVisible.value = true
        pendingRestartReasons.value = res.restart_reasons || []
      } else {
        restartPromptVisible.value = false
      }
    }
  } catch (err) {
    console.error('Failed to save settings:', err)
  } finally {
    isSaving.value = false
  }
}

// 重啟伺服器確認與執行
const confirmRestartServer = () => {
  showRestartConfirm.value = true
}

const executeRestart = async () => {
  showRestartConfirm.value = false
  isRestarting.value = true
  isReconnecting.value = true
  reconnectTimer.value = 0

  try {
    await restartServer()
  } catch (err) {
    console.error('Trigger restart error (expected during process restart):', err)
  }

  // 開始計時與連線輪詢
  reconnectInterval = setInterval(async () => {
    reconnectTimer.value += 1
    // 預留 2 秒緩衝讓容器開始關閉
    if (reconnectTimer.value >= 2) {
      const isAlive = await checkServerHealth()
      if (isAlive) {
        clearInterval(reconnectInterval)
        isReconnecting.value = false
        isRestarting.value = false
        restartPromptVisible.value = false
        saveSuccessMessage.value = '✅ 伺服器已成功重啟完成並恢復連線！'
        await loadEnvSettings()
        await loadStorageStats()
      }
    }
    // 逾時保護 (60 秒)
    if (reconnectTimer.value > 60) {
      clearInterval(reconnectInterval)
      isReconnecting.value = false
      isRestarting.value = false
      alert('伺服器重啟探測逾時，請手動刷新頁面確認連線。')
    }
  }, 1500)
}

const goBack = () => {
  router.push('/')
}

onMounted(() => {
  loadEnvSettings()
  loadStorageStats()
})

onUnmounted(() => {
  if (reconnectInterval) {
    clearInterval(reconnectInterval)
  }
})
</script>

<style scoped>
.settings-page-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px 20px 80px 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* 頂部頁頭 */
.settings-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  background: #ffffff;
  padding: 20px 24px;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.header-left {
  display: flex;
  align-items: flex-start;
  gap: 16px;
}

.back-btn {
  margin-top: 4px;
}

.page-title {
  font-size: 1.45rem;
  font-weight: 700;
  color: #0f172a;
  margin: 0 0 6px 0;
  display: flex;
  align-items: center;
}

.page-subtitle {
  font-size: 0.88rem;
  color: #64748b;
  margin: 0;
}

.page-subtitle code {
  background: #f1f5f9;
  color: #0284c7;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 600;
}

.header-actions {
  display: flex;
  gap: 10px;
  align-items: center;
}

/* 警示橫幅 */
.alert-banner {
  padding: 14px 20px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.04);
}

.warning-banner {
  background-color: #fffbeb;
  border: 1px solid #fde68a;
  color: #92400e;
}

.success-banner {
  background-color: #ecfdf5;
  border: 1px solid #a7f3d0;
  color: #065f46;
}

.alert-content {
  display: flex;
  align-items: center;
  gap: 12px;
}

.alert-icon {
  font-size: 1.5rem;
  flex-shrink: 0;
}

.alert-title {
  font-weight: 700;
  font-size: 0.95rem;
  margin-bottom: 2px;
}

.alert-desc {
  font-size: 0.85rem;
}

.banner-close {
  background: transparent;
  border: none;
  cursor: pointer;
  color: #64748b;
  font-size: 0.9rem;
}

/* 磁碟儲存卡片 */
.storage-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 20px 24px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.card-title {
  display: flex;
  align-items: center;
}

.card-title h3 {
  margin: 0;
  font-size: 1.05rem;
  color: #1e293b;
}

.storage-metrics-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.metric-box {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.metric-box.highlight {
  background: #eff6ff;
  border-color: #bfdbfe;
}

.metric-label {
  font-size: 0.8rem;
  color: #64748b;
  margin-bottom: 4px;
}

.metric-value {
  font-size: 1.25rem;
  font-weight: 700;
  color: #0f172a;
}

.metric-sub {
  font-size: 0.75rem;
  color: #94a3b8;
  margin-top: 2px;
}

.cleanup-actions {
  display: flex;
  gap: 10px;
}

.cleanup-alert {
  margin-top: 14px;
  background: #f1f5f9;
  border-radius: 6px;
  padding: 8px 12px;
  font-size: 0.85rem;
  color: #334155;
  display: flex;
  align-items: center;
}

/* 分類標籤 */
.category-tabs {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding-bottom: 4px;
}

.tab-btn {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 8px 16px;
  font-size: 0.88rem;
  color: #475569;
  cursor: pointer;
  display: flex;
  align-items: center;
  white-space: nowrap;
  transition: all 0.2s ease;
}

.tab-btn:hover {
  background: #f8fafc;
  border-color: #cbd5e1;
}

.tab-btn.active {
  background: #0f172a;
  color: #ffffff;
  border-color: #0f172a;
  font-weight: 600;
}

/* 設定群組卡片 */
.category-group-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  margin-bottom: 20px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.group-header {
  background: #f8fafc;
  padding: 14px 20px;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  gap: 10px;
}

.group-icon {
  font-size: 1.15rem;
  color: #3b82f6;
}

.group-header h3 {
  margin: 0;
  font-size: 1.05rem;
  color: #0f172a;
  font-weight: 700;
}

.env-source-tag {
  margin-left: auto;
  font-size: 0.75rem;
  background: #e2e8f0;
  color: #475569;
  padding: 2px 8px;
  border-radius: 9999px;
  font-weight: 600;
}

.settings-items-list {
  display: flex;
  flex-direction: column;
}

.setting-item-row {
  display: grid;
  grid-template-columns: 1fr 380px;
  gap: 24px;
  padding: 18px 24px;
  border-bottom: 1px solid #f1f5f9;
  transition: background 0.15s ease;
}

.setting-item-row:last-child {
  border-bottom: none;
}

.setting-item-row:hover {
  background: #fafbfd;
}

.setting-item-row.changed {
  background: #f0fdf4;
}

.meta-title-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 6px;
}

.item-label {
  font-weight: 700;
  font-size: 0.95rem;
  color: #1e293b;
}

.env-key-badge {
  background: #f1f5f9;
  color: #475569;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.8rem;
  font-weight: 600;
}

.badge-restart {
  font-size: 0.75rem;
  color: #b45309;
  background: #fef3c7;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.badge-dynamic {
  font-size: 0.75rem;
  color: #047857;
  background: #d1fae5;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.badge-modified {
  font-size: 0.75rem;
  color: #15803d;
  background: #bbf7d0;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 700;
}

.item-description {
  margin: 0 0 6px 0;
  font-size: 0.85rem;
  color: #64748b;
  line-height: 1.45;
  white-space: pre-line;
}

.item-example-box {
  font-size: 0.8rem;
  color: #475569;
  background: #f8fafc;
  padding: 4px 8px;
  border-radius: 4px;
  border-left: 3px solid #38bdf8;
  display: inline-block;
}

.example-label {
  font-weight: 600;
  color: #64748b;
}

.item-example-box code {
  color: #0284c7;
  font-weight: 600;
}

.setting-item-control {
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.setting-input {
  width: 100%;
  padding: 9px 12px;
  padding-right: 36px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  font-size: 0.9rem;
  color: #0f172a;
  background: #ffffff;
  outline: none;
  font-family: inherit;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.setting-input:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2);
}

.btn-toggle-secret {
  position: absolute;
  right: 8px;
  background: transparent;
  border: none;
  color: #64748b;
  cursor: pointer;
  padding: 4px;
  font-size: 0.95rem;
}

.btn-toggle-secret:hover {
  color: #0f172a;
}

.original-val-hint {
  font-size: 0.75rem;
  color: #94a3b8;
  margin-top: 4px;
}

.original-val-hint code {
  color: #64748b;
}

/* Provider 切換 Banner */
.provider-switch-banner {
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
  padding: 14px 20px;
}

.provider-switch-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
  flex-wrap: wrap;
  gap: 6px;
}

.provider-switch-title {
  font-size: 0.88rem;
  font-weight: 700;
  color: #1e293b;
  display: flex;
  align-items: center;
}

.provider-switch-hint {
  font-size: 0.78rem;
  color: #64748b;
}

.provider-chips-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.provider-badge-btn {
  background: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 6px 12px;
  font-size: 0.82rem;
  color: #334155;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  transition: all 0.2s ease;
}

.provider-badge-btn:hover {
  background: #f1f5f9;
  border-color: #94a3b8;
}

.provider-badge-btn.active {
  background: #2563eb;
  border-color: #2563eb;
  color: #ffffff;
  font-weight: 600;
  box-shadow: 0 2px 4px rgba(37, 99, 235, 0.2);
}

.provider-badge-btn.active .provider-tag {
  background: rgba(255, 255, 255, 0.25);
  color: #ffffff;
}

.provider-tag {
  font-size: 0.72rem;
  background: #e2e8f0;
  color: #475569;
  padding: 1px 6px;
  border-radius: 4px;
}

.provider-select {
  cursor: pointer;
}

/* LLM 模型選擇專用樣式 */
.model-select-wrapper {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.model-input {
  padding-right: 96px !important;
}

.btn-fetch-models {
  position: absolute;
  right: 6px;
  background: #f1f5f9;
  border: 1px solid #cbd5e1;
  color: #334155;
  border-radius: 4px;
  padding: 4px 8px;
  font-size: 0.78rem;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  transition: all 0.2s ease;
}

.btn-fetch-models:hover:not(:disabled) {
  background: #e2e8f0;
  color: #0f172a;
}

.btn-fetch-models:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.model-dropdown-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 2px;
}

.model-dropdown-label {
  font-size: 0.8rem;
  color: #64748b;
  white-space: nowrap;
  display: flex;
  align-items: center;
  font-weight: 600;
}

.model-select {
  flex: 1;
  padding: 6px 10px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  font-size: 0.85rem;
  color: #1e293b;
  background-color: #f8fafc;
  outline: none;
  cursor: pointer;
}

.model-select:focus {
  border-color: #3b82f6;
  background-color: #ffffff;
}

.model-chips-list {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  margin-top: 2px;
}

.chips-label {
  font-size: 0.75rem;
  color: #64748b;
  font-weight: 600;
}

.model-chip {
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  border-radius: 9999px;
  padding: 2px 10px;
  font-size: 0.78rem;
  color: #334155;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  transition: all 0.15s ease;
  user-select: none;
}

.model-chip:hover {
  background: #e2e8f0;
  border-color: #cbd5e1;
}

.model-chip.active {
  background: #dbeafe;
  border-color: #93c5fd;
  color: #1d4ed8;
  font-weight: 600;
}

.model-status-hint {
  font-size: 0.75rem;
  color: #059669;
  display: flex;
  align-items: center;
  margin-top: 2px;
}

.model-status-hint.error {
  color: #d97706;
}

/* 浮動儲存列 */
.floating-save-bar {
  position: fixed;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  background: #0f172a;
  color: #ffffff;
  padding: 12px 24px;
  border-radius: 9999px;
  display: flex;
  align-items: center;
  gap: 20px;
  box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4);
  z-index: 900;
}

.save-bar-info {
  display: flex;
  align-items: center;
  font-size: 0.9rem;
}

.save-bar-info code {
  background: rgba(255, 255, 255, 0.2);
  padding: 2px 6px;
  border-radius: 4px;
}

.save-bar-actions {
  display: flex;
  gap: 8px;
}

/* 對話框樣式 */
.modal-backdrop {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(15, 23, 42, 0.6);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-dialog {
  background: #ffffff;
  border-radius: 12px;
  width: 480px;
  max-width: 90vw;
  padding: 24px;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.25);
}

.dialog-header {
  display: flex;
  align-items: center;
  margin-bottom: 12px;
}

.dialog-header h3 {
  margin: 0;
  font-size: 1.15rem;
  color: #0f172a;
}

.dialog-body {
  margin-bottom: 20px;
  line-height: 1.5;
  color: #334155;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

/* 重啟覆蓋遮罩 */
.reconnect-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(15, 23, 42, 0.85);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1100;
  color: #ffffff;
}

.reconnect-box {
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 16px;
  padding: 36px 44px;
  text-align: center;
  max-width: 460px;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
}

.spinner-icon {
  font-size: 3rem;
  color: #38bdf8;
  margin-bottom: 16px;
}

.reconnect-box h3 {
  margin: 0 0 10px 0;
  font-size: 1.35rem;
}

.reconnect-desc {
  font-size: 0.92rem;
  color: #94a3b8;
  margin-bottom: 20px;
  line-height: 1.5;
}

.ping-status {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: rgba(0, 0, 0, 0.3);
  padding: 6px 14px;
  border-radius: 9999px;
  font-size: 0.8rem;
  color: #cbd5e1;
}

.ping-dot {
  font-size: 0.6rem;
  color: #34d399;
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0% { opacity: 0.3; }
  50% { opacity: 1; }
  100% { opacity: 0.3; }
}

.text-primary {
  color: #3b82f6;
}

.text-danger {
  color: #ef4444;
}

.text-indigo {
  color: #6366f1;
}

.text-secondary {
  color: #64748b;
}

.text-sm {
  font-size: 0.85rem;
}

.mr-1 {
  margin-right: 0.25rem;
}

.mr-2 {
  margin-right: 0.5rem;
}

@media (max-width: 768px) {
  .setting-item-row {
    grid-template-columns: 1fr;
    gap: 12px;
  }
  .storage-metrics-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
