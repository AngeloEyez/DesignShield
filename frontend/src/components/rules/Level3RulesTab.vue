<template>
  <div class="tab-content">
    <!-- 搜尋與篩選工具列 -->
    <div class="filter-card">
      <div class="filter-controls">
        <div class="search-input-wrapper">
          <i class="pi pi-search search-icon"></i>
          <input
            v-model="searchQuery"
            type="text"
            placeholder="搜尋 Level 3 規則名稱、說明、標籤或網域..."
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
          <select v-model="selectedDomain" class="filter-select">
            <option value="">全部網域 (All Domains)</option>
            <option v-for="d in level3Domains" :key="d" :value="d">
              {{ d }}
            </option>
          </select>

          <select v-model="selectedSeverity" class="filter-select">
            <option value="">全部嚴重等級 (All Severities)</option>
            <option value="Fatal">Fatal (致命異常)</option>
            <option value="Error">Error (嚴重違規)</option>
            <option value="Warning">Warning (潛在警告)</option>
            <option value="Info">Info (提示資訊)</option>
          </select>

          <select v-model="selectedTag" class="filter-select">
            <option value="">全部標籤 (All Tags)</option>
            <option v-for="t in allTags" :key="t" :value="t">
              {{ t }}
            </option>
          </select>
        </div>
      </div>

      <div class="filter-summary">
        <span>顯示 <strong>{{ filteredRules.length }}</strong> / {{ rules.length }} 條 DRC 規則</span>
      </div>
    </div>

    <!-- Level 3 規則卡片列表 -->
    <div class="rules-grid">
      <div v-if="filteredRules.length === 0" class="empty-placeholder">
        <i class="pi pi-inbox text-4xl mb-3 text-muted"></i>
        <p>無符合條件之 Level 3 DRC 規則項目</p>
      </div>

      <div
        v-for="rule in filteredRules"
        :key="rule.name"
        class="rule-card"
        :class="`border-${getSeverityClass(rule.severity)}`"
      >
        <div class="rule-card-header">
          <div class="header-badges">
            <span class="severity-badge" :class="getSeverityClass(rule.severity)">
              <i :class="getSeverityIcon(rule.severity)" class="mr-1"></i>
              {{ rule.severity }}
            </span>
            <span class="domain-badge">
              <i class="pi pi-folder mr-1"></i>{{ rule._domain }}
            </span>
          </div>
          <button
            type="button"
            class="yaml-view-btn"
            title="查看原始 YAML 檔"
            @click="$emit('view-yaml', rule._filename, rule._raw_yaml)"
          >
            <i class="pi pi-file-code mr-1"></i>YAML
          </button>
        </div>

        <div class="rule-card-body">
          <h3 class="rule-title">{{ rule.name }}</h3>
          <p class="rule-desc">{{ rule.description || '無詳細說明' }}</p>

          <div class="rule-meta-section">
            <div class="meta-item">
              <span class="meta-label">檢查機制:</span>
              <span class="meta-value check-type-pill">
                <i class="pi pi-cog mr-1"></i>
                {{ formatCheckLogicType(rule.check_logic) }}
              </span>
            </div>
            <div class="meta-item">
              <span class="meta-label">關聯標籤:</span>
              <div class="tags-container">
                <span v-for="tag in rule.tags" :key="tag" class="rule-tag-chip">
                  {{ tag }}
                </span>
              </div>
            </div>
          </div>

          <!-- 觸發條件預覽 -->
          <div class="rule-condition-box">
            <span class="cond-title">
              <i class="pi pi-bolt text-amber mr-1"></i>觸發特徵:
            </span>
            <code class="cond-code">
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

const getSeverityClass = (sev: string) => {
  switch (sev) {
    case 'Fatal': return 'fatal'
    case 'Error': return 'error'
    case 'Warning': return 'warning'
    default: return 'info'
  }
}

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

<style scoped>
.tab-content {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.filter-card {
  background-color: var(--surface-card, #1e293b);
  border: 1px solid #334155;
  border-radius: 8px;
  padding: 1rem 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.filter-controls {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
}

.search-input-wrapper {
  position: relative;
  flex: 1;
  min-width: 260px;
}

.search-icon {
  position: absolute;
  left: 0.75rem;
  top: 50%;
  transform: translateY(-50%);
  color: #94a3b8;
  font-size: 0.875rem;
}

.filter-search-input {
  width: 100%;
  padding: 0.5rem 2rem 0.5rem 2.25rem;
  background-color: #0f172a;
  border: 1px solid #334155;
  border-radius: 6px;
  color: #f8fafc;
  font-size: 0.875rem;
}

.filter-search-input:focus {
  outline: none;
  border-color: var(--primary-color, #38bdf8);
}

.clear-btn {
  position: absolute;
  right: 0.5rem;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  color: #94a3b8;
  cursor: pointer;
  padding: 0.2rem;
}

.filter-select-group {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.filter-select {
  padding: 0.5rem 0.75rem;
  background-color: #0f172a;
  border: 1px solid #334155;
  border-radius: 6px;
  color: #f8fafc;
  font-size: 0.875rem;
}

.filter-select:focus {
  outline: none;
  border-color: var(--primary-color, #38bdf8);
}

.filter-summary {
  font-size: 0.8rem;
  color: #94a3b8;
}

.rules-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
  gap: 1rem;
}

.empty-placeholder {
  grid-column: 1 / -1;
  padding: 3rem;
  text-align: center;
  color: #94a3b8;
  background-color: var(--surface-card, #1e293b);
  border: 1px dashed #334155;
  border-radius: 8px;
}

.rule-card {
  background-color: var(--surface-card, #1e293b);
  border: 1px solid #334155;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: all 0.2s ease;
}

.rule-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

.border-fatal { border-top: 3px solid #ef4444; }
.border-error { border-top: 3px solid #f97316; }
.border-warning { border-top: 3px solid #eab308; }
.border-info { border-top: 3px solid #38bdf8; }

.rule-card-header {
  padding: 0.75rem 1rem;
  background-color: rgba(15, 23, 42, 0.5);
  border-bottom: 1px solid #334155;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-badges {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.severity-badge {
  font-size: 0.75rem;
  font-weight: 600;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  display: flex;
  align-items: center;
}

.severity-badge.fatal {
  background-color: rgba(239, 68, 68, 0.2);
  color: #f87171;
}

.severity-badge.error {
  background-color: rgba(249, 115, 22, 0.2);
  color: #fb923c;
}

.severity-badge.warning {
  background-color: rgba(234, 179, 8, 0.2);
  color: #facc15;
}

.severity-badge.info {
  background-color: rgba(56, 189, 248, 0.2);
  color: #38bdf8;
}

.domain-badge {
  background-color: #334155;
  color: #cbd5e1;
  font-size: 0.75rem;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  display: flex;
  align-items: center;
}

.yaml-view-btn {
  background-color: #1e293b;
  border: 1px solid #334155;
  color: #38bdf8;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  transition: all 0.2s ease;
}

.yaml-view-btn:hover {
  background-color: #38bdf8;
  color: #0f172a;
}

.rule-card-body {
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  flex: 1;
}

.rule-title {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  color: #f8fafc;
  word-break: break-all;
}

.rule-desc {
  margin: 0;
  font-size: 0.825rem;
  color: #94a3b8;
  line-height: 1.4;
}

.rule-meta-section {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  padding-top: 0.5rem;
  border-top: 1px dashed #334155;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.8rem;
}

.meta-label {
  color: #64748b;
  min-width: 65px;
}

.meta-value {
  color: #e2e8f0;
}

.check-type-pill {
  background-color: rgba(99, 102, 241, 0.15);
  color: #818cf8;
  padding: 0.15rem 0.45rem;
  border-radius: 4px;
  font-size: 0.75rem;
  display: inline-flex;
  align-items: center;
}

.tags-container {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
}

.rule-tag-chip {
  background-color: #0f172a;
  border: 1px solid #334155;
  color: #94a3b8;
  font-size: 0.7rem;
  padding: 0.1rem 0.4rem;
  border-radius: 4px;
}

.rule-condition-box {
  background-color: #0f172a;
  border: 1px solid #1e293b;
  border-radius: 6px;
  padding: 0.5rem 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  margin-top: auto;
}

.cond-title {
  font-size: 0.75rem;
  color: #f59e0b;
  font-weight: 600;
  display: flex;
  align-items: center;
}

.cond-code {
  font-family: 'Fira Code', monospace;
  font-size: 0.75rem;
  color: #cbd5e1;
  word-break: break-all;
}
</style>
