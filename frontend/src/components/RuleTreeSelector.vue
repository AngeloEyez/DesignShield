<template>
  <div class="rule-tree-card">
    <!-- 頂部說明與批次選取列 -->
    <div class="tree-header">
      <div class="tree-header-intro">
        <span class="card-desc">
          <i class="pi pi-sparkles text-cyan mr-1"></i>系統依據圖譜特徵自動比對觸發條件並推薦標註規則（預設已勾選），您可於下方領域目錄樹狀結構中自由選取或展開其他未被推薦的規則。
        </span>
      </div>

      <div class="header-actions">
        <Button
          :label="isAllRecommendedSelected ? '取消全選' : '全選所有推薦'"
          icon="pi pi-filter"
          text
          size="small"
          severity="info"
          class="compact-action-btn"
          @click="toggleSelectRecommended"
        />
        <Button
          :label="isAllRulesSelected ? '清空全部' : '全選所有規則'"
          icon="pi pi-check-circle"
          text
          size="small"
          severity="secondary"
          class="compact-action-btn"
          @click="toggleSelectAll"
        />
        <Button
          :icon="isAllExpanded ? 'pi pi-chevron-up' : 'pi pi-chevron-down'"
          :label="isAllExpanded ? '摺疊全部' : '展開全部'"
          text
          size="small"
          severity="secondary"
          class="compact-action-btn"
          @click="toggleExpandAll"
        />
      </div>
    </div>

    <!-- 預先分析特徵摘要列 (VS Code Status Bar 風格) -->
    <div class="summary-chips">
      <div class="chip-item">
        <i class="pi pi-box chip-icon"></i>
        <span class="chip-label">元件總數:</span>
        <span class="chip-value">{{ summary.component_count }}</span>
      </div>
      <div class="chip-divider"></div>
      <div class="chip-item">
        <i class="pi pi-share-alt chip-icon"></i>
        <span class="chip-label">網路總數:</span>
        <span class="chip-value">{{ summary.net_count }}</span>
      </div>
      <div class="chip-divider"></div>
      <div class="chip-item">
        <i class="pi pi-compass chip-icon"></i>
        <span class="chip-label">偵測匯流排:</span>
        <span class="chip-value">{{ summary.buses.join(', ') || '未偵測' }}</span>
      </div>
      <div class="chip-divider"></div>
      <div class="chip-item">
        <i class="pi pi-server chip-icon"></i>
        <span class="chip-label">主控平台:</span>
        <span class="chip-value">{{ summary.platforms.join(', ') || '通用' }}</span>
      </div>
    </div>

    <!-- 快速搜尋與多維度過濾列 -->
    <div class="filter-toolbar">
      <div class="search-box">
        <IconField class="w-full">
          <InputIcon class="pi pi-search search-icon" />
          <InputText
            v-model="searchQuery"
            type="text"
            size="small"
            class="search-input"
            placeholder="搜尋規則代碼、名稱、標籤或領域..."
          />
          <InputIcon
            v-if="searchQuery"
            class="pi pi-times clear-search-icon"
            @click="searchQuery = ''"
          />
        </IconField>
      </div>

      <div class="filter-buttons">
        <Button
          :label="`全部規則 (${totalRulesCount})`"
          size="small"
          :severity="filterMode === 'all' ? 'primary' : 'secondary'"
          :variant="filterMode === 'all' ? undefined : 'outlined'"
          class="filter-pill-btn"
          @click="filterMode = 'all'"
        />
        <Button
          :label="`僅推薦 (${recommendedCount})`"
          icon="pi pi-star-fill text-amber"
          size="small"
          :severity="filterMode === 'recommended' ? 'primary' : 'secondary'"
          :variant="filterMode === 'recommended' ? undefined : 'outlined'"
          class="filter-pill-btn"
          @click="filterMode = 'recommended'"
        />
        <Button
          :label="`僅已勾選 (${selectedRuleIds.length})`"
          icon="pi pi-check text-success"
          size="small"
          :severity="filterMode === 'selected' ? 'primary' : 'secondary'"
          :variant="filterMode === 'selected' ? undefined : 'outlined'"
          class="filter-pill-btn"
          @click="filterMode = 'selected'"
        />
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
            <Button
              :label="isCategoryAllSelected(catNode) ? '取消此類' : '全選此類'"
              size="small"
              text
              severity="secondary"
              class="cat-action-btn"
              @click="toggleCategorySelect(catNode)"
            />
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
            <Checkbox
              v-model="selectedRuleIds"
              :value="rule.id"
              size="small"
              class="rule-checkbox"
            />

            <div class="rule-main">
              <div class="rule-title-row">
                <span class="rule-name">{{ rule.name }}</span>
                <span class="rule-id-badge">{{ rule.id }}</span>

                <!-- 嚴重度標籤 -->
                <Tag
                  v-if="rule.severity"
                  :value="rule.severity"
                  :severity="getSeverityTagSeverity(rule.severity)"
                  class="severity-tag"
                />

                <!-- 檢測類型標籤 -->
                <Tag
                  :value="formatCheckType(rule.check_type)"
                  :severity="getCheckTypeSeverity(rule.check_type)"
                  class="type-tag"
                />
              </div>

              <!-- 說明與推薦原因 (緊湊單行呈現) -->
              <div v-if="getRuleReason(rule.id) || (rule.description && rule.description !== rule.name)" class="rule-subtext">
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

    <!-- 底部確認與統計列 (VS Code 狀態底欄風格) -->
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
          size="small"
          class="confirm-run-btn"
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
 * 採用 VS Code 現代化緊湊布局與 PrimeVue v4 組件，最大化垂直可視範圍
 */

import { ref, computed, watch, onMounted } from 'vue'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import Checkbox from 'primevue/checkbox'
import InputText from 'primevue/inputtext'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import type { TaskSummary, RecommendedRuleItem } from '@/types/task'
import type { DrcRuleItem } from '@/types/rule'
import { fetchPatternTree } from '@/services/api'
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
const getSeverityTagSeverity = (sev?: string): 'danger' | 'warn' | 'info' | 'secondary' => {
  switch (sev) {
    case 'Fatal':
    case 'Error':
      return 'danger'
    case 'Warning':
      return 'warn'
    default:
      return 'info'
  }
}

const formatCheckType = (type?: string): string => {
  if (type === 'python_script' || type === 'LEVEL3_PARTDB') return 'PartDB 查表'
  if (type === 'llm_agent' || type === 'LLM') return '大模型推理'
  return '拓撲斷言'
}

const getCheckTypeSeverity = (type?: string): 'warn' | 'help' | 'info' => {
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
  height: 100%;
  gap: 0.65rem;
  background-color: var(--vscode-bg-panel, #252526);
  border: 1px solid var(--vscode-border, #333333);
  border-radius: 6px;
  padding: 0.75rem 0.85rem;
  box-sizing: border-box;
}

/* 頂部說明與全選控制列 */
.tree-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.75rem;
  flex-shrink: 0;
  padding-bottom: 0.25rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.tree-header-intro {
  flex: 1;
  min-width: 0;
}

.card-desc {
  margin: 0;
  font-size: 0.78rem;
  color: var(--vscode-text-muted, #858585);
  line-height: 1.35;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.header-actions {
  display: flex;
  gap: 0.35rem;
  flex-shrink: 0;
}

:deep(.compact-action-btn) {
  font-size: 0.72rem !important;
  padding: 0.2rem 0.45rem !important;
}

/* 預先分析特徵摘要列 (VS Code Status Bar 風格) */
.summary-chips {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.6rem;
  padding: 0.35rem 0.65rem;
  background-color: var(--vscode-bg-base, #1e1e1e);
  border: 1px solid var(--vscode-border, #333333);
  border-radius: 4px;
  font-size: 0.75rem;
  flex-shrink: 0;
}

.chip-item {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
}

.chip-icon {
  font-size: 0.75rem;
  color: #38bdf8;
}

.chip-label {
  color: var(--vscode-text-muted, #858585);
  font-size: 0.73rem;
}

.chip-value {
  color: #38bdf8;
  font-weight: 600;
  font-family: var(--vscode-editor-font-family, monospace);
  font-size: 0.75rem;
}

.chip-divider {
  width: 1px;
  height: 12px;
  background-color: var(--vscode-border, #333333);
}

/* 快速搜尋與過濾工具列 */
.filter-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.6rem;
  flex-shrink: 0;
}

.search-box {
  flex: 1;
  position: relative;
}

:deep(.search-box .p-iconfield) {
  width: 100%;
}

:deep(.search-input) {
  width: 100%;
  font-size: 0.78rem !important;
  padding-top: 0.3rem !important;
  padding-bottom: 0.3rem !important;
  background-color: var(--vscode-bg-input, #1e1e1e) !important;
  border-color: var(--vscode-border, #333333) !important;
  color: var(--vscode-text-main, #cccccc) !important;
}

:deep(.search-input:focus) {
  border-color: var(--vscode-blue, #007acc) !important;
}

.clear-search-icon {
  cursor: pointer;
  color: var(--vscode-text-muted, #858585);
  font-size: 0.75rem;
}

.filter-buttons {
  display: flex;
  gap: 0.35rem;
  flex-shrink: 0;
}

:deep(.filter-pill-btn) {
  font-size: 0.72rem !important;
  padding: 0.25rem 0.55rem !important;
}

/* 規則樹狀分類清單 (最大化可視範圍與垂直滾動) */
.rule-tree-container {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  padding-right: 0.2rem;
}

.empty-rules {
  padding: 2.5rem;
  text-align: center;
  color: var(--vscode-text-muted, #858585);
  font-size: 0.82rem;
}

/* 樹狀分類卡片 */
.category-node {
  flex-shrink: 0; /* 關鍵：避免 flexbox 在高度不足時壓縮分類卡片導致文字遮擋 */
  border: 1px solid var(--vscode-border, #333333);
  border-radius: 4px;
  background-color: var(--vscode-bg-base, #1e1e1e);
  overflow: hidden;
}

.category-node-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.4rem 0.65rem;
  background-color: var(--vscode-bg-header, #2d2d2d);
  cursor: pointer;
  user-select: none;
  transition: background-color 0.15s ease;
}

.category-node-header:hover {
  background-color: var(--vscode-bg-hover, #37373d);
}

.node-left {
  display: flex;
  align-items: center;
  gap: 0.45rem;
}

.collapse-icon {
  color: var(--vscode-text-muted, #858585);
  font-size: 0.7rem;
  display: flex;
  align-items: center;
}

.folder-icon {
  color: #38bdf8;
  font-size: 0.82rem;
  display: flex;
  align-items: center;
}

.category-title {
  font-weight: 600;
  font-size: 0.8rem;
  color: var(--vscode-text-heading, #ffffff);
}

.category-meta-badge {
  font-size: 0.72rem;
  color: var(--vscode-text-muted, #858585);
  margin-left: 0.2rem;
}

.meta-rec {
  color: #4ade80;
  font-weight: 500;
}

:deep(.cat-action-btn) {
  font-size: 0.68rem !important;
  padding: 0.15rem 0.4rem !important;
}

/* 子規則項目清單 */
.category-children {
  display: flex;
  flex-direction: column;
}

.tree-rule-item {
  display: flex;
  align-items: flex-start;
  gap: 0.6rem;
  padding: 0.45rem 0.75rem;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  cursor: pointer;
  transition: background-color 0.12s ease;
  box-sizing: border-box;
}

.tree-rule-item:hover {
  background-color: rgba(255, 255, 255, 0.03);
}

.tree-rule-item.selected {
  background-color: rgba(56, 189, 248, 0.06);
}

.tree-rule-item.border-fatal {
  border-left: 3px solid #ef4444;
}

:deep(.rule-checkbox) {
  margin-top: 0.1rem;
  flex-shrink: 0;
}

.rule-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.rule-title-row {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  flex-wrap: wrap;
}

.rule-name {
  font-weight: 600;
  font-size: 0.8rem;
  color: var(--vscode-text-heading, #ffffff);
  line-height: 1.35;
}

.rule-id-badge {
  font-size: 0.68rem;
  color: #94a3b8;
  background-color: rgba(255, 255, 255, 0.06);
  padding: 0.05rem 0.35rem;
  border-radius: 3px;
  font-family: var(--vscode-editor-font-family, monospace);
}

:deep(.severity-tag) {
  font-size: 0.62rem !important;
  padding: 0.05rem 0.3rem !important;
  line-height: 1 !important;
}

:deep(.type-tag) {
  font-size: 0.62rem !important;
  padding: 0.05rem 0.3rem !important;
  line-height: 1 !important;
}

.rule-subtext {
  font-size: 0.72rem;
  line-height: 1.35;
}

.reason-text {
  color: #fbbf24;
  font-weight: 500;
}

.rule-desc {
  color: var(--vscode-text-muted, #858585);
}

.rule-tags-row {
  display: flex;
  gap: 0.25rem;
  flex-wrap: wrap;
}

.mini-tag {
  font-size: 0.62rem;
  color: var(--vscode-text-muted, #858585);
  background-color: rgba(255, 255, 255, 0.04);
  padding: 0.05rem 0.25rem;
  border-radius: 2px;
}

.rule-status-badge {
  margin-top: 0.05rem;
  flex-shrink: 0;
}

:deep(.recommended-tag) {
  font-size: 0.68rem !important;
  padding: 0.1rem 0.35rem !important;
}

.unrecommended-tag {
  font-size: 0.68rem;
  color: var(--vscode-text-muted, #858585);
}

/* 底部確認與統計列 (緊湊 VS Code 狀態底欄) */
.tree-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.75rem;
  padding-top: 0.45rem;
  border-top: 1px solid var(--vscode-border, #333333);
  flex-shrink: 0;
}

.footer-stats {
  display: flex;
  align-items: baseline;
  gap: 0.45rem;
  flex-wrap: wrap;
}

.selected-count-text {
  font-size: 0.82rem;
  color: var(--vscode-text-heading, #ffffff);
}

.stats-subtext {
  font-size: 0.72rem;
  color: var(--vscode-text-muted, #858585);
}

.footer-actions {
  flex-shrink: 0;
}

:deep(.confirm-run-btn) {
  font-size: 0.8rem !important;
  padding: 0.35rem 0.85rem !important;
}

.text-amber { color: #f59e0b; }
.text-success { color: #22c55e; }
.text-cyan { color: #38bdf8; }
.cursor-pointer { cursor: pointer; }
.w-full { width: 100%; }
.mr-1 { margin-right: 0.25rem; }
.mr-2 { margin-right: 0.5rem; }
</style>
