<template>
  <div class="tab-content flex flex-col gap-4">
    <div class="level2-grid grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <div
        v-for="pat in patterns"
        :key="pat.name"
        class="l2-card bg-[#252526] border border-[#333333] rounded-md p-4 flex flex-col gap-3 shadow-none transition-opacity"
        :class="{ 'opacity-60': pat.enabled === false }"
      >
        <div class="l2-card-header flex justify-between items-start">
          <div>
            <div class="flex items-center gap-2">
              <span class="l2-category-tag bg-blue-500/20 text-blue-400 font-bold text-xs px-2 py-0.5 rounded">{{ pat.category }}</span>
              <Tag
                :value="pat.enabled === false ? '已停用' : '啟用'"
                :severity="pat.enabled === false ? 'secondary' : 'success'"
                class="status-tag text-[10px] px-1.5 py-0.2 rounded font-normal"
              />
            </div>
            <h3 class="l2-title mt-2 font-semibold text-white text-base">{{ pat.name }}</h3>
          </div>
          <div class="l2-header-right flex items-center">
            <span class="priority-badge bg-[#1e1e1e] border border-[#333333] text-[#858585] text-xs px-2 py-0.5 rounded">優先級: {{ pat.priority }}</span>
            <button
              type="button"
              class="yaml-view-btn ml-2 bg-[#1e1e1e] hover:bg-[#2a2d2e] hover:text-white border border-[#333333] text-sky-400 text-xs px-2 py-1 rounded flex items-center transition-colors cursor-pointer"
              @click="$emit('view-yaml', pat._filename, pat._raw_yaml)"
            >
              <i class="pi pi-file-code mr-1"></i>YAML
            </button>
          </div>
        </div>

        <div class="l2-signals-list flex flex-col gap-1.5">
          <span class="section-sublabel text-xs font-medium text-[#858585]">訊號群組特徵:</span>
          <div class="signal-chips flex flex-wrap gap-1.5">
            <span v-for="sig in pat.signals" :key="sig.role" class="signal-chip bg-[#1e1e1e] border border-[#333333] text-[#cccccc] text-xs px-2 py-0.5 rounded">
              {{ sig.role }} <small v-if="sig.required" class="text-sky-300 font-normal">(必備)</small>
            </span>
          </div>
        </div>

        <div v-if="(pat.component_role_overrides && pat.component_role_overrides.length > 0) || (pat.role_overrides && pat.role_overrides.length > 0)" class="role-overrides-box bg-[#1e1e1e] border border-[#333333] rounded p-3 flex flex-col gap-1.5">
          <span class="section-sublabel text-xs font-medium text-[#858585]">元件角色拓撲覆寫 (Component Role Overrides):</span>
          <ul class="overrides-list m-0 pl-4 text-xs text-[#cccccc] space-y-1 list-disc">
            <li v-for="(ov, idx) in (pat.component_role_overrides || pat.role_overrides)" :key="idx">
              <code class="text-sky-300 font-mono">{{ ov.original_sub_category }}</code> 連接至 <code class="text-sky-300 font-mono">{{ ov.connected_to }}</code> ➔ 覆寫為 <strong class="text-emerald-400">{{ ov.new_role }}</strong>
            </li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import Tag from 'primevue/tag'
import type { Level2PatternItem } from '@/types/pattern'

defineProps<{
  patterns: Level2PatternItem[]
}>()

defineEmits<{
  (e: 'view-yaml', filename: string, rawYaml: string): void
}>()
</script>
