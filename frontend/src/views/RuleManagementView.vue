<template>
  <div class="rule-management-view">
    <!-- 頂部頁頭導航與動作列 -->
    <div class="rules-header">
      <div class="header-left">
        <h1 class="page-title">
          <i class="pi pi-sliders-h text-primary mr-2"></i>
          DRC 規則庫管理 (Rule Library Management)
        </h1>
        <p class="page-subtitle">
          集中維護線路檢測規則庫，支援圖論啟發式規則 (HEURISTIC) 與本地大模型邏輯推理規則 (LLM)。
        </p>
      </div>

      <div class="header-actions">
        <Button
          label="重新整理"
          icon="pi pi-refresh"
          severity="secondary"
          size="small"
          :loading="isLoading"
          @click="loadRules"
        />
        <Button
          label="新增規則"
          icon="pi pi-plus"
          severity="primary"
          size="small"
          @click="openCreateModal"
        />
      </div>
    </div>

    <!-- 訊息提示橫幅 -->
    <div v-if="successMessage" class="alert-banner success-banner">
      <div class="alert-content">
        <i class="pi pi-check-circle alert-icon"></i>
        <span>{{ successMessage }}</span>
      </div>
      <button class="banner-close" @click="successMessage = ''">
        <i class="pi pi-times"></i>
      </button>
    </div>

    <div v-if="errorMessage" class="alert-banner error-banner">
      <div class="alert-content">
        <i class="pi pi-exclamation-circle alert-icon"></i>
        <span>{{ errorMessage }}</span>
      </div>
      <button class="banner-close" @click="errorMessage = ''">
        <i class="pi pi-times"></i>
      </button>
    </div>

    <!-- 統計指標卡片 -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-icon-wrapper bg-blue-light">
          <i class="pi pi-list text-blue"></i>
        </div>
        <div class="stat-info">
          <span class="stat-label">規則總筆數</span>
          <span class="stat-value">{{ rules.length }}</span>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon-wrapper bg-indigo-light">
          <i class="pi pi-code text-indigo"></i>
        </div>
        <div class="stat-info">
          <span class="stat-label">傳統演算法 (HEURISTIC)</span>
          <span class="stat-value">{{ heuristicCount }}</span>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon-wrapper bg-pink-light">
          <i class="pi pi-microchip-ai text-pink"></i>
        </div>
        <div class="stat-info">
          <span class="stat-label">本地大模型 (LLM)</span>
          <span class="stat-value">{{ llmCount }}</span>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon-wrapper bg-green-light">
          <i class="pi pi-check-circle text-green"></i>
        </div>
        <div class="stat-info">
          <span class="stat-label">啟用中規則</span>
          <span class="stat-value">{{ activeCount }}</span>
        </div>
      </div>
    </div>

    <!-- 搜尋與過濾工具列 -->
    <div class="filter-card">
      <div class="filter-controls">
        <div class="search-input-wrapper">
          <i class="pi pi-search search-icon"></i>
          <input
            v-model="searchQuery"
            type="text"
            placeholder="搜尋規則代碼、名稱、抽取器或參數..."
            class="filter-search-input"
          />
          <button
            v-if="searchQuery"
            type="button"
            class="clear-btn"
            @click="searchQuery = ''"
          >
            <i class="pi pi-times"></i>
          </button>
        </div>

        <div class="filter-select-group">
          <select v-model="selectedCategory" class="filter-select">
            <option value="">全部分類 ({{ categoryOptions.length }} 類)</option>
            <option v-for="cat in categoryOptions" :key="cat" :value="cat">
              {{ cat }}
            </option>
          </select>

          <select v-model="selectedCheckType" class="filter-select">
            <option value="">全部檢測型態</option>
            <option value="HEURISTIC">HEURISTIC (傳統圖論)</option>
            <option value="LLM">LLM (大模型邏輯)</option>
          </select>

          <select v-model="selectedStatus" class="filter-select">
            <option value="">全部狀態</option>
            <option value="active">僅啟用</option>
            <option value="inactive">僅停用</option>
          </select>
        </div>
      </div>

      <div class="filter-summary">
        <span>顯示 <strong>{{ filteredRules.length }}</strong> / {{ rules.length }} 筆規則</span>
      </div>
    </div>

    <!-- 規則表格清單 -->
    <div class="rules-table-container">
      <table class="rules-table">
        <thead>
          <tr>
            <th style="width: 200px;">規則代碼 (ID)</th>
            <th style="width: 240px;">規則中文名稱</th>
            <th style="width: 150px;">分類</th>
            <th style="width: 130px;">檢測方式</th>
            <th style="width: 90px;">狀態</th>
            <th>上下文抽取器 / 樣板摘要</th>
            <th style="width: 140px; text-align: center;">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="filteredRules.length === 0">
            <td colspan="7" class="empty-table-cell">
              <i class="pi pi-inbox mr-2"></i>
              <span>無符合條件之規則項目</span>
            </td>
          </tr>

          <tr v-for="rule in filteredRules" :key="rule.id" class="rule-row">
            <td>
              <span class="rule-id-badge">{{ rule.id }}</span>
            </td>
            <td>
              <span class="rule-title-text">{{ rule.name }}</span>
            </td>
            <td>
              <span class="category-tag">{{ rule.category }}</span>
            </td>
            <td>
              <Tag
                :value="rule.check_type"
                :severity="rule.check_type === 'LLM' ? 'warn' : 'info'"
                class="type-tag"
              />
            </td>
            <td>
              <Tag
                :value="rule.is_active ? '啟用' : '停用'"
                :severity="rule.is_active ? 'success' : 'secondary'"
                class="status-tag"
              />
            </td>
            <td>
              <div class="meta-preview">
                <span v-if="rule.context_extractor" class="extractor-preview" :title="rule.context_extractor">
                  <i class="pi pi-link mr-1"></i>{{ rule.context_extractor }}
                </span>
                <span v-if="rule.prompt_template" class="prompt-preview" :title="rule.prompt_template">
                  <i class="pi pi-comment mr-1"></i>LLM 提示詞設定
                </span>
                <span v-if="Object.keys(rule.parameters || {}).length > 0" class="param-preview">
                  <i class="pi pi-cog mr-1"></i>{{ Object.keys(rule.parameters).length }} 個參數
                </span>
                <span v-if="!rule.context_extractor && !rule.prompt_template && Object.keys(rule.parameters || {}).length === 0" class="empty-meta">
                  無附加參數
                </span>
              </div>
            </td>
            <td>
              <div class="row-actions">
                <Button
                  label="編輯"
                  icon="pi pi-pencil"
                  severity="secondary"
                  size="small"
                  text
                  @click="openEditModal(rule)"
                />
                <Button
                  label="刪除"
                  icon="pi pi-trash"
                  severity="danger"
                  size="small"
                  text
                  @click="confirmDeleteRule(rule)"
                />
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 新增 / 修改規則對話框 (Modal) -->
    <div v-if="showEditModal" class="modal-backdrop" @click.self="closeEditModal">
      <div class="modal-dialog rule-edit-dialog">
        <!-- 對話框頁首 -->
        <div class="dialog-header">
          <div class="dialog-title-wrapper">
            <i :class="modalMode === 'create' ? 'pi pi-plus-circle text-primary' : 'pi pi-pencil text-primary'" class="dialog-title-icon mr-2"></i>
            <h3>{{ modalMode === 'create' ? '新增 DRC 檢驗規則' : `修改規則: ${currentRuleForm.id}` }}</h3>
          </div>
          <button class="dialog-close-btn" @click="closeEditModal">
            <i class="pi pi-times"></i>
          </button>
        </div>

        <!-- 模式切換按鈕組 (UI Form vs Advanced JSON) -->
        <div class="dialog-mode-tabs">
          <button
            type="button"
            class="mode-tab-btn"
            :class="{ active: editMode === 'form' }"
            @click="switchEditMode('form')"
          >
            <i class="pi pi-file-edit mr-1"></i> 標準表單模式 (UI Form)
          </button>
          <button
            type="button"
            class="mode-tab-btn"
            :class="{ active: editMode === 'json' }"
            @click="switchEditMode('json')"
          >
            <i class="pi pi-code mr-1"></i> 進階 JSON 模式 (Advanced JSON)
          </button>
        </div>

        <!-- 對話框內容主體 -->
        <div class="dialog-body">
          <!-- 模式 1: 標準表單模式 -->
          <div v-if="editMode === 'form'" class="form-mode-content">
            <div class="form-grid">
              <!-- 必要欄位 1: 規則代碼 (ID) -->
              <div class="form-group">
                <label class="form-label required">
                  規則代碼 (ID)
                  <span class="required-star">*</span>
                </label>
                <input
                  v-model="currentRuleForm.id"
                  type="text"
                  class="form-input"
                  :disabled="modalMode === 'edit'"
                  placeholder="例如: RULE-PWR-CAP-DERATING"
                />
                <span class="form-help">
                  {{ modalMode === 'edit' ? '規則代碼為唯一主鍵，修改時不可變更' : '英數字與連字號組成之唯一識別代碼' }}
                </span>
              </div>

              <!-- 必要欄位 2: 檢測方式 (check_type) -->
              <div class="form-group">
                <label class="form-label required">
                  檢測方式 (Check Type)
                  <span class="required-star">*</span>
                </label>
                <select v-model="currentRuleForm.check_type" class="form-select">
                  <option value="HEURISTIC">HEURISTIC (傳統圖論演算法比對)</option>
                  <option value="LLM">LLM (本地大模型語意推理)</option>
                </select>
                <span class="form-help">傳統演算法速度極快；大模型適合複雜語意與引腳邏輯</span>
              </div>

              <!-- 必要欄位 3: 規則中文名稱 (name) -->
              <div class="form-group span-2">
                <label class="form-label required">
                  規則中文名稱 (Name)
                  <span class="required-star">*</span>
                </label>
                <input
                  v-model="currentRuleForm.name"
                  type="text"
                  class="form-input"
                  placeholder="例如: 電源濾波電容耐壓降額檢查"
                />
              </div>

              <!-- 必要欄位 4: 規則分類 (category) -->
              <div class="form-group">
                <label class="form-label required">
                  規則分類 (Category)
                  <span class="required-star">*</span>
                </label>
                <input
                  v-model="currentRuleForm.category"
                  type="text"
                  list="categoryList"
                  class="form-input"
                  placeholder="例如: Bus Integrity, Power Domain"
                />
                <datalist id="categoryList">
                  <option v-for="cat in categoryOptions" :key="cat" :value="cat" />
                  <option value="Bus Integrity" />
                  <option value="Power Domain" />
                  <option value="Pin Connection" />
                  <option value="Interface Mode" />
                  <option value="Signal Integrity" />
                </datalist>
                <span class="form-help">可直接輸入或自下拉推薦選單挑選</span>
              </div>

              <!-- 規則狀態 (is_active) -->
              <div class="form-group">
                <label class="form-label">啟用狀態 (Status)</label>
                <div class="toggle-switch-wrapper">
                  <label class="switch">
                    <input type="checkbox" v-model="currentRuleForm.is_active" />
                    <span class="slider round"></span>
                  </label>
                  <span class="toggle-label">{{ currentRuleForm.is_active ? '啟用 (Active)' : '停用 (Inactive)' }}</span>
                </div>
              </div>

              <!-- 上下文抽取器識別碼 -->
              <div class="form-group span-2">
                <label class="form-label">圖譜上下文抽取器識別碼 (Context Extractor)</label>
                <input
                  v-model="currentRuleForm.context_extractor"
                  type="text"
                  class="form-input"
                  placeholder="例如: extract_power_capacitors_context, extract_i2c_bus_context"
                />
                <span class="form-help">後端抽取電路子圖並餵入演算法或大模型的函式名稱</span>
              </div>

              <!-- LLM 專用提示詞樣板 -->
              <div v-if="currentRuleForm.check_type === 'LLM'" class="form-group span-2">
                <label class="form-label">
                  LLM 提示詞樣板 (Prompt Template)
                  <span class="badge-hint">LLM 模式專用</span>
                </label>
                <textarea
                  v-model="currentRuleForm.prompt_template"
                  rows="4"
                  class="form-textarea"
                  placeholder="輸入提示詞樣板，可使用 {context} 代表抽取出的電路圖譜上下文資訊..."
                ></textarea>
                <span class="form-help">樣板中可包含 {context} 作為電路網路連接關係佔位符</span>
              </div>

              <!-- 自訂參數 (Parameters JSON) -->
              <div class="form-group span-2">
                <label class="form-label">規則自訂參數 (Parameters - JSON)</label>
                <textarea
                  v-model="formParametersJson"
                  rows="3"
                  class="form-textarea font-mono"
                  placeholder='{"derating_factor": 0.5, "min_headroom_ratio": 0.3}'
                  @input="handleFormParametersInput"
                ></textarea>
                <span v-if="formParamsError" class="field-error-text">
                  <i class="pi pi-exclamation-triangle mr-1"></i>{{ formParamsError }}
                </span>
                <span v-else class="form-help">請填寫標準 JSON 物件格式（預設為 {}）</span>
              </div>
            </div>
          </div>

          <!-- 模式 2: 進階 JSON 模式 -->
          <div v-if="editMode === 'json'" class="json-mode-content">
            <div class="json-editor-header">
              <span class="json-editor-tip">
                <i class="pi pi-info-circle mr-1"></i>
                直接編輯規則完整 JSON 物件。系統會動態檢驗格式與必要欄位，全數符合方可儲存。
              </span>
              <button
                type="button"
                class="format-json-btn"
                @click="formatAdvancedJson"
                :disabled="!jsonValidation.isValidSyntax"
              >
                <i class="pi pi-align-left mr-1"></i> 格式化排版
              </button>
            </div>

            <textarea
              v-model="advancedJsonText"
              rows="14"
              class="advanced-json-textarea"
              spellcheck="false"
              placeholder="請輸入標準 JSON 格式..."
              @input="handleAdvancedJsonInput"
            ></textarea>

            <!-- 動態檢查檢驗狀態報告面板 (Dynamic Validation Feedback) -->
            <div class="validation-status-box" :class="{ valid: jsonValidation.isValid, invalid: !jsonValidation.isValid }">
              <div class="validation-status-header">
                <div class="validation-status-title">
                  <i :class="jsonValidation.isValid ? 'pi pi-check-circle text-green' : 'pi pi-exclamation-triangle text-danger'" class="mr-2"></i>
                  <span>{{ jsonValidation.isValid ? '動態檢驗通過：JSON 格式正確且必要欄位完整' : '動態檢驗未通過：請修正以下問題以啟用儲存' }}</span>
                </div>
              </div>

              <!-- 檢驗未通過時顯示錯誤清單 -->
              <ul v-if="!jsonValidation.isValid && jsonValidation.errors.length > 0" class="validation-error-list">
                <li v-for="(err, idx) in jsonValidation.errors" :key="idx" class="validation-error-item">
                  <i class="pi pi-times-circle text-danger mr-1"></i>
                  <span>{{ err }}</span>
                </li>
              </ul>
            </div>
          </div>
        </div>

        <!-- 對話框頁尾動作按鈕 -->
        <div class="dialog-footer">
          <div class="footer-left">
            <span v-if="editMode === 'form' && formValidationError" class="field-error-text">
              <i class="pi pi-exclamation-circle mr-1"></i>{{ formValidationError }}
            </span>
          </div>

          <div class="footer-buttons">
            <Button
              label="取消"
              severity="secondary"
              @click="closeEditModal"
            />
            <Button
              :label="modalMode === 'create' ? '確定建立' : '儲存修改'"
              icon="pi pi-check"
              severity="primary"
              :loading="isSaving"
              :disabled="isSaveDisabled"
              @click="submitRuleForm"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- 刪除確認對話框 -->
    <div v-if="showDeleteConfirm" class="modal-backdrop" @click.self="showDeleteConfirm = false">
      <div class="modal-dialog delete-confirm-dialog">
        <div class="dialog-header">
          <i class="pi pi-trash text-danger mr-2"></i>
          <h3>確認刪除規則？</h3>
        </div>
        <div class="dialog-body">
          <p>
            您即將從系統規則庫中永久刪除以下規則：
          </p>
          <div class="delete-rule-target">
            <strong class="text-danger">{{ ruleToDelete?.id }}</strong>
            <span class="target-name">({{ ruleToDelete?.name }})</span>
          </div>
          <p class="text-secondary text-sm">
            此操作將從資料庫中移除該規則設定，後續 DRC 檢測任務將無法再選用此規則。請確認是否繼續？
          </p>
        </div>
        <div class="dialog-footer">
          <Button label="取消" severity="secondary" @click="showDeleteConfirm = false" />
          <Button
            label="確認刪除"
            icon="pi pi-trash"
            severity="danger"
            :loading="isDeleting"
            @click="executeDeleteRule"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * @file RuleManagementView.vue
 * @description DRC 規則庫管理頁面，支援規則增刪查改、UI 欄位填寫與進階 JSON 模式動態檢核
 */

import { ref, computed, onMounted } from 'vue'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import type { DrcRuleItem, RuleCreatePayload, RuleUpdatePayload, RuleCheckType } from '@/types/rule'
import { fetchRules, createRule, updateRule, deleteRule } from '@/services/api'

// 規則資料集與狀態
const rules = ref<DrcRuleItem[]>([])
const isLoading = ref<boolean>(false)
const isSaving = ref<boolean>(false)
const isDeleting = ref<boolean>(false)

// 提示訊息
const successMessage = ref<string>('')
const errorMessage = ref<string>('')

// 搜尋過濾條件
const searchQuery = ref<string>('')
const selectedCategory = ref<string>('')
const selectedCheckType = ref<string>('')
const selectedStatus = ref<string>('')

// 新增 / 編輯對話框狀態
const showEditModal = ref<boolean>(false)
const modalMode = ref<'create' | 'edit'>('create')
const editMode = ref<'form' | 'json'>('form')

// 刪除確認對話框狀態
const showDeleteConfirm = ref<boolean>(false)
const ruleToDelete = ref<DrcRuleItem | null>(null)

// 編輯表單資料模型
const currentRuleForm = ref<{
  id: string
  name: string
  category: string
  check_type: RuleCheckType
  is_active: boolean
  parameters: Record<string, any>
  prompt_template: string
  context_extractor: string
}>({
  id: '',
  name: '',
  category: '',
  check_type: 'HEURISTIC',
  is_active: true,
  parameters: {},
  prompt_template: '',
  context_extractor: '',
})

// 表單模式下的 parameters JSON 字串
const formParametersJson = ref<string>('{}')
const formParamsError = ref<string>('')

// 進階 JSON 模式下的原始編輯文字
const advancedJsonText = ref<string>('')

/**
 * 載入所有規則清單
 */
const loadRules = async () => {
  isLoading.value = true
  errorMessage.value = ''
  try {
    const data = await fetchRules()
    rules.value = data
  } catch (err: any) {
    console.error('載入規則庫失敗:', err)
    errorMessage.value = err?.response?.data?.detail || '載入規則清單失敗，請檢查伺服器連線狀態'
  } finally {
    isLoading.value = false
  }
}

onMounted(() => {
  loadRules()
})

// 統計數據
const heuristicCount = computed(() => rules.value.filter((r) => r.check_type === 'HEURISTIC').length)
const llmCount = computed(() => rules.value.filter((r) => r.check_type === 'LLM').length)
const activeCount = computed(() => rules.value.filter((r) => r.is_active).length)

// 現有分類清單
const categoryOptions = computed(() => {
  const cats = new Set<string>()
  rules.value.forEach((r) => {
    if (r.category) cats.add(r.category)
  })
  return Array.from(cats).sort()
})

// 過濾後的規則清單
const filteredRules = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  return rules.value.filter((rule) => {
    if (selectedCategory.value && rule.category !== selectedCategory.value) {
      return false
    }
    if (selectedCheckType.value && rule.check_type !== selectedCheckType.value) {
      return false
    }
    if (selectedStatus.value === 'active' && !rule.is_active) {
      return false
    }
    if (selectedStatus.value === 'inactive' && rule.is_active) {
      return false
    }
    if (q) {
      const matchId = rule.id.toLowerCase().includes(q)
      const matchName = rule.name.toLowerCase().includes(q)
      const matchCategory = rule.category.toLowerCase().includes(q)
      const matchExtractor = (rule.context_extractor || '').toLowerCase().includes(q)
      const matchParams = JSON.stringify(rule.parameters || {}).toLowerCase().includes(q)
      return matchId || matchName || matchCategory || matchExtractor || matchParams
    }
    return true
  })
})

/**
 * 開啟新增規則對話框
 */
const openCreateModal = () => {
  modalMode.value = 'create'
  editMode.value = 'form'
  currentRuleForm.value = {
    id: '',
    name: '',
    category: '',
    check_type: 'HEURISTIC',
    is_active: true,
    parameters: {},
    prompt_template: '',
    context_extractor: '',
  }
  formParametersJson.value = '{}'
  formParamsError.value = ''
  syncFormToJson()
  showEditModal.value = true
}

/**
 * 開啟編輯規則對話框
 */
const openEditModal = (rule: DrcRuleItem) => {
  modalMode.value = 'edit'
  editMode.value = 'form'
  currentRuleForm.value = {
    id: rule.id,
    name: rule.name,
    category: rule.category,
    check_type: rule.check_type,
    is_active: rule.is_active,
    parameters: rule.parameters ? { ...rule.parameters } : {},
    prompt_template: rule.prompt_template || '',
    context_extractor: rule.context_extractor || '',
  }
  formParametersJson.value = JSON.stringify(rule.parameters || {}, null, 2)
  formParamsError.value = ''
  syncFormToJson()
  showEditModal.value = true
}

/**
 * 關閉編輯對話框
 */
const closeEditModal = () => {
  showEditModal.value = false
}

/**
 * 將目前表單狀態同步至進階 JSON 文本
 */
const syncFormToJson = () => {
  let params = currentRuleForm.value.parameters
  try {
    params = JSON.parse(formParametersJson.value)
  } catch {
    // 保留既有物件
  }

  const jsonObj: Record<string, any> = {
    id: currentRuleForm.value.id,
    name: currentRuleForm.value.name,
    category: currentRuleForm.value.category,
    check_type: currentRuleForm.value.check_type,
    is_active: currentRuleForm.value.is_active,
    parameters: params,
    context_extractor: currentRuleForm.value.context_extractor || null,
  }

  if (currentRuleForm.value.check_type === 'LLM' || currentRuleForm.value.prompt_template) {
    jsonObj.prompt_template = currentRuleForm.value.prompt_template || null
  }

  advancedJsonText.value = JSON.stringify(jsonObj, null, 2)
}

/**
 * 將進階 JSON 同步至表單欄位
 */
const syncJsonToForm = () => {
  if (!jsonValidation.value.isValid) return
  try {
    const parsed = JSON.parse(advancedJsonText.value)
    if (modalMode.value === 'create') {
      currentRuleForm.value.id = parsed.id || ''
    }
    currentRuleForm.value.name = parsed.name || ''
    currentRuleForm.value.category = parsed.category || ''
    currentRuleForm.value.check_type = parsed.check_type || 'HEURISTIC'
    currentRuleForm.value.is_active = parsed.is_active ?? true
    currentRuleForm.value.parameters = parsed.parameters || {}
    currentRuleForm.value.prompt_template = parsed.prompt_template || ''
    currentRuleForm.value.context_extractor = parsed.context_extractor || ''
    formParametersJson.value = JSON.stringify(parsed.parameters || {}, null, 2)
  } catch {
    // ignore
  }
}

/**
 * 切換編輯模式 (UI 表單 vs 進階 JSON)
 */
const switchEditMode = (mode: 'form' | 'json') => {
  if (mode === editMode.value) return
  if (mode === 'json') {
    syncFormToJson()
    editMode.value = 'json'
  } else {
    // 從 JSON 切換回 Form: 檢查 JSON 是否合法
    if (jsonValidation.value.isValid) {
      syncJsonToForm()
      editMode.value = 'form'
    } else {
      // 提示使用者先修復 JSON 錯誤
      errorMessage.value = '切換回表單前請先修復 JSON 格式與必要欄位錯誤'
      setTimeout(() => {
        if (errorMessage.value.includes('切換回表單')) errorMessage.value = ''
      }, 3000)
    }
  }
}

/**
 * 處理表單自訂參數文字變更
 */
const handleFormParametersInput = () => {
  try {
    const parsed = JSON.parse(formParametersJson.value)
    if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
      formParamsError.value = '自訂參數必須為 JSON 物件 (如 {"key": "val"})'
    } else {
      formParamsError.value = ''
      currentRuleForm.value.parameters = parsed
    }
  } catch (err: any) {
    formParamsError.value = `JSON 格式錯誤: ${err.message}`
  }
}

/**
 * 處理進階 JSON 模式輸入
 */
const handleAdvancedJsonInput = () => {
  // 自動由 computed jsonValidation 處理動態檢查
}

/**
 * 格式化排版進階 JSON
 */
const formatAdvancedJson = () => {
  try {
    const parsed = JSON.parse(advancedJsonText.value)
    advancedJsonText.value = JSON.stringify(parsed, null, 2)
  } catch {
    // ignore
  }
}

/**
 * 進階 JSON 動態驗證物件
 */
interface JsonValidationResult {
  isValid: boolean
  isValidSyntax: boolean
  errors: string[]
  parsedData: any
}

const jsonValidation = computed<JsonValidationResult>(() => {
  const raw = advancedJsonText.value.trim()
  if (!raw) {
    return {
      isValid: false,
      isValidSyntax: false,
      errors: ['JSON 不得為空'],
      parsedData: null,
    }
  }

  let parsed: any
  try {
    parsed = JSON.parse(raw)
  } catch (err: any) {
    return {
      isValid: false,
      isValidSyntax: false,
      errors: [`JSON 語法錯誤: ${err.message}`],
      parsedData: null,
    }
  }

  if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
    return {
      isValid: false,
      isValidSyntax: true,
      errors: ['最外層必須為 JSON 物件 (即以 { } 包裹)'],
      parsedData: parsed,
    }
  }

  const errors: string[] = []

  // 必要欄位 1: id
  if (modalMode.value === 'create') {
    if (!parsed.id || typeof parsed.id !== 'string' || !parsed.id.trim()) {
      errors.push("缺少必要欄位 'id' (規則代碼不可為空)")
    } else if (!/^[A-Za-z0-9_-]+$/.test(parsed.id.trim())) {
      errors.push("欄位 'id' 格式不符，僅允許英數字、底線與連字號")
    }
  } else {
    // 編輯模式: id 必須存在且相符
    if (!parsed.id || parsed.id !== currentRuleForm.value.id) {
      errors.push(`編輯模式下不可修改規則代碼 'id'，必須維持為 '${currentRuleForm.value.id}'`)
    }
  }

  // 必要欄位 2: name
  if (!parsed.name || typeof parsed.name !== 'string' || !parsed.name.trim()) {
    errors.push("缺少必要欄位 'name' (規則中文名稱不可為空)")
  }

  // 必要欄位 3: category
  if (!parsed.category || typeof parsed.category !== 'string' || !parsed.category.trim()) {
    errors.push("缺少必要欄位 'category' (規則分類不可為空)")
  }

  // 必要欄位 4: check_type
  if (!parsed.check_type || !['HEURISTIC', 'LLM'].includes(parsed.check_type)) {
    errors.push("缺少或不正確的必要欄位 'check_type' (檢測方式必須為 'HEURISTIC' 或 'LLM')")
  }

  // 其他型態檢驗
  if (parsed.parameters !== undefined && (typeof parsed.parameters !== 'object' || parsed.parameters === null || Array.isArray(parsed.parameters))) {
    errors.push("欄位 'parameters' 若填寫必須為 JSON 物件 (例如 {})")
  }

  return {
    isValid: errors.length === 0,
    isValidSyntax: true,
    errors,
    parsedData: parsed,
  }
})

/**
 * 表單模式欄位錯誤檢查
 */
const formValidationError = computed<string>(() => {
  if (modalMode.value === 'create' && !currentRuleForm.value.id.trim()) {
    return '請填寫規則代碼 (ID)'
  }
  if (!currentRuleForm.value.name.trim()) {
    return '請填寫規則中文名稱'
  }
  if (!currentRuleForm.value.category.trim()) {
    return '請填寫規則分類'
  }
  if (!['HEURISTIC', 'LLM'].includes(currentRuleForm.value.check_type)) {
    return '請選取合法的檢測方式'
  }
  if (formParamsError.value) {
    return formParamsError.value
  }
  return ''
})

/**
 * 儲存按鈕是否處於禁用狀態
 */
const isSaveDisabled = computed<boolean>(() => {
  if (editMode.value === 'json') {
    return !jsonValidation.value.isValid
  } else {
    return Boolean(formValidationError.value)
  }
})

/**
 * 提交儲存規則 (建立或更新)
 */
const submitRuleForm = async () => {
  errorMessage.value = ''
  successMessage.value = ''

  let payloadData: any = {}

  if (editMode.value === 'json') {
    if (!jsonValidation.value.isValid) return
    payloadData = { ...jsonValidation.value.parsedData }
  } else {
    if (formValidationError.value) return
    let params = currentRuleForm.value.parameters
    try {
      params = JSON.parse(formParametersJson.value)
    } catch {
      params = {}
    }

    payloadData = {
      id: currentRuleForm.value.id.trim(),
      name: currentRuleForm.value.name.trim(),
      category: currentRuleForm.value.category.trim(),
      check_type: currentRuleForm.value.check_type,
      is_active: currentRuleForm.value.is_active,
      parameters: params,
      prompt_template: currentRuleForm.value.prompt_template || null,
      context_extractor: currentRuleForm.value.context_extractor || null,
    }
  }

  isSaving.value = true

  try {
    if (modalMode.value === 'create') {
      const createPayload: RuleCreatePayload = {
        id: payloadData.id,
        name: payloadData.name,
        category: payloadData.category,
        check_type: payloadData.check_type,
        is_active: payloadData.is_active ?? true,
        parameters: payloadData.parameters || {},
        prompt_template: payloadData.prompt_template,
        context_extractor: payloadData.context_extractor,
      }
      await createRule(createPayload)
      successMessage.value = `規則 [${createPayload.id}] 建立成功！`
    } else {
      const updatePayload: RuleUpdatePayload = {
        name: payloadData.name,
        category: payloadData.category,
        check_type: payloadData.check_type,
        is_active: payloadData.is_active,
        parameters: payloadData.parameters,
        prompt_template: payloadData.prompt_template,
        context_extractor: payloadData.context_extractor,
      }
      await updateRule(currentRuleForm.value.id, updatePayload)
      successMessage.value = `規則 [${currentRuleForm.value.id}] 更新成功！`
    }

    closeEditModal()
    await loadRules()
  } catch (err: any) {
    console.error('儲存規則失敗:', err)
    errorMessage.value = err?.response?.data?.detail || '儲存規則失敗，請檢查輸入內容或伺服器紀錄'
  } finally {
    isSaving.value = false
  }
}

/**
 * 開啟刪除確認對話框
 */
const confirmDeleteRule = (rule: DrcRuleItem) => {
  ruleToDelete.value = rule
  showDeleteConfirm.value = true
}

/**
 * 執行刪除規則
 */
const executeDeleteRule = async () => {
  if (!ruleToDelete.value) return
  isDeleting.value = true
  errorMessage.value = ''
  successMessage.value = ''

  try {
    const deletedId = ruleToDelete.value.id
    await deleteRule(deletedId)
    successMessage.value = `規則 [${deletedId}] 已成功自系統中刪除！`
    showDeleteConfirm.value = false
    ruleToDelete.value = null
    await loadRules()
  } catch (err: any) {
    console.error('刪除規則失敗:', err)
    errorMessage.value = err?.response?.data?.detail || '刪除規則失敗，請稍後重試'
  } finally {
    isDeleting.value = false
  }
}
</script>

<style scoped>
.rule-management-view {
  padding: 1.5rem 2rem;
  max-width: 1440px;
  margin: 0 auto;
}

.rules-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #ffffff;
  padding: 1.25rem 1.75rem;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  margin-bottom: 1.25rem;
  gap: 1rem;
}

.page-title {
  margin: 0 0 0.3rem 0;
  font-size: 1.35rem;
  font-weight: 700;
  color: #0f172a;
  display: flex;
  align-items: center;
}

.page-subtitle {
  margin: 0;
  font-size: 0.85rem;
  color: #64748b;
}

.header-actions {
  display: flex;
  gap: 0.75rem;
  flex-shrink: 0;
}

/* 警示橫幅 */
.alert-banner {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.85rem 1.25rem;
  border-radius: 6px;
  margin-bottom: 1.25rem;
  font-size: 0.9rem;
  animation: fadeIn 0.25s ease;
}

.success-banner {
  background-color: #f0fdf4;
  border: 1px solid #bbf7d0;
  color: #166534;
}

.error-banner {
  background-color: #fef2f2;
  border: 1px solid #fecaca;
  color: #991b1b;
}

.alert-content {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}

.alert-icon {
  font-size: 1.1rem;
}

.banner-close {
  background: transparent;
  border: none;
  cursor: pointer;
  color: inherit;
  opacity: 0.7;
}

.banner-close:hover {
  opacity: 1;
}

/* 統計指標卡片 */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1rem;
  margin-bottom: 1.25rem;
}

@media (max-width: 900px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

.stat-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 1rem 1.25rem;
  display: flex;
  align-items: center;
  gap: 1rem;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
}

.stat-icon-wrapper {
  width: 44px;
  height: 44px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.25rem;
  flex-shrink: 0;
}

.bg-blue-light { background: #eff6ff; }
.bg-indigo-light { background: #e0e7ff; }
.bg-pink-light { background: #fdf2f8; }
.bg-green-light { background: #f0fdf4; }

.text-blue { color: #2563eb; }
.text-indigo { color: #4f46e5; }
.text-pink { color: #db2777; }
.text-green { color: #16a34a; }

.stat-info {
  display: flex;
  flex-direction: column;
}

.stat-label {
  font-size: 0.78rem;
  color: #64748b;
  font-weight: 500;
}

.stat-value {
  font-size: 1.45rem;
  font-weight: 700;
  color: #0f172a;
}

/* 過濾列 */
.filter-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 0.85rem 1.25rem;
  margin-bottom: 1.25rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
}

.filter-controls {
  display: flex;
  gap: 0.85rem;
  align-items: center;
  flex: 1;
  flex-wrap: wrap;
}

.search-input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
  min-width: 280px;
  flex: 1;
}

.search-icon {
  position: absolute;
  left: 0.75rem;
  color: #94a3b8;
  font-size: 0.85rem;
}

.filter-search-input {
  width: 100%;
  padding: 0.45rem 2rem 0.45rem 2.25rem;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  font-size: 0.85rem;
  outline: none;
  transition: all 0.15s;
}

.filter-search-input:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15);
}

.clear-btn {
  position: absolute;
  right: 0.5rem;
  background: transparent;
  border: none;
  color: #94a3b8;
  cursor: pointer;
  padding: 0.2rem;
}

.filter-select-group {
  display: flex;
  gap: 0.5rem;
}

.filter-select {
  padding: 0.45rem 0.75rem;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  background-color: #ffffff;
  font-size: 0.85rem;
  color: #334155;
  outline: none;
}

.filter-summary {
  font-size: 0.825rem;
  color: #64748b;
  flex-shrink: 0;
}

/* 規則表格 */
.rules-table-container {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  margin-bottom: 2rem;
}

.rules-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
  font-size: 0.875rem;
}

.rules-table thead th {
  background-color: #f8fafc;
  color: #475569;
  font-weight: 600;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid #e2e8f0;
  font-size: 0.82rem;
  letter-spacing: 0.02em;
}

.rules-table tbody td {
  padding: 0.85rem 1rem;
  border-bottom: 1px solid #f1f5f9;
  vertical-align: middle;
}

.rule-row:hover {
  background-color: #f8fafc;
}

.rule-id-badge {
  background: #f1f5f9;
  color: #334155;
  border: 1px solid #cbd5e1;
  font-family: monospace;
  font-size: 0.78rem;
  padding: 0.15rem 0.45rem;
  border-radius: 4px;
  font-weight: 600;
  display: inline-block;
}

.rule-title-text {
  font-weight: 600;
  color: #0f172a;
}

.category-tag {
  color: #475569;
  background: #f1f5f9;
  padding: 0.15rem 0.5rem;
  border-radius: 4px;
  font-size: 0.78rem;
  display: inline-block;
}

.type-tag,
.status-tag {
  font-size: 0.72rem;
}

.meta-preview {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  font-size: 0.78rem;
}

.extractor-preview {
  color: #0284c7;
  background: #f0f9ff;
  border: 1px solid #e0f2fe;
  padding: 0.1rem 0.4rem;
  border-radius: 4px;
  max-width: 200px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.prompt-preview {
  color: #7c3aed;
  background: #f5f3ff;
  border: 1px solid #ede9fe;
  padding: 0.1rem 0.4rem;
  border-radius: 4px;
}

.param-preview {
  color: #b45309;
  background: #fefce8;
  border: 1px solid #fef08a;
  padding: 0.1rem 0.4rem;
  border-radius: 4px;
}

.empty-meta {
  color: #94a3b8;
  font-style: italic;
}

.row-actions {
  display: flex;
  justify-content: center;
  gap: 0.25rem;
}

.empty-table-cell {
  text-align: center;
  padding: 3rem !important;
  color: #94a3b8;
  font-style: italic;
}

/* Modal 對話框 */
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
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.25);
  display: flex;
  flex-direction: column;
}

.rule-edit-dialog {
  width: 760px;
  max-width: 95vw;
  max-height: 90vh;
}

.delete-confirm-dialog {
  width: 480px;
  max-width: 90vw;
  padding: 24px;
}

.dialog-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.25rem 1.5rem;
  border-bottom: 1px solid #f1f5f9;
}

.dialog-title-wrapper {
  display: flex;
  align-items: center;
}

.dialog-title-wrapper h3 {
  margin: 0;
  font-size: 1.2rem;
  color: #0f172a;
  font-weight: 700;
}

.dialog-close-btn {
  background: transparent;
  border: none;
  font-size: 1rem;
  color: #94a3b8;
  cursor: pointer;
  padding: 0.25rem;
}

.dialog-close-btn:hover {
  color: #475569;
}

/* 模式切換按鈕 */
.dialog-mode-tabs {
  display: flex;
  background: #f8fafc;
  padding: 0.5rem 1.5rem;
  border-bottom: 1px solid #e2e8f0;
  gap: 0.5rem;
}

.mode-tab-btn {
  background: transparent;
  border: 1px solid transparent;
  color: #64748b;
  font-size: 0.85rem;
  padding: 0.35rem 0.75rem;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
  transition: all 0.15s;
  display: inline-flex;
  align-items: center;
}

.mode-tab-btn:hover {
  color: #1e293b;
  background: #e2e8f0;
}

.mode-tab-btn.active {
  background: #ffffff;
  border-color: #cbd5e1;
  color: #2563eb;
  font-weight: 600;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.dialog-body {
  padding: 1.25rem 1.5rem;
  overflow-y: auto;
  flex: 1;
}

/* 表單樣式 */
.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.25rem;
}

.form-group {
  display: flex;
  flex-direction: column;
}

.span-2 {
  grid-column: span 2;
}

.form-label {
  font-size: 0.85rem;
  font-weight: 600;
  color: #334155;
  margin-bottom: 0.35rem;
  display: flex;
  align-items: center;
}

.required-star {
  color: #ef4444;
  margin-left: 0.25rem;
}

.form-input,
.form-select,
.form-textarea {
  padding: 0.5rem 0.75rem;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  font-size: 0.875rem;
  outline: none;
  color: #1e293b;
  transition: border-color 0.15s;
}

.form-input:focus,
.form-select:focus,
.form-textarea:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15);
}

.form-input:disabled {
  background: #f1f5f9;
  color: #64748b;
  cursor: not-allowed;
}

.form-help {
  font-size: 0.75rem;
  color: #64748b;
  margin-top: 0.25rem;
}

.field-error-text {
  font-size: 0.78rem;
  color: #ef4444;
  margin-top: 0.25rem;
  display: flex;
  align-items: center;
}

.font-mono {
  font-family: monospace;
}

.badge-hint {
  font-size: 0.7rem;
  background: #fdf2f8;
  color: #db2777;
  padding: 0.1rem 0.4rem;
  border-radius: 4px;
  margin-left: 0.5rem;
  font-weight: normal;
}

/* 開關 Toggle Switch */
.toggle-switch-wrapper {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-top: 0.35rem;
}

.switch {
  position: relative;
  display: inline-block;
  width: 44px;
  height: 24px;
}

.switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: #cbd5e1;
  transition: 0.2s;
  border-radius: 24px;
}

.slider:before {
  position: absolute;
  content: "";
  height: 18px;
  width: 18px;
  left: 3px;
  bottom: 3px;
  background-color: white;
  transition: 0.2s;
  border-radius: 50%;
}

input:checked + .slider {
  background-color: #10b981;
}

input:checked + .slider:before {
  transform: translateX(20px);
}

.toggle-label {
  font-size: 0.85rem;
  color: #334155;
  font-weight: 500;
}

/* 進階 JSON 編輯器樣式 */
.json-mode-content {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.json-editor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.json-editor-tip {
  font-size: 0.8rem;
  color: #64748b;
}

.format-json-btn {
  background: #f1f5f9;
  border: 1px solid #cbd5e1;
  color: #334155;
  font-size: 0.75rem;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  cursor: pointer;
}

.format-json-btn:hover:not(:disabled) {
  background: #e2e8f0;
}

.format-json-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.advanced-json-textarea {
  width: 100%;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 0.85rem;
  line-height: 1.5;
  padding: 0.75rem 1rem;
  background: #f8fafc;
  color: #0f172a;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  outline: none;
  resize: vertical;
}

.advanced-json-textarea:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15);
}

/* 動態檢驗狀態反饋框 */
.validation-status-box {
  padding: 0.75rem 1rem;
  border-radius: 6px;
  border: 1px solid;
  transition: all 0.2s ease;
}

.validation-status-box.valid {
  background-color: #f0fdf4;
  border-color: #bbf7d0;
  color: #166534;
}

.validation-status-box.invalid {
  background-color: #fef2f2;
  border-color: #fecaca;
  color: #991b1b;
}

.validation-status-header {
  display: flex;
  align-items: center;
  font-size: 0.85rem;
  font-weight: 600;
}

.validation-error-list {
  margin: 0.5rem 0 0 0;
  padding-left: 1.25rem;
  font-size: 0.8rem;
  list-style-type: none;
}

.validation-error-item {
  display: flex;
  align-items: center;
  margin-bottom: 0.25rem;
}

/* 對話框頁尾 */
.dialog-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.5rem;
  border-top: 1px solid #f1f5f9;
  background: #f8fafc;
  border-radius: 0 0 12px 12px;
}

.footer-buttons {
  display: flex;
  gap: 0.75rem;
}

/* 刪除對話框專屬樣式 */
.delete-rule-target {
  background: #fef2f2;
  border: 1px solid #fee2e2;
  padding: 0.6rem 0.85rem;
  border-radius: 6px;
  margin: 0.75rem 0;
  font-family: monospace;
  font-size: 0.9rem;
}

.target-name {
  color: #475569;
  font-family: sans-serif;
  margin-left: 0.5rem;
}

.text-danger {
  color: #ef4444;
}

.text-secondary {
  color: #64748b;
}

.text-sm {
  font-size: 0.825rem;
}

.text-primary {
  color: #3b82f6;
}

.mr-1 {
  margin-right: 0.25rem;
}

.mr-2 {
  margin-right: 0.5rem;
}
</style>
