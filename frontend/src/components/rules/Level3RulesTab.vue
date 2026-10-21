<template>
  <div class="tab-content flex flex-col gap-3">
    <!-- 搜尋與篩選工具列 -->
    <div class="filter-card bg-surface-card border border-surface-border rounded p-3 flex flex-col gap-2">
      <div class="filter-controls flex gap-2 flex-wrap">
        <div class="search-input-wrapper relative flex-1 min-w-[220px]">
          <i class="pi pi-search search-icon absolute left-2.5 top-1/2 -translate-y-1/2 text-surface-400 text-xs"></i>
          <input
            v-model="searchQuery"
            type="text"
            placeholder="搜尋 Level 3 規則名稱、說明、標籤或網域..."
            class="filter-search-input w-full pl-7 pr-7 py-1 h-7 bg-surface-ground border border-surface-border rounded text-surface-0 text-xs focus:outline-none focus:border-primary-500"
          />
          <button
            v-if="searchQuery"
            type="button"
            class="clear-btn absolute right-2 top-1/2 -translate-y-1/2 text-surface-400 hover:text-surface-0 cursor-pointer p-0.5 bg-transparent border-0"
            @click="searchQuery = ''"
          >
            <i class="pi pi-times text-[10px]"></i>
          </button>
        </div>

        <div class="filter-select-group flex gap-2 flex-wrap">
          <select v-model="selectedDomain" class="filter-select px-2 py-1 h-7 bg-surface-ground border border-surface-border rounded text-surface-100 text-xs focus:outline-none focus:border-primary-500">
            <option value="">全部網域 (All Domains)</option>
            <option v-for="d in level3Domains" :key="d" :value="d">
              {{ d }}
            </option>
          </select>

          <select v-model="selectedSeverity" class="filter-select px-2 py-1 h-7 bg-surface-ground border border-surface-border rounded text-surface-100 text-xs focus:outline-none focus:border-primary-500">
            <option value="">全部嚴重等級 (All Severities)</option>
            <option value="Fatal">Fatal (致命異常)</option>
            <option value="Error">Error (嚴重違規)</option>
            <option value="Warning">Warning (潛在警告)</option>
            <option value="Info">Info (提示資訊)</option>
          </select>

          <select v-model="selectedTag" class="filter-select px-2 py-1 h-7 bg-surface-ground border border-surface-border rounded text-surface-100 text-xs focus:outline-none focus:border-primary-500">
            <option value="">全部標籤 (All Tags)</option>
            <option v-for="t in allTags" :key="t" :value="t">
              {{ t }}
            </option>
          </select>

          <select v-model="selectedStatus" class="filter-status-select px-2 py-1 h-7 bg-surface-ground border border-surface-border rounded text-surface-100 text-xs focus:outline-none focus:border-primary-500">
            <option value="">全部狀態 (All Statuses)</option>
            <option value="enabled">僅顯示已啟用 (Enabled)</option>
            <option value="disabled">僅顯示已停用 (Disabled)</option>
          </select>
        </div>
      </div>

      <div class="filter-summary text-xs text-surface-400">
        <span>顯示 <strong class="text-surface-0">{{ filteredRules.length }}</strong> / {{ rules.length }} 條 DRC 規則</span>
      </div>
    </div>

    <!-- Level 3 規則卡片列表 -->
    <div class="rules-grid grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
      <div v-if="filteredRules.length === 0" class="empty-placeholder col-span-full p-8 text-center text-surface-400 bg-surface-panel border border-dashed border-surface-border rounded">
        <i class="pi pi-inbox text-2xl mb-2 text-surface-500 block"></i>
        <p class="m-0 text-xs">無符合條件之 Level 3 DRC 規則項目</p>
      </div>

      <div
        v-for="rule in filteredRules"
        :key="rule.name"
        class="rule-card bg-surface-panel border border-surface-border rounded flex flex-col overflow-hidden transition-all border-l-4"
        :class="{
          'opacity-60': rule.enabled === false,
          'border-l-red-500': rule.severity === 'Fatal' || rule.severity === 'Error',
          'border-l-amber-500': rule.severity === 'Warning',
          'border-l-primary-500': rule.severity !== 'Fatal' && rule.severity !== 'Error' && rule.severity !== 'Warning'
        }"
      >
        <div class="rule-card-header px-3 py-2 bg-surface-card border-b border-surface-border flex justify-between items-center">
          <div class="header-badges flex gap-1.5 items-center flex-wrap">
            <Tag
              :value="rule.enabled === false ? '已停用' : '啟用'"
              :severity="rule.enabled === false ? 'secondary' : 'success'"
              class="status-tag text-[10px] px-1.5 py-0.2 rounded font-normal"
            />
            <span
              class="severity-badge text-[10px] font-semibold px-1.5 py-0.2 rounded flex items-center font-mono"
              :class="{
                'bg-red-500/15 text-red-500': rule.severity === 'Fatal' || rule.severity === 'Error',
                'bg-amber-500/15 text-amber-500': rule.severity === 'Warning',
                'bg-surface-panel text-surface-300 border border-surface-border': rule.severity !== 'Fatal' && rule.severity !== 'Error' && rule.severity !== 'Warning'
              }"
            >
              {{ rule.severity }}
            </span>
            <span class="domain-badge bg-surface-panel border border-surface-border text-surface-300 text-[10px] px-1.5 py-0.2 rounded flex items-center font-mono">
              <i class="pi pi-folder mr-1 text-[10px]"></i>{{ rule._domain }}
            </span>
          </div>
          <button
            type="button"
            v-tooltip.left="'查看原始 YAML 檔'"
            class="yaml-view-btn bg-surface-panel hover:bg-surface-hover border border-surface-border text-primary-400 text-xs p-1 rounded flex items-center transition-colors cursor-pointer"
            @click="$emit('view-yaml', rule._filename, rule._raw_yaml)"
          >
            <i class="pi pi-file-code text-xs"></i>
            <span class="sr-only">YAML</span>
          </button>
        </div>

        <div class="rule-card-body p-3 flex flex-col gap-2 flex-1">
          <h3 class="rule-title text-xs font-semibold text-surface-0 font-mono break-all m-0">{{ rule.name }}</h3>
          <p class="rule-desc text-xs text-surface-300 leading-relaxed m-0">{{ rule.description || '無詳細說明' }}</p>

          <div class="rule-meta-section flex flex-col gap-1 pt-2 border-t border-surface-border">
            <div class="meta-item flex items-center gap-2 text-xs">
              <span class="meta-label text-surface-400 min-w-[60px]">檢查機制:</span>
              <span class="meta-value check-type-pill bg-primary-500/15 text-primary-400 px-1.5 py-0.2 rounded text-[11px] font-mono inline-flex items-center">
                {{ formatCheckLogicType(rule.check_logic) }}
              </span>
            </div>
            <div class="meta-item flex items-center gap-2 text-xs">
              <span class="meta-label text-surface-400 min-w-[60px]">關聯標籤:</span>
              <div class="tags-container flex flex-wrap gap-1">
                <span v-for="tag in rule.tags" :key="tag" class="rule-tag-chip bg-surface-card border border-surface-border text-surface-300 text-[10px] px-1.5 py-0.2 rounded">
                  {{ tag }}
                </span>
              </div>
            </div>
          </div>

          <!-- 觸發條件預覽 -->
          <div class="rule-condition-box pt-1.5 border-t border-surface-border flex flex-col gap-0.5 mt-auto">
            <span class="cond-title text-[10px] text-surface-400 font-semibold uppercase">觸發特徵:</span>
            <code class="cond-code font-mono text-[11px] text-primary-400 break-all">
              {{ formatTriggerSummary(rule.trigger_conditions) }}
            </code>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * @file Level3RulesTab.vue
 * @description Level 3 DRC 規則卡片頁籤 (2026 雙主題版)
 */

import { ref, computed } from 'vue'
import Tag from 'primevue/tag'
import type { Level3RuleItem } from '@/types/pattern'

const props = defineProps<{
  rules: Level3RuleItem[]
  allTags: string[]
}>()

defineEmits<{
  (e: 'view-yaml', filename: string, rawYaml: string): void
}>()

const searchQuery = ref<string>('')
const selectedDomain = ref<string>('')
const selectedSeverity = ref<string>('')
const selectedTag = ref<string>('')
const selectedStatus = ref<string>('')

const level3Domains = computed(() => {
  const set = new Set<string>()
  props.rules.forEach((r) => {
    if (r._domain) set.add(r._domain)
  })
  return Array.from(set).sort()
})

const filteredRules = computed(() => {
  return props.rules.filter((rule) => {
    if (searchQuery.value) {
      const q = searchQuery.value.toLowerCase()
      const matchName = rule.name.toLowerCase().includes(q)
      const matchDesc = (rule.description || '').toLowerCase().includes(q)
      const matchDomain = (rule._domain || '').toLowerCase().includes(q)
      const matchTag = (rule.tags || []).some((t) => t.toLowerCase().includes(q))
      if (!matchName && !matchDesc && !matchDomain && !matchTag) return false
    }

    if (selectedDomain.value && rule._domain !== selectedDomain.value) {
      return false
    }

    if (selectedSeverity.value && rule.severity !== selectedSeverity.value) {
      return false
    }

    if (selectedTag.value && !(rule.tags || []).includes(selectedTag.value)) {
      return false
    }

    if (selectedStatus.value === 'enabled' && rule.enabled === false) {
      return false
    }

    if (selectedStatus.value === 'disabled' && rule.enabled !== false) {
      return false
    }

    return true
  })
})

const formatCheckLogicType = (cl: any) => {
  if (!cl) return '未定義'
  if (Array.isArray(cl)) {
    return cl.map((item) => item.type).join(', ')
  }
  return cl.type || '自訂'
}

const formatTriggerSummary = (cond: any) => {
  if (!cond) return '無特定條件'
  try {
    const parts = []
    if (cond.target_entity) parts.push(`目標: ${cond.target_entity}`)
    if (cond.component_features) {
      const cf = cond.component_features
      if (cf.sub_category) parts.push(`次分類: ${cf.sub_category}`)
      if (cf.functional_role) parts.push(`角色: ${cf.functional_role}`)
    }
    if (cond.net_features) {
      const nf = cond.net_features
      if (nf.classification) parts.push(`網路: ${nf.classification}`)
      if (nf.operating_voltage) parts.push(`電壓: ${nf.operating_voltage}`)
    }
    return parts.length > 0 ? parts.join(' | ') : JSON.stringify(cond)
  } catch {
    return String(cond)
  }
}
</script>
