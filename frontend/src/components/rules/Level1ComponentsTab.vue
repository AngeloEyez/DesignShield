<template>
  <div class="tab-content flex flex-col gap-3">
    <div class="level1-table-wrapper bg-surface-panel border border-surface-border rounded overflow-x-auto">
      <DataTable
        :value="sortedPatterns"
        size="small"
        class="level1-table w-full text-xs [&_td]:!py-1.5 [&_td]:!px-3 [&_th]:!py-2 [&_th]:!px-3"
      >
        <Column header="狀態" style="width: 80px">
          <template #body="{ data: rule }">
            <Tag
              :value="rule.enabled === false ? '已停用' : '啟用'"
              :severity="rule.enabled === false ? 'secondary' : 'success'"
              class="status-tag text-[10px] px-1.5 py-0.2 rounded font-normal"
            />
          </template>
        </Column>
        <Column field="priority" header="優先級" style="width: 90px">
          <template #body="{ data: rule }">
            <span class="priority-num font-semibold text-primary-400 font-mono">{{ rule.priority }}</span>
          </template>
        </Column>
        <Column field="name" header="規則名稱 (Rule Name)" style="width: 240px">
          <template #body="{ data: rule }">
            <span class="rule-name-text font-semibold text-surface-0 font-mono">{{ rule.name }}</span>
            <p v-if="rule.description" class="rule-desc-text m-0 mt-0.5 text-xs text-surface-400">{{ rule.description }}</p>
          </template>
        </Column>
        <Column header="主分類 (Category)" style="width: 140px">
          <template #body="{ data: rule }">
            <span class="cat-pill bg-surface-card text-surface-200 border border-surface-border px-1.5 py-0.2 rounded text-xs font-mono">{{ rule.assigns?.category }}</span>
          </template>
        </Column>
        <Column header="次分類 (Sub-Category)" style="width: 150px">
          <template #body="{ data: rule }">
            <span class="subcat-text text-surface-200 text-xs">{{ rule.assigns?.sub_category }}</span>
          </template>
        </Column>
        <Column header="元件拓撲角色 (Component Role)" style="width: 160px">
          <template #body="{ data: rule }">
            <span class="role-badge bg-primary-500/15 text-primary-400 px-1.5 py-0.2 rounded text-xs font-mono">{{ rule.assigns?.component_role || rule.assigns?.functional_role }}</span>
          </template>
        </Column>
        <Column header="信心度" style="width: 90px">
          <template #body="{ data: rule }">
            <span class="confidence-text text-surface-0 font-semibold font-mono">{{ (rule.assigns?.confidence * 100).toFixed(0) }}%</span>
          </template>
        </Column>
        <Column header="YAML" headerClass="text-center" bodyClass="text-center" style="width: 70px">
          <template #body="{ data: rule }">
            <button
              type="button"
              v-tooltip.left="'檢視 YAML'"
              class="icon-code-btn text-primary-400 hover:text-surface-0 hover:bg-surface-hover p-1 rounded transition-colors cursor-pointer bg-transparent border-0"
              @click="$emit('view-yaml', rule._filename, rule._raw_yaml)"
            >
              <i class="pi pi-file-code text-xs"></i>
            </button>
          </template>
        </Column>
      </DataTable>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * @file Level1ComponentsTab.vue
 * @description Level 1 元件辨識規範表格頁籤 (PrimeVue DataTable 雙主題版)
 */

import { computed } from 'vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'
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
