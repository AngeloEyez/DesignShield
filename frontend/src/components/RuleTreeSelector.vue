<template>
  <div class="rule-tree-card flex flex-col h-full gap-2.5 bg-surface-card border border-surface-border rounded-md p-3 box-border">
    <!-- 頂部說明與批次選取列 -->
    <div class="tree-header flex justify-between items-center gap-3 shrink-0 pb-2 border-b border-surface-border">
      <div class="tree-header-intro flex-1 min-w-0">
        <span class="card-desc m-0 text-xs text-surface-400 leading-normal">
          <i class="pi pi-sparkles text-sky-400 mr-1"></i>系統依據圖譜特徵自動比對觸發條件並推薦標註規則（預設已勾選），您可於下方領域目錄樹狀結構中自由選取或展開其他未被推薦的規則。
        </span>
      </div>

      <div class="header-actions flex items-center gap-1 shrink-0">
        <Button
          :label="isAllRecommendedSelected ? '取消全選' : '全選所有推薦'"
          icon="pi pi-filter"
          text
          size="small"
          severity="info"
          class="compact-action-btn text-xs px-2 py-1"
          @click="toggleSelectRecommended"
        />
        <Button
          :label="isAllRulesSelected ? '清空全部' : '全選所有規則'"
          icon="pi pi-check-circle"
          text
          size="small"
          severity="secondary"
          class="compact-action-btn text-xs px-2 py-1"
          @click="toggleSelectAll"
        />
        <Button
          :icon="isAllExpanded ? 'pi pi-chevron-up' : 'pi pi-chevron-down'"
          :label="isAllExpanded ? '摺疊全部' : '展開全部'"
          text
          size="small"
          severity="secondary"
          class="compact-action-btn text-xs px-2 py-1"
          @click="toggleExpandAll"
        />
      </div>
    </div>

    <!-- 預先分析特徵摘要列 (VS Code Status Bar 風格) -->
    <div class="summary-chips flex items-center gap-3 px-3 py-1.5 rounded bg-surface-ground border border-surface-border text-xs text-surface-300 overflow-x-auto">
      <div class="chip-item flex items-center gap-1 whitespace-nowrap">
        <i class="pi pi-box chip-icon text-surface-400"></i>
        <span class="chip-label text-surface-400">元件總數:</span>
        <span class="chip-value font-mono font-semibold text-surface-900 dark:text-surface-0">{{ summary.component_count }}</span>
      </div>
      <div class="chip-divider w-px h-3 bg-surface-border"></div>
      <div class="chip-item flex items-center gap-1 whitespace-nowrap">
        <i class="pi pi-share-alt chip-icon text-surface-400"></i>
        <span class="chip-label text-surface-400">網路總數:</span>
        <span class="chip-value font-mono font-semibold text-surface-900 dark:text-surface-0">{{ summary.net_count }}</span>
      </div>
      <div class="chip-divider w-px h-3 bg-surface-border"></div>
      <div class="chip-item flex items-center gap-1 whitespace-nowrap">
        <i class="pi pi-compass chip-icon text-surface-400"></i>
        <span class="chip-label text-surface-400">偵測匯流排:</span>
        <span class="chip-value font-mono font-semibold text-sky-400">{{ summary.buses.join(', ') || '未偵測' }}</span>
      </div>
      <div class="chip-divider w-px h-3 bg-surface-border"></div>
      <div class="chip-item flex items-center gap-1 whitespace-nowrap">
        <i class="pi pi-server chip-icon text-surface-400"></i>
        <span class="chip-label text-surface-400">主控平台:</span>
        <span class="chip-value font-mono font-semibold text-violet-400">{{ summary.platforms.join(', ') || '通用' }}</span>
      </div>
    </div>

    <!-- 快速搜尋與多維度過濾列 -->
    <div class="filter-toolbar flex flex-col sm:flex-row items-stretch sm:items-center gap-2 justify-between">
      <div class="search-box flex-1 min-w-0">
        <IconField class="w-full">
          <InputIcon class="pi pi-search search-icon text-surface-400 text-xs" />
          <InputText
            v-model="searchQuery"
            type="text"
            size="small"
            class="search-input w-full text-xs"
            placeholder="搜尋規則代碼、名稱、標籤或領域..."
          />
          <InputIcon
            v-if="searchQuery"
            class="pi pi-times clear-search-icon text-surface-400 hover:text-surface-200 cursor-pointer text-xs"
            @click="searchQuery = ''"
          />
        </IconField>
      </div>

      <div class="filter-buttons flex items-center gap-1.5 shrink-0">
        <Button
          :label="`全部規則 (${totalRulesCount})`"
          size="small"
          :severity="filterMode === 'all' ? 'primary' : 'secondary'"
          :variant="filterMode === 'all' ? undefined : 'outlined'"
          class="filter-pill-btn text-xs px-2.5 py-1"
          @click="filterMode = 'all'"
        />
        <Button
          :label="`僅推薦 (${recommendedCount})`"
          icon="pi pi-star-fill text-amber-400"
          size="small"
          :severity="filterMode === 'recommended' ? 'primary' : 'secondary'"
          :variant="filterMode === 'recommended' ? undefined : 'outlined'"
          class="filter-pill-btn text-xs px-2.5 py-1"
          @click="filterMode = 'recommended'"
        />
        <Button
          :label="`僅已勾選 (${selectedRuleIds.length})`"
          icon="pi pi-check text-green-400"
          size="small"
          :severity="filterMode === 'selected' ? 'primary' : 'secondary'"
          :variant="filterMode === 'selected' ? undefined : 'outlined'"
          class="filter-pill-btn text-xs px-2.5 py-1"
          @click="filterMode = 'selected'"
        />
      </div>
    </div>

    <!-- 規則樹狀分類清單 (Tree Structure by Domain / Category) -->
    <div class="rule-tree-container flex-1 overflow-y-auto flex flex-col gap-2 min-h-0 pr-1">
      <div v-if="filteredCategories.length === 0" class="empty-rules p-8 text-center text-surface-400 text-xs">
        <i class="pi pi-info-circle mr-2"></i>
        <span>無符合條件的規則項目</span>
      </div>

      <div
        v-for="catNode in filteredCategories"
        :key="catNode.category"
        class="category-node border border-surface-border rounded-md overflow-hidden bg-surface-ground/30"
      >
        <!-- 樹狀結構父節點：領域/分類標頭 -->
        <div class="category-node-header flex justify-between items-center px-3 py-2 bg-surface-ground cursor-pointer select-none hover:bg-surface-hover transition-colors" @click="toggleCategory(catNode.category)">
          <div class="node-left flex items-center gap-2 text-xs font-semibold text-surface-900 dark:text-surface-0">
            <span class="collapse-icon text-surface-400 text-[10px]">
              <i :class="isCategoryExpanded(catNode.category) ? 'pi pi-chevron-down' : 'pi pi-chevron-right'"></i>
            </span>
            <span class="folder-icon text-sky-400 text-xs">
              <i :class="isCategoryExpanded(catNode.category) ? 'pi pi-folder-open' : 'pi pi-folder'"></i>
            </span>
            <span class="category-title">{{ catNode.category }}</span>
            <span class="category-meta-badge text-[11px] text-surface-400 font-normal ml-2">
              共 {{ catNode.rules.length }} 條
              <span v-if="catNode.recommendedCount > 0" class="meta-rec text-green-400 font-medium">
                · {{ catNode.recommendedCount }} 條推薦
              </span>
            </span>
          </div>

          <div class="node-right flex items-center" @click.stop>
            <Button
              :label="isCategoryAllSelected(catNode) ? '取消此類' : '全選此類'"
              size="small"
              text
              severity="secondary"
              class="cat-action-btn text-xs px-2 py-0.5"
              @click="toggleCategorySelect(catNode)"
            />
          </div>
        </div>

        <!-- 樹狀結構子節點清單 -->
        <div v-show="isCategoryExpanded(catNode.category)" class="category-children flex flex-col divide-y divide-surface-border">
          <label
            v-for="rule in catNode.rules"
            :key="rule.id"
            class="tree-rule-item flex items-start gap-2.5 p-2.5 cursor-pointer transition-colors hover:bg-surface-hover/50 text-xs"
            :class="{
              'bg-primary/5': selectedRuleIds.includes(rule.id),
              'border-l-2 border-l-green-400': isRecommended(rule.id),
              'border-l-2 border-l-red-500': rule.severity === 'Fatal' && !isRecommended(rule.id),
            }"
          >
            <Checkbox
              v-model="selectedRuleIds"
              :value="rule.id"
              size="small"
              class="rule-checkbox mr-1 mt-0.5"
            />

            <div class="rule-main flex-1 flex flex-col gap-1 min-w-0">
              <div class="rule-title-row flex items-center gap-2 flex-wrap">
                <span class="rule-name font-semibold text-surface-900 dark:text-surface-0">{{ rule.name }}</span>
                <span class="rule-id-badge font-mono text-[10px] text-surface-400 bg-surface-ground px-1 py-0.5 rounded border border-surface-border">{{ rule.id }}</span>

                <!-- 嚴重度標籤 -->
                <Tag
                  v-if="rule.severity"
                  :value="rule.severity"
                  :severity="getSeverityTagSeverity(rule.severity)"
                  class="severity-tag text-[10px] px-1 py-0.2 rounded"
                />

                <!-- 檢測類型標籤 -->
                <Tag
                  :value="formatCheckType(rule.check_type)"
                  :severity="getCheckTypeSeverity(rule.check_type)"
                  class="type-tag text-[10px] px-1 py-0.2 rounded"
                />
              </div>

              <!-- 說明與推薦原因 (緊湊單行呈現) -->
              <div v-if="getRuleReason(rule.id) || (rule.description && rule.description !== rule.name)" class="rule-subtext text-[11px] text-surface-400 leading-tight">
                <span v-if="getRuleReason(rule.id)" class="reason-text text-amber-300 font-medium">
                  <i class="pi pi-bolt mr-1 text-amber-400"></i>推薦原因: {{ getRuleReason(rule.id) }}
                </span>
                <span v-else-if="rule.description && rule.description !== rule.name" class="rule-desc">
                  {{ rule.description }}
                </span>
              </div>

              <!-- 關聯 Tags -->
              <div v-if="rule.tags && rule.tags.length > 0" class="rule-tags-row flex gap-1 flex-wrap">
                <span v-for="t in rule.tags" :key="t" class="mini-tag text-[10px] text-surface-400 font-mono">#{{ t }}</span>
              </div>
            </div>

            <!-- 標註是否為推薦規則 -->
            <div class="rule-status-badge shrink-0 flex items-center">
              <Tag
                v-if="isRecommended(rule.id)"
                value="推薦"
                severity="success"
                class="recommended-tag text-[10px] px-1.5 py-0.5 rounded"
              />
              <span v-else class="unrecommended-tag text-[10px] text-surface-400 bg-surface-ground px-1.5 py-0.5 rounded border border-surface-border">
                <i class="pi pi-plus-circle mr-1"></i>未推薦 (可自選)
              </span>
            </div>
          </label>
        </div>
      </div>
    </div>

    <!-- 底部確認與統計列 (VS Code 狀態底欄風格) -->
    <div class="tree-footer flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 pt-2 border-t border-surface-border text-xs">
      <div class="footer-stats flex items-center gap-2 flex-wrap text-surface-300">
        <span class="selected-count-text">
          已選取 <strong>{{ selectedRuleIds.length }}</strong> 條規則
        </span>
        <span class="stats-subtext text-surface-400 text-[11px]">
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
