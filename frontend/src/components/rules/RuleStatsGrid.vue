<template>
  <div class="stats-grid grid grid-cols-2 lg:grid-cols-4 divide-x divide-surface-border border-b border-surface-border bg-surface-panel">
    <!-- 1. Level 3 指標格 -->
    <div
      v-tooltip.bottom="'點擊篩選 Level 3 DRC 驗證規範'"
      class="stat-card flex items-center justify-between gap-2 px-4 py-2 cursor-pointer transition-colors hover:bg-surface-hover"
      :class="{ 'bg-primary/10 border-b-2 border-primary active': activeTab === 'level3' }"
      @click="$emit('select-tab', 'level3')"
    >
      <div class="flex items-center gap-2 min-w-0">
        <i class="pi pi-shield text-xs text-primary shrink-0"></i>
        <span class="stat-label text-xs text-vscode-textSecondary font-medium truncate">Level 3: DRC 驗證規範</span>
      </div>
      <span class="stat-value text-sm font-semibold text-vscode-textHeading font-mono shrink-0">
        {{ level3Count }} <small class="unit text-[11px] font-sans font-normal text-vscode-textMuted">條規則</small>
      </span>
    </div>

    <!-- 2. Level 2 指標格 -->
    <div
      v-tooltip.bottom="'點擊篩選 Level 2 網路拓撲與匯流排規範'"
      class="stat-card flex items-center justify-between gap-2 px-4 py-2 cursor-pointer transition-colors hover:bg-surface-hover"
      :class="{ 'bg-primary/10 border-b-2 border-primary active': activeTab === 'level2' }"
      @click="$emit('select-tab', 'level2')"
    >
      <div class="flex items-center gap-2 min-w-0">
        <i class="pi pi-sitemap text-xs text-vscode-textMuted shrink-0"></i>
        <span class="stat-label text-xs text-vscode-textSecondary font-medium truncate">Level 2: 網路拓撲與匯流排</span>
      </div>
      <span class="stat-value text-sm font-semibold text-vscode-textHeading font-mono shrink-0">
        {{ level2Count }} <small class="unit text-[11px] font-sans font-normal text-vscode-textMuted">項規範</small>
      </span>
    </div>

    <!-- 3. Level 1 指標格 -->
    <div
      v-tooltip.bottom="'點擊篩選 Level 1 元件辨識規範'"
      class="stat-card flex items-center justify-between gap-2 px-4 py-2 cursor-pointer transition-colors hover:bg-surface-hover"
      :class="{ 'bg-primary/10 border-b-2 border-primary active': activeTab === 'level1' }"
      @click="$emit('select-tab', 'level1')"
    >
      <div class="flex items-center gap-2 min-w-0">
        <i class="pi pi-th-large text-xs text-vscode-textMuted shrink-0"></i>
        <span class="stat-label text-xs text-vscode-textSecondary font-medium truncate">Level 1: 元件辨識規範</span>
      </div>
      <span class="stat-value text-sm font-semibold text-vscode-textHeading font-mono shrink-0">
        {{ level1Count }} <small class="unit text-[11px] font-sans font-normal text-vscode-textMuted">項規範</small>
      </span>
    </div>

    <!-- 4. PartDB 指標格 -->
    <div
      v-tooltip.bottom="'點擊篩選 PartDB 零件特規庫'"
      class="stat-card flex items-center justify-between gap-2 px-4 py-2 cursor-pointer transition-colors hover:bg-surface-hover"
      :class="{ 'bg-primary/10 border-b-2 border-primary active': activeTab === 'partdb' }"
      @click="$emit('select-tab', 'partdb')"
    >
      <div class="flex items-center gap-2 min-w-0">
        <i class="pi pi-microchip text-xs text-vscode-textMuted shrink-0"></i>
        <span class="stat-label text-xs text-vscode-textSecondary font-medium truncate">PartDB: 零件特規庫</span>
      </div>
      <span class="stat-value text-sm font-semibold text-vscode-textHeading font-mono shrink-0">
        {{ partdbCount }} <small class="unit text-[11px] font-sans font-normal text-vscode-textMuted">顆晶片</small>
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * @file RuleStatsGrid.vue
 * @description 規則庫頂部 40px 單行關鍵指標橫條 (Compact Metric Strip)
 */

defineProps<{
  activeTab?: 'level3' | 'level2' | 'level1' | 'partdb' | ''
  level3Count: number
  partdbCount: number
  level2Count: number
  level1Count: number
}>()

defineEmits<{
  (e: 'select-tab', tab: 'level3' | 'level2' | 'level1' | 'partdb' | ''): void
}>()
</script>
