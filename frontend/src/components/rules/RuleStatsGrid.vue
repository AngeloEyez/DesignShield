<template>
  <div class="stats-grid">
    <div
      class="stat-card"
      :class="{ active: activeTab === 'level3' }"
      @click="$emit('select-tab', 'level3')"
    >
      <div class="stat-icon-wrapper bg-red-light">
        <i class="pi pi-shield text-red"></i>
      </div>
      <div class="stat-info">
        <span class="stat-label">Level 3: DRC 驗證規範</span>
        <span class="stat-value">{{ level3Count }} <small class="unit">條規則</small></span>
      </div>
    </div>

    <div
      class="stat-card"
      :class="{ active: activeTab === 'partdb' }"
      @click="$emit('select-tab', 'partdb')"
    >
      <div class="stat-icon-wrapper bg-indigo-light">
        <i class="pi pi-microchip text-indigo"></i>
      </div>
      <div class="stat-info">
        <span class="stat-label">PartDB: 零件特規庫</span>
        <span class="stat-value">{{ partdbCount }} <small class="unit">顆晶片</small></span>
      </div>
    </div>

    <div
      class="stat-card"
      :class="{ active: activeTab === 'level2' }"
      @click="$emit('select-tab', 'level2')"
    >
      <div class="stat-icon-wrapper bg-blue-light">
        <i class="pi pi-sitemap text-blue"></i>
      </div>
      <div class="stat-info">
        <span class="stat-label">Level 2: 網路拓撲與匯流排</span>
        <span class="stat-value">{{ level2Count }} <small class="unit">項規範</small></span>
      </div>
    </div>

    <div
      class="stat-card"
      :class="{ active: activeTab === 'level1' }"
      @click="$emit('select-tab', 'level1')"
    >
      <div class="stat-icon-wrapper bg-green-light">
        <i class="pi pi-th-large text-green"></i>
      </div>
      <div class="stat-info">
        <span class="stat-label">Level 1: 元件辨識規範</span>
        <span class="stat-value">{{ level1Count }} <small class="unit">項規範</small></span>
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

<style scoped>
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1rem;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem 1.25rem;
  background-color: var(--surface-card, #1e293b);
  border: 1px solid #334155;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.stat-card:hover {
  border-color: #64748b;
  transform: translateY(-2px);
}

.stat-card.active {
  border-color: var(--primary-color, #38bdf8);
  box-shadow: 0 0 0 1px var(--primary-color, #38bdf8);
  background-color: rgba(56, 189, 248, 0.05);
}

.stat-icon-wrapper {
  width: 44px;
  height: 44px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.25rem;
  flex-shrink: 0;
}

.bg-red-light { background-color: rgba(239, 68, 68, 0.15); }
.bg-indigo-light { background-color: rgba(99, 102, 241, 0.15); }
.bg-blue-light { background-color: rgba(59, 130, 246, 0.15); }
.bg-green-light { background-color: rgba(34, 197, 94, 0.15); }

.text-red { color: #f87171; }
.text-indigo { color: #818cf8; }
.text-blue { color: #60a5fa; }
.text-green { color: #4ade80; }

.stat-info {
  display: flex;
  flex-direction: column;
}

.stat-label {
  font-size: 0.8rem;
  color: #94a3b8;
  font-weight: 500;
}

.stat-value {
  font-size: 1.35rem;
  font-weight: 700;
  color: #f8fafc;
}

.unit {
  font-size: 0.8rem;
  font-weight: 400;
  color: #94a3b8;
}

@media (max-width: 1024px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 640px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }
}
</style>
