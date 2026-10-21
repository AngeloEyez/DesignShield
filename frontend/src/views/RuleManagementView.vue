<template>
  <div class="flex flex-col bg-surface-ground min-h-screen text-vscode-textMain">
    <!-- 頂部緊湊頁頭列 (1px Grid Border) -->
    <div class="flex items-center justify-between gap-3 px-4 py-2 bg-surface-card border-b border-surface-border">
      <div class="flex items-center gap-2">
        <i class="pi pi-book text-primary text-sm"></i>
        <h1 class="text-sm font-semibold m-0 text-vscode-textHeading">
          DRC 規則庫與知識庫中心
        </h1>
      </div>
      <div class="flex items-center gap-1.5">
        <Button
          v-tooltip.bottom="'重新掃描磁碟並編譯 YAML 規則庫'"
          icon="pi pi-refresh"
          severity="primary"
          size="small"
          :loading="isLoading"
          class="!w-7 !h-7 !p-0"
          @click="handleReloadPatterns"
        >
          <i class="pi pi-refresh text-xs" :class="{ 'pi-spin': isLoading }"></i>
          <span class="sr-only">重新載入規則庫</span>
        </Button>
        <Button
          v-tooltip.bottom="'檢視 GitOps 規則庫維護與貢獻指引'"
          icon="pi pi-book"
          severity="secondary"
          size="small"
          outlined
          class="!w-7 !h-7 !p-0"
          @click="showGitOpsGuide = true"
        >
          <i class="pi pi-book text-xs"></i>
          <span class="sr-only">GitOps 貢獻手冊</span>
        </Button>
      </div>
    </div>

    <!-- 訊息提示橫幅 -->
    <div v-if="successMessage" class="flex items-center justify-between px-4 py-1.5 text-xs bg-emerald-500/10 border-b border-emerald-500/30 text-emerald-500">
      <div class="flex items-center gap-2">
        <i class="pi pi-check-circle text-xs"></i>
        <span>{{ successMessage }}</span>
      </div>
      <button type="button" class="bg-transparent border-0 text-inherit cursor-pointer p-0.5" @click="successMessage = ''">
        <i class="pi pi-times text-xs"></i>
      </button>
    </div>

    <div v-if="errorMessage" class="flex flex-col gap-1.5 px-4 py-2 text-xs bg-red-500/10 border-b border-red-500/30 text-red-500">
      <div class="flex items-center justify-between w-full">
        <div class="flex items-center gap-2">
          <i class="pi pi-exclamation-circle text-xs"></i>
          <span>{{ errorMessage }}</span>
        </div>
        <div class="flex items-center gap-2">
          <button
            v-if="validationErrors.length > 0"
            type="button"
            class="detail-toggle-btn inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded bg-red-500/15 border border-red-500/30 text-red-500 hover:bg-red-500/25 cursor-pointer transition-colors"
            @click="showErrorDetails = !showErrorDetails"
          >
            {{ showErrorDetails ? '收起詳細錯誤' : `查看詳細錯誤 (${validationErrors.length})` }}
            <i :class="showErrorDetails ? 'pi pi-chevron-up' : 'pi pi-chevron-down'" class="text-[10px] ml-0.5"></i>
          </button>
          <button type="button" class="bg-transparent border-0 text-inherit cursor-pointer p-0.5" @click="clearErrorMessage">
            <i class="pi pi-times text-xs"></i>
          </button>
        </div>
      </div>
      <div v-if="showErrorDetails && validationErrors.length > 0" class="error-details-list bg-surface-panel border border-red-500/30 rounded p-2 max-h-48 overflow-y-auto flex flex-col gap-1 mt-0.5">
        <div v-for="(err, idx) in validationErrors" :key="idx" class="flex items-start gap-1.5 text-xs text-red-500 font-mono break-all">
          <i class="pi pi-times-circle text-red-500 text-xs mt-0.5 shrink-0"></i>
          <span class="leading-snug">{{ err }}</span>
        </div>
      </div>
    </div>

    <!-- 頂部 40px 單行統計指標橫條 (按照 Level 3 -> 2 -> 1 -> PartDB 排序，點擊快速過濾並雙向連動) -->
    <RuleStatsGrid
      :active-tab="currentSelectedLevel as any"
      :level3-count="level3Rules.length"
      :partdb-count="partdbParts.length"
      :level2-count="level2Patterns.length"
      :level1-count="level1Patterns.length"
      @select-tab="handleQuickFilterLevel"
    />

    <!-- 統一目錄結構樹檢視 (TreeTable，支援層級下拉選單雙向連動) -->
    <RuleDirectoryTree
      ref="ruleTreeRef"
      v-model:selected-level="currentSelectedLevel"
      :level1-rules="level1Patterns"
      :level2-rules="level2Patterns"
      :level3-rules="level3Rules"
      :partdb-parts="partdbParts"
      :all-tags="allTags"
      @toggle-rule="handleToggleRule"
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
/**
 * @file RuleManagementView.vue
 * @description DRC 規則庫與知識庫中心頁面 (2026 緊湊雙主題 1px 網格版)
 */

import { ref, onMounted } from 'vue'
import Button from 'primevue/button'
import type {
  PatternTreeResponse,
  Level3RuleItem,
  Level2PatternItem,
  Level1PatternItem,
  PartDBItem,
} from '@/types/pattern'

import RuleStatsGrid from '@/components/rules/RuleStatsGrid.vue'
import RuleDirectoryTree from '@/components/rules/RuleDirectoryTree.vue'
import YamlViewerModal from '@/components/rules/YamlViewerModal.vue'
import GitOpsGuideModal from '@/components/rules/GitOpsGuideModal.vue'
import { fetchPatternTree, reloadPatterns, updateRuleEnabled } from '@/services/api'

// 狀態控制
const ruleTreeRef = ref<any>(null)
const currentSelectedLevel = ref<string>('')
const isLoading = ref<boolean>(false)
const successMessage = ref<string>('')
const errorMessage = ref<string>('')
const validationErrors = ref<string[]>([])
const showErrorDetails = ref<boolean>(false)

/**
 * 點擊統計指標橫條快速聯動目錄樹過濾層級 (支援 Toggle 與雙向連動)
 */
const handleQuickFilterLevel = (level: string) => {
  if (currentSelectedLevel.value === level) {
    currentSelectedLevel.value = ''
  } else {
    currentSelectedLevel.value = level
  }
}

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

/**
 * 即時開關規則狀態更新
 */
const handleToggleRule = async (payload: { ruleName: string; enabled: boolean }) => {
  try {
    const res = await updateRuleEnabled(payload.ruleName, payload.enabled)
    successMessage.value = res.message || `規則 ${payload.ruleName} 狀態已成功切換`
    for (const r of level1Patterns.value) {
      if (r.name === payload.ruleName) r.enabled = payload.enabled
    }
    for (const r of level2Patterns.value) {
      if (r.name === payload.ruleName) r.enabled = payload.enabled
    }
    for (const r of level3Rules.value) {
      if (r.name === payload.ruleName) r.enabled = payload.enabled
    }
  } catch (err: any) {
    const msg = err.response?.data?.detail || err.message || err
    errorMessage.value = `更新規則 '${payload.ruleName}' 失敗: ${msg}`
  }
}

// YAML 彈跳檢視視窗狀態
const showYamlModal = ref<boolean>(false)
const currentYamlFilename = ref<string>('')
const currentYamlCode = ref<string>('')

// GitOps 說明彈窗狀態
const showGitOpsGuide = ref<boolean>(false)

/**
 * 載入規則庫目錄樹資料
 */
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

/**
 * 重新載入規則與編譯快取 (Reload & Recompile)
 */
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
