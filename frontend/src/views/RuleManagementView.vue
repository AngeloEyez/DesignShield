<template>
  <div class="rules-management-container">
    <!-- 頁頭 (Header) -->
    <div class="rules-header">
      <div>
        <h1 class="page-title">
          <i class="pi pi-book text-primary mr-2"></i>
          DRC 規則庫與知識庫中心
        </h1>
        <p class="page-subtitle">
          全域硬體檢查規範集中檢視中心，支援 GitOps File-based YAML 檔案架構與即時熱載入。
        </p>
      </div>
      <div class="header-actions">
        <Button
          label="重新載入規則庫"
          icon="pi pi-refresh"
          severity="secondary"
          size="small"
          :loading="isLoading"
          @click="handleReloadPatterns"
        />
        <Button
          label="GitOps 貢獻手冊"
          icon="pi pi-book"
          severity="primary"
          size="small"
          @click="showGitOpsGuide = true"
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

    <div v-if="errorMessage" class="alert-banner error-banner flex-col-banner">
      <div class="banner-main-row">
        <div class="alert-content">
          <i class="pi pi-exclamation-circle alert-icon"></i>
          <span>{{ errorMessage }}</span>
        </div>
        <div class="banner-actions">
          <button
            v-if="validationErrors.length > 0"
            class="detail-toggle-btn"
            @click="showErrorDetails = !showErrorDetails"
          >
            {{ showErrorDetails ? '收起詳細錯誤' : `查看詳細錯誤 (${validationErrors.length})` }}
            <i :class="showErrorDetails ? 'pi pi-chevron-up' : 'pi pi-chevron-down'" style="font-size: 0.75rem; margin-left: 4px;"></i>
          </button>
          <button class="banner-close" @click="clearErrorMessage">
            <i class="pi pi-times"></i>
          </button>
        </div>
      </div>
      <div v-if="showErrorDetails && validationErrors.length > 0" class="error-details-list">
        <div v-for="(err, idx) in validationErrors" :key="idx" class="error-item">
          <i class="pi pi-times-circle error-item-icon"></i>
          <span class="error-item-text">{{ err }}</span>
        </div>
      </div>
    </div>

    <!-- 統計指標卡片 -->
    <RuleStatsGrid
      :active-tab="activeTab"
      :level3-count="level3Rules.length"
      :partdb-count="partdbParts.length"
      :level2-count="level2Patterns.length"
      :level1-count="level1Patterns.length"
      @select-tab="activeTab = $event"
    />

    <!-- 分頁切換選單 (Navigation Tabs) -->
    <div class="tabs-nav">
      <button
        type="button"
        class="tab-btn"
        :class="{ active: activeTab === 'level3' }"
        @click="activeTab = 'level3'"
      >
        <i class="pi pi-shield mr-2"></i>
        Level 3: DRC 驗證規範 ({{ level3Rules.length }})
      </button>
      <button
        type="button"
        class="tab-btn"
        :class="{ active: activeTab === 'partdb' }"
        @click="activeTab = 'partdb'"
      >
        <i class="pi pi-microchip mr-2"></i>
        PartDB: 零件特規庫 ({{ partdbParts.length }})
      </button>
      <button
        type="button"
        class="tab-btn"
        :class="{ active: activeTab === 'level2' }"
        @click="activeTab = 'level2'"
      >
        <i class="pi pi-sitemap mr-2"></i>
        Level 2: 網路拓撲與匯流排 ({{ level2Patterns.length }})
      </button>
      <button
        type="button"
        class="tab-btn"
        :class="{ active: activeTab === 'level1' }"
        @click="activeTab = 'level1'"
      >
        <i class="pi pi-th-large mr-2"></i>
        Level 1: 元件辨識規範 ({{ level1Patterns.length }})
      </button>
    </div>

    <!-- 分頁內容組件 -->
    <Level3RulesTab
      v-show="activeTab === 'level3'"
      :rules="level3Rules"
      :all-tags="allTags"
      @view-yaml="openYamlModal"
    />

    <PartDbTab
      v-show="activeTab === 'partdb'"
      :parts="partdbParts"
      @view-yaml="openYamlModal"
    />

    <Level2TopologyTab
      v-show="activeTab === 'level2'"
      :patterns="level2Patterns"
      @view-yaml="openYamlModal"
    />

    <Level1ComponentsTab
      v-show="activeTab === 'level1'"
      :patterns="level1Patterns"
      @view-yaml="openYamlModal"
    />

    <!-- YAML 原始檔檢視對話框 (Modal) -->
    <YamlViewerModal
      v-model:visible="showYamlModal"
      :filename="currentYamlFilename"
      :code="currentYamlCode"
    />

    <!-- GitOps 貢獻指引對話框 (Modal) -->
    <GitOpsGuideModal
      v-model:visible="showGitOpsGuide"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import Button from 'primevue/button'
import { fetchPatternTree, reloadPatterns } from '@/services/api'
import type {
  PatternTreeResponse,
  Level3RuleItem,
  Level2PatternItem,
  Level1PatternItem,
  PartDBItem,
} from '@/types/pattern'

import RuleStatsGrid from '@/components/rules/RuleStatsGrid.vue'
import Level3RulesTab from '@/components/rules/Level3RulesTab.vue'
import PartDbTab from '@/components/rules/PartDbTab.vue'
import Level2TopologyTab from '@/components/rules/Level2TopologyTab.vue'
import Level1ComponentsTab from '@/components/rules/Level1ComponentsTab.vue'
import YamlViewerModal from '@/components/rules/YamlViewerModal.vue'
import GitOpsGuideModal from '@/components/rules/GitOpsGuideModal.vue'

// 狀態控制
const activeTab = ref<'level3' | 'partdb' | 'level2' | 'level1'>('level3')
const isLoading = ref<boolean>(false)
const successMessage = ref<string>('')
const errorMessage = ref<string>('')
const validationErrors = ref<string[]>([])
const showErrorDetails = ref<boolean>(false)

const clearErrorMessage = () => {
  errorMessage.value = ''
  validationErrors.value = []
  showErrorDetails.value = false
}

// 規則資料結構
const level3Rules = ref<Level3RuleItem[]>([])
const level2Patterns = ref<Level2PatternItem[]>([])
const level1Patterns = ref<Level1PatternItem[]>([])
const partdbParts = ref<PartDBItem[]>([])
const allTags = ref<string[]>([])

// YAML 彈跳檢視視窗狀態
const showYamlModal = ref<boolean>(false)
const currentYamlFilename = ref<string>('')
const currentYamlCode = ref<string>('')

// GitOps 說明彈窗狀態
const showGitOpsGuide = ref<boolean>(false)

// 開啟 YAML 彈窗
const openYamlModal = (filename: string, code: string) => {
  currentYamlFilename.value = filename
  currentYamlCode.value = code
  showYamlModal.value = true
}

// 載入資料
const loadPatternData = async () => {
  isLoading.value = true
  try {
    const data: PatternTreeResponse = await fetchPatternTree()
    level1Patterns.value = data.level1 || []
    level2Patterns.value = data.level2 || []
    level3Rules.value = data.level3 || []
    partdbParts.value = data.partdb?.parts || []
    allTags.value = data.tags || []
  } catch (err: any) {
    errorMessage.value = `載入規則庫失敗: ${err.message || err}`
  } finally {
    isLoading.value = false
  }
}

// 重新載入規則與編譯快取 (Reload & Recompile)
const handleReloadPatterns = async () => {
  isLoading.value = true
  successMessage.value = ''
  clearErrorMessage()
  try {
    const res = await reloadPatterns()
    if (!res.success) {
      errorMessage.value = res.message || 'YAML 校驗失敗，已取消編譯'
      validationErrors.value = res.errors || []
      return
    }
    await loadPatternData()
    const stats = res.compile_stats
    if (stats) {
      successMessage.value = `${res.message} (Level 1: ${stats.level1_rules}, Level 2: ${stats.level2_rules}, Level 3: ${stats.level3_rules}, PartDB: ${stats.partdb_parts}, Regex 快取: ${stats.regex_compiled})`
    } else {
      successMessage.value = `${res.message} (共載入 Level 3: ${level3Rules.value.length} 條, PartDB: ${partdbParts.value.length} 顆晶片)`
    }
  } catch (err: any) {
    const responseData = err.response?.data
    if (responseData && responseData.errors && responseData.errors.length > 0) {
      errorMessage.value = responseData.message || 'YAML 校驗失敗，已取消編譯'
      validationErrors.value = responseData.errors
    } else {
      errorMessage.value = `重新載入失敗: ${responseData?.message || err.message || err}`
    }
  } finally {
    isLoading.value = false
  }
}

onMounted(() => {
  loadPatternData()
})
</script>

<style scoped>
.rules-management-container {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  padding: 1.5rem;
  background-color: var(--surface-ground, #0b1120);
  min-height: 100vh;
}

/* 頁頭 */
.rules-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.page-title {
  font-size: 1.5rem;
  font-weight: 700;
  margin: 0 0 0.5rem 0;
  display: flex;
  align-items: center;
}

.page-subtitle {
  color: #94a3b8;
  font-size: 0.875rem;
  margin: 0;
}

.header-actions {
  display: flex;
  gap: 0.75rem;
}

/* 提示橫幅 */
.alert-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1rem;
  border-radius: 6px;
  font-size: 0.875rem;
}

.flex-col-banner {
  flex-direction: column;
  align-items: stretch;
  gap: 0.5rem;
}

.banner-main-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

.banner-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.detail-toggle-btn {
  background: rgba(239, 68, 68, 0.2);
  border: 1px solid rgba(239, 68, 68, 0.4);
  color: #fca5a5;
  font-size: 0.75rem;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  transition: all 0.2s ease;
}

.detail-toggle-btn:hover {
  background: rgba(239, 68, 68, 0.3);
  color: #ffffff;
}

.error-details-list {
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 4px;
  padding: 0.5rem 0.75rem;
  max-height: 200px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  margin-top: 0.25rem;
}

.error-item {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  font-size: 0.8rem;
  color: #fecaca;
  font-family: monospace;
  word-break: break-all;
}

.error-item-icon {
  margin-top: 2px;
  color: #ef4444;
  font-size: 0.8rem;
  flex-shrink: 0;
}

.error-item-text {
  line-height: 1.3;
}

.success-banner {
  background-color: rgba(34, 197, 94, 0.15);
  border: 1px solid rgba(34, 197, 94, 0.3);
  color: #4ade80;
}

.error-banner {
  background-color: rgba(239, 68, 68, 0.15);
  border: 1px solid rgba(239, 68, 68, 0.3);
  color: #f87171;
}

.banner-close {
  background: none;
  border: none;
  color: inherit;
  cursor: pointer;
}

/* 分頁切換選單 */
.tabs-nav {
  display: flex;
  gap: 0.5rem;
  border-bottom: 1px solid #334155;
  padding-bottom: 0.5rem;
}

.tab-btn {
  background: none;
  border: none;
  color: #94a3b8;
  padding: 0.6rem 1rem;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  border-radius: 6px;
  display: flex;
  align-items: center;
  transition: all 0.2s ease;
}

.tab-btn:hover {
  color: #f8fafc;
  background-color: rgba(255, 255, 255, 0.05);
}

.tab-btn.active {
  color: var(--primary-color, #38bdf8);
  background-color: rgba(56, 189, 248, 0.1);
}
</style>
