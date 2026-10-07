<template>
  <div class="drawer-step-content">
    <!-- 拓撲數據統計 Banner -->
    <div class="drawer-stat-banner">
      <div class="banner-stat">
        <span class="stat-num">{{ graphDetails?.components_count ?? preSummary?.component_count ?? 0 }}</span>
        <span class="stat-name">元件總數</span>
      </div>
      <div class="banner-stat">
        <span class="stat-num">{{ graphDetails?.nets_count ?? preSummary?.net_count ?? 0 }}</span>
        <span class="stat-name">網路 (Net) 數</span>
      </div>
      <div class="banner-stat">
        <span class="stat-num">{{ graphDetails?.pins_count ?? 0 }}</span>
        <span class="stat-name">引腳連接 (Pin) 數</span>
      </div>
      <div class="banner-stat">
        <span class="stat-num text-cyan">{{ detectedBuses.length }}</span>
        <span class="stat-name">偵測匯流排</span>
      </div>
    </div>

    <!-- 匯流排清單 -->
    <div class="chip-row">
      <span class="chip-label">匯流排種類:</span>
      <span v-if="detectedBuses.length === 0" class="text-secondary text-sm">(無)</span>
      <span v-for="bus in detectedBuses" :key="bus" class="badge-tag tag-cyan">{{ bus }}</span>
    </div>

    <!-- 核心晶片與控制器 -->
    <div class="chip-row">
      <span class="chip-label">核心晶片與控制器 (Key ICs):</span>
      <span v-if="keyIcsList.length === 0" class="text-secondary text-sm">(無)</span>
      <span v-for="ic in keyIcsList" :key="ic" class="badge-tag tag-purple">{{ ic }}</span>
    </div>

    <!-- 主要介面連接器 -->
    <div v-if="keyConnectorsList.length > 0" class="chip-row">
      <span class="chip-label">主要介面連接器 (Key Connectors):</span>
      <span v-for="conn in keyConnectorsList" :key="conn" class="badge-tag tag-blue">{{ conn }}</span>
    </div>

    <!-- 晶片功能清單 (IC Directory by Role) -->
    <div v-if="Object.keys(icDirectoryByRole).length > 0" class="role-directory-card">
      <h4 class="content-subtitle">晶片功能清單 (IC Directory by Role)</h4>
      <div v-for="(ics, role) in icDirectoryByRole" :key="role" class="chip-row role-row">
        <span class="chip-label role-label">{{ role }}:</span>
        <span v-for="ic in ics" :key="ic" class="badge-tag tag-outline">{{ ic }}</span>
      </div>
    </div>

    <!-- 非電氣/機構件分流 -->
    <div v-if="nonElectricalList.length > 0" class="chip-row">
      <span class="chip-label">非電氣/機構件分流 (Non-Electrical):</span>
      <span class="badge-tag tag-gray">已隔離 {{ nonElectricalList.length }} 顆機構/測試點件</span>
    </div>

    <!-- 子頁籤導覽 (Sub-Tabs) -->
    <div class="step2-subtabs">
      <button
        type="button"
        class="subtab-btn"
        :class="{ active: currentTab === 'components' }"
        @click="currentTab = 'components'"
      >
        <i class="pi pi-box mr-1"></i>
        <span>元件清單 (Components)</span>
        <span class="subtab-badge">{{ allComponents.length }}</span>
      </button>
      <button
        type="button"
        class="subtab-btn"
        :class="{ active: currentTab === 'nets' }"
        @click="currentTab = 'nets'"
      >
        <i class="pi pi-share-alt mr-1"></i>
        <span>網路清單 (Nets)</span>
        <span class="subtab-badge">{{ allNets.length }}</span>
      </button>
    </div>

    <!-- ================= 頁籤 1: 元件表格與表頭 Filter ================= -->
    <div v-if="currentTab === 'components'" class="tab-pane-content">
      <div class="table-filter-toolbar">
        <!-- 關鍵字搜尋 -->
        <div class="filter-search-box">
          <i class="pi pi-search filter-search-icon"></i>
          <input
            v-model="currentCompSearch"
            type="text"
            placeholder="搜尋 RefDes / 型號 / 封裝 / 描述..."
            class="filter-search-input"
          />
        </div>

        <!-- 實體類別篩選 -->
        <select v-model="currentCompCategoryFilter" class="filter-select">
          <option value="">全部實體類別 ({{ availableCategories.length }})</option>
          <option v-for="cat in availableCategories" :key="cat" :value="cat">
            {{ cat }}
          </option>
        </select>

        <!-- 細部類型篩選 -->
        <select v-model="currentCompSubCategoryFilter" class="filter-select">
          <option value="">全部細部類型 ({{ availableSubCategories.length }})</option>
          <option v-for="sc in availableSubCategories" :key="sc" :value="sc">
            {{ sc }}
          </option>
        </select>

        <!-- 拓撲角色篩選 -->
        <select v-model="currentCompRoleFilter" class="filter-select">
          <option value="">全部拓撲角色 ({{ availableRoles.length }})</option>
          <option v-for="r in availableRoles" :key="r" :value="r">
            {{ r }}
          </option>
        </select>

        <!-- 電氣性篩選 -->
        <select v-model="currentCompElectricalFilter" class="filter-select">
          <option value="all">電氣性: 全部</option>
          <option value="electrical">⚡ 僅電氣件</option>
          <option value="non_electrical">⚪ 僅非電氣件</option>
        </select>

        <!-- 重設篩選 -->
        <button v-if="hasCompFilters" type="button" class="btn-clear-filter" @click="clearCompFilters">
          <i class="pi pi-times mr-1"></i>清除篩選
        </button>
      </div>

      <!-- 分頁與筆數統計列 -->
      <div class="table-pagination-bar">
        <div class="pagination-info">
          顯示 <strong>{{ paginatedComponents.length }}</strong> 筆
          <span class="text-secondary">
            (篩選結果: {{ filteredComponents.length }} / 全部: {{ allComponents.length }} 顆)
          </span>
        </div>

        <div class="pagination-controls">
          <label class="page-size-label">每頁:</label>
          <select v-model.number="currentCompPageSize" class="page-size-select">
            <option :value="20">20</option>
            <option :value="50">50</option>
            <option :value="100">100</option>
            <option :value="-1">全部</option>
          </select>

          <button
            type="button"
            class="pagination-btn"
            :disabled="currentCompPage <= 1"
            @click="currentCompPage--"
          >
            上一頁
          </button>
          <span class="page-number-indicator">第 {{ currentCompPage }} / {{ totalCompPages }} 頁</span>
          <button
            type="button"
            class="pagination-btn"
            :disabled="currentCompPage >= totalCompPages"
            @click="currentCompPage++"
          >
            下一頁
          </button>
        </div>
      </div>

      <!-- 元件清單表格 -->
      <div class="table-container">
        <table class="drawer-table">
          <thead>
            <tr>
              <th style="min-width: 90px;">RefDes</th>
              <th style="min-width: 100px;">實體類別</th>
              <th style="min-width: 110px;">細部類型</th>
              <th style="min-width: 110px;">拓撲角色</th>
              <th style="min-width: 90px;">電氣性</th>
              <th style="min-width: 130px;">型號 / 數值</th>
              <th style="min-width: 110px;">封裝 (Package)</th>
              <th style="min-width: 80px;">引腳數</th>
              <th style="min-width: 180px;">描述 (Description)</th>
            </tr>
          </thead>
          <tbody v-if="paginatedComponents.length > 0">
            <tr v-for="comp in paginatedComponents" :key="comp.ref_des">
              <td>
                <strong>{{ comp.ref_des }}</strong>
                <span v-if="isKeyIc(comp.ref_des)" class="badge-tag tag-purple ml-1" title="核心晶片">Core</span>
              </td>
              <td>
                <span class="badge-tag" :class="getCategoryTagClass(comp.category)">
                  {{ comp.category }}
                </span>
              </td>
              <td>{{ comp.sub_category || '-' }}</td>
              <td>
                <span v-if="comp.functional_role && comp.functional_role !== 'None'" class="badge-tag tag-outline">
                  {{ comp.functional_role }}
                </span>
                <span v-else class="text-secondary text-xs">-</span>
              </td>
              <td>
                <span v-if="comp.is_electrical !== false" class="badge-tag tag-green">
                  ⚡ 電氣件
                </span>
                <span v-else class="badge-tag tag-gray">
                  ⚪ 非電氣
                </span>
              </td>
              <td><code>{{ comp.part_value || '-' }}</code></td>
              <td><span class="text-secondary text-xs">{{ comp.package || '-' }}</span></td>
              <td>{{ comp.pins_count }} pins</td>
              <td>
                <span class="cell-desc" :title="comp.description || ''">
                  {{ comp.description || '-' }}
                </span>
              </td>
            </tr>
          </tbody>
          <tbody v-else>
            <tr>
              <td colspan="9" class="empty-table-state">
                <i class="pi pi-filter-slash mr-1"></i>無符合篩選條件的元件
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- ================= 頁籤 2: 網路表格與表頭 Filter ================= -->
    <div v-if="currentTab === 'nets'" class="tab-pane-content">
      <div class="table-filter-toolbar">
        <!-- 關鍵字搜尋 -->
        <div class="filter-search-box">
          <i class="pi pi-search filter-search-icon"></i>
          <input
            v-model="currentNetSearch"
            type="text"
            placeholder="搜尋網路名稱 (Net Name) 或連接元件..."
            class="filter-search-input"
          />
        </div>

        <!-- 網路類型篩選 -->
        <select v-model="currentNetTypeFilter" class="filter-select">
          <option value="all">全部網路類型</option>
          <option value="power">⚡ 電源 (Power)</option>
          <option value="ground">⏚ 接地 (Ground)</option>
          <option value="bus">🚌 匯流排 (Bus)</option>
          <option value="signal">〰️ 一般訊號 (Signal)</option>
        </select>

        <!-- 匯流排協定篩選 -->
        <select v-model="currentNetBusFilter" class="filter-select">
          <option value="">全部匯流排協定 ({{ availableNetBuses.length }})</option>
          <option v-for="b in availableNetBuses" :key="b" :value="b">
            {{ b }}
          </option>
        </select>

        <!-- 重設篩選 -->
        <button v-if="hasNetFilters" type="button" class="btn-clear-filter" @click="clearNetFilters">
          <i class="pi pi-times mr-1"></i>清除篩選
        </button>
      </div>

      <!-- 分頁與筆數統計列 -->
      <div class="table-pagination-bar">
        <div class="pagination-info">
          顯示 <strong>{{ paginatedNets.length }}</strong> 條
          <span class="text-secondary">
            (篩選結果: {{ filteredNets.length }} / 全部: {{ allNets.length }} 條)
          </span>
        </div>

        <div class="pagination-controls">
          <label class="page-size-label">每頁:</label>
          <select v-model.number="currentNetPageSize" class="page-size-select">
            <option :value="20">20</option>
            <option :value="50">50</option>
            <option :value="100">100</option>
            <option :value="-1">全部</option>
          </select>

          <button
            type="button"
            class="pagination-btn"
            :disabled="currentNetPage <= 1"
            @click="currentNetPage--"
          >
            上一頁
          </button>
          <span class="page-number-indicator">第 {{ currentNetPage }} / {{ totalNetPages }} 頁</span>
          <button
            type="button"
            class="pagination-btn"
            :disabled="currentNetPage >= totalNetPages"
            @click="currentNetPage++"
          >
            下一頁
          </button>
        </div>
      </div>

      <!-- 網路清單表格 -->
      <div class="table-container">
        <table class="drawer-table">
          <thead>
            <tr>
              <th style="min-width: 140px;">網路名稱 (Net Name)</th>
              <th style="min-width: 110px;">網路屬性 (Type)</th>
              <th style="min-width: 100px;">匯流排協定</th>
              <th style="min-width: 90px;">連接元件數</th>
              <th style="min-width: 250px;">相連元件標籤 (Connected Components)</th>
            </tr>
          </thead>
          <tbody v-if="paginatedNets.length > 0">
            <tr v-for="net in paginatedNets" :key="net.net_name">
              <td><code><strong>{{ net.net_name }}</strong></code></td>
              <td>
                <span v-if="net.is_power" class="badge-tag tag-yellow mr-1">⚡ 電源</span>
                <span v-if="net.is_ground" class="badge-tag tag-gray mr-1">⏚ 接地</span>
                <span v-if="net.bus_type" class="badge-tag tag-cyan mr-1">🚌 {{ net.bus_type }}</span>
                <span v-if="!net.is_power && !net.is_ground && !net.bus_type" class="badge-tag tag-blue">〰️ 訊號</span>
              </td>
              <td>
                <span v-if="net.bus_type" class="badge-tag tag-cyan">{{ net.bus_type }}</span>
                <span v-else class="text-secondary text-xs">-</span>
              </td>
              <td>{{ net.connected_components?.length || 0 }} 顆</td>
              <td>
                <div class="net-tags-wrapper">
                  <span
                    v-for="c in (net.connected_components || []).slice(0, 6)"
                    :key="c"
                    class="net-tag"
                  >
                    {{ c }}
                  </span>
                  <span
                    v-if="(net.connected_components || []).length > 6"
                    class="net-tag-more"
                    :title="(net.connected_components || []).join(', ')"
                  >
                    +{{ (net.connected_components || []).length - 6 }} more
                  </span>
                </div>
              </td>
            </tr>
          </tbody>
          <tbody v-else>
            <tr>
              <td colspan="5" class="empty-table-state">
                <i class="pi pi-filter-slash mr-1"></i>無符合篩選條件的網路
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * @file Step2TopologyDrawer.vue
 * @description TaskMonitorView 抽屜 Step 2：線路圖譜拓撲、核心晶片與元件/網路篩選表格
 */

import { computed } from 'vue'
import type { TaskGraphDetails, TaskSummary } from '@/types/task'

interface Props {
  graphDetails: TaskGraphDetails | null
  preSummary?: TaskSummary | null
  activeTab?: 'components' | 'nets'
  compSearch?: string
  compCategoryFilter?: string
  compSubCategoryFilter?: string
  compRoleFilter?: string
  compElectricalFilter?: 'all' | 'electrical' | 'non_electrical'
  compPage?: number
  compPageSize?: number
  netSearch?: string
  netTypeFilter?: 'all' | 'power' | 'ground' | 'bus' | 'signal'
  netBusFilter?: string
  netPage?: number
  netPageSize?: number
}

const props = withDefaults(defineProps<Props>(), {
  graphDetails: null,
  preSummary: () => ({ buses: [], platforms: [], component_count: 0, net_count: 0 }),
  activeTab: 'components',
  compSearch: '',
  compCategoryFilter: '',
  compSubCategoryFilter: '',
  compRoleFilter: '',
  compElectricalFilter: 'all',
  compPage: 1,
  compPageSize: 20,
  netSearch: '',
  netTypeFilter: 'all',
  netBusFilter: '',
  netPage: 1,
  netPageSize: 20,
})

const emit = defineEmits<{
  (e: 'update:activeTab', val: 'components' | 'nets'): void
  (e: 'update:compSearch', val: string): void
  (e: 'update:compCategoryFilter', val: string): void
  (e: 'update:compSubCategoryFilter', val: string): void
  (e: 'update:compRoleFilter', val: string): void
  (e: 'update:compElectricalFilter', val: 'all' | 'electrical' | 'non_electrical'): void
  (e: 'update:compPage', val: number): void
  (e: 'update:compPageSize', val: number): void
  (e: 'update:netSearch', val: string): void
  (e: 'update:netTypeFilter', val: 'all' | 'power' | 'ground' | 'bus' | 'signal'): void
  (e: 'update:netBusFilter', val: string): void
  (e: 'update:netPage', val: number): void
  (e: 'update:netPageSize', val: number): void
}>()

// 雙向綁定 Computed
const currentTab = computed({
  get: () => props.activeTab,
  set: (val) => emit('update:activeTab', val),
})

const currentCompSearch = computed({
  get: () => props.compSearch,
  set: (val) => {
    emit('update:compSearch', val)
    emit('update:compPage', 1)
  },
})

const currentCompCategoryFilter = computed({
  get: () => props.compCategoryFilter,
  set: (val) => {
    emit('update:compCategoryFilter', val)
    emit('update:compPage', 1)
  },
})

const currentCompSubCategoryFilter = computed({
  get: () => props.compSubCategoryFilter,
  set: (val) => {
    emit('update:compSubCategoryFilter', val)
    emit('update:compPage', 1)
  },
})

const currentCompRoleFilter = computed({
  get: () => props.compRoleFilter,
  set: (val) => {
    emit('update:compRoleFilter', val)
    emit('update:compPage', 1)
  },
})

const currentCompElectricalFilter = computed({
  get: () => props.compElectricalFilter,
  set: (val) => {
    emit('update:compElectricalFilter', val)
    emit('update:compPage', 1)
  },
})

const currentCompPage = computed({
  get: () => props.compPage,
  set: (val) => emit('update:compPage', val),
})

const currentCompPageSize = computed({
  get: () => props.compPageSize,
  set: (val) => {
    emit('update:compPageSize', val)
    emit('update:compPage', 1)
  },
})

const currentNetSearch = computed({
  get: () => props.netSearch,
  set: (val) => {
    emit('update:netSearch', val)
    emit('update:netPage', 1)
  },
})

const currentNetTypeFilter = computed({
  get: () => props.netTypeFilter,
  set: (val) => {
    emit('update:netTypeFilter', val)
    emit('update:netPage', 1)
  },
})

const currentNetBusFilter = computed({
  get: () => props.netBusFilter,
  set: (val) => {
    emit('update:netBusFilter', val)
    emit('update:netPage', 1)
  },
})

const currentNetPage = computed({
  get: () => props.netPage,
  set: (val) => emit('update:netPage', val),
})

const currentNetPageSize = computed({
  get: () => props.netPageSize,
  set: (val) => {
    emit('update:netPageSize', val)
    emit('update:netPage', 1)
  },
})

// 特徵欄位計算
const detectedBuses = computed(() => {
  return props.graphDetails?.buses || props.preSummary?.buses || []
})

const keyIcsList = computed(() => {
  if (props.graphDetails?.key_ics !== undefined) {
    return props.graphDetails.key_ics
  }
  return props.graphDetails?.main_ics || []
})

const keyConnectorsList = computed(() => {
  return props.graphDetails?.key_connectors || []
})

const icDirectoryByRole = computed(() => {
  return props.graphDetails?.ic_directory_by_role || {}
})

const nonElectricalList = computed(() => {
  return props.graphDetails?.non_electrical_components || []
})

const allComponents = computed(() => {
  return props.graphDetails?.components || []
})

const allNets = computed(() => {
  return props.graphDetails?.nets || []
})

const availableCategories = computed(() => {
  const set = new Set<string>()
  allComponents.value.forEach((c) => {
    if (c.category) set.add(c.category)
  })
  return Array.from(set).sort()
})

const availableSubCategories = computed(() => {
  const set = new Set<string>()
  allComponents.value.forEach((c) => {
    if (c.sub_category) set.add(c.sub_category)
  })
  return Array.from(set).sort()
})

const availableRoles = computed(() => {
  const set = new Set<string>()
  allComponents.value.forEach((c) => {
    if (c.functional_role && c.functional_role !== 'None') set.add(c.functional_role)
  })
  return Array.from(set).sort()
})

const filteredComponents = computed(() => {
  let list = allComponents.value
  if (props.compCategoryFilter) {
    list = list.filter((c) => c.category === props.compCategoryFilter)
  }
  if (props.compSubCategoryFilter) {
    list = list.filter((c) => c.sub_category === props.compSubCategoryFilter)
  }
  if (props.compRoleFilter) {
    list = list.filter((c) => c.functional_role === props.compRoleFilter)
  }
  if (props.compElectricalFilter === 'electrical') {
    list = list.filter((c) => c.is_electrical !== false)
  } else if (props.compElectricalFilter === 'non_electrical') {
    list = list.filter((c) => c.is_electrical === false)
  }
  if (props.compSearch.trim()) {
    const q = props.compSearch.trim().toLowerCase()
    list = list.filter(
      (c) =>
        c.ref_des.toLowerCase().includes(q) ||
        (c.part_value && c.part_value.toLowerCase().includes(q)) ||
        (c.package && c.package.toLowerCase().includes(q)) ||
        (c.description && c.description.toLowerCase().includes(q))
    )
  }
  return list
})

const totalCompPages = computed(() => {
  if (props.compPageSize === -1) return 1
  return Math.max(1, Math.ceil(filteredComponents.value.length / props.compPageSize))
})

const paginatedComponents = computed(() => {
  if (props.compPageSize === -1) return filteredComponents.value
  const start = (props.compPage - 1) * props.compPageSize
  return filteredComponents.value.slice(start, start + props.compPageSize)
})

const hasCompFilters = computed(() => {
  return !!(
    props.compSearch ||
    props.compCategoryFilter ||
    props.compSubCategoryFilter ||
    props.compRoleFilter ||
    props.compElectricalFilter !== 'all'
  )
})

const clearCompFilters = () => {
  emit('update:compSearch', '')
  emit('update:compCategoryFilter', '')
  emit('update:compSubCategoryFilter', '')
  emit('update:compRoleFilter', '')
  emit('update:compElectricalFilter', 'all')
  emit('update:compPage', 1)
}

// 網路可用篩選選項
const availableNetBuses = computed(() => {
  const set = new Set<string>()
  allNets.value.forEach((n) => {
    if (n.bus_type) set.add(n.bus_type)
  })
  return Array.from(set).sort()
})

const filteredNets = computed(() => {
  let list = allNets.value
  if (props.netTypeFilter === 'power') {
    list = list.filter((n) => n.is_power)
  } else if (props.netTypeFilter === 'ground') {
    list = list.filter((n) => n.is_ground)
  } else if (props.netTypeFilter === 'bus') {
    list = list.filter((n) => !!n.bus_type)
  } else if (props.netTypeFilter === 'signal') {
    list = list.filter((n) => !n.is_power && !n.is_ground && !n.bus_type)
  }

  if (props.netBusFilter) {
    list = list.filter((n) => n.bus_type === props.netBusFilter)
  }

  if (props.netSearch.trim()) {
    const q = props.netSearch.trim().toLowerCase()
    list = list.filter(
      (n) =>
        n.net_name.toLowerCase().includes(q) ||
        (n.connected_components && n.connected_components.some((c) => c.toLowerCase().includes(q)))
    )
  }
  return list
})

const totalNetPages = computed(() => {
  if (props.netPageSize === -1) return 1
  return Math.max(1, Math.ceil(filteredNets.value.length / props.netPageSize))
})

const paginatedNets = computed(() => {
  if (props.netPageSize === -1) return filteredNets.value
  const start = (props.netPage - 1) * props.netPageSize
  return filteredNets.value.slice(start, start + props.netPageSize)
})

const hasNetFilters = computed(() => {
  return !!(props.netSearch || props.netTypeFilter !== 'all' || props.netBusFilter)
})

const clearNetFilters = () => {
  emit('update:netSearch', '')
  emit('update:netTypeFilter', 'all')
  emit('update:netBusFilter', '')
  emit('update:netPage', 1)
}

const getCategoryTagClass = (category: string): string => {
  switch (category) {
    case 'IC':
      return 'tag-purple'
    case 'Passive':
      return 'tag-blue'
    case 'Discrete':
      return 'tag-cyan'
    case 'Connector':
      return 'tag-green'
    case 'NonElectrical':
      return 'tag-gray'
    case 'Electromechanical':
      return 'tag-orange'
    default:
      return 'tag-outline'
  }
}

const isKeyIc = (refDes: string): boolean => {
  return keyIcsList.value.some((ic) => ic === refDes || ic.startsWith(refDes + ' ') || ic.startsWith(refDes + '('))
}
</script>

<style scoped>
.drawer-step-content {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
}

.drawer-stat-banner {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(110px, 1fr));
  gap: 0.65rem;
  background-color: var(--vscode-bg-panel, #252526);
  border: 1px solid var(--vscode-border, #333333);
  border-radius: 6px;
  padding: 0.75rem;
}

.banner-stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.stat-num {
  font-size: 1.2rem;
  font-weight: 700;
  color: var(--vscode-text-heading, #ffffff);
}

.stat-name {
  font-size: 0.68rem;
  color: var(--vscode-text-muted, #858585);
}

.chip-row {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  flex-wrap: wrap;
}

.chip-label {
  font-size: 0.76rem;
  color: var(--vscode-text-secondary, #999999);
  font-weight: 600;
}

.role-directory-card {
  background-color: var(--vscode-bg-panel, #252526);
  border: 1px solid var(--vscode-border, #333333);
  border-radius: 4px;
  padding: 0.65rem;
}

.content-subtitle {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--vscode-text-heading, #ffffff);
  margin: 0 0 0.45rem 0;
}

.role-row {
  margin-bottom: 0.3rem;
}

.role-label {
  color: var(--vscode-text-secondary, #999999);
  min-width: 100px;
}

.step2-subtabs {
  display: flex;
  gap: 0.45rem;
  margin: 0.5rem 0 0.25rem 0;
  border-bottom: 1px solid var(--vscode-border, #333333);
  padding-bottom: 0.45rem;
}

.subtab-btn {
  background: transparent;
  border: none;
  padding: 0.4rem 0.75rem;
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--vscode-text-muted, #858585);
  cursor: pointer;
  border-radius: 4px;
  display: flex;
  align-items: center;
  gap: 0.4rem;
  transition: all 0.15s ease;
}

.subtab-btn:hover {
  background-color: var(--vscode-bg-hover, #2a2d2e);
  color: #ffffff;
}

.subtab-btn.active {
  background-color: #1e3a5f;
  color: #38bdf8;
}

.subtab-badge {
  font-size: 0.7rem;
  background-color: #1e1e1e;
  color: #cccccc;
  padding: 0.08rem 0.4rem;
  border-radius: 999px;
  font-weight: 700;
  border: 1px solid #3c3c3c;
}

.subtab-btn.active .subtab-badge {
  background-color: #0284c7;
  color: #ffffff;
  border-color: #0284c7;
}

.table-filter-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.45rem;
  margin-bottom: 0.65rem;
  background-color: var(--vscode-bg-panel, #252526);
  padding: 0.55rem 0.65rem;
  border-radius: 4px;
  border: 1px solid var(--vscode-border, #333333);
}

.filter-search-box {
  position: relative;
  flex: 1 1 200px;
  min-width: 180px;
}

.filter-search-input {
  width: 100%;
  padding: 0.35rem 0.65rem 0.35rem 1.85rem;
  font-size: 0.78rem;
  border: 1px solid var(--vscode-border-light, #3c3c3c);
  border-radius: 3px;
  background-color: var(--vscode-bg-base, #1e1e1e);
  color: var(--vscode-text-main, #cccccc);
  outline: none;
  box-sizing: border-box;
}

.filter-search-input:focus {
  border-color: var(--vscode-blue, #007acc);
}

.filter-search-icon {
  position: absolute;
  left: 0.55rem;
  top: 50%;
  transform: translateY(-50%);
  color: var(--vscode-text-muted, #858585);
  font-size: 0.78rem;
  pointer-events: none;
}

.filter-select {
  padding: 0.35rem 0.55rem;
  font-size: 0.78rem;
  border: 1px solid var(--vscode-border-light, #3c3c3c);
  border-radius: 3px;
  background-color: var(--vscode-bg-base, #1e1e1e);
  color: var(--vscode-text-main, #cccccc);
  outline: none;
  cursor: pointer;
}

.filter-select:focus {
  border-color: var(--vscode-blue, #007acc);
}

.btn-clear-filter {
  background: transparent;
  border: 1px dashed var(--vscode-border-light, #3c3c3c);
  color: var(--vscode-text-muted, #858585);
  padding: 0.3rem 0.55rem;
  font-size: 0.75rem;
  border-radius: 3px;
  cursor: pointer;
  transition: all 0.15s ease;
  display: flex;
  align-items: center;
}

.btn-clear-filter:hover {
  background-color: rgba(241, 76, 76, 0.15);
  border-color: var(--vscode-danger, #f14c4c);
  color: var(--vscode-danger, #f14c4c);
}

.table-pagination-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.35rem 0.2rem 0.55rem 0.2rem;
  font-size: 0.75rem;
  color: var(--vscode-text-muted, #858585);
  flex-wrap: wrap;
  gap: 0.45rem;
}

.pagination-controls {
  display: flex;
  align-items: center;
  gap: 0.35rem;
}

.page-size-label {
  font-size: 0.72rem;
  color: var(--vscode-text-muted, #858585);
}

.page-size-select {
  padding: 0.18rem 0.35rem;
  font-size: 0.72rem;
  border: 1px solid var(--vscode-border-light, #3c3c3c);
  border-radius: 3px;
  background: var(--vscode-bg-panel, #252526);
  color: var(--vscode-text-main, #cccccc);
}

.pagination-btn {
  border: 1px solid var(--vscode-border-light, #3c3c3c);
  background: var(--vscode-bg-panel, #252526);
  color: var(--vscode-text-main, #cccccc);
  padding: 0.2rem 0.45rem;
  border-radius: 3px;
  font-size: 0.72rem;
  cursor: pointer;
  transition: all 0.1s ease;
}

.pagination-btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.pagination-btn:not(:disabled):hover {
  background-color: #333333;
}

.page-number-indicator {
  font-size: 0.72rem;
  color: var(--vscode-text-main, #cccccc);
  font-weight: 600;
  padding: 0 0.2rem;
}

.table-container {
  overflow-x: auto;
  border: 1px solid var(--vscode-border, #333333);
  border-radius: 4px;
  background-color: var(--vscode-bg-base, #1e1e1e);
  max-height: 480px;
  overflow-y: auto;
}

.drawer-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.78rem;
}

.drawer-table th {
  background-color: var(--vscode-bg-panel, #252526);
  padding: 0.45rem 0.65rem;
  border-bottom: 1px solid var(--vscode-border, #333333);
  text-align: left;
  color: var(--vscode-text-secondary, #999999);
  font-weight: 600;
}

.drawer-table td {
  padding: 0.45rem 0.65rem;
  border-bottom: 1px solid #282828;
  color: var(--vscode-text-main, #cccccc);
}

.drawer-table tbody tr:hover td {
  background-color: var(--vscode-bg-hover, #2a2d2e);
}

.cell-desc {
  max-width: 220px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  display: inline-block;
  vertical-align: middle;
  font-size: 0.76rem;
  color: var(--vscode-text-muted, #858585);
}

.net-tags-wrapper {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.2rem;
}

.net-tag {
  font-size: 0.68rem;
  padding: 0.1rem 0.35rem;
  border-radius: 2px;
  background-color: var(--vscode-bg-panel, #252526);
  color: var(--vscode-text-main, #cccccc);
  border: 1px solid var(--vscode-border-light, #3c3c3c);
  display: inline-block;
  font-family: monospace;
}

.net-tag-more {
  font-size: 0.68rem;
  color: var(--vscode-blue, #007acc);
  font-weight: 600;
  cursor: help;
  padding: 0.1rem 0.2rem;
}

.empty-table-state {
  padding: 2rem;
  text-align: center;
  color: var(--vscode-text-muted, #858585);
  font-size: 0.82rem;
}

.badge-tag {
  font-size: 0.7rem;
  padding: 0.12rem 0.4rem;
  border-radius: 3px;
  background-color: #2d2d2d;
  color: #cccccc;
}

.tag-cyan { background-color: #10323c; color: #4ec9b0; border: 1px solid #1a4f5f; font-weight: 600; }
.tag-purple { background-color: #351a44; color: #c586c0; border: 1px solid #58296e; font-weight: 600; }
.tag-blue { background-color: #162a45; color: #4fc1ff; border: 1px solid #1f426d; }
.tag-green { background-color: #133323; color: #89d185; border: 1px solid #1e5238; }
.tag-gray { background-color: #282828; color: #858585; border: 1px solid #3c3c3c; }
.tag-outline { background-color: #252526; color: #cccccc; border: 1px solid #3c3c3c; }
.tag-yellow { background-color: #3c3814; color: #dcdcaa; border: 1px solid #5e5720; font-weight: 600; }
.tag-orange { background-color: #3e2617; color: #ce9178; border: 1px solid #623d24; font-weight: 600; }
</style>
