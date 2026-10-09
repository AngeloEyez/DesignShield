<template>
  <div class="dashboard-container p-6 max-w-[1500px] mx-auto">
    <!-- 頂部頁頭資訊與主要操作 -->
    <header class="dashboard-header flex justify-between items-start mb-6 border-b border-[var(--vscode-border,#333333)] pb-5">
      <div class="header-left flex flex-col">
        <h1 class="page-title text-[1.45rem] font-bold text-[var(--vscode-text-heading,#ffffff)] mb-1.5 flex items-center">
          <i class="pi pi-th-large text-emerald-400 mr-2"></i>
          系統任務總覽儀表板 (Mission Dashboard)
        </h1>
        <p class="page-subtitle text-[0.85rem] text-[var(--vscode-text-muted,#858585)] m-0">
          實時監控所有 DRC 線路檢測與分析任務、系統伺服器健康狀況與儲存磁碟佔用指標。
        </p>
      </div>

      <div class="header-actions flex gap-3">
        <Button
          label="重新整理"
          icon="pi pi-refresh"
          severity="secondary"
          size="small"
          :loading="isLoading"
          @click="loadDashboardData"
        />
        <Button
          label="新增 DRC 任務"
          icon="pi pi-plus"
          severity="primary"
          size="small"
          @click="navigateToNewTask"
        />
      </div>
    </header>

    <!-- 系統健康度與關鍵指標卡片列 -->
    <section class="stats-overview-grid grid grid-cols-[repeat(auto-fit,minmax(260px,1fr))] gap-5 mb-7">
      <!-- 指標 1: 伺服器健康狀態 (含 FastAPI/DBOS, Database, LLM 燈號) -->
      <div class="stat-card health-stat-card bg-[var(--vscode-bg-panel,#252526)] rounded-md p-4 flex items-start gap-4 shadow-md border border-[var(--vscode-border,#333333)] transition-all duration-150 hover:-translate-y-0.5 hover:shadow-lg">
        <div
          class="stat-icon-wrapper w-[42px] h-[42px] rounded-md flex items-center justify-center text-xl shrink-0"
          :class="isHealthy ? 'bg-emerald-500/15 text-emerald-400' : 'bg-red-500/15 text-red-400'"
        >
          <i class="pi pi-server"></i>
        </div>
        <div class="stat-body flex flex-col flex-1 min-w-0">
          <div class="stat-header-row flex justify-between items-center mb-1">
            <span class="stat-label text-[0.75rem] font-semibold text-[var(--vscode-text-muted,#858585)] uppercase tracking-wider mb-1">伺服器健康狀態</span>
            <span
              class="badge-mini text-[0.68rem] px-1.5 py-0.5 rounded font-semibold inline-flex items-center"
              :class="isHealthy ? 'status-online bg-emerald-500/15 text-emerald-400' : 'status-danger bg-red-500/15 text-red-400'"
            >
              <span
                class="pulse-indicator w-1.5 h-1.5 rounded-full inline-block mr-1.5"
                :class="isHealthy ? 'pulse-green bg-emerald-400 shadow-[0_0_6px_#4ec9b0]' : 'pulse-red bg-red-500 shadow-[0_0_6px_#f14c4c]'"
              ></span>
              {{ isHealthy ? '健康運作' : '連線異常' }}
            </span>
          </div>

          <!-- 各元件燈號列表 (FASTAPI/DBOS, Database, LLM) -->
          <div class="health-lights-row flex items-center gap-1.5 my-1 flex-wrap">
            <div class="light-chip inline-flex items-center gap-1.5 bg-[#1e1e1e] border border-[#333333] px-2 py-0.5 rounded-full text-[0.7rem] text-[#cccccc] cursor-default hover:border-[#555555] transition-colors" :title="healthDetails.components?.api?.message || 'FastAPI / DBOS 引擎在線'">
              <span class="light-dot w-[7px] h-[7px] rounded-full inline-block" :class="getLightDotClass(healthDetails.components?.api?.status)"></span>
              <span class="light-label font-medium text-[0.69rem]">FastAPI/DBOS</span>
            </div>
            <div class="light-chip inline-flex items-center gap-1.5 bg-[#1e1e1e] border border-[#333333] px-2 py-0.5 rounded-full text-[0.7rem] text-[#cccccc] cursor-default hover:border-[#555555] transition-colors" :title="healthDetails.components?.database?.message || '資料庫連線正常'">
              <span class="light-dot w-[7px] h-[7px] rounded-full inline-block" :class="getLightDotClass(healthDetails.components?.database?.status)"></span>
              <span class="light-label font-medium text-[0.69rem]">Database</span>
            </div>
            <div class="light-chip inline-flex items-center gap-1.5 bg-[#1e1e1e] border border-[#333333] px-2 py-0.5 rounded-full text-[0.7rem] text-[#cccccc] cursor-default hover:border-[#555555] transition-colors" :title="llmChipTooltip">
              <span class="light-dot w-[7px] h-[7px] rounded-full inline-block" :class="getLightDotClass(healthDetails.components?.llm?.status)"></span>
              <span class="light-label font-medium text-[0.69rem]">LLM</span>
            </div>
          </div>
          <div
            class="stat-hint health-stat-hint text-[0.72rem] text-[var(--vscode-text-muted,#858585)] whitespace-normal break-words leading-relaxed mt-1 block"
            :title="healthHintItems.map((item) => item.text).join(' · ')"
          >
            <template v-for="(item, idx) in healthHintItems" :key="idx">
              <span v-if="idx > 0" class="hint-separator text-[#555555] mx-1"> · </span>
              <span :class="item.className">{{ item.text }}</span>
            </template>
          </div>
        </div>
      </div>

      <!-- 指標 2: 儲存空間佔用 (含剩餘空間顯示與小型直條圖) -->
      <div class="stat-card storage-stat-card bg-[var(--vscode-bg-panel,#252526)] rounded-md p-4 flex items-start gap-4 shadow-md border border-[var(--vscode-border,#333333)] transition-all duration-150 hover:-translate-y-0.5 hover:shadow-lg">
        <div class="stat-icon-wrapper w-[42px] h-[42px] rounded-md flex items-center justify-center text-xl shrink-0 bg-sky-500/15 text-sky-400">
          <i class="pi pi-database"></i>
        </div>
        <div class="stat-body flex flex-col flex-1 min-w-0">
          <div class="stat-header-row flex justify-between items-center mb-1">
            <span class="stat-label text-[0.75rem] font-semibold text-[var(--vscode-text-muted,#858585)] uppercase tracking-wider mb-1">儲存空間總佔用</span>
            <span class="badge-mini status-info text-[0.68rem] px-1.5 py-0.5 rounded font-semibold inline-flex items-center bg-sky-500/15 text-sky-400" :title="storageBarTooltip">
              剩餘: {{ formattedDiskFree }}
            </span>
          </div>

          <div class="stat-value-row flex items-baseline gap-2 mb-1">
            <span class="stat-value text-[1.35rem] font-bold text-[var(--vscode-text-heading,#ffffff)]">{{ storageStats.total_mb }} MB</span>
            <span class="stat-subtext text-[0.78rem] text-[var(--vscode-text-muted,#858585)]">/ {{ storageStats.total_files }} 個檔案</span>
          </div>

          <!-- 小型圖形化直條圖 (直條進度圖) -->
          <div class="mini-bar-container my-1" :title="storageBarTooltip">
            <div class="mini-bar-track h-1.5 bg-[#1e1e1e] rounded-[3px] overflow-hidden flex border border-[#333333]">
              <!-- 已用空間直條 (以青藍色高亮呈現) -->
              <div
                class="mini-bar-fill bar-used bg-gradient-to-r from-sky-600 to-sky-400 h-full transition-[width] duration-300"
                :style="{ width: diskUsedBarWidth + '%' }"
              ></div>
              <!-- 剩餘可用空間直條 (以深灰底色呈現剩餘) -->
              <div
                class="mini-bar-fill bar-free bg-[#2a2d2e] h-full transition-[width] duration-300"
                :style="{ width: (100 - diskUsedBarWidth) + '%' }"
              ></div>
            </div>
            <div class="mini-bar-labels flex justify-between items-center mt-1 text-[0.68rem] text-[var(--vscode-text-muted,#858585)]">
              <span class="bar-legend-item inline-flex items-center gap-1">
                <span class="legend-color legend-blue w-1.5 h-1.5 rounded-[2px] inline-block bg-sky-400"></span>已用 {{ storageStats.disk_used_percent || 0 }}%
              </span>
              <span class="bar-legend-item inline-flex items-center gap-1">
                <span class="legend-color legend-green w-1.5 h-1.5 rounded-[2px] inline-block bg-emerald-400"></span>剩餘 {{ formattedDiskFree }}
              </span>
            </div>
          </div>

          <span class="stat-hint text-[0.72rem] text-[var(--vscode-text-muted,#858585)] truncate">
            上傳: {{ storageStats.uploads.file_count }} ({{ formatStorageMb(storageStats.uploads.total_bytes) }}) | 暫存: {{ storageStats.staging.file_count }} | 報告: {{ storageStats.reports.file_count }}
          </span>
        </div>
      </div>

      <!-- 指標 3: DRC 規則庫規模 -->
      <div class="stat-card bg-[var(--vscode-bg-panel,#252526)] rounded-md p-4 flex items-start gap-4 shadow-md border border-[var(--vscode-border,#333333)] transition-all duration-150 hover:-translate-y-0.5 hover:shadow-lg">
        <div class="stat-icon-wrapper w-[42px] h-[42px] rounded-md flex items-center justify-center text-xl shrink-0 bg-purple-500/15 text-purple-400">
          <i class="pi pi-sliders-h"></i>
        </div>
        <div class="stat-body flex flex-col flex-1 min-w-0">
          <span class="stat-label text-[0.75rem] font-semibold text-[var(--vscode-text-muted,#858585)] uppercase tracking-wider mb-1">規則庫規模</span>
          <div class="stat-value-row flex items-baseline gap-2 mb-1">
            <span class="stat-value text-[1.35rem] font-bold text-[var(--vscode-text-heading,#ffffff)]">{{ totalRulesCount }} 條</span>
            <span class="badge-mini status-active text-[0.68rem] px-1.5 py-0.5 rounded font-semibold inline-flex items-center bg-purple-500/15 text-purple-400">{{ activeRulesCount }} 條啟用中</span>
          </div>
          <span class="stat-hint text-[0.72rem] text-[var(--vscode-text-muted,#858585)] truncate">
            傳統演算法: {{ heuristicRulesCount }} | 本地 LLM: {{ llmRulesCount }}
          </span>
        </div>
      </div>

      <!-- 指標 4: 任務狀態分佈 -->
      <div class="stat-card bg-[var(--vscode-bg-panel,#252526)] rounded-md p-4 flex items-start gap-4 shadow-md border border-[var(--vscode-border,#333333)] transition-all duration-150 hover:-translate-y-0.5 hover:shadow-lg">
        <div class="stat-icon-wrapper w-[42px] h-[42px] rounded-md flex items-center justify-center text-xl shrink-0 bg-emerald-500/15 text-emerald-400">
          <i class="pi pi-list-check"></i>
        </div>
        <div class="stat-body flex flex-col flex-1 min-w-0">
          <span class="stat-label text-[0.75rem] font-semibold text-[var(--vscode-text-muted,#858585)] uppercase tracking-wider mb-1">進行中與已排程任務</span>
          <div class="stat-value-row flex items-baseline gap-2 mb-1">
            <span class="stat-value text-[1.35rem] font-bold text-emerald-400">{{ runningTasksCount }} 執行中</span>
            <span class="stat-subtext text-[0.78rem] text-[var(--vscode-text-muted,#858585)]">/ {{ scheduledTasksCount }} 等待排程</span>
          </div>
          <span class="stat-hint text-[0.72rem] text-[var(--vscode-text-muted,#858585)] truncate">累計完成檢測: {{ completedTasksCount }} 筆</span>
        </div>
      </div>
    </section>

    <!-- 任務清單區塊 (含狀態分頁 Tab) -->
    <section class="tasks-table-section bg-[var(--vscode-bg-panel,#252526)] rounded-md border border-[var(--vscode-border,#333333)] shadow-md overflow-hidden">
      <div class="section-toolbar flex justify-between items-center p-2.5 px-4 border-b border-[var(--vscode-border,#333333)] bg-[var(--vscode-bg-header,#2d2d2d)] flex-wrap gap-3">
        <div class="tabs-nav flex gap-1.5">
          <button
            class="tab-btn border-0 text-[0.82rem] px-3 py-1.5 rounded cursor-pointer flex items-center transition-all hover:text-white hover:bg-[var(--vscode-bg-hover,#2a2d2e)]"
            :class="currentTab === 'running' ? 'active text-sky-400 bg-sky-500/20 font-semibold' : 'bg-transparent text-[var(--vscode-text-secondary,#999999)] font-medium'"
            @click="currentTab = 'running'"
          >
            <i class="pi pi-spin pi-spinner mr-1" v-if="runningTasksCount > 0"></i>
            正在進行中
            <span class="tab-count text-[0.7rem] bg-white/10 text-[var(--vscode-text-main,#cccccc)] px-1.5 py-0.5 rounded-full ml-1.5">{{ runningTasksCount }}</span>
          </button>
          <button
            class="tab-btn border-0 text-[0.82rem] px-3 py-1.5 rounded cursor-pointer flex items-center transition-all hover:text-white hover:bg-[var(--vscode-bg-hover,#2a2d2e)]"
            :class="currentTab === 'scheduled' ? 'active text-sky-400 bg-sky-500/20 font-semibold' : 'bg-transparent text-[var(--vscode-text-secondary,#999999)] font-medium'"
            @click="currentTab = 'scheduled'"
          >
            等待與排程
            <span class="tab-count text-[0.7rem] bg-white/10 text-[var(--vscode-text-main,#cccccc)] px-1.5 py-0.5 rounded-full ml-1.5">{{ scheduledTasksCount }}</span>
          </button>
          <button
            class="tab-btn border-0 text-[0.82rem] px-3 py-1.5 rounded cursor-pointer flex items-center transition-all hover:text-white hover:bg-[var(--vscode-bg-hover,#2a2d2e)]"
            :class="currentTab === 'completed' ? 'active text-sky-400 bg-sky-500/20 font-semibold' : 'bg-transparent text-[var(--vscode-text-secondary,#999999)] font-medium'"
            @click="currentTab = 'completed'"
          >
            已完成與歷史紀錄 (最近 10 筆)
            <span class="tab-count text-[0.7rem] bg-white/10 text-[var(--vscode-text-main,#cccccc)] px-1.5 py-0.5 rounded-full ml-1.5">{{ filteredCompletedTasks.length }}</span>
          </button>
          <button
            class="tab-btn border-0 text-[0.82rem] px-3 py-1.5 rounded cursor-pointer flex items-center transition-all hover:text-white hover:bg-[var(--vscode-bg-hover,#2a2d2e)]"
            :class="currentTab === 'all' ? 'active text-sky-400 bg-sky-500/20 font-semibold' : 'bg-transparent text-[var(--vscode-text-secondary,#999999)] font-medium'"
            @click="currentTab = 'all'"
          >
            所有任務
            <span class="tab-count text-[0.7rem] bg-white/10 text-[var(--vscode-text-main,#cccccc)] px-1.5 py-0.5 rounded-full ml-1.5">{{ allTasks.length }}</span>
          </button>
        </div>

        <div class="type-filter flex items-center gap-2">
          <span class="filter-label text-[0.78rem] text-[var(--vscode-text-muted,#858585)]">任務類型:</span>
          <select v-model="selectedTypeFilter" class="filter-select text-[0.78rem] p-1 px-2.5 border border-[var(--vscode-border,#333333)] rounded bg-[var(--vscode-bg-input,#1e1e1e)] text-[var(--vscode-text-main,#cccccc)] outline-none">
            <option value="ALL">全部類型 (All)</option>
            <option value="DRC">線路 DRC 檢測</option>
            <option value="RULE_EXTRACTION">規則提取 (擴充)</option>
            <option value="DATASHEET_ANALYSIS">Datasheet 分析 (擴充)</option>
          </select>
        </div>
      </div>

      <!-- 任務列表表格 -->
      <div class="table-container overflow-x-auto">
        <div v-if="isLoading" class="loading-state flex flex-col items-center justify-center py-16 px-8 text-[var(--vscode-text-muted,#858585)]">
          <i class="pi pi-spin pi-spinner loading-icon text-[2.2rem] mb-3 text-[var(--vscode-text-muted,#858585)]"></i>
          <span>正在載入任務列表與系統指標...</span>
        </div>

        <div v-else-if="currentDisplayTasks.length === 0" class="empty-state flex flex-col items-center justify-center py-16 px-8 text-[var(--vscode-text-muted,#858585)]">
          <i class="pi pi-inbox empty-icon text-[2.2rem] mb-3 text-[var(--vscode-text-muted,#858585)]"></i>
          <p class="empty-text text-[0.9rem] mb-4">目前尚無符合此條件的任務</p>
          <Button
            label="立即建立新任務"
            icon="pi pi-plus"
            severity="primary"
            size="small"
            @click="navigateToNewTask"
          />
        </div>

        <table v-else class="compact-task-table w-full border-collapse text-left text-[0.82rem]">
          <thead>
            <tr>
              <th class="bg-[var(--vscode-bg-header,#2d2d2d)] text-[var(--vscode-text-secondary,#999999)] font-semibold p-2.5 px-3.5 border-b border-[var(--vscode-border,#333333)]" style="width: 24%">專案名稱 / 任務 ID</th>
              <th class="bg-[var(--vscode-bg-header,#2d2d2d)] text-[var(--vscode-text-secondary,#999999)] font-semibold p-2.5 px-3.5 border-b border-[var(--vscode-border,#333333)]" style="width: 13%">任務類型</th>
              <th class="bg-[var(--vscode-bg-header,#2d2d2d)] text-[var(--vscode-text-secondary,#999999)] font-semibold p-2.5 px-3.5 border-b border-[var(--vscode-border,#333333)]" style="width: 14%">狀態</th>
              <th class="bg-[var(--vscode-bg-header,#2d2d2d)] text-[var(--vscode-text-secondary,#999999)] font-semibold p-2.5 px-3.5 border-b border-[var(--vscode-border,#333333)]" style="width: 22%">拓撲特徵摘要</th>
              <th class="bg-[var(--vscode-bg-header,#2d2d2d)] text-[var(--vscode-text-secondary,#999999)] font-semibold p-2.5 px-3.5 border-b border-[var(--vscode-border,#333333)]" style="width: 15%">建立時間</th>
              <th class="bg-[var(--vscode-bg-header,#2d2d2d)] text-[var(--vscode-text-secondary,#999999)] font-semibold p-2.5 px-3.5 border-b border-[var(--vscode-border,#333333)]" style="width: 12%">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="task in currentDisplayTasks"
              :key="task.id"
              class="task-row cursor-pointer transition-colors hover:bg-[var(--vscode-bg-hover,#2a2d2e)]"
              @click="navigateToTask(task.id)"
            >
              <td class="p-3 px-3.5 border-b border-[var(--vscode-border,#333333)] align-middle">
                <div class="project-name-cell flex flex-col gap-1">
                  <span class="project-title font-semibold text-[var(--vscode-text-heading,#ffffff)]">{{ task.project_name }}</span>
                  <div class="task-id-badge text-[0.7rem] text-[var(--vscode-text-muted,#858585)] inline-flex items-center gap-1.5" @click.stop="copyTaskId(task.id)">
                    <code>{{ task.id.substring(0, 16) }}...</code>
                    <i class="pi pi-copy copy-icon text-[0.7rem] cursor-pointer opacity-70 hover:opacity-100 hover:text-sky-400" title="複製完整 UUID"></i>
                  </div>
                </div>
              </td>
              <td class="p-3 px-3.5 border-b border-[var(--vscode-border,#333333)] align-middle">
                <span class="badge-type text-[0.7rem] font-semibold px-2 py-0.5 rounded" :class="getTypeBadgeClass(task.task_type)">
                  {{ formatTaskType(task.task_type) }}
                </span>
              </td>
              <td class="p-3 px-3.5 border-b border-[var(--vscode-border,#333333)] align-middle">
                <Tag :value="formatStatus(task.status)" :severity="getStatusSeverity(task.status)" />
              </td>
              <td class="p-3 px-3.5 border-b border-[var(--vscode-border,#333333)] align-middle">
                <div class="summary-pills flex gap-1.5 flex-wrap">
                  <span v-if="task.pre_analysis_summary?.component_count" class="pill text-[0.7rem] bg-[var(--vscode-bg-header,#2d2d2d)] text-[var(--vscode-text-main,#cccccc)] px-1.5 py-0.5 rounded font-medium border border-[var(--vscode-border,#333333)]">
                    {{ task.pre_analysis_summary.component_count }} 元件
                  </span>
                  <span v-if="task.pre_analysis_summary?.net_count" class="pill text-[0.7rem] bg-[var(--vscode-bg-header,#2d2d2d)] text-[var(--vscode-text-main,#cccccc)] px-1.5 py-0.5 rounded font-medium border border-[var(--vscode-border,#333333)]">
                    {{ task.pre_analysis_summary.net_count }} 網路
                  </span>
                  <span
                    v-if="task.pre_analysis_summary?.buses?.length"
                    class="pill pill-cyan text-[0.7rem] px-1.5 py-0.5 rounded font-medium border bg-emerald-500/15 text-emerald-400 border-emerald-500/30"
                  >
                    {{ task.pre_analysis_summary.buses.slice(0, 2).join(', ') }}
                  </span>
                  <span v-if="task.selected_rules?.length" class="pill pill-indigo text-[0.7rem] px-1.5 py-0.5 rounded font-medium border bg-sky-500/15 text-sky-400 border-sky-500/30">
                    {{ task.selected_rules.length }} 規則
                  </span>
                  <span v-if="!task.pre_analysis_summary?.component_count" class="text-xs text-[var(--vscode-text-muted,#858585)]">
                    尚未解析
                  </span>
                </div>
              </td>
              <td class="p-3 px-3.5 border-b border-[var(--vscode-border,#333333)] align-middle">
                <div class="time-cell text-[var(--vscode-text-muted,#858585)] text-[0.78rem]">
                  <span>{{ formatDateTime(task.created_at) }}</span>
                </div>
              </td>
              <td class="p-3 px-3.5 border-b border-[var(--vscode-border,#333333)] align-middle">
                <div class="actions-cell flex gap-1" @click.stop>
                  <Button
                    icon="pi pi-arrow-right"
                    severity="info"
                    size="small"
                    text
                    rounded
                    title="進入任務檢測視圖"
                    @click="navigateToTask(task.id)"
                  />
                  <Button
                    v-if="task.status === 'PROCESSING'"
                    icon="pi pi-stop-circle"
                    severity="warn"
                    size="small"
                    text
                    rounded
                    title="中止此任務"
                    @click="handleStopTask(task.id)"
                  />
                  <Button
                    icon="pi pi-trash"
                    severity="danger"
                    size="small"
                    text
                    rounded
                    title="刪除任務與關聯檔案"
                    @click="handleDeleteTask(task.id)"
                  />
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
/**
 * @file DashboardView.vue
 * @description DesignShield 首頁總覽儀表板，提供任務分類導航、系統健康狀態與儲存佔用統計
 */

import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import type { TaskListItem } from '@/types/task'
import type { StorageStats, ServerHealthDetails } from '@/types/settings'
import {
  fetchTasks,
  fetchStorageStats,
  checkServerHealth,
  fetchServerHealthDetails,
  fetchPatternTree,
  stopTask,
  deleteTask,
} from '@/services/api'

const router = useRouter()

// 載入狀態與數據
const isLoading = ref<boolean>(false)
const isHealthy = ref<boolean>(true)
const allTasks = ref<TaskListItem[]>([])
const currentTab = ref<'running' | 'scheduled' | 'completed' | 'all'>('running')
const selectedTypeFilter = ref<string>('ALL')

// 各伺服器元件健康度詳細資訊 (FastAPI/DBOS, Database, LLM 燈號)
const healthDetails = ref<ServerHealthDetails>({
  status: 'healthy',
  service: 'DesignShield',
  version: '0.1.0',
  components: {
    api: { status: 'healthy', label: 'FASTAPI / DBOS', message: '在線' },
    database: { status: 'healthy', label: 'Database', message: '正常' },
    llm: { status: 'healthy', label: '本地 LLM', provider: 'local', message: '已就緒' },
  },
})

// 規則庫與儲存指標
const totalRulesCount = ref<number>(0)
const activeRulesCount = ref<number>(0)
const heuristicRulesCount = ref<number>(0)
const llmRulesCount = ref<number>(0)

const storageStats = ref<StorageStats>({
  storage_root: './storage',
  uploads: { file_count: 0, total_bytes: 0 },
  staging: { file_count: 0, total_bytes: 0 },
  reports: { file_count: 0, total_bytes: 0 },
  total_files: 0,
  total_bytes: 0,
  total_mb: 0,
  disk_total_bytes: 0,
  disk_used_bytes: 0,
  disk_free_bytes: 0,
  disk_total_gb: 0,
  disk_used_gb: 0,
  disk_free_gb: 0,
  disk_used_percent: 0,
})

// 燈號顏色類別映射
const getLightDotClass = (status?: string): string => {
  switch (status) {
    case 'healthy':
      return 'dot-green bg-emerald-400 shadow-[0_0_4px_#4ec9b0]'
    case 'warning':
    case 'degraded':
      return 'dot-amber bg-amber-400 shadow-[0_0_4px_#e5c07b]'
    case 'error':
    case 'offline':
    case 'unhealthy':
      return 'dot-red bg-red-500 shadow-[0_0_4px_#f14c4c]'
    default:
      return 'dot-green bg-emerald-400 shadow-[0_0_4px_#4ec9b0]'
  }
}

interface HealthHintItem {
  text: string
  className?: string
}

/**
 * 格式化 LiteLLM 服務提供商名稱為友善顯示字串
 */
const formatProviderName = (provider?: string, label?: string): string => {
  const p = (provider || '').toLowerCase().trim()
  if (p === 'gemini' || p === 'google') return 'Google Gemini'
  if (p === 'openai') return 'OpenAI'
  if (p === 'anthropic') return 'Anthropic'
  if (p === 'openrouter') return 'OpenRouter'
  if (p === 'groq') return 'Groq'
  if (p === 'deepseek') return 'DeepSeek'
  if (p === 'local') return '本地推理 (Local)'
  if (p) {
    return p.charAt(0).toUpperCase() + p.slice(1)
  }

  // 若尚未取得 provider 欄位，從 label 或常用名稱推斷
  if (label) {
    if (/gemini/i.test(label)) return 'Google Gemini'
    if (/openai/i.test(label)) return 'OpenAI'
    if (/anthropic/i.test(label)) return 'Anthropic'
    if (/openrouter/i.test(label)) return 'OpenRouter'
    if (/groq/i.test(label)) return 'Groq'
    if (/deepseek/i.test(label)) return 'DeepSeek'
    if (/本地/i.test(label)) return '本地推理 (Local)'
    return label
  }

  return '本地推理 (Local)'
}

/**
 * 伺服器健康狀態說明項目：
 * 1. 正常項目的信息不顯示，如有異常再顯示異常狀況
 * 2. LLM 固定顯示目前採用的 provider；若有異常則附帶異常資訊
 */
const healthHintItems = computed<HealthHintItem[]>(() => {
  const items: HealthHintItem[] = []

  // 若整體伺服器未連線
  if (!isHealthy.value) {
    items.push({
      text: '伺服器連線異常，請確認後端服務運作狀態',
      className: 'hint-error text-red-400 font-medium',
    })
    return items
  }

  const apiComp = healthDetails.value?.components?.api
  const dbComp = healthDetails.value?.components?.database
  const llmComp = healthDetails.value?.components?.llm

  // 1. FastAPI/DBOS：正常項目的信息不用顯示，如有異常再顯示異常狀況
  if (apiComp && apiComp.status !== 'healthy') {
    const msg =
      apiComp.message && !apiComp.message.includes('在線') && !apiComp.message.includes('就緒')
        ? apiComp.message
        : '連線異常'
    items.push({
      text: `FastAPI/DBOS: ${msg}`,
      className: 'hint-error text-red-400 font-medium',
    })
  }

  // 2. Database：正常項目的信息不用顯示，如有異常再顯示異常狀況
  if (dbComp && dbComp.status !== 'healthy') {
    const msg = dbComp.message && !dbComp.message.includes('正常') ? dbComp.message : '連線中斷'
    items.push({
      text: `資料庫: ${msg}`,
      className: 'hint-error text-red-400 font-medium',
    })
  }

  // 3. LLM：固定顯示目前採用的 provider；若有異常再顯示異常狀況
  const providerDisplay = formatProviderName(llmComp?.provider, llmComp?.label)
  if (llmComp && llmComp.status !== 'healthy') {
    const abnormalReason =
      llmComp.message &&
      !llmComp.message.includes('正常') &&
      !llmComp.message.includes('就緒') &&
      !llmComp.message.includes('已配置')
        ? llmComp.message
        : '異常'
    items.push({
      text: `LLM Provider: ${providerDisplay} (${abnormalReason})`,
      className: llmComp.status === 'warning' ? 'hint-warning text-amber-400 font-medium' : 'hint-error text-red-400 font-medium',
    })
  } else {
    items.push({
      text: `LLM Provider: ${providerDisplay}`,
      className: 'hint-normal text-[var(--vscode-text-muted,#858585)]',
    })
  }

  return items
})

// LLM 燈號懸浮提示 (Tooltip)
const llmChipTooltip = computed(() => {
  const llmComp = healthDetails.value?.components?.llm
  const providerDisplay = formatProviderName(llmComp?.provider, llmComp?.label)
  const modelText = llmComp?.model ? ` | 模型: ${llmComp.model}` : ''
  const msgText = llmComp?.message ? ` | 狀態: ${llmComp.message}` : ''
  return `LLM 提供者: ${providerDisplay}${modelText}${msgText}`
})

// 格式化主機剩餘可用磁碟空間
const formattedDiskFree = computed(() => {
  if (storageStats.value.disk_free_gb && storageStats.value.disk_free_gb > 0) {
    return `${storageStats.value.disk_free_gb} GB`
  }
  if (storageStats.value.disk_free_bytes && storageStats.value.disk_free_bytes > 0) {
    const mb = Math.round(storageStats.value.disk_free_bytes / (1024 * 1024))
    return `${mb} MB`
  }
  return '充足'
})

// 直條圖進度條已用百分比寬度
const diskUsedBarWidth = computed(() => {
  if (storageStats.value.disk_used_percent !== undefined && storageStats.value.disk_used_percent > 0) {
    return Math.max(3, Math.min(97, storageStats.value.disk_used_percent))
  }
  const mb = storageStats.value.total_mb || 0
  if (mb > 0) {
    return Math.min(60, Math.max(5, Math.round(mb * 2)))
  }
  return 10
})

// 直條圖詳細提示資訊
const storageBarTooltip = computed(() => {
  const free = formattedDiskFree.value
  const percent = storageStats.value.disk_used_percent || 0
  const totalGb = storageStats.value.disk_total_gb ? `${storageStats.value.disk_total_gb} GB` : '未知'
  return `主機磁碟總量: ${totalGb} | 佔用率: ${percent}% | 剩餘可用: ${free}`
})

const formatStorageMb = (bytes: number): string => {
  if (!bytes) return '0 B'
  const mb = bytes / (1024 * 1024)
  if (mb >= 1) {
    return `${mb.toFixed(1)} MB`
  }
  const kb = bytes / 1024
  return `${kb.toFixed(0)} KB`
}

/**
 * 載入 Dashboard 儀表板所有數據
 */
const loadDashboardData = async () => {
  isLoading.value = true
  try {
    const [tasksRes, healthRes, storageRes, patternsRes, healthDetailsRes] = await Promise.allSettled([
      fetchTasks({ limit: 100 }),
      checkServerHealth(),
      fetchStorageStats(),
      fetchPatternTree(),
      fetchServerHealthDetails ? fetchServerHealthDetails() : Promise.resolve(null),
    ])

    if (tasksRes.status === 'fulfilled') {
      allTasks.value = tasksRes.value.tasks || []
      // 若目前進行中無任務且有等待或完成任務，預設切換至有任務的標籤
      if (
        runningTasksCount.value === 0 &&
        currentTab.value === 'running' &&
        allTasks.value.length > 0
      ) {
        currentTab.value = scheduledTasksCount.value > 0 ? 'scheduled' : 'completed'
      }
    }

    if (healthRes.status === 'fulfilled') {
      isHealthy.value = healthRes.value
    }

    if (healthDetailsRes.status === 'fulfilled' && healthDetailsRes.value) {
      healthDetails.value = healthDetailsRes.value
      if (healthDetailsRes.value.status === 'unhealthy') {
        isHealthy.value = false
      }
    }

    if (storageRes.status === 'fulfilled') {
      storageStats.value = storageRes.value
    }

    if (patternsRes.status === 'fulfilled' && patternsRes.value) {
      const l3 = patternsRes.value.level3 || []
      totalRulesCount.value = l3.length
      activeRulesCount.value = l3.filter((r) => r.is_active !== false).length
      heuristicRulesCount.value = l3.filter((r) => {
        const firstType = r.check_logic?.[0]?.type
        return firstType === 'topology_check' || firstType === 'python_script'
      }).length
      llmRulesCount.value = l3.filter((r) => {
        return r.check_logic?.[0]?.type === 'llm_agent'
      }).length
    }
  } catch (err) {
    console.error('載入儀表板資料失敗:', err)
  } finally {
    isLoading.value = false
  }
}

onMounted(() => {
  loadDashboardData()
})

// 計算不同狀態數量
const runningTasksCount = computed(() => {
  return allTasks.value.filter((t) => t.status === 'PROCESSING').length
})

const scheduledTasksCount = computed(() => {
  return allTasks.value.filter((t) => ['PENDING', 'READY_FOR_RUN'].includes(t.status)).length
})

const completedTasksCount = computed(() => {
  return allTasks.value.filter((t) => ['COMPLETED', 'FAILED', 'CANCELLED'].includes(t.status)).length
})

const filteredCompletedTasks = computed(() => {
  return allTasks.value
    .filter((t) => ['COMPLETED', 'FAILED', 'CANCELLED'].includes(t.status))
    .slice(0, 10) // 顯示最近 10 筆已完成/已結束任務
})

/**
 * 依據 Tab 與類型篩選後的任務清單
 */
const currentDisplayTasks = computed(() => {
  let list: TaskListItem[] = []

  if (currentTab.value === 'running') {
    list = allTasks.value.filter((t) => t.status === 'PROCESSING')
  } else if (currentTab.value === 'scheduled') {
    list = allTasks.value.filter((t) => ['PENDING', 'READY_FOR_RUN'].includes(t.status))
  } else if (currentTab.value === 'completed') {
    list = filteredCompletedTasks.value
  } else {
    list = allTasks.value
  }

  if (selectedTypeFilter.value !== 'ALL') {
    list = list.filter((t) => (t.task_type || 'DRC') === selectedTypeFilter.value)
  }

  return list
})

// 導航控制
const navigateToNewTask = () => {
  router.push('/drc')
}

const navigateToTask = (taskId: string) => {
  router.push({ path: '/drc', query: { taskId } })
}

const copyTaskId = async (id: string) => {
  try {
    await navigator.clipboard.writeText(id)
  } catch {
    // 忽略剪貼簿錯誤
  }
}

const handleStopTask = async (taskId: string) => {
  try {
    await stopTask(taskId)
    await loadDashboardData()
  } catch (err) {
    console.error('停止任務失敗:', err)
  }
}

const handleDeleteTask = async (taskId: string) => {
  if (!confirm('確定要刪除此任務與其所有暫存檔案嗎？此操作不可逆。')) {
    return
  }
  try {
    await deleteTask(taskId)
    allTasks.value = allTasks.value.filter((t) => t.id !== taskId)
  } catch (err) {
    console.error('刪除任務失敗:', err)
  }
}

// 格式化輔助函式
const formatTaskType = (type?: string): string => {
  switch (type) {
    case 'RULE_EXTRACTION':
      return '規則提取'
    case 'DATASHEET_ANALYSIS':
      return 'Datasheet'
    default:
      return '線路 DRC'
  }
}

const getTypeBadgeClass = (type?: string): string => {
  switch (type) {
    case 'RULE_EXTRACTION':
      return 'type-extraction bg-amber-500/20 text-amber-400'
    case 'DATASHEET_ANALYSIS':
      return 'type-datasheet bg-purple-500/20 text-purple-400'
    default:
      return 'type-drc bg-sky-500/20 text-sky-400'
  }
}

const formatStatus = (status: string): string => {
  switch (status) {
    case 'PROCESSING':
      return '執行中'
    case 'READY_FOR_RUN':
      return '待選規則'
    case 'PENDING':
      return '排程中'
    case 'COMPLETED':
      return '已完成'
    case 'FAILED':
      return '失敗'
    case 'CANCELLED':
      return '已中止'
    default:
      return status
  }
}

const getStatusSeverity = (status: string) => {
  switch (status) {
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

const formatDateTime = (isoStr?: string): string => {
  if (!isoStr) return '-'
  try {
    const d = new Date(isoStr)
    return d.toLocaleString('zh-TW', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return isoStr
  }
}
</script>
