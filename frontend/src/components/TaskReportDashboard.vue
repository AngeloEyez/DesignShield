<template>
  <div class="task-report-dashboard flex flex-col gap-2.5 text-vscode-textMain font-sans">
    <!-- 0. BOM Config 切換橫幅 (當存在多個 BOM Config 時顯示) -->
    <div
      v-if="availableConfigs.length > 0"
      class="bom-config-filter-group flex items-center justify-between gap-2 px-3 py-1.5 rounded bg-surface-panel border border-surface-border flex-wrap"
    >
      <div class="flex items-center gap-1.5 text-xs font-medium text-vscode-textSecondary">
        <i class="pi pi-sliders-h text-primary text-xs"></i>
        <span>BOM 組態檢視：</span>
      </div>
      <div class="flex items-center gap-1.5 flex-wrap">
        <button
          v-for="cfgName in availableConfigs"
          :key="cfgName"
          type="button"
          class="bom-config-filter-btn px-2.5 py-1 rounded text-xs font-medium cursor-pointer transition-all flex items-center gap-1.5 border"
          :class="getBomConfigBtnClass(cfgName)"
          @click="selectBomConfig(cfgName)"
        >
          <span>{{ cfgName }}</span>
          <span
            v-if="hasConfigFail(cfgName)"
            class="fail-badge-indicator px-1 py-0.2 rounded text-[10px] bg-black/25 text-white font-mono"
          >
            FAIL ({{ getConfigFailCount(cfgName) }})
          </span>
          <span
            v-else
            class="px-1 py-0.2 rounded text-[10px] font-mono font-medium"
            :class="selectedBomConfig === cfgName ? 'bg-white/20 text-white' : 'bg-surface-ground text-emerald-600 dark:text-emerald-400'"
          >
            PASS
          </span>
        </button>
      </div>
    </div>

    <!-- 1. 頂部緊湊 40px 單行關鍵指標橫條 (Compact Metric Strip) -->
    <div class="summary-cards-grid grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 divide-x divide-surface-border border border-surface-border rounded bg-surface-panel overflow-hidden">
      <!-- 總檢驗規則數 -->
      <div
        v-tooltip.top="'點擊顯示全部規則：已執行之自動化檢查項目總數'"
        class="summary-card card-total px-3 py-2 flex items-center justify-between gap-2 cursor-pointer transition-colors hover:bg-surface-hover"
        @click="selectedStatus = 'ALL'"
      >
        <div class="flex items-center gap-1.5 min-w-0">
          <i class="pi pi-list-check text-xs text-primary shrink-0"></i>
          <span class="card-label text-[11px] font-medium text-vscode-textMuted truncate">總檢查規則</span>
        </div>
        <div class="card-number text-sm font-semibold text-vscode-textHeading font-mono shrink-0">
          {{ activeSummary.total_rules_checked }}
        </div>
      </div>

      <!-- 通過數 (PASS) -->
      <div
        v-tooltip.top="'點擊篩選：全數符合硬體設計規範之項目'"
        class="summary-card card-pass px-3 py-2 flex items-center justify-between gap-2 cursor-pointer transition-colors hover:bg-surface-hover"
        :class="selectedStatus === 'PASS' ? 'bg-emerald-500/10' : ''"
        @click="toggleStatusFilter('PASS')"
      >
        <div class="flex items-center gap-1.5 min-w-0">
          <i class="pi pi-check-circle text-xs text-emerald-600 dark:text-emerald-500 shrink-0"></i>
          <span class="card-label text-[11px] font-medium text-vscode-textMuted truncate">通過項目 (PASS)</span>
        </div>
        <div class="card-number text-sm font-semibold text-emerald-600 dark:text-emerald-500 font-mono shrink-0">
          {{ activeSummary.pass_count }}
        </div>
      </div>

      <!-- 違規數 (FAIL) -->
      <div
        v-tooltip.top="'點擊篩選：需工程師優先修正之硬體缺陷'"
        class="summary-card card-fail px-3 py-2 flex items-center justify-between gap-2 cursor-pointer transition-colors hover:bg-surface-hover"
        :class="selectedStatus === 'FAIL' ? 'bg-red-500/10' : ''"
        @click="toggleStatusFilter('FAIL')"
      >
        <div class="flex items-center gap-1.5 min-w-0">
          <i class="pi pi-times-circle text-xs text-red-600 dark:text-red-500 shrink-0"></i>
          <span class="card-label text-[11px] font-medium text-vscode-textMuted truncate">違規項目 (FAIL)</span>
        </div>
        <div class="card-number text-sm font-semibold text-red-600 dark:text-red-500 font-mono shrink-0">
          {{ activeSummary.fail_count }}
        </div>
      </div>

      <!-- 警告數 (WARNING) -->
      <div
        v-tooltip.top="'點擊篩選：潛在設計風險與人工複核建議'"
        class="summary-card card-warning px-3 py-2 flex items-center justify-between gap-2 cursor-pointer transition-colors hover:bg-surface-hover"
        :class="selectedStatus === 'WARNING' ? 'bg-amber-500/10' : ''"
        @click="toggleStatusFilter('WARNING')"
      >
        <div class="flex items-center gap-1.5 min-w-0">
          <i class="pi pi-exclamation-triangle text-xs text-amber-600 dark:text-amber-500 shrink-0"></i>
          <span class="card-label text-[11px] font-medium text-vscode-textMuted truncate">警告 (WARN)</span>
        </div>
        <div class="card-number text-sm font-semibold text-amber-600 dark:text-amber-500 font-mono shrink-0">
          {{ activeSummary.warning_count }}
        </div>
      </div>

      <!-- 略過數 (SKIPPED) -->
      <div
        v-tooltip.top="'點擊篩選：未觸發前置條件之略過規則'"
        class="summary-card card-skipped px-3 py-2 flex items-center justify-between gap-2 cursor-pointer transition-colors hover:bg-surface-hover"
        :class="selectedStatus === 'SKIPPED' ? 'bg-surface-card' : ''"
        @click="toggleStatusFilter('SKIPPED')"
      >
        <div class="flex items-center gap-1.5 min-w-0">
          <i class="pi pi-minus-circle text-xs text-vscode-textMuted shrink-0"></i>
          <span class="card-label text-[11px] font-medium text-vscode-textMuted truncate">略過 (SKIP)</span>
        </div>
        <div class="card-number text-sm font-semibold text-vscode-textSecondary font-mono shrink-0">
          {{ activeSummary.skip_count || 0 }}
        </div>
      </div>

      <!-- 整體合規通過率 -->
      <div
        v-tooltip.top="`整體通過率 ${formattedPassRate}%`"
        class="summary-card card-rate px-3 py-2 flex items-center justify-between gap-2"
      >
        <div class="flex items-center gap-1.5 min-w-0">
          <i class="pi pi-chart-pie text-xs text-primary shrink-0"></i>
          <span class="card-label text-[11px] font-medium text-vscode-textMuted truncate">整體通過率</span>
        </div>
        <div class="card-number text-sm font-semibold font-mono shrink-0" :class="passRateTextClass">
          {{ formattedPassRate }}%
        </div>
      </div>
    </div>

    <!-- 2. 各領域分類健康度橫條 (緊湊單列區塊) -->
    <div v-if="categoryEntries.length > 0" class="category-health-panel px-3 py-2 rounded bg-surface-panel border border-surface-border">
      <div class="flex items-center justify-between mb-1.5">
        <div class="section-title text-xs font-semibold text-vscode-textHeading flex items-center gap-1.5">
          <i class="pi pi-sitemap text-primary text-xs"></i>
          <span>各領域規範檢驗分佈</span>
        </div>
        <span class="text-[11px] text-vscode-textMuted">點擊分類可直接篩選明細</span>
      </div>
      <div class="category-bars-grid grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
        <div
          v-for="[catName, stats] in categoryEntries"
          :key="catName"
          class="category-bar-item px-2.5 py-1.5 rounded bg-surface-card border cursor-pointer transition-colors"
          :class="selectedCategory === catName ? 'border-primary bg-primary/10' : 'border-surface-border hover:border-surface-border-light'"
          @click="toggleCategoryFilter(catName)"
        >
          <div class="cat-header flex justify-between items-center mb-1 gap-2">
            <span class="cat-name text-xs font-semibold text-vscode-textHeading truncate">{{ catName }}</span>
            <div class="cat-badges flex gap-1 text-[10px] font-mono shrink-0">
              <span v-if="stats.fail > 0" class="badge-fail px-1 py-0.2 rounded bg-red-500/15 text-red-600 dark:text-red-400 font-semibold">
                {{ stats.fail }} FAIL
              </span>
              <span v-if="stats.warning > 0" class="badge-warn px-1 py-0.2 rounded bg-amber-500/15 text-amber-600 dark:text-amber-400 font-semibold">
                {{ stats.warning }} WARN
              </span>
              <span class="badge-pass px-1 py-0.2 rounded bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 font-semibold">
                {{ stats.pass }} PASS
              </span>
              <span v-if="stats.skip && stats.skip > 0" class="badge-skip px-1 py-0.2 rounded bg-surface-ground text-vscode-textMuted border border-surface-border">
                {{ stats.skip }} SKIP
              </span>
            </div>
          </div>
          <!-- 堆疊比例條 -->
          <div class="stacked-bar w-full h-1 bg-surface-ground rounded-full overflow-hidden flex">
            <div
              v-if="stats.fail > 0"
              class="bar-seg seg-fail bg-red-500 h-full"
              :style="{ width: getSegmentPercent(stats, 'fail') + '%' }"
            ></div>
            <div
              v-if="stats.warning > 0"
              class="bar-seg seg-warn bg-amber-500 h-full"
              :style="{ width: getSegmentPercent(stats, 'warning') + '%' }"
            ></div>
            <div
              v-if="stats.pass > 0"
              class="bar-seg seg-pass bg-emerald-500 h-full"
              :style="{ width: getSegmentPercent(stats, 'pass') + '%' }"
            ></div>
          </div>
        </div>
      </div>
    </div>

    <!-- 2.5 PartDB 規格庫缺失待補清單 (當檢驗結果有缺失 PartDB 時顯示) -->
    <div
      v-if="missingPartDbGroups.length > 0"
      class="missing-partdb-section px-3 py-2.5 rounded bg-surface-panel border border-amber-500/40 flex flex-col gap-2"
    >
      <div class="flex items-center justify-between gap-2 flex-wrap">
        <div class="flex items-center gap-1.5">
          <i class="pi pi-database text-amber-500 text-xs"></i>
          <span class="text-xs font-semibold text-vscode-textHeading">
            PartDB 規格庫缺失待補清單 (共 {{ missingPartDbGroups.length }} 項物料待補齊穿透定義)
          </span>
        </div>
        <span class="text-[11px] text-vscode-textMuted">
          若元件已上件，導通檢測標註為 SKIPPED；若未上件，拓撲已標註 [X]
        </span>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
        <div
          v-for="group in missingPartDbGroups"
          :key="group.key"
          class="missing-partdb-card px-2.5 py-2 rounded bg-surface-card border border-surface-border flex flex-col gap-1.5"
        >
          <div class="flex items-center justify-between gap-2 min-w-0">
            <span class="font-mono text-xs font-bold text-amber-600 dark:text-amber-400 truncate" :title="group.key">
              {{ group.key }}
            </span>
            <span class="text-[10px] px-1.5 py-0.2 rounded font-mono bg-amber-500/15 text-amber-600 dark:text-amber-400 border border-amber-500/30 shrink-0">
              缺失待補
            </span>
          </div>

          <div class="text-[11px] text-vscode-textSecondary flex items-center gap-1">
            <span>製造商:</span>
            <span class="font-mono text-vscode-textHeading font-medium">{{ group.mfg }}</span>
            <span class="mx-1 text-surface-400">|</span>
            <span>料號:</span>
            <span class="font-mono text-vscode-textHeading font-medium">{{ group.pn }}</span>
          </div>

          <div class="flex items-center gap-1.5 flex-wrap pt-1 border-t border-surface-border">
            <span class="text-[11px] text-vscode-textMuted">受影響元件 ({{ group.references.length }}):</span>
            <div class="flex items-center gap-1 flex-wrap">
              <span
                v-for="ref in group.references"
                :key="ref.ref_des"
                class="font-mono text-[10px] px-1.5 py-0.5 rounded border"
                :class="ref.is_mounted ? 'bg-surface-panel text-vscode-textHeading border-surface-border' : 'bg-surface-ground text-vscode-textMuted border-dashed border-surface-border'"
                :title="ref.is_mounted ? `${ref.ref_des} (已上件)` : `${ref.ref_des} (未上件)`"
              >
                {{ ref.ref_des }}
                <span v-if="!ref.is_mounted" class="text-vscode-textMuted ml-0.5">[X]</span>
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 3. 檢驗項目明細與過濾工具列 (無外層多餘卡片套嵌，直接 1px 邊框區塊) -->
    <div class="violations-section rounded bg-surface-panel border border-surface-border flex flex-col">
      <!-- 工具列 -->
      <div class="toolbar px-3 py-2 border-b border-surface-border flex flex-col gap-2">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <div class="flex items-center gap-2 flex-wrap">
            <div class="section-title text-xs font-semibold text-vscode-textHeading flex items-center gap-1.5">
              <i class="pi pi-filter text-primary text-xs"></i>
              <span>DRC 檢驗結果明細</span>
              <span class="count-pill px-1.5 py-0.5 rounded bg-surface-card text-[11px] font-mono text-vscode-textSecondary border border-surface-border">
                {{ filteredRuleGroups.length }} 條規則 / {{ filteredViolations.length }} 個受測項
              </span>
            </div>

            <!-- 檢視模式切換 (規則分組 vs 平面展開) -->
            <div class="view-mode-switcher flex items-center bg-surface-ground p-0.5 rounded border border-surface-border text-[11px]">
              <button
                type="button"
                v-tooltip.top="'依規則卡片聚合受測通道'"
                class="view-mode-btn-grouped px-2 py-0.5 rounded cursor-pointer transition-colors flex items-center gap-1 border-0"
                :class="viewMode === 'grouped' ? 'bg-primary text-white font-medium shadow-xs' : 'bg-transparent text-vscode-textMuted hover:text-vscode-textHeading'"
                @click="viewMode = 'grouped'"
              >
                <i class="pi pi-objects-column text-[10px]"></i>
                <span>規則分組</span>
              </button>
              <button
                type="button"
                v-tooltip.top="'平面展開所有受測項目'"
                class="view-mode-btn-flat px-2 py-0.5 rounded cursor-pointer transition-colors flex items-center gap-1 border-0"
                :class="viewMode === 'flat' ? 'bg-primary text-white font-medium shadow-xs' : 'bg-transparent text-vscode-textMuted hover:text-vscode-textHeading'"
                @click="viewMode = 'flat'"
              >
                <i class="pi pi-bars text-[10px]"></i>
                <span>平面清單</span>
              </button>
            </div>

            <!-- 批次展開/收合控制 (圖示按鈕 + Tooltip) -->
            <div v-if="viewMode === 'grouped'" class="batch-expand-controls flex items-center gap-1 text-[11px]">
              <button
                type="button"
                v-tooltip.top="'展開全部規則群組'"
                class="btn-expand-all w-6 h-6 rounded bg-surface-card hover:bg-surface-hover text-vscode-textSecondary hover:text-vscode-textHeading border border-surface-border cursor-pointer transition-colors flex items-center justify-center"
                @click="expandAllRuleGroups"
              >
                <i class="pi pi-angle-double-down text-xs"></i>
                <span class="sr-only">展開全部</span>
              </button>
              <button
                type="button"
                v-tooltip.top="'收合全部規則群組'"
                class="btn-collapse-all w-6 h-6 rounded bg-surface-card hover:bg-surface-hover text-vscode-textSecondary hover:text-vscode-textHeading border border-surface-border cursor-pointer transition-colors flex items-center justify-center"
                @click="collapseAllRuleGroups"
              >
                <i class="pi pi-angle-double-up text-xs"></i>
                <span class="sr-only">收合全部</span>
              </button>
            </div>
          </div>

          <div class="toolbar-actions flex flex-wrap items-center gap-1.5">
            <!-- 關鍵字搜尋 -->
            <IconField class="search-box">
              <InputIcon class="pi pi-search text-xs text-vscode-textMuted" />
              <InputText
                v-model="searchQuery"
                type="text"
                size="small"
                placeholder="搜尋規則、元件 (U1)、網路 (I2C_SDA)..."
                class="search-input w-48 sm:w-60 text-xs py-1 bg-surface-ground border-surface-border text-vscode-textMain placeholder:text-vscode-textMuted"
              />
              <button
                v-if="searchQuery"
                type="button"
                class="clear-search-btn absolute right-2 top-1/2 -translate-y-1/2 text-vscode-textMuted hover:text-vscode-textHeading bg-transparent border-0 cursor-pointer p-0"
                @click="searchQuery = ''"
              >
                <i class="pi pi-times text-[10px]"></i>
              </button>
            </IconField>

            <!-- 每頁筆數選擇 (PrimeVue Select) -->
            <div class="page-size-box flex items-center gap-1 text-[11px] text-vscode-textMuted">
              <span>每頁</span>
              <Select
                v-model="pageSize"
                :options="pageSizeOptions"
                optionLabel="label"
                optionValue="value"
                size="small"
                class="page-size-select text-xs bg-surface-ground border-surface-border min-w-[4.5rem]"
              />
            </div>

            <!-- 匯出 JSON 報告按鈕 (圖示按鈕 + Tooltip) -->
            <Button
              v-tooltip.top="'匯出 JSON 檢驗報告'"
              icon="pi pi-download"
              severity="secondary"
              size="small"
              outlined
              class="export-btn !w-7 !h-7 !p-0"
              @click="exportReportJson"
            >
              <i class="pi pi-download text-xs"></i>
              <span class="sr-only">匯出 JSON</span>
            </Button>
          </div>
        </div>

        <!-- 狀態與分類過濾膠囊列 -->
        <div class="filter-pills-row flex flex-wrap items-center justify-between gap-2 pt-1.5 border-t border-surface-border">
          <!-- 狀態快速篩選 -->
          <div class="status-pills flex items-center gap-1 flex-wrap">
            <span class="text-[11px] text-vscode-textSecondary font-medium mr-1">狀態：</span>
            <button
              v-for="st in statusFilterOptions"
              :key="st.value"
              type="button"
              class="filter-pill-btn px-2 py-0.5 rounded text-[11px] font-medium cursor-pointer transition-all border flex items-center gap-1"
              :class="selectedStatus === st.value ? st.activeClass : 'bg-surface-ground text-vscode-textSecondary border-surface-border hover:text-vscode-textHeading hover:bg-surface-hover'"
              @click="selectedStatus = st.value"
            >
              <i :class="st.icon" class="text-[10px]"></i>
              <span>{{ st.label }}</span>
              <span class="font-mono text-[10px] opacity-80">({{ st.count }})</span>
            </button>
          </div>

          <!-- 檢驗方法與活躍過濾條件清除 -->
          <div class="method-pills flex items-center gap-1 flex-wrap">
            <span class="text-[11px] text-vscode-textSecondary font-medium mr-1">引擎：</span>
            <button
              v-for="chk in checkTypeOptions"
              :key="chk.value"
              type="button"
              class="method-pill-btn px-2 py-0.5 rounded text-[11px] cursor-pointer transition-all border"
              :class="selectedCheckType === chk.value ? 'bg-primary/15 text-primary border-primary/40 font-medium' : 'bg-surface-ground text-vscode-textSecondary border-surface-border hover:text-vscode-textHeading hover:bg-surface-hover'"
              @click="selectedCheckType = chk.value"
            >
              {{ chk.label }}
            </button>

            <button
              v-if="hasActiveFilters"
              type="button"
              v-tooltip.top="'重設所有篩選條件'"
              class="reset-filter-btn ml-1 px-2 py-0.5 rounded text-[11px] bg-surface-card text-vscode-textSecondary border border-surface-border hover:bg-surface-hover hover:text-vscode-textHeading cursor-pointer transition-colors flex items-center gap-1"
              @click="resetAllFilters"
            >
              <i class="pi pi-filter-slash text-[10px]"></i>
              <span>清除篩選</span>
            </button>
          </div>
        </div>
      </div>

      <!-- 4A. 規則分組檢視模式 (Grouped by Rule ID) -->
      <div v-if="viewMode === 'grouped' && paginatedRuleGroups.length > 0" class="rules-grouped-list">
        <div
          v-for="group in paginatedRuleGroups"
          :key="group.rule_id"
          class="rule-group-card bg-surface-panel overflow-hidden transition-colors border-b border-surface-border last:border-b-0"
          :class="getWorstStatusBorderClass(group.worst_status)"
        >
          <!-- 規則卡片標題列 -->
          <div
            class="rule-group-header px-3 py-2 bg-surface-card flex flex-col sm:flex-row sm:items-center justify-between gap-2 cursor-pointer hover:bg-surface-hover transition-colors border-l-4"
            :class="getWorstStatusBorderClass(group.worst_status)"
            @click="toggleRuleGroupExpand(group.rule_id)"
          >
            <div class="flex items-center gap-1.5 flex-wrap min-w-0">
              <!-- 展開收合箭頭 (稍微縮小一號至 10px) -->
              <i
                class="pi text-[10px] text-vscode-textMuted transition-transform w-3 text-center shrink-0"
                :class="isRuleGroupExpanded(group.rule_id) ? 'pi-chevron-down' : 'pi-chevron-right'"
              ></i>
              <!-- 規則名稱 (非標籤形式，粗體文字) -->
              <span class="rule-id font-bold font-mono text-xs text-vscode-textHeading shrink-0">
                {{ group.rule_id }}
              </span>
              <!-- 分隔符號 -->
              <span class="text-surface-400 dark:text-surface-600 select-none font-light shrink-0">|</span>
              <!-- 規則描述 (正常字重文字) -->
              <span class="rule-group-title text-xs font-normal text-vscode-textMain truncate">
                {{ group.rule_title }}
              </span>
              <!-- 規則分類標籤 (低飽和中性石色) -->
              <span class="rule-category text-[10px] px-1.5 py-0.2 rounded bg-surface-panel text-vscode-textSecondary border border-surface-border shrink-0">
                {{ group.rule_category }}
              </span>
              <!-- 檢驗引擎標籤 (2色低飽和規範) -->
              <span
                class="check-type-badge text-[10px] px-1.5 py-0.2 rounded font-mono shrink-0"
                :class="getCheckTypeBadgeClass(group.check_type)"
              >
                {{ formatCheckTypeLabel(group.check_type) }}
              </span>
            </div>

            <!-- 通道統計計數徽章群 -->
            <div class="rule-group-counts flex items-center gap-1 text-[10px] font-mono shrink-0">
              <span v-if="group.fail_count > 0" class="px-1.5 py-0.5 rounded bg-red-500/15 text-red-600 dark:text-red-400 border border-red-500/30 font-semibold">
                {{ group.fail_count }} FAIL
              </span>
              <span v-if="group.warn_count > 0" class="px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-600 dark:text-amber-400 border border-amber-500/30 font-semibold">
                {{ group.warn_count }} WARN
              </span>
              <span v-if="group.pass_count > 0" class="px-1.5 py-0.5 rounded bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30 font-semibold">
                {{ group.pass_count }} PASS
              </span>
              <span v-if="group.skip_count > 0" class="px-1.5 py-0.5 rounded bg-surface-panel text-vscode-textMuted border border-surface-border">
                {{ group.skip_count }} SKIP
              </span>
              <span class="text-vscode-textMuted ml-1">
                (共 {{ group.items.length }} 組受測)
              </span>
            </div>
          </div>

          <!-- 規則卡片內受測通道清單 (避免使用 divide-y 覆蓋子項目各自的 border-l 狀態顏色) -->
          <div v-show="isRuleGroupExpanded(group.rule_id)" class="rule-group-body border-t border-surface-border">
            <div
              v-for="item in group.items"
              :key="item.item_id"
              class="violation-item transition-colors hover:bg-surface-hover/50 border-l-4 border-b border-b-surface-border last:border-b-0"
              :class="getStatusBorderClass(item)"
            >
              <div
                class="item-main-row px-3 py-1.5 flex flex-col sm:flex-row sm:items-center justify-between gap-2 cursor-pointer"
                @click="toggleExpand(item.item_id)"
              >
                <div class="item-left flex flex-col gap-0.5 min-w-0 flex-1">
                  <div class="item-meta-row flex items-center gap-1.5 flex-wrap">
                    <!-- 嚴重度徽章 (僅非 PASS/SKIPPED 顯示) -->
                    <span
                      v-if="item.status !== 'PASS' && item.status !== 'SKIPPED'"
                      class="severity-badge text-[10px] px-1 py-0.2 rounded font-mono"
                      :class="getSeverityBadgeClass(item.severity)"
                    >
                      {{ item.severity }}
                    </span>

                    <!-- 受測通道標題 -->
                    <span
                      v-if="item.evidence_trail && item.evidence_trail.channel_title"
                      class="channel-title text-xs font-mono font-medium text-vscode-textHeading flex items-center gap-1.5"
                    >
                      <Tag
                        v-if="isDiffChannelTitle(item.evidence_trail.channel_title)"
                        value="DIFF"
                        severity="info"
                        class="tag-diff !text-[9px] !px-1 !py-0 font-mono"
                      />
                      <span>{{ formatCleanChannelTitle(item.evidence_trail.channel_title) }}</span>
                    </span>

                    <!-- 單行關鍵違規/檢驗訊息摘要 -->
                    <span
                      v-if="item.error_message || item.description"
                      class="text-xs truncate max-w-xl"
                      :class="item.status === 'FAIL' ? 'text-red-600 dark:text-red-400 font-medium' : 'text-vscode-textSecondary'"
                    >
                      {{ item.error_message || item.description }}
                    </span>
                  </div>
                </div>

                <!-- 右側：受測元件/網路快速標籤 + 展開按鈕 -->
                <div class="item-right flex items-center gap-2 shrink-0 self-end sm:self-center">
                  <div class="target-Preview hidden md:flex items-center gap-1 max-w-xs overflow-hidden">
                    <span
                      v-for="comp in item.target_nodes.components.slice(0, 3)"
                      :key="comp"
                      class="node-chip px-1.5 py-0.2 rounded text-[10px] font-mono border"
                      :class="isUnmountedChip(comp, item)
                        ? 'bg-surface-ground text-surface-400 border-surface-border line-through'
                        : 'bg-surface-card text-primary font-medium dark:text-primary-400 border-surface-border'"
                    >
                      {{ formatComponentChipLabel(comp, item) }}
                    </span>
                    <span
                      v-if="item.target_nodes.components.length > 3"
                      class="text-[10px] text-vscode-textMuted font-mono"
                    >
                      +{{ item.target_nodes.components.length - 3 }}
                    </span>
                    <span
                      v-for="net in item.target_nodes.nets.slice(0, 2)"
                      :key="net"
                      class="node-chip px-1.5 py-0.2 rounded bg-surface-card text-vscode-textSecondary text-[10px] font-mono border border-surface-border truncate max-w-[110px]"
                    >
                      {{ net }}
                    </span>
                  </div>

                  <button
                    type="button"
                    v-tooltip.top="isExpanded(item.item_id) ? '收合佐證' : '檢視佐證'"
                    :aria-label="isExpanded(item.item_id) ? '收合佐證' : '檢視佐證'"
                    class="expand-btn w-6 h-6 rounded bg-transparent hover:bg-surface-hover text-vscode-textSecondary hover:text-vscode-textHeading flex items-center justify-center cursor-pointer transition-colors border-0"
                    @click.stop="toggleExpand(item.item_id)"
                  >
                    <i class="pi text-[8px]" :class="isExpanded(item.item_id) ? 'pi-chevron-up' : 'pi-chevron-down'"></i>
                  </button>
                </div>
              </div>

              <!-- 展開之詳細佐證與工程建議區 -->
              <EvidenceDetailsBlock
                v-if="isExpanded(item.item_id)"
                :item="item"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- 4B. 平面清單檢視模式 (Flat List) -->
      <div v-else-if="viewMode === 'flat' && paginatedViolations.length > 0" class="items-list">
        <div
          v-for="item in paginatedViolations"
          :key="item.item_id"
          class="violation-item bg-surface-panel overflow-hidden transition-colors border-l-4 border-b border-b-surface-border last:border-b-0"
          :class="getStatusBorderClass(item)"
        >
          <!-- 項目主體列 (可點擊展開佐證歷程) -->
          <div
            class="item-main-row px-3 py-2 flex flex-col sm:flex-row sm:items-center justify-between gap-2 cursor-pointer hover:bg-surface-hover/50 transition-colors"
            @click="toggleExpand(item.item_id)"
          >
            <div class="item-left flex flex-col gap-0.5 min-w-0 flex-1">
              <div class="item-meta-row flex items-center gap-1.5 flex-wrap">
                <!-- 嚴重度徽章 (僅非 PASS 顯示) -->
                <span
                  v-if="item.status !== 'PASS' && item.status !== 'SKIPPED'"
                  class="severity-badge text-[10px] px-1.5 py-0.2 rounded font-mono"
                  :class="getSeverityBadgeClass(item.severity)"
                >
                  {{ item.severity }}
                </span>

                <!-- 規則編號 -->
                <span class="rule-id font-mono text-[11px] font-medium text-vscode-textHeading bg-surface-card px-1.5 py-0.2 rounded border border-surface-border">
                  {{ item.rule_id }}
                </span>

                <!-- 規則分類 -->
                <span class="rule-category text-[11px] px-1.5 py-0.2 rounded bg-surface-card text-vscode-textSecondary border border-surface-border">
                  {{ item.rule_category }}
                </span>

                <!-- 檢驗引擎標籤 -->
                <span
                  class="check-type-badge text-[10px] px-1.5 py-0.2 rounded font-mono"
                  :class="getCheckTypeBadgeClass(item.check_type)"
                >
                  {{ formatCheckTypeLabel(item.check_type) }}
                </span>

                <!-- 受測通道標題 -->
                <span
                  v-if="item.evidence_trail && item.evidence_trail.channel_title"
                  class="channel-title text-xs font-mono font-medium text-vscode-textHeading flex items-center gap-1.5"
                >
                  <Tag
                    v-if="isDiffChannelTitle(item.evidence_trail.channel_title)"
                    value="DIFF"
                    severity="info"
                    class="tag-diff !text-[9px] !px-1 !py-0 font-mono"
                  />
                  <span>{{ formatCleanChannelTitle(item.evidence_trail.channel_title) }}</span>
                </span>
              </div>

              <!-- 規則標題與違規描述 -->
              <div class="item-title text-xs font-medium text-vscode-textMain mt-0.5">
                {{ item.rule_title }}
              </div>
              <div v-if="item.error_message && item.status !== 'PASS'" class="item-error-preview text-xs text-red-600 dark:text-red-400 font-medium mt-0.5">
                {{ item.error_message }}
              </div>
            </div>

            <!-- 右側：受測元件/網路快速預覽 + 展開箭頭 -->
            <div class="item-right flex items-center gap-2 shrink-0 self-end sm:self-center">
              <div class="target-Preview hidden md:flex items-center gap-1 max-w-xs overflow-hidden">
                <span
                  v-for="comp in item.target_nodes.components.slice(0, 3)"
                  :key="comp"
                  class="node-chip px-1.5 py-0.2 rounded text-[10px] font-mono border"
                  :class="isUnmountedChip(comp, item)
                    ? 'bg-surface-ground text-surface-400 border-surface-border line-through'
                    : 'bg-surface-card text-primary font-medium dark:text-primary-400 border-surface-border'"
                >
                  {{ formatComponentChipLabel(comp, item) }}
                </span>
                <span
                  v-if="item.target_nodes.components.length > 3"
                  class="text-[10px] text-vscode-textMuted font-mono"
                >
                  +{{ item.target_nodes.components.length - 3 }}
                </span>
                <span
                  v-for="net in item.target_nodes.nets.slice(0, 2)"
                  :key="net"
                  class="node-chip px-1.5 py-0.2 rounded bg-surface-card text-vscode-textSecondary text-[10px] font-mono border border-surface-border truncate max-w-[110px]"
                >
                  {{ net }}
                </span>
              </div>

              <button
                type="button"
                v-tooltip.top="isExpanded(item.item_id) ? '收合佐證' : '檢視佐證'"
                :aria-label="isExpanded(item.item_id) ? '收合佐證' : '檢視佐證'"
                class="expand-btn w-6 h-6 rounded bg-transparent hover:bg-surface-hover text-vscode-textSecondary hover:text-vscode-textHeading flex items-center justify-center cursor-pointer transition-colors border-0"
                @click.stop="toggleExpand(item.item_id)"
              >
                <i class="pi text-[8px]" :class="isExpanded(item.item_id) ? 'pi-chevron-up' : 'pi-chevron-down'"></i>
              </button>
            </div>
          </div>

          <!-- 展開之詳細佐證與工程建議區 -->
          <EvidenceDetailsBlock
            v-if="isExpanded(item.item_id)"
            :item="item"
          />
        </div>
      </div>

      <!-- 無符合項目之空狀態 -->
      <div v-else class="empty-violations py-8 text-center text-vscode-textMuted">
        <i class="pi pi-check-square text-2xl mb-1.5 text-vscode-textMuted block"></i>
        <p class="m-0 text-xs font-medium text-vscode-textHeading">目前篩選條件下無對應之檢驗項目</p>
        <p class="m-0 text-[11px] mt-0.5 text-vscode-textMuted">您可以切換上方狀態標籤或清除搜尋條件以檢視全部規則</p>
      </div>

      <!-- 5. 分頁導覽列 (Pagination Footer) -->
      <div
        v-if="totalPages > 1"
        class="pagination-bar px-3 py-2 border-t border-surface-border flex flex-wrap items-center justify-between gap-2 text-xs text-vscode-textMuted"
      >
        <div class="pagination-info font-mono text-[11px]">
          顯示第 {{ paginationStart }} - {{ paginationEnd }} 筆（共 {{ currentTotalItems }} 筆{{ viewMode === 'grouped' ? '規則群組' : '受測項目' }}）
        </div>
        <div class="pagination-controls flex items-center gap-1">
          <button
            type="button"
            class="page-btn px-2 py-0.5 rounded bg-surface-ground border border-surface-border text-vscode-textSecondary disabled:opacity-40 cursor-pointer hover:bg-surface-hover hover:text-vscode-textHeading text-[11px]"
            :disabled="currentPage <= 1"
            @click="currentPage = 1"
          >
            首頁
          </button>
          <button
            type="button"
            class="page-btn px-2 py-0.5 rounded bg-surface-ground border border-surface-border text-vscode-textSecondary disabled:opacity-40 cursor-pointer hover:bg-surface-hover hover:text-vscode-textHeading text-[11px]"
            :disabled="currentPage <= 1"
            @click="currentPage--"
          >
            上一頁
          </button>
          <span class="px-2 py-0.5 font-mono text-vscode-textHeading text-[11px]">
            頁次 {{ currentPage }} / {{ totalPages }}
          </span>
          <button
            type="button"
            class="page-btn px-2 py-0.5 rounded bg-surface-ground border border-surface-border text-vscode-textSecondary disabled:opacity-40 cursor-pointer hover:bg-surface-hover hover:text-vscode-textHeading text-[11px]"
            :disabled="currentPage >= totalPages"
            @click="currentPage++"
          >
            下一頁
          </button>
          <button
            type="button"
            class="page-btn px-2 py-0.5 rounded bg-surface-ground border border-surface-border text-vscode-textSecondary disabled:opacity-40 cursor-pointer hover:bg-surface-hover hover:text-vscode-textHeading text-[11px]"
            :disabled="currentPage >= totalPages"
            @click="currentPage = totalPages"
          >
            末頁
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * @file TaskReportDashboard.vue
 * @description 步驟六 DRC 檢驗報告視覺化儀表板元件 (2026 緊湊雙主題版)
 * 具備 40px 單行關鍵指標橫條、領域健康度分佈、多維度過濾、規則分組與佐證展開功能
 */

import { ref, computed, watch } from 'vue'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import Select from 'primevue/select'
import InputText from 'primevue/inputtext'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import EvidenceDetailsBlock from './EvidenceDetailsBlock.vue'

/**
 * 單一分類統計結構
 */
export interface CategoryStat {
  pass: number
  fail: number
  warning: number
  skip?: number
}

/**
 * 報告統計總覽結構
 */
export interface ReportSummary {
  total_rules_checked: number
  pass_count: number
  fail_count: number
  warning_count: number
  skip_count?: number
  pass_rate_percentage: number
  by_category: Record<string, CategoryStat>
  /** 多 BOM Config 各自的獨立統計摘要 */
  configs?: Record<string, {
    total_rules_checked: number
    pass_count: number
    fail_count: number
    warning_count: number
    skip_count?: number
    pass_rate_percentage: number
    by_category: Record<string, CategoryStat>
  }>
}

/**
 * 受測節點結構
 */
export interface TargetNodes {
  components: string[]
  nets: string[]
}

/**
 * 單筆檢驗結果/違規項目結構
 */
export interface ViolationItem {
  item_id: string
  rule_id: string
  rule_category: string
  rule_title: string
  check_type: 'DETERMINISTIC' | 'HEURISTIC' | 'SPATIAL_AI' | string
  status: 'PASS' | 'FAIL' | 'WARNING' | 'SKIPPED' | string
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'WARNING' | 'INFO' | string
  target_nodes: TargetNodes
  description?: string
  comment?: string
  error_message?: string
  recommendation?: string
  evidence_trail?: Record<string, any>
  /** 所屬 BOM Config 名稱 */
  bom_config?: string
}

/**
 * 規則群組聚合結構 (同規則多受測通道歸納於同一張規則卡片)
 */
export interface RuleGroup {
  rule_id: string
  rule_category: string
  rule_title: string
  check_type: string
  worst_status: 'FAIL' | 'WARNING' | 'PASS' | 'SKIPPED' | string
  fail_count: number
  warn_count: number
  pass_count: number
  skip_count: number
  items: ViolationItem[]
}

/**
 * PartDB 規格庫缺失待補物料項目結構
 */
export interface MissingPartDbRef {
  ref_des: string
  is_mounted: boolean
}

export interface MissingPartDbGroup {
  key: string
  mfg: string
  pn: string
  references: MissingPartDbRef[]
}

interface Props {
  /** 報告總覽數據 */
  summary: ReportSummary
  /** 檢驗結果明細清單 */
  violations: ViolationItem[]
  /** 任務 ID (匯出報告命名使用) */
  taskId?: string
}

const props = withDefaults(defineProps<Props>(), {
  taskId: 'unknown-task'
})

// 過濾與搜尋狀態
const selectedStatus = ref<string>('ALL')
const selectedCategory = ref<string>('ALL')
const selectedCheckType = ref<string>('ALL')
const searchQuery = ref<string>('')
const expandedIds = ref<Set<string>>(new Set())

// BOM Config 選擇狀態
const selectedBomConfig = ref<string>('')

// 每頁筆數選項
const pageSizeOptions = [
  { label: '20 筆', value: 20 },
  { label: '50 筆', value: 50 },
  { label: '100 筆', value: 100 },
]

/**
 * 取得可用的 BOM Config 名稱清單
 */
const availableConfigs = computed<string[]>(() => {
  if (props.summary?.configs && Object.keys(props.summary.configs).length > 0) {
    return Object.keys(props.summary.configs)
  }
  const set = new Set<string>()
  for (const v of props.violations) {
    if (v.bom_config) set.add(v.bom_config)
  }
  return Array.from(set)
})

// 當 availableConfigs 變動且尚未選擇時，預設選取第一個 Config
watch(
  availableConfigs,
  (configs) => {
    if (configs.length > 0 && (!selectedBomConfig.value || !configs.includes(selectedBomConfig.value))) {
      selectedBomConfig.value = configs[0]
    }
  },
  { immediate: true }
)

/**
 * 切換選擇的 BOM Config
 */
const selectBomConfig = (cfgName: string) => {
  selectedBomConfig.value = cfgName
}

/**
 * 取得特定 BOM Config 的 FAIL 數量
 */
const getConfigFailCount = (cfgName: string): number => {
  if (props.summary?.configs && props.summary.configs[cfgName]) {
    return props.summary.configs[cfgName].fail_count || 0
  }
  return props.violations.filter((v) => v.bom_config === cfgName && v.status === 'FAIL').length
}

/**
 * 判斷特定 BOM Config 是否有任何 FAIL 項目
 */
const hasConfigFail = (cfgName: string): boolean => {
  return getConfigFailCount(cfgName) > 0
}

/**
 * 取得 BOM Config 按鈕樣式：
 * 若該 Config 有 FAIL 項目，按鈕固定為紅底 (bg-red-600) 以強化工程警示
 */
const getBomConfigBtnClass = (cfgName: string): string => {
  const isSelected = selectedBomConfig.value === cfgName
  const isFail = hasConfigFail(cfgName)

  if (isFail) {
    return isSelected
      ? 'bg-red-600 text-white border-red-400 ring-1 ring-red-400/50'
      : 'bg-red-600/80 text-white/90 border-red-500/60 opacity-85 hover:opacity-100'
  }
  return isSelected
    ? 'bg-primary text-white border-primary shadow-xs'
    : 'bg-surface-card text-vscode-textSecondary border-surface-border hover:border-surface-border-light'
}

/**
 * 當前激活的 Summary (根據選中的 BOM Config 動態連動全頁統計卡與領域健康度)
 */
const activeSummary = computed<ReportSummary>(() => {
  const cfg = selectedBomConfig.value
  if (cfg && props.summary?.configs && props.summary.configs[cfg]) {
    return props.summary.configs[cfg]
  }
  return props.summary
})

// 檢視模式 ('grouped': 依規則分組, 'flat': 平面清單) 與分頁狀態
const viewMode = ref<'grouped' | 'flat'>('grouped')
const currentPage = ref<number>(1)
const pageSize = ref<number>(20)
const collapsedRuleGroupIds = ref<Set<string>>(new Set())

// 當篩選條件或檢視模式變更時，自動重置回第 1 頁
watch([selectedBomConfig, selectedStatus, selectedCategory, selectedCheckType, searchQuery, viewMode, pageSize], () => {
  currentPage.value = 1
})

/**
 * 格式化通過率百分比 (取小數點後一位)
 */
const formattedPassRate = computed<string>(() => {
  const rate = activeSummary.value?.pass_rate_percentage ?? 0
  return String(rate)
})

/**
 * 根據通過率決定文字顏色
 */
const passRateTextClass = computed<string>(() => {
  const rate = activeSummary.value?.pass_rate_percentage ?? 0
  if (rate >= 90) return 'text-emerald-500'
  if (rate >= 70) return 'text-amber-500'
  return 'text-red-500'
})

/**
 * 領域分類清單
 */
const categoryEntries = computed<[string, CategoryStat][]>(() => {
  if (!activeSummary.value?.by_category) return []
  return Object.entries(activeSummary.value.by_category)
})

/**
 * 依選中 BOM Config 過濾後的基準項目清單
 */
const configScopedViolations = computed<ViolationItem[]>(() => {
  if (!selectedBomConfig.value || availableConfigs.value.length === 0) {
    return props.violations
  }
  return props.violations.filter((v) => !v.bom_config || v.bom_config === selectedBomConfig.value)
})

/**
 * 彙總當前檢測結果中所有缺少 PartDB 的物料群組
 * 以 mfg_pn 為主 key 分組，列出使用該物料的 part references 清單
 */
const missingPartDbGroups = computed<MissingPartDbGroup[]>(() => {
  const map = new Map<string, { mfg: string; pn: string; refs: Map<string, boolean> }>()

  for (const item of configScopedViolations.value) {
    const list: any[] = []
    if (Array.isArray(item.evidence_trail?.missing_partdb)) {
      list.push(...item.evidence_trail.missing_partdb)
    }
    if (Array.isArray(item.evidence_trail?.topology?.missing_partdb)) {
      list.push(...item.evidence_trail.topology.missing_partdb)
    }

    for (const entry of list) {
      if (!entry || !entry.ref_des) continue
      const mfg = String(entry.mfg || 'UNKNOWN').trim()
      const pn = String(entry.pn || 'UNKNOWN').trim()
      const key = `${mfg}_${pn}`
      const isMounted = entry.is_mounted !== false

      let grp = map.get(key)
      if (!grp) {
        grp = { mfg, pn, refs: new Map<string, boolean>() }
        map.set(key, grp)
      }
      const prev = grp.refs.get(entry.ref_des)
      if (prev === undefined || (!prev && isMounted)) {
        grp.refs.set(entry.ref_des, isMounted)
      }
    }
  }

  const result: MissingPartDbGroup[] = []
  for (const [key, val] of map.entries()) {
    const sortedRefs = Array.from(val.refs.entries())
      .map(([ref_des, is_mounted]) => ({ ref_des, is_mounted }))
      .sort((a, b) => a.ref_des.localeCompare(b.ref_des, undefined, { numeric: true }))

    result.push({
      key,
      mfg: val.mfg,
      pn: val.pn,
      references: sortedRefs
    })
  }

  return result.sort((a, b) => a.key.localeCompare(b.key))
})

/**
 * 狀態過濾膠囊選項
 */
const statusFilterOptions = computed(() => {
  const baseList = configScopedViolations.value
  const total = baseList.length
  const failCount = baseList.filter((v) => v.status === 'FAIL').length
  const warnCount = baseList.filter((v) => v.status === 'WARNING').length
  const passCount = baseList.filter((v) => v.status === 'PASS').length
  const skipCount = baseList.filter((v) => v.status === 'SKIPPED').length

  return [
    {
      label: '全部',
      value: 'ALL',
      count: total,
      icon: 'pi pi-list',
      activeClass: 'bg-primary/15 text-primary border-primary/40 font-medium'
    },
    {
      label: '違規 (FAIL)',
      value: 'FAIL',
      count: failCount,
      icon: 'pi pi-times-circle',
      activeClass: 'bg-red-500/15 text-red-600 dark:text-red-400 border-red-500/40 font-medium'
    },
    {
      label: '警告 (WARN)',
      value: 'WARNING',
      count: warnCount,
      icon: 'pi pi-exclamation-triangle',
      activeClass: 'bg-amber-500/15 text-amber-600 dark:text-amber-400 border-amber-500/40 font-medium'
    },
    {
      label: '通過 (PASS)',
      value: 'PASS',
      count: passCount,
      icon: 'pi pi-check-circle',
      activeClass: 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-emerald-500/40 font-medium'
    },
    {
      label: '略過 (SKIP)',
      value: 'SKIPPED',
      count: skipCount,
      icon: 'pi pi-minus-circle',
      activeClass: 'bg-surface-card text-vscode-textSecondary border-surface-border font-medium'
    }
  ]
})

/**
 * 檢驗引擎方法過濾選項
 */
const checkTypeOptions = [
  { label: '全部引擎', value: 'ALL' },
  { label: '定性規則 (Deterministic)', value: 'DETERMINISTIC' },
  { label: '啟發式邏輯 (Heuristic)', value: 'HEURISTIC' },
  { label: '空間視覺 AI (Spatial AI)', value: 'SPATIAL_AI' }
]

/**
 * 是否有作用中的過濾條件
 */
const hasActiveFilters = computed<boolean>(() => {
  return (
    selectedStatus.value !== 'ALL' ||
    selectedCategory.value !== 'ALL' ||
    selectedCheckType.value !== 'ALL' ||
    searchQuery.value.trim() !== ''
  )
})

/**
 * 計算過濾後的檢驗結果清單 (同時排序：FAIL > WARNING > PASS > SKIPPED)
 */
const filteredViolations = computed<ViolationItem[]>(() => {
  const q = searchQuery.value.trim().toLowerCase()
  const statusWeight: Record<string, number> = { FAIL: 0, WARNING: 1, PASS: 2, SKIPPED: 3 }

  return configScopedViolations.value
    .filter((item) => {
      if (selectedStatus.value !== 'ALL' && item.status !== selectedStatus.value) {
        return false
      }
      if (selectedCategory.value !== 'ALL' && item.rule_category !== selectedCategory.value) {
        return false
      }
      if (selectedCheckType.value !== 'ALL' && item.check_type !== selectedCheckType.value) {
        return false
      }
      if (q) {
        const matchId = item.rule_id.toLowerCase().includes(q)
        const matchTitle = item.rule_title.toLowerCase().includes(q)
        const matchCategory = item.rule_category.toLowerCase().includes(q)
        const matchDesc = (item.description || '').toLowerCase().includes(q)
        const matchErr = (item.error_message || '').toLowerCase().includes(q)
        const matchComp = item.target_nodes.components.some((c) => c.toLowerCase().includes(q))
        const matchNet = item.target_nodes.nets.some((n) => n.toLowerCase().includes(q))
        return matchId || matchTitle || matchCategory || matchDesc || matchErr || matchComp || matchNet
      }
      return true
    })
    .sort((a, b) => {
      const wa = statusWeight[a.status] ?? 99
      const wb = statusWeight[b.status] ?? 99
      return wa - wb
    })
})

/**
 * 將過濾後的項目依 rule_id 聚合成規則群組
 * 最壞情況判定原則 (Worst-case Aggregation): FAIL > WARNING > PASS > SKIPPED
 */
const filteredRuleGroups = computed<RuleGroup[]>(() => {
  const map = new Map<string, RuleGroup>()
  const statusPriority: Record<string, number> = { FAIL: 0, WARNING: 1, PASS: 2, SKIPPED: 3 }

  for (const item of filteredViolations.value) {
    let group = map.get(item.rule_id)
    if (!group) {
      group = {
        rule_id: item.rule_id,
        rule_category: item.rule_category,
        rule_title: item.rule_title,
        check_type: item.check_type,
        worst_status: item.status,
        fail_count: 0,
        warn_count: 0,
        pass_count: 0,
        skip_count: 0,
        items: []
      }
      map.set(item.rule_id, group)
    }

    group.items.push(item)
    if (item.status === 'FAIL') group.fail_count++
    else if (item.status === 'WARNING') group.warn_count++
    else if (item.status === 'PASS') group.pass_count++
    else if (item.status === 'SKIPPED') group.skip_count++

    const currentWorstWeight = statusPriority[group.worst_status] ?? 99
    const itemWeight = statusPriority[item.status] ?? 99
    if (itemWeight < currentWorstWeight) {
      group.worst_status = item.status
    }
  }

  return Array.from(map.values()).sort((a, b) => {
    const wa = statusPriority[a.worst_status] ?? 99
    const wb = statusPriority[b.worst_status] ?? 99
    if (wa !== wb) return wa - wb
    return b.fail_count - a.fail_count
  })
})

/**
 * 分頁計算：總筆數與當前頁切片
 */
const currentTotalItems = computed<number>(() => {
  return viewMode.value === 'grouped'
    ? filteredRuleGroups.value.length
    : filteredViolations.value.length
})

const totalPages = computed<number>(() => {
  return Math.max(1, Math.ceil(currentTotalItems.value / pageSize.value))
})

const paginationStart = computed<number>(() => {
  if (currentTotalItems.value === 0) return 0
  return (currentPage.value - 1) * pageSize.value + 1
})

const paginationEnd = computed<number>(() => {
  return Math.min(currentTotalItems.value, currentPage.value * pageSize.value)
})

const paginatedRuleGroups = computed<RuleGroup[]>(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return filteredRuleGroups.value.slice(start, start + pageSize.value)
})

const paginatedViolations = computed<ViolationItem[]>(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return filteredViolations.value.slice(start, start + pageSize.value)
})

/**
 * 切換規則群組展開/收合 (預設展開)
 */
const isRuleGroupExpanded = (ruleId: string): boolean => {
  return !collapsedRuleGroupIds.value.has(ruleId)
}

const toggleRuleGroupExpand = (ruleId: string) => {
  const next = new Set(collapsedRuleGroupIds.value)
  if (next.has(ruleId)) {
    next.delete(ruleId)
  } else {
    next.add(ruleId)
  }
  collapsedRuleGroupIds.value = next
}

const expandAllRuleGroups = () => {
  collapsedRuleGroupIds.value = new Set()
}

const collapseAllRuleGroups = () => {
  collapsedRuleGroupIds.value = new Set(filteredRuleGroups.value.map((g) => g.rule_id))
}

/**
 * 切換狀態篩選 (點擊上方統計卡)
 */
const toggleStatusFilter = (status: string) => {
  selectedStatus.value = selectedStatus.value === status ? 'ALL' : status
}

/**
 * 切換領域分類篩選
 */
const toggleCategoryFilter = (category: string) => {
  selectedCategory.value = selectedCategory.value === category ? 'ALL' : category
}

/**
 * 重置所有篩選條件
 */
const resetAllFilters = () => {
  selectedStatus.value = 'ALL'
  selectedCategory.value = 'ALL'
  selectedCheckType.value = 'ALL'
  searchQuery.value = ''
}

/**
 * 計算領域分類堆疊條百分比
 */
const getSegmentPercent = (stats: CategoryStat, key: 'pass' | 'fail' | 'warning'): number => {
  const total = (stats.pass || 0) + (stats.fail || 0) + (stats.warning || 0)
  if (total === 0) return 0
  return Math.round(((stats[key] || 0) / total) * 100)
}

/**
 * 判斷項目是否已展開
 */
const isExpanded = (itemId: string): boolean => {
  return expandedIds.value.has(itemId)
}

/**
 * 切換單一項目佐證展開狀態
 */
const toggleExpand = (itemId: string) => {
  const next = new Set(expandedIds.value)
  if (next.has(itemId)) {
    next.delete(itemId)
  } else {
    next.add(itemId)
  }
  expandedIds.value = next
}

/**
 * 匯出當前報告為 JSON 檔案
 */
const exportReportJson = () => {
  const payload = {
    task_id: props.taskId,
    exported_at: new Date().toISOString(),
    summary: props.summary,
    violations: props.violations
  }
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `drc_report_${props.taskId}.json`
  a.click()
  URL.revokeObjectURL(url)
}

/**
 * 樣式輔助函式：依檢驗狀態判定左側邊條顏色
 * 保留測試選擇器 class：border-l-red-500 / border-l-green-500 / border-l-amber-500 / border-l-surface-400
 *
 * @param {string} status - 檢驗狀態 ('FAIL' | 'WARNING' | 'PASS' | 'SKIPPED')
 * @returns {string} 對應 Tailwind 邊條色彩 class
 */
const getWorstStatusBorderClass = (status: string): string => {
  const s = (status || '').toUpperCase()
  if (s === 'FAIL') return 'border-l-red-500'
  if (s === 'WARNING' || s === 'WARN') return 'border-l-amber-500'
  if (s === 'SKIPPED' || s === 'SKIP') return 'border-l-surface-400 dark:border-l-surface-600'
  return 'border-l-green-500'
}

/**
 * 取得單一受測項目的左側狀態邊條 class
 *
 * @param {ViolationItem} item - 單筆受測結果項目
 * @returns {string} 對應 Tailwind 邊條色彩 class
 */
const getStatusBorderClass = (item: ViolationItem): string => {
  return getWorstStatusBorderClass(item.status)
}

const getSeverityBadgeClass = (severity: string): string => {
  const s = (severity || '').toUpperCase()
  if (s === 'CRITICAL' || s === 'HIGH') return 'bg-red-500/15 text-red-600 dark:text-red-400'
  if (s === 'MEDIUM' || s === 'WARNING') return 'bg-amber-500/15 text-amber-600 dark:text-amber-400'
  return 'bg-surface-card text-vscode-textSecondary'
}

/**
 * 檢驗引擎標籤：遵循 2 色低飽和規範 (主色 Slate-Blue 與中性 Warm Stone Gray)
 */
const getCheckTypeBadgeClass = (checkType: string): string => {
  if (checkType === 'SPATIAL_AI') return 'bg-primary/15 text-primary border border-primary/30 font-medium'
  return 'bg-surface-panel text-vscode-textSecondary border border-surface-border'
}

const formatCheckTypeLabel = (checkType: string): string => {
  if (checkType === 'DETERMINISTIC') return 'Deterministic'
  if (checkType === 'HEURISTIC') return 'Heuristic'
  if (checkType === 'SPATIAL_AI') return 'Spatial AI'
  return checkType || 'Rule'
}

/**
 * 判斷通道標題是否屬於差分通道
 */
const isDiffChannelTitle = (title: string | undefined): boolean => {
  if (!title) return false
  return title.includes('差分通道') || title.toUpperCase().includes('DIFF')
}

/**
 * 清理通道標題文字，移除冗餘的「 差分通道」字樣以配合 DIFF Tag 呈現
 */
const formatCleanChannelTitle = (title: string | undefined): string => {
  if (!title) return ''
  return title.replace(/\s*差分通道/g, '')
}

/**
 * 判斷受測元件是否為未上件 (Unmounted)
 */
const isUnmountedChip = (comp: string, item: ViolationItem): boolean => {
  if (comp.includes('[X]')) return true
  const ev = item.evidence_trail
  if (!ev) return false
  if (ev.is_mounted === false && (!ev.faulty_component || ev.faulty_component === comp)) {
    return true
  }
  return false
}

/**
 * 格式化受測元件標籤，若為未上件則確保附加 [X]
 */
const formatComponentChipLabel = (comp: string, item: ViolationItem): string => {
  if (comp.includes('[X]')) return comp
  if (isUnmountedChip(comp, item)) return `${comp} [X]`
  return comp
}
</script>
