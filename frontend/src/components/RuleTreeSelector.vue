<template>
  <div class="rule-tree-card flex flex-col h-full bg-transparent overflow-hidden text-surface-200 gap-2.5 box-border">
    <!-- 頂部說明與批次選取列 (無痕極簡單行 Hint + 幽靈按鈕) -->
    <div class="tree-header flex justify-between items-center gap-3 shrink-0 pb-1.5 border-b border-surface-border/40">
      <div class="tree-header-intro flex-1 min-w-0">
        <span class="card-desc m-0 text-xs text-surface-400 flex items-center leading-normal">
          <i class="pi pi-sparkles text-sky-400 mr-1.5"></i>
          系統已依圖譜特徵自動推薦標註規則，可於下方領域目錄自由微調選取。
        </span>
      </div>

      <div class="header-actions flex items-center gap-1 shrink-0">
        <Button
          :label="isAllRecommendedSelected ? '取消全選' : '全選所有推薦'"
          icon="pi pi-filter"
          text
          size="small"
          severity="info"
          class="compact-action-btn text-xs px-2 py-0.5 text-surface-400 hover:text-white"
          @click="toggleSelectRecommended"
        />
        <Button
          :label="isAllRulesSelected ? '清空全部' : '全選所有規則'"
          icon="pi pi-check-circle"
          text
          size="small"
          severity="secondary"
          class="compact-action-btn text-xs px-2 py-0.5 text-surface-400 hover:text-white"
          @click="toggleSelectAll"
        />
        <Button
          :icon="isAllExpanded ? 'pi pi-chevron-up' : 'pi pi-chevron-down'"
          :label="isAllExpanded ? '摺疊全部' : '展開全部'"
          text
          size="small"
          severity="secondary"
          class="compact-action-btn text-xs px-2 py-0.5 text-surface-400 hover:text-white"
          @click="toggleExpandAll"
        />
      </div>
    </div>

    <!-- 預先分析特徵摘要列 (收斂中性微型 Status Bar，消除刺眼彩虹文字) -->
    <div class="summary-chips flex items-center gap-3 px-3 py-1.5 rounded bg-surface-ground/70 border border-surface-border/30 text-xs text-surface-400 overflow-x-auto shrink-0 select-none">
      <div class="chip-item flex items-center gap-1 whitespace-nowrap">
        <i class="pi pi-box chip-icon text-surface-500"></i>
        <span class="chip-label text-surface-400">元件總數:</span>
        <span class="chip-value font-mono font-semibold text-surface-100">{{ summary.component_count }}</span>
      </div>
      <div class="chip-divider w-px h-3 bg-surface-border/40"></div>
      <div class="chip-item flex items-center gap-1 whitespace-nowrap">
        <i class="pi pi-share-alt chip-icon text-surface-500"></i>
        <span class="chip-label text-surface-400">網路總數:</span>
        <span class="chip-value font-mono font-semibold text-surface-100">{{ summary.net_count }}</span>
      </div>
      <div class="chip-divider w-px h-3 bg-surface-border/40"></div>
      <div class="chip-item flex items-center gap-1 whitespace-nowrap">
        <i class="pi pi-compass chip-icon text-surface-500"></i>
        <span class="chip-label text-surface-400">偵測匯流排:</span>
        <span class="chip-value font-mono font-medium text-surface-200">{{ summary.buses.join(', ') || '未偵測' }}</span>
      </div>
      <div class="chip-divider w-px h-3 bg-surface-border/40"></div>
      <div class="chip-item flex items-center gap-1 whitespace-nowrap">
        <i class="pi pi-server chip-icon text-surface-500"></i>
        <span class="chip-label text-surface-400">主控平台:</span>
        <span class="chip-value font-mono font-medium text-surface-200">{{ summary.platforms.join(', ') || '通用' }}</span>
      </div>
    </div>

    <!-- 統合篩選列 (Unified Filter Bar: 單行整合搜尋、分類 Tab 與密度切換) -->
    <div class="filter-toolbar flex flex-wrap items-center gap-2 justify-between shrink-0 py-0.5">
      <div class="search-box flex-1 min-w-[220px]">
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

        <div class="h-3 w-px bg-surface-border/50 mx-0.5"></div>

        <!-- 視圖密度切換按鈕 (Compact vs Detailed View) -->
        <Button
          :icon="viewDensity === 'compact' ? 'pi pi-list' : 'pi pi-bars'"
          :label="viewDensity === 'compact' ? '緊湊視圖' : '詳細視圖'"
          size="small"
          text
          severity="secondary"
          class="density-toggle-btn text-xs px-2 py-1 text-surface-400 hover:text-white"
          :title="viewDensity === 'compact' ? '切換為詳細視圖' : '切換為緊湊視圖'"
          @click="viewDensity = viewDensity === 'compact' ? 'detailed' : 'compact'"
        />
      </div>
    </div>

    <!-- 規則樹狀分類清單 (輕量無框分組 Borderless Section Groups，獨立流暢滾動，pb-8 保證絕不遮擋) -->
    <div class="rule-tree-container flex-1 overflow-y-auto flex flex-col gap-3 min-h-0 pr-1 pb-8">
      <div v-if="filteredCategories.length === 0" class="empty-rules p-8 text-center text-surface-400 text-xs">
        <i class="pi pi-info-circle mr-2"></i>
        <span>{{ totalRulesCount === 0 ? '無規則可選' : '無符合條件的規則項目' }}</span>
      </div>

      <div
        v-for="catNode in filteredCategories"
        :key="catNode.category"
        class="category-node flex flex-col"
      >
        <!-- 樹狀結構父節點：輕量無框分類標題 -->
        <div
          class="category-node-header flex justify-between items-center px-1.5 py-1.5 cursor-pointer select-none text-surface-300 hover:text-white transition-colors"
          @click="toggleCategory(catNode.category)"
        >
          <div class="node-left flex items-center gap-1.5 text-xs font-semibold">
            <span class="collapse-icon text-surface-500 text-[10px]">
              <i :class="isCategoryExpanded(catNode.category) ? 'pi pi-chevron-down' : 'pi pi-chevron-right'"></i>
            </span>
            <span class="folder-icon text-sky-400 text-xs">
              <i :class="isCategoryExpanded(catNode.category) ? 'pi pi-folder-open' : 'pi pi-folder'"></i>
            </span>
            <span class="category-title text-surface-100">{{ catNode.category }}</span>
            <span class="category-meta-badge text-[11px] text-surface-500 font-normal ml-1.5">
              共 {{ catNode.rules.length }} 條
              <span v-if="catNode.recommendedCount > 0" class="meta-rec text-surface-400 font-medium">
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
              class="cat-action-btn text-xs px-1.5 py-0.5 text-surface-400 hover:text-white"
              @click="toggleCategorySelect(catNode)"
            />
          </div>
        </div>

        <!-- 樹狀結構子節點清單 (無框無痕分割線，Hover 微弱亮色切換，漸進式揭露) -->
        <div
          v-show="isCategoryExpanded(catNode.category)"
          class="category-children flex flex-col divide-y divide-surface-border/20 pl-2"
        >
          <div
            v-for="rule in catNode.rules"
            :key="rule.id"
            class="tree-rule-item group flex flex-col p-2 transition-colors hover:bg-surface-hover/40 rounded cursor-pointer text-xs"
            :class="{
              'bg-primary/5': selectedRuleIds.includes(rule.id),
            }"
            @click="toggleRuleSelect(rule.id)"
          >
            <!-- 主行：緊湊核心資訊 (勾選框 + 中文標題 + 嚴重度 + 推薦標記 + 單項展開箭頭) -->
            <div class="rule-row-header flex items-center justify-between gap-2">
              <div class="rule-title-row flex items-center gap-2 flex-1 min-w-0" @click.stop>
                <Checkbox
                  v-model="selectedRuleIds"
                  :value="rule.id"
                  size="small"
                  class="rule-checkbox mr-0.5"
                />

                <span class="rule-name font-medium text-surface-100 truncate text-xs">{{ rule.name }}</span>

                <!-- 僅在詳細模式或單項展開時顯示代碼；緊湊模式下收合以降低干擾 -->
                <span
                  v-if="isRuleExpanded(rule.id)"
                  class="rule-id-badge font-mono text-[10px] text-surface-400 bg-surface-ground/70 px-1 py-0.2 rounded border border-surface-border/40 shrink-0"
                >
                  {{ rule.id }}
                </span>

                <!-- 嚴重度標籤 (保留低飽和警示色) -->
                <Tag
                  v-if="rule.severity"
                  :value="rule.severity"
                  :severity="getSeverityTagSeverity(rule.severity)"
                  class="severity-tag text-[10px] px-1 py-0.2 rounded shrink-0"
                />

                <!-- 僅在為大模型時顯示簡潔中性 LLM 標籤，徹底移除拓撲斷言標籤 -->
                <span
                  v-if="isLlmRule(rule.check_type)"
                  class="llm-tag text-[10px] font-mono px-1 py-0.2 rounded bg-purple-500/15 text-purple-300 border border-purple-500/20 shrink-0"
                >
                  LLM
                </span>
              </div>

              <!-- 右側推薦徽章與單項展開箭頭 -->
              <div class="rule-actions-col flex items-center gap-2 shrink-0" @click.stop>
                <!-- 標註是否為推薦規則 (低調精緻微型標籤) -->
                <Tag
                  v-if="isRecommended(rule.id)"
                  value="推薦"
                  severity="success"
                  class="recommended-tag text-[10px] px-1.5 py-0.2 rounded font-normal"
                />
                <span
                  v-else
                  class="unrecommended-tag text-[10px] text-surface-500 bg-surface-ground/50 px-1.5 py-0.2 rounded border border-surface-border/40 font-normal"
                >
                  <i class="pi pi-plus-circle mr-1"></i>未推薦 (可自選)
                </span>

                <!-- 單項展開/收合細節箭頭 -->
                <button
                  type="button"
                  class="expand-rule-btn bg-transparent border-0 text-surface-500 hover:text-surface-200 cursor-pointer p-0.5 text-xs transition-colors"
                  :title="isRuleExpanded(rule.id) ? '收起詳細技術細節' : '展開詳細技術細節'"
                  @click="toggleRuleExpanded(rule.id)"
                >
                  <i :class="isRuleExpanded(rule.id) ? 'pi pi-chevron-down' : 'pi pi-chevron-right'"></i>
                </button>
              </div>
            </div>

            <!-- 漸進式揭露細節區 (詳細模式或展開該項時展示：英文字碼、推薦原因、說明、Hash Tags) -->
            <div
              v-if="isRuleExpanded(rule.id)"
              class="rule-expanded-details mt-1.5 pl-6 flex flex-col gap-1 text-[11px] text-surface-400 border-l border-surface-border/40 ml-1.5"
            >
              <!-- 推薦原因 (次要柔和說明) -->
              <div v-if="getRuleReason(rule.id)" class="reason-text text-amber-300/90 font-medium">
                <i class="pi pi-bolt mr-1 text-amber-400/80"></i>推薦原因: {{ getRuleReason(rule.id) }}
              </div>

              <!-- 規則描述 (若存在且與名稱不同) -->
              <div v-if="rule.description && rule.description !== rule.name" class="rule-desc text-surface-400">
                {{ rule.description }}
              </div>

              <!-- 弱化關聯 Tags -->
              <div v-if="rule.tags && rule.tags.length > 0" class="rule-tags-row flex gap-1.5 flex-wrap">
                <span v-for="t in rule.tags" :key="t" class="mini-tag text-[10px] text-surface-500 font-mono">#{{ t }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 底部確認與統計列 (Sticky 固定底欄，永遠不遮擋列表，VS Code 狀態底欄風格) -->
    <div class="tree-footer shrink-0 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 pt-2.5 pb-1 border-t border-surface-border/50 bg-surface-overlay/90 text-xs rounded-b">
      <div class="footer-stats flex items-center gap-2 flex-wrap text-surface-300">
        <span class="selected-count-text">
          已選取 <strong class="text-white">{{ selectedRuleIds.length }}</strong> 條規則
        </span>
        <span class="stats-subtext text-surface-500 text-[11px]">
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
import { fetchPatternTree } from '@/services/api'
import type { PatternTreeResponse, Level3RuleItem } from '@/types/pattern'

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

interface Props {
  summary: TaskSummary
  recommendedRules: RecommendedRuleItem[]
  allRules?: TreeRuleItem[]
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

// 視圖密度模式 ('compact' 緊湊模式預設 | 'detailed' 詳細模式)
const viewDensity = ref<'compact' | 'detailed'>('compact')
// 單項展開狀態字典
const expandedRuleIds = ref<Record<string, boolean>>({})

const toggleRuleExpanded = (ruleId: string) => {
  expandedRuleIds.value[ruleId] = !expandedRuleIds.value[ruleId]
}

const isRuleExpanded = (ruleId: string): boolean => {
  if (viewDensity.value === 'detailed') return true
  return !!expandedRuleIds.value[ruleId]
}

const isLlmRule = (checkType?: string): boolean => {
  return checkType === 'llm_agent' || checkType === 'LLM' || checkType === 'llm'
}

const toggleRuleSelect = (ruleId: string) => {
  if (selectedRuleIds.value.includes(ruleId)) {
    selectedRuleIds.value = selectedRuleIds.value.filter((id) => id !== ruleId)
  } else {
    selectedRuleIds.value.push(ruleId)
  }
}

// 已選取的 Rule IDs
const selectedRuleIds = ref<string[]>([])

// 搜尋關鍵字與過濾模式 ('all' | 'recommended' | 'selected')
const searchQuery = ref<string>('')
const filterMode = ref<'all' | 'recommended' | 'selected'>('all')

// 摺疊/展開狀態字典
const expandedCategories = ref<Record<string, boolean>>({})

const buildRulesFromProps = (): TreeRuleItem[] => {
  const merged = new Map<string, TreeRuleItem>()
  if (props.allRules && props.allRules.length > 0) {
    props.allRules.forEach((r) => {
      merged.set(r.id, {
        id: r.id,
        name: r.name,
        category: r.category,
        severity: r.severity || 'Error',
        check_type: r.check_type,
        tags: r.tags || [],
        reason: r.reason,
        description: r.description,
        trigger_conditions: r.trigger_conditions,
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
          description: r.description,
        })
      }
    })
  }
  return Array.from(merged.values())
}

// 系統完整規則列表 (100% 依賴真實規則，不捏造任何假資料)
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
      // 合併真實 Level 3 規則與推薦列表
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
    // 異常時如實使用傳入之 props
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

// 點擊確認並執行
const confirmAndRun = () => {
  emit('run', selectedRuleIds.value)
}

onMounted(() => {
  loadAllRules()
})
</script>
