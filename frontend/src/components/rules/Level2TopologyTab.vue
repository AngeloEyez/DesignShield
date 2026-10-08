<template>
  <div class="tab-content">
    <div class="level2-grid">
      <div
        v-for="pat in patterns"
        :key="pat.name"
        class="l2-card"
      >
        <div class="l2-card-header">
          <div>
            <span class="l2-category-tag">{{ pat.category }}</span>
            <h3 class="l2-title">{{ pat.name }}</h3>
          </div>
          <div class="l2-header-right">
            <span class="priority-badge">優先級: {{ pat.priority }}</span>
            <button
              type="button"
              class="yaml-view-btn ml-2"
              @click="$emit('view-yaml', pat._filename, pat._raw_yaml)"
            >
              <i class="pi pi-file-code mr-1"></i>YAML
            </button>
          </div>
        </div>

        <div class="l2-signals-list">
          <span class="section-sublabel">訊號群組特徵:</span>
          <div class="signal-chips">
            <span v-for="sig in pat.signals" :key="sig.role" class="signal-chip">
              {{ sig.role }} <small v-if="sig.required">(必備)</small>
            </span>
          </div>
        </div>

        <div v-if="pat.role_overrides && pat.role_overrides.length > 0" class="role-overrides-box">
          <span class="section-sublabel">動態角色覆寫 (Topology Overrides):</span>
          <ul class="overrides-list">
            <li v-for="(ov, idx) in pat.role_overrides" :key="idx">
              <code>{{ ov.original_sub_category }}</code> 連接至 <code>{{ ov.connected_to }}</code> ➔ 覆寫為 <strong>{{ ov.new_role }}</strong>
            </li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Level2PatternItem } from '@/types/pattern'

defineProps<{
  patterns: Level2PatternItem[]
}>()

defineEmits<{
  (e: 'view-yaml', filename: string, rawYaml: string): void
}>()
</script>

<style scoped>
.tab-content {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.level2-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
  gap: 1.25rem;
}

.l2-card {
  background-color: var(--surface-card, #1e293b);
  border: 1px solid #334155;
  border-radius: 8px;
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.l2-card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.l2-category-tag {
  background-color: rgba(59, 130, 246, 0.2);
  color: #60a5fa;
  font-size: 0.75rem;
  font-weight: 700;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
}

.l2-title {
  margin: 0.4rem 0 0 0;
  font-size: 1.05rem;
  font-weight: 600;
  color: #f8fafc;
}

.l2-header-right {
  display: flex;
  align-items: center;
}

.priority-badge {
  background-color: #0f172a;
  border: 1px solid #334155;
  color: #94a3b8;
  font-size: 0.75rem;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
}

.section-sublabel {
  font-size: 0.8rem;
  color: #94a3b8;
  font-weight: 500;
}

.l2-signals-list {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.signal-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}

.signal-chip {
  background-color: #0f172a;
  border: 1px solid #334155;
  color: #e2e8f0;
  font-size: 0.75rem;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
}

.signal-chip small {
  color: #38bdf8;
}

.role-overrides-box {
  background-color: #0f172a;
  border: 1px solid #1e293b;
  border-radius: 6px;
  padding: 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.overrides-list {
  margin: 0;
  padding-left: 1.25rem;
  font-size: 0.8rem;
  color: #cbd5e1;
}

.overrides-list li {
  margin-bottom: 0.25rem;
}

.overrides-list code {
  color: #38bdf8;
  font-family: monospace;
}

.overrides-list strong {
  color: #4ade80;
}

.yaml-view-btn {
  background-color: #1e293b;
  border: 1px solid #334155;
  color: #38bdf8;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  transition: all 0.2s ease;
}

.yaml-view-btn:hover {
  background-color: #38bdf8;
  color: #0f172a;
}
</style>
