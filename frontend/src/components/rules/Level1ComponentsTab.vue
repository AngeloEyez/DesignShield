<template>
  <div class="tab-content">
    <div class="level1-table-wrapper">
      <table class="level1-table">
        <thead>
          <tr>
            <th style="width: 110px;">優先級</th>
            <th style="width: 240px;">規則名稱 (Rule Name)</th>
            <th style="width: 140px;">主分類 (Category)</th>
            <th style="width: 160px;">次分類 (Sub-Category)</th>
            <th style="width: 160px;">預設功能角色</th>
            <th style="width: 100px;">信心度</th>
            <th style="width: 90px; text-align: center;">YAML</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="rule in sortedPatterns" :key="rule.name">
            <td>
              <span class="priority-num">{{ rule.priority }}</span>
            </td>
            <td>
              <span class="rule-name-text">{{ rule.name }}</span>
              <p v-if="rule.description" class="rule-desc-text">{{ rule.description }}</p>
            </td>
            <td>
              <span class="cat-pill">{{ rule.assigns?.category }}</span>
            </td>
            <td>
              <span class="subcat-text">{{ rule.assigns?.sub_category }}</span>
            </td>
            <td>
              <span class="role-badge">{{ rule.assigns?.functional_role }}</span>
            </td>
            <td>
              <span class="confidence-text">{{ (rule.assigns?.confidence * 100).toFixed(0) }}%</span>
            </td>
            <td style="text-align: center;">
              <button
                type="button"
                class="icon-code-btn"
                title="檢視 YAML"
                @click="$emit('view-yaml', rule._filename, rule._raw_yaml)"
              >
                <i class="pi pi-file-code"></i>
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Level1PatternItem } from '@/types/pattern'

const props = defineProps<{
  patterns: Level1PatternItem[]
}>()

defineEmits<{
  (e: 'view-yaml', filename: string, rawYaml: string): void
}>()

const sortedPatterns = computed(() => {
  return [...props.patterns].sort((a, b) => b.priority - a.priority)
})
</script>

<style scoped>
.tab-content {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.level1-table-wrapper {
  background-color: var(--surface-card, #1e293b);
  border: 1px solid #334155;
  border-radius: 8px;
  overflow-x: auto;
}

.level1-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.875rem;
}

.level1-table th, .level1-table td {
  padding: 0.85rem 1rem;
  text-align: left;
  border-bottom: 1px solid #334155;
}

.level1-table th {
  background-color: #0f172a;
  color: #94a3b8;
  font-weight: 600;
  font-size: 0.8rem;
}

.priority-num {
  font-weight: 700;
  color: #38bdf8;
}

.rule-name-text {
  font-weight: 600;
  color: #f8fafc;
}

.rule-desc-text {
  margin: 0.2rem 0 0 0;
  font-size: 0.75rem;
  color: #94a3b8;
}

.cat-pill {
  background-color: rgba(34, 197, 94, 0.2);
  color: #4ade80;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
}

.subcat-text {
  color: #cbd5e1;
}

.role-badge {
  background-color: rgba(56, 189, 248, 0.15);
  color: #38bdf8;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
}

.confidence-text {
  color: #e2e8f0;
  font-weight: 600;
}

.icon-code-btn {
  background: none;
  border: none;
  color: #38bdf8;
  font-size: 1.1rem;
  cursor: pointer;
  padding: 0.2rem;
  border-radius: 4px;
  transition: all 0.2s ease;
}

.icon-code-btn:hover {
  background-color: rgba(56, 189, 248, 0.15);
  color: #7dd3fc;
}
</style>
