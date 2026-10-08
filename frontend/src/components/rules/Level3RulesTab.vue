<template>
  <div class="tab-content flex flex-col gap-5">
    <!-- 搜尋與篩選工具列 -->
    <div class="filter-card bg-slate-800/80 border border-slate-700 rounded-lg p-4 sm:p-5 flex flex-col gap-3 shadow-sm">
      <div class="filter-controls flex gap-3 flex-wrap">
        <div class="search-input-wrapper relative flex-1 min-w-[260px]">
          <i class="pi pi-search search-icon absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-sm"></i>
          <input
            v-model="searchQuery"
            type="text"
            placeholder="搜尋 Level 3 規則名稱、說明、標籤或網域..."
            class="filter-search-input w-full pl-9 pr-8 py-2 bg-slate-900 border border-slate-700 rounded-md text-slate-100 text-sm focus:outline-none focus:border-sky-400"
          />
          <button
            v-if="searchQuery"
            type="button"
            class="clear-btn absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200 cursor-pointer p-0.5"
            @click="searchQuery = ''"
          >
            <i class="pi pi-times text-xs"></i>
          </button>
        </div>

        <div class="filter-select-group flex gap-3 flex-wrap">
          <select v-model="selectedDomain" class="filter-select px-3 py-2 bg-slate-900 border border-slate-700 rounded-md text-slate-100 text-sm focus:outline-none focus:border-sky-400">
            <option value="">全部網域 (All Domains)</option>
            <option v-for="d in level3Domains" :key="d" :value="d">
              {{ d }}
            </option>
          </select>

          <select v-model="selectedSeverity" class="filter-select px-3 py-2 bg-slate-900 border border-slate-700 rounded-md text-slate-100 text-sm focus:outline-none focus:border-sky-400">
            <option value="">全部嚴重等級 (All Severities)</option>
            <option value="Fatal">Fatal (致命異常)</option>
            <option value="Error">Error (嚴重違規)</option>
            <option value="Warning">Warning (潛在警告)</option>
            <option value="Info">Info (提示資訊)</option>
          </select>

          <select v-model="selectedTag" class="filter-select px-3 py-2 bg-slate-900 border border-slate-700 rounded-md text-slate-100 text-sm focus:outline-none focus:border-sky-400">
            <option value="">全部標籤 (All Tags)</option>
            <option v-for="t in allTags" :key="t" :value="t">
              {{ t }}
            </option>
          </select>
        </div>
      </div>

      <div class="filter-summary text-xs text-slate-400">
        <span>顯示 <strong>{{ filteredRules.length }}</strong> / {{ rules.length }} 條 DRC 規則</span>
      </div>
    </div>

    <!-- Level 3 規則卡片列表 -->
    <div class="rules-grid grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <div v-if="filteredRules.length === 0" class="empty-placeholder col-span-full p-12 text-center text-slate-400 bg-slate-800/80 border border-dashed border-slate-700 rounded-lg">
        <i class="pi pi-inbox text-4xl mb-3 text-slate-500"></i>
        <p class="m-0">無符合條件之 Level 3 DRC 規則項目</p>
      </div>

      <div
        v-for="rule in filteredRules"
        :key="rule.name"
        class="rule-card bg-slate-800/80 border border-slate-700 rounded-lg flex flex-col overflow-hidden hover:-translate-y-0.5 hover:shadow-lg transition-all"
        :class="{
          'border-t-4 border-t-red-500': rule.severity === 'Fatal',
          'border-t-4 border-t-orange-500': rule.severity === 'Error',
          'border-t-4 border-t-amber-500': rule.severity === 'Warning',
          'border-t-4 border-t-sky-500': rule.severity !== 'Fatal' && rule.severity !== 'Error' && rule.severity !== 'Warning'
        }"
      >
        <div class="rule-card-header px-4 py-3 bg-slate-900/60 border-b border-slate-700 flex justify-between items-center">
          <div class="header-badges flex gap-2 items-center">
            <span
              class="severity-badge text-xs font-semibold px-2 py-0.5 rounded flex items-center"
              :class="{
                'bg-red-500/20 text-red-400': rule.severity === 'Fatal',
                'bg-orange-500/20 text-orange-400': rule.severity === 'Error',
                'bg-amber-500/20 text-amber-400': rule.severity === 'Warning',
                'bg-sky-500/20 text-sky-400': rule.severity !== 'Fatal' && rule.severity !== 'Error' && rule.severity !== 'Warning'
              }"
            >
              <i :class="getSeverityIcon(rule.severity)" class="mr-1 text-xs"></i>
              {{ rule.severity }}
            </span>
            <span class="domain-badge bg-slate-700 text-slate-200 text-xs px-2 py-0.5 rounded flex items-center">
              <i class="pi pi-folder mr-1 text-xs"></i>{{ rule._domain }}
            </span>
          </div>
          <button
            type="button"
            class="yaml-view-btn bg-slate-800 hover:bg-sky-400 hover:text-slate-900 border border-slate-700 text-sky-400 text-xs px-2 py-1 rounded flex items-center transition-colors"
            title="查看原始 YAML 檔"
            @click="$emit('view-yaml', rule._filename, rule._raw_yaml)"
          >
            <i class="pi pi-file-code mr-1"></i>YAML
          </button>
        </div>

        <div class="rule-card-body p-4 flex flex-col gap-3 flex-1">
          <h3 class="rule-title text-base font-semibold text-slate-100 break-all m-0">{{ rule.name }}</h3>
          <p class="rule-desc text-xs text-slate-400 leading-relaxed m-0">{{ rule.description || '無詳細說明' }}</p>

          <div class="rule-meta-section flex flex-col gap-1.5 pt-2 border-t border-dashed border-slate-700">
            <div class="meta-item flex items-center gap-2 text-xs">
              <span class="meta-label text-slate-500 min-w-[65px]">檢查機制:</span>
              <span class="meta-value check-type-pill bg-indigo-500/15 text-indigo-400 px-2 py-0.5 rounded text-xs inline-flex items-center">
                <i class="pi pi-cog mr-1"></i>
                {{ formatCheckLogicType(rule.check_logic) }}
              </span>
            </div>
            <div class="meta-item flex items-center gap-2 text-xs">
              <span class="meta-label text-slate-500 min-w-[65px]">關聯標籤:</span>
              <div class="tags-container flex flex-wrap gap-1">
                <span v-for="tag in rule.tags" :key="tag" class="rule-tag-chip bg-slate-900 border border-slate-700 text-slate-400 text-[11px] px-1.5 py-0.5 rounded">
                  {{ tag }}
                </span>
              </div>
            </div>
          </div>

          <!-- 觸發條件預覽 -->
          <div class="rule-condition-box bg-slate-900 border border-slate-800 rounded p-2.5 flex flex-col gap-1 mt-auto">
            <span class="cond-title text-xs text-amber-400 font-semibold flex items-center">
              <i class="pi pi-bolt mr-1"></i>觸發特徵:
            </span>
            <code class="cond-code font-mono text-xs text-slate-300 break-all">
              {{ formatTriggerSummary(rule.trigger_conditions) }}
            </code>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
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

    return true
  })
})

const getSeverityIcon = (sev: string) => {
  switch (sev) {
    case 'Fatal': return 'pi pi-times-circle'
    case 'Error': return 'pi pi-exclamation-triangle'
    case 'Warning': return 'pi pi-exclamation-circle'
    default: return 'pi pi-info-circle'
  }
}

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
