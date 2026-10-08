<template>
  <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 stats-grid">
    <div
      class="stat-card flex items-center gap-4 p-4 sm:p-5 rounded-lg border border-slate-700 bg-slate-800/80 hover:border-slate-500 cursor-pointer transition-all duration-200 hover:-translate-y-0.5"
      :class="{ 'border-sky-400 ring-1 ring-sky-400 bg-sky-950/20 active': activeTab === 'level3' }"
      @click="$emit('select-tab', 'level3')"
    >
      <div class="stat-icon-wrapper bg-red-light w-11 h-11 rounded-lg flex items-center justify-center text-xl shrink-0 bg-red-500/15 text-red-400">
        <i class="pi pi-shield text-red"></i>
      </div>
      <div class="stat-info flex flex-col">
        <span class="stat-label text-xs text-slate-400 font-medium">Level 3: DRC 驗證規範</span>
        <span class="stat-value text-xl font-bold text-slate-100">{{ level3Count }} <small class="unit text-xs font-normal text-slate-400">條規則</small></span>
      </div>
    </div>

    <div
      class="stat-card flex items-center gap-4 p-4 sm:p-5 rounded-lg border border-slate-700 bg-slate-800/80 hover:border-slate-500 cursor-pointer transition-all duration-200 hover:-translate-y-0.5"
      :class="{ 'border-sky-400 ring-1 ring-sky-400 bg-sky-950/20 active': activeTab === 'partdb' }"
      @click="$emit('select-tab', 'partdb')"
    >
      <div class="stat-icon-wrapper bg-indigo-light w-11 h-11 rounded-lg flex items-center justify-center text-xl shrink-0 bg-indigo-500/15 text-indigo-400">
        <i class="pi pi-microchip text-indigo"></i>
      </div>
      <div class="stat-info flex flex-col">
        <span class="stat-label text-xs text-slate-400 font-medium">PartDB: 零件特規庫</span>
        <span class="stat-value text-xl font-bold text-slate-100">{{ partdbCount }} <small class="unit text-xs font-normal text-slate-400">顆晶片</small></span>
      </div>
    </div>

    <div
      class="stat-card flex items-center gap-4 p-4 sm:p-5 rounded-lg border border-slate-700 bg-slate-800/80 hover:border-slate-500 cursor-pointer transition-all duration-200 hover:-translate-y-0.5"
      :class="{ 'border-sky-400 ring-1 ring-sky-400 bg-sky-950/20 active': activeTab === 'level2' }"
      @click="$emit('select-tab', 'level2')"
    >
      <div class="stat-icon-wrapper bg-blue-light w-11 h-11 rounded-lg flex items-center justify-center text-xl shrink-0 bg-blue-500/15 text-blue-400">
        <i class="pi pi-sitemap text-blue"></i>
      </div>
      <div class="stat-info flex flex-col">
        <span class="stat-label text-xs text-slate-400 font-medium">Level 2: 網路拓撲與匯流排</span>
        <span class="stat-value text-xl font-bold text-slate-100">{{ level2Count }} <small class="unit text-xs font-normal text-slate-400">項規範</small></span>
      </div>
    </div>

    <div
      class="stat-card flex items-center gap-4 p-4 sm:p-5 rounded-lg border border-slate-700 bg-slate-800/80 hover:border-slate-500 cursor-pointer transition-all duration-200 hover:-translate-y-0.5"
      :class="{ 'border-sky-400 ring-1 ring-sky-400 bg-sky-950/20 active': activeTab === 'level1' }"
      @click="$emit('select-tab', 'level1')"
    >
      <div class="stat-icon-wrapper bg-green-light w-11 h-11 rounded-lg flex items-center justify-center text-xl shrink-0 bg-green-500/15 text-green-400">
        <i class="pi pi-th-large text-green"></i>
      </div>
      <div class="stat-info flex flex-col">
        <span class="stat-label text-xs text-slate-400 font-medium">Level 1: 元件辨識規範</span>
        <span class="stat-value text-xl font-bold text-slate-100">{{ level1Count }} <small class="unit text-xs font-normal text-slate-400">項規範</small></span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  activeTab: 'level3' | 'partdb' | 'level2' | 'level1'
  level3Count: number
  partdbCount: number
  level2Count: number
  level1Count: number
}>()

defineEmits<{
  (e: 'select-tab', tab: 'level3' | 'partdb' | 'level2' | 'level1'): void
}>()
</script>
