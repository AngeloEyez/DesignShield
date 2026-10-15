<template>
  <div class="flex flex-col gap-6 p-6 bg-surface-ground min-h-screen">
    <!-- 頁頭 (Header) -->
    <div class="flex flex-col sm:flex-row justify-between items-start gap-4">
      <div>
        <h1 class="text-2xl font-bold m-0 flex items-center text-white">
          <i class="pi pi-book text-sky-400 mr-2"></i>
          DRC 規則庫與知識庫中心
        </h1>
      </div>
      <div class="flex gap-3">
        <Button
          label="重新載入規則庫"
          icon="pi pi-refresh"
          severity="primary"
          size="small"
          :loading="isLoading"
          @click="handleReloadPatterns"
        />
        <Button
          label="GitOps 貢獻手冊"
          icon="pi pi-book"
          severity="secondary"
          size="small"
          @click="showGitOpsGuide = true"
        />
      </div>
    </div>

    <!-- 訊息提示橫幅 -->
    <div v-if="successMessage" class="flex items-center justify-between p-3 px-4 rounded-md text-sm bg-emerald-500/15 border border-emerald-500/30 text-emerald-400">
      <div class="flex items-center gap-2">
        <i class="pi pi-check-circle"></i>
        <span>{{ successMessage }}</span>
      </div>
      <button class="bg-transparent border-0 text-inherit cursor-pointer p-1" @click="successMessage = ''">
        <i class="pi pi-times"></i>
      </button>
    </div>

    <div v-if="errorMessage" class="flex flex-col gap-2 p-3 px-4 rounded-md text-sm bg-rose-500/15 border border-rose-500/30 text-rose-400">
      <div class="flex items-center justify-between w-full">
        <div class="flex items-center gap-2">
          <i class="pi pi-exclamation-circle"></i>
          <span>{{ errorMessage }}</span>
        </div>
        <div class="flex items-center gap-3">
          <button
            v-if="validationErrors.length > 0"
            class="detail-toggle-btn inline-flex items-center gap-1 text-xs px-2 py-1 rounded bg-rose-500/20 border border-rose-500/40 text-rose-200 hover:bg-rose-500/30 cursor-pointer transition-colors"
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
      <div v-if="showErrorDetails && validationErrors.length > 0" class="error-details-list bg-[#1e1e1e] border border-rose-500/30 rounded p-2.5 max-h-52 overflow-y-auto flex flex-col gap-1.5 mt-1">
        <div v-for="(err, idx) in validationErrors" :key="idx" class="flex items-start gap-2 text-xs text-rose-200 font-mono break-all">
          <i class="pi pi-times-circle text-rose-500 text-xs mt-0.5 shrink-0"></i>
          <span class="leading-snug">{{ err }}</span>
        </div>
      </div>
    </div>

    <!-- 統計指標卡片 (按照 Level 3 -> 2 -> 1 -> PartDB 排序，點擊快速過濾並雙向連動) -->
    <RuleStatsGrid
      :active-tab="currentSelectedLevel"
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

// 點擊統計卡片快速聯動目錄樹過濾層級 (支援 Toggle 與雙向連動)
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

// 即時開關規則狀態更新
const handleToggleRule = async (payload: { ruleName: string; enabled: boolean }) => {
  try {
    const res = await updateRuleEnabled(payload.ruleName, payload.enabled)
    successMessage.value = res.message || `規則 ${payload.ruleName} 狀態已成功切換`
    // 同步更新本地 state
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
