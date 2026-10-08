<template>
  <div class="rule-tree-card">
    <div class="tree-header">
      <div class="tree-header-intro">
        <p class="card-desc">
          系統依據圖譜特徵自動比對觸發條件並推薦標註規則（預設已勾選），您可於下方領域目錄樹狀結構中自由選取或展開其他未被推薦的規則。
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

    <!-- 預先分析特徵摘要標籤 (Pre-Analysis Summary Chips) -->
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
          placeholder="搜尋規則代碼、名稱、標籤或領域..."
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

    <!-- 規則樹狀分類清單 (Tree Structure by Domain / Category) -->
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
        <!-- 樹狀結構父節點：領域/分類標頭 -->
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
              'border-fatal': rule.severity === 'Fatal',
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

                <!-- 嚴重度標籤 -->
                <span v-if="rule.severity" class="severity-chip" :class="getSeverityClass(rule.severity)">
                  {{ rule.severity }}
                </span>

                <!-- 檢測類型標籤 -->
                <Tag
                  :value="formatCheckType(rule.check_type)"
                  :severity="getCheckTypeSeverity(rule.check_type)"
                  class="type-tag"
                />
              </div>

              <!-- 說明與推薦原因 -->
              <div class="rule-subtext">
                <span v-if="getRuleReason(rule.id)" class="reason-text">
                  <i class="pi pi-bolt mr-1 text-amber"></i>推薦原因: {{ getRuleReason(rule.id) }}
                </span>
                <span v-else-if="rule.description && rule.description !== rule.name" class="rule-desc">
                  {{ rule.description }}
                </span>
              </div>

              <!-- 關聯 Tags -->
              <div v-if="rule.tags && rule.tags.length > 0" class="rule-tags-row">
                <span v-for="t in rule.tags" :key="t" class="mini-tag">#{{ t }}</span>
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
 * @description Level 3 DRC 規則選取樹狀抽屜，支援圖譜特徵自動推薦、實體領域分群與多維度過濾
 */

import { ref, computed, watch, onMounted } from 'vue'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import type { TaskSummary, RecommendedRuleItem } from '@/types/task'
import type { DrcRuleItem } from '@/types/rule'
import { fetchPatternTree, fetchRules } from '@/services/api'
import type { PatternTreeResponse, Level3RuleItem } from '@/types/pattern'

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

export interface TreeRuleItem {
  id: string
  name: string
  category: string
  severity?: string
  check_type?: string
  tags?: string[]
  reason?: string
  description?: string
  trigger_conditions?: any
}

// 已選取的 Rule IDs
const selectedRuleIds = ref<string[]>([])

// 搜尋關鍵字與過濾模式 ('all' | 'recommended' | 'selected')
const searchQuery = ref<string>('')
const filterMode = ref<'all' | 'recommended' | 'selected'>('all')

// 摺疊/展開狀態字典
const expandedCategories = ref<Record<string, boolean>>({})

// 預設規則庫備援資料 (若無 API 回應時安全降級)
const FALLBACK_RULES: TreeRuleItem[] = [
  { id: 'I2C_Pull_Up_Existence', name: 'I2C 匯流排上拉電阻存在性檢查', category: 'interfaces', severity: 'Error', check_type: 'topology_check', tags: ['I2C', 'Signal Integrity'] },
  { id: 'I2C_Address_Conflict', name: 'I2C 匯流排設備地址衝突檢查', category: 'interfaces', severity: 'Error', check_type: 'topology_check', tags: ['I2C', 'Bus Integrity'] },
  { id: 'I2C_PartDB_Dynamic_Compliance', name: 'I2C PartDB 動態特規合規性檢查', category: 'interfaces', severity: 'Error', check_type: 'python_script', tags: ['I2C', 'PartDB'] },
  { id: 'Power_Ground_Short_Fatal', name: '電源-接地短路致命異常檢測', category: 'power', severity: 'Fatal', check_type: 'topology_check', tags: ['Power Domain', 'Short Circuit'] },
  { id: 'Power_Capacitor_Derating', name: '電源濾波電容耐壓降額檢查', category: 'power', severity: 'Error', check_type: 'topology_check', tags: ['Power Domain', 'Derating'] },
  { id: 'IC_Decoupling_Capacitor_Existence', name: '晶片電源引腳去耦電容配置檢查', category: 'power', severity: 'Warning', check_type: 'topology_check', tags: ['Power Domain', 'Decoupling'] },
  { id: 'RULE-BUS-I2C-ADDR', name: 'I2C 匯流排地址唯一性檢查', category: 'Bus Integrity', severity: 'Error', check_type: 'HEURISTIC' },
  { id: 'RULE-PWR-CAP-DERATING', name: '電源濾波電容耐壓降額檢查', category: 'Power Domain', severity: 'Error', check_type: 'HEURISTIC' },
  { id: 'RULE-PWR-DECOUPLING', name: '晶片電源引腳去耦電容配置檢查', category: 'Power Domain', severity: 'Warning', check_type: 'HEURISTIC' },
  { id: 'RULE-CONN-PINOUT', name: '連接器引腳訊號完整性與保護檢查', category: 'Pin Connection', severity: 'Warning', check_type: 'HEURISTIC' },
  { id: 'RULE-LLM-SD-MODE', name: 'MicroSD 介面工作模式合理性確認', category: 'Interface Mode', severity: 'Warning', check_type: 'LLM' },
]

const buildRulesFromProps = (): TreeRuleItem[] => {
  const merged = new Map<string, TreeRuleItem>()
  if (props.allRules && props.allRules.length > 0) {
    props.allRules.forEach((r) => {
      merged.set(r.id, {
        id: r.id,
        name: r.name,
        category: r.category,
        severity: 'Error',
        check_type: r.check_type,
      })
    })
    return Array.from(merged.values())
  }
  if (props.recommendedRules && props.recommendedRules.length > 0) {
    props.recommendedRules.forEach((r: any) => {
      if (!merged.has(r.id)) {
        merged.set(r.id, {
          id: r.id,
          name: r.name,
          category: r.category,
          severity: r.severity || 'Error',
          check_type: r.check_type || 'topology_check',
          tags: r.tags || [],
          reason: r.reason,
        })
      }
    })
  }
  FALLBACK_RULES.forEach((r) => {
    if (!merged.has(r.id)) {
      merged.set(r.id, r)
    }
  })
  return Array.from(merged.values())
}

// 系統完整規則列表 (預設即由 props 與備援同步初始化)
const internalAllRules = ref<TreeRuleItem[]>(buildRulesFromProps())

watch(
  [() => props.allRules, () => props.recommendedRules],
  () => {
    internalAllRules.value = buildRulesFromProps()
  },
  { deep: true }
)

/**
 * 載入所有規則清單 (嘗試從後端取得最新 Pattern 目錄樹)
 */
const loadAllRules = async () => {
  if (props.allRules && props.allRules.length > 0) {
    return
  }

  try {
    const data: PatternTreeResponse = await fetchPatternTree()
    if (data && data.level3 && data.level3.length > 0) {
      const l3List: TreeRuleItem[] = data.level3.map((r: Level3RuleItem) => ({
        id: r.name,
        name: r.description || r.name,
        category: r._domain || 'interfaces',
        severity: r.severity || 'Error',
        check_type: r.check_logic?.[0]?.type || 'topology_check',
        tags: r.tags || [],
        description: r.description,
        trigger_conditions: r.trigger_conditions,
      }))
      // 合併既有推薦與備援規則
      const map = new Map<string, TreeRuleItem>()
      l3List.forEach((r) => map.set(r.id, r))
      props.recommendedRules.forEach((r: any) => {
        if (!map.has(r.id)) {
          map.set(r.id, {
            id: r.id,
            name: r.name,
            category: r.category,
            severity: r.severity || 'Error',
            check_type: r.check_type || 'topology_check',
            tags: r.tags || [],
            reason: r.reason,
          })
        }
      })
      internalAllRules.value = Array.from(map.values())
      return
    }
  } catch {
    // 降級使用 props 與備援
  }
}

// 推薦規則 ID 集合
const recommendedIdSet = computed(() => {
  return new Set(props.recommendedRules.map((r) => r.id))
})

// 推薦原因查找表
const recommendedReasonMap = computed(() => {
  const map: Record<string, string> = {}
  props.recommendedRules.forEach((r: any) => {
    if (r.reason) map[r.id] = r.reason
  })
  return map
})

const getRuleReason = (ruleId: string): string => {
  return recommendedReasonMap.value[ruleId] || ''
}

const isRecommended = (ruleId: string): boolean => {
  return recommendedIdSet.value.has(ruleId)
}

// 監聽 recommendedRules，預設勾選推薦規則
watch(
  () => props.recommendedRules,
  (newRecs) => {
    if (newRecs && newRecs.length > 0) {
      const recIds = newRecs.map((r) => r.id)
      selectedRuleIds.value = Array.from(new Set([...selectedRuleIds.value, ...recIds]))
      // 自動將推薦規則所屬的分類展開
      newRecs.forEach((r) => {
        if (r.category) expandedCategories.value[r.category] = true
      })
    }
  },
  { immediate: true }
)

// 統計數值
const totalRulesCount = computed(() => internalAllRules.value.length)
const recommendedCount = computed(() => {
  return internalAllRules.value.filter((r) => isRecommended(r.id)).length
})
const selectedRecommendedCount = computed(() => {
  return selectedRuleIds.value.filter((id) => isRecommended(id)).length
})
const selectedNonRecommendedCount = computed(() => {
  return selectedRuleIds.value.filter((id) => !isRecommended(id)).length
})

// 樹狀分類節點型態
interface CategoryNode {
  category: string
  rules: TreeRuleItem[]
  recommendedCount: number
}

// 依領域/分類組織並過濾樹狀資料
const filteredCategories = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  const map = new Map<string, TreeRuleItem[]>()

  internalAllRules.value.forEach((rule) => {
    // 依模式過濾
    if (filterMode.value === 'recommended' && !isRecommended(rule.id)) return
    if (filterMode.value === 'selected' && !selectedRuleIds.value.includes(rule.id)) return

    // 關鍵字搜尋 (代碼、名稱、標籤、領域)
    if (q) {
      const matchId = rule.id.toLowerCase().includes(q)
      const matchName = rule.name.toLowerCase().includes(q)
      const matchCat = rule.category.toLowerCase().includes(q)
      const matchTag = (rule.tags || []).some((t) => t.toLowerCase().includes(q))
      if (!matchId && !matchName && !matchCat && !matchTag) return
    }

    const cat = rule.category || '通用規則'
    if (!map.has(cat)) {
      map.set(cat, [])
    }
    map.get(cat)!.push(rule)
  })

  // 組織為分類節點陣列
  const nodes: CategoryNode[] = []
  map.forEach((rules, category) => {
    const recCount = rules.filter((r) => isRecommended(r.id)).length
    nodes.push({
      category,
      rules,
      recommendedCount: recCount,
    })
  })

  return nodes
})

// 分類節點折疊控制
const isCategoryExpanded = (cat: string): boolean => {
  return expandedCategories.value[cat] ?? true
}

const toggleCategory = (cat: string) => {
  expandedCategories.value[cat] = !isCategoryExpanded(cat)
}

const isAllExpanded = computed(() => {
  if (filteredCategories.value.length === 0) return true
  return filteredCategories.value.every((c) => isCategoryExpanded(c.category))
})

const toggleExpandAll = () => {
  const target = !isAllExpanded.value
  filteredCategories.value.forEach((c) => {
    expandedCategories.value[c.category] = target
  })
}

// 分類內全選/取消全選
const isCategoryAllSelected = (catNode: CategoryNode): boolean => {
  if (catNode.rules.length === 0) return false
  return catNode.rules.every((r) => selectedRuleIds.value.includes(r.id))
}

const toggleCategorySelect = (catNode: CategoryNode) => {
  const allSel = isCategoryAllSelected(catNode)
  const catIds = catNode.rules.map((r) => r.id)
  if (allSel) {
    selectedRuleIds.value = selectedRuleIds.value.filter((id) => !catIds.includes(id))
  } else {
    selectedRuleIds.value = Array.from(new Set([...selectedRuleIds.value, ...catIds]))
  }
}

// 全選/取消推薦
const isAllRecommendedSelected = computed(() => {
  const recRules = internalAllRules.value.filter((r) => isRecommended(r.id))
  if (recRules.length === 0) return false
  return recRules.every((r) => selectedRuleIds.value.includes(r.id))
})

const toggleSelectRecommended = () => {
  const recIds = internalAllRules.value.filter((r) => isRecommended(r.id)).map((r) => r.id)
  if (isAllRecommendedSelected.value) {
    selectedRuleIds.value = selectedRuleIds.value.filter((id) => !recIds.includes(id))
  } else {
    selectedRuleIds.value = Array.from(new Set([...selectedRuleIds.value, ...recIds]))
  }
}

// 全選/清空全部規則
const isAllRulesSelected = computed(() => {
  if (internalAllRules.value.length === 0) return false
  return internalAllRules.value.every((r) => selectedRuleIds.value.includes(r.id))
})

const toggleSelectAll = () => {
  if (isAllRulesSelected.value) {
    selectedRuleIds.value = []
  } else {
    selectedRuleIds.value = internalAllRules.value.map((r) => r.id)
  }
}

// 嚴重度標籤樣式
const getSeverityClass = (sev?: string): string => {
  switch (sev) {
    case 'Fatal':
      return 'fatal'
    case 'Error':
      return 'error'
    case 'Warning':
      return 'warning'
    default:
      return 'info'
  }
}

const formatCheckType = (type?: string): string => {
  if (type === 'python_script' || type === 'LEVEL3_PARTDB') return 'PartDB 查表'
  if (type === 'llm_agent' || type === 'LLM') return '大模型推理'
  return '拓撲斷言'
}

const getCheckTypeSeverity = (type?: string): string => {
  if (type === 'llm_agent' || type === 'LLM') return 'warn'
  if (type === 'python_script' || type === 'LEVEL3_PARTDB') return 'help'
  return 'info'
}

// 點擊確認並執行
const confirmAndRun = () => {
  emit('run', selectedRuleIds.value)
}

onMounted(() => {
  loadAllRules()
})
</script>

<style scoped>
.rule-tree-card {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  background-color: var(--surface-card, #1e293b);
  border: 1px solid #334155;
  border-radius: 8px;
  padding: 1.25rem;
}

.tree-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
}

.card-desc {
  margin: 0;
  font-size: 0.85rem;
  color: #94a3b8;
  line-height: 1.45;
}

.header-actions {
  display: flex;
  gap: 0.5rem;
  flex-shrink: 0;
}

/* 摘要 Chips */
.summary-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  padding: 0.65rem 0.85rem;
  background-color: #0f172a;
  border: 1px solid #334155;
  border-radius: 6px;
  font-size: 0.8rem;
}

.chip-item {
  display: flex;
  align-items: center;
  gap: 0.35rem;
}

.chip-label {
  color: #64748b;
}

.chip-value {
  color: #38bdf8;
  font-weight: 600;
}

/* 過濾列 */
.filter-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.75rem;
}

.search-box {
  position: relative;
  flex: 1;
}

.search-icon {
  position: absolute;
  left: 0.75rem;
  top: 50%;
  transform: translateY(-50%);
  color: #64748b;
}

.search-input {
  width: 100%;
  padding: 0.45rem 2rem 0.45rem 2.25rem;
  background-color: #0f172a;
  border: 1px solid #334155;
  border-radius: 6px;
  color: #f8fafc;
  font-size: 0.85rem;
}

.clear-search-btn {
  position: absolute;
  right: 0.5rem;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  color: #64748b;
  cursor: pointer;
}

.filter-buttons {
  display: flex;
  gap: 0.35rem;
}

.filter-pill {
  padding: 0.35rem 0.65rem;
  background-color: #0f172a;
  border: 1px solid #334155;
  border-radius: 4px;
  color: #94a3b8;
  font-size: 0.75rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  transition: all 0.2s;
}

.filter-pill:hover {
  color: #f8fafc;
}

.filter-pill.active {
  background-color: #38bdf8;
  border-color: #38bdf8;
  color: #0f172a;
  font-weight: 600;
}

/* 樹狀分類列表 */
.rule-tree-container {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  max-height: 480px;
  overflow-y: auto;
  padding-right: 0.25rem;
}

.empty-rules {
  padding: 2rem;
  text-align: center;
  color: #64748b;
  font-size: 0.875rem;
}

.category-node {
  border: 1px solid #334155;
  border-radius: 6px;
  background-color: #0f172a;
  overflow: hidden;
}

.category-node-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.65rem 0.85rem;
  background-color: rgba(30, 41, 59, 0.6);
  cursor: pointer;
  user-select: none;
  transition: background-color 0.2s;
}

.category-node-header:hover {
  background-color: rgba(30, 41, 59, 0.9);
}

.node-left {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.collapse-icon {
  color: #94a3b8;
  font-size: 0.75rem;
}

.folder-icon {
  color: #38bdf8;
}

.category-title {
  font-weight: 600;
  font-size: 0.875rem;
  color: #f8fafc;
}

.category-meta-badge {
  font-size: 0.75rem;
  color: #64748b;
  margin-left: 0.25rem;
}

.meta-rec {
  color: #4ade80;
}

.cat-action-btn {
  background: none;
  border: 1px solid #334155;
  color: #94a3b8;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  font-size: 0.7rem;
  cursor: pointer;
}

.cat-action-btn:hover {
  color: #f8fafc;
  border-color: #64748b;
}

/* 子規則項目清單 */
.category-children {
  display: flex;
  flex-direction: column;
}

.tree-rule-item {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  border-top: 1px solid #1e293b;
  cursor: pointer;
  transition: background-color 0.15s;
}

.tree-rule-item:hover {
  background-color: rgba(56, 189, 248, 0.05);
}

.tree-rule-item.selected {
  background-color: rgba(56, 189, 248, 0.08);
}

.tree-rule-item.border-fatal {
  border-left: 3px solid #ef4444;
}

.rule-checkbox {
  margin-top: 0.25rem;
  cursor: pointer;
  accent-color: #38bdf8;
}

.rule-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.rule-title-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.rule-name {
  font-weight: 600;
  font-size: 0.875rem;
  color: #f8fafc;
}

.rule-id-badge {
  font-size: 0.7rem;
  color: #94a3b8;
  background-color: #1e293b;
  padding: 0.1rem 0.35rem;
  border-radius: 3px;
  font-family: monospace;
}

.severity-chip {
  font-size: 0.65rem;
  font-weight: 700;
  padding: 0.1rem 0.35rem;
  border-radius: 3px;
}

.severity-chip.fatal { background-color: rgba(239, 68, 68, 0.25); color: #f87171; }
.severity-chip.error { background-color: rgba(249, 115, 22, 0.25); color: #fb923c; }
.severity-chip.warning { background-color: rgba(234, 179, 8, 0.25); color: #facc15; }
.severity-chip.info { background-color: rgba(56, 189, 248, 0.25); color: #38bdf8; }

.type-tag {
  font-size: 0.65rem !important;
  padding: 0.1rem 0.35rem !important;
}

.rule-subtext {
  font-size: 0.75rem;
}

.reason-text {
  color: #fbbf24;
  font-weight: 500;
}

.rule-desc {
  color: #94a3b8;
}

.rule-tags-row {
  display: flex;
  gap: 0.35rem;
  flex-wrap: wrap;
}

.mini-tag {
  font-size: 0.65rem;
  color: #64748b;
  background-color: #1e293b;
  padding: 0.05rem 0.3rem;
  border-radius: 2px;
}

.rule-status-badge {
  margin-top: 0.15rem;
}

.recommended-tag {
  font-size: 0.7rem !important;
}

.unrecommended-tag {
  font-size: 0.7rem;
  color: #64748b;
}

/* 底部列 */
.tree-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 0.75rem;
  border-top: 1px solid #334155;
}

.footer-stats {
  display: flex;
  flex-direction: column;
}

.selected-count-text {
  font-size: 0.95rem;
  color: #f8fafc;
}

.stats-subtext {
  font-size: 0.75rem;
  color: #94a3b8;
}

.text-amber { color: #f59e0b; }
.text-success { color: #22c55e; }
</style>
