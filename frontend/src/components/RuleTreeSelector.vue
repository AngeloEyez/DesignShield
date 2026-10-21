<template>
  <div class="rule-tree-card flex flex-col h-full bg-transparent overflow-hidden text-vscode-textMain gap-2 box-border">
    <!-- 頂部說明與批次選取列 (無痕極簡單行 Hint + 圖示按鈕) -->
    <div class="tree-header flex justify-between items-center gap-3 shrink-0 pb-1.5 border-b border-surface-border">
      <div class="tree-header-intro flex-1 min-w-0">
        <span class="card-desc m-0 text-xs text-vscode-textMuted flex items-center leading-normal">
          <i class="pi pi-sparkles text-primary mr-1.5"></i>
          系統已依圖譜特徵自動推薦標註規則，可於下方領域目錄自由微調選取。
        </span>
      </div>

      <div class="header-actions flex items-center gap-1 shrink-0">
        <button
          v-tooltip.bottom="isAllRecommendedSelected ? '取消全選推薦規則' : '全選所有推薦規則'"
          type="button"
          class="compact-action-btn inline-flex items-center justify-center w-6 h-6 rounded text-xs text-vscode-textSecondary hover:text-vscode-textHeading hover:bg-surface-hover bg-transparent border-0 cursor-pointer transition-colors"
          :title="isAllRecommendedSelected ? '取消全選' : '全選所有推薦'"
          @click="toggleSelectRecommended"
        >
          <i class="pi pi-filter text-xs"></i>
          <span class="sr-only">{{ isAllRecommendedSelected ? '取消全選' : '全選所有推薦' }}</span>
        </button>
        <button
          v-tooltip.bottom="isAllRulesSelected ? '清空全部已選規則' : '全選所有啟用規則'"
          type="button"
          class="compact-action-btn inline-flex items-center justify-center w-6 h-6 rounded text-xs text-vscode-textSecondary hover:text-vscode-textHeading hover:bg-surface-hover bg-transparent border-0 cursor-pointer transition-colors"
          :title="isAllRulesSelected ? '清空全部' : '全選所有規則'"
          @click="toggleSelectAll"
        >
          <i class="pi pi-check-circle text-xs"></i>
          <span class="sr-only">{{ isAllRulesSelected ? '清空全部' : '全選所有規則' }}</span>
        </button>
        <button
          v-tooltip.bottom="isAllExpanded ? '摺疊全部領域目錄' : '展開全部領域目錄'"
          type="button"
          class="compact-action-btn inline-flex items-center justify-center w-6 h-6 rounded text-xs text-vscode-textSecondary hover:text-vscode-textHeading hover:bg-surface-hover bg-transparent border-0 cursor-pointer transition-colors"
          :title="isAllExpanded ? '摺疊全部' : '展開全部'"
          @click="toggleExpandAll"
        >
          <i :class="isAllExpanded ? 'pi pi-chevron-up' : 'pi pi-chevron-down'" class="text-xs"></i>
          <span class="sr-only">{{ isAllExpanded ? '摺疊全部' : '展開全部' }}</span>
        </button>
      </div>
    </div>

    <!-- 預先分析特徵與 BOM Config 單行整合橫條 (Compact Metric Strip) -->
    <div class="summary-chips flex flex-wrap items-center justify-between gap-3 px-3 py-1.5 rounded bg-surface-panel border border-surface-border text-xs text-vscode-textSecondary shrink-0 select-none">
      <div class="flex items-center gap-2.5 flex-wrap">
        <div class="chip-item flex items-center gap-1 whitespace-nowrap">
          <i class="pi pi-box chip-icon text-vscode-textMuted"></i>
          <span class="chip-label text-vscode-textMuted">元件總數:</span>
          <span class="chip-value font-mono font-semibold text-vscode-textHeading">{{ summary.component_count }}</span>
        </div>
        <div class="chip-divider w-px h-3 bg-surface-border"></div>
        <div class="chip-item flex items-center gap-1 whitespace-nowrap">
          <i class="pi pi-share-alt chip-icon text-vscode-textMuted"></i>
          <span class="chip-label text-vscode-textMuted">網路總數:</span>
          <span class="chip-value font-mono font-semibold text-vscode-textHeading">{{ summary.net_count }}</span>
        </div>
        <div class="chip-divider w-px h-3 bg-surface-border"></div>
        <div class="chip-item flex items-center gap-1 whitespace-nowrap">
          <i class="pi pi-compass chip-icon text-vscode-textMuted"></i>
          <span class="chip-label text-vscode-textMuted">偵測匯流排:</span>
          <span class="chip-value font-mono font-medium text-primary">{{ summary.buses.join(', ') || '未偵測' }}</span>
        </div>
        <div class="chip-divider w-px h-3 bg-surface-border"></div>
        <div class="chip-item flex items-center gap-1 whitespace-nowrap">
          <i class="pi pi-server chip-icon text-vscode-textMuted"></i>
          <span class="chip-label text-vscode-textMuted">主控平台:</span>
          <span class="chip-value font-mono font-medium text-vscode-textMain">{{ summary.platforms.join(', ') || '通用' }}</span>
        </div>
      </div>

      <!-- BOM Config 執行設定 -->
      <div class="bom-config-toolbar flex items-center gap-2 flex-wrap">
        <div v-if="summary.is_multi_config && (summary.config_names?.length || 0) > 1" class="flex items-center gap-1.5 flex-wrap">
          <span class="text-vscode-textMuted font-medium flex items-center gap-1">
            <i class="pi pi-sliders-h text-primary text-[11px]"></i>
            <span>BOM Config:</span>
          </span>
          <div class="flex items-center gap-1 flex-wrap">
            <div
              v-for="cfg in summary.config_names"
              :key="cfg"
              class="flex items-center gap-1.5 px-2 py-0.5 rounded bg-surface-ground border transition-colors cursor-pointer"
              :class="selectedConfigs.includes(cfg) ? 'border-primary bg-primary/10 text-vscode-textHeading' : 'border-surface-border text-vscode-textMuted hover:border-surface-borderLight'"
              @click="toggleConfigSelect(cfg)"
            >
              <Checkbox
                v-model="selectedConfigs"
                :value="cfg"
                :input-id="`cfg-cb-${cfg}`"
                size="small"
                @click.stop
              />
              <label :for="`cfg-cb-${cfg}`" class="cursor-pointer text-xs font-mono select-none">
                {{ cfg }}
              </label>
            </div>
          </div>
          <Button
            :label="isAllConfigsSelected ? '清空 Config' : '全選 Config'"
            text
            size="small"
            severity="secondary"
            class="text-[11px] px-1.5 py-0.5 text-vscode-textMuted hover:text-vscode-textHeading"
            @click="toggleAllConfigs"
          />
        </div>
        <div v-else class="flex items-center gap-1 text-vscode-textMuted text-[11px]">
          <i class="pi pi-file text-primary text-[10px]"></i>
          <span>BOM Config: <strong class="text-vscode-textMain font-mono">{{ summary.config_names?.[0] || 'Config 1' }}</strong></span>
        </div>
      </div>
    </div>

    <!-- 統合篩選列 (Unified Filter Bar: 單行整合搜尋、分類 Tab 與密度切換) -->
    <div class="filter-toolbar flex flex-wrap items-center gap-2 justify-between shrink-0 py-0.5">
      <div class="search-box flex-1 min-w-[220px]">
        <IconField class="w-full">
          <InputIcon class="pi pi-search search-icon text-vscode-textMuted text-xs" />
          <InputText
            v-model="searchQuery"
            type="text"
            size="small"
            class="search-input w-full text-xs"
            placeholder="搜尋規則代碼、名稱、標籤或領域..."
          />
          <InputIcon
            v-if="searchQuery"
            class="pi pi-times clear-search-icon text-vscode-textMuted hover:text-vscode-textHeading cursor-pointer text-xs"
            @click="searchQuery = ''"
          />
        </IconField>
      </div>

      <div class="filter-buttons flex items-center gap-1 shrink-0">
        <Button
          :label="`全部規則 (${totalRulesCount})`"
          size="small"
          :severity="filterMode === 'all' ? 'primary' : 'secondary'"
          :variant="filterMode === 'all' ? undefined : 'outlined'"
          class="filter-pill-btn text-xs px-2 py-1 h-7"
          @click="filterMode = 'all'"
        />
        <Button
          :label="`僅推薦 (${recommendedCount})`"
          icon="pi pi-star-fill text-vscode-yellow"
          size="small"
          :severity="filterMode === 'recommended' ? 'primary' : 'secondary'"
          :variant="filterMode === 'recommended' ? undefined : 'outlined'"
          class="filter-pill-btn text-xs px-2 py-1 h-7"
          @click="filterMode = 'recommended'"
        />
        <Button
          :label="`僅已勾選 (${selectedRuleIds.length})`"
          icon="pi pi-check text-vscode-green"
          size="small"
          :severity="filterMode === 'selected' ? 'primary' : 'secondary'"
          :variant="filterMode === 'selected' ? undefined : 'outlined'"
          class="filter-pill-btn text-xs px-2 py-1 h-7"
          @click="filterMode = 'selected'"
        />

        <div class="h-3 w-px bg-surface-border mx-0.5"></div>

        <!-- 視圖密度切換按鈕 (圖示 + Tooltip，保留 sr-only 文字供測試斷言) -->
        <button
          v-tooltip.bottom="viewDensity === 'compact' ? '目前為緊湊視圖 (點擊切換為詳細視圖)' : '目前為詳細視圖 (點擊切換為緊湊視圖)'"
          type="button"
          class="density-toggle-btn inline-flex items-center justify-center w-7 h-7 rounded text-xs text-vscode-textSecondary hover:text-vscode-textHeading hover:bg-surface-hover bg-transparent border border-surface-border cursor-pointer transition-colors"
          :title="viewDensity === 'compact' ? '切換為詳細視圖' : '切換為緊湊視圖'"
          @click="viewDensity = viewDensity === 'compact' ? 'detailed' : 'compact'"
        >
          <i :class="viewDensity === 'compact' ? 'pi pi-list' : 'pi pi-bars'" class="text-xs"></i>
          <span class="sr-only">{{ viewDensity === 'compact' ? '緊湊視圖' : '詳細視圖' }}</span>
        </button>
      </div>
    </div>

    <!-- 規則樹狀分類清單 (輕量無框分組 Borderless Section Groups，獨立流暢滾動) -->
    <div class="rule-tree-container flex-1 overflow-y-auto flex flex-col gap-2 min-h-0 pr-1 pb-6">
      <div v-if="filteredCategories.length === 0" class="empty-rules p-8 text-center text-vscode-textMuted text-xs">
        <i class="pi pi-info-circle mr-2"></i>
        <span>{{ totalRulesCount === 0 ? '無規則可選' : '無符合條件的規則項目' }}</span>
      </div>

      <div
        v-for="catNode in filteredCategories"
        :key="catNode.category"
        class="category-node flex flex-col bg-surface-panel border border-surface-border rounded overflow-hidden"
      >
        <!-- 樹狀結構父節點：分類標題 -->
        <div
          class="category-node-header flex justify-between items-center px-2.5 py-1.5 bg-surface-header border-b border-surface-border cursor-pointer select-none text-vscode-textMain hover:text-vscode-textHeading transition-colors"
          @click="toggleCategory(catNode.category)"
        >
          <div class="node-left flex items-center gap-1.5 text-xs font-medium">
            <span class="collapse-icon text-vscode-textMuted text-[10px]">
              <i :class="isCategoryExpanded(catNode.category) ? 'pi pi-chevron-down' : 'pi pi-chevron-right'"></i>
            </span>
            <span class="folder-icon text-primary text-xs">
              <i :class="isCategoryExpanded(catNode.category) ? 'pi pi-folder-open' : 'pi pi-folder'"></i>
            </span>
            <span class="category-title text-vscode-textHeading font-semibold">{{ catNode.category }}</span>
            <span class="category-meta-badge text-[11px] text-vscode-textMuted font-normal ml-1">
              共 {{ catNode.rules.length }} 條
              <span v-if="catNode.recommendedCount > 0" class="meta-rec text-primary font-medium">
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
              class="cat-action-btn text-[11px] px-1.5 py-0.5 h-6 text-vscode-textSecondary hover:text-vscode-textHeading"
              @click="toggleCategorySelect(catNode)"
            />
          </div>
        </div>

        <!-- 樹狀結構子節點清單 -->
        <div
          v-show="isCategoryExpanded(catNode.category)"
          class="category-children flex flex-col divide-y divide-surface-border"
        >
          <div
            v-for="rule in catNode.rules"
            :key="rule.id"
            class="tree-rule-item group flex flex-col px-2.5 py-1.5 transition-colors text-xs"
            :class="{
              'hover:bg-surface-hover cursor-pointer': rule.enabled !== false,
              'bg-primary/5': selectedRuleIds.includes(rule.id),
              'opacity-50 cursor-not-allowed bg-surface-ground': rule.enabled === false,
            }"
            @click="toggleRuleSelect(rule.id)"
          >
            <!-- 主行：緊湊核心資訊 (勾選框 + 中文標題 + 嚴重度 + 推薦標記 + 單項展開箭頭) -->
            <div class="rule-row-header flex items-center justify-between gap-2">
              <div class="rule-title-row flex items-center gap-2 flex-1 min-w-0" @click.stop>
                <Checkbox
                  v-model="selectedRuleIds"
                  :value="rule.id"
                  :disabled="rule.enabled === false"
                  size="small"
                  class="rule-checkbox mr-0.5"
                />

                <span class="rule-name font-medium text-vscode-textHeading truncate text-xs">{{ rule.name }}</span>

                <span
                  v-if="isRuleExpanded(rule.id)"
                  class="rule-id-badge font-mono text-[10px] text-vscode-textMuted bg-surface-ground px-1.5 py-0.2 rounded border border-surface-border shrink-0"
                >
                  {{ rule.id }}
                </span>

                <!-- 嚴重度標籤 -->
                <Tag
                  v-if="rule.severity"
                  :value="rule.severity"
                  :severity="getSeverityTagSeverity(rule.severity)"
                  class="severity-tag text-[10px] px-1.5 py-0.2 rounded shrink-0"
                />

                <!-- 僅在為大模型時顯示簡潔中性 LLM 標籤 -->
                <span
                  v-if="isLlmRule(rule.check_type)"
                  class="llm-tag text-[10px] font-mono px-1.5 py-0.2 rounded bg-primary/10 text-primary border border-primary/30 shrink-0"
                >
                  LLM
                </span>
              </div>

              <!-- 右側推薦徽章與單項展開箭頭 -->
              <div class="rule-actions-col flex items-center gap-1.5 shrink-0" @click.stop>
                <Tag
                  v-if="rule.enabled === false"
                  value="已停用"
                  severity="secondary"
                  class="disabled-tag text-[10px] px-1.5 py-0.2 rounded font-normal"
                />
                <Tag
                  v-else-if="isRecommended(rule.id)"
                  value="推薦"
                  severity="success"
                  class="recommended-tag text-[10px] px-1.5 py-0.2 rounded font-normal"
                />
                <span
                  v-else
                  class="unrecommended-tag text-[10px] text-vscode-textMuted bg-surface-ground px-1.5 py-0.2 rounded border border-surface-border font-normal"
                >
                  <i class="pi pi-plus-circle mr-1 text-[9px]"></i>未推薦 (可自選)
                </span>

                <!-- 單項展開/收合細節箭頭 -->
                <button
                  v-tooltip.left="isRuleExpanded(rule.id) ? '收起詳細技術細節' : '展開詳細技術細節'"
                  type="button"
                  class="expand-rule-btn bg-transparent border-0 text-vscode-textMuted hover:text-vscode-textHeading cursor-pointer p-0.5 text-xs transition-colors"
                  :title="isRuleExpanded(rule.id) ? '收起詳細技術細節' : '展開詳細技術細節'"
                  @click="toggleRuleExpanded(rule.id)"
                >
                  <i :class="isRuleExpanded(rule.id) ? 'pi pi-chevron-down' : 'pi pi-chevron-right'"></i>
                </button>
              </div>
            </div>

            <!-- 漸進式揭露細節區 -->
            <div
              v-if="isRuleExpanded(rule.id)"
              class="rule-expanded-details mt-1.5 pl-5 flex flex-col gap-1 text-[11px] text-vscode-textSecondary border-l-2 border-primary/40 ml-1.5"
            >
              <div v-if="getRuleReason(rule.id)" class="reason-text text-primary font-medium">
                <i class="pi pi-bolt mr-1"></i>推薦原因: {{ getRuleReason(rule.id) }}
              </div>

              <div v-if="rule.description && rule.description !== rule.name" class="rule-desc text-vscode-textSecondary">
                {{ rule.description }}
              </div>

              <div v-if="rule.tags && rule.tags.length > 0" class="rule-tags-row flex gap-1.5 flex-wrap">
                <span v-for="t in rule.tags" :key="t" class="mini-tag text-[10px] text-vscode-textMuted font-mono">#{{ t }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 底部確認與統計列 -->
    <div class="tree-footer shrink-0 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 pt-2 pb-1 border-t border-surface-border bg-surface-header px-3 rounded text-xs">
      <div class="footer-stats flex items-center gap-2 flex-wrap text-vscode-textSecondary">
        <span class="selected-count-text">
          已選取 <strong class="text-vscode-textHeading">{{ selectedRuleIds.length }}</strong> 條規則
        </span>
        <span class="stats-subtext text-vscode-textMuted text-[11px]">
          (包含 <strong>{{ selectedRecommendedCount }}</strong> 條推薦規則，
          <strong>{{ selectedNonRecommendedCount }}</strong> 條額外選取規則)
        </span>
        <span v-if="summary.is_multi_config" class="text-primary font-mono text-[11px]">
          · 將執行 {{ selectedConfigs.length }} 組 Config
        </span>
      </div>

      <div class="footer-actions">
        <Button
          label="確認並啟動正式 DRC"
          icon="pi pi-play"
          severity="primary"
          size="small"
          class="confirm-run-btn text-xs"
          :loading="isSubmitting"
          :disabled="selectedRuleIds.length === 0 || (summary.is_multi_config && selectedConfigs.length === 0)"
          @click="confirmAndRun"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * @file RuleTreeSelector.vue
 * @description Level 3 DRC 規則選取樹狀面板，支援圖譜特徵自動推薦、實體領域分群與多維度過濾 (雙主題適配)
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
  enabled?: boolean
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
  (e: 'run', payload: { ruleIds: string[]; selectedConfigs?: string[] } | string[]): void
}>()

const selectedConfigs = ref<string[]>([])

watch(
  () => props.summary.config_names,
  (names) => {
    if (names && names.length > 0) {
      selectedConfigs.value = [...names]
    } else {
      selectedConfigs.value = ['Config 1']
    }
  },
  { immediate: true }
)

const isAllConfigsSelected = computed(() => {
  const allNames = props.summary.config_names || ['Config 1']
  return allNames.length > 0 && selectedConfigs.value.length === allNames.length
})

const toggleAllConfigs = () => {
  const allNames = props.summary.config_names || ['Config 1']
  if (isAllConfigsSelected.value) {
    selectedConfigs.value = []
  } else {
    selectedConfigs.value = [...allNames]
  }
}

const toggleConfigSelect = (cfgName: string) => {
  const idx = selectedConfigs.value.indexOf(cfgName)
  if (idx > -1) {
    selectedConfigs.value.splice(idx, 1)
  } else {
    selectedConfigs.value.push(cfgName)
  }
}

const viewDensity = ref<'compact' | 'detailed'>('compact')
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
  const rule = internalAllRules.value.find((r) => r.id === ruleId)
  if (rule && rule.enabled === false) {
    return
  }
  if (selectedRuleIds.value.includes(ruleId)) {
    selectedRuleIds.value = selectedRuleIds.value.filter((id) => id !== ruleId)
  } else {
    selectedRuleIds.value.push(ruleId)
  }
}

const selectedRuleIds = ref<string[]>([])
const searchQuery = ref<string>('')
const filterMode = ref<'all' | 'recommended' | 'selected'>('all')
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
        enabled: r.enabled !== false,
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
          enabled: r.enabled !== false,
        })
      }
    })
  }
  return Array.from(merged.values())
}

const internalAllRules = ref<TreeRuleItem[]>(buildRulesFromProps())

watch(
  [() => props.allRules, () => props.recommendedRules],
  () => {
    internalAllRules.value = buildRulesFromProps()
  },
  { deep: true }
)

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
        enabled: r.enabled !== false,
      }))
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
            enabled: r.enabled !== false,
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

const recommendedIdSet = computed(() => {
  return new Set(props.recommendedRules.map((r) => r.id))
})

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

watch(
  () => props.recommendedRules,
  (newRecs) => {
    if (newRecs && newRecs.length > 0) {
      const recIds = newRecs.filter((r: any) => r.enabled !== false).map((r) => r.id)
      selectedRuleIds.value = Array.from(new Set([...selectedRuleIds.value, ...recIds]))
      newRecs.forEach((r) => {
        if (r.category) expandedCategories.value[r.category] = true
      })
    }
  },
  { immediate: true }
)

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

interface CategoryNode {
  category: string
  rules: TreeRuleItem[]
  recommendedCount: number
}

const filteredCategories = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  const map = new Map<string, TreeRuleItem[]>()

  internalAllRules.value.forEach((rule) => {
    if (filterMode.value === 'recommended' && !isRecommended(rule.id)) return
    if (filterMode.value === 'selected' && !selectedRuleIds.value.includes(rule.id)) return

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

const isCategoryAllSelected = (catNode: CategoryNode): boolean => {
  const activeRules = catNode.rules.filter((r) => r.enabled !== false)
  if (activeRules.length === 0) return false
  return activeRules.every((r) => selectedRuleIds.value.includes(r.id))
}

const toggleCategorySelect = (catNode: CategoryNode) => {
  const allSel = isCategoryAllSelected(catNode)
  const activeCatIds = catNode.rules.filter((r) => r.enabled !== false).map((r) => r.id)
  if (allSel) {
    selectedRuleIds.value = selectedRuleIds.value.filter((id) => !activeCatIds.includes(id))
  } else {
    selectedRuleIds.value = Array.from(new Set([...selectedRuleIds.value, ...activeCatIds]))
  }
}

const isAllRecommendedSelected = computed(() => {
  const recRules = internalAllRules.value.filter((r) => isRecommended(r.id) && r.enabled !== false)
  if (recRules.length === 0) return false
  return recRules.every((r) => selectedRuleIds.value.includes(r.id))
})

const toggleSelectRecommended = () => {
  const recIds = internalAllRules.value
    .filter((r) => isRecommended(r.id) && r.enabled !== false)
    .map((r) => r.id)
  if (isAllRecommendedSelected.value) {
    selectedRuleIds.value = selectedRuleIds.value.filter((id) => !recIds.includes(id))
  } else {
    selectedRuleIds.value = Array.from(new Set([...selectedRuleIds.value, ...recIds]))
  }
}

const isAllRulesSelected = computed(() => {
  const activeRules = internalAllRules.value.filter((r) => r.enabled !== false)
  if (activeRules.length === 0) return false
  return activeRules.every((r) => selectedRuleIds.value.includes(r.id))
})

const toggleSelectAll = () => {
  if (isAllRulesSelected.value) {
    selectedRuleIds.value = []
  } else {
    selectedRuleIds.value = internalAllRules.value
      .filter((r) => r.enabled !== false)
      .map((r) => r.id)
  }
}

const getSeverityTagSeverity = (sev?: string): 'danger' | 'warn' | 'info' | 'secondary' => {
  switch (sev) {
    case 'Fatal':
    case 'Error':
      return 'danger'
    case 'Warning':
      return 'warn'
    default:
      return 'secondary'
  }
}

const confirmAndRun = () => {
  emit('run', {
    ruleIds: selectedRuleIds.value,
    selectedConfigs: props.summary.is_multi_config ? selectedConfigs.value : undefined,
  })
}

onMounted(() => {
  loadAllRules()
})
</script>
