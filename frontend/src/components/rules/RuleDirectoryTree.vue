<template>
  <div class="rule-directory-tree flex flex-col gap-4">
    <!-- 統一篩選與控制工具列 (Filter Controls - VSCode 緊湊風格) -->
    <div class="tree-toolbar bg-[#252526] border border-[#333333] rounded-lg p-2.5 flex flex-col gap-2 shadow-sm">
      <div class="flex flex-wrap items-center justify-between gap-2">
        <!-- 關鍵字搜尋 -->
        <div class="relative flex-1 min-w-[220px]">
          <i class="pi pi-search absolute left-2.5 top-1/2 -translate-y-1/2 text-[#858585] text-xs"></i>
          <input
            v-model="filterText"
            type="text"
            placeholder="搜尋規則名稱、說明、標籤或目錄路徑..."
            class="filter-search-input w-full pl-7 pr-6 py-1 h-7 bg-[#1e1e1e] border border-[#333333] rounded text-white text-xs focus:outline-none focus:border-[#007acc]"
          />
          <button
            v-if="filterText"
            type="button"
            class="absolute right-1.5 top-1/2 -translate-y-1/2 text-[#858585] hover:text-white cursor-pointer p-0.5"
            @click="filterText = ''"
          >
            <i class="pi pi-times text-[10px]"></i>
          </button>
        </div>

        <!-- 規則層級過濾 (Level Filter: Level 3 -> Level 2 -> Level 1 -> PartDB) -->
        <select
          v-model="selectedLevel"
          class="filter-level-select px-2 py-1 h-7 bg-[#1e1e1e] border border-[#333333] rounded text-white text-xs focus:outline-none focus:border-[#007acc]"
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
          class="filter-severity-select px-2 py-1 h-7 bg-[#1e1e1e] border border-[#333333] rounded text-white text-xs focus:outline-none focus:border-[#007acc]"
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
          class="filter-status-select px-2 py-1 h-7 bg-[#1e1e1e] border border-[#333333] rounded text-white text-xs focus:outline-none focus:border-[#007acc]"
        >
          <option value="">全部狀態 (All Statuses)</option>
          <option value="enabled">僅顯示已啟用 (Enabled)</option>
          <option value="disabled">僅顯示已停用 (Disabled)</option>
        </select>

        <!-- 標籤過濾 (Tag Filter) -->
        <select
          v-if="allTags.length > 0"
          v-model="selectedTag"
          class="filter-tag-select px-2 py-1 h-7 bg-[#1e1e1e] border border-[#333333] rounded text-white text-xs focus:outline-none focus:border-[#007acc]"
        >
          <option value="">全部標籤 (All Tags)</option>
          <option v-for="t in allTags" :key="t" :value="t">{{ t }}</option>
        </select>
      </div>

      <!-- 工具列底層：展開/收合 + 統計資訊 -->
      <div class="flex items-center justify-between text-xs text-[#858585] pt-1 border-t border-[#333333]/50">
        <div class="flex items-center gap-2">
          <Button
            :label="isAllExpanded ? '全部收合' : '全部展開'"
            :icon="isAllExpanded ? 'pi pi-chevron-up' : 'pi pi-chevron-down'"
            text
            size="small"
            severity="secondary"
            class="text-xs text-[#cccccc] p-0"
            @click="toggleExpandAll"
          />
          <button
            v-if="hasActiveFilters"
            type="button"
            class="text-xs text-sky-400 hover:text-sky-300 cursor-pointer bg-transparent border-0 underline ml-2"
            @click="clearFilters"
          >
            重設篩選
          </button>
        </div>

        <div class="flex items-center gap-2">
          <span>
            顯示 <strong>{{ filteredRuleCount }}</strong> / {{ totalRulesCount }} 條規則
          </span>
        </div>
      </div>
    </div>

    <!-- TreeTable 樹狀結構表格主檢視區 (VSCode 緊湊佈局) -->
    <div class="treetable-container bg-[#252526] border border-[#333333] rounded-lg overflow-hidden shadow-sm">
      <TreeTable
        v-model:expanded-keys="expandedKeys"
        :value="filteredTreeNodes"
        size="small"
        class="w-full text-xs [&_td]:!py-1 [&_td]:!px-2.5 [&_th]:!py-1.5 [&_th]:!px-2.5 [&_.p-treetable-toggler]:!w-4 [&_.p-treetable-toggler]:!h-4 [&_.p-treetable-toggler]:!mr-1 [&_.p-treetable-tbody>tr]:hover:!bg-[#2a2d2e]"
        table-style="min-width: 45rem"
      >
        <!-- 欄位 1: 目錄與規則名稱 (佔用最小不遮擋寬度約 24rem，其餘寬度留給最後一欄) -->
        <Column
          field="name"
          header="目錄 / 規則項目"
          expander
          header-class="whitespace-nowrap"
          class="whitespace-nowrap"
          style="width: 24rem; min-width: 22rem; max-width: 26rem"
        >
          <template #body="{ node }">
            <!-- 資料夾節點 (次要文字註解計數，無 tag 外框) -->
            <div v-if="node.data.type === 'folder'" class="folder-row flex items-center gap-1.5 py-0.5 select-none leading-tight">
              <i :class="node.expanded ? 'pi pi-folder-open text-amber-400' : 'pi pi-folder text-amber-400'" class="text-xs"></i>
              <span class="font-semibold text-white tracking-wide">{{ node.data.name }}</span>
              <span v-if="node.data.ruleCount" class="text-[11px] text-[#858585] font-normal ml-0.5">
                ({{ node.data.ruleCount }} 條)
              </span>
            </div>

            <!-- PartDB 項目節點：無 ToggleSwitch，僅提供 Viewer -->
            <div
              v-else-if="node.data.type === 'partdb'"
              class="partdb-row flex items-center gap-1.5 py-0.5 leading-tight"
            >
              <i class="pi pi-database text-teal-400 text-xs shrink-0 ml-0.5"></i>
              <span
                class="font-mono text-white text-xs truncate cursor-pointer hover:text-teal-300 hover:underline"
                :title="node.data.description ? `${node.data.name} - ${node.data.description}` : node.data.name"
                @click="viewRuleYaml(node.data)"
              >
                {{ node.data.name }}
              </span>
            </div>

            <!-- 規則節點：ToggleSwitch 放在開頭 (緊湊 scale)，移除啟用文字 -->
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
              <i class="pi pi-file-code text-sky-400 text-xs shrink-0"></i>
              <span
                class="font-mono text-white text-xs truncate cursor-pointer hover:text-sky-300 hover:underline"
                :title="node.data.description ? `${node.data.name} - ${node.data.description}` : node.data.name"
                @click="viewRuleYaml(node.data)"
              >
                {{ node.data.name }}
              </span>
            </div>
          </template>
        </Column>

        <!-- 欄位 2: 層級 (Level - 緊湊固定最小寬度) -->
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
              class="text-[10px] px-1.5 py-0.5 rounded font-mono uppercase inline-block whitespace-nowrap"
              :class="{
                'bg-rose-500/15 text-rose-300 border border-rose-500/20': node.data.level === 'level3',
                'bg-sky-500/15 text-sky-300 border border-sky-500/20': node.data.level === 'level2',
                'bg-emerald-500/15 text-emerald-300 border border-emerald-500/20': node.data.level === 'level1',
                'bg-teal-500/15 text-teal-300 border border-teal-500/20': node.data.level === 'partdb'
              }"
            >
              {{ formatLevelLabel(node.data.level) }}
            </span>
          </template>
        </Column>

        <!-- 欄位 3: 嚴重等級 (Severity - 緊湊固定最小寬度) -->
        <Column
          field="severity"
          header="嚴重等級"
          header-class="whitespace-nowrap text-center"
          class="whitespace-nowrap text-center"
          style="width: 5.5rem; min-width: 5.5rem"
        >
          <template #body="{ node }">
            <span
              v-if="node.data.severity"
              class="text-[10px] px-1.5 py-0.5 rounded font-mono uppercase inline-block whitespace-nowrap"
              :class="{
                'bg-rose-500/15 text-rose-400 border border-rose-500/30': node.data.severity === 'Fatal',
                'bg-orange-500/15 text-orange-400 border border-orange-500/30': node.data.severity === 'Error',
                'bg-amber-500/15 text-amber-400 border border-amber-500/30': node.data.severity === 'Warning',
                'bg-sky-500/15 text-sky-400 border border-sky-500/30': node.data.severity === 'Info'
              }"
            >
              {{ node.data.severity }}
            </span>
            <span v-else-if="node.data.type === 'rule' || node.data.type === 'partdb'" class="text-[#666666] text-xs font-mono">-</span>
          </template>
        </Column>

        <!-- 欄位 4: 說明與領域標籤 (自動佔滿剩餘全部橫向空間) -->
        <Column field="description" header="說明與領域標籤" class="w-full">
          <template #body="{ node }">
            <div v-if="node.data.type === 'rule' || node.data.type === 'partdb'" class="flex items-center gap-2 w-full py-0.5">
              <span class="text-xs text-[#cccccc] leading-normal break-words" :title="node.data.description">
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
      class="!w-[650px] !max-w-[90vw] !bg-[#1e1e1e] !border-l !border-[#333333] !text-white"
      :header="selectedRuleData?.name || '規則 YAML 原始碼'"
    >
      <div v-if="selectedRuleData" class="flex flex-col gap-4 h-full pb-4">
        <!-- 中繼資訊條 -->
        <div class="flex flex-wrap gap-2 items-center p-3 rounded bg-[#252526] border border-[#333333] text-xs">
          <div class="flex items-center gap-1">
            <span class="text-[#858585]">層級:</span>
            <strong class="text-white uppercase font-mono">{{ formatLevelLabel(selectedRuleData.level) }}</strong>
          </div>
          <div class="w-px h-3 bg-[#333333]"></div>
          <div class="flex items-center gap-1">
            <span class="text-[#858585]">目錄:</span>
            <code class="text-sky-300 font-mono">{{ selectedRuleData.category_path }}</code>
          </div>
          <div v-if="selectedRuleData.level !== 'partdb'" class="w-px h-3 bg-[#333333]"></div>
          <div v-if="selectedRuleData.level !== 'partdb'" class="flex items-center gap-1">
            <span class="text-[#858585]">狀態:</span>
            <Tag
              :value="selectedRuleData.enabled !== false ? '已啟用' : '已停用'"
              :severity="selectedRuleData.enabled !== false ? 'success' : 'secondary'"
              class="text-[10px]"
            />
          </div>
        </div>

        <div v-if="selectedRuleData.description" class="text-xs text-[#cccccc] leading-relaxed p-2.5 rounded bg-[#252526] border border-[#333333]">
          {{ selectedRuleData.description }}
        </div>

        <!-- 複製與原始 YAML -->
        <div class="flex justify-between items-center mt-1">
          <span class="text-xs text-[#858585] font-mono flex items-center gap-1">
            <i class="pi pi-file text-xs"></i>
            {{ selectedRuleData.filename }}
          </span>
          <button
            type="button"
            class="bg-[#252526] hover:bg-[#333333] border border-[#333333] text-[#cccccc] hover:text-white px-2.5 py-1 rounded text-xs flex items-center gap-1 transition-colors cursor-pointer"
            @click="copyDrawerYaml"
          >
            <i class="pi pi-copy text-xs"></i>
            {{ isCopied ? '已複製!' : '複製 YAML' }}
          </button>
        </div>

        <div class="flex-1 overflow-y-auto rounded border border-[#333333] bg-[#141414] p-3">
          <pre class="m-0 font-mono text-xs text-[#d4d4d4] leading-relaxed whitespace-pre-wrap break-all"><code>{{ selectedRuleData.rawYaml }}</code></pre>
        </div>
      </div>
    </Drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import TreeTable from 'primevue/treetable'
import Column from 'primevue/column'
import ToggleSwitch from 'primevue/toggleswitch'
import Drawer from 'primevue/drawer'
import Tag from 'primevue/tag'
import Button from 'primevue/button'
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
  // 樂觀更新前端物件狀態
  ruleData.enabled = newVal
  setTimeout(() => {
    updatingRule.value = null
  }, 400)
}

const getSeverityTagSeverity = (sev: string) => {
  switch (sev) {
    case 'Fatal': return 'danger'
    case 'Error': return 'warn'
    case 'Warning': return 'info'
    default: return 'secondary'
  }
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
    if (!partdbDomainMap[domain]) partdbDomainMap[domain] = []
    partdbDomainMap[domain].push({
      key: `partdb_${p.pn}`,
      data: {
        type: 'partdb',
        name: p.pn,
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

  // 根目錄 patterns/ (依序: Level 3 -> Level 2 -> Level 1 -> PartDB)
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

    // 關鍵字搜尋
    if (filterText.value.trim()) {
      const q = filterText.value.trim().toLowerCase()
      const matchName = (data.name || '').toLowerCase().includes(q)
      const matchDesc = (data.description || '').toLowerCase().includes(q)
      const matchPath = (data.category_path || '').toLowerCase().includes(q)
      const matchTag = (data.tags || []).some((t: string) => t.toLowerCase().includes(q))
      if (!matchName && !matchDesc && !matchPath && !matchTag) return null
    }

    // 層級篩選
    if (selectedLevel.value && data.level !== selectedLevel.value) {
      return null
    }

    // 嚴重等級篩選 (PartDB 沒有 severity，選特定嚴重度時過濾掉)
    if (selectedSeverity.value && data.severity !== selectedSeverity.value) {
      return null
    }

    // 狀態篩選 (PartDB 無啟用/停用概念，選特定狀態時過濾掉)
    if (selectedStatus.value === 'enabled' && (data.type === 'partdb' || data.enabled === false)) {
      return null
    }
    if (selectedStatus.value === 'disabled' && (data.type === 'partdb' || data.enabled !== false)) {
      return null
    }

    // 標籤篩選 (PartDB 沒有 tags，選特定標籤時過濾掉)
    if (selectedTag.value && !(data.tags || []).includes(selectedTag.value)) {
      return null
    }

    return { ...node }
  }

  // 資料夾節點遞迴篩選子項目
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

// 計算過濾後符合條件的規則總數 (含 PartDB)
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

