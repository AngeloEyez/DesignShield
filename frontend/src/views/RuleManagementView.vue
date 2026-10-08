<template>
  <div class="flex flex-col gap-6 p-6 bg-surface-ground min-h-screen">
    <!-- 頁頭 (Header) -->
    <div class="flex flex-col sm:flex-row justify-between items-start gap-4">
      <div>
        <h1 class="text-2xl font-bold m-0 mb-2 flex items-center text-surface-900 dark:text-surface-0">
          <i class="pi pi-book text-primary mr-2"></i>
          DRC 規則庫與知識庫中心
        </h1>
        <p class="text-surface-400 text-sm m-0">
          全域硬體檢查規範集中檢視中心，支援 GitOps File-based YAML 檔案架構與即時熱載入。
        </p>
      </div>
      <div class="flex gap-3">
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
    <div v-if="successMessage" class="flex items-center justify-between p-3 px-4 rounded-md text-sm bg-green-500/15 border border-green-500/30 text-green-400">
      <div class="flex items-center gap-2">
        <i class="pi pi-check-circle"></i>
        <span>{{ successMessage }}</span>
      </div>
      <button class="bg-transparent border-0 text-inherit cursor-pointer p-1" @click="successMessage = ''">
        <i class="pi pi-times"></i>
      </button>
    </div>

    <div v-if="errorMessage" class="flex flex-col gap-2 p-3 px-4 rounded-md text-sm bg-red-500/15 border border-red-500/30 text-red-400">
      <div class="flex items-center justify-between w-full">
        <div class="flex items-center gap-2">
          <i class="pi pi-exclamation-circle"></i>
          <span>{{ errorMessage }}</span>
        </div>
        <div class="flex items-center gap-3">
          <button
            v-if="validationErrors.length > 0"
            class="detail-toggle-btn inline-flex items-center gap-1 text-xs px-2 py-1 rounded bg-red-500/20 border border-red-500/40 text-red-200 hover:bg-red-500/30 cursor-pointer transition-colors"
            @click="showErrorDetails = !showErrorDetails"
          >
            {{ showErrorDetails ? '收起詳細錯誤' : `查看詳細錯誤 (${validationErrors.length})` }}
            <i :class="showErrorDetails ? 'pi pi-chevron-up' : 'pi pi-chevron-down'" class="text-xs ml-1"></i>
          </button>
          <button class="bg-transparent border-0 text-inherit cursor-pointer p-1" @click="clearErrorMessage">
            <i class="pi pi-times"></i>
          </button>
        </div>
      </div>
      <div v-if="showErrorDetails && validationErrors.length > 0" class="error-details-list bg-surface-900/60 border border-red-500/30 rounded p-2.5 max-h-52 overflow-y-auto flex flex-col gap-1.5 mt-1">
        <div v-for="(err, idx) in validationErrors" :key="idx" class="flex items-start gap-2 text-xs text-red-200 font-mono break-all">
          <i class="pi pi-times-circle text-red-500 text-xs mt-0.5 shrink-0"></i>
          <span class="leading-snug">{{ err }}</span>
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
    <div class="flex gap-2 border-b border-surface-border pb-2">
      <button
        type="button"
        class="tab-btn flex items-center px-4 py-2 text-sm font-semibold rounded-md border-0 cursor-pointer transition-colors"
        :class="activeTab === 'level3' ? 'text-primary bg-primary/10' : 'text-surface-400 hover:text-surface-0 hover:bg-surface-hover'"
        @click="activeTab = 'level3'"
      >
        <i class="pi pi-shield mr-2"></i>
        Level 3: DRC 驗證規範 ({{ level3Rules.length }})
      </button>
      <button
        type="button"
        class="tab-btn flex items-center px-4 py-2 text-sm font-semibold rounded-md border-0 cursor-pointer transition-colors"
        :class="activeTab === 'partdb' ? 'text-primary bg-primary/10' : 'text-surface-400 hover:text-surface-0 hover:bg-surface-hover'"
        @click="activeTab = 'partdb'"
      >
        <i class="pi pi-microchip mr-2"></i>
        PartDB: 零件特規庫 ({{ partdbParts.length }})
      </button>
      <button
        type="button"
        class="tab-btn flex items-center px-4 py-2 text-sm font-semibold rounded-md border-0 cursor-pointer transition-colors"
        :class="activeTab === 'level2' ? 'text-primary bg-primary/10' : 'text-surface-400 hover:text-surface-0 hover:bg-surface-hover'"
        @click="activeTab = 'level2'"
      >
        <i class="pi pi-sitemap mr-2"></i>
        Level 2: 網路拓撲與匯流排 ({{ level2Patterns.length }})
      </button>
      <button
        type="button"
        class="tab-btn flex items-center px-4 py-2 text-sm font-semibold rounded-md border-0 cursor-pointer transition-colors"
        :class="activeTab === 'level1' ? 'text-primary bg-primary/10' : 'text-surface-400 hover:text-surface-0 hover:bg-surface-hover'"
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
