<template>
  <div class="drawer-step-content flex flex-col gap-4">
    <!-- 報告已產出時展示統計 Banner -->
    <template v-if="taskReport">
      <div class="drawer-stat-banner grid grid-cols-3 gap-2.5 bg-[#252526] border border-[#333333] rounded-md p-4 text-center">
        <div class="banner-stat flex flex-col items-center gap-1">
          <span class="stat-num text-xl font-bold text-emerald-400">{{ taskReport.summary?.pass_rate_percentage ?? 0 }}%</span>
          <span class="stat-name text-xs text-[#858585]">規則通過率</span>
        </div>
        <div class="banner-stat flex flex-col items-center gap-1">
          <span class="stat-num text-xl font-bold text-white">{{ taskReport.summary?.total_rules_checked ?? 0 }}</span>
          <span class="stat-name text-xs text-[#858585]">檢查項目總數</span>
        </div>
        <div class="banner-stat flex flex-col items-center gap-1">
          <span class="stat-num text-xl font-bold text-rose-400">{{ taskReport.summary?.fail_count ?? 0 }}</span>
          <span class="stat-name text-xs text-[#858585]">違規警告數</span>
        </div>
      </div>
      <p class="text-hint text-xs text-[#858585] m-0 flex items-center">
        <i class="pi pi-check-circle text-emerald-400 mr-1.5"></i>
        報告已落地儲存，可於下方檢視完整 DRC 報告 Dashboard。
      </p>
    </template>

    <!-- 尚未完成時的 Empty State -->
    <div v-else class="report-empty-state border border-[#333333] rounded-md p-8 flex flex-col items-center justify-center gap-2 text-center bg-[#252526]">
      <i class="pi pi-file-excel text-3xl text-[#555555]"></i>
      <span class="text-xs text-[#858585]">DRC 檢驗報告尚未生成</span>
      <span class="text-[11px] text-[#666666]">待前置規則比對與語意推理步驟全部完成後，系統將自動彙整報告並落地儲存</span>
    </div>
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
