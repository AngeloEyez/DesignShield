<template>
  <div class="drawer-step-content flex flex-col gap-4">
    <div class="drawer-stat-banner grid grid-cols-3 gap-2.5 bg-surface-card border border-surface-border rounded-md p-4 text-center">
      <div class="banner-stat flex flex-col items-center gap-1">
        <span class="stat-num text-xl font-bold text-green-400">{{ taskReport?.summary?.pass_rate_percentage || 100 }}%</span>
        <span class="stat-name text-xs text-surface-400">規則通過率</span>
      </div>
      <div class="banner-stat flex flex-col items-center gap-1">
        <span class="stat-num text-xl font-bold text-surface-900 dark:text-surface-0">{{ taskReport?.summary?.total_rules_checked || 0 }}</span>
        <span class="stat-name text-xs text-surface-400">檢查項目總數</span>
      </div>
      <div class="banner-stat flex flex-col items-center gap-1">
        <span class="stat-num text-xl font-bold text-red-400">{{ taskReport?.summary?.fail_count || 0 }}</span>
        <span class="stat-name text-xs text-surface-400">違規警告數</span>
      </div>
    </div>
    <p class="text-hint text-xs text-surface-400 m-0 flex items-center">
      <i class="pi pi-check-circle text-green-400 mr-1.5"></i>
      報告已落地儲存，可於下方檢視完整 DRC 報告 Dashboard。
    </p>
  </div>
</template>

<script setup lang="ts">
/**
 * @file Step6ReportSummaryDrawer.vue
 * @description TaskMonitorView 抽屜 Step 6：報告落地彙整與指標統計 Banner
 */

interface Props {
  taskReport: any
}

defineProps<Props>()
</script>
