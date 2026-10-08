<template>
  <div class="tab-content flex flex-col gap-5">
    <div class="level1-table-wrapper bg-slate-800/80 border border-slate-700 rounded-lg overflow-x-auto shadow-sm">
      <table class="level1-table w-full border-collapse text-sm">
        <thead>
          <tr class="bg-slate-900/90 text-slate-400 font-semibold text-xs border-b border-slate-700">
            <th class="p-3.5 text-left w-[110px]">優先級</th>
            <th class="p-3.5 text-left w-[240px]">規則名稱 (Rule Name)</th>
            <th class="p-3.5 text-left w-[140px]">主分類 (Category)</th>
            <th class="p-3.5 text-left w-[160px]">次分類 (Sub-Category)</th>
            <th class="p-3.5 text-left w-[160px]">預設功能角色</th>
            <th class="p-3.5 text-left w-[100px]">信心度</th>
            <th class="p-3.5 text-center w-[90px]">YAML</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-700">
          <tr v-for="rule in sortedPatterns" :key="rule.name" class="hover:bg-slate-700/30 transition-colors">
            <td class="p-3.5">
              <span class="priority-num font-bold text-sky-400">{{ rule.priority }}</span>
            </td>
            <td class="p-3.5">
              <span class="rule-name-text font-semibold text-slate-100">{{ rule.name }}</span>
              <p v-if="rule.description" class="rule-desc-text mt-1 text-xs text-slate-400">{{ rule.description }}</p>
            </td>
            <td class="p-3.5">
              <span class="cat-pill bg-emerald-500/20 text-emerald-400 px-2 py-0.5 rounded text-xs">{{ rule.assigns?.category }}</span>
            </td>
            <td class="p-3.5">
              <span class="subcat-text text-slate-300 text-xs">{{ rule.assigns?.sub_category }}</span>
            </td>
            <td class="p-3.5">
              <span class="role-badge bg-sky-500/15 text-sky-400 px-2 py-0.5 rounded text-xs">{{ rule.assigns?.functional_role }}</span>
            </td>
            <td class="p-3.5">
              <span class="confidence-text text-slate-200 font-semibold">{{ (rule.assigns?.confidence * 100).toFixed(0) }}%</span>
            </td>
            <td class="p-3.5 text-center">
              <button
                type="button"
                class="icon-code-btn text-sky-400 hover:text-sky-300 hover:bg-sky-500/15 p-1 rounded transition-colors"
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
