<template>
  <div class="tab-content flex flex-col gap-4">
    <div class="level1-table-wrapper bg-[#252526] border border-[#333333] rounded-md overflow-x-auto shadow-none">
      <table class="level1-table w-full border-collapse text-xs">
        <thead>
          <tr class="bg-[#1e1e1e] text-[#cccccc] font-semibold text-xs border-b border-[#333333]">
            <th class="p-3 text-left w-[80px]">狀態</th>
            <th class="p-3 text-left w-[100px]">優先級</th>
            <th class="p-3 text-left w-[240px]">規則名稱 (Rule Name)</th>
            <th class="p-3 text-left w-[140px]">主分類 (Category)</th>
            <th class="p-3 text-left w-[160px]">次分類 (Sub-Category)</th>
            <th class="p-3 text-left w-[160px]">預設功能角色</th>
            <th class="p-3 text-left w-[100px]">信心度</th>
            <th class="p-3 text-center w-[90px]">YAML</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-[#333333]">
          <tr
            v-for="rule in sortedPatterns"
            :key="rule.name"
            class="hover:bg-[#2a2d2e]/50 transition-colors"
            :class="{ 'opacity-60': rule.enabled === false }"
          >
            <td class="p-3">
              <Tag
                :value="rule.enabled === false ? '已停用' : '啟用'"
                :severity="rule.enabled === false ? 'secondary' : 'success'"
                class="status-tag text-[10px] px-1.5 py-0.5 rounded font-normal"
              />
            </td>
            <td class="p-3">
              <span class="priority-num font-bold text-sky-400">{{ rule.priority }}</span>
            </td>
            <td class="p-3">
              <span class="rule-name-text font-semibold text-white">{{ rule.name }}</span>
              <p v-if="rule.description" class="rule-desc-text mt-1 text-xs text-[#858585]">{{ rule.description }}</p>
            </td>
            <td class="p-3">
              <span class="cat-pill bg-emerald-500/20 text-emerald-400 px-2 py-0.5 rounded text-xs">{{ rule.assigns?.category }}</span>
            </td>
            <td class="p-3">
              <span class="subcat-text text-[#cccccc] text-xs">{{ rule.assigns?.sub_category }}</span>
            </td>
            <td class="p-3">
              <span class="role-badge bg-sky-500/15 text-sky-400 px-2 py-0.5 rounded text-xs">{{ rule.assigns?.functional_role }}</span>
            </td>
            <td class="p-3">
              <span class="confidence-text text-white font-semibold">{{ (rule.assigns?.confidence * 100).toFixed(0) }}%</span>
            </td>
            <td class="p-3 text-center">
              <button
                type="button"
                class="icon-code-btn text-sky-400 hover:text-white hover:bg-[#2a2d2e] p-1 rounded transition-colors cursor-pointer"
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
