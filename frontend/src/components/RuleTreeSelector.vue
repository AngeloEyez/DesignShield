<template>
  <div class="rule-tree-card flex flex-col h-full bg-transparent overflow-hidden text-vscode-textMain gap-2 box-border min-h-0">
    <!-- 預先分析特徵與 BOM Config 單行整合橫條 (Compact Metric Strip，全寬置頂) -->
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

      <!-- BOM Config 執行設定 (採取 xs size 按鈕) -->
      <div class="bom-config-toolbar flex items-center gap-2 flex-wrap">
        <div v-if="summary.is_multi_config && (summary.config_names?.length || 0) > 1" class="flex items-center gap-1.5 flex-wrap">
          <span class="text-vscode-textMuted font-medium flex items-center gap-1 text-[11px]">
            <i class="pi pi-sliders-h text-primary text-[10px]"></i>
            <span>BOM Config:</span>
          </span>
          <div class="flex items-center gap-1 flex-wrap">
            <div
              v-for="cfg in summary.config_names"
              :key="cfg"
              class="flex items-center gap-1.5 px-1.5 py-0.5 rounded bg-surface-ground border transition-colors cursor-pointer text-[11px]"
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
              <label :for="`cfg-cb-${cfg}`" class="cursor-pointer text-[11px] font-mono select-none">
                {{ cfg }}
              </label>
            </div>
          </div>
          <Button
            :label="isAllConfigsSelected ? '清空 Config' : '全選 Config'"
            text
            size="small"
            severity="secondary"
            class="!text-[11px] !px-1.5 !py-0.5 !h-6 text-vscode-textMuted hover:text-vscode-textHeading"
            @click="toggleAllConfigs"
          />
        </div>
        <div v-else class="flex items-center gap-1 text-vscode-textMuted text-[11px]">
          <i class="pi pi-file text-primary text-[10px]"></i>
          <span>BOM Config: <strong class="text-vscode-textMain font-mono">{{ summary.config_names?.[0] || 'Config 1' }}</strong></span>
        </div>
      </div>
    </div>

    <!-- 行動/窄螢幕橫向滾動分類導航列 (RWD: md:hidden 比照 SettingsView) -->
    <div
      v-if="filteredCategories.length > 0"
      class="category-tabs flex md:hidden gap-1.5 overflow-x-auto px-2 py-1.5 bg-surface-card border border-surface-border rounded shrink-0 select-none"
    >
      <button
        v-for="catNode in filteredCategories"
        :key="catNode.category"
        type="button"
        class="tab-btn px-2 py-0.5 text-[11px] font-medium rounded border cursor-pointer transition-colors whitespace-nowrap flex items-center gap-1.5"
        :class="activeCategory === catNode.category
          ? 'bg-primary text-white border-primary'
          : 'bg-surface-panel border-surface-border text-vscode-textSecondary hover:text-vscode-textHeading hover:bg-surface-hover'"
        @click="scrollToCategory(catNode.category)"
      >
        <span>{{ catNode.category }}</span>
        <span class="font-mono text-[10px] opacity-80">({{ getCategorySelectedCount(catNode) }}/{{ catNode.rules.length }})</span>
      </button>
    </div>

    <!-- 左右雙欄主佈局 (VS Code 設定風格：左欄大綱導航 + 右欄長頁面規則清單) -->
    <div class="rule-split-container flex-1 min-h-0 flex w-full border border-surface-border rounded bg-surface-card overflow-hidden">
      <!-- 左側大綱導航 (Sticky Outline Sidebar，桌機版 md:flex，獨立捲動) -->
      <aside class="rule-outline-sidebar w-52 lg:w-60 shrink-0 border-r border-surface-border bg-surface-card p-2 hidden md:flex flex-col gap-1 min-h-0 overflow-y-auto">
        <div class="outline-header px-2 py-1 text-[11px] font-semibold uppercase tracking-wider text-vscode-textMuted flex items-center justify-between shrink-0">
          <span class="flex items-center gap-1.5">
            <i class="pi pi-compass text-[11px] text-primary"></i>
            <span>規則大綱 (Outline)</span>
          </span>
          <span class="text-[10px] font-mono text-vscode-textMuted">共 {{ totalRulesCount }} 條</span>
        </div>

        <nav class="outline-nav flex flex-col gap-0.5 mt-1 flex-1">
          <button
            v-for="catNode in filteredCategories"
            :key="catNode.category"
            type="button"
            class="tab-btn outline-item-btn w-full text-left px-2 py-1.5 rounded text-xs font-medium cursor-pointer transition-colors flex items-center justify-between group"
            :class="activeCategory === catNode.category
              ? 'bg-primary/10 text-primary font-semibold border-l-2 border-primary'
              : 'text-vscode-textSecondary hover:text-vscode-textHeading hover:bg-surface-hover border-l-2 border-transparent'"
            @click="scrollToCategory(catNode.category)"
          >
            <span class="truncate">{{ catNode.category }}</span>
            <div class="flex items-center gap-1 shrink-0">
              <span
                v-if="catNode.recommendedCount > 0"
                v-tooltip.top="`${catNode.recommendedCount} 條推薦規則`"
                class="w-1.5 h-1.5 rounded-full bg-primary inline-block shrink-0"
              ></span>
              <Tag
                :value="`${getCategorySelectedCount(catNode)}/${catNode.rules.length}`"
                :severity="isCategoryAllSelected(catNode) ? 'success' : (getCategorySelectedCount(catNode) > 0 ? 'info' : 'secondary')"
                class="!text-[10px] !py-0 !px-1.5 !font-mono"
              />
            </div>
          </button>
        </nav>
      </aside>

      <!-- 右側長頁面規則清單 (Continuous Scroll Panel，獨立捲動卷軸，保留 .rule-tree-container 選擇器) -->
      <main
        ref="rightPaneRef"
        class="rule-content-pane rule-tree-container flex-1 min-w-0 flex flex-col h-full min-h-0 overflow-y-auto bg-surface-ground relative"
      >
        <!-- 右側專屬 Sticky 頂部工具列 (搜尋列、篩選標籤按鈕與批次操作按鈕，按鈕採取 xs size) -->
        <div class="filter-toolbar sticky top-0 z-20 bg-surface-header/95 backdrop-blur-sm border-b border-surface-border px-3 py-1.5 flex flex-wrap items-center justify-between gap-2 shrink-0">
          <!-- 搜尋輸入框 -->
          <div class="search-box flex-1 min-w-[200px] max-w-sm">
            <IconField class="w-full">
              <InputIcon class="pi pi-search search-icon text-vscode-textMuted text-xs" />
              <InputText
                v-model="searchQuery"
                type="text"
                size="small"
                class="search-input w-full !text-xs !py-0.5 !h-6"
                placeholder="搜尋規則代碼、名稱、標籤或領域..."
              />
              <InputIcon
                v-if="searchQuery"
                class="pi pi-times clear-search-icon text-vscode-textMuted hover:text-vscode-textHeading cursor-pointer text-xs"
                @click="searchQuery = ''"
              />
            </IconField>
          </div>

          <!-- 篩選條件與批次操作按鈕組 (xs size) -->
          <div class="filter-buttons flex items-center gap-1 shrink-0 flex-wrap">
            <Button
              :label="`全部規則 (${totalRulesCount})`"
              size="small"
              :severity="filterMode === 'all' ? 'primary' : 'secondary'"
              :variant="filterMode === 'all' ? undefined : 'outlined'"
              class="filter-pill-btn !text-[11px] !px-2 !py-0.5 !h-6"
              @click="filterMode = 'all'"
            />
            <Button
              :label="`僅推薦 (${recommendedCount})`"
              icon="pi pi-star-fill text-vscode-yellow"
              size="small"
              :severity="filterMode === 'recommended' ? 'primary' : 'secondary'"
              :variant="filterMode === 'recommended' ? undefined : 'outlined'"
              class="filter-pill-btn !text-[11px] !px-2 !py-0.5 !h-6"
              @click="filterMode = 'recommended'"
            />
            <Button
              :label="`僅已勾選 (${selectedRuleIds.length})`"
              icon="pi pi-check text-vscode-green"
              size="small"
              :severity="filterMode === 'selected' ? 'primary' : 'secondary'"
              :variant="filterMode === 'selected' ? undefined : 'outlined'"
              class="filter-pill-btn !text-[11px] !px-2 !py-0.5 !h-6"
              @click="filterMode = 'selected'"
            />

            <div class="h-3.5 w-px bg-surface-border mx-0.5"></div>

            <!-- 批次快速選取按鈕 (xs size: !w-6 !h-6，保留既有 sr-only 文字供測試斷言) -->
            <button
              v-tooltip.bottom="isAllRecommendedSelected ? '取消全選推薦規則' : '全選所有推薦規則'"
              type="button"
              class="compact-action-btn inline-flex items-center justify-center !w-6 !h-6 rounded text-xs text-vscode-textSecondary hover:text-vscode-textHeading hover:bg-surface-hover bg-transparent border border-surface-border cursor-pointer transition-colors"
              :title="isAllRecommendedSelected ? '取消全選' : '全選所有推薦'"
              @click="toggleSelectRecommended"
            >
              <i class="pi pi-filter text-[11px]"></i>
              <span class="sr-only">{{ isAllRecommendedSelected ? '取消全選' : '全選所有推薦' }}</span>
            </button>

            <button
              v-tooltip.bottom="isAllRulesSelected ? '清空全部已選規則' : '全選所有啟用規則'"
              type="button"
              class="compact-action-btn inline-flex items-center justify-center !w-6 !h-6 rounded text-xs text-vscode-textSecondary hover:text-vscode-textHeading hover:bg-surface-hover bg-transparent border border-surface-border cursor-pointer transition-colors"
              :title="isAllRulesSelected ? '清空全部' : '全選所有規則'"
              @click="toggleSelectAll"
            >
              <i class="pi pi-check-circle text-[11px]"></i>
              <span class="sr-only">{{ isAllRulesSelected ? '清空全部' : '全選所有規則' }}</span>
            </button>

            <button
              v-tooltip.bottom="isAllExpanded ? '摺疊全部領域目錄' : '展開全部領域目錄'"
              type="button"
              class="compact-action-btn inline-flex items-center justify-center !w-6 !h-6 rounded text-xs text-vscode-textSecondary hover:text-vscode-textHeading hover:bg-surface-hover bg-transparent border border-surface-border cursor-pointer transition-colors"
              :title="isAllExpanded ? '摺疊全部' : '展開全部'"
              @click="toggleExpandAll"
            >
              <i :class="isAllExpanded ? 'pi pi-chevron-up' : 'pi pi-chevron-down'" class="text-[11px]"></i>
              <span class="sr-only">{{ isAllExpanded ? '摺疊全部' : '展開全部' }}</span>
            </button>

            <div class="h-3.5 w-px bg-surface-border mx-0.5"></div>

            <!-- 視圖密度切換按鈕 (xs size: !w-6 !h-6，保留既有 sr-only 文字供測試斷言) -->
            <button
              v-tooltip.bottom="viewDensity === 'compact' ? '目前為緊湊視圖 (點擊切換為詳細視圖)' : '目前為詳細視圖 (點擊切換為緊湊視圖)'"
              type="button"
              class="density-toggle-btn inline-flex items-center justify-center !w-6 !h-6 rounded text-xs text-vscode-textSecondary hover:text-vscode-textHeading hover:bg-surface-hover bg-transparent border border-surface-border cursor-pointer transition-colors"
              :title="viewDensity === 'compact' ? '切換為詳細視圖' : '切換為緊湊視圖'"
              @click="viewDensity = viewDensity === 'compact' ? 'detailed' : 'compact'"
            >
              <i :class="viewDensity === 'compact' ? 'pi pi-list' : 'pi pi-bars'" class="text-[11px]"></i>
              <span class="sr-only">{{ viewDensity === 'compact' ? '緊湊視圖' : '詳細視圖' }}</span>
            </button>
          </div>
        </div>

        <!-- 搜尋與過濾無結果提示 -->
        <div
          v-if="filteredCategories.length === 0"
          class="empty-rules p-10 text-center text-vscode-textMuted text-xs flex flex-col items-center gap-2"
        >
          <i class="pi pi-info-circle text-xl text-vscode-textMuted"></i>
          <span>{{ totalRulesCount === 0 ? '無規則可選' : '無符合條件的規則項目' }}</span>
          <Button
            v-if="searchQuery || filterMode !== 'all'"
            label="重置篩選條件"
            size="small"
            severity="secondary"
            outlined
            class="!text-[11px] !py-0.5 !px-2 !h-6 mt-1"
            @click="searchQuery = ''; filterMode = 'all'"
          />
        </div>

        <!-- 各分類長頁面章節 (Continuous Category Sections，VS Code 設定風格) -->
        <div class="categories-list flex flex-col gap-3 p-3">
          <div
            v-for="catNode in filteredCategories"
            :id="getCategoryAnchorId(catNode.category)"
            :key="catNode.category"
            class="category-node scroll-mt-12 flex flex-col bg-surface-panel border border-surface-border rounded overflow-hidden shadow-xs"
          >
            <!-- 樹狀結構父節點：分類標題 (支援摺疊與類別全選) -->
            <div
              class="category-node-header flex justify-between items-center px-2.5 py-1.5 bg-surface-header border-b border-surface-border cursor-pointer select-none text-vscode-textMain hover:text-vscode-textHeading transition-colors"
              @click="toggleCategory(catNode.category)"
            >
              <div class="node-left flex items-center gap-1.5 text-xs font-medium min-w-0">
                <span class="collapse-icon text-vscode-textMuted text-[10px]">
                  <i :class="isCategoryExpanded(catNode.category) ? 'pi pi-chevron-down' : 'pi pi-chevron-right'"></i>
                </span>
                <span class="category-title text-vscode-textHeading font-semibold truncate">{{ catNode.category }}</span>
                <span class="category-meta-badge text-[11px] text-vscode-textMuted font-normal ml-1 shrink-0">
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
                  class="cat-action-btn !text-[11px] !px-1.5 !py-0.5 !h-6 text-vscode-textSecondary hover:text-vscode-textHeading"
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
      </main>
    </div>

    <!-- 底部確認與統計列 (固定於最底端不隨長頁面滾動消失，主要按鈕維持標準 small) -->
    <div class="tree-footer shrink-0 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 pt-2 pb-1 border-t border-surface-border bg-surface-header px-3 rounded text-xs select-none">
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
          class="confirm-run-btn text-xs !py-1 !px-3 !h-7"
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
 * @description Level 3 DRC 規則選取樹狀面板，支援圖譜特徵自動推薦、VS Code 雙欄大綱導航與長頁面連續滾動 (Zero-Custom-CSS)
 */

import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
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

// 大綱導航選中與滾動活躍項目 (Scrollspy)
const activeCategory = ref<string>('')
const rightPaneRef = ref<HTMLElement | null>(null)
let scrollObserver: IntersectionObserver | null = null

/**
 * 產生規格安全的錨點 DOM ID
 */
const getCategoryAnchorId = (category: string): string => {
  return `rule-cat-${category.replace(/[^a-zA-Z0-9_-]/g, '_')}`
}

/**
 * 取得特定分類已勾選的規則數量
 */
const getCategorySelectedCount = (catNode: CategoryNode): number => {
  return catNode.rules.filter((r) => selectedRuleIds.value.includes(r.id)).length
}

/**
 * 平滑滾動至指定分類區塊（精準對齊分類群組標題，避開頂部釘選工具列）
 */
const scrollToCategory = (category: string) => {
  activeCategory.value = category
  const targetId = getCategoryAnchorId(category)
  const el = document.getElementById(targetId)
  const container = rightPaneRef.value
  if (el && container) {
    const toolbar = container.querySelector('.filter-toolbar') as HTMLElement | null
    const toolbarHeight = toolbar ? toolbar.offsetHeight : 40
    const containerTop = container.getBoundingClientRect().top
    const elTop = el.getBoundingClientRect().top
    const targetScrollTop = container.scrollTop + (elTop - containerTop) - toolbarHeight - 8
    container.scrollTo({
      top: Math.max(0, targetScrollTop),
      behavior: 'smooth',
    })
  } else if (el) {
    el.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
}

/**
 * 建立右側長頁面滾動監聽 (Scrollspy)
 */
const setupScrollspy = () => {
  if (typeof window === 'undefined' || !('IntersectionObserver' in window)) return
  if (scrollObserver) {
    scrollObserver.disconnect()
  }

  const scrollContainer = rightPaneRef.value || (document.querySelector('.rule-content-pane') as HTMLElement | null)

  scrollObserver = new IntersectionObserver(
    (entries) => {
      // 滾動容器接近最頂端時直接高亮第一項
      if (scrollContainer && scrollContainer.scrollTop < 30 && filteredCategories.value.length > 0) {
        activeCategory.value = filteredCategories.value[0].category
        return
      }
      const visible = entries.filter((e) => e.isIntersecting)
      if (visible.length > 0) {
        const topEntry = visible.reduce((prev, curr) =>
          prev.boundingClientRect.top < curr.boundingClientRect.top ? prev : curr
        )
        const matched = filteredCategories.value.find(
          (c) => getCategoryAnchorId(c.category) === topEntry.target.id
        )
        if (matched) {
          activeCategory.value = matched.category
        }
      }
    },
    {
      root: scrollContainer,
      rootMargin: '-30px 0px -60% 0px',
      threshold: 0,
    }
  )

  filteredCategories.value.forEach((cat) => {
    const el = document.getElementById(getCategoryAnchorId(cat.category))
    if (el) {
      scrollObserver?.observe(el)
    }
  })
}

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

watch(
  filteredCategories,
  async (cats) => {
    if (cats.length > 0) {
      if (!activeCategory.value || !cats.some((c) => c.category === activeCategory.value)) {
        activeCategory.value = cats[0].category
      }
    }
    await nextTick()
    setupScrollspy()
  },
  { immediate: true }
)

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

const confirmAndRun = () => {
  emit('run', {
    ruleIds: selectedRuleIds.value,
    selectedConfigs: props.summary.is_multi_config ? selectedConfigs.value : undefined,
  })
}

onMounted(() => {
  loadAllRules()
})

onUnmounted(() => {
  if (scrollObserver) {
    scrollObserver.disconnect()
    scrollObserver = null
  }
})
</script>
