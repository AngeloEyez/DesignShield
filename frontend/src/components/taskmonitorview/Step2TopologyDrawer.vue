<template>
  <div class="drawer-step-content flex flex-col gap-2.5">
    <!-- 1. 拓撲數據單行橫條 (Compact Metric Strip，高 ~38px) -->
    <div class="drawer-stat-banner grid grid-cols-2 sm:grid-cols-4 divide-y sm:divide-y-0 sm:divide-x divide-surface-border bg-surface-panel border border-surface-border rounded">
      <div class="banner-stat px-3 py-1.5 flex items-center justify-between">
        <span class="stat-name text-xs text-vscode-textSecondary">元件總數</span>
        <span class="stat-num text-sm font-semibold text-vscode-textHeading font-mono">{{ graphDetails?.components_count ?? preSummary?.component_count ?? 0 }}</span>
      </div>
      <div class="banner-stat px-3 py-1.5 flex items-center justify-between">
        <span class="stat-name text-xs text-vscode-textSecondary">網路 (Net) 數</span>
        <span class="stat-num text-sm font-semibold text-vscode-textHeading font-mono">{{ graphDetails?.nets_count ?? preSummary?.net_count ?? 0 }}</span>
      </div>
      <div class="banner-stat px-3 py-1.5 flex items-center justify-between">
        <span class="stat-name text-xs text-vscode-textSecondary">引腳連接 (Pin) 數</span>
        <span class="stat-num text-sm font-semibold text-vscode-textHeading font-mono">{{ graphDetails?.pins_count ?? 0 }}</span>
      </div>
      <div class="banner-stat px-3 py-1.5 flex items-center justify-between">
        <span class="stat-name text-xs text-vscode-textSecondary">偵測匯流排</span>
        <span class="stat-num text-sm font-semibold text-primary font-mono">{{ detectedBuses.length }}</span>
      </div>
    </div>

    <!-- 2. 緊湊拓撲特徵與核心晶片摘要列 (雙色低彩度：主色藍灰 vs 中性暖灰) -->
    <div class="flex flex-wrap items-center gap-x-4 gap-y-1.5 px-3 py-1.5 bg-surface-panel border border-surface-border rounded text-xs">
      <!-- 匯流排清單 -->
      <div class="chip-row flex items-center gap-1.5 flex-wrap">
        <span class="chip-label text-vscode-textMuted">匯流排:</span>
        <span v-if="detectedBuses.length === 0" class="text-vscode-textMuted">(無)</span>
        <span v-for="bus in detectedBuses" :key="bus" class="badge-tag tag-cyan text-[10px] font-mono px-1.5 py-0.2 rounded border border-primary/30 bg-primary/10 text-primary">{{ bus }}</span>
      </div>

      <div class="h-3 w-px bg-surface-border hidden sm:block"></div>

      <!-- 核心晶片與控制器 -->
      <div class="chip-row flex items-center gap-1.5 flex-wrap">
        <span class="chip-label text-vscode-textMuted">核心晶片 (Key ICs):</span>
        <span v-if="keyIcsList.length === 0" class="text-vscode-textMuted">(無)</span>
        <span v-for="ic in keyIcsList" :key="ic" class="badge-tag tag-purple text-[10px] font-mono px-1.5 py-0.2 rounded border border-primary/30 bg-primary/10 text-primary">{{ ic }}</span>
      </div>

      <!-- 主要介面連接器 -->
      <template v-if="keyConnectorsList.length > 0">
        <div class="h-3 w-px bg-surface-border hidden sm:block"></div>
        <div class="chip-row flex items-center gap-1.5 flex-wrap">
          <span class="chip-label text-vscode-textMuted">連接器:</span>
          <span v-for="conn in keyConnectorsList" :key="conn" class="badge-tag tag-blue text-[10px] font-mono px-1.5 py-0.2 rounded border border-surface-border bg-surface-ground text-vscode-textSecondary">{{ conn }}</span>
        </div>
      </template>

      <!-- 非電氣/機構件分流 -->
      <template v-if="nonElectricalList.length > 0">
        <div class="h-3 w-px bg-surface-border hidden sm:block"></div>
        <div class="chip-row flex items-center gap-1.5 flex-wrap">
          <span class="badge-tag tag-gray text-[10px] px-1.5 py-0.2 rounded border border-surface-border bg-surface-ground text-vscode-textMuted">已隔離 {{ nonElectricalList.length }} 顆機構/測試點件</span>
        </div>
      </template>
    </div>

    <!-- 晶片功能清單 (IC Directory by Role - 輕量無框分組) -->
    <div v-if="Object.keys(icDirectoryByRole).length > 0" class="role-directory-card px-3 py-1.5 rounded bg-surface-panel border border-surface-border flex flex-wrap items-center gap-x-4 gap-y-1 text-xs">
      <span class="content-subtitle text-[11px] font-medium text-vscode-textSecondary">晶片角色目錄:</span>
      <div v-for="(ics, role) in icDirectoryByRole" :key="role" class="chip-row role-row flex items-center gap-1 flex-wrap">
        <span class="chip-label role-label text-vscode-textMuted text-[11px]">{{ role }}:</span>
        <span v-for="ic in ics" :key="ic" class="badge-tag tag-outline text-[10px] font-mono px-1.5 py-0.2 rounded border border-surface-border bg-surface-ground text-vscode-textMain">{{ ic }}</span>
      </div>
    </div>

    <!-- 子頁籤導覽 (Sub-Tabs) -->
    <div class="step2-subtabs flex gap-1.5 border-b border-surface-border pb-1">
      <button
        type="button"
        class="subtab-btn flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-medium cursor-pointer border-0 transition-colors"
        :class="currentTab === 'components' ? 'bg-surface-active text-vscode-textHeading font-semibold' : 'bg-transparent text-vscode-textSecondary hover:text-vscode-textHeading hover:bg-surface-hover'"
        @click="currentTab = 'components'"
      >
        <i class="pi pi-box text-[11px]"></i>
        <span>元件清單 (Components)</span>
        <span class="subtab-badge text-[10px] px-1.5 py-0.2 rounded bg-surface-ground border border-surface-border text-vscode-textMuted font-mono">{{ allComponents.length }}</span>
      </button>
      <button
        type="button"
        class="subtab-btn flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-medium cursor-pointer border-0 transition-colors"
        :class="currentTab === 'nets' ? 'bg-surface-active text-vscode-textHeading font-semibold' : 'bg-transparent text-vscode-textSecondary hover:text-vscode-textHeading hover:bg-surface-hover'"
        @click="currentTab = 'nets'"
      >
        <i class="pi pi-share-alt text-[11px]"></i>
        <span>網路清單 (Nets)</span>
        <span class="subtab-badge text-[10px] px-1.5 py-0.2 rounded bg-surface-ground border border-surface-border text-vscode-textMuted font-mono">{{ allNets.length }}</span>
      </button>
    </div>

    <!-- ================= 頁籤 1: 元件表格與表頭 Filter ================= -->
    <div v-if="currentTab === 'components'" class="tab-pane-content flex flex-col gap-2">
      <div class="table-filter-toolbar flex items-center gap-2 flex-wrap text-xs">
        <!-- 關鍵字搜尋 (PrimeVue IconField + InputText) -->
        <div class="filter-search-box flex-1 min-w-[200px]">
          <IconField class="w-full">
            <InputIcon class="pi pi-search filter-search-icon text-vscode-textMuted text-xs" />
            <InputText
              v-model="currentCompSearch"
              type="text"
              size="small"
              placeholder="搜尋 RefDes / 型號 / 封裝 / 描述..."
              class="filter-search-input w-full text-xs"
            />
          </IconField>
        </div>

        <!-- 實體類別篩選 -->
        <Select
          v-model="currentCompCategoryFilter"
          :options="categoryFilterOptions"
          option-label="label"
          option-value="value"
          size="small"
          class="filter-select text-xs min-w-[130px]"
        />

        <!-- 細部類型篩選 -->
        <Select
          v-model="currentCompSubCategoryFilter"
          :options="subCategoryFilterOptions"
          option-label="label"
          option-value="value"
          size="small"
          class="filter-select text-xs min-w-[130px]"
        />

        <!-- 拓撲角色篩選 -->
        <Select
          v-model="currentCompRoleFilter"
          :options="roleFilterOptions"
          option-label="label"
          option-value="value"
          size="small"
          class="filter-select text-xs min-w-[130px]"
        />

        <!-- 電氣性篩選 -->
        <Select
          v-model="currentCompElectricalFilter"
          :options="electricalFilterOptions"
          option-label="label"
          option-value="value"
          size="small"
          class="filter-select text-xs min-w-[115px]"
        />

        <!-- 重設篩選 (圖示 + Tooltip) -->
        <Button
          v-if="hasCompFilters"
          v-tooltip.top="'清除所有篩選條件'"
          icon="pi pi-filter-slash"
          text
          size="small"
          severity="secondary"
          class="btn-clear-filter w-7 h-7 !p-0"
          title="清除篩選"
          @click="clearCompFilters"
        />
      </div>

      <!-- 分頁與筆數統計列 -->
      <div class="table-pagination-bar flex justify-between items-center text-xs text-vscode-textMuted py-0.5">
        <div class="pagination-info">
          顯示 <strong class="text-vscode-textHeading">{{ paginatedComponents.length }}</strong> 筆
          <span>
            (篩選結果: {{ filteredComponents.length }} / 全部: {{ allComponents.length }} 顆)
          </span>
        </div>

        <div class="pagination-controls flex items-center gap-1.5">
          <label class="page-size-label text-xs text-vscode-textMuted">每頁:</label>
          <Select
            v-model="currentCompPageSize"
            :options="pageSizeOptions"
            option-label="label"
            option-value="value"
            size="small"
            class="page-size-select text-xs"
          />

          <Button
            v-tooltip.top="'上一頁'"
            icon="pi pi-chevron-left"
            text
            size="small"
            severity="secondary"
            class="pagination-btn w-6 h-6 !p-0"
            :disabled="currentCompPage <= 1"
            @click="currentCompPage--"
          />
          <span class="page-number-indicator text-xs font-mono text-vscode-textMain">{{ currentCompPage }} / {{ totalCompPages }}</span>
          <Button
            v-tooltip.top="'下一頁'"
            icon="pi pi-chevron-right"
            text
            size="small"
            severity="secondary"
            class="pagination-btn w-6 h-6 !p-0"
            :disabled="currentCompPage >= totalCompPages"
            @click="currentCompPage++"
          />
        </div>
      </div>

      <!-- 元件清單表格 (PrimeVue DataTable) -->
      <div class="table-container overflow-x-auto border border-surface-border rounded bg-surface-panel">
        <DataTable
          :value="paginatedComponents"
          data-key="ref_des"
          size="small"
          class="drawer-table w-full text-xs [&_td]:!py-1.5 [&_td]:!px-2.5 [&_th]:!py-1.5 [&_th]:!px-2.5 [&_th]:!bg-surface-header [&_th]:!text-vscode-textSecondary [&_th]:!font-medium"
        >
          <template #empty>
            <div class="empty-table-state p-6 text-center text-vscode-textMuted">
              <i class="pi pi-filter-slash mr-1"></i>無符合篩選條件的元件
            </div>
          </template>

          <Column header="RefDes" style="min-width: 65px">
            <template #body="{ data: comp }">
              <strong class="text-vscode-textHeading font-mono">{{ comp.ref_des }}</strong>
              <span v-if="isKeyIc(comp.ref_des)" class="badge-tag tag-purple ml-1 text-[9px] font-mono px-1 py-0.2 rounded border border-primary/30 bg-primary/10 text-primary" title="核心晶片">Core</span>
            </template>
          </Column>
          <Column header="實體類別" style="min-width: 65px">
            <template #body="{ data: comp }">
              <span class="badge-tag text-[10px] font-medium px-1.5 py-0.2 rounded border" :class="getCategoryTagClass(comp.category)">
                {{ comp.category }}
              </span>
            </template>
          </Column>
          <Column header="細部類型" style="min-width: 75px">
            <template #body="{ data: comp }">
              <span class="text-vscode-textMain">{{ comp.sub_category || '-' }}</span>
            </template>
          </Column>
          <Column header="拓撲角色" style="min-width: 75px">
            <template #body="{ data: comp }">
              <span v-if="(comp.component_role || comp.functional_role) && (comp.component_role || comp.functional_role) !== 'None'" class="badge-tag tag-outline text-[10px] px-1.5 py-0.2 rounded border border-surface-border bg-surface-ground text-vscode-textSecondary">
                {{ comp.component_role || comp.functional_role }}
              </span>
              <span v-else class="text-vscode-textMuted text-xs">-</span>
            </template>
          </Column>
          <Column header="電氣性" style="min-width: 50px">
            <template #body="{ data: comp }">
              <span v-if="comp.is_electrical !== false" class="badge-tag tag-green text-[10px] font-medium px-1.5 py-0.2 rounded border border-primary/30 bg-primary/10 text-primary">
                電氣件
              </span>
              <span v-else class="badge-tag tag-gray text-[10px] px-1.5 py-0.2 rounded border border-surface-border bg-surface-ground text-vscode-textMuted">
                非電氣
              </span>
            </template>
          </Column>
          <Column header="型號 / 數值" style="min-width: 85px">
            <template #body="{ data: comp }">
              <code class="font-mono text-primary">{{ comp.part_value || '-' }}</code>
            </template>
          </Column>
          <Column header="封裝 (Package)" style="min-width: 70px">
            <template #body="{ data: comp }">
              <span class="text-vscode-textMuted text-xs font-mono">{{ comp.package || '-' }}</span>
            </template>
          </Column>
          <Column header="引腳數" style="min-width: 48px">
            <template #body="{ data: comp }">
              <span class="text-vscode-textMain font-mono">{{ comp.pins_count }} pins</span>
            </template>
          </Column>
          <Column header="描述 (Description)" style="min-width: 110px">
            <template #body="{ data: comp }">
              <span class="cell-desc line-clamp-1 text-vscode-textMuted" :title="comp.description || ''">
                {{ comp.description || '-' }}
              </span>
            </template>
          </Column>
        </DataTable>
      </div>
    </div>

    <!-- ================= 頁籤 2: 網路表格與表頭 Filter ================= -->
    <div v-if="currentTab === 'nets'" class="tab-pane-content flex flex-col gap-2">
      <div class="table-filter-toolbar flex items-center gap-2 flex-wrap text-xs">
        <!-- 關鍵字搜尋 -->
        <div class="filter-search-box flex-1 min-w-[200px]">
          <IconField class="w-full">
            <InputIcon class="pi pi-search filter-search-icon text-vscode-textMuted text-xs" />
            <InputText
              v-model="currentNetSearch"
              type="text"
              size="small"
              placeholder="搜尋網路名稱 (Net Name) 或連接元件..."
              class="filter-search-input w-full text-xs"
            />
          </IconField>
        </div>

        <!-- 網路類型篩選 -->
        <Select
          v-model="currentNetTypeFilter"
          :options="netTypeFilterOptions"
          option-label="label"
          option-value="value"
          placeholder="全部"
          size="small"
          class="filter-select text-xs min-w-[120px]"
        />

        <!-- 匯流排協定篩選 -->
        <Select
          v-model="currentNetBusFilter"
          :options="netBusFilterOptions"
          option-label="label"
          option-value="value"
          placeholder="全部匯流排協定"
          size="small"
          class="filter-select text-xs min-w-[140px]"
        />

        <!-- 重設篩選 -->
        <Button
          v-if="hasNetFilters"
          v-tooltip.top="'清除所有篩選條件'"
          icon="pi pi-filter-slash"
          text
          size="small"
          severity="secondary"
          class="btn-clear-filter w-7 h-7 !p-0"
          title="清除篩選"
          @click="clearNetFilters"
        />
      </div>

      <!-- 分頁與筆數統計列 -->
      <div class="table-pagination-bar flex justify-between items-center text-xs text-vscode-textMuted py-0.5">
        <div class="pagination-info">
          顯示 <strong class="text-vscode-textHeading">{{ paginatedNets.length }}</strong> 筆
          <span>
            (篩選結果: {{ filteredNets.length }} / 全部: {{ allNets.length }} 條)
          </span>
        </div>

        <div class="pagination-controls flex items-center gap-1.5">
          <label class="page-size-label text-xs text-vscode-textMuted">每頁:</label>
          <Select
            v-model="currentNetPageSize"
            :options="pageSizeOptions"
            option-label="label"
            option-value="value"
            size="small"
            class="page-size-select text-xs"
          />

          <Button
            v-tooltip.top="'上一頁'"
            icon="pi pi-chevron-left"
            text
            size="small"
            severity="secondary"
            class="pagination-btn w-6 h-6 !p-0"
            :disabled="currentNetPage <= 1"
            @click="currentNetPage--"
          />
          <span class="page-number-indicator text-xs font-mono text-vscode-textMain">{{ currentNetPage }} / {{ totalNetPages }}</span>
          <Button
            v-tooltip.top="'下一頁'"
            icon="pi pi-chevron-right"
            text
            size="small"
            severity="secondary"
            class="pagination-btn w-6 h-6 !p-0"
            :disabled="currentNetPage >= totalNetPages"
            @click="currentNetPage++"
          />
        </div>
      </div>

      <!-- 網路清單表格 (PrimeVue DataTable) -->
      <div class="table-container overflow-x-auto border border-surface-border rounded bg-surface-panel">
        <DataTable
          :value="paginatedNets"
          data-key="net_name"
          size="small"
          class="drawer-table w-full text-xs [&_td]:!py-1.5 [&_td]:!px-2.5 [&_th]:!py-1.5 [&_th]:!px-2.5 [&_th]:!bg-surface-header [&_th]:!text-vscode-textSecondary [&_th]:!font-medium"
        >
          <template #empty>
            <div class="empty-table-state p-6 text-center text-vscode-textMuted">
              <i class="pi pi-filter-slash mr-1"></i>無符合篩選條件的網路
            </div>
          </template>

          <Column header="網路名稱 (Net Name)" style="min-width: 95px">
            <template #body="{ data: net }">
              <code class="font-mono text-vscode-textHeading"><strong>{{ net.net_name }}</strong></code>
            </template>
          </Column>
          <Column header="網路屬性 (Type)" style="min-width: 60px">
            <template #body="{ data: net }">
              <span v-if="net.is_power || net.net_type === 'Power'" class="badge-tag tag-yellow text-[10px] font-medium px-1.5 py-0.2 rounded border border-primary/30 bg-primary/10 text-primary">Power</span>
              <span v-else-if="net.is_ground || net.net_type === 'GND' || net.net_type === 'Ground'" class="badge-tag tag-gray text-[10px] px-1.5 py-0.2 rounded border border-surface-border bg-surface-ground text-vscode-textMuted">GND</span>
              <span v-else-if="net.net_type === 'Differential'" class="badge-tag tag-purple text-[10px] font-medium px-1.5 py-0.2 rounded border border-primary/30 bg-primary/10 text-primary">Differential</span>
              <span v-else-if="net.net_type === 'Bus'" class="badge-tag tag-cyan text-[10px] px-1.5 py-0.2 rounded border border-primary/30 bg-primary/10 text-primary">Bus</span>
              <span v-else-if="net.net_type" class="badge-tag tag-blue text-[10px] px-1.5 py-0.2 rounded border border-surface-border bg-surface-ground text-vscode-textSecondary">{{ net.net_type }}</span>
              <span v-else class="text-vscode-textMuted text-xs">-</span>
            </template>
          </Column>
          <Column header="匯流排協定" style="min-width: 70px">
            <template #body="{ data: net }">
              <span v-if="net.bus_type" class="badge-tag tag-cyan text-[10px] font-mono px-1.5 py-0.2 rounded border border-primary/30 bg-primary/10 text-primary">{{ net.bus_type }}</span>
              <span v-else class="text-vscode-textMuted text-xs">-</span>
            </template>
          </Column>
          <Column header="連接元件數" style="min-width: 55px">
            <template #body="{ data: net }">
              <span class="font-mono text-vscode-textMain">{{ net.connected_components?.length || 0 }} 顆</span>
            </template>
          </Column>
          <Column header="相連元件標籤 (Connected Components)" style="min-width: 175px">
            <template #body="{ data: net }">
              <div class="net-tags-wrapper flex flex-wrap gap-1 items-center">
                <span
                  v-for="c in (net.connected_components || []).slice(0, 6)"
                  :key="c"
                  class="net-tag text-[10px] font-mono px-1.5 py-0.2 rounded bg-surface-ground border border-surface-border text-vscode-textSecondary"
                >
                  {{ c }}
                </span>
                <span
                  v-if="(net.connected_components || []).length > 6"
                  class="net-tag-more text-[10px] font-mono px-1.5 py-0.2 rounded bg-primary/10 border border-primary/30 text-primary cursor-pointer hover:bg-primary/20 transition-colors"
                  @mouseenter="showMorePopup($event, net)"
                  @mouseleave="handleMoreMouseLeave"
                >
                  +{{ (net.connected_components || []).length - 6 }} more
                </span>
              </div>
            </template>
          </Column>
        </DataTable>
      </div>
    </div>

    <!-- 相連元件浮動小窗口 (當滑鼠 overlay 在 +N more 標籤上時顯示所有內容) -->
    <Teleport to="body">
      <div
        v-if="hoveredNet && popupVisible"
        class="net-components-floating-window fixed z-[9999] bg-surface-panel border border-surface-border rounded-md shadow-xl p-2.5 flex flex-col gap-2 max-w-sm"
        :class="`placement-${popupPlacement}`"
        :style="popupPositionStyle"
        @mouseenter="cancelHide"
        @mousemove="cancelHide"
        @mouseleave="handleMoreMouseLeave"
      >
        <div class="popup-header flex justify-between items-center pb-1 border-b border-surface-border text-xs">
          <div class="popup-title flex items-center gap-1.5 font-medium text-vscode-textHeading">
            <i class="pi pi-share-alt popup-icon text-primary text-xs"></i>
            <span>網路 <code class="font-mono text-primary">{{ hoveredNet.net_name }}</code> 相連元件</span>
          </div>
          <div class="popup-header-actions flex items-center gap-1.5">
            <span class="popup-badge text-[10px] px-1.5 py-0.2 rounded bg-primary/10 text-primary font-mono">全數 {{ hoveredNet.connected_components?.length || 0 }} 顆</span>
            <button
              type="button"
              class="popup-close-btn bg-transparent border-0 text-vscode-textMuted hover:text-vscode-textHeading cursor-pointer p-0.5 text-xs transition-colors"
              title="關閉"
              @click.stop="closePopupImmediately"
            >
              <i class="pi pi-times"></i>
            </button>
          </div>
        </div>
        <div class="popup-body flex flex-wrap gap-1 max-h-48 overflow-y-auto p-0.5">
          <span
            v-for="c in (hoveredNet.connected_components || [])"
            :key="c"
            class="net-tag text-[10px] font-mono px-1.5 py-0.2 rounded border"
            :class="isKeyIc(c) ? 'border-primary/40 bg-primary/15 text-primary font-semibold' : 'border-surface-border bg-surface-ground text-vscode-textSecondary'"
            :title="isKeyIc(c) ? '核心晶片 (Key IC)' : ''"
          >
            {{ c }}
          </span>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
/**
 * @file Step2TopologyDrawer.vue
 * @description TaskMonitorView 抽屜 Step 2：線路圖譜拓撲、核心晶片與元件/網路篩選表格 (PrimeVue DataTable/Select/InputText 雙主題版)
 */

import { computed, ref, onMounted, onUnmounted } from 'vue'
import Button from 'primevue/button'
import Select from 'primevue/select'
import InputText from 'primevue/inputtext'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import { fetchLevel2Categories } from '@/services/api'
import type { TaskGraphDetails, TaskSummary, NetDetail } from '@/types/task'

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
  netTypeFilter?: string
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
  netBusFilter: 'all',
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
  (e: 'update:netTypeFilter', val: string): void
  (e: 'update:netBusFilter', val: string): void
  (e: 'update:netPage', val: number): void
  (e: 'update:netPageSize', val: number): void
}>()

const pageSizeOptions = [
  { label: '20', value: 20 },
  { label: '50', value: 50 },
  { label: '100', value: 100 },
  { label: '全部', value: -1 },
]

const electricalFilterOptions = [
  { label: '電氣性: 全部', value: 'all' },
  { label: '僅電氣件', value: 'electrical' },
  { label: '僅非電氣件', value: 'non_electrical' },
]

const defaultL2Categories = ['Bus', 'Power', 'GND', 'Differential', 'Control', 'Clock', 'Analog']
const dynamicL2Categories = ref<string[]>([])

onMounted(async () => {
  try {
    const cats = await fetchLevel2Categories()
    if (cats && cats.length > 0) {
      dynamicL2Categories.value = cats
    }
  } catch (err) {
    console.warn('載入 Level 2 類別清單失敗，回退預設白名單', err)
  }
})

const netTypeFilterOptions = computed(() => {
  const cats = dynamicL2Categories.value.length > 0 ? dynamicL2Categories.value : defaultL2Categories
  return [
    { label: '全部屬性', value: 'all' },
    ...cats.map((c) => ({ label: c, value: c.toLowerCase() })),
    { label: '未分類 (-)', value: 'unclassified' },
  ]
})

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
  get: () => props.netTypeFilter || 'all',
  set: (val) => {
    emit('update:netTypeFilter', val || 'all')
    emit('update:netPage', 1)
  },
})

const currentNetBusFilter = computed({
  get: () => props.netBusFilter || 'all',
  set: (val) => {
    emit('update:netBusFilter', val || 'all')
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

const categoryFilterOptions = computed(() => [
  { label: `全部實體類別 (${availableCategories.value.length})`, value: '' },
  ...availableCategories.value.map((c) => ({ label: c, value: c })),
])

const availableSubCategories = computed(() => {
  const set = new Set<string>()
  allComponents.value.forEach((c) => {
    if (c.sub_category) set.add(c.sub_category)
  })
  return Array.from(set).sort()
})

const subCategoryFilterOptions = computed(() => [
  { label: `全部細部類型 (${availableSubCategories.value.length})`, value: '' },
  ...availableSubCategories.value.map((sc) => ({ label: sc, value: sc })),
])

const availableRoles = computed(() => {
  const set = new Set<string>()
  allComponents.value.forEach((c) => {
    const r = c.component_role || c.functional_role
    if (r && r !== 'None') set.add(r)
  })
  return Array.from(set).sort()
})

const roleFilterOptions = computed(() => [
  { label: `全部拓撲角色 (${availableRoles.value.length})`, value: '' },
  ...availableRoles.value.map((r) => ({ label: r, value: r })),
])

const filteredComponents = computed(() => {
  let list = allComponents.value
  if (props.compCategoryFilter) {
    list = list.filter((c) => c.category === props.compCategoryFilter)
  }
  if (props.compSubCategoryFilter) {
    list = list.filter((c) => c.sub_category === props.compSubCategoryFilter)
  }
  if (props.compRoleFilter) {
    list = list.filter((c) => (c.component_role || c.functional_role) === props.compRoleFilter)
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

const availableNetBuses = computed(() => {
  const set = new Set<string>()
  allNets.value.forEach((n) => {
    if (n.bus_type) set.add(n.bus_type)
  })
  return Array.from(set).sort()
})

const netBusFilterOptions = computed(() => [
  { label: '全部匯流排協定', value: 'all' },
  ...availableNetBuses.value.map((b) => ({ label: b, value: b })),
])

const filteredNets = computed(() => {
  let list = allNets.value
  const f = (props.netTypeFilter || 'all').toLowerCase()
  if (f === 'power') {
    list = list.filter((n) => n.is_power || n.net_type === 'Power')
  } else if (f === 'ground' || f === 'gnd') {
    list = list.filter((n) => n.is_ground || n.net_type === 'GND' || n.net_type === 'Ground')
  } else if (f === 'differential') {
    list = list.filter((n) => n.net_type === 'Differential')
  } else if (f === 'bus') {
    list = list.filter((n) => n.net_type === 'Bus' || !!n.bus_type)
  } else if (f === 'unclassified') {
    list = list.filter((n) => !n.net_type && !n.is_power && !n.is_ground)
  } else if (f && f !== 'all') {
    list = list.filter((n) => n.net_type?.toLowerCase() === f)
  }

  if (props.netBusFilter && props.netBusFilter !== 'all') {
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
  return !!(
    props.netSearch ||
    (props.netTypeFilter && props.netTypeFilter !== 'all') ||
    (props.netBusFilter && props.netBusFilter !== 'all')
  )
})

const clearNetFilters = () => {
  emit('update:netSearch', '')
  emit('update:netTypeFilter', 'all')
  emit('update:netBusFilter', 'all')
  emit('update:netPage', 1)
}

/**
 * 雙色低彩度分類樣式：IC 與 Connector 使用主色藍灰，其餘使用中性暖灰
 */
const getCategoryTagClass = (category: string): string => {
  switch (category) {
    case 'IC':
    case 'Connector':
      return 'text-primary border-primary/30 bg-primary/10'
    default:
      return 'text-vscode-textSecondary border-surface-border bg-surface-ground'
  }
}

const isKeyIc = (refDes: string): boolean => {
  return keyIcsList.value.some((ic) => ic === refDes || ic.startsWith(refDes + ' ') || ic.startsWith(refDes + '('))
}

const hoveredNet = ref<NetDetail | null>(null)
const popupVisible = ref(false)
const popupPlacement = ref<'below' | 'above'>('below')
const popupPosition = ref({ top: 0, left: 0 })
let hideTimer: ReturnType<typeof setTimeout> | null = null

const popupPositionStyle = computed(() => ({
  top: `${popupPosition.value.top}px`,
  left: `${popupPosition.value.left}px`,
}))

const showMorePopup = (event: MouseEvent, net: NetDetail) => {
  if (hideTimer) {
    clearTimeout(hideTimer)
    hideTimer = null
  }
  hoveredNet.value = net

  const target = event.currentTarget as HTMLElement | null
  if (!target) return

  const rect = target.getBoundingClientRect()
  const popupWidth = 340
  const estimatedHeight = 220

  let left = rect.left
  if (left + popupWidth > window.innerWidth - 16) {
    left = Math.max(16, window.innerWidth - popupWidth - 16)
  }

  let isAbove = false
  let top = rect.bottom + 4
  if (top + estimatedHeight > window.innerHeight - 16 && rect.top > estimatedHeight + 16) {
    top = rect.top - estimatedHeight - 4
    isAbove = true
  }
  popupPlacement.value = isAbove ? 'above' : 'below'

  popupPosition.value = { top, left }
  popupVisible.value = true
}

const handleMoreMouseLeave = () => {
  if (hideTimer) {
    clearTimeout(hideTimer)
  }
  hideTimer = setTimeout(() => {
    popupVisible.value = false
    hoveredNet.value = null
  }, 300)
}

const cancelHide = () => {
  if (hideTimer) {
    clearTimeout(hideTimer)
    hideTimer = null
  }
}

const closePopupImmediately = () => {
  if (hideTimer) {
    clearTimeout(hideTimer)
    hideTimer = null
  }
  popupVisible.value = false
  hoveredNet.value = null
}

const onWindowScroll = (event: Event) => {
  const target = event.target as HTMLElement | null
  if (target) {
    if (
      target.classList?.contains('popup-body') ||
      target.classList?.contains('net-components-floating-window') ||
      target.closest?.('.net-components-floating-window')
    ) {
      return
    }
  }
  closePopupImmediately()
}

onMounted(() => {
  window.addEventListener('scroll', onWindowScroll, true)
})

onUnmounted(() => {
  window.removeEventListener('scroll', onWindowScroll, true)
  if (hideTimer) {
    clearTimeout(hideTimer)
  }
})
</script>
