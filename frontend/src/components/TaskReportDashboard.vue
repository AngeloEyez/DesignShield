<template>
  <div class="report-dashboard-container flex flex-col gap-5 mt-4 text-[#cccccc]">
    <!-- 1. 總結評分指標卡區塊 (支援點擊連動過濾) -->
    <div class="summary-cards-grid grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3.5">
      <!-- 總檢查規則 -->
      <div
        class="summary-card card-total bg-[#252526] rounded-md p-3.5 flex items-center gap-3.5 shadow-sm border cursor-pointer transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md"
        :class="currentFilter === 'ALL' ? 'border-primary ring-1 ring-primary' : 'border-[#333333] hover:border-[#4ec9b0]/50'"
        @click="currentFilter = 'ALL'"
      >
        <div class="card-icon text-2xl text-[#858585] shrink-0"><i class="pi pi-list-check"></i></div>
        <div class="card-data flex flex-col">
          <span class="card-label text-xs text-[#858585] mb-0.5">總檢查規則</span>
          <span class="card-number text-xl font-bold text-white">{{ summary.total_rules_checked }}</span>
        </div>
      </div>

      <!-- 通過項目 (PASS) -->
      <div
        class="summary-card card-pass bg-[#252526] rounded-md p-3.5 flex items-center gap-3.5 shadow-sm border cursor-pointer transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md"
        :class="currentFilter === 'PASS' ? 'border-green-500 ring-1 ring-green-500' : 'border-[#333333] hover:border-green-500/50'"
        @click="currentFilter = 'PASS'"
      >
        <div class="card-icon text-2xl text-green-400 shrink-0"><i class="pi pi-check-circle"></i></div>
        <div class="card-data flex flex-col">
          <span class="card-label text-xs text-[#858585] mb-0.5">通過項目 (PASS)</span>
          <span class="card-number text-xl font-bold text-green-400">{{ summary.pass_count }}</span>
        </div>
      </div>

      <!-- 違規項目 (FAIL) -->
      <div
        class="summary-card card-fail bg-[#252526] rounded-md p-3.5 flex items-center gap-3.5 shadow-sm border cursor-pointer transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md"
        :class="currentFilter === 'FAIL' ? 'border-red-500 ring-1 ring-red-500' : 'border-[#333333] hover:border-red-500/50'"
        @click="currentFilter = 'FAIL'"
      >
        <div class="card-icon text-2xl text-red-400 shrink-0"><i class="pi pi-times-circle"></i></div>
        <div class="card-data flex flex-col">
          <span class="card-label text-xs text-[#858585] mb-0.5">違規項目 (FAIL)</span>
          <span class="card-number text-xl font-bold text-red-400">{{ summary.fail_count }}</span>
        </div>
      </div>

      <!-- 潛在風險 (WARN) -->
      <div
        class="summary-card card-warning bg-[#252526] rounded-md p-3.5 flex items-center gap-3.5 shadow-sm border cursor-pointer transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md"
        :class="currentFilter === 'WARNING' ? 'border-amber-500 ring-1 ring-amber-500' : 'border-[#333333] hover:border-amber-500/50'"
        @click="currentFilter = 'WARNING'"
      >
        <div class="card-icon text-2xl text-amber-400 shrink-0"><i class="pi pi-exclamation-triangle"></i></div>
        <div class="card-data flex flex-col">
          <span class="card-label text-xs text-[#858585] mb-0.5">潛在風險 (WARN)</span>
          <span class="card-number text-xl font-bold text-amber-400">{{ summary.warning_count }}</span>
        </div>
      </div>

      <!-- 未觸發 (SKIPPED) -->
      <div
        class="summary-card card-skipped bg-[#252526] rounded-md p-3.5 flex items-center gap-3.5 shadow-sm border cursor-pointer transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md"
        :class="currentFilter === 'SKIPPED' ? 'border-surface-400 ring-1 ring-surface-400' : 'border-[#333333] hover:border-surface-400/50'"
        @click="currentFilter = 'SKIPPED'"
      >
        <div class="card-icon text-2xl text-[#858585] shrink-0"><i class="pi pi-minus-circle"></i></div>
        <div class="card-data flex flex-col">
          <span class="card-label text-xs text-[#858585] mb-0.5">未觸發 (SKIPPED)</span>
          <span class="card-number text-xl font-bold text-[#858585]">{{ summary.skip_count }}</span>
        </div>
      </div>

      <!-- 總體通過率 -->
      <div class="summary-card card-rate bg-[#252526] rounded-md p-3.5 flex items-center gap-3.5 shadow-sm border border-[#333333]">
        <div class="card-icon text-2xl text-sky-400 shrink-0"><i class="pi pi-percentage"></i></div>
        <div class="card-data flex flex-col">
          <span class="card-label text-xs text-[#858585] mb-0.5">總體通過率</span>
          <span class="card-number text-xl font-bold text-primary">{{ summary.pass_rate_percentage }}%</span>
        </div>
      </div>
    </div>

    <!-- 2. 分類通過分佈區塊 (Category Breakdown) -->
    <div v-if="Object.keys(summary.by_category || {}).length > 0" class="category-breakdown-card bg-[#252526] border border-[#333333] rounded-md p-4 flex flex-col gap-2.5">
      <h4 class="sub-title m-0 text-xs font-semibold text-white flex items-center tracking-wide uppercase">
        <i class="pi pi-chart-pie mr-2 text-primary"></i> 各類別規則檢查分佈 (Category Breakdown)
      </h4>
      <div class="category-pills flex flex-wrap gap-2">
        <div
          v-for="(stat, catName) in summary.by_category"
          :key="catName"
          class="category-pill flex items-center gap-2 py-1.5 px-3 rounded bg-[#1e1e1e] border border-[#333333] text-xs hover:border-[#3c3c3c] transition-colors"
        >
          <span class="cat-title font-medium text-[#cccccc]">{{ catName }}</span>
          <span class="cat-stat-badge pass-badge text-[10px] px-1.5 py-0.5 rounded font-mono font-semibold bg-green-500/15 text-green-400 border border-green-500/30">PASS: {{ stat.pass }}</span>
          <span v-if="stat.fail > 0" class="cat-stat-badge fail-badge text-[10px] px-1.5 py-0.5 rounded font-mono font-semibold bg-red-500/15 text-red-400 border border-red-500/30">FAIL: {{ stat.fail }}</span>
          <span v-if="stat.warning > 0" class="cat-stat-badge warn-badge text-[10px] px-1.5 py-0.5 rounded font-mono font-semibold bg-amber-500/15 text-amber-400 border border-amber-500/30">WARN: {{ stat.warning }}</span>
          <span v-if="stat.skip && stat.skip > 0" class="cat-stat-badge skip-badge text-[10px] px-1.5 py-0.5 rounded font-mono font-semibold bg-surface-500/15 text-surface-400 border border-surface-500/30">SKIP: {{ stat.skip }}</span>
        </div>
      </div>
    </div>

    <!-- 3. 詳細檢測清單 (簡約單行清單 + 異常置頂 + 原地下拉折疊) -->
    <div class="violations-table-card bg-[#252526] border border-[#333333] rounded-md p-4 flex flex-col gap-3.5">
      <!-- 標題與過濾工具列 -->
      <div class="table-header-row flex flex-col md:flex-row justify-between items-start md:items-center gap-3 pb-3 border-b border-[#333333]">
        <div>
          <h3 class="card-title m-0 text-sm font-bold text-white flex items-center">
            <i class="pi pi-shield mr-2 text-primary"></i> 詳細檢測結果與工程改善建議
          </h3>
          <p class="card-desc m-0 text-xs text-[#858585] mt-1">
            預設異常項目優先置頂展示。點選任一項目可展開受測節點與完整驗證歷程佐證
          </p>
        </div>

        <!-- 過濾按鈕列 -->
        <div class="filter-btn-group flex items-center gap-1.5 flex-wrap">
          <button
            v-for="filter in filters"
            :key="filter.key"
            class="filter-pill-btn px-2.5 py-1 text-xs rounded border cursor-pointer transition-colors"
            :class="currentFilter === filter.key ? 'bg-primary/20 border-primary text-white font-semibold' : 'border-[#333333] bg-[#1e1e1e] text-[#858585] hover:text-[#cccccc] hover:bg-[#2a2d2e]'"
            @click="currentFilter = filter.key"
          >
            {{ filter.label }}
          </button>
          <Button
            label="匯出 JSON 報告"
            icon="pi pi-download"
            size="small"
            severity="secondary"
            class="text-xs"
            @click="exportJsonReport"
          />
        </div>
      </div>

      <!-- 分頁資訊與控制列 (頂部) -->
      <div v-if="totalCount > 0" class="table-pagination-bar flex flex-wrap justify-between items-center text-xs text-[#858585] py-1 border-b border-[#333333]/50">
        <div class="pagination-info flex items-center gap-1.5">
          <span>顯示第 <strong class="text-white">{{ pageStartIdx }}</strong> 至 <strong class="text-white">{{ pageEndIdx }}</strong> 筆，共 <strong class="text-white">{{ totalCount }}</strong> 筆</span>
          <span v-if="currentFilter !== 'ALL'" class="text-primary-300">（已套用篩選）</span>
        </div>

        <div class="pagination-controls flex items-center gap-3">
          <div class="page-size-selector flex items-center gap-1">
            <span>每頁顯示:</span>
            <select
              v-model="pageSize"
              class="bg-[#1e1e1e] border border-[#333333] text-[#cccccc] rounded px-1.5 py-0.5 text-xs outline-none cursor-pointer hover:border-[#3c3c3c]"
            >
              <option :value="25">25 筆</option>
              <option :value="50">50 筆</option>
              <option :value="100">100 筆</option>
              <option :value="-1">全部</option>
            </select>
          </div>

          <div v-if="pageSize > 0 && totalPages > 1" class="page-nav-btns flex items-center gap-1">
            <button
              class="pagination-btn px-2 py-0.5 rounded border border-[#333333] bg-[#1e1e1e] text-[#cccccc] disabled:opacity-40 disabled:cursor-not-allowed hover:bg-[#2a2d2e] cursor-pointer text-xs"
              :disabled="currentPage <= 1"
              @click="currentPage--"
            >
              <i class="pi pi-chevron-left text-[10px]"></i>
            </button>
            <span class="px-1 text-white">{{ currentPage }} / {{ totalPages }}</span>
            <button
              class="pagination-btn px-2 py-0.5 rounded border border-[#333333] bg-[#1e1e1e] text-[#cccccc] disabled:opacity-40 disabled:cursor-not-allowed hover:bg-[#2a2d2e] cursor-pointer text-xs"
              :disabled="currentPage >= totalPages"
              @click="currentPage++"
            >
              <i class="pi pi-chevron-right text-[10px]"></i>
            </button>
          </div>
        </div>
      </div>

      <!-- 檢驗清單 (Compact Row + VS Code Dark Theme) -->
      <div class="items-list flex flex-col gap-2">
        <div
          v-for="item in paginatedItems"
          :key="item.item_id"
          class="violation-item rounded-md border bg-[#252526] hover:bg-[#2a2d2e]/80 flex flex-col transition-all duration-150 overflow-hidden"
          :class="getCardBorderClass(item.status)"
        >
          <!-- 單行摘要列 (點擊整行或按鈕皆可切換展開) -->
          <div
            class="item-compact-row p-2.5 px-3 flex justify-between items-center gap-2.5 cursor-pointer select-none"
            @click="toggleExpand(item.item_id)"
          >
            <!-- 左側標籤與標題 -->
            <div class="item-left flex items-center gap-2 flex-wrap text-xs min-w-0 flex-1">
              <!-- 狀態標籤 -->
              <span
                class="status-indicator-tag text-[10px] font-bold px-1.5 py-0.5 rounded uppercase tracking-wider shrink-0"
                :class="getStatusBadgeClass(item.status)"
              >
                {{ item.status }}
              </span>

              <!-- 嚴重性標籤 -->
              <span
                class="severity-indicator-tag text-[10px] font-semibold px-1.5 py-0.5 rounded shrink-0"
                :class="getSeverityBadgeClass(item.severity)"
              >
                {{ item.severity }}
              </span>

              <!-- 規則分類標籤 -->
              <span class="category-pill-tag text-[10px] px-1.5 py-0.5 rounded bg-[#1e1e1e] text-[#cccccc] border border-[#333333] shrink-0">
                {{ item.rule_category }}
              </span>

              <!-- 規則中文標題 (高對比亮白灰，消除深藍看不清問題) -->
              <span class="item-title font-semibold text-[#e2e8f0] text-xs truncate max-w-md" :title="item.rule_title">
                {{ item.rule_title }}
              </span>

              <!-- 規則代碼 -->
              <span class="item-rule-id font-mono text-[#858585] text-[11px] shrink-0">
                ({{ item.rule_id }})
              </span>

              <!-- 受測節點快照標籤 -->
              <div class="target-quick-badges flex items-center gap-1 shrink-0 ml-auto md:ml-1">
                <!-- 若為端到端通道規則，呈現精準通道標籤 (P72 ↔ TJ1) -->
                <span
                  v-if="item.evidence_trail && item.evidence_trail.channel_title"
                  class="channel-chip text-[10px] font-mono px-2 py-0.5 rounded bg-sky-500/15 border border-sky-500/30 text-sky-300 font-semibold max-w-[280px] truncate"
                  :title="`端到端通道: ${item.evidence_trail.channel_title}`"
                >
                  <i class="pi pi-arrows-h mr-1 text-[9px]"></i>{{ item.evidence_trail.channel_title }}
                </span>

                <!-- 普通節點快照 -->
                <template v-else>
                  <span
                    v-for="c in item.target_nodes.components.slice(0, 2)"
                    :key="c"
                    class="node-chip text-[10px] font-mono px-1.5 py-0.2 rounded bg-[#1e1e1e] border border-[#3c3c3c] text-sky-400"
                    :title="`受測元件: ${c}`"
                  >
                    {{ c }}
                  </span>
                  <span
                    v-if="item.target_nodes.components.length > 2"
                    class="text-[10px] text-[#858585]"
                  >
                    +{{ item.target_nodes.components.length - 2 }}
                  </span>

                  <span
                    v-for="n in item.target_nodes.nets.slice(0, 1)"
                    :key="n"
                    class="node-chip text-[10px] font-mono px-1.5 py-0.2 rounded bg-[#1e1e1e] border border-[#3c3c3c] text-teal-300"
                    :title="`受測網路: ${n}`"
                  >
                    {{ n }}
                  </span>
                  <span
                    v-if="item.target_nodes.nets.length > 1"
                    class="text-[10px] text-[#858585]"
                  >
                    +{{ item.target_nodes.nets.length - 1 }}
                  </span>
                </template>
              </div>
            </div>

            <!-- 右側展開按鈕 -->
            <div class="item-right flex items-center shrink-0">
              <button
                class="expand-btn flex items-center gap-1 text-xs text-primary hover:text-primary-300 cursor-pointer bg-transparent border-0 p-1 transition-colors"
                @click.stop="toggleExpand(item.item_id)"
              >
                <span>{{ expandedItems[item.item_id] ? '收合' : '詳情' }}</span>
                <i :class="expandedItems[item.item_id] ? 'pi pi-chevron-up' : 'pi pi-chevron-down'" class="text-[10px]"></i>
              </button>
            </div>
          </div>

          <!-- 原地下拉折疊面板 (VS Code 深灰黑 #181818 風格，徹底消除深藍底色) -->
          <div
            v-if="expandedItems[item.item_id]"
            class="evidence-details-block border-t border-[#333333] bg-[#181818] p-3.5 flex flex-col gap-3 text-xs"
          >
            <!-- 1. 規則意圖與描述 -->
            <div class="rule-description-box p-2.5 rounded bg-[#1e1e1e] border border-[#2a2a2a] text-[#cccccc] flex items-start gap-2">
              <i class="pi pi-info-circle text-sky-400 mt-0.5 shrink-0"></i>
              <div class="flex flex-col gap-0.5">
                <span class="text-[11px] font-semibold text-[#858585] uppercase tracking-wider">規則意圖與檢驗規範</span>
                <span class="leading-relaxed">{{ item.description || item.rule_title }}</span>
              </div>
            </div>

            <!-- 2. 違規原因與工程建議 (若為 FAIL / WARN) -->
            <div v-if="item.error_message" class="error-msg-box p-2.5 rounded bg-red-500/10 border border-red-500/30 text-red-300 flex items-start gap-2">
              <i class="pi pi-exclamation-circle text-red-400 mt-0.5 shrink-0"></i>
              <div class="flex flex-col gap-0.5">
                <span class="text-[11px] font-semibold text-red-400 uppercase tracking-wider">違規判定原因 (Violation Cause)</span>
                <span class="leading-relaxed font-medium">{{ item.error_message }}</span>
              </div>
            </div>

            <div v-if="item.recommendation" class="recommendation-box p-2.5 rounded bg-amber-500/10 border border-amber-500/30 text-amber-300 flex items-start gap-2">
              <i class="pi pi-lightbulb text-amber-400 mt-0.5 shrink-0"></i>
              <div class="flex flex-col gap-0.5">
                <span class="text-[11px] font-semibold text-amber-400 uppercase tracking-wider">工程改善建議 (Recommendation)</span>
                <span class="leading-relaxed">{{ item.recommendation }}</span>
              </div>
            </div>

            <!-- 狀態備註 (PASS / SKIPPED 簡明標示，不展示空泛重複文字) -->
            <div v-if="item.status === 'SKIPPED'" class="skipped-box p-2 rounded bg-[#1e1e1e] border border-[#333333] text-[#858585] flex items-center gap-2">
              <i class="pi pi-ban text-[#858585]"></i>
              <span>電路圖中未發現符合觸發條件之目標，此規則略過執行</span>
            </div>

            <div v-else-if="item.status === 'PASS' && !item.error_message && !item.recommendation" class="pass-box text-green-400/90 flex items-center gap-1.5 text-xs py-0.5">
              <i class="pi pi-check-circle text-green-400"></i>
              <span>此受測標的已全數通過規範判定</span>
            </div>

            <!-- 3. 詳細受測節點資訊 (Inspected Target Nodes) -->
            <div class="target-nodes-section p-2.5 rounded bg-[#1e1e1e] border border-[#2a2a2a] flex flex-col gap-1.5">
              <span class="text-[11px] font-semibold text-[#858585] uppercase tracking-wider">檢驗節點資訊 (Inspected Targets)</span>
              <div class="nodes-row flex items-center gap-3 flex-wrap">
                <div class="flex items-center gap-1.5">
                  <span class="node-label text-[#858585]">受測元件:</span>
                  <span v-if="item.target_nodes.components.length > 0" class="flex items-center gap-1 flex-wrap">
                    <span
                      v-for="c in item.target_nodes.components"
                      :key="c"
                      class="code-chip text-[11px] font-mono px-1.5 py-0.5 rounded bg-[#141414] border border-[#333333] text-sky-400"
                    >
                      {{ c }}
                    </span>
                  </span>
                  <span v-else class="text-[#666666]">無特定元件</span>
                </div>

                <div class="flex items-center gap-1.5 ml-0 sm:ml-4">
                  <span class="node-label text-[#858585]">受測網路:</span>
                  <span v-if="item.target_nodes.nets.length > 0" class="flex items-center gap-1 flex-wrap">
                    <span
                      v-for="n in item.target_nodes.nets"
                      :key="n"
                      class="code-chip text-[11px] font-mono px-1.5 py-0.5 rounded bg-[#141414] border border-[#333333] text-teal-300"
                    >
                      {{ n }}
                    </span>
                  </span>
                  <span v-else class="text-[#666666]">無特定網路</span>
                </div>
              </div>
            </div>

            <!-- 3.5 結構化審計量測總結 (Structured Measurement & Audit Summary) -->
            <div v-if="item.evidence_trail && item.evidence_trail.audit_summary" class="audit-summary-box p-2.5 rounded bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 flex items-start gap-2">
              <i class="pi pi-check-circle text-emerald-400 mt-0.5 shrink-0"></i>
              <div class="flex flex-col gap-0.5">
                <span class="text-[11px] font-semibold text-emerald-400 uppercase tracking-wider">電路量測審計結論 (Audit Summary)</span>
                <span class="leading-relaxed font-medium">{{ item.evidence_trail.audit_summary }}</span>
              </div>
            </div>

            <!-- 3.55 差分通道鏈路拓撲歷程 (Channel Topology Path Segments) -->
            <div
              v-if="hasTopologyFlow(item.evidence_trail)"
              class="channel-segments-box p-3 rounded bg-[#1e1e1e] border border-[#2a2a2a] flex flex-col gap-2.5"
            >
              <div class="flex items-center justify-between flex-wrap gap-1.5">
                <div class="flex items-center gap-2">
                  <i class="pi pi-sitemap text-teal-400 text-xs"></i>
                  <span class="text-[11px] font-semibold text-[#a0a0a0] uppercase tracking-wider">
                    差分通道端到端鏈路拓撲 (Channel End-to-End Topology)
                  </span>
                </div>
                <div class="flex items-center gap-2 flex-wrap">
                  <span
                    v-if="item.evidence_trail.pass_through_components && item.evidence_trail.pass_through_components.length > 0"
                    class="text-[10px] px-1.5 py-0.5 rounded bg-sky-500/10 border border-sky-500/25 text-sky-300 font-mono"
                  >
                    途經元件: {{ item.evidence_trail.pass_through_components.join(', ') }}
                  </span>
                  <span
                    v-if="item.evidence_trail.symmetry_check"
                    class="text-[10px] px-1.5 py-0.5 rounded font-mono font-semibold"
                    :class="item.evidence_trail.symmetry_check.is_symmetric ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30' : 'bg-red-500/15 text-red-300 border border-red-500/30'"
                  >
                    {{ item.evidence_trail.symmetry_check.is_symmetric ? 'P/N 拓撲完全對稱' : 'P/N 拓撲不對稱' }}
                  </span>
                </div>
              </div>

              <!-- 正極 (P) 鏈路拓撲 -->
              <div class="channel-p-flow flex flex-col gap-1">
                <div class="flex items-center gap-1.5 text-[10px] font-mono text-emerald-400 font-semibold">
                  <span class="px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">P+ 正極鏈路</span>
                  <span class="text-[#858585] font-normal">({{ item.evidence_trail.p_net || '正極網路' }})</span>
                </div>
                <!-- 拓撲鏈路節點流程 (Breadcrumbs flow) -->
                <div class="path-segments-flow flex items-center gap-2 flex-wrap p-2.5 rounded bg-[#141414] border border-[#2a2a2a] text-xs">
                  <template v-for="(stage, stIdx) in getTopologyFlow(item.evidence_trail, 'p')" :key="'p-' + stIdx">
                    <!-- 階段 A: 端點元件與網路 (Endpoints stage) -->
                    <template v-if="stage.stage === 'endpoints'">
                      <div class="flex items-center gap-1.5 flex-wrap">
                        <!-- 起點端點: Devices 在前，Net 在後 -->
                        <template v-if="stIdx === 0">
                          <div v-if="stage.devices && stage.devices.length > 0" class="flex items-center gap-1 flex-wrap">
                            <div
                              v-for="(dev, dIdx) in stage.devices"
                              :key="dIdx"
                              :class="getDeviceBadgeClass(dev.type, dev.ref_des)"
                              class="device-chip flex items-center gap-1 px-2 py-0.5 rounded border font-mono text-[11px]"
                              :title="dev.part_number ? `料號: ${dev.part_number}` : ''"
                            >
                              <i :class="getDeviceIcon(dev.type, dev.ref_des)" class="text-[10px]"></i>
                              <span class="font-bold">{{ dev.ref_des }}</span>
                              <span v-if="dev.pin" class="text-[10px] opacity-80">[Pin {{ dev.pin }}]</span>
                            </div>
                          </div>
                          <i v-if="stage.devices && stage.devices.length > 0" class="pi pi-arrow-right text-[10px] text-teal-400/60"></i>
                          <span class="net-name-chip font-mono px-2 py-0.5 rounded bg-teal-500/10 border border-teal-500/30 text-teal-300 font-semibold text-xs">
                            {{ stage.net }}
                          </span>
                        </template>
                        <!-- 終點端點: Net 在前，Devices 在後 -->
                        <template v-else>
                          <span class="net-name-chip font-mono px-2 py-0.5 rounded bg-teal-500/10 border border-teal-500/30 text-teal-300 font-semibold text-xs">
                            {{ stage.net }}
                          </span>
                          <i v-if="stage.devices && stage.devices.length > 0" class="pi pi-arrow-right text-[10px] text-teal-400/60"></i>
                          <div v-if="stage.devices && stage.devices.length > 0" class="flex items-center gap-1 flex-wrap">
                            <div
                              v-for="(dev, dIdx) in stage.devices"
                              :key="dIdx"
                              :class="getDeviceBadgeClass(dev.type, dev.ref_des)"
                              class="device-chip flex items-center gap-1 px-2 py-0.5 rounded border font-mono text-[11px]"
                              :title="dev.part_number ? `料號: ${dev.part_number}` : ''"
                            >
                              <i :class="getDeviceIcon(dev.type, dev.ref_des)" class="text-[10px]"></i>
                              <span class="font-bold">{{ dev.ref_des }}</span>
                              <span v-if="dev.pin" class="text-[10px] opacity-80">[Pin {{ dev.pin }}]</span>
                            </div>
                          </div>
                        </template>
                      </div>
                    </template>

                    <!-- 階段 B: 穿透元件 (Pass-through stage, 如 TL1 CMC) -->
                    <template v-else-if="stage.stage === 'pass_through'">
                      <i class="pi pi-arrow-right text-[10px] text-[#666666]"></i>
                      <div class="pass-comp-pill flex items-center gap-1.5 px-2 py-0.5 rounded bg-sky-500/15 border border-sky-500/35 text-sky-300 font-mono text-[11px]">
                        <i class="pi pi-compass text-[11px] text-sky-400"></i>
                        <span class="font-bold">{{ stage.component }}</span>
                        <span v-if="stage.type" class="text-[9px] px-1 py-0.2 rounded bg-sky-400/20 text-sky-200 uppercase">
                          {{ stage.type }}
                        </span>
                        <span v-if="stage.in_pin && stage.out_pin" class="text-[10px] font-semibold text-sky-400">
                          ({{ stage.in_pin }} ➔ {{ stage.out_pin }})
                        </span>
                      </div>
                      <i class="pi pi-arrow-right text-[10px] text-[#666666]"></i>
                    </template>
                  </template>
                </div>
              </div>

              <!-- 負極 (N) 鏈路拓撲 (若有 n 端拓撲流向) -->
              <div
                v-if="getTopologyFlow(item.evidence_trail, 'n').length > 0"
                class="channel-n-flow flex flex-col gap-1 mt-1"
              >
                <div class="flex items-center gap-1.5 text-[10px] font-mono text-emerald-400 font-semibold">
                  <span class="px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">N- 負極鏈路</span>
                  <span class="text-[#858585] font-normal">({{ item.evidence_trail.n_net || '負極網路' }})</span>
                </div>
                <div class="path-segments-flow-n flex items-center gap-2 flex-wrap p-2.5 rounded bg-[#141414] border border-[#2a2a2a] text-xs">
                  <template v-for="(stage, stIdx) in getTopologyFlow(item.evidence_trail, 'n')" :key="'n-' + stIdx">
                    <!-- 階段 A: 端點元件與網路 -->
                    <template v-if="stage.stage === 'endpoints'">
                      <div class="flex items-center gap-1.5 flex-wrap">
                        <!-- 起點端點: Devices 在前，Net 在後 -->
                        <template v-if="stIdx === 0">
                          <div v-if="stage.devices && stage.devices.length > 0" class="flex items-center gap-1 flex-wrap">
                            <div
                              v-for="(dev, dIdx) in stage.devices"
                              :key="dIdx"
                              :class="getDeviceBadgeClass(dev.type, dev.ref_des)"
                              class="device-chip flex items-center gap-1 px-2 py-0.5 rounded border font-mono text-[11px]"
                              :title="dev.part_number ? `料號: ${dev.part_number}` : ''"
                            >
                              <i :class="getDeviceIcon(dev.type, dev.ref_des)" class="text-[10px]"></i>
                              <span class="font-bold">{{ dev.ref_des }}</span>
                              <span v-if="dev.pin" class="text-[10px] opacity-80">[Pin {{ dev.pin }}]</span>
                            </div>
                          </div>
                          <i v-if="stage.devices && stage.devices.length > 0" class="pi pi-arrow-right text-[10px] text-teal-400/60"></i>
                          <span class="net-name-chip font-mono px-2 py-0.5 rounded bg-teal-500/10 border border-teal-500/30 text-teal-300 font-semibold text-xs">
                            {{ stage.net }}
                          </span>
                        </template>
                        <!-- 終點端點: Net 在前，Devices 在後 -->
                        <template v-else>
                          <span class="net-name-chip font-mono px-2 py-0.5 rounded bg-teal-500/10 border border-teal-500/30 text-teal-300 font-semibold text-xs">
                            {{ stage.net }}
                          </span>
                          <i v-if="stage.devices && stage.devices.length > 0" class="pi pi-arrow-right text-[10px] text-teal-400/60"></i>
                          <div v-if="stage.devices && stage.devices.length > 0" class="flex items-center gap-1 flex-wrap">
                            <div
                              v-for="(dev, dIdx) in stage.devices"
                              :key="dIdx"
                              :class="getDeviceBadgeClass(dev.type, dev.ref_des)"
                              class="device-chip flex items-center gap-1 px-2 py-0.5 rounded border font-mono text-[11px]"
                              :title="dev.part_number ? `料號: ${dev.part_number}` : ''"
                            >
                              <i :class="getDeviceIcon(dev.type, dev.ref_des)" class="text-[10px]"></i>
                              <span class="font-bold">{{ dev.ref_des }}</span>
                              <span v-if="dev.pin" class="text-[10px] opacity-80">[Pin {{ dev.pin }}]</span>
                            </div>
                          </div>
                        </template>
                      </div>
                    </template>

                    <!-- 階段 B: 穿透元件 (Pass-through stage) -->
                    <template v-else-if="stage.stage === 'pass_through'">
                      <i class="pi pi-arrow-right text-[10px] text-[#666666]"></i>
                      <div class="pass-comp-pill flex items-center gap-1.5 px-2 py-0.5 rounded bg-sky-500/15 border border-sky-500/35 text-sky-300 font-mono text-[11px]">
                        <i class="pi pi-compass text-[11px] text-sky-400"></i>
                        <span class="font-bold">{{ stage.component }}</span>
                        <span v-if="stage.type" class="text-[9px] px-1 py-0.2 rounded bg-sky-400/20 text-sky-200 uppercase">
                          {{ stage.type }}
                        </span>
                        <span v-if="stage.in_pin && stage.out_pin" class="text-[10px] font-semibold text-sky-400">
                          ({{ stage.in_pin }} ➔ {{ stage.out_pin }})
                        </span>
                      </div>
                      <i class="pi pi-arrow-right text-[10px] text-[#666666]"></i>
                    </template>
                  </template>
                </div>
              </div>
            </div>

            <!-- 3.6 實測電阻與參數卡片 (若有檢測到電阻) -->
            <div v-if="item.evidence_trail && item.evidence_trail.resistors && item.evidence_trail.resistors.length > 0" class="resistors-table-box p-2.5 rounded bg-[#1e1e1e] border border-[#2a2a2a] flex flex-col gap-1.5">
              <span class="text-[11px] font-semibold text-[#858585] uppercase tracking-wider">找到之配置電阻與量測數值 (Detected Resistors)</span>
              <div class="flex flex-col gap-1.5">
                <div
                  v-for="(r, rIdx) in item.evidence_trail.resistors"
                  :key="rIdx"
                  class="resistor-row flex items-center justify-between p-1.5 px-2 rounded bg-[#141414] border border-[#2a2a2a] text-xs flex-wrap gap-2"
                >
                  <div class="flex items-center gap-2 flex-wrap">
                    <span class="font-mono font-bold text-sky-400">{{ r.ref_des }}</span>
                    <span class="text-[#858585]">標稱值:</span>
                    <span class="font-mono text-emerald-300">{{ r.part_value || (r.resistance_ohm ? `${r.resistance_ohm}Ω` : '未知') }}</span>
                    <span v-if="r.power_rail" class="text-[#858585]">供電軌:</span>
                    <span v-if="r.power_rail" class="font-mono text-teal-300">{{ r.power_rail }}</span>
                  </div>
                  <span
                    class="text-[10px] font-semibold px-1.5 py-0.5 rounded"
                    :class="r.compliant !== false ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30' : 'bg-red-500/15 text-red-300 border border-red-500/30'"
                  >
                    {{ r.compliant !== false ? '規格合規' : '偏離門檻' }}
                  </span>
                </div>
              </div>
            </div>

            <!-- 4. 詳細檢驗佐證歷程 (Evidence Trail / VS Code Editor 風格) -->
            <div class="raw-evidence-section flex flex-col gap-1.5">
              <div class="flex justify-between items-center">
                <span class="evidence-title text-[11px] font-semibold text-[#858585] uppercase tracking-wider">
                  檢驗歷程與佐證 (Evidence Trail)
                </span>
                <button
                  class="copy-json-btn flex items-center gap-1 text-[11px] text-[#858585] hover:text-white cursor-pointer bg-transparent border-0 p-0.5 transition-colors"
                  @click.stop="copyEvidenceJson(item)"
                >
                  <i :class="copiedItemMap[item.item_id] ? 'pi pi-check text-green-400' : 'pi pi-copy'"></i>
                  <span>{{ copiedItemMap[item.item_id] ? '已複製' : '複製 JSON' }}</span>
                </button>
              </div>
              <pre class="json-code m-0 font-mono text-[11px] text-[#d4d4d4] bg-[#121212] p-3 rounded max-h-56 overflow-y-auto border border-[#2a2a2a] leading-relaxed select-text">{{ formatJson(item.evidence_trail) }}</pre>
            </div>
          </div>
        </div>

        <!-- 空狀態通知 -->
        <div v-if="sortedFilteredItems.length === 0" class="empty-items-notice p-8 text-center text-[#858585] flex flex-col items-center gap-2 text-xs">
          <i class="pi pi-inbox text-2xl text-[#666666]"></i>
          <span>目前過濾條件下無任何項目</span>
        </div>
      </div>

      <!-- 分頁控制列 (底部) -->
      <div v-if="pageSize > 0 && totalPages > 1" class="table-pagination-bar-bottom flex justify-between items-center text-xs text-[#858585] pt-2 border-t border-[#333333]/50">
        <span>第 {{ currentPage }} / {{ totalPages }} 頁</span>
        <div class="page-nav-btns flex items-center gap-1">
          <button
            class="pagination-btn px-2.5 py-1 rounded border border-[#333333] bg-[#1e1e1e] text-[#cccccc] disabled:opacity-40 disabled:cursor-not-allowed hover:bg-[#2a2d2e] cursor-pointer text-xs"
            :disabled="currentPage <= 1"
            @click="changePage(currentPage - 1)"
          >
            上一頁
          </button>
          <button
            class="pagination-btn px-2.5 py-1 rounded border border-[#333333] bg-[#1e1e1e] text-[#cccccc] disabled:opacity-40 disabled:cursor-not-allowed hover:bg-[#2a2d2e] cursor-pointer text-xs"
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
 * 採用正統 VS Code 暗色風格、異常優先置頂與簡約單行清單模式
 */

import { ref, computed, watch } from 'vue'
import Button from 'primevue/button'
import { copyToClipboard } from '@/utils/clipboard'

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

const currentFilter = ref<string>('ALL')
const expandedItems = ref<Record<string, boolean>>({})
const copiedItemMap = ref<Record<string, boolean>>({})

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

// 分頁衍生運算
const totalCount = computed(() => sortedFilteredItems.value.length)
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

const paginatedItems = computed(() => {
  if (pageSize.value <= 0) return sortedFilteredItems.value
  const start = (currentPage.value - 1) * pageSize.value
  return sortedFilteredItems.value.slice(start, start + pageSize.value)
})

// 當過濾條件變更時自動重設回第一頁
watch([currentFilter, pageSize], () => {
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
 * 切換項目詳情展開狀態
 */
const toggleExpand = (itemId: string) => {
  expandedItems.value[itemId] = !expandedItems.value[itemId]
}

/**
 * 格式化 JSON 字串
 */
const formatJson = (data: any): string => {
  if (!data || Object.keys(data).length === 0) {
    return '{\n  "note": "此檢測項目無額外佐證歷程記錄"\n}'
  }
  return JSON.stringify(data, null, 2)
}

/**
 * 複製佐證歷程 JSON
 */
const copyEvidenceJson = async (item: ViolationItem) => {
  const text = JSON.stringify(item.evidence_trail || {}, null, 2)
  const ok = await copyToClipboard(text)
  if (ok) {
    copiedItemMap.value[item.item_id] = true
    setTimeout(() => {
      copiedItemMap.value[item.item_id] = false
    }, 2000)
  } else {
    console.error('無法將佐證歷程複製到剪貼簿')
  }
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

/**
 * 檢查佐證歷程是否包含差分通道拓撲鏈路資料
 */
const hasTopologyFlow = (evidence: Record<string, any> | undefined): boolean => {
  if (!evidence) return false
  return Boolean(
    (Array.isArray(evidence.topology_flow) && evidence.topology_flow.length > 0) ||
    (Array.isArray(evidence.path_segments) && evidence.path_segments.length > 0) ||
    (Array.isArray(evidence.p_endpoints) && evidence.p_endpoints.length > 0 && evidence.p_net)
  )
}

/**
 * 取得差分通道端到端完整鏈路拓撲流程 (Topology Flow)
 * 支援後端預先建構的 topology_flow，並具備前端動態 fallback 組合機制
 */
const getTopologyFlow = (
  evidence: Record<string, any> | undefined,
  polarity: 'p' | 'n' = 'p'
): TopologyFlowStage[] => {
  if (!evidence) return []

  const flowKey = polarity === 'p' ? 'topology_flow' : 'n_topology_flow'
  if (Array.isArray(evidence[flowKey]) && evidence[flowKey].length > 0) {
    return evidence[flowKey]
  }

  // 客戶端相容 Fallback 邏輯
  const segs = polarity === 'p' ? (evidence.path_segments || []) : (evidence.n_path_segments || [])
  const endpoints = polarity === 'p' ? (evidence.p_endpoints || []) : (evidence.n_endpoints || [])
  const startNet = polarity === 'p' ? (evidence.p_net || '') : (evidence.n_net || '')

  // 1. 去重 segments (防止舊資料或重複端點造成 TL1 出現多次)
  const seenSegs = new Set<string>()
  const uniqueSegs: any[] = []
  for (const s of segs) {
    const k = `${s.from_net}|${s.pass_component}|${s.in_pin}|${s.out_pin}|${s.to_net}`
    if (!seenSegs.has(k)) {
      seenSegs.add(k)
      uniqueSegs.push(s)
    }
  }

  // 2. 若無穿透元件，直接呈現單一階段端點元件與網路
  if (uniqueSegs.length === 0) {
    if (endpoints.length > 0) {
      return [
        {
          stage: 'endpoints',
          net: startNet,
          devices: endpoints.map((ep: any) => ({
            ref_des: ep.ref_des,
            pin: ep.pin || '',
            part_number: ep.part_number || '',
            type: ep.component_type || '',
          })),
        },
      ]
    }
    return []
  }

  // 3. 有穿透元件時，將端點元件依照 connected_net 分組
  const endpointsByNet: Record<string, FlowDevice[]> = {}
  for (const ep of endpoints) {
    const net = ep.connected_net || (endpoints.indexOf(ep) === 0 ? uniqueSegs[0].from_net : uniqueSegs[uniqueSegs.length - 1].to_net)
    if (!endpointsByNet[net]) {
      endpointsByNet[net] = []
    }
    endpointsByNet[net].push({
      ref_des: ep.ref_des,
      pin: ep.pin || '',
      part_number: ep.part_number || '',
      type: ep.component_type || '',
    })
  }

  const flow: TopologyFlowStage[] = []
  const visitedNets = new Set<string>()

  uniqueSegs.forEach((seg, idx) => {
    const fromNet = seg.from_net
    const toNet = seg.to_net

    if (!visitedNets.has(fromNet)) {
      visitedNets.add(fromNet)
      flow.push({
        stage: 'endpoints',
        net: fromNet,
        devices: endpointsByNet[fromNet] || [],
      })
    }

    flow.push({
      stage: 'pass_through',
      component: seg.pass_component,
      type: seg.pass_component_type || 'Passive',
      in_pin: seg.in_pin || '',
      out_pin: seg.out_pin || '',
      from_net: fromNet,
      to_net: toNet,
    })

    if (!visitedNets.has(toNet) && (idx === uniqueSegs.length - 1 || uniqueSegs[idx + 1].from_net !== toNet)) {
      visitedNets.add(toNet)
      flow.push({
        stage: 'endpoints',
        net: toNet,
        devices: endpointsByNet[toNet] || [],
      })
    }
  })

  return flow
}

/**
 * 依據元件類型與 RefDes 取得 PrimeIcons 圖標名稱
 */
const getDeviceIcon = (type?: string, refDes?: string): string => {
  const t = (type || '').toLowerCase()
  const r = (refDes || '').toUpperCase()
  if (t.includes('connector') || r.startsWith('J') || r.startsWith('P') || r.startsWith('CN')) {
    return 'pi pi-link'
  }
  if (t.includes('ic') || r.startsWith('U')) {
    return 'pi pi-server'
  }
  return 'pi pi-box'
}

/**
 * 依據元件類型取得徽章色彩樣式 (符合 PrimeVue 與 Tailwind 色彩令牌)
 */
const getDeviceBadgeClass = (type?: string, refDes?: string): string => {
  const t = (type || '').toLowerCase()
  const r = (refDes || '').toUpperCase()
  if (t.includes('connector') || r.startsWith('J') || r.startsWith('P') || r.startsWith('CN')) {
    return 'bg-amber-500/15 border-amber-500/35 text-amber-300'
  }
  if (t.includes('ic') || r.startsWith('U')) {
    return 'bg-purple-500/15 border-purple-500/35 text-purple-300'
  }
  return 'bg-slate-700/40 border-slate-600 text-slate-300'
}
</script>
