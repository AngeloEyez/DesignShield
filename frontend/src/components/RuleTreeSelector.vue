<template>
  <div class="rule-tree-card">
    <div class="tree-header">
      <div>
        <h3 class="card-title">
          <i class="pi pi-sitemap mr-2 text-primary"></i> 預先分析與完整規則選取庫 (DRC Rule Tree Selector)
        </h3>
        <p class="card-desc">
          系統依據圖譜特徵自動推薦標註規則（預設已勾選），您可於下方樹狀結構中自由選取或展開其他未被推薦的規則。
        </p>
      </div>

      <div class="header-actions">
        <Button
          :label="isAllRecommendedSelected ? '取消全選' : '全選所有推薦'"
          icon="pi pi-filter"
          text
          size="small"
          @click="toggleSelectRecommended"
        />
        <Button
          :label="isAllRulesSelected ? '清空全部' : '全選所有規則'"
          icon="pi pi-check-circle"
          text
          size="small"
          severity="secondary"
          @click="toggleSelectAll"
        />
        <Button
          :icon="isAllExpanded ? 'pi pi-chevron-up' : 'pi pi-chevron-down'"
          :label="isAllExpanded ? '摺疊全部' : '展開全部'"
          text
          size="small"
          severity="secondary"
          @click="toggleExpandAll"
        />
      </div>
    </div>

    <!-- 預先分析特徵摘要標籤 -->
    <div class="summary-chips">
      <div class="chip-item">
        <span class="chip-label">元件總數:</span>
        <span class="chip-value">{{ summary.component_count }}</span>
      </div>
      <div class="chip-item">
        <span class="chip-label">網路總數:</span>
        <span class="chip-value">{{ summary.net_count }}</span>
      </div>
      <div class="chip-item">
        <span class="chip-label">偵測匯流排:</span>
        <span class="chip-value">{{ summary.buses.join(', ') || '未偵測' }}</span>
      </div>
      <div class="chip-item">
        <span class="chip-label">主控平台:</span>
        <span class="chip-value">{{ summary.platforms.join(', ') || '通用' }}</span>
      </div>
    </div>

    <!-- 快速搜尋與過濾列 -->
    <div class="filter-toolbar">
      <div class="search-box">
        <i class="pi pi-search search-icon"></i>
        <input
          v-model="searchQuery"
          type="text"
          class="search-input"
          placeholder="搜尋規則代碼、名稱或關鍵字..."
        />
        <button
          v-if="searchQuery"
          type="button"
          class="clear-search-btn"
          @click="searchQuery = ''"
        >
          <i class="pi pi-times"></i>
        </button>
      </div>

      <div class="filter-buttons">
        <button
          type="button"
          class="filter-pill"
          :class="{ active: filterMode === 'all' }"
          @click="filterMode = 'all'"
        >
          全部規則 ({{ totalRulesCount }})
        </button>
        <button
          type="button"
          class="filter-pill"
          :class="{ active: filterMode === 'recommended' }"
          @click="filterMode = 'recommended'"
        >
          <i class="pi pi-star-fill text-amber mr-1"></i>
          僅推薦 ({{ recommendedCount }})
        </button>
        <button
          type="button"
          class="filter-pill"
          :class="{ active: filterMode === 'selected' }"
          @click="filterMode = 'selected'"
        >
          <i class="pi pi-check text-success mr-1"></i>
          僅已勾選 ({{ selectedRuleIds.length }})
        </button>
      </div>
    </div>

    <!-- 規則樹狀分類清單 (Tree Structure) -->
    <div class="rule-tree-container">
      <div v-if="filteredCategories.length === 0" class="empty-rules">
        <i class="pi pi-info-circle mr-2"></i>
        <span>無符合條件的規則項目</span>
      </div>

      <div
        v-for="catNode in filteredCategories"
        :key="catNode.category"
        class="category-node"
      >
        <!-- 樹狀結構父節點：分類標頭 -->
        <div class="category-node-header" @click="toggleCategory(catNode.category)">
          <div class="node-left">
            <span class="collapse-icon">
              <i :class="isCategoryExpanded(catNode.category) ? 'pi pi-chevron-down' : 'pi pi-chevron-right'"></i>
            </span>
            <span class="folder-icon">
              <i :class="isCategoryExpanded(catNode.category) ? 'pi pi-folder-open' : 'pi pi-folder'"></i>
            </span>
            <span class="category-title">{{ catNode.category }}</span>
            <span class="category-meta-badge">
              共 {{ catNode.rules.length }} 條
              <span v-if="catNode.recommendedCount > 0" class="meta-rec">
                · {{ catNode.recommendedCount }} 條推薦
              </span>
            </span>
          </div>

          <div class="node-right" @click.stop>
            <button
              type="button"
              class="cat-action-btn"
              @click="toggleCategorySelect(catNode)"
            >
              {{ isCategoryAllSelected(catNode) ? '取消此類' : '全選此類' }}
            </button>
          </div>
        </div>

        <!-- 樹狀結構子節點清單 -->
        <div v-show="isCategoryExpanded(catNode.category)" class="category-children">
          <label
            v-for="rule in catNode.rules"
            :key="rule.id"
            class="tree-rule-item"
            :class="{
              selected: selectedRuleIds.includes(rule.id),
              recommended: isRecommended(rule.id),
            }"
          >
            <input
              type="checkbox"
              :value="rule.id"
              v-model="selectedRuleIds"
              class="rule-checkbox"
            />

            <div class="rule-main">
              <div class="rule-title-row">
                <span class="rule-name">{{ rule.name }}</span>
                <span class="rule-id-badge">{{ rule.id }}</span>
                <Tag
                  :value="rule.check_type || 'HEURISTIC'"
                  :severity="rule.check_type === 'LLM' ? 'warn' : 'info'"
                  class="type-tag"
                />
              </div>
              <div v-if="rule.context_extractor" class="rule-subtext">
                <span class="extractor-label">
                  <i class="pi pi-link mr-1"></i>抽取器: {{ rule.context_extractor }}
                </span>
              </div>
            </div>

            <!-- 標註是否為推薦規則 -->
            <div class="rule-status-badge">
              <Tag
                v-if="isRecommended(rule.id)"
                value="推薦"
                severity="success"
                class="recommended-tag"
              />
              <span v-else class="unrecommended-tag">
                <i class="pi pi-plus-circle mr-1"></i>未推薦 (可自選)
              </span>
            </div>
          </label>
        </div>
      </div>
    </div>

    <!-- 底部確認與統計列 -->
    <div class="tree-footer">
      <div class="footer-stats">
        <span class="selected-count-text">
          已選取 <strong>{{ selectedRuleIds.length }}</strong> 條規則
        </span>
        <span class="stats-subtext">
          (包含 <strong>{{ selectedRecommendedCount }}</strong> 條推薦規則，
          <strong>{{ selectedNonRecommendedCount }}</strong> 條額外選取規則)
        </span>
      </div>

      <div class="footer-actions">
        <Button
          label="確認並啟動正式 DRC"
          icon="pi pi-play"
          severity="success"
          :loading="isSubmitting"
          :disabled="selectedRuleIds.length === 0"
          @click="confirmAndRun"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * @file RuleTreeSelector.vue
 * @description 預先分析摘要展示與完整 DRC 規則庫樹狀勾選元件，支援選取未被推薦的規則
 */

import { ref, computed, watch, onMounted } from 'vue'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import type { TaskSummary, RecommendedRuleItem } from '@/types/task'
import type { DrcRuleItem } from '@/types/rule'
import { fetchRules } from '@/services/api'

interface Props {
  summary: TaskSummary
  recommendedRules: RecommendedRuleItem[]
  allRules?: DrcRuleItem[]
  isSubmitting?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  summary: () => ({ buses: [], platforms: [], component_count: 0, net_count: 0 }),
  recommendedRules: () => [],
  allRules: () => [],
  isSubmitting: false,
})

const emit = defineEmits<{
  (e: 'run', selectedIds: string[]): void
}>()

// 已選取的 Rule IDs
const selectedRuleIds = ref<string[]>([])

// 系統完整規則列表
const internalAllRules = ref<DrcRuleItem[]>([])

// 搜尋關鍵字與過濾模式 ('all' | 'recommended' | 'selected')
const searchQuery = ref<string>('')
const filterMode = ref<'all' | 'recommended' | 'selected'>('all')

// 摺疊/展開狀態字典
const expandedCategories = ref<Record<string, boolean>>({})

// 預設規則庫備援資料 (若無 API 回應時安全降級)
const FALLBACK_RULES: DrcRuleItem[] = [
  { id: 'RULE-BUS-I2C-ADDR', name: 'I2C 匯流排地址唯一性檢查', category: 'Bus Integrity', check_type: 'HEURISTIC', is_active: true, parameters: {} },
  { id: 'RULE-PWR-CAP-DERATING', name: '電源濾波電容耐壓降額檢查', category: 'Power Domain', check_type: 'HEURISTIC', is_active: true, parameters: {} },
  { id: 'RULE-PWR-DECOUPLING', name: '晶片電源引腳去耦電容配置檢查', category: 'Power Domain', check_type: 'HEURISTIC', is_active: true, parameters: {} },
  { id: 'RULE-CONN-PINOUT', name: '連接器引腳訊號完整性與保護檢查', category: 'Pin Connection', check_type: 'HEURISTIC', is_active: true, parameters: {} },
  { id: 'RULE-LLM-SD-MODE', name: 'MicroSD 介面工作模式合理性確認', category: 'Interface Mode', check_type: 'LLM', is_active: true, parameters: {} },
  { id: 'RULE-LLM-POWER-SEQUENCE', name: '晶片上下電時序與復位電路邏輯確認', category: 'Power Domain', check_type: 'LLM', is_active: true, parameters: {} },
  { id: 'RULE-LLM-LEVEL-SHIFT', name: '跨電壓域電平轉換邏輯合理性確認', category: 'Signal Integrity', check_type: 'LLM', is_active: true, parameters: {} },
]

/**
 * 載入所有規則清單
 */
const loadAllRules = async () => {
  if (props.allRules && props.allRules.length > 0) {
    internalAllRules.value = [...props.allRules]
    return
  }

  try {
    const list = await fetchRules()
    if (list && list.length > 0) {
      internalAllRules.value = list
      return
    }
  } catch (err) {
    // 降級處理
  }

  // 若 API 未載入，結合推薦規則與預設備援規則
  const ruleMap = new Map<string, DrcRuleItem>()
  props.recommendedRules.forEach((r) => {
    ruleMap.set(r.id, {
      id: r.id,
      name: r.name,
      category: r.category,
      check_type: r.id.includes('LLM') ? 'LLM' : 'HEURISTIC',
      is_active: true,
      parameters: {},
    })
  })
  FALLBACK_RULES.forEach((r) => {
    if (!ruleMap.has(r.id)) {
      ruleMap.set(r.id, r)
    }
  })
  internalAllRules.value = Array.from(ruleMap.values())
}

onMounted(() => {
  loadAllRules()
})

watch(
  () => props.allRules,
  (newVal) => {
    if (newVal && newVal.length > 0) {
      internalAllRules.value = [...newVal]
    }
  },
  { immediate: true }
)

// 推薦規則 ID 集合 (用於快速判定)
const recommendedIdSet = computed(() => {
  return new Set(props.recommendedRules.map((r) => r.id))
})

/**
 * 判斷指定規則是否屬於推薦規則
 */
const isRecommended = (ruleId: string): boolean => {
  return recommendedIdSet.value.has(ruleId)
}

// 初始化預設勾選所有推薦規則
watch(
  () => props.recommendedRules,
  (newRules) => {
    const recIds = newRules.map((r) => r.id)
    // 預設選中推薦規則
    selectedRuleIds.value = Array.from(new Set([...selectedRuleIds.value, ...recIds]))
    if (selectedRuleIds.value.length === 0) {
      selectedRuleIds.value = recIds
    }
  },
  { immediate: true }
)

/**
 * 有效的全部規則集合
 */
const effectiveAllRules = computed<DrcRuleItem[]>(() => {
  const map = new Map<string, DrcRuleItem>()
  // 先加入 internalAllRules
  internalAllRules.value.forEach((r) => map.set(r.id, r))
  // 確保 props.recommendedRules 內的規則一定包含在內
  props.recommendedRules.forEach((r) => {
    if (!map.has(r.id)) {
      map.set(r.id, {
        id: r.id,
        name: r.name,
        category: r.category,
        check_type: r.id.includes('LLM') ? 'LLM' : 'HEURISTIC',
        is_active: true,
        parameters: {},
      })
    }
  })
  return Array.from(map.values())
})

const totalRulesCount = computed(() => effectiveAllRules.value.length)
const recommendedCount = computed(() => {
  return effectiveAllRules.value.filter((r) => isRecommended(r.id)).length
})

/**
 * 已選取之推薦規則數
 */
const selectedRecommendedCount = computed(() => {
  return selectedRuleIds.value.filter((id) => isRecommended(id)).length
})

/**
 * 已選取之非推薦規則數
 */
const selectedNonRecommendedCount = computed(() => {
  return selectedRuleIds.value.filter((id) => !isRecommended(id)).length
})

/**
 * 樹狀結構分類節點資料
 */
interface CategoryNode {
  category: string
  rules: DrcRuleItem[]
  recommendedCount: number
}

const categorizedRules = computed<CategoryNode[]>(() => {
  const groups: Record<string, DrcRuleItem[]> = {}
  effectiveAllRules.value.forEach((rule) => {
    const cat = rule.category || '未分類'
    if (!groups[cat]) {
      groups[cat] = []
    }
    groups[cat].push(rule)
  })

  return Object.keys(groups)
    .sort()
    .map((category) => {
      const rules = groups[category]
      const recCount = rules.filter((r) => isRecommended(r.id)).length
      return {
        category,
        rules,
        recommendedCount: recCount,
      }
    })
})

/**
 * 根據搜尋字串與過濾模式過濾分類樹狀節點
 */
const filteredCategories = computed<CategoryNode[]>(() => {
  const query = searchQuery.value.trim().toLowerCase()
  const mode = filterMode.value

  const result: CategoryNode[] = []

  categorizedRules.value.forEach((catNode) => {
    const matchedRules = catNode.rules.filter((rule) => {
      // 模式過濾
      if (mode === 'recommended' && !isRecommended(rule.id)) {
        return false
      }
      if (mode === 'selected' && !selectedRuleIds.value.includes(rule.id)) {
        return false
      }

      // 關鍵字搜尋
      if (query) {
        const inId = rule.id.toLowerCase().includes(query)
        const inName = rule.name.toLowerCase().includes(query)
        const inCat = rule.category.toLowerCase().includes(query)
        return inId || inName || inCat
      }

      return true
    })

    if (matchedRules.length > 0) {
      result.push({
        category: catNode.category,
        rules: matchedRules,
        recommendedCount: matchedRules.filter((r) => isRecommended(r.id)).length,
      })
    }
  })

  return result
})

/**
 * 檢查分類是否展開
 */
const isCategoryExpanded = (category: string): boolean => {
  if (expandedCategories.value[category] === undefined) {
    return true // 預設全部展開
  }
  return expandedCategories.value[category]
}

/**
 * 切換單一分類展開/摺疊
 */
const toggleCategory = (category: string) => {
  expandedCategories.value[category] = !isCategoryExpanded(category)
}

/**
 * 切換所有分類展開/摺疊
 */
const isAllExpanded = computed(() => {
  return categorizedRules.value.every((c) => isCategoryExpanded(c.category))
})

const toggleExpandAll = () => {
  const target = !isAllExpanded.value
  categorizedRules.value.forEach((c) => {
    expandedCategories.value[c.category] = target
  })
}

/**
 * 檢查分類下是否所有規則已被選取
 */
const isCategoryAllSelected = (catNode: CategoryNode): boolean => {
  return catNode.rules.length > 0 && catNode.rules.every((r) => selectedRuleIds.value.includes(r.id))
}

/**
 * 切換單一分類全選/取消全選
 */
const toggleCategorySelect = (catNode: CategoryNode) => {
  const catRuleIds = catNode.rules.map((r) => r.id)
  if (isCategoryAllSelected(catNode)) {
    selectedRuleIds.value = selectedRuleIds.value.filter((id) => !catRuleIds.includes(id))
  } else {
    selectedRuleIds.value = Array.from(new Set([...selectedRuleIds.value, ...catRuleIds]))
  }
}

/**
 * 是否所有推薦規則已選取
 */
const isAllRecommendedSelected = computed(() => {
  const recIds = props.recommendedRules.map((r) => r.id)
  return recIds.length > 0 && recIds.every((id) => selectedRuleIds.value.includes(id))
})

/**
 * 切換推薦規則全選狀態
 */
const toggleSelectRecommended = () => {
  const recIds = props.recommendedRules.map((r) => r.id)
  if (isAllRecommendedSelected.value) {
    selectedRuleIds.value = selectedRuleIds.value.filter((id) => !recIds.includes(id))
  } else {
    selectedRuleIds.value = Array.from(new Set([...selectedRuleIds.value, ...recIds]))
  }
}

/**
 * 是否所有規則已全選
 */
const isAllRulesSelected = computed(() => {
  return (
    totalRulesCount.value > 0 &&
    selectedRuleIds.value.length === totalRulesCount.value
  )
})

/**
 * 切換全選所有規則狀態
 */
const toggleSelectAll = () => {
  if (isAllRulesSelected.value) {
    selectedRuleIds.value = []
  } else {
    selectedRuleIds.value = effectiveAllRules.value.map((r) => r.id)
  }
}

/**
 * 確認選取並啟動
 */
const confirmAndRun = () => {
  emit('run', selectedRuleIds.value)
}
</script>

<style scoped>
.rule-tree-card {
  background: #ffffff;
  border-radius: 8px;
  padding: 1.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  border: 1px solid #e2e8f0;
}

.tree-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1.25rem;
  gap: 1rem;
}

.card-title {
  margin: 0;
  font-size: 1.25rem;
  color: #0f172a;
  display: flex;
  align-items: center;
  font-weight: 700;
}

.card-desc {
  margin: 0.35rem 0 0 0;
  font-size: 0.85rem;
  color: #64748b;
  line-height: 1.5;
}

.header-actions {
  display: flex;
  gap: 0.5rem;
  flex-shrink: 0;
}

.summary-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  background: #f8fafc;
  padding: 0.85rem 1rem;
  border-radius: 6px;
  margin-bottom: 1.25rem;
  border: 1px solid #e2e8f0;
}

.chip-item {
  display: inline-flex;
  gap: 0.4rem;
  font-size: 0.85rem;
}

.chip-label {
  color: #64748b;
}

.chip-value {
  font-weight: 600;
  color: #1e293b;
}

.filter-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1.25rem;
  flex-wrap: wrap;
}

.search-box {
  position: relative;
  display: flex;
  align-items: center;
  flex: 1;
  min-width: 260px;
}

.search-icon {
  position: absolute;
  left: 0.75rem;
  color: #94a3b8;
  font-size: 0.85rem;
}

.search-input {
  width: 100%;
  padding: 0.45rem 2rem 0.45rem 2.25rem;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  font-size: 0.85rem;
  outline: none;
  transition: border-color 0.15s, box-shadow 0.15s;
}

.search-input:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15);
}

.clear-search-btn {
  position: absolute;
  right: 0.5rem;
  background: transparent;
  border: none;
  color: #94a3b8;
  cursor: pointer;
  padding: 0.2rem;
  font-size: 0.8rem;
}

.clear-search-btn:hover {
  color: #475569;
}

.filter-buttons {
  display: flex;
  gap: 0.5rem;
}

.filter-pill {
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  color: #475569;
  padding: 0.35rem 0.75rem;
  border-radius: 9999px;
  font-size: 0.8rem;
  cursor: pointer;
  font-weight: 500;
  display: inline-flex;
  align-items: center;
  transition: all 0.15s;
}

.filter-pill:hover {
  background: #e2e8f0;
  color: #1e293b;
}

.filter-pill.active {
  background: #eff6ff;
  border-color: #3b82f6;
  color: #2563eb;
  font-weight: 600;
}

.rule-tree-container {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
  margin-bottom: 1.5rem;
  max-height: 520px;
  overflow-y: auto;
  padding-right: 0.25rem;
}

.empty-rules {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2.5rem;
  color: #94a3b8;
  font-size: 0.9rem;
  background: #f8fafc;
  border-radius: 6px;
}

.category-node {
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  overflow: hidden;
  background: #ffffff;
}

.category-node-header {
  background: #f8fafc;
  padding: 0.65rem 0.85rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  user-select: none;
  border-bottom: 1px solid #f1f5f9;
  transition: background-color 0.15s;
}

.category-node-header:hover {
  background: #f1f5f9;
}

.node-left {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.collapse-icon {
  color: #64748b;
  font-size: 0.75rem;
  width: 14px;
  display: flex;
  justify-content: center;
}

.folder-icon {
  color: #3b82f6;
  font-size: 0.95rem;
}

.category-title {
  font-weight: 600;
  font-size: 0.9rem;
  color: #1e293b;
}

.category-meta-badge {
  font-size: 0.75rem;
  color: #64748b;
  background: #e2e8f0;
  padding: 0.1rem 0.45rem;
  border-radius: 9999px;
  margin-left: 0.25rem;
}

.meta-rec {
  color: #16a34a;
  font-weight: 600;
}

.cat-action-btn {
  background: transparent;
  border: 1px solid #cbd5e1;
  color: #475569;
  font-size: 0.75rem;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.15s;
}

.cat-action-btn:hover {
  background: #e2e8f0;
  color: #1e293b;
}

.category-children {
  display: flex;
  flex-direction: column;
}

.tree-rule-item {
  display: flex;
  align-items: center;
  padding: 0.65rem 1rem 0.65rem 2.25rem;
  border-bottom: 1px solid #f1f5f9;
  cursor: pointer;
  transition: background-color 0.12s;
  position: relative;
}

.tree-rule-item:last-child {
  border-bottom: none;
}

.tree-rule-item:hover {
  background-color: #f8fafc;
}

.tree-rule-item.selected {
  background-color: #f0fdf4;
}

.tree-rule-item.recommended.selected {
  background-color: #f0fdf4;
}

.rule-checkbox {
  margin-right: 0.85rem;
  cursor: pointer;
  width: 16px;
  height: 16px;
  accent-color: #16a34a;
}

.rule-main {
  flex: 1;
}

.rule-title-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.rule-name {
  font-size: 0.9rem;
  font-weight: 500;
  color: #1e293b;
}

.rule-id-badge {
  font-size: 0.75rem;
  background: #f1f5f9;
  color: #475569;
  border: 1px solid #e2e8f0;
  padding: 0.05rem 0.4rem;
  border-radius: 4px;
  font-family: monospace;
}

.type-tag {
  font-size: 0.7rem;
  padding: 0.1rem 0.4rem;
}

.rule-subtext {
  margin-top: 0.2rem;
  font-size: 0.75rem;
  color: #64748b;
}

.extractor-label {
  display: inline-flex;
  align-items: center;
}

.rule-status-badge {
  flex-shrink: 0;
  margin-left: 0.75rem;
}

.recommended-tag {
  font-size: 0.72rem;
}

.unrecommended-tag {
  font-size: 0.72rem;
  color: #64748b;
  background: #f1f5f9;
  border: 1px dashed #cbd5e1;
  padding: 0.15rem 0.45rem;
  border-radius: 4px;
  display: inline-flex;
  align-items: center;
}

.tree-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-top: 1px solid #e2e8f0;
  padding-top: 1.25rem;
  flex-wrap: wrap;
  gap: 1rem;
}

.footer-stats {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.selected-count-text {
  font-size: 0.95rem;
  color: #1e293b;
}

.stats-subtext {
  font-size: 0.8rem;
  color: #64748b;
}

.footer-actions {
  display: flex;
  gap: 0.75rem;
}

.text-primary {
  color: #3b82f6;
}

.text-amber {
  color: #f59e0b;
}

.text-success {
  color: #16a34a;
}

.mr-1 {
  margin-right: 0.25rem;
}

.mr-2 {
  margin-right: 0.5rem;
}
</style>
