<template>
  <div class="rule-directory-tree flex flex-col flex-1 text-vscode-textMain">
    <!-- 統一篩選與控制工具列 (1px Grid Border 緊湊單列) -->
    <div class="tree-toolbar bg-surface-card border-b border-surface-border px-4 py-2 flex flex-wrap items-center justify-between gap-2">
      <div class="flex flex-wrap items-center gap-2 flex-1">
        <!-- 關鍵字搜尋 (PrimeVue IconField + InputText) -->
        <IconField class="relative flex-1 min-w-[200px] max-w-sm">
          <InputIcon class="pi pi-search text-vscode-textMuted text-xs" />
          <InputText
            v-model="filterText"
            type="text"
            size="small"
            placeholder="搜尋規則名稱、說明、標籤或目錄路徑..."
            class="filter-search-input w-full py-1 text-xs bg-surface-ground border-surface-border text-vscode-textHeading placeholder:text-vscode-textMuted"
          />
          <button
            v-if="filterText"
            type="button"
            class="absolute right-2 top-1/2 -translate-y-1/2 text-vscode-textMuted hover:text-vscode-textHeading cursor-pointer p-0.5 bg-transparent border-0"
            @click="filterText = ''"
          >
            <i class="pi pi-times text-[10px]"></i>
          </button>
        </IconField>

        <!-- 規則層級過濾 (Level Filter: Level 3 -> Level 2 -> Level 1 -> PartDB) -->
        <select
          v-model="selectedLevel"
          class="filter-level-select px-2 py-1 h-7 bg-surface-ground border border-surface-border rounded text-vscode-textHeading text-xs focus:outline-none focus:border-primary"
        >
          <option value="">全部層級 (All Levels)</option>
          <option value="level3">Level 3: DRC 驗證規範 ({{ level3Rules.length }})</option>
          <option value="level2">Level 2: 網路拓撲與匯流排 ({{ level2Rules.length }})</option>
          <option value="level1">Level 1: 元件辨識規範 ({{ level1Rules.length }})</option>
          <option value="partdb">PartDB: 零件規格庫 ({{ (partdbParts || []).length }})</option>
        </select>

        <!-- 嚴重等級過濾 (Severity Filter) -->
        <select
          v-model="selectedSeverity"
          class="filter-severity-select px-2 py-1 h-7 bg-surface-ground border border-surface-border rounded text-vscode-textHeading text-xs focus:outline-none focus:border-primary"
        >
          <option value="">全部嚴重等級 (All Severities)</option>
          <option value="Fatal">Fatal (致命異常)</option>
          <option value="Error">Error (嚴重違規)</option>
          <option value="Warning">Warning (潛在警告)</option>
          <option value="Info">Info (提示資訊)</option>
        </select>

        <!-- 狀態過濾 (Status Filter) -->
        <select
          v-model="selectedStatus"
          class="filter-status-select px-2 py-1 h-7 bg-surface-ground border border-surface-border rounded text-vscode-textHeading text-xs focus:outline-none focus:border-primary"
        >
          <option value="">全部狀態 (All Statuses)</option>
          <option value="enabled">僅顯示已啟用 (Enabled)</option>
          <option value="disabled">僅顯示已停用 (Disabled)</option>
        </select>

        <!-- 標籤過濾 (Tag Filter) -->
        <select
          v-if="allTags.length > 0"
          v-model="selectedTag"
          class="filter-tag-select px-2 py-1 h-7 bg-surface-ground border border-surface-border rounded text-vscode-textHeading text-xs focus:outline-none focus:border-primary"
        >
          <option value="">全部標籤 (All Tags)</option>
          <option v-for="t in allTags" :key="t" :value="t">{{ t }}</option>
        </select>
      </div>

      <!-- 工具列右側：展開/收合圖示按鈕 + 統計資訊 -->
      <div class="flex items-center gap-2 text-xs text-vscode-textMuted shrink-0">
        <Button
          v-tooltip.top="isAllExpanded ? '全部收合目錄' : '全部展開目錄'"
          :icon="isAllExpanded ? 'pi pi-chevron-up' : 'pi pi-chevron-down'"
          text
          size="small"
          severity="secondary"
          class="!w-6 !h-6 !p-0 text-vscode-textSecondary hover:text-vscode-textHeading"
          @click="toggleExpandAll"
        >
          <i :class="isAllExpanded ? 'pi pi-chevron-up' : 'pi pi-chevron-down'" class="text-xs"></i>
          <span class="sr-only">{{ isAllExpanded ? '全部收合' : '全部展開' }}</span>
        </Button>

        <button
          v-if="hasActiveFilters"
          type="button"
          v-tooltip.top="'重設所有篩選條件'"
          class="text-xs text-primary hover:underline cursor-pointer bg-transparent border-0"
          @click="clearFilters"
        >
          重設篩選
        </button>

        <span class="font-mono text-[11px] pl-1 border-l border-surface-border">
          顯示 <strong class="text-vscode-textHeading font-semibold">{{ filteredRuleCount }}</strong> / {{ totalRulesCount }} 條規則
        </span>
      </div>
    </div>

    <!-- TreeTable 樹狀結構表格主檢視區 (無多餘圓角卡片外框，全寬貼齊) -->
    <div class="treetable-container bg-surface-panel border-b border-surface-border overflow-x-auto flex-1">
      <TreeTable
        v-model:expanded-keys="expandedKeys"
        :value="filteredTreeNodes"
        size="small"
        class="w-full text-xs [&_td]:!py-1 [&_td]:!px-3 [&_th]:!py-1.5 [&_th]:!px-3 [&_.p-treetable-toggler]:!w-4 [&_.p-treetable-toggler]:!h-4 [&_.p-treetable-toggler]:!mr-1 [&_.p-treetable-tbody>tr:hover]:!bg-surface-hover [&_.p-treetable-tbody>tr:hover>td]:!bg-surface-hover [&_.p-treetable-tbody>tr]:transition-colors"
        table-style="min-width: 45rem"
      >
        <!-- 欄位 1: 目錄與規則名稱 -->
        <Column
          field="name"
          header="目錄 / 規則項目"
          expander
          header-class="whitespace-nowrap"
          class="whitespace-nowrap"
          style="width: 24rem; min-width: 22rem; max-width: 26rem"
        >
          <template #body="{ node }">
            <!-- 資料夾節點 -->
            <div v-if="node.data.type === 'folder'" class="folder-row flex items-center gap-1.5 py-0.5 select-none leading-tight">
              <i :class="node.expanded ? 'pi pi-folder-open text-primary' : 'pi pi-folder text-primary'" class="text-xs"></i>
              <span class="font-semibold text-vscode-textHeading tracking-wide">{{ node.data.name }}</span>
              <span v-if="node.data.ruleCount" class="text-[11px] text-vscode-textMuted font-normal ml-0.5 font-mono">
                ({{ node.data.ruleCount }} 條)
              </span>
            </div>

            <!-- PartDB 項目節點：無 ToggleSwitch，僅提供 Viewer，展示廠商 (Mfg) 與廠商料號 (Mfg PN) -->
            <div
              v-else-if="node.data.type === 'partdb'"
              class="partdb-row flex items-center gap-1.5 py-0.5 leading-tight flex-wrap sm:flex-nowrap"
            >
              <i class="pi pi-database text-vscode-textMuted text-xs shrink-0 ml-0.5"></i>
              <Tag
                v-if="node.data.mfg"
                :value="node.data.mfg"
                severity="secondary"
                class="partdb-mfg-tag text-[10px] px-1.5 py-0 font-mono tracking-wider font-semibold bg-surface-card border border-surface-border text-vscode-textSecondary shrink-0"
              />
              <span
                class="partdb-pn font-mono text-vscode-textHeading text-xs font-semibold truncate cursor-pointer hover:text-primary hover:underline"
                :title="node.data.description ? `${node.data.mfg ? node.data.mfg + ' ' : ''}${node.data.mfg_pn || node.data.name} - ${node.data.description}` : (node.data.mfg_pn || node.data.name)"
                @click="viewRuleYaml(node.data)"
              >
                {{ node.data.mfg_pn || node.data.name }}
              </span>
            </div>

            <!-- 規則節點：ToggleSwitch 放在開頭 -->
            <div
              v-else
              class="rule-row flex items-center gap-1.5 py-0.5 leading-tight"
              :class="{ 'opacity-60': node.data.enabled === false }"
            >
              <!-- 1. 開頭的 ToggleSwitch 開關 (緊湊小尺寸) -->
              <div class="rule-switch-wrapper shrink-0 flex items-center -my-0.5" @click.stop>
                <ToggleSwitch
                  :model-value="node.data.enabled !== false"
                  :disabled="updatingRule === node.data.name"
                  class="scale-[0.65] origin-left"
                  @update:model-value="handleToggleSwitch(node.data, $event)"
                />
              </div>

              <!-- 2. 圖示與規則名稱 (點擊開啟 YAML Viewer) -->
              <i class="pi pi-file-code text-primary text-xs shrink-0"></i>
              <span
                class="font-mono text-vscode-textHeading text-xs truncate cursor-pointer hover:text-primary hover:underline"
                :title="node.data.description ? `${node.data.name} - ${node.data.description}` : node.data.name"
                @click="viewRuleYaml(node.data)"
              >
                {{ node.data.name }}
              </span>
            </div>
          </template>
        </Column>

        <!-- 欄位 2: 層級 (Level - Level 3/2/1 各自採用專屬語義色區分) -->
        <Column
          field="level"
          header="規則層級"
          header-class="whitespace-nowrap text-center"
          class="whitespace-nowrap text-center"
          style="width: 5.5rem; min-width: 5.5rem"
        >
          <template #body="{ node }">
            <span
              v-if="node.data.level"
              class="level-badge text-[10px] px-1.5 py-0.5 rounded font-mono uppercase inline-block whitespace-nowrap"
              :class="getLevelBadgeClass(node.data.level)"
            >
              {{ formatLevelLabel(node.data.level) }}
            </span>
          </template>
        </Column>

        <!-- 欄位 3: 嚴重等級 / 優先級 (Level 3 共用 Severity，Level 1/2 共用 Priority) -->
        <Column
          field="severity"
          header="嚴重等級 / 優先級"
          header-class="whitespace-nowrap text-center"
          class="whitespace-nowrap text-center"
          style="width: 7.5rem; min-width: 7rem"
        >
          <template #body="{ node }">
            <!-- Level 3: 嚴重等級標籤 (Fatal / Error / Warning / Info) -->
            <span
              v-if="node.data.severity"
              class="severity-badge text-[10px] px-1.5 py-0.5 rounded font-mono uppercase inline-block whitespace-nowrap"
              :class="{
                'bg-red-500/15 text-red-600 dark:text-red-400 border border-red-500/30 font-medium': node.data.severity === 'Fatal' || node.data.severity === 'Error',
                'bg-amber-500/15 text-amber-600 dark:text-amber-400 border border-amber-500/30 font-medium': node.data.severity === 'Warning',
                'bg-surface-hover text-vscode-textSecondary border border-surface-border': node.data.severity === 'Info'
              }"
            >
              {{ node.data.severity }}
            </span>
            <!-- Level 1 / Level 2: 規則優先級數值 (純文字顯示，無 Tag 外框) -->
            <span
              v-else-if="node.data.priority !== undefined && node.data.priority !== null"
              class="priority-text text-xs font-mono text-vscode-textSecondary font-medium select-all"
              :title="`優先級: ${node.data.priority}`"
            >
              {{ node.data.priority }}
            </span>
            <span v-else-if="node.data.type === 'rule' || node.data.type === 'partdb'" class="text-vscode-textMuted text-xs font-mono">-</span>
          </template>
        </Column>

        <!-- 欄位 4: 說明與領域標籤 -->
        <Column field="description" header="說明與領域標籤" class="w-full">
          <template #body="{ node }">
            <div v-if="node.data.type === 'rule' || node.data.type === 'partdb'" class="flex items-center gap-2 w-full py-0.5">
              <span class="text-xs text-vscode-textMain leading-normal break-words" :title="node.data.description">
                {{ node.data.description || '無描述' }}
              </span>
            </div>
          </template>
        </Column>
      </TreeTable>
    </div>

    <!-- 側邊抽屜式 YAML 唯讀檢視器 (Drawer) -->
    <Drawer
      v-model:visible="showDrawer"
      position="right"
      class="!w-[650px] !max-w-[90vw] !bg-surface-panel !border-l !border-surface-border !text-vscode-textHeading"
      :header="selectedRuleData?.name || '規則 YAML 原始碼'"
    >
      <div v-if="selectedRuleData" class="flex flex-col gap-3 h-full pb-4">
        <!-- 中繼資訊條 -->
        <div class="flex flex-wrap gap-2 items-center px-3 py-2 rounded bg-surface-card border border-surface-border text-xs">
          <div class="flex items-center gap-1">
            <span class="text-vscode-textMuted">層級:</span>
            <span
              class="level-badge text-[10px] px-1.5 py-0.5 rounded font-mono uppercase inline-block whitespace-nowrap"
              :class="getLevelBadgeClass(selectedRuleData.level)"
            >
              {{ formatLevelLabel(selectedRuleData.level) }}
            </span>
          </div>
          <div class="w-px h-3 bg-surface-border"></div>
          <div class="flex items-center gap-1">
            <span class="text-vscode-textMuted">目錄:</span>
            <code class="text-primary font-mono">{{ selectedRuleData.category_path }}</code>
          </div>
          <template v-if="selectedRuleData.level === 'partdb'">
            <div v-if="selectedRuleData.mfg" class="w-px h-3 bg-surface-border"></div>
            <div v-if="selectedRuleData.mfg" class="flex items-center gap-1">
              <span class="text-vscode-textMuted">廠商:</span>
              <strong class="text-vscode-textHeading font-mono">{{ selectedRuleData.mfg }}</strong>
            </div>
            <div v-if="selectedRuleData.mfg_pn || selectedRuleData.name" class="w-px h-3 bg-surface-border"></div>
            <div v-if="selectedRuleData.mfg_pn || selectedRuleData.name" class="flex items-center gap-1">
              <span class="text-vscode-textMuted">廠商料號:</span>
              <strong class="text-primary font-mono">{{ selectedRuleData.mfg_pn || selectedRuleData.name }}</strong>
            </div>
          </template>
          <template v-else>
            <div v-if="selectedRuleData.severity" class="w-px h-3 bg-surface-border"></div>
            <div v-if="selectedRuleData.severity" class="flex items-center gap-1">
              <span class="text-vscode-textMuted">嚴重等級:</span>
              <span
                class="text-[10px] px-1.5 py-0.5 rounded font-mono uppercase inline-block whitespace-nowrap"
                :class="{
                  'bg-red-500/15 text-red-600 dark:text-red-400 border border-red-500/30 font-medium': selectedRuleData.severity === 'Fatal' || selectedRuleData.severity === 'Error',
                  'bg-amber-500/15 text-amber-600 dark:text-amber-400 border border-amber-500/30 font-medium': selectedRuleData.severity === 'Warning',
                  'bg-surface-hover text-vscode-textSecondary border border-surface-border': selectedRuleData.severity === 'Info'
                }"
              >
                {{ selectedRuleData.severity }}
              </span>
            </div>
            <div v-if="selectedRuleData.priority !== undefined && selectedRuleData.priority !== null" class="w-px h-3 bg-surface-border"></div>
            <div v-if="selectedRuleData.priority !== undefined && selectedRuleData.priority !== null" class="flex items-center gap-1">
              <span class="text-vscode-textMuted">優先級:</span>
              <span class="priority-text font-mono text-xs text-vscode-textHeading font-medium">
                {{ selectedRuleData.priority }}
              </span>
            </div>
            <div class="w-px h-3 bg-surface-border"></div>
            <div class="flex items-center gap-1">
              <span class="text-vscode-textMuted">狀態:</span>
              <Tag
                :value="selectedRuleData.enabled !== false ? '已啟用' : '已停用'"
                :severity="selectedRuleData.enabled !== false ? 'success' : 'secondary'"
                class="text-[10px]"
              />
            </div>
          </template>
        </div>

        <div v-if="selectedRuleData.description" class="text-xs text-vscode-textMain leading-relaxed px-3 py-2 rounded bg-surface-card border border-surface-border">
          {{ selectedRuleData.description }}
        </div>

        <!-- 複製與原始 YAML -->
        <div class="flex justify-between items-center mt-0.5">
          <span class="text-xs text-vscode-textMuted font-mono flex items-center gap-1">
            <i class="pi pi-file text-xs"></i>
            {{ selectedRuleData.filename }}
          </span>
          <button
            type="button"
            v-tooltip.left="isCopied ? '已複製!' : '複製 YAML 原始碼'"
            class="bg-surface-card hover:bg-surface-hover border border-surface-border text-vscode-textSecondary hover:text-vscode-textHeading px-2 py-1 rounded text-xs flex items-center gap-1 transition-colors cursor-pointer"
            @click="copyDrawerYaml"
          >
            <i :class="isCopied ? 'pi pi-check text-emerald-500' : 'pi pi-copy'" class="text-xs"></i>
            <span>{{ isCopied ? '已複製!' : '複製 YAML' }}</span>
          </button>
        </div>

        <div class="flex-1 overflow-y-auto rounded border border-surface-border bg-surface-ground p-3">
          <pre class="m-0 font-mono text-xs text-vscode-textMain leading-relaxed whitespace-pre-wrap break-all"><code>{{ selectedRuleData.rawYaml }}</code></pre>
        </div>
      </div>
    </Drawer>
  </div>
</template>

<script setup lang="ts">
/**
 * @file RuleDirectoryTree.vue
 * @description 統一規則目錄結構樹檢視組件 (2026 雙主題 2色低飽和版)
 */

import { ref, computed, watch } from 'vue'
import TreeTable from 'primevue/treetable'
import Column from 'primevue/column'
import ToggleSwitch from 'primevue/toggleswitch'
import Drawer from 'primevue/drawer'
import Tag from 'primevue/tag'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import { copyToClipboard } from '@/utils/clipboard'
import type { TreeNode } from 'primevue/treenode'
import type { Level1PatternItem, Level2PatternItem, Level3RuleItem, PartDBItem } from '@/types/pattern'

const props = withDefaults(
  defineProps<{
    level1Rules: Level1PatternItem[]
    level2Rules: Level2PatternItem[]
    level3Rules: Level3RuleItem[]
    partdbParts?: PartDBItem[]
    allTags?: string[]
    selectedLevel?: string
  }>(),
  {
    partdbParts: () => [],
    allTags: () => [],
    selectedLevel: '',
  }
)

const emit = defineEmits<{
  (e: 'toggle-rule', payload: { ruleName: string; enabled: boolean }): void
  (e: 'update:selectedLevel', level: string): void
}>()

// 篩選狀態 (支援與外部 filter 按鈕雙向連動)
const filterText = ref<string>('')
const internalSelectedLevel = ref<string>(props.selectedLevel || '')

watch(
  () => props.selectedLevel,
  (newVal) => {
    if (newVal !== undefined && newVal !== internalSelectedLevel.value) {
      internalSelectedLevel.value = newVal
    }
  }
)

const selectedLevel = computed({
  get: () => (props.selectedLevel !== undefined ? props.selectedLevel : internalSelectedLevel.value),
  set: (val: string) => {
    internalSelectedLevel.value = val
    emit('update:selectedLevel', val)
  },
})

const selectedSeverity = ref<string>('')
const selectedStatus = ref<string>('')
const selectedTag = ref<string>('')

const isAllExpanded = ref<boolean>(true)
const expandedKeys = ref<Record<string, boolean>>({})
const updatingRule = ref<string | null>(null)

// 側邊 Drawer 狀態
const showDrawer = ref<boolean>(false)
const selectedRuleData = ref<any>(null)
const isCopied = ref<boolean>(false)

const hasActiveFilters = computed(() => {
  return (
    !!filterText.value ||
    !!selectedLevel.value ||
    !!selectedSeverity.value ||
    !!selectedStatus.value ||
    !!selectedTag.value
  )
})

const clearFilters = () => {
  filterText.value = ''
  selectedLevel.value = ''
  selectedSeverity.value = ''
  selectedStatus.value = ''
  selectedTag.value = ''
}

const formatLevelLabel = (level: string) => {
  switch (level) {
    case 'level1': return 'Level 1'
    case 'level2': return 'Level 2'
    case 'level3': return 'Level 3'
    case 'partdb': return 'PartDB'
    default: return level
  }
}

/**
 * 依規則層級取得對應之低飽和語義色標籤樣式 (Level 3 / Level 2 / Level 1 分色區隔)
 * - Level 3 (DRC 檢驗規範): Primary 藍色
 * - Level 2 (網路拓撲與匯流排): Teal 藍綠色
 * - Level 1 (元件識別規範): Purple 紫色
 * - PartDB (零件規格庫): Neutral 中性灰
 *
 * @param {string} level 規則層級代碼 ('level1' | 'level2' | 'level3' | 'partdb')
 * @returns {string} Tailwind CSS 類別字串
 */
const getLevelBadgeClass = (level: string): string => {
  switch (level) {
    case 'level3':
      return 'bg-primary-500/15 text-primary-700 dark:text-primary-300 border border-primary-500/30 font-medium'
    case 'level2':
      return 'bg-teal-500/15 text-teal-700 dark:text-teal-300 border border-teal-500/30 font-medium'
    case 'level1':
      return 'bg-purple-500/15 text-purple-700 dark:text-purple-300 border border-purple-500/30 font-medium'
    case 'partdb':
    default:
      return 'bg-surface-hover text-vscode-textSecondary border border-surface-border'
  }
}

const viewRuleYaml = (data: any) => {
  if (!data) return
  selectedRuleData.value = data
  showDrawer.value = true
}

const copyDrawerYaml = async () => {
  if (!selectedRuleData.value?.rawYaml) return
  const ok = await copyToClipboard(selectedRuleData.value.rawYaml)
  if (ok) {
    isCopied.value = true
    setTimeout(() => {
      isCopied.value = false
    }, 2000)
  }
}

const handleToggleSwitch = (ruleData: any, newVal: boolean) => {
  if (!ruleData || !ruleData.name) return
  updatingRule.value = ruleData.name
  emit('toggle-rule', {
    ruleName: ruleData.name,
    enabled: newVal,
  })
  ruleData.enabled = newVal
  setTimeout(() => {
    updatingRule.value = null
  }, 400)
}

// 計算規則總數 (含 PartDB)
const totalRulesCount = computed(() => {
  return (
    props.level1Rules.length +
    props.level2Rules.length +
    props.level3Rules.length +
    (props.partdbParts?.length || 0)
  )
})

// 建立完整目錄結構樹 (排序順序: Level 3 -> Level 2 -> Level 1 -> PartDB)
const fullTreeNodes = computed<TreeNode[]>(() => {
  // 1. patterns/rules/... (Level 3)
  const l3DomainMap: Record<string, TreeNode[]> = {}
  props.level3Rules.forEach((r) => {
    const domain = r._domain || 'root'
    if (!l3DomainMap[domain]) l3DomainMap[domain] = []
    l3DomainMap[domain].push({
      key: `l3_${r.name}`,
      data: {
        type: 'rule',
        name: r.name,
        level: 'level3',
        category_path: `patterns/rules/${domain}`,
        filename: r._filename || `${r.name}.yaml`,
        description: r.description || '',
        severity: r.severity || 'Error',
        priority: (r as any).priority,
        tags: r.tags || [],
        enabled: r.enabled !== false,
        rawYaml: r._raw_yaml || '',
      },
    })
  })

  const l3SubFolders: TreeNode[] = Object.keys(l3DomainMap).map((d) => ({
    key: `folder_l3_${d}`,
    data: {
      type: 'folder',
      name: d,
      ruleCount: l3DomainMap[d].length,
    },
    children: l3DomainMap[d],
  }))

  const l3Folder: TreeNode = {
    key: 'folder_rules',
    data: {
      type: 'folder',
      name: 'rules (Level 3 DRC 設計規則)',
      ruleCount: props.level3Rules.length,
    },
    children: l3SubFolders,
  }

  // 2. Level 2 (buses, power, signals)
  const l2DomainMap: Record<string, TreeNode[]> = {
    buses: [],
    power: [],
    signals: [],
  }

  props.level2Rules.forEach((r) => {
    const domain = r._domain || 'buses'
    if (!l2DomainMap[domain]) l2DomainMap[domain] = []
    l2DomainMap[domain].push({
      key: `l2_${r.name}`,
      data: {
        type: 'rule',
        name: r.name,
        level: 'level2',
        category_path: `patterns/${domain}`,
        filename: r._filename || `${r.name}.yaml`,
        description: r.category || '',
        severity: '',
        priority: r.priority,
        enabled: r.enabled !== false,
        rawYaml: r._raw_yaml || '',
      },
    })
  })

  const l2Folders: TreeNode[] = Object.keys(l2DomainMap).map((d) => ({
    key: `folder_l2_${d}`,
    data: {
      type: 'folder',
      name: `${d} (Level 2 網路拓撲)`,
      ruleCount: l2DomainMap[d].length,
    },
    children: l2DomainMap[d],
  }))

  // 3. patterns/components (Level 1)
  const l1Children: TreeNode[] = props.level1Rules.map((r) => ({
    key: `l1_${r.name}`,
    data: {
      type: 'rule',
      name: r.name,
      level: 'level1',
      category_path: 'patterns/components',
      filename: r._filename || 'component_rule.yaml',
      description: r.description || '',
      severity: '',
      priority: r.priority,
      enabled: r.enabled !== false,
      rawYaml: r._raw_yaml || '',
    },
  }))

  const l1Folder: TreeNode = {
    key: 'folder_components',
    data: {
      type: 'folder',
      name: 'components (Level 1 元件分類)',
      ruleCount: l1Children.length,
    },
    children: l1Children,
  }

  // 4. patterns/partdb/data/... (PartDB 零件特規庫)
  const partdbParts = props.partdbParts || []
  const partdbDomainMap: Record<string, TreeNode[]> = {}

  partdbParts.forEach((p) => {
    const domain = p._domain || 'root'
    const mfg = p.mfg || (p._filename && p._filename.includes('_') ? p._filename.split('_')[0] : '')
    const mfgPn = p.mfg_pn || p.pn || ''
    if (!partdbDomainMap[domain]) partdbDomainMap[domain] = []
    partdbDomainMap[domain].push({
      key: `partdb_${p.pn}`,
      data: {
        type: 'partdb',
        name: p.pn,
        mfg: mfg,
        mfg_pn: mfgPn,
        level: 'partdb',
        category_path: p._rel_path || `patterns/partdb/data/${domain}`,
        filename: p._filename || `${p.pn}.yaml`,
        description: p.description || '',
        severity: '',
        enabled: undefined,
        rawYaml: p._raw_yaml || '',
      },
    })
  })

  const partdbSubFolders: TreeNode[] = Object.keys(partdbDomainMap).map((d) => ({
    key: `folder_partdb_${d}`,
    data: {
      type: 'folder',
      name: d,
      ruleCount: partdbDomainMap[d].length,
    },
    children: partdbDomainMap[d],
  }))

  const partdbFolder: TreeNode = {
    key: 'folder_partdb',
    data: {
      type: 'folder',
      name: 'partdb (PartDB 零件規格庫)',
      ruleCount: partdbParts.length,
    },
    children: partdbSubFolders,
  }

  return [
    {
      key: 'root_patterns',
      data: {
        type: 'folder',
        name: 'patterns/ (規則庫根目錄)',
        ruleCount: totalRulesCount.value,
      },
      children: [
        l3Folder,
        ...l2Folders,
        l1Folder,
        partdbFolder,
      ],
    },
  ]
})

// 初始化展開所有目錄
const initExpandedKeys = (nodes: TreeNode[]) => {
  const map: Record<string, boolean> = {}
  const traverse = (list: TreeNode[]) => {
    for (const item of list) {
      if (item.data?.type === 'folder' && item.key) {
        map[item.key] = true
        if (item.children) traverse(item.children)
      }
    }
  }
  traverse(nodes)
  expandedKeys.value = map
}

watch(
  fullTreeNodes,
  (nodes) => {
    if (nodes && isAllExpanded.value) {
      initExpandedKeys(nodes)
    }
  },
  { immediate: true }
)

const toggleExpandAll = () => {
  isAllExpanded.value = !isAllExpanded.value
  if (isAllExpanded.value) {
    initExpandedKeys(fullTreeNodes.value)
  } else {
    expandedKeys.value = {}
  }
}

// 遞迴過濾節點
const filterNode = (node: TreeNode): TreeNode | null => {
  if (node.data?.type === 'rule' || node.data?.type === 'partdb') {
    const data = node.data

    if (filterText.value.trim()) {
      const q = filterText.value.trim().toLowerCase()
      const matchName = (data.name || '').toLowerCase().includes(q)
      const matchMfg = (data.mfg || '').toLowerCase().includes(q)
      const matchMfgPn = (data.mfg_pn || '').toLowerCase().includes(q)
      const matchDesc = (data.description || '').toLowerCase().includes(q)
      const matchPath = (data.category_path || '').toLowerCase().includes(q)
      const matchTag = (data.tags || []).some((t: string) => t.toLowerCase().includes(q))
      const matchSeverity = (data.severity || '').toLowerCase().includes(q)
      const matchPriority = data.priority !== undefined && data.priority !== null && String(data.priority).includes(q)
      if (!matchName && !matchMfg && !matchMfgPn && !matchDesc && !matchPath && !matchTag && !matchSeverity && !matchPriority) return null
    }

    if (selectedLevel.value && data.level !== selectedLevel.value) {
      return null
    }

    if (selectedSeverity.value && data.severity !== selectedSeverity.value) {
      return null
    }

    if (selectedStatus.value === 'enabled' && (data.type === 'partdb' || data.enabled === false)) {
      return null
    }
    if (selectedStatus.value === 'disabled' && (data.type === 'partdb' || data.enabled !== false)) {
      return null
    }

    if (selectedTag.value && !(data.tags || []).includes(selectedTag.value)) {
      return null
    }

    return { ...node }
  }

  if (node.children) {
    const validChildren: TreeNode[] = []
    for (const child of node.children) {
      const filteredChild = filterNode(child)
      if (filteredChild) validChildren.push(filteredChild)
    }
    if (validChildren.length > 0) {
      return {
        ...node,
        children: validChildren,
        data: {
          ...node.data,
          ruleCount: validChildren.reduce((acc, c) => acc + (c.data?.type === 'rule' || c.data?.type === 'partdb' ? 1 : (c.data?.ruleCount || 0)), 0),
        },
      }
    }
  }

  return null
}

const filteredTreeNodes = computed<TreeNode[]>(() => {
  const result: TreeNode[] = []
  for (const root of fullTreeNodes.value) {
    const matched = filterNode(root)
    if (matched) result.push(matched)
  }
  return result
})

const filteredRuleCount = computed(() => {
  let count = 0
  const countRules = (nodes: TreeNode[]) => {
    for (const n of nodes) {
      if (n.data?.type === 'rule' || n.data?.type === 'partdb') {
        count++
      } else if (n.children) {
        countRules(n.children)
      }
    }
  }
  countRules(filteredTreeNodes.value)
  return count
})

defineExpose({
  selectedLevel,
  filterText,
  clearFilters,
})
</script>
