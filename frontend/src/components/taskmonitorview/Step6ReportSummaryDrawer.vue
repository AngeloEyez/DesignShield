<template>
  <div class="drawer-step-content flex flex-col gap-3">
    <!-- 報告已產出時展示單行統計橫條 -->
    <template v-if="taskReport">
      <div class="drawer-stat-banner grid grid-cols-3 divide-x divide-surface-border bg-surface-panel border border-surface-border rounded">
        <div class="banner-stat px-3 py-1.5 flex items-center justify-between">
          <span class="stat-name text-xs text-vscode-textSecondary">規則通過率</span>
          <span class="stat-num text-sm font-semibold text-vscode-green font-mono">{{ taskReport.summary?.pass_rate_percentage ?? 0 }}%</span>
        </div>
        <div class="banner-stat px-3 py-1.5 flex items-center justify-between">
          <span class="stat-name text-xs text-vscode-textSecondary">檢查項目總數</span>
          <span class="stat-num text-sm font-semibold text-vscode-textHeading font-mono">{{ taskReport.summary?.total_rules_checked ?? 0 }}</span>
        </div>
        <div class="banner-stat px-3 py-1.5 flex items-center justify-between">
          <span class="stat-name text-xs text-vscode-textSecondary">違規警告數</span>
          <span class="stat-num text-sm font-semibold text-vscode-danger font-mono">{{ taskReport.summary?.fail_count ?? 0 }}</span>
        </div>
      </div>
      <p class="text-hint text-xs text-vscode-textMuted m-0 flex items-center">
        <i class="pi pi-check-circle text-vscode-green mr-1.5"></i>
        報告已落地儲存，可於下方檢視完整 DRC 報告 Dashboard。
      </p>
    </template>

    <!-- 尚未完成時的 Empty State -->
    <div v-else class="report-empty-state border border-surface-border rounded p-6 flex flex-col items-center justify-center gap-1.5 text-center bg-surface-panel">
      <i class="pi pi-file-excel text-xl text-vscode-textMuted"></i>
      <span class="text-xs text-vscode-textSecondary">DRC 檢驗報告尚未生成</span>
      <span class="text-[11px] text-vscode-textMuted">待前置規則比對與語意推理步驟全部完成後，系統將自動彙整報告並落地儲存</span>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * @file Step6ReportSummaryDrawer.vue
 * @description TaskMonitorView 抽屜 Step 6：報告落地彙整與指標統計橫條
 */

interface Props {
  taskReport: any
}

defineProps<Props>()
</script>
