<template>
  <div class="report-dashboard-container flex flex-col gap-3 mt-2 text-[#cccccc]">
    <!-- 1. 總結評分指標卡區塊 (支援點擊連動過濾) -->
    <div class="summary-cards-grid grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5">
      <!-- 總檢查規則 -->
      <div
        class="summary-card card-total bg-[#252526] rounded-md p-2.5 px-3 flex items-center gap-2.5 shadow-sm border cursor-pointer transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md"
        :class="currentFilter === 'ALL' ? 'border-primary ring-1 ring-primary' : 'border-[#333333] hover:border-[#4ec9b0]/50'"
        @click="currentFilter = 'ALL'"
      >
        <div class="card-icon text-xl text-[#858585] shrink-0"><i class="pi pi-list-check"></i></div>
        <div class="card-data flex flex-col">
          <span class="card-label text-[11px] text-[#858585]">總檢查規則</span>
          <span class="card-number text-lg font-bold text-white">{{ summary.total_rules_checked }}</span>
        </div>
      </div>

      <!-- 通過項目 (PASS) -->
      <div
        class="summary-card card-pass bg-[#252526] rounded-md p-2.5 px-3 flex items-center gap-2.5 shadow-sm border cursor-pointer transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md"
        :class="currentFilter === 'PASS' ? 'border-green-500 ring-1 ring-green-500' : 'border-[#333333] hover:border-green-500/50'"
        @click="currentFilter = 'PASS'"
      >
        <div class="card-icon text-xl text-green-400 shrink-0"><i class="pi pi-check-circle"></i></div>
        <div class="card-data flex flex-col">
          <span class="card-label text-[11px] text-[#858585]">通過項目 (PASS)</span>
          <span class="card-number text-lg font-bold text-green-400">{{ summary.pass_count }}</span>
        </div>
      </div>

      <!-- 違規項目 (FAIL) -->
      <div
        class="summary-card card-fail bg-[#252526] rounded-md p-2.5 px-3 flex items-center gap-2.5 shadow-sm border cursor-pointer transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md"
        :class="currentFilter === 'FAIL' ? 'border-red-500 ring-1 ring-red-500' : 'border-[#333333] hover:border-red-500/50'"
        @click="currentFilter = 'FAIL'"
      >
        <div class="card-icon text-xl text-red-400 shrink-0"><i class="pi pi-times-circle"></i></div>
        <div class="card-data flex flex-col">
          <span class="card-label text-[11px] text-[#858585]">違規項目 (FAIL)</span>
          <span class="card-number text-lg font-bold text-red-400">{{ summary.fail_count }}</span>
        </div>
      </div>

      <!-- 潛在風險 (WARN) -->
      <div
        class="summary-card card-warning bg-[#252526] rounded-md p-2.5 px-3 flex items-center gap-2.5 shadow-sm border cursor-pointer transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md"
        :class="currentFilter === 'WARNING' ? 'border-amber-500 ring-1 ring-amber-500' : 'border-[#333333] hover:border-amber-500/50'"
        @click="currentFilter = 'WARNING'"
      >
        <div class="card-icon text-xl text-amber-400 shrink-0"><i class="pi pi-exclamation-triangle"></i></div>
        <div class="card-data flex flex-col">
          <span class="card-label text-[11px] text-[#858585]">潛在風險 (WARN)</span>
          <span class="card-number text-lg font-bold text-amber-400">{{ summary.warning_count }}</span>
        </div>
      </div>

      <!-- 未觸發 (SKIPPED) -->
      <div
        class="summary-card card-skipped bg-[#252526] rounded-md p-2.5 px-3 flex items-center gap-2.5 shadow-sm border cursor-pointer transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md"
        :class="currentFilter === 'SKIPPED' ? 'border-surface-400 ring-1 ring-surface-400' : 'border-[#333333] hover:border-surface-400/50'"
        @click="currentFilter = 'SKIPPED'"
      >
        <div class="card-icon text-xl text-[#858585] shrink-0"><i class="pi pi-minus-circle"></i></div>
        <div class="card-data flex flex-col">
          <span class="card-label text-[11px] text-[#858585]">未觸發 (SKIPPED)</span>
          <span class="card-number text-lg font-bold text-[#858585]">{{ summary.skip_count }}</span>
        </div>
      </div>

      <!-- 總體通過率 -->
      <div class="summary-card card-rate bg-[#252526] rounded-md p-2.5 px-3 flex items-center gap-2.5 shadow-sm border border-[#333333]">
        <div class="card-icon text-xl text-sky-400 shrink-0"><i class="pi pi-percentage"></i></div>
        <div class="card-data flex flex-col">
          <span class="card-label text-[11px] text-[#858585]">總體通過率</span>
          <span class="card-number text-lg font-bold text-primary">{{ summary.pass_rate_percentage }}%</span>
        </div>
      </div>
    </div>

    <!-- 2. 分類通過分佈區塊 (Category Breakdown) -->
    <div v-if="Object.keys(summary.by_category || {}).length > 0" class="category-breakdown-card bg-[#252526] border border-[#333333] rounded-md p-2.5 px-3 flex flex-col gap-1.5">
      <h4 class="sub-title m-0 text-[11px] font-semibold text-[#a0a0a0] flex items-center tracking-wide uppercase">
        <i class="pi pi-chart-pie mr-1.5 text-primary"></i> 規則分類統計
      </h4>
      <div class="category-pills flex flex-wrap gap-1.5">
        <div
          v-for="(stat, catName) in summary.by_category"
          :key="catName"
          class="category-pill flex items-center gap-1.5 py-0.5 px-2.5 rounded bg-[#1e1e1e] border border-[#333333] text-xs hover:border-[#3c3c3c] transition-colors"
        >
          <span class="cat-title font-medium text-[#cccccc] text-[11px]">{{ catName }}</span>
          <span class="cat-stat-badge pass-badge text-[10px] px-1.5 py-0.2 rounded font-mono font-semibold bg-green-500/15 text-green-400 border border-green-500/30">PASS: {{ stat.pass }}</span>
          <span v-if="stat.fail > 0" class="cat-stat-badge fail-badge text-[10px] px-1.5 py-0.2 rounded font-mono font-semibold bg-red-500/15 text-red-400 border border-red-500/30">FAIL: {{ stat.fail }}</span>
          <span v-if="stat.warning > 0" class="cat-stat-badge warn-badge text-[10px] px-1.5 py-0.2 rounded font-mono font-semibold bg-amber-500/15 text-amber-400 border border-amber-500/30">WARN: {{ stat.warning }}</span>
          <span v-if="stat.skip && stat.skip > 0" class="cat-stat-badge skip-badge text-[10px] px-1.5 py-0.2 rounded font-mono font-semibold bg-surface-500/15 text-surface-400 border border-surface-500/30">SKIP: {{ stat.skip }}</span>
        </div>
      </div>
    </div>

    <!-- 3. 詳細檢測清單 (緊湊極簡版 + 規則歸類手風琴 + 平面清單切換) -->
    <div class="violations-table-card bg-[#252526] border border-[#333333] rounded-md p-3 flex flex-col gap-2.5">
      <!-- 標題與過濾工具列 -->
      <div class="table-header-row flex flex-col md:flex-row justify-between items-start md:items-center gap-2 pb-2 border-b border-[#333333]">
        <div class="flex items-center gap-2">
          <h3 class="card-title m-0 text-xs font-bold text-white flex items-center">
            <i class="pi pi-shield mr-1.5 text-primary"></i> 詳細檢測結果
          </h3>
        </div>

        <!-- 工具列群組 (過濾按鈕 + 檢視模式 + 展開收合 + 匯出) -->
        <div class="filter-toolbar flex items-center gap-2 flex-wrap text-xs">
          <!-- 過濾按鈕列 -->
          <div class="filter-btn-group flex items-center gap-1 flex-wrap">
            <button
              v-for="filter in filters"
              :key="filter.key"
              class="filter-pill-btn px-2 py-0.5 text-[11px] rounded border cursor-pointer transition-colors"
              :class="currentFilter === filter.key ? 'bg-primary/20 border-primary text-white font-semibold' : 'border-[#333333] bg-[#1e1e1e] text-[#858585] hover:text-[#cccccc] hover:bg-[#2a2d2e]'"
              @click="currentFilter = filter.key"
            >
              {{ filter.label }}
            </button>
          </div>

          <!-- 檢視模式切換 (規則分組 vs 平面清單) -->
          <div class="view-mode-toggle flex items-center bg-[#1e1e1e] border border-[#333333] rounded p-0.5 text-[11px]">
            <button
              type="button"
              class="view-mode-btn-grouped px-2 py-0.5 rounded transition-colors flex items-center gap-1 cursor-pointer"
              :class="viewMode === 'grouped' ? 'bg-primary/25 border border-primary/40 text-white font-medium' : 'text-[#858585] hover:text-[#cccccc]'"
              @click="viewMode = 'grouped'"
              title="依規則歸類分組展示"
            >
              <i class="pi pi-folder text-[10px]"></i>
              <span>規則分組</span>
            </button>
            <button
              type="button"
              class="view-mode-btn-flat px-2 py-0.5 rounded transition-colors flex items-center gap-1 cursor-pointer"
              :class="viewMode === 'flat' ? 'bg-primary/25 border border-primary/40 text-white font-medium' : 'text-[#858585] hover:text-[#cccccc]'"
              @click="viewMode = 'flat'"
              title="平鋪單行清單展示"
            >
              <i class="pi pi-list text-[10px]"></i>
              <span>平面清單</span>
            </button>
          </div>

          <!-- 批次展開 / 收合按鈕 (分組模式專用) -->
          <div v-if="viewMode === 'grouped'" class="batch-expand-btns flex items-center gap-1">
            <button
              type="button"
              class="btn-expand-all px-1.5 py-0.5 text-[11px] rounded border border-[#333333] bg-[#1e1e1e] text-[#858585] hover:text-white hover:bg-[#2a2d2e] cursor-pointer flex items-center gap-0.5"
              @click="expandAllRules"
              title="全部展開規則"
            >
              <i class="pi pi-angle-double-down text-[10px]"></i>
              <span>展開全部</span>
            </button>
            <button
              type="button"
              class="btn-collapse-all px-1.5 py-0.5 text-[11px] rounded border border-[#333333] bg-[#1e1e1e] text-[#858585] hover:text-white hover:bg-[#2a2d2e] cursor-pointer flex items-center gap-0.5"
              @click="collapseAllRules"
              title="全部收合規則"
            >
              <i class="pi pi-angle-double-up text-[10px]"></i>
              <span>收合全部</span>
            </button>
          </div>

          <!-- 匯出 JSON 按鈕 -->
          <Button
            label="匯出 JSON 報告"
            icon="pi pi-download"
            size="small"
            severity="secondary"
            class="text-[11px] py-0.5 px-2"
            @click="exportJsonReport"
          />
        </div>
      </div>

      <!-- 分頁資訊與控制列 (頂部) -->
      <div v-if="totalCount > 0" class="table-pagination-bar flex flex-wrap justify-between items-center text-[11px] text-[#858585] py-0.5 border-b border-[#333333]/50">
        <div class="pagination-info flex items-center gap-1.5">
          <span v-if="viewMode === 'grouped'">
            顯示第 <strong class="text-white">{{ pageStartIdx }}</strong> 至 <strong class="text-white">{{ pageEndIdx }}</strong> 條規則，共 <strong class="text-white">{{ totalCount }}</strong> 條規則（涵蓋 <strong class="text-white">{{ totalItemsCount }}</strong> 個受測項目）
          </span>
          <span v-else>
            顯示第 <strong class="text-white">{{ pageStartIdx }}</strong> 至 <strong class="text-white">{{ pageEndIdx }}</strong> 筆，共 <strong class="text-white">{{ totalCount }}</strong> 筆
          </span>
          <span v-if="currentFilter !== 'ALL'" class="text-primary-300">（已篩選）</span>
        </div>

        <div class="pagination-controls flex items-center gap-2">
          <div class="page-size-selector flex items-center gap-1">
            <span>每頁:</span>
            <select
              v-model="pageSize"
              class="bg-[#1e1e1e] border border-[#333333] text-[#cccccc] rounded px-1.5 py-0.5 text-[11px] outline-none cursor-pointer hover:border-[#3c3c3c]"
            >
              <option :value="25">25</option>
              <option :value="50">50</option>
              <option :value="100">100</option>
              <option :value="-1">全部</option>
            </select>
          </div>

          <div v-if="pageSize > 0 && totalPages > 1" class="page-nav-btns flex items-center gap-1">
            <button
              class="pagination-btn px-1.5 py-0.5 rounded border border-[#333333] bg-[#1e1e1e] text-[#cccccc] disabled:opacity-40 disabled:cursor-not-allowed hover:bg-[#2a2d2e] cursor-pointer text-[10px]"
              :disabled="currentPage <= 1"
              @click="currentPage--"
            >
              <i class="pi pi-chevron-left"></i>
            </button>
            <span class="px-1 text-white">{{ currentPage }} / {{ totalPages }}</span>
            <button
              class="pagination-btn px-1.5 py-0.5 rounded border border-[#333333] bg-[#1e1e1e] text-[#cccccc] disabled:opacity-40 disabled:cursor-not-allowed hover:bg-[#2a2d2e] cursor-pointer text-[10px]"
              :disabled="currentPage >= totalPages"
              @click="currentPage++"
            >
              <i class="pi pi-chevron-right"></i>
            </button>
          </div>
        </div>
      </div>

      <!-- 模式 A：依規則歸類分組檢視 (Grouped View - 預設推薦) -->
      <div v-if="viewMode === 'grouped'" class="rules-grouped-list flex flex-col gap-2">
        <div
          v-for="group in paginatedRuleGroups"
          :key="group.rule_id"
          class="rule-group-card rounded-md border bg-[#252526] flex flex-col transition-all duration-150 overflow-hidden"
          :class="getCardBorderClass(group.status)"
        >
          <!-- 規則卡片標頭 (Rule Header Row - 左邊框已有狀態顏色，移除重複狀態標籤) -->
          <div
            class="rule-group-header p-2 px-2.5 flex justify-between items-center gap-2 cursor-pointer select-none hover:bg-[#2a2d2e]/70 transition-colors"
            @click="toggleRuleGroup(group.rule_id)"
          >
            <!-- 左側標籤與規則名 -->
            <div class="rule-header-left flex items-center gap-1.5 flex-wrap text-xs min-w-0 flex-1">
              <!-- 嚴重性標籤 -->
              <span
                class="severity-indicator-tag text-[10px] font-semibold px-1.5 py-0.2 rounded shrink-0"
                :class="getSeverityBadgeClass(group.severity)"
              >
                {{ group.severity }}
              </span>

              <!-- 規則分類標籤 -->
              <span class="category-pill-tag text-[10px] px-1.5 py-0.2 rounded bg-[#1e1e1e] text-[#cccccc] border border-[#333333] shrink-0">
                {{ group.rule_category }}
              </span>

              <!-- 規則中文標題 -->
              <span class="rule-title font-semibold text-[#e2e8f0] text-xs truncate max-w-sm sm:max-w-md lg:max-w-lg" :title="group.rule_title">
                {{ group.rule_title }}
              </span>

              <!-- 規則代碼 -->
              <span class="rule-id font-mono text-[#858585] text-[10px] shrink-0">
                ({{ group.rule_id }})
              </span>

              <!-- 統計膠囊 (各狀態計數) -->
              <div class="group-stat-pills flex items-center gap-1 ml-auto sm:ml-1 shrink-0 text-[10px] font-mono">
                <span
                  v-if="group.fail_count > 0"
                  class="px-1.5 py-0.2 rounded bg-red-500/15 text-red-400 border border-red-500/30 font-semibold"
                >
                  {{ group.fail_count }} FAIL
                </span>
                <span
                  v-if="group.warning_count > 0"
                  class="px-1.5 py-0.2 rounded bg-amber-500/15 text-amber-400 border border-amber-500/30 font-semibold"
                >
                  {{ group.warning_count }} WARN
                </span>
                <span
                  v-if="group.pass_count > 0"
                  class="px-1.5 py-0.2 rounded bg-green-500/15 text-green-400 border border-green-500/30"
                >
                  {{ group.pass_count }} PASS
                </span>
                <span class="px-1.5 py-0.2 rounded bg-[#1e1e1e] text-[#858585] border border-[#333333]">
                  共 {{ group.total_count }} 組受測
                </span>
              </div>
            </div>

            <!-- 右側展開 / 收合按鈕 -->
            <div class="rule-header-right flex items-center shrink-0 ml-1">
              <button
                class="rule-expand-btn flex items-center gap-1 text-[11px] text-primary hover:text-primary-300 cursor-pointer bg-transparent border-0 p-0.5"
                @click.stop="toggleRuleGroup(group.rule_id)"
              >
                <span>{{ isRuleGroupExpanded(group) ? '收合' : '展開' }}</span>
                <i :class="isRuleGroupExpanded(group) ? 'pi pi-chevron-up' : 'pi pi-chevron-down'" class="text-[9px]"></i>
              </button>
            </div>
          </div>

          <!-- 規則展開區域 (Sub-items Container) -->
          <div
            v-show="isRuleGroupExpanded(group)"
            class="rule-group-body border-t border-[#333333] bg-[#1a1a1a] p-2 flex flex-col gap-1.5"
          >
            <!-- 受測項目清單 (每通道一行) -->
            <div class="group-sub-items flex flex-col gap-1.5">
              <div
                v-for="item in group.items"
                :key="item.item_id"
                class="violation-item rounded border bg-[#222222] hover:bg-[#282828] flex flex-col transition-colors overflow-hidden"
                :class="getCardBorderClass(item.status)"
              >
                <!-- 通道緊湊單行 (不重複顯示狀態標籤與規則標題) -->
                <div
                  class="item-compact-row py-1.5 px-2.5 flex justify-between items-center gap-2 cursor-pointer select-none text-xs"
                  @click="toggleExpand(item.item_id)"
                >
                  <div class="item-left flex items-center gap-2 flex-wrap min-w-0 flex-1">
                    <!-- 通道資訊 (純文字顯示，移除雙向箭頭圖標與外框) -->
                    <template v-if="item.evidence_trail && item.evidence_trail.channel_title">
                      <span
                        class="channel-title font-mono text-xs text-[#d4d4d4] font-medium truncate max-w-[360px]"
                        :title="item.evidence_trail.channel_title"
                      >
                        {{ formatChannelName(item.evidence_trail.channel_title) }}
                      </span>

                      <!-- 差分通道使用 PrimeVue 小 size DIFF Tag -->
                      <Tag
                        v-if="isDifferentialChannel(item)"
                        value="DIFF"
                        severity="info"
                        class="tag-diff text-[9px] px-1 py-0 font-mono font-bold leading-none shrink-0"
                      />
                    </template>

                    <!-- 非差分通道之普通節點快照與說明摘要 -->
                    <template v-else>
                      <span
                        v-for="c in item.target_nodes.components.slice(0, 3)"
                        :key="c"
                        class="node-chip text-[10px] font-mono px-1.5 py-0.2 rounded bg-[#1e1e1e] border border-[#3c3c3c] text-sky-400"
                      >
                        {{ c }}
                      </span>
                      <span
                        v-for="n in item.target_nodes.nets.slice(0, 2)"
                        :key="n"
                        class="node-chip text-[10px] font-mono px-1.5 py-0.2 rounded bg-[#1e1e1e] border border-[#3c3c3c] text-teal-300"
                      >
                        {{ n }}
                      </span>
                      <span
                        v-if="item.description"
                        class="item-desc-snippet text-[11px] text-[#858585] truncate max-w-[260px]"
                        :title="item.description"
                      >
                        {{ item.description }}
                      </span>
                    </template>

                    <!-- 違規原因快顯 (FAIL/WARN 單行快顯) -->
                    <span
                      v-if="item.error_message"
                      class="item-error-snip text-[11px] text-red-400 truncate max-w-[300px] font-medium"
                      :title="item.error_message"
                    >
                      <i class="pi pi-exclamation-circle mr-1 text-[10px]"></i>{{ item.error_message }}
                    </span>
                  </div>

                  <!-- 右側展開佐證按鈕 -->
                  <div class="item-right flex items-center shrink-0">
                    <button
                      class="expand-btn flex items-center gap-1 text-[11px] text-primary hover:text-primary-300 cursor-pointer bg-transparent border-0 p-0.5 transition-colors"
                      @click.stop="toggleExpand(item.item_id)"
                    >
                      <span>{{ expandedItems[item.item_id] ? '收合' : '佐證拓撲' }}</span>
                      <i :class="expandedItems[item.item_id] ? 'pi pi-chevron-up' : 'pi pi-chevron-down'" class="text-[9px]"></i>
                    </button>
                  </div>
                </div>

                <!-- 展開之完整佐證區塊 -->
                <EvidenceDetailsBlock
                  v-if="expandedItems[item.item_id]"
                  :item="item"
                />
              </div>
            </div>
          </div>
        </div>

        <!-- 空狀態通知 -->
        <div v-if="ruleGroups.length === 0" class="empty-items-notice p-6 text-center text-[#858585] flex flex-col items-center gap-2 text-xs">
          <i class="pi pi-inbox text-2xl text-[#666666]"></i>
          <span>目前過濾條件下無任何符合項目</span>
        </div>
      </div>

      <!-- 模式 B：平面清單檢視 (Flat List View - 保留舊有比對習慣) -->
      <div v-else class="items-list flex flex-col gap-1.5">
        <div
          v-for="item in paginatedItems"
          :key="item.item_id"
          class="violation-item rounded border bg-[#252526] hover:bg-[#2a2d2e]/80 flex flex-col transition-all duration-150 overflow-hidden"
          :class="getCardBorderClass(item.status)"
        >
          <!-- 單行摘要列 (左邊框已有狀態顏色，移除重複狀態標籤) -->
          <div
            class="item-compact-row py-1.5 px-2.5 flex justify-between items-center gap-2 cursor-pointer select-none"
            @click="toggleExpand(item.item_id)"
          >
            <!-- 左側標籤與標題 -->
            <div class="item-left flex items-center gap-1.5 flex-wrap text-xs min-w-0 flex-1">
              <!-- 嚴重性標籤 -->
              <span
                class="severity-indicator-tag text-[9px] font-semibold px-1.5 py-0.2 rounded shrink-0"
                :class="getSeverityBadgeClass(item.severity)"
              >
                {{ item.severity }}
              </span>

              <!-- 規則分類標籤 -->
              <span class="category-pill-tag text-[9px] px-1.5 py-0.2 rounded bg-[#1e1e1e] text-[#cccccc] border border-[#333333] shrink-0">
                {{ item.rule_category }}
              </span>

              <!-- 規則中文標題 (平面模式保留作為識別) -->
              <span class="item-title font-semibold text-[#e2e8f0] text-xs truncate max-w-md" :title="item.rule_title">
                {{ item.rule_title }}
              </span>

              <!-- 規則代碼 -->
              <span class="item-rule-id font-mono text-[#858585] text-[10px] shrink-0">
                ({{ item.rule_id }})
              </span>

              <!-- 受測節點快照標籤 -->
              <div class="target-quick-badges flex items-center gap-1.5 shrink-0 ml-auto md:ml-1">
                <!-- 通道資訊 (純文字顯示 + 小 size DIFF Tag，無圖標無外框) -->
                <template v-if="item.evidence_trail && item.evidence_trail.channel_title">
                  <span
                    class="channel-title font-mono text-[10px] text-[#d4d4d4] font-medium truncate max-w-[260px]"
                    :title="item.evidence_trail.channel_title"
                  >
                    {{ formatChannelName(item.evidence_trail.channel_title) }}
                  </span>
                  <Tag
                    v-if="isDifferentialChannel(item)"
                    value="DIFF"
                    severity="info"
                    class="tag-diff text-[9px] px-1 py-0 font-mono font-bold leading-none shrink-0"
                  />
                </template>

                <!-- 普通節點快照 -->
                <template v-else>
                  <span
                    v-for="c in item.target_nodes.components.slice(0, 2)"
                    :key="c"
                    class="node-chip text-[9px] font-mono px-1.5 py-0.2 rounded bg-[#1e1e1e] border border-[#3c3c3c] text-sky-400"
                    :title="`受測元件: ${c}`"
                  >
                    {{ c }}
                  </span>
                  <span
                    v-for="n in item.target_nodes.nets.slice(0, 1)"
                    :key="n"
                    class="node-chip text-[9px] font-mono px-1.5 py-0.2 rounded bg-[#1e1e1e] border border-[#3c3c3c] text-teal-300"
                    :title="`受測網路: ${n}`"
                  >
                    {{ n }}
                  </span>
                </template>
              </div>
            </div>

            <!-- 右側展開按鈕 -->
            <div class="item-right flex items-center shrink-0">
              <button
                class="expand-btn flex items-center gap-1 text-[11px] text-primary hover:text-primary-300 cursor-pointer bg-transparent border-0 p-0.5 transition-colors"
                @click.stop="toggleExpand(item.item_id)"
              >
                <span>{{ expandedItems[item.item_id] ? '收合' : '詳情' }}</span>
                <i :class="expandedItems[item.item_id] ? 'pi pi-chevron-up' : 'pi pi-chevron-down'" class="text-[9px]"></i>
              </button>
            </div>
          </div>

          <!-- 展開佐證歷程 -->
          <EvidenceDetailsBlock
            v-if="expandedItems[item.item_id]"
            :item="item"
          />
        </div>

        <!-- 空狀態通知 -->
        <div v-if="sortedFilteredItems.length === 0" class="empty-items-notice p-6 text-center text-[#858585] flex flex-col items-center gap-2 text-xs">
          <i class="pi pi-inbox text-2xl text-[#666666]"></i>
          <span>目前過濾條件下無任何項目</span>
        </div>
      </div>

      <!-- 分頁控制列 (底部) -->
      <div v-if="pageSize > 0 && totalPages > 1" class="table-pagination-bar-bottom flex justify-between items-center text-[11px] text-[#858585] pt-1.5 border-t border-[#333333]/50">
        <span>第 {{ currentPage }} / {{ totalPages }} 頁</span>
        <div class="page-nav-btns flex items-center gap-1">
          <button
            class="pagination-btn px-2 py-0.5 rounded border border-[#333333] bg-[#1e1e1e] text-[#cccccc] disabled:opacity-40 disabled:cursor-not-allowed hover:bg-[#2a2d2e] cursor-pointer text-[10px]"
            :disabled="currentPage <= 1"
            @click="changePage(currentPage - 1)"
          >
            上一頁
          </button>
          <button
            class="pagination-btn px-2 py-0.5 rounded border border-[#333333] bg-[#1e1e1e] text-[#cccccc] disabled:opacity-40 disabled:cursor-not-allowed hover:bg-[#2a2d2e] cursor-pointer text-[10px]"
            :disabled="currentPage >= totalPages"
            @click="changePage(currentPage + 1)"
          >
            下一頁
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * @file TaskReportDashboard.vue
 * @description 符合 docs/report_schema.md 標準之 DRC 最終檢測報告視覺化 Dashboard 元件
 * 採用 2026 最新 EDA/DRC UX 最佳實踐：極簡緊湊風格、規則聚合手風琴、異常優先置頂與雙檢視模式切換
 */

import { ref, computed, watch } from 'vue'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import EvidenceDetailsBlock from './EvidenceDetailsBlock.vue'

defineOptions({
  name: 'TaskReportDashboard',
})

export interface FlowDevice {
  ref_des: string
  pin?: string
  part_number?: string
  type?: string
}

export interface FlowStageEndpoints {
  stage: 'endpoints'
  net: string
  devices: FlowDevice[]
}

export interface FlowStagePassThrough {
  stage: 'pass_through'
  component: string
  type?: string
  in_pin?: string
  out_pin?: string
  from_net: string
  to_net: string
}

export type TopologyFlowStage = FlowStageEndpoints | FlowStagePassThrough

export interface TargetNodes {
  components: string[]
  nets: string[]
  page_indices?: number[]
}

export interface ViolationItem {
  item_id: string
  rule_id: string
  rule_category: string
  rule_title: string
  check_type: 'HEURISTIC' | 'LLM' | string
  status: 'PASS' | 'FAIL' | 'WARNING' | 'SKIPPED' | 'ERROR'
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO' | string
  target_nodes: TargetNodes
  error_message: string
  recommendation?: string
  description?: string
  comment?: string
  evidence_trail: Record<string, any>
}

export interface ReportSummary {
  total_rules_checked: number
  pass_count: number
  fail_count: number
  warning_count: number
  skip_count: number
  pass_rate_percentage: number
  by_category: Record<string, { pass: number; fail: number; warning: number; skip?: number }>
}

export interface RuleGroup {
  rule_id: string
  rule_title: string
  rule_category: string
  severity: string
  status: 'PASS' | 'FAIL' | 'WARNING' | 'SKIPPED' | 'ERROR'
  description?: string
  items: ViolationItem[]
  pass_count: number
  fail_count: number
  warning_count: number
  skip_count: number
  total_count: number
}

interface Props {
  taskId: string
  summary: ReportSummary
  violations: ViolationItem[]
}

const props = withDefaults(defineProps<Props>(), {
  taskId: '',
  summary: () => ({
    total_rules_checked: 0,
    pass_count: 0,
    fail_count: 0,
    warning_count: 0,
    skip_count: 0,
    pass_rate_percentage: 0.0,
    by_category: {},
  }),
  violations: () => [],
})

// 檢視模式切換：'grouped' (依規則歸類) | 'flat' (平面清單)
const viewMode = ref<'grouped' | 'flat'>('grouped')

// 規則群組展開狀態管理
const expandedRuleGroups = ref<Record<string, boolean>>({})

// 個別受測項目佐證歷程展開狀態管理
const expandedItems = ref<Record<string, boolean>>({})

// 過濾條件
const currentFilter = ref<string>('ALL')

// 分頁控制
const currentPage = ref<number>(1)
const pageSize = ref<number>(50)

const filters = [
  { key: 'ALL', label: '全部項目' },
  { key: 'FAIL', label: '違規項目 (FAIL)' },
  { key: 'WARNING', label: '潛在風險 (WARN)' },
  { key: 'PASS', label: '通過項目 (PASS)' },
  { key: 'SKIPPED', label: '略過/未觸發 (SKIPPED)' },
  { key: 'LLM', label: '本地 LLM 推理' },
  { key: 'HEURISTIC', label: '傳統圖論演算法' },
]

/**
 * 依條件過濾原始清單
 */
const rawFilteredItems = computed(() => {
  if (currentFilter.value === 'ALL') return props.violations
  if (currentFilter.value === 'FAIL') return props.violations.filter((v) => v.status === 'FAIL')
  if (currentFilter.value === 'WARNING')
    return props.violations.filter((v) => v.status === 'WARNING')
  if (currentFilter.value === 'PASS') return props.violations.filter((v) => v.status === 'PASS')
  if (currentFilter.value === 'SKIPPED') return props.violations.filter((v) => v.status === 'SKIPPED')
  if (currentFilter.value === 'LLM') return props.violations.filter((v) => v.check_type === 'LLM')
  if (currentFilter.value === 'HEURISTIC')
    return props.violations.filter((v) => v.check_type === 'HEURISTIC' || v.check_type.startsWith('LEVEL3'))
  return props.violations
})

/**
 * 異常優先置頂排序 (FAIL / ERROR > WARNING > SKIPPED > PASS)
 */
const statusPriority: Record<string, number> = {
  FAIL: 1,
  ERROR: 1,
  WARNING: 2,
  SKIPPED: 3,
  PASS: 4,
}

const sortedFilteredItems = computed(() => {
  return [...rawFilteredItems.value].sort((a, b) => {
    const pA = statusPriority[a.status] || 99
    const pB = statusPriority[b.status] || 99
    return pA - pB
  })
})

/**
 * 依規則歸類聚合清單 (Rule Groups)
 */
const ruleGroups = computed<RuleGroup[]>(() => {
  const groupMap = new Map<string, RuleGroup>()

  for (const item of rawFilteredItems.value) {
    if (!groupMap.has(item.rule_id)) {
      groupMap.set(item.rule_id, {
        rule_id: item.rule_id,
        rule_title: item.rule_title,
        rule_category: item.rule_category,
        severity: item.severity,
        status: 'PASS',
        description: item.description,
        items: [],
        pass_count: 0,
        fail_count: 0,
        warning_count: 0,
        skip_count: 0,
        total_count: 0,
      })
    }

    const group = groupMap.get(item.rule_id)!
    group.items.push(item)
    group.total_count++

    if (item.status === 'PASS') group.pass_count++
    else if (item.status === 'FAIL' || item.status === 'ERROR') group.fail_count++
    else if (item.status === 'WARNING') group.warning_count++
    else if (item.status === 'SKIPPED') group.skip_count++

    // 最壞情況判定
    if (group.status !== 'FAIL') {
      if (item.status === 'FAIL' || item.status === 'ERROR') {
        group.status = 'FAIL'
      } else if (item.status === 'WARNING' && group.status !== 'FAIL') {
        group.status = 'WARNING'
      } else if (item.status === 'SKIPPED' && group.status !== 'WARNING' && group.pass_count === 0) {
        group.status = 'SKIPPED'
      }
    }
  }

  // 內部通道依嚴重度優先排序
  for (const group of groupMap.values()) {
    group.items.sort((a, b) => (statusPriority[a.status] || 99) - (statusPriority[b.status] || 99))
  }

  // 外層規則群組依最壞狀態排序 (FAIL 規則置頂)
  return Array.from(groupMap.values()).sort((a, b) => {
    return (statusPriority[a.status] || 99) - (statusPriority[b.status] || 99)
  })
})

/**
 * 判斷規則卡片是否展開
 * 異常 (FAIL/WARN) 預設展開；若全為 PASS 但僅有 1 條規則亦預設展開
 */
const isRuleGroupExpanded = (group: RuleGroup): boolean => {
  if (expandedRuleGroups.value[group.rule_id] !== undefined) {
    return expandedRuleGroups.value[group.rule_id]
  }
  if (group.status === 'FAIL' || group.status === 'WARNING') return true
  if (ruleGroups.value.length === 1) return true
  return false
}

/**
 * 切換單條規則展開/收合
 */
const toggleRuleGroup = (ruleId: string) => {
  const grp = ruleGroups.value.find((g) => g.rule_id === ruleId)
  const current = grp ? isRuleGroupExpanded(grp) : false
  expandedRuleGroups.value[ruleId] = !current
}

/**
 * 批次操作：展開全部規則
 */
const expandAllRules = () => {
  ruleGroups.value.forEach((g) => {
    expandedRuleGroups.value[g.rule_id] = true
  })
}

/**
 * 批次操作：收合全部規則
 */
const collapseAllRules = () => {
  ruleGroups.value.forEach((g) => {
    expandedRuleGroups.value[g.rule_id] = false
  })
}

// 分頁衍生運算
const totalCount = computed(() => {
  return viewMode.value === 'grouped' ? ruleGroups.value.length : sortedFilteredItems.value.length
})

const totalItemsCount = computed(() => sortedFilteredItems.value.length)

const totalPages = computed(() => {
  if (pageSize.value <= 0) return 1
  return Math.ceil(totalCount.value / pageSize.value) || 1
})

const pageStartIdx = computed(() => {
  if (totalCount.value === 0) return 0
  if (pageSize.value <= 0) return 1
  return (currentPage.value - 1) * pageSize.value + 1
})

const pageEndIdx = computed(() => {
  if (pageSize.value <= 0) return totalCount.value
  return Math.min(currentPage.value * pageSize.value, totalCount.value)
})

const paginatedRuleGroups = computed(() => {
  if (pageSize.value <= 0) return ruleGroups.value
  const start = (currentPage.value - 1) * pageSize.value
  return ruleGroups.value.slice(start, start + pageSize.value)
})

const paginatedItems = computed(() => {
  if (pageSize.value <= 0) return sortedFilteredItems.value
  const start = (currentPage.value - 1) * pageSize.value
  return sortedFilteredItems.value.slice(start, start + pageSize.value)
})

// 當過濾條件或檢視模式變更時自動重設回第一頁
watch([currentFilter, pageSize, viewMode], () => {
  currentPage.value = 1
})

/**
 * 切換頁碼
 */
const changePage = (page: number) => {
  if (page >= 1 && page <= totalPages.value) {
    currentPage.value = page
  }
}

/**
 * 卡片邊框樣式類
 */
const getCardBorderClass = (status: string): string => {
  switch (status) {
    case 'FAIL':
      return 'border-l-4 border-l-red-500 border-[#333333]'
    case 'WARNING':
      return 'border-l-4 border-l-amber-500 border-[#333333]'
    case 'PASS':
      return 'border-l-4 border-l-green-500 border-[#333333]'
    case 'SKIPPED':
      return 'border-l-4 border-l-[#6e7681] border-[#333333]'
    default:
      return 'border-l-4 border-l-surface-500 border-[#333333]'
  }
}

/**
 * 狀態標籤樣式
 */
const getStatusBadgeClass = (status: string): string => {
  switch (status) {
    case 'FAIL':
      return 'bg-red-500/20 text-red-400 border border-red-500/30'
    case 'WARNING':
      return 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
    case 'PASS':
      return 'bg-green-500/20 text-green-400 border border-green-500/30'
    case 'SKIPPED':
      return 'bg-surface-500/20 text-surface-400 border border-surface-500/30'
    default:
      return 'bg-surface-500/20 text-surface-300'
  }
}

/**
 * 嚴重性標籤樣式
 */
const getSeverityBadgeClass = (severity: string): string => {
  switch (severity?.toUpperCase()) {
    case 'CRITICAL':
    case 'FATAL':
      return 'bg-red-500/25 text-red-300 border border-red-500/40'
    case 'HIGH':
    case 'ERROR':
      return 'bg-red-500/15 text-red-400 border border-red-500/30'
    case 'MEDIUM':
    case 'WARNING':
      return 'bg-amber-500/15 text-amber-300 border border-amber-500/30'
    case 'LOW':
      return 'bg-sky-500/15 text-sky-300 border border-sky-500/30'
    default:
      return 'bg-[#1e1e1e] text-[#858585] border border-[#333333]'
  }
}

/**
 * 格式化通道名稱文字 (去除冗餘的 "差分通道" 字樣)
 */
const formatChannelName = (title: string): string => {
  if (!title) return ''
  return title.replace(/\s*差分通道/g, '').trim()
}

/**
 * 判斷受測項目是否為差分通道
 */
const isDifferentialChannel = (item: ViolationItem): boolean => {
  const title = item.evidence_trail?.channel_title || ''
  const pairType = item.evidence_trail?.pair_type || ''
  return (
    title.includes('差分') ||
    pairType.toLowerCase().includes('diff') ||
    Boolean(item.evidence_trail?.p_net && item.evidence_trail?.n_net)
  )
}

/**
 * 切換受測通道佐證展開狀態
 */
const toggleExpand = (itemId: string) => {
  expandedItems.value[itemId] = !expandedItems.value[itemId]
}

/**
 * 匯出完整 JSON 報告
 */
const exportJsonReport = () => {
  const dataStr =
    'data:text/json;charset=utf-8,' +
    encodeURIComponent(
      JSON.stringify(
        {
          task_id: props.taskId,
          summary: props.summary,
          violations: props.violations,
        },
        null,
        2
      )
    )
  const downloadAnchor = document.createElement('a')
  downloadAnchor.setAttribute('href', dataStr)
  downloadAnchor.setAttribute('download', `drc_report_${props.taskId || 'export'}.json`)
  document.body.appendChild(downloadAnchor)
  downloadAnchor.click()
  downloadAnchor.remove()
}
</script>
