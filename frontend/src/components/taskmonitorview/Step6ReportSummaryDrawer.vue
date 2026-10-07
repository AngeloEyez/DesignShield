<template>
  <div class="drawer-step-content">
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
    <p class="text-hint">
      <i class="pi pi-check-circle text-green mr-1"></i>
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

<style scoped>
.drawer-step-content {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.drawer-stat-banner {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.65rem;
  background-color: var(--vscode-bg-panel, #252526);
  border: 1px solid var(--vscode-border, #333333);
  border-radius: 6px;
  padding: 1rem;
  text-align: center;
}

.banner-stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.25rem;
}

.stat-num {
  font-size: 1.45rem;
  font-weight: 700;
  color: var(--vscode-text-heading, #ffffff);
}

.stat-name {
  font-size: 0.72rem;
  color: var(--vscode-text-muted, #858585);
}

.text-green {
  color: #89d185;
}

.text-danger {
  color: var(--vscode-danger, #f14c4c);
}

.text-hint {
  font-size: 0.82rem;
  color: var(--vscode-text-muted, #858585);
  margin: 0;
  display: flex;
  align-items: center;
}
</style>
