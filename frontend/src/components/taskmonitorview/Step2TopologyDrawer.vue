<template>
  <div class="drawer-step-content flex flex-col gap-3.5">
    <!-- 拓撲數據統計 Banner -->
    <div class="drawer-stat-banner grid grid-cols-2 sm:grid-cols-4 gap-2.5 bg-surface-card border border-surface-border rounded-md p-3">
      <div class="banner-stat flex flex-col items-center text-center">
        <span class="stat-num text-lg font-bold text-surface-900 dark:text-surface-0">{{ graphDetails?.components_count ?? preSummary?.component_count ?? 0 }}</span>
        <span class="stat-name text-xs text-surface-400">元件總數</span>
      </div>
      <div class="banner-stat flex flex-col items-center text-center">
        <span class="stat-num text-lg font-bold text-surface-900 dark:text-surface-0">{{ graphDetails?.nets_count ?? preSummary?.net_count ?? 0 }}</span>
        <span class="stat-name text-xs text-surface-400">網路 (Net) 數</span>
      </div>
      <div class="banner-stat flex flex-col items-center text-center">
        <span class="stat-num text-lg font-bold text-surface-900 dark:text-surface-0">{{ graphDetails?.pins_count ?? 0 }}</span>
        <span class="stat-name text-xs text-surface-400">引腳連接 (Pin) 數</span>
      </div>
      <div class="banner-stat flex flex-col items-center text-center">
        <span class="stat-num text-lg font-bold text-sky-400">{{ detectedBuses.length }}</span>
        <span class="stat-name text-xs text-surface-400">偵測匯流排</span>
      </div>
    </div>

    <!-- 匯流排清單 -->
    <div class="chip-row flex items-center gap-2 flex-wrap text-xs">
      <span class="chip-label text-surface-400 font-medium">匯流排種類:</span>
      <span v-if="detectedBuses.length === 0" class="text-surface-400 text-xs">(無)</span>
      <span v-for="bus in detectedBuses" :key="bus" class="badge-tag tag-cyan text-[11px] font-semibold px-2 py-0.5 rounded border border-sky-400/30 bg-sky-500/10 text-sky-400">{{ bus }}</span>
    </div>

    <!-- 核心晶片與控制器 -->
    <div class="chip-row flex items-center gap-2 flex-wrap text-xs">
      <span class="chip-label text-surface-400 font-medium">核心晶片與控制器 (Key ICs):</span>
      <span v-if="keyIcsList.length === 0" class="text-surface-400 text-xs">(無)</span>
      <span v-for="ic in keyIcsList" :key="ic" class="badge-tag tag-purple text-[11px] font-semibold px-2 py-0.5 rounded border border-purple-400/30 bg-purple-500/10 text-purple-400">{{ ic }}</span>
    </div>

    <!-- 主要介面連接器 -->
    <div v-if="keyConnectorsList.length > 0" class="chip-row flex items-center gap-2 flex-wrap text-xs">
      <span class="chip-label text-surface-400 font-medium">主要介面連接器 (Key Connectors):</span>
      <span v-for="conn in keyConnectorsList" :key="conn" class="badge-tag tag-blue text-[11px] font-semibold px-2 py-0.5 rounded border border-blue-400/30 bg-blue-500/10 text-blue-400">{{ conn }}</span>
    </div>

    <!-- 晶片功能清單 (IC Directory by Role) -->
    <div v-if="Object.keys(icDirectoryByRole).length > 0" class="role-directory-card p-3 rounded-md bg-surface-ground/50 border border-surface-border flex flex-col gap-2">
      <h4 class="content-subtitle m-0 text-xs font-semibold text-surface-200">晶片功能清單 (IC Directory by Role)</h4>
      <div v-for="(ics, role) in icDirectoryByRole" :key="role" class="chip-row role-row flex items-center gap-2 flex-wrap text-xs">
        <span class="chip-label role-label text-surface-400">{{ role }}:</span>
        <span v-for="ic in ics" :key="ic" class="badge-tag tag-outline text-[11px] px-2 py-0.5 rounded border border-surface-border bg-surface-card text-surface-300">{{ ic }}</span>
      </div>
    </div>

    <!-- 非電氣/機構件分流 -->
    <div v-if="nonElectricalList.length > 0" class="chip-row flex items-center gap-2 flex-wrap text-xs">
      <span class="chip-label text-surface-400 font-medium">非電氣/機構件分流 (Non-Electrical):</span>
      <span class="badge-tag tag-gray text-[11px] px-2 py-0.5 rounded border border-surface-border bg-surface-ground text-surface-400">已隔離 {{ nonElectricalList.length }} 顆機構/測試點件</span>
    </div>

    <!-- 子頁籤導覽 (Sub-Tabs) -->
    <div class="step2-subtabs flex gap-2 border-b border-surface-border pb-1">
      <button
        type="button"
        class="subtab-btn flex items-center gap-1.5 px-3 py-1.5 rounded-t text-xs font-semibold cursor-pointer border-0 transition-colors"
        :class="currentTab === 'components' ? 'bg-primary/20 text-primary-contrast dark:text-primary-300 border-b-2 border-primary' : 'bg-transparent text-surface-400 hover:text-surface-100 hover:bg-surface-hover'"
        @click="currentTab = 'components'"
      >
        <i class="pi pi-box mr-1"></i>
        <span>元件清單 (Components)</span>
        <span class="subtab-badge text-[10px] px-1.5 py-0.2 rounded-full bg-surface-ground text-surface-400 font-mono">{{ allComponents.length }}</span>
      </button>
      <button
        type="button"
        class="subtab-btn flex items-center gap-1.5 px-3 py-1.5 rounded-t text-xs font-semibold cursor-pointer border-0 transition-colors"
        :class="currentTab === 'nets' ? 'bg-primary/20 text-primary-contrast dark:text-primary-300 border-b-2 border-primary' : 'bg-transparent text-surface-400 hover:text-surface-100 hover:bg-surface-hover'"
        @click="currentTab = 'nets'"
      >
        <i class="pi pi-share-alt mr-1"></i>
        <span>網路清單 (Nets)</span>
        <span class="subtab-badge text-[10px] px-1.5 py-0.2 rounded-full bg-surface-ground text-surface-400 font-mono">{{ allNets.length }}</span>
      </button>
    </div>

    <!-- ================= 頁籤 1: 元件表格與表頭 Filter ================= -->
    <div v-if="currentTab === 'components'" class="tab-pane-content flex flex-col gap-2.5">
      <div class="table-filter-toolbar flex items-center gap-2 flex-wrap text-xs">
        <!-- 關鍵字搜尋 -->
        <div class="filter-search-box relative flex items-center flex-1 min-w-[200px]">
          <i class="pi pi-search filter-search-icon absolute left-2.5 text-surface-400 text-xs pointer-events-none"></i>
          <input
            v-model="currentCompSearch"
            type="text"
            placeholder="搜尋 RefDes / 型號 / 封裝 / 描述..."
            class="filter-search-input w-full pl-7 pr-3 py-1 text-xs rounded border border-surface-border bg-surface-ground text-surface-900 dark:text-surface-100 placeholder:text-surface-500 focus:outline-none focus:border-primary"
          />
        </div>

        <!-- 實體類別篩選 -->
        <select v-model="currentCompCategoryFilter" class="filter-select px-2.5 py-1 text-xs rounded border border-surface-border bg-surface-ground text-surface-900 dark:text-surface-100 focus:outline-none focus:border-primary cursor-pointer">
          <option value="">全部實體類別 ({{ availableCategories.length }})</option>
          <option v-for="cat in availableCategories" :key="cat" :value="cat">
            {{ cat }}
          </option>
        </select>

        <!-- 細部類型篩選 -->
        <select v-model="currentCompSubCategoryFilter" class="filter-select px-2.5 py-1 text-xs rounded border border-surface-border bg-surface-ground text-surface-900 dark:text-surface-100 focus:outline-none focus:border-primary cursor-pointer">
          <option value="">全部細部類型 ({{ availableSubCategories.length }})</option>
          <option v-for="sc in availableSubCategories" :key="sc" :value="sc">
            {{ sc }}
          </option>
        </select>

        <!-- 拓撲角色篩選 -->
        <select v-model="currentCompRoleFilter" class="filter-select px-2.5 py-1 text-xs rounded border border-surface-border bg-surface-ground text-surface-900 dark:text-surface-100 focus:outline-none focus:border-primary cursor-pointer">
          <option value="">全部拓撲角色 ({{ availableRoles.length }})</option>
          <option v-for="r in availableRoles" :key="r" :value="r">
            {{ r }}
          </option>
        </select>

        <!-- 電氣性篩選 -->
        <select v-model="currentCompElectricalFilter" class="filter-select px-2.5 py-1 text-xs rounded border border-surface-border bg-surface-ground text-surface-900 dark:text-surface-100 focus:outline-none focus:border-primary cursor-pointer">
          <option value="all">電氣性: 全部</option>
          <option value="electrical">僅電氣件</option>
          <option value="non_electrical">僅非電氣件</option>
        </select>

        <!-- 重設篩選 -->
        <button v-if="hasCompFilters" type="button" class="btn-clear-filter px-2 py-1 text-xs rounded border border-surface-border bg-surface-card text-surface-400 hover:text-surface-100 cursor-pointer" @click="clearCompFilters">
          <i class="pi pi-times mr-1"></i>清除篩選
        </button>
      </div>

      <!-- 分頁與筆數統計列 -->
      <div class="table-pagination-bar flex justify-between items-center text-xs text-surface-400 py-1">
        <div class="pagination-info">
          顯示 <strong>{{ paginatedComponents.length }}</strong> 筆
          <span class="text-surface-400">
            (篩選結果: {{ filteredComponents.length }} / 全部: {{ allComponents.length }} 顆)
          </span>
        </div>

        <div class="pagination-controls flex items-center gap-2">
          <label class="page-size-label text-xs">每頁:</label>
          <select v-model.number="currentCompPageSize" class="page-size-select px-1.5 py-0.5 rounded border border-surface-border bg-surface-ground text-surface-900 dark:text-surface-100 text-xs">
            <option :value="20">20</option>
            <option :value="50">50</option>
            <option :value="100">100</option>
            <option :value="-1">全部</option>
          </select>

          <button
            type="button"
            class="pagination-btn px-2 py-0.5 rounded border border-surface-border bg-surface-card text-surface-300 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-surface-hover cursor-pointer text-xs"
            :disabled="currentCompPage <= 1"
            @click="currentCompPage--"
          >
            上一頁
          </button>
          <span class="page-number-indicator text-xs font-mono">第 {{ currentCompPage }} / {{ totalCompPages }} 頁</span>
          <button
            type="button"
            class="pagination-btn px-2 py-0.5 rounded border border-surface-border bg-surface-card text-surface-300 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-surface-hover cursor-pointer text-xs"
            :disabled="currentCompPage >= totalCompPages"
            @click="currentCompPage++"
          >
            下一頁
          </button>
        </div>
      </div>

      <!-- 元件清單表格 -->
      <div class="table-container overflow-x-auto border border-surface-border rounded-md">
        <table class="drawer-table w-full text-left border-collapse text-xs">
          <thead>
            <tr class="bg-surface-ground border-b border-surface-border">
              <th class="p-2 font-semibold text-surface-300" style="min-width: 65px;">RefDes</th>
              <th class="p-2 font-semibold text-surface-300" style="min-width: 65px;">實體類別</th>
              <th class="p-2 font-semibold text-surface-300" style="min-width: 75px;">細部類型</th>
              <th class="p-2 font-semibold text-surface-300" style="min-width: 75px;">拓撲角色</th>
              <th class="p-2 font-semibold text-surface-300" style="min-width: 50px;">電氣性</th>
              <th class="p-2 font-semibold text-surface-300" style="min-width: 85px;">型號 / 數值</th>
              <th class="p-2 font-semibold text-surface-300" style="min-width: 70px;">封裝 (Package)</th>
              <th class="p-2 font-semibold text-surface-300" style="min-width: 48px;">引腳數</th>
              <th class="p-2 font-semibold text-surface-300" style="min-width: 110px;">描述 (Description)</th>
            </tr>
          </thead>
          <tbody v-if="paginatedComponents.length > 0">
            <tr v-for="comp in paginatedComponents" :key="comp.ref_des" class="border-b border-surface-border/50 hover:bg-surface-hover/30 transition-colors">
              <td class="p-2">
                <strong>{{ comp.ref_des }}</strong>
                <span v-if="isKeyIc(comp.ref_des)" class="badge-tag tag-purple ml-1 text-[10px] font-semibold px-1 py-0.2 rounded border border-purple-400/30 bg-purple-500/10 text-purple-400" title="核心晶片">Core</span>
              </td>
              <td class="p-2">
                <span class="badge-tag text-[11px] font-semibold px-2 py-0.5 rounded border" :class="getCategoryTagClass(comp.category)">
                  {{ comp.category }}
                </span>
              </td>
              <td class="p-2">{{ comp.sub_category || '-' }}</td>
              <td class="p-2">
                <span v-if="comp.functional_role && comp.functional_role !== 'None'" class="badge-tag tag-outline text-[11px] px-2 py-0.5 rounded border border-surface-border bg-surface-card text-surface-300">
                  {{ comp.functional_role }}
                </span>
                <span v-else class="text-surface-400 text-xs">-</span>
              </td>
              <td class="p-2">
                <span v-if="comp.is_electrical !== false" class="badge-tag tag-green text-[11px] font-semibold px-2 py-0.5 rounded border border-green-400/30 bg-green-500/10 text-green-400">
                  電氣件
                </span>
                <span v-else class="badge-tag tag-gray text-[11px] px-2 py-0.5 rounded border border-surface-border bg-surface-ground text-surface-400">
                  非電氣
                </span>
              </td>
              <td class="p-2"><code class="font-mono text-sky-300">{{ comp.part_value || '-' }}</code></td>
              <td class="p-2"><span class="text-surface-400 text-xs">{{ comp.package || '-' }}</span></td>
              <td class="p-2">{{ comp.pins_count }} pins</td>
              <td class="p-2">
                <span class="cell-desc line-clamp-1 text-surface-400" :title="comp.description || ''">
                  {{ comp.description || '-' }}
                </span>
              </td>
            </tr>
          </tbody>
          <tbody v-else>
            <tr>
              <td colspan="9" class="empty-table-state p-6 text-center text-surface-400">
                <i class="pi pi-filter-slash mr-1"></i>無符合篩選條件的元件
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- ================= 頁籤 2: 網路表格與表頭 Filter ================= -->
    <div v-if="currentTab === 'nets'" class="tab-pane-content flex flex-col gap-2.5">
      <div class="table-filter-toolbar flex items-center gap-2 flex-wrap text-xs">
        <!-- 關鍵字搜尋 -->
        <div class="filter-search-box relative flex items-center flex-1 min-w-[200px]">
          <i class="pi pi-search filter-search-icon absolute left-2.5 text-surface-400 text-xs pointer-events-none"></i>
          <input
            v-model="currentNetSearch"
            type="text"
            placeholder="搜尋網路名稱 (Net Name) 或連接元件..."
            class="filter-search-input w-full pl-7 pr-3 py-1 text-xs rounded border border-surface-border bg-surface-ground text-surface-900 dark:text-surface-100 placeholder:text-surface-500 focus:outline-none focus:border-primary"
          />
        </div>

        <!-- 網路類型篩選 -->
        <select v-model="currentNetTypeFilter" class="filter-select px-2.5 py-1 text-xs rounded border border-surface-border bg-surface-ground text-surface-900 dark:text-surface-100 focus:outline-none focus:border-primary cursor-pointer">
          <option value="all">全部網路類型</option>
          <option value="power">僅電源網路 (Power)</option>
          <option value="ground">僅接地網路 (Ground)</option>
          <option value="bus">僅匯流排網路 (Bus)</option>
          <option value="signal">僅一般訊號網路 (Signal)</option>
        </select>

        <!-- 匯流排協定篩選 -->
        <select v-model="currentNetBusFilter" class="filter-select px-2.5 py-1 text-xs rounded border border-surface-border bg-surface-ground text-surface-900 dark:text-surface-100 focus:outline-none focus:border-primary cursor-pointer">
          <option value="">全部匯流排協定 ({{ availableNetBuses.length }})</option>
          <option v-for="b in availableNetBuses" :key="b" :value="b">
            {{ b }}
          </option>
        </select>

        <!-- 重設篩選 -->
        <button v-if="hasNetFilters" type="button" class="btn-clear-filter px-2 py-1 text-xs rounded border border-surface-border bg-surface-card text-surface-400 hover:text-surface-100 cursor-pointer" @click="clearNetFilters">
          <i class="pi pi-times mr-1"></i>清除篩選
        </button>
      </div>

      <!-- 分頁與筆數統計列 -->
      <div class="table-pagination-bar flex justify-between items-center text-xs text-surface-400 py-1">
        <div class="pagination-info">
          顯示 <strong>{{ paginatedNets.length }}</strong> 筆
          <span class="text-surface-400">
            (篩選結果: {{ filteredNets.length }} / 全部: {{ allNets.length }} 條)
          </span>
        </div>

        <div class="pagination-controls flex items-center gap-2">
          <label class="page-size-label text-xs">每頁:</label>
          <select v-model.number="currentNetPageSize" class="page-size-select px-1.5 py-0.5 rounded border border-surface-border bg-surface-ground text-surface-900 dark:text-surface-100 text-xs">
            <option :value="20">20</option>
            <option :value="50">50</option>
            <option :value="100">100</option>
            <option :value="-1">全部</option>
          </select>

          <button
            type="button"
            class="pagination-btn px-2 py-0.5 rounded border border-surface-border bg-surface-card text-surface-300 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-surface-hover cursor-pointer text-xs"
            :disabled="currentNetPage <= 1"
            @click="currentNetPage--"
          >
            上一頁
          </button>
          <span class="page-number-indicator text-xs font-mono">第 {{ currentNetPage }} / {{ totalNetPages }} 頁</span>
          <button
            type="button"
            class="pagination-btn px-2 py-0.5 rounded border border-surface-border bg-surface-card text-surface-300 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-surface-hover cursor-pointer text-xs"
            :disabled="currentNetPage >= totalNetPages"
            @click="currentNetPage++"
          >
            下一頁
          </button>
        </div>
      </div>

      <!-- 網路清單表格 -->
      <div class="table-container overflow-x-auto border border-surface-border rounded-md">
        <table class="drawer-table w-full text-left border-collapse text-xs">
          <thead>
            <tr class="bg-surface-ground border-b border-surface-border">
              <th class="p-2 font-semibold text-surface-300" style="min-width: 95px;">網路名稱 (Net Name)</th>
              <th class="p-2 font-semibold text-surface-300" style="min-width: 60px;">網路屬性 (Type)</th>
              <th class="p-2 font-semibold text-surface-300" style="min-width: 70px;">匯流排協定</th>
              <th class="p-2 font-semibold text-surface-300" style="min-width: 55px;">連接元件數</th>
              <th class="p-2 font-semibold text-surface-300" style="min-width: 175px;">相連元件標籤 (Connected Components)</th>
            </tr>
          </thead>
          <tbody v-if="paginatedNets.length > 0">
            <tr v-for="net in paginatedNets" :key="net.net_name" class="border-b border-surface-border/50 hover:bg-surface-hover/30 transition-colors">
              <td class="p-2"><code class="font-mono text-surface-100"><strong>{{ net.net_name }}</strong></code></td>
              <td class="p-2">
                <span v-if="net.is_power" class="badge-tag tag-yellow text-[11px] font-semibold px-2 py-0.5 rounded border border-amber-400/30 bg-amber-500/10 text-amber-400">電源</span>
                <span v-if="net.is_ground" class="badge-tag tag-gray text-[11px] px-2 py-0.5 rounded border border-surface-border bg-surface-ground text-surface-400">接地</span>
                <span v-if="net.bus_type" class="badge-tag tag-cyan text-[11px] font-semibold px-2 py-0.5 rounded border border-sky-400/30 bg-sky-500/10 text-sky-400">{{ net.bus_type }}</span>
                <span v-if="!net.is_power && !net.is_ground && !net.bus_type" class="badge-tag tag-blue text-[11px] font-semibold px-2 py-0.5 rounded border border-blue-400/30 bg-blue-500/10 text-blue-400">訊號</span>
              </td>
              <td class="p-2">
                <span v-if="net.bus_type" class="badge-tag tag-cyan text-[11px] font-semibold px-2 py-0.5 rounded border border-sky-400/30 bg-sky-500/10 text-sky-400">{{ net.bus_type }}</span>
                <span v-else class="text-surface-400 text-xs">-</span>
              </td>
              <td class="p-2">{{ net.connected_components?.length || 0 }} 顆</td>
              <td class="p-2">
                <div class="net-tags-wrapper flex flex-wrap gap-1 items-center">
                  <span
                    v-for="c in (net.connected_components || []).slice(0, 6)"
                    :key="c"
                    class="net-tag text-[10px] font-mono px-1.5 py-0.5 rounded bg-surface-ground border border-surface-border text-surface-300"
                  >
                    {{ c }}
                  </span>
                  <span
                    v-if="(net.connected_components || []).length > 6"
                    class="net-tag-more text-[10px] font-mono px-1.5 py-0.5 rounded bg-primary/10 border border-primary/30 text-primary cursor-pointer hover:bg-primary/20 transition-colors"
                    @mouseenter="showMorePopup($event, net)"
                    @mouseleave="handleMoreMouseLeave"
                  >
                    +{{ (net.connected_components || []).length - 6 }} more
                  </span>
                </div>
              </td>
            </tr>
          </tbody>
          <tbody v-else>
            <tr>
              <td colspan="5" class="empty-table-state p-6 text-center text-surface-400">
                <i class="pi pi-filter-slash mr-1"></i>無符合篩選條件的網路
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 相連元件浮動小窗口 (當滑鼠 overlay 在 +N more 標籤上時顯示所有內容) -->
    <Teleport to="body">
      <div
        v-if="hoveredNet && popupVisible"
        class="net-components-floating-window fixed z-[9999] bg-surface-card border border-surface-border rounded-lg shadow-2xl p-3 flex flex-col gap-2 max-w-sm"
        :class="`placement-${popupPlacement}`"
        :style="popupPositionStyle"
        @mouseenter="cancelHide"
        @mousemove="cancelHide"
        @mouseleave="handleMoreMouseLeave"
      >
        <div class="popup-header flex justify-between items-center pb-1.5 border-b border-surface-border text-xs">
          <div class="popup-title flex items-center gap-1.5 font-semibold text-surface-900 dark:text-surface-0">
            <i class="pi pi-share-alt popup-icon text-sky-400"></i>
            <span>網路 <code class="font-mono text-sky-300">{{ hoveredNet.net_name }}</code> 相連元件</span>
          </div>
          <div class="popup-header-actions flex items-center gap-2">
            <span class="popup-badge text-[10px] px-1.5 py-0.5 rounded bg-primary/10 text-primary font-mono">全數 {{ hoveredNet.connected_components?.length || 0 }} 顆</span>
            <button
              type="button"
              class="popup-close-btn bg-transparent border-0 text-surface-400 hover:text-surface-100 cursor-pointer p-0.5 text-xs transition-colors"
              title="關閉"
              @click.stop="closePopupImmediately"
            >
              <i class="pi pi-times"></i>
            </button>
          </div>
        </div>
        <div class="popup-body flex flex-wrap gap-1 max-h-48 overflow-y-auto p-1">
          <span
            v-for="c in (hoveredNet.connected_components || [])"
            :key="c"
            class="net-tag text-[10px] font-mono px-1.5 py-0.5 rounded border"
            :class="isKeyIc(c) ? 'border-purple-400/40 bg-purple-500/15 text-purple-300 font-bold' : 'border-surface-border bg-surface-ground text-surface-300'"
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
 * @description TaskMonitorView 抽屜 Step 2：線路圖譜拓撲、核心晶片與元件/網路篩選表格
 */

import { computed, ref, onMounted, onUnmounted } from 'vue'
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
      return 'text-purple-400 border-purple-400/30 bg-purple-500/10'
    case 'Passive':
      return 'text-blue-400 border-blue-400/30 bg-blue-500/10'
    case 'Discrete':
      return 'text-sky-400 border-sky-400/30 bg-sky-500/10'
    case 'Connector':
      return 'text-green-400 border-green-400/30 bg-green-500/10'
    case 'NonElectrical':
      return 'text-surface-400 border-surface-border bg-surface-ground'
    case 'Electromechanical':
      return 'text-orange-400 border-orange-400/30 bg-orange-500/10'
    default:
      return 'text-surface-300 border-surface-border bg-surface-card'
  }
}

const isKeyIc = (refDes: string): boolean => {
  return keyIcsList.value.some((ic) => ic === refDes || ic.startsWith(refDes + ' ') || ic.startsWith(refDes + '('))
}

// 浮動小窗口狀態管理 (相連元件 +more 標籤 overlay)
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

  // 計算水平位置，避免超出視窗右邊界
  let left = rect.left
  if (left + popupWidth > window.innerWidth - 16) {
    left = Math.max(16, window.innerWidth - popupWidth - 16)
  }

  // 計算垂直位置，若下方空間不足則顯示在上方
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
  // 檢查滾動事件是否發生於浮動小窗口內部；若是浮動小窗口本身的滾動條滾動，則不觸發關閉！
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
