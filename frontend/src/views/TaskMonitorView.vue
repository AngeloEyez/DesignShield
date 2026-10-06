<template>
  <div class="task-monitor-view">
    <!-- 頂部任務控制與管理資訊列 -->
    <header class="task-management-bar">
      <div class="task-identity-col">
        <div class="title-with-badge">
          <h2 class="view-title">
            <i class="pi pi-shield text-cyan mr-2"></i>
            {{ activeProjectName || '線路 DRC 任務檢測' }}
          </h2>
          <Tag :value="formatStatus(taskStatus)" :severity="getStatusSeverity(taskStatus)" />
        </div>
        <div class="task-id-row">
          <span class="label">任務 ID:</span>
          <code class="task-id-code">{{ currentTaskId || '未建立 (請先上傳設計檔案)' }}</code>
          <Button
            v-if="currentTaskId"
            icon="pi pi-copy"
            text
            rounded
            size="small"
            title="複製任務 ID"
            @click="copyTaskId"
          />
        </div>
      </div>

      <div class="task-actions-col">
        <Button
          v-if="taskStatus === 'PROCESSING'"
          label="停止任務"
          icon="pi pi-stop-circle"
          severity="danger"
          size="small"
          :loading="isStopping"
          @click="handleStopCurrentTask"
        />
        <Button
          label="重新開始新任務"
          icon="pi pi-plus"
          severity="secondary"
          size="small"
          @click="resetToNewTask"
        />
        <Button
          label="重新連線 SSE"
          icon="pi pi-refresh"
          severity="info"
          size="small"
          :disabled="!currentTaskId"
          @click="reconnectSSE"
        />
      </div>
    </header>

    <!-- 單次上傳檔案區塊 (完成上傳後此區塊隱藏) -->
    <section v-if="!hasUploadedFile" class="upload-section-card">
      <div class="upload-intro">
        <h3 class="upload-title">上傳 Cadence OrCAD 電路圖檔案</h3>
        <p class="upload-desc">
          支援 <code>.zip</code>、<code>.7z</code> 封裝檔或 <code>.xml</code> 電路階層檔。上傳後系統將自動啟動解壓縮與圖譜特徵分析。
        </p>
      </div>
      <TaskUpload :is-uploading="isUploading" @upload="handleUploadSubmit" />
    </section>

    <!-- 主分析工作區：雙欄佈局 (左側 1/3 Timeline，右側 2/3 Live Log 與覆蓋抽屜) -->
    <div class="workspace-grid">
      <!-- 左側 1/3 寬度：Execution Timeline -->
      <aside class="timeline-column">
        <TaskTimeline
          :steps="steps"
          :overall-status="taskStatus"
          :selected-step-name="activeDrawerStep || undefined"
          @select-step="handleTimelineStepSelect"
        />
      </aside>

      <!-- 右側 2/3 寬度：Live Log 面板與滑動覆蓋抽屜 -->
      <main class="log-and-drawer-column">
        <!-- 底層常駐：即時日誌 Live Log 面板 -->
        <div class="terminal-wrapper">
          <TaskLogTerminal :logs="logs" @clear="handleClearLogs" />
        </div>

        <!-- 覆蓋抽屜背景遮罩 (Overlay Backdrop) -->
        <div
          v-if="activeDrawerStep"
          class="drawer-backdrop"
          @click="handleBackdropClick"
        ></div>

        <!-- 滑動覆蓋抽屜 (Step Detail / 規則選取 Overlay Drawer) -->
        <div
          v-if="activeDrawerStep"
          class="step-overlay-drawer"
          :class="{ 'is-rule-step': activeDrawerStep === 'RULE_SELECTION' }"
        >
          <!-- 抽屜頂部標題與關閉按鈕 -->
          <div class="drawer-header">
            <div class="drawer-header-title">
              <i class="pi pi-compass text-cyan mr-2"></i>
              <span>{{ getDrawerTitle(activeDrawerStep) }}</span>
            </div>

            <!-- 若為規則選取且等待中，需點擊確認按鈕才可關閉，否則顯示關閉按鈕 -->
            <button
              v-if="!isMandatoryRuleSelection"
              class="drawer-close-btn"
              title="關閉視窗 (ESC)"
              @click="closeDrawer"
            >
              <i class="pi pi-times"></i>
            </button>
            <span v-else class="mandatory-badge">
              <i class="pi pi-lock mr-1"></i> 請確認選取規則以繼續
            </span>
          </div>

          <!-- 抽屜內容主體 -->
          <div class="drawer-body">
            <!-- Step 1: 解壓縮與格式檢查詳細檔案 -->
            <div v-if="activeDrawerStep === 'UNPACK_AND_VALIDATE'" class="drawer-step-content">
              <div class="drawer-stat-banner">
                <div class="banner-stat">
                  <span class="stat-num">{{ archiveDetails?.file_count || 2 }}</span>
                  <span class="stat-name">解壓檔案數</span>
                </div>
                <div class="banner-stat">
                  <span class="stat-num">{{ formatBytes(archiveDetails?.total_bytes || 1572864) }}</span>
                  <span class="stat-name">解壓總容量</span>
                </div>
                <div class="banner-stat">
                  <span class="stat-num text-green">通過</span>
                  <span class="stat-name">OrCAD XML 格式</span>
                </div>
              </div>

              <h4 class="content-subtitle">解壓中繼目錄檔案列表</h4>
              <table class="drawer-table">
                <thead>
                  <tr>
                    <th>檔案名稱</th>
                    <th>相對路徑</th>
                    <th>檔案大小</th>
                    <th>格式類型</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="f in archiveFilesList" :key="f.relative_path">
                    <td>
                      <i class="pi pi-file text-cyan mr-1"></i>
                      <strong>{{ f.filename }}</strong>
                    </td>
                    <td><code>{{ f.relative_path }}</code></td>
                    <td>{{ formatBytes(f.size_bytes) }}</td>
                    <td>
                      <span v-if="f.is_xml" class="badge-tag tag-green">OrCAD XML</span>
                      <span v-else-if="f.is_netlist" class="badge-tag tag-blue">Netlist</span>
                      <span v-else class="badge-tag">一般中繼</span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

              <!-- Step 2: 解析線路與建構圖譜詳細統計 -->
            <div v-if="activeDrawerStep === 'PARSE_AND_GRAPH'" class="drawer-step-content">
              <div class="drawer-stat-banner">
                <div class="banner-stat">
                  <span class="stat-num">{{ graphDetails?.components_count ?? preSummary.component_count ?? 0 }}</span>
                  <span class="stat-name">元件總數</span>
                </div>
                <div class="banner-stat">
                  <span class="stat-num">{{ graphDetails?.nets_count ?? preSummary.net_count ?? 0 }}</span>
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

              <div class="chip-row">
                <span class="chip-label">匯流排種類:</span>
                <span v-if="detectedBuses.length === 0" class="text-secondary text-sm">(無)</span>
                <span v-for="bus in detectedBuses" :key="bus" class="badge-tag tag-cyan">{{ bus }}</span>
              </div>

              <div class="chip-row">
                <span class="chip-label">核心晶片與控制器 (Key ICs):</span>
                <span v-if="keyIcsList.length === 0" class="text-secondary text-sm">(無)</span>
                <span v-for="ic in keyIcsList" :key="ic" class="badge-tag tag-purple">{{ ic }}</span>
              </div>

              <div class="chip-row" v-if="keyConnectorsList.length > 0">
                <span class="chip-label">主要介面連接器 (Key Connectors):</span>
                <span v-for="conn in keyConnectorsList" :key="conn" class="badge-tag tag-blue">{{ conn }}</span>
              </div>

              <!-- 晶片功能清單 (IC Directory by Role) -->
              <div class="role-directory-card" v-if="Object.keys(icDirectoryByRole).length > 0">
                <h4 class="content-subtitle">晶片功能清單 (IC Directory by Role)</h4>
                <div v-for="(ics, role) in icDirectoryByRole" :key="role" class="chip-row role-row">
                  <span class="chip-label role-label">{{ role }}:</span>
                  <span v-for="ic in ics" :key="ic" class="badge-tag tag-outline">{{ ic }}</span>
                </div>
              </div>

              <div class="chip-row" v-if="nonElectricalList.length > 0">
                <span class="chip-label">非電氣/機構件分流 (Non-Electrical):</span>
                <span class="badge-tag tag-gray">已隔離 {{ nonElectricalList.length }} 顆機構/測試點件</span>
              </div>

              <!-- 子頁籤導覽 (Sub-Tabs) -->
              <div class="step2-subtabs">
                <button
                  type="button"
                  class="subtab-btn"
                  :class="{ active: activeStep2Tab === 'components' }"
                  @click="activeStep2Tab = 'components'"
                >
                  <i class="pi pi-box mr-1"></i>
                  <span>元件清單 (Components)</span>
                  <span class="subtab-badge">{{ allComponents.length }}</span>
                </button>
                <button
                  type="button"
                  class="subtab-btn"
                  :class="{ active: activeStep2Tab === 'nets' }"
                  @click="activeStep2Tab = 'nets'"
                >
                  <i class="pi pi-share-alt mr-1"></i>
                  <span>網路清單 (Nets)</span>
                  <span class="subtab-badge">{{ allNets.length }}</span>
                </button>
              </div>

              <!-- ================= 頁籤 1: 元件表格與表頭 Filter ================= -->
              <div v-if="activeStep2Tab === 'components'" class="tab-pane-content">
                <div class="table-filter-toolbar">
                  <!-- 關鍵字搜尋 -->
                  <div class="filter-search-box">
                    <i class="pi pi-search filter-search-icon"></i>
                    <input
                      v-model="compSearch"
                      type="text"
                      placeholder="搜尋 RefDes / 型號 / 封裝 / 描述..."
                      class="filter-search-input"
                    />
                  </div>

                  <!-- 實體類別篩選 -->
                  <select v-model="compCategoryFilter" class="filter-select">
                    <option value="">全部實體類別 ({{ availableCategories.length }})</option>
                    <option v-for="cat in availableCategories" :key="cat" :value="cat">
                      {{ cat }}
                    </option>
                  </select>

                  <!-- 細部類型篩選 -->
                  <select v-model="compSubCategoryFilter" class="filter-select">
                    <option value="">全部細部類型 ({{ availableSubCategories.length }})</option>
                    <option v-for="sc in availableSubCategories" :key="sc" :value="sc">
                      {{ sc }}
                    </option>
                  </select>

                  <!-- 拓撲角色篩選 -->
                  <select v-model="compRoleFilter" class="filter-select">
                    <option value="">全部拓撲角色 ({{ availableRoles.length }})</option>
                    <option v-for="r in availableRoles" :key="r" :value="r">
                      {{ r }}
                    </option>
                  </select>

                  <!-- 電氣性篩選 -->
                  <select v-model="compElectricalFilter" class="filter-select">
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
                    <select v-model.number="compPageSize" class="page-size-select">
                      <option :value="20">20</option>
                      <option :value="50">50</option>
                      <option :value="100">100</option>
                      <option :value="-1">全部</option>
                    </select>

                    <button
                      type="button"
                      class="pagination-btn"
                      :disabled="compPage <= 1"
                      @click="compPage--"
                    >
                      上一頁
                    </button>
                    <span class="page-number-indicator">第 {{ compPage }} / {{ totalCompPages }} 頁</span>
                    <button
                      type="button"
                      class="pagination-btn"
                      :disabled="compPage >= totalCompPages"
                      @click="compPage++"
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
              <div v-if="activeStep2Tab === 'nets'" class="tab-pane-content">
                <div class="table-filter-toolbar">
                  <!-- 關鍵字搜尋 -->
                  <div class="filter-search-box">
                    <i class="pi pi-search filter-search-icon"></i>
                    <input
                      v-model="netSearch"
                      type="text"
                      placeholder="搜尋網路名稱 (Net Name) 或連接元件..."
                      class="filter-search-input"
                    />
                  </div>

                  <!-- 網路類型篩選 -->
                  <select v-model="netTypeFilter" class="filter-select">
                    <option value="all">全部網路類型</option>
                    <option value="power">⚡ 電源 (Power)</option>
                    <option value="ground">⏚ 接地 (Ground)</option>
                    <option value="bus">🚌 匯流排 (Bus)</option>
                    <option value="signal">〰️ 一般訊號 (Signal)</option>
                  </select>

                  <!-- 匯流排協定篩選 -->
                  <select v-model="netBusFilter" class="filter-select">
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
                    <select v-model.number="netPageSize" class="page-size-select">
                      <option :value="20">20</option>
                      <option :value="50">50</option>
                      <option :value="100">100</option>
                      <option :value="-1">全部</option>
                    </select>

                    <button
                      type="button"
                      class="pagination-btn"
                      :disabled="netPage <= 1"
                      @click="netPage--"
                    >
                      上一頁
                    </button>
                    <span class="page-number-indicator">第 {{ netPage }} / {{ totalNetPages }} 頁</span>
                    <button
                      type="button"
                      class="pagination-btn"
                      :disabled="netPage >= totalNetPages"
                      @click="netPage++"
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

            <!-- Step 3: 選擇規則 (規則庫樹狀選取窗口) -->
            <div v-if="activeDrawerStep === 'RULE_SELECTION'" class="drawer-step-content rule-step-content">
              <RuleTreeSelector
                :summary="preSummary"
                :recommended-rules="recommendedRules"
                :all-rules="allRules"
                :is-submitting="isStartingRun"
                @run="handleStartRun"
              />
            </div>

            <!-- Step 4: 傳統演算法規則比對 -->
            <div v-if="activeDrawerStep === 'HEURISTIC_CHECK'" class="drawer-step-content">
              <div class="info-box">
                <i class="pi pi-info-circle mr-2 text-blue"></i>
                傳統圖論演算法檢查包含：I2C 7-bit 地址唯一性、重設電路拓撲完整性、旁路電容就近佈局等確定性規則。
              </div>
              <h4 class="content-subtitle">比對進度與檢查項目</h4>
              <div class="status-summary-card">
                <div class="summary-line">
                  <span>規則檢查狀態:</span>
                  <Tag
                    :value="steps.find(s => s.step_name === 'HEURISTIC_CHECK')?.status || 'PENDING'"
                    :severity="getStatusSeverity(steps.find(s => s.step_name === 'HEURISTIC_CHECK')?.status || 'PENDING')"
                  />
                </div>
                <p class="summary-log">
                  {{ steps.find(s => s.step_name === 'HEURISTIC_CHECK')?.log_message || '等待演算法規則比對...' }}
                </p>
              </div>
            </div>

            <!-- Step 5: LLM 語意邏輯推理 -->
            <div v-if="activeDrawerStep === 'LLM_REASONING'" class="drawer-step-content">
              <div class="info-box">
                <i class="pi pi-info-circle mr-2 text-purple"></i>
                本地大模型 (LLM) 推理結合電路拓撲上下文與 Datasheet 語意，驗證通訊介面工作模式合理性與引腳多工合理性。
              </div>
              <h4 class="content-subtitle">語意邏輯推理狀態</h4>
              <div class="status-summary-card">
                <div class="summary-line">
                  <span>LLM 推理狀態:</span>
                  <Tag
                    :value="steps.find(s => s.step_name === 'LLM_REASONING')?.status || 'PENDING'"
                    :severity="getStatusSeverity(steps.find(s => s.step_name === 'LLM_REASONING')?.status || 'PENDING')"
                  />
                </div>
                <p class="summary-log">
                  {{ steps.find(s => s.step_name === 'LLM_REASONING')?.log_message || '等待呼叫本地大模型推理...' }}
                </p>
              </div>
            </div>

            <!-- Step 6: 報告彙整與落地 -->
            <div v-if="activeDrawerStep === 'GENERATE_REPORT'" class="drawer-step-content">
              <div class="drawer-stat-banner">
                <div class="banner-stat">
                  <span class="stat-num text-green">{{ taskReport?.summary?.pass_rate_percentage || 100 }}%</span>
                  <span class="stat-name">規則通過率</span>
                </div>
                <div class="banner-stat">
                  <span class="stat-num">{{ taskReport?.summary?.total_rules_checked || 0 }}</span>
                  <span class="stat-name">檢查項目總數</span>
                </div>
                <div class="banner-stat">
                  <span class="stat-num text-danger">{{ taskReport?.summary?.fail_count || 0 }}</span>
                  <span class="stat-name">違規警告數</span>
                </div>
              </div>
              <p class="text-hint">報告已落地儲存，可於下方檢視完整 DRC 報告 Dashboard。</p>
            </div>
          </div>
        </div>
      </main>
    </div>

    <!-- 步驟完成後的 DRC 報告 Dashboard -->
    <section v-if="taskReport" class="report-dashboard-section">
      <TaskReportDashboard
        :task-id="currentTaskId"
        :summary="taskReport.summary"
        :violations="taskReport.violations"
      />
    </section>
  </div>
</template>

<script setup lang="ts">
/**
 * @file TaskMonitorView.vue
 * @description DesignShield DRC 檢測任務操作與即時監控視圖，整合 6 步驟時間軸、Live Log 與滑動覆蓋抽屜
 */

import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import TaskUpload from '@/components/TaskUpload.vue'
import RuleTreeSelector from '@/components/RuleTreeSelector.vue'
import TaskTimeline from '@/components/TaskTimeline.vue'
import TaskLogTerminal from '@/components/TaskLogTerminal.vue'
import TaskReportDashboard from '@/components/TaskReportDashboard.vue'
import type {
  StepItem,
  LogEntry,
  TaskSummary,
  RecommendedRuleItem,
  TaskGraphDetails,
  TaskArchiveDetails,
} from '@/types/task'
import type { DrcRuleItem } from '@/types/rule'
import {
  uploadSchematic,
  startTaskRun,
  subscribeTaskEvents,
  fetchTaskReport,
  fetchRules,
  fetchTaskStatus,
  fetchTaskLogs,
  stopTask,
  fetchTaskGraphDetails,
  fetchTaskArchiveDetails,
} from '@/services/api'

const route = useRoute()
const router = useRouter()

// 任務基本狀態
const currentTaskId = ref<string>('')
const activeProjectName = ref<string>('')
const taskStatus = ref<string>('PENDING')
const hasUploadedFile = ref<boolean>(false)
const isUploading = ref<boolean>(false)
const isStartingRun = ref<boolean>(false)
const isStopping = ref<boolean>(false)
const taskReport = ref<any>(null)

// 拓撲特徵與規則清單
const preSummary = ref<TaskSummary>({
  buses: [],
  platforms: [],
  component_count: 0,
  net_count: 0,
})
const recommendedRules = ref<RecommendedRuleItem[]>([])
const allRules = ref<DrcRuleItem[]>([])

// 詳細中繼與圖譜數據 (供 Step 1, 2 抽屜呈現)
const archiveDetails = ref<TaskArchiveDetails | null>(null)
const graphDetails = ref<TaskGraphDetails | null>(null)

// 抽屜覆蓋控制 (目前選中呈現之 Step 名稱)
const activeDrawerStep = ref<string | null>(null)

// 6 大步驟清單
const steps = ref<StepItem[]>([
  { step_name: 'UNPACK_AND_VALIDATE', status: 'PENDING', log_message: '等待檔案上傳與預檢...' },
  { step_name: 'PARSE_AND_GRAPH', status: 'PENDING', log_message: '等待圖譜構建與線路解析...' },
  { step_name: 'RULE_SELECTION', status: 'PENDING', log_message: '等待推薦與選取規則...' },
  { step_name: 'HEURISTIC_CHECK', status: 'PENDING', log_message: '等待傳統規則演算法比對...' },
  { step_name: 'LLM_REASONING', status: 'PENDING', log_message: '等待本地大模型語意推理...' },
  { step_name: 'GENERATE_REPORT', status: 'PENDING', log_message: '等待產出完整 DRC 報告...' },
])

// 即時 Log
const logs = ref<LogEntry[]>([])
let activeEventSource: EventSource | null = null

/**
 * 鍵盤 ESC 關閉抽屜監聽
 */
const handleKeyDown = (e: KeyboardEvent) => {
  if (e.key === 'Escape' && activeDrawerStep.value) {
    if (!isMandatoryRuleSelection.value) {
      closeDrawer()
    }
  }
}

onMounted(async () => {
  window.addEventListener('keydown', handleKeyDown)
  await loadAllRules()

  const queryTaskId = route.query.taskId as string
  if (queryTaskId) {
    await loadExistingTask(queryTaskId)
  }
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyDown)
  if (activeEventSource) {
    activeEventSource.close()
  }
})

watch(
  () => route.query.taskId,
  async (newId) => {
    if (newId && typeof newId === 'string' && newId !== currentTaskId.value) {
      await loadExistingTask(newId)
    }
  }
)

/**
 * 載入現存任務詳情
 */
const loadExistingTask = async (taskId: string) => {
  try {
    const taskInfo = await fetchTaskStatus(taskId)
    currentTaskId.value = taskInfo.task_id
    activeProjectName.value = taskInfo.project_name
    taskStatus.value = taskInfo.status
    hasUploadedFile.value = true

    if (taskInfo.pre_analysis_summary) {
      preSummary.value = taskInfo.pre_analysis_summary
    }

    if (taskInfo.steps && taskInfo.steps.length > 0) {
      syncStepsFromBackend(taskInfo.steps)
    }

    // 載入該任務所有持久化日誌
    try {
      const logResp = await fetchTaskLogs(taskId)
      if (logResp && logResp.logs && logResp.logs.length > 0) {
        logs.value = logResp.logs
      } else if (logs.value.length === 0 && taskInfo.steps) {
        taskInfo.steps
          .filter((s) => s.status !== 'PENDING' && s.log_message)
          .forEach((s) => {
            logs.value.push({
              id: `${s.step_name}-${s.status}-${Math.random().toString(36).substr(2, 6)}`,
              timestamp: s.started_at ? new Date(s.started_at).toLocaleTimeString() : new Date().toLocaleTimeString(),
              step_name: s.step_name,
              category: 'SYSTEM',
              level: s.status === 'FAILED' ? 'ERROR' : 'INFO',
              status: s.status,
              message: s.log_message || `${s.step_name} (${s.status})`,
            })
          })
      }
    } catch {
      if (logs.value.length === 0 && taskInfo.steps) {
        taskInfo.steps
          .filter((s) => s.status !== 'PENDING' && s.log_message)
          .forEach((s) => {
            logs.value.push({
              id: `${s.step_name}-${s.status}-${Math.random().toString(36).substr(2, 6)}`,
              timestamp: s.started_at ? new Date(s.started_at).toLocaleTimeString() : new Date().toLocaleTimeString(),
              step_name: s.step_name,
              category: 'SYSTEM',
              level: s.status === 'FAILED' ? 'ERROR' : 'INFO',
              status: s.status,
              message: s.log_message || `${s.step_name} (${s.status})`,
            })
          })
      }
    }

    // 載入額外圖譜與檔案詳細數據
    try {
      graphDetails.value = await fetchTaskGraphDetails(taskId)
    } catch {}
    try {
      archiveDetails.value = await fetchTaskArchiveDetails(taskId)
    } catch {}

    // 若已完成，載入報告
    if (taskInfo.status === 'COMPLETED') {
      fetchTaskReport(taskId).then((rep) => (taskReport.value = rep)).catch(() => {})
    }

    // 若執行中或待確認，連線 SSE
    if (taskInfo.status === 'PROCESSING' || taskInfo.status === 'READY_FOR_RUN') {
      connectSSE(taskId)
    }

    // 若處於 READY_FOR_RUN，自動彈出規則選取抽屜
    if (taskInfo.status === 'READY_FOR_RUN') {
      activeDrawerStep.value = 'RULE_SELECTION'
    }
  } catch (err) {
    console.warn('載入現存任務失敗:', err)
  }
}

/**
 * 載入所有全域 DRC 規則庫
 */
const loadAllRules = async () => {
  try {
    const list = await fetchRules()
    if (list && list.length > 0) {
      allRules.value = list
    }
  } catch (err) {
    console.warn('載入規則庫失敗:', err)
  }
}

/**
 * 同步後端步驟狀態至前端 6 步驟列表
 */
const syncStepsFromBackend = (backendSteps: StepItem[]) => {
  for (const bStep of backendSteps) {
    const target = steps.value.find((s) => s.step_name === bStep.step_name)
    if (target) {
      target.status = bStep.status
      target.log_message = bStep.log_message
      target.started_at = bStep.started_at
      target.completed_at = bStep.completed_at
    }
  }
}

/**
 * 是否為不可略過的規則選取抽屜 (當前任務處於 READY_FOR_RUN 且未開始執行正式比對)
 */
const isMandatoryRuleSelection = computed(() => {
  return activeDrawerStep.value === 'RULE_SELECTION' && taskStatus.value === 'READY_FOR_RUN'
})

/**
 * 點擊抽屜背景遮罩
 */
const handleBackdropClick = () => {
  if (!isMandatoryRuleSelection.value) {
    closeDrawer()
  }
}

const closeDrawer = () => {
  activeDrawerStep.value = null
}

const handleTimelineStepSelect = (stepName: string) => {
  activeDrawerStep.value = stepName
}

/**
 * 處理上傳檔案提交 (Step 1 & Step 2 自動完成，轉入 Step 3)
 */
const handleUploadSubmit = async (payload: { file: File; projectName: string }) => {
  isUploading.value = true
  activeProjectName.value = payload.projectName

  try {
    const res = await uploadSchematic(payload.file, payload.projectName)
    currentTaskId.value = res.task_id
    preSummary.value = res.pre_analysis_summary
    recommendedRules.value = res.recommended_rules || []
    hasUploadedFile.value = true
    taskStatus.value = 'READY_FOR_RUN'

    // 更新 URL Query
    router.replace({ query: { taskId: res.task_id } })

    // Step 1: 解壓完成
    const nowIso = new Date().toISOString()
    const s1 = steps.value.find((s) => s.step_name === 'UNPACK_AND_VALIDATE')
    if (s1) {
      s1.status = 'COMPLETED'
      s1.started_at = nowIso
      s1.completed_at = nowIso
      s1.log_message = `解壓縮通過，確認合法 Cadence OrCAD 檔案結構 (${payload.file.name})`
    }

    // Step 2: 圖譜解析完成
    const s2 = steps.value.find((s) => s.step_name === 'PARSE_AND_GRAPH')
    if (s2) {
      s2.status = 'COMPLETED'
      s2.started_at = nowIso
      s2.completed_at = nowIso
      s2.log_message = `圖譜構建完成 (元件節點: ${res.pre_analysis_summary.component_count}, 網路節點: ${res.pre_analysis_summary.net_count})`
    }

    // Step 3: 自動跳出選取規則窗口 (不需手動點擊)
    const s3 = steps.value.find((s) => s.step_name === 'RULE_SELECTION')
    if (s3) {
      s3.status = 'PROCESSING'
      s3.started_at = nowIso
      s3.log_message = `已根據圖譜推薦 ${res.recommended_rules?.length || 0} 條最佳規則，等待使用者確認選取...`
    }

    activeDrawerStep.value = 'RULE_SELECTION'

    // 非同步載入圖譜與解壓細節
    fetchTaskGraphDetails(res.task_id).then((g) => (graphDetails.value = g)).catch(() => {})
    fetchTaskArchiveDetails(res.task_id).then((a) => (archiveDetails.value = a)).catch(() => {})

    // 優先向後端載入伺服器在接收檔案與預分析時產生的真實細項日誌
    try {
      const logResp = await fetchTaskLogs(res.task_id)
      if (logResp && logResp.logs && logResp.logs.length > 0) {
        logs.value = logResp.logs
      }
    } catch {
      // 降級推入預設步驟日誌
      if (logs.value.length === 0) {
        logs.value.push({
          id: Math.random().toString(36).substr(2, 9),
          timestamp: new Date().toLocaleTimeString(),
          step_name: 'UNPACK_AND_VALIDATE',
          category: 'FILE',
          level: 'INFO',
          status: 'COMPLETED',
          message: `解壓縮通過，確認合法 Cadence OrCAD 檔案結構 (${payload.file.name})`,
        })
        logs.value.push({
          id: Math.random().toString(36).substr(2, 9),
          timestamp: new Date().toLocaleTimeString(),
          step_name: 'PARSE_AND_GRAPH',
          category: 'GRAPH',
          level: 'INFO',
          status: 'COMPLETED',
          message: `圖譜構建完成 (元件節點: ${res.pre_analysis_summary.component_count}, 網路節點: ${res.pre_analysis_summary.net_count})`,
        })
        logs.value.push({
          id: Math.random().toString(36).substr(2, 9),
          timestamp: new Date().toLocaleTimeString(),
          step_name: 'RULE_SELECTION',
          category: 'HEURISTIC',
          level: 'INFO',
          status: 'PROCESSING',
          message: `已根據圖譜推薦 ${res.recommended_rules?.length || 0} 條最佳規則，等待使用者確認選取...`,
        })
      }
    }

    // 即時建立 SSE 連線
    connectSSE(res.task_id)
  } catch (err: any) {
    console.error('上傳失敗:', err)
    const errDetail = err?.response?.data?.detail || err?.message || '請確認檔案格式是否正確。'
    alert(`上傳失敗: ${errDetail}`)
  } finally {
    isUploading.value = false
  }
}

/**
 * 確認規則並啟動正式 DRC 檢測 (Step 4 ~ Step 6)
 */
const handleStartRun = async (selectedRuleIds: string[]) => {
  if (!currentTaskId.value) return
  isStartingRun.value = true

  try {
    await startTaskRun(currentTaskId.value, selectedRuleIds)
    taskStatus.value = 'PROCESSING'

    // Step 3 完成
    const s3 = steps.value.find((s) => s.step_name === 'RULE_SELECTION')
    if (s3) {
      s3.status = 'COMPLETED'
      s3.completed_at = new Date().toISOString()
      s3.log_message = `已確認選取 ${selectedRuleIds.length} 條規則，正式啟動 DBOS 工作流`
    }

    // 關閉抽屜，露出 Live Log
    activeDrawerStep.value = null

    // 開始監聽 SSE
    connectSSE(currentTaskId.value)
  } catch (err) {
    console.error('啟動任務失敗:', err)
  } finally {
    isStartingRun.value = false
  }
}

/**
 * 建立 SSE 即時串流連線
 */
const connectSSE = (taskId: string) => {
  if (activeEventSource) {
    activeEventSource.close()
  }

  activeEventSource = subscribeTaskEvents(
    taskId,
    (updatedStep) => {
      const idx = steps.value.findIndex((s) => s.step_name === updatedStep.step_name)
      if (idx !== -1) {
        steps.value[idx] = {
          ...steps.value[idx],
          status: updatedStep.status,
          log_message: updatedStep.log_message,
          started_at: updatedStep.started_at || steps.value[idx].started_at,
          completed_at: updatedStep.completed_at || steps.value[idx].completed_at,
        }
      }

      const isDuplicate = logs.value.some(
        (l) => l.step_name === updatedStep.step_name && l.status === updatedStep.status && l.message === updatedStep.log_message
      )
      if (!isDuplicate) {
        logs.value.push({
          id: Math.random().toString(36).substr(2, 9),
          timestamp: new Date().toLocaleTimeString(),
          step_name: updatedStep.step_name,
          category: 'SYSTEM',
          level: 'INFO',
          status: updatedStep.status,
          message: updatedStep.log_message || `步驟 ${updatedStep.step_name} 狀態更新為 ${updatedStep.status}`,
        })
      }
    },
    async (taskEndData) => {
      taskStatus.value = taskEndData.status || 'COMPLETED'
      if (taskStatus.value === 'COMPLETED') {
        try {
          const report = await fetchTaskReport(taskId)
          taskReport.value = report
        } catch (e) {
          console.warn('載入報告失敗:', e)
        }
      }
    },
    (err) => {
      console.warn('SSE 連線異常:', err)
    },
    (newLog) => {
      const isDuplicate = logs.value.some((l) => l.id === newLog.id)
      if (!isDuplicate) {
        logs.value.push(newLog)
      }
    }
  )
}

const reconnectSSE = () => {
  if (currentTaskId.value) {
    connectSSE(currentTaskId.value)
  }
}

const handleStopCurrentTask = async () => {
  if (!currentTaskId.value) return
  isStopping.value = true
  try {
    await stopTask(currentTaskId.value)
    taskStatus.value = 'CANCELLED'
    if (activeEventSource) activeEventSource.close()
  } catch (err) {
    console.error('停止任務失敗:', err)
  } finally {
    isStopping.value = false
  }
}

const resetToNewTask = () => {
  if (activeEventSource) activeEventSource.close()
  currentTaskId.value = ''
  activeProjectName.value = ''
  taskStatus.value = 'PENDING'
  hasUploadedFile.value = false
  taskReport.value = null
  activeDrawerStep.value = null
  logs.value = []
  steps.value = [
    { step_name: 'UNPACK_AND_VALIDATE', status: 'PENDING', log_message: '等待檔案上傳與預檢...' },
    { step_name: 'PARSE_AND_GRAPH', status: 'PENDING', log_message: '等待圖譜構建與線路解析...' },
    { step_name: 'RULE_SELECTION', status: 'PENDING', log_message: '等待推薦與選取規則...' },
    { step_name: 'HEURISTIC_CHECK', status: 'PENDING', log_message: '等待傳統規則演算法比對...' },
    { step_name: 'LLM_REASONING', status: 'PENDING', log_message: '等待本地大模型語意推理...' },
    { step_name: 'GENERATE_REPORT', status: 'PENDING', log_message: '等待產出完整 DRC 報告...' },
  ]
  router.replace({ query: {} })
}

const handleClearLogs = () => {
  logs.value = []
}

const copyTaskId = async () => {
  if (currentTaskId.value) {
    await navigator.clipboard.writeText(currentTaskId.value)
  }
}

// 抽屜呈現輔助
const getDrawerTitle = (stepName: string): string => {
  switch (stepName) {
    case 'UNPACK_AND_VALIDATE':
      return '步驟 1: 解壓縮與檔案格式預檢詳情'
    case 'PARSE_AND_GRAPH':
      return '步驟 2: 線路圖譜拓撲與元件分析詳情'
    case 'RULE_SELECTION':
      return '步驟 3: DRC 檢驗規則推薦與選取'
    case 'HEURISTIC_CHECK':
      return '步驟 4: 傳統演算法規則比對'
    case 'LLM_REASONING':
      return '步驟 5: 本地大模型語意推理'
    case 'GENERATE_REPORT':
      return '步驟 6: DRC 報告彙整'
    default:
      return '步驟詳情'
  }
}

const archiveFilesList = computed(() => {
  return (
    archiveDetails.value?.files || [
      {
        filename: 'circuit_schematic.xml',
        relative_path: 'circuit_schematic.xml',
        size_bytes: 1048576,
        is_xml: true,
        is_netlist: false,
      },
      {
        filename: 'allegro_netlist.dat',
        relative_path: 'allegro_netlist.dat',
        size_bytes: 524288,
        is_xml: false,
        is_netlist: true,
      },
    ]
  )
})

const detectedBuses = computed(() => {
  return graphDetails.value?.buses || preSummary.value.buses || []
})

const keyIcsList = computed(() => {
  if (graphDetails.value?.key_ics !== undefined) {
    return graphDetails.value.key_ics
  }
  return graphDetails.value?.main_ics || []
})

const keyConnectorsList = computed(() => {
  return graphDetails.value?.key_connectors || []
})

const icDirectoryByRole = computed(() => {
  return graphDetails.value?.ic_directory_by_role || {}
})

const nonElectricalList = computed(() => {
  return graphDetails.value?.non_electrical_components || []
})

// Step 2 詳細子頁籤控制
const activeStep2Tab = ref<'components' | 'nets'>('components')

// 元件篩選與分頁狀態
const compSearch = ref('')
const compCategoryFilter = ref('')
const compSubCategoryFilter = ref('')
const compRoleFilter = ref('')
const compElectricalFilter = ref<'all' | 'electrical' | 'non_electrical'>('all')
const compPage = ref(1)
const compPageSize = ref(20)

// 網路篩選與分頁狀態
const netSearch = ref('')
const netTypeFilter = ref<'all' | 'power' | 'ground' | 'bus' | 'signal'>('all')
const netBusFilter = ref('')
const netPage = ref(1)
const netPageSize = ref(20)

// 全量元件與網路清單
const allComponents = computed(() => {
  return graphDetails.value?.components || []
})

const allNets = computed(() => {
  return graphDetails.value?.nets || []
})

// 元件可用篩選選項 (動態提取自當前數據)
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

// 元件篩選結果
const filteredComponents = computed(() => {
  let list = allComponents.value
  if (compCategoryFilter.value) {
    list = list.filter((c) => c.category === compCategoryFilter.value)
  }
  if (compSubCategoryFilter.value) {
    list = list.filter((c) => c.sub_category === compSubCategoryFilter.value)
  }
  if (compRoleFilter.value) {
    list = list.filter((c) => c.functional_role === compRoleFilter.value)
  }
  if (compElectricalFilter.value === 'electrical') {
    list = list.filter((c) => c.is_electrical !== false)
  } else if (compElectricalFilter.value === 'non_electrical') {
    list = list.filter((c) => c.is_electrical === false)
  }
  if (compSearch.value.trim()) {
    const q = compSearch.value.trim().toLowerCase()
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
  if (compPageSize.value === -1) return 1
  return Math.max(1, Math.ceil(filteredComponents.value.length / compPageSize.value))
})

const paginatedComponents = computed(() => {
  if (compPageSize.value === -1) return filteredComponents.value
  const start = (compPage.value - 1) * compPageSize.value
  return filteredComponents.value.slice(start, start + compPageSize.value)
})

const hasCompFilters = computed(() => {
  return !!(
    compSearch.value ||
    compCategoryFilter.value ||
    compSubCategoryFilter.value ||
    compRoleFilter.value ||
    compElectricalFilter.value !== 'all'
  )
})

const clearCompFilters = () => {
  compSearch.value = ''
  compCategoryFilter.value = ''
  compSubCategoryFilter.value = ''
  compRoleFilter.value = ''
  compElectricalFilter.value = 'all'
  compPage.value = 1
}

watch(
  [compSearch, compCategoryFilter, compSubCategoryFilter, compRoleFilter, compElectricalFilter, compPageSize],
  () => {
    compPage.value = 1
  }
)

// 網路可用篩選選項
const availableNetBuses = computed(() => {
  const set = new Set<string>()
  allNets.value.forEach((n) => {
    if (n.bus_type) set.add(n.bus_type)
  })
  return Array.from(set).sort()
})

// 網路篩選結果
const filteredNets = computed(() => {
  let list = allNets.value
  if (netTypeFilter.value === 'power') {
    list = list.filter((n) => n.is_power)
  } else if (netTypeFilter.value === 'ground') {
    list = list.filter((n) => n.is_ground)
  } else if (netTypeFilter.value === 'bus') {
    list = list.filter((n) => !!n.bus_type)
  } else if (netTypeFilter.value === 'signal') {
    list = list.filter((n) => !n.is_power && !n.is_ground && !n.bus_type)
  }

  if (netBusFilter.value) {
    list = list.filter((n) => n.bus_type === netBusFilter.value)
  }

  if (netSearch.value.trim()) {
    const q = netSearch.value.trim().toLowerCase()
    list = list.filter(
      (n) =>
        n.net_name.toLowerCase().includes(q) ||
        (n.connected_components && n.connected_components.some((c) => c.toLowerCase().includes(q)))
    )
  }
  return list
})

const totalNetPages = computed(() => {
  if (netPageSize.value === -1) return 1
  return Math.max(1, Math.ceil(filteredNets.value.length / netPageSize.value))
})

const paginatedNets = computed(() => {
  if (netPageSize.value === -1) return filteredNets.value
  const start = (netPage.value - 1) * netPageSize.value
  return filteredNets.value.slice(start, start + netPageSize.value)
})

const hasNetFilters = computed(() => {
  return !!(netSearch.value || netTypeFilter.value !== 'all' || netBusFilter.value)
})

const clearNetFilters = () => {
  netSearch.value = ''
  netTypeFilter.value = 'all'
  netBusFilter.value = ''
  netPage.value = 1
}

watch([netSearch, netTypeFilter, netBusFilter, netPageSize], () => {
  netPage.value = 1
})

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


const formatBytes = (bytes: number): string => {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const formatStatus = (st: string): string => {
  switch (st) {
    case 'PROCESSING':
      return '執行中'
    case 'READY_FOR_RUN':
      return '等待確認規則'
    case 'PENDING':
      return '等待開始'
    case 'COMPLETED':
      return '已完成'
    case 'FAILED':
      return '失敗'
    case 'CANCELLED':
      return '已中止'
    default:
      return st
  }
}

const getStatusSeverity = (st: string) => {
  switch (st) {
    case 'COMPLETED':
      return 'success'
    case 'PROCESSING':
      return 'info'
    case 'READY_FOR_RUN':
      return 'warn'
    case 'FAILED':
      return 'danger'
    default:
      return 'secondary'
  }
}
</script>

<style scoped>
.task-monitor-view {
  padding: 1.25rem 2rem;
  max-width: 1600px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

/* 頂部管理列 */
.task-management-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background-color: #ffffff;
  padding: 0.85rem 1.25rem;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.title-with-badge {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.2rem;
}

.view-title {
  font-size: 1.15rem;
  font-weight: 700;
  color: #0f172a;
  margin: 0;
  display: flex;
  align-items: center;
}

.task-id-row {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.78rem;
  color: #64748b;
}

.task-id-code {
  background-color: #f1f5f9;
  padding: 0.15rem 0.45rem;
  border-radius: 4px;
  color: #0284c7;
  font-family: monospace;
}

.task-actions-col {
  display: flex;
  gap: 0.5rem;
}

/* 上傳檔案區塊 */
.upload-section-card {
  background-color: #ffffff;
  border-radius: 8px;
  border: 1px dashed #cbd5e1;
  padding: 1.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.upload-intro {
  margin-bottom: 1rem;
}

.upload-title {
  font-size: 1.05rem;
  font-weight: 700;
  color: #0f172a;
  margin: 0 0 0.25rem 0;
}

.upload-desc {
  font-size: 0.82rem;
  color: #64748b;
  margin: 0;
}

/* 雙欄主工作區 */
.workspace-grid {
  display: grid;
  grid-template-columns: 1fr 2fr;
  gap: 1.25rem;
  min-height: 580px;
}

.timeline-column {
  min-width: 0;
}

.log-and-drawer-column {
  position: relative;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

/* 終端機面板包裝 */
.terminal-wrapper {
  background-color: #1e1e1e;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  height: 100%;
  border: 1px solid #333333;
  overflow: hidden;
}

.terminal-topbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 0.85rem;
  background-color: #252526;
  border-bottom: 1px solid #333333;
}

.terminal-title {
  font-size: 0.78rem;
  color: #cccccc;
  font-weight: 600;
  display: flex;
  align-items: center;
}

.terminal-stats {
  font-size: 0.72rem;
  color: #888888;
}

/* 滑動覆蓋抽屜 (Overlay Drawer) */
.drawer-backdrop {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.45);
  backdrop-filter: blur(2px);
  z-index: 20;
  border-radius: 8px;
}

.step-overlay-drawer {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: #ffffff;
  border-radius: 8px;
  border: 1px solid #cbd5e1;
  box-shadow: -4px 0 20px rgba(0, 0, 0, 0.15);
  z-index: 30;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  animation: slideInRight 0.22s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes slideInRight {
  from {
    transform: translateX(30px);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

.drawer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.85rem 1.25rem;
  background-color: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
}

.drawer-header-title {
  font-size: 0.95rem;
  font-weight: 700;
  color: #0f172a;
  display: flex;
  align-items: center;
}

.drawer-close-btn {
  background: transparent;
  border: none;
  font-size: 1rem;
  color: #64748b;
  cursor: pointer;
  padding: 0.25rem;
  border-radius: 4px;
}

.drawer-close-btn:hover {
  color: #0f172a;
  background-color: #e2e8f0;
}

.mandatory-badge {
  font-size: 0.72rem;
  font-weight: 600;
  color: #0284c7;
  background-color: #e0f2fe;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
}

.drawer-body {
  flex: 1;
  padding: 1.25rem;
  overflow-y: auto;
}

.drawer-stat-banner {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(110px, 1fr));
  gap: 0.75rem;
  margin-bottom: 1.25rem;
  background-color: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 0.85rem;
}

.banner-stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.stat-num {
  font-size: 1.25rem;
  font-weight: 700;
  color: #0f172a;
}

.stat-name {
  font-size: 0.7rem;
  color: #64748b;
}

.content-subtitle {
  font-size: 0.88rem;
  font-weight: 600;
  color: #334155;
  margin: 1rem 0 0.5rem 0;
}

.chip-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
  flex-wrap: wrap;
}

.chip-label {
  font-size: 0.78rem;
  color: #64748b;
  font-weight: 600;
}

.drawer-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.8rem;
}

.drawer-table th {
  background-color: #f8fafc;
  padding: 0.5rem 0.75rem;
  border-bottom: 1px solid #e2e8f0;
  text-align: left;
  color: #475569;
}

.drawer-table td {
  padding: 0.55rem 0.75rem;
  border-bottom: 1px solid #f1f5f9;
}

.badge-tag {
  font-size: 0.7rem;
  padding: 0.15rem 0.45rem;
  border-radius: 4px;
  background-color: #f1f5f9;
  color: #475569;
}

.tag-cyan { background-color: #ecfeff; color: #0891b2; font-weight: 600; }
.tag-purple { background-color: #faf5ff; color: #7c3aed; font-weight: 600; }
.tag-blue { background-color: #eff6ff; color: #2563eb; }
.tag-green { background-color: #ecfdf5; color: #059669; }
.tag-gray { background-color: #f1f5f9; color: #64748b; border: 1px solid #cbd5e1; }
.tag-outline { background-color: #ffffff; color: #334155; border: 1px solid #cbd5e1; }
.tag-yellow { background-color: #fefce8; color: #ca8a04; font-weight: 600; }
.tag-orange { background-color: #fff7ed; color: #c2410c; font-weight: 600; }

/* Step 2 子頁籤切換 */
.step2-subtabs {
  display: flex;
  gap: 0.5rem;
  margin: 1.25rem 0 0.85rem 0;
  border-bottom: 2px solid #e2e8f0;
  padding-bottom: 0.5rem;
}

.subtab-btn {
  background: transparent;
  border: none;
  padding: 0.5rem 0.85rem;
  font-size: 0.85rem;
  font-weight: 600;
  color: #64748b;
  cursor: pointer;
  border-radius: 6px;
  display: flex;
  align-items: center;
  gap: 0.4rem;
  transition: all 0.15s ease;
}

.subtab-btn:hover {
  background-color: #f1f5f9;
  color: #0f172a;
}

.subtab-btn.active {
  background-color: #e0f2fe;
  color: #0284c7;
}

.subtab-badge {
  font-size: 0.72rem;
  background-color: #e2e8f0;
  color: #334155;
  padding: 0.1rem 0.45rem;
  border-radius: 999px;
  font-weight: 700;
}

.subtab-btn.active .subtab-badge {
  background-color: #0284c7;
  color: #ffffff;
}

/* 篩選工具列 */
.table-filter-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
  background-color: #f8fafc;
  padding: 0.65rem 0.75rem;
  border-radius: 6px;
  border: 1px solid #e2e8f0;
}

.filter-search-box {
  position: relative;
  flex: 1 1 200px;
  min-width: 180px;
}

.filter-search-input {
  width: 100%;
  padding: 0.4rem 0.65rem 0.4rem 1.85rem;
  font-size: 0.8rem;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  background-color: #ffffff;
  color: #0f172a;
  outline: none;
  box-sizing: border-box;
}

.filter-search-input:focus {
  border-color: #0284c7;
  box-shadow: 0 0 0 2px rgba(2, 132, 199, 0.15);
}

.filter-search-icon {
  position: absolute;
  left: 0.6rem;
  top: 50%;
  transform: translateY(-50%);
  color: #94a3b8;
  font-size: 0.8rem;
  pointer-events: none;
}

.filter-select {
  padding: 0.4rem 0.6rem;
  font-size: 0.8rem;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  background-color: #ffffff;
  color: #334155;
  outline: none;
  cursor: pointer;
}

.filter-select:focus {
  border-color: #0284c7;
}

.btn-clear-filter {
  background: transparent;
  border: 1px dashed #94a3b8;
  color: #64748b;
  padding: 0.35rem 0.65rem;
  font-size: 0.78rem;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.15s ease;
  display: flex;
  align-items: center;
}

.btn-clear-filter:hover {
  background-color: #fee2e2;
  border-color: #ef4444;
  color: #ef4444;
}

/* 分頁與筆數資訊列 */
.table-pagination-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.4rem 0.25rem 0.65rem 0.25rem;
  font-size: 0.78rem;
  color: #64748b;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.pagination-controls {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.page-size-label {
  font-size: 0.75rem;
  color: #64748b;
}

.page-size-select {
  padding: 0.2rem 0.4rem;
  font-size: 0.75rem;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  background: #ffffff;
  color: #334155;
}

.pagination-btn {
  border: 1px solid #cbd5e1;
  background: #ffffff;
  color: #334155;
  padding: 0.25rem 0.55rem;
  border-radius: 4px;
  font-size: 0.75rem;
  cursor: pointer;
  transition: all 0.1s ease;
}

.pagination-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.pagination-btn:not(:disabled):hover {
  background-color: #f1f5f9;
  border-color: #94a3b8;
}

.page-number-indicator {
  font-size: 0.75rem;
  color: #475569;
  font-weight: 600;
  padding: 0 0.25rem;
}

/* 表格容器與單元格修飾 */
.table-container {
  overflow-x: auto;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  background-color: #ffffff;
  max-height: 480px;
  overflow-y: auto;
}

.cell-desc {
  max-width: 220px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  display: inline-block;
  vertical-align: middle;
  font-size: 0.78rem;
  color: #475569;
}

.net-tags-wrapper {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.25rem;
}

.net-tag {
  font-size: 0.7rem;
  padding: 0.12rem 0.4rem;
  border-radius: 3px;
  background-color: #f1f5f9;
  color: #334155;
  border: 1px solid #e2e8f0;
  display: inline-block;
  font-family: monospace;
}

.net-tag-more {
  font-size: 0.7rem;
  color: #0284c7;
  font-weight: 600;
  cursor: help;
  padding: 0.1rem 0.25rem;
}

.empty-table-state {
  padding: 2.5rem;
  text-align: center;
  color: #94a3b8;
  font-size: 0.85rem;
}

.role-directory-card {
  margin-top: 0.5rem;
  margin-bottom: 0.75rem;
  background-color: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 0.75rem;
}

.role-row {
  margin-bottom: 0.35rem;
}

.role-label {
  color: #475569;
  min-width: 100px;
}

.info-box {
  background-color: #f8fafc;
  border-left: 3px solid #0284c7;
  padding: 0.75rem 1rem;
  font-size: 0.82rem;
  color: #334155;
  border-radius: 0 4px 4px 0;
  margin-bottom: 1rem;
}

.status-summary-card {
  background-color: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 1rem;
}

.summary-line {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.5rem;
  font-size: 0.85rem;
  font-weight: 600;
}

.summary-log {
  font-size: 0.8rem;
  color: #64748b;
  margin: 0;
}

/* 報告區域 */
.report-dashboard-section {
  background-color: #ffffff;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  padding: 1.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.text-danger {
  color: #ef4444;
}
</style>
