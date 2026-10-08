<template>
  <div class="tab-content flex flex-col gap-5">
    <div class="level2-grid grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
      <div
        v-for="pat in patterns"
        :key="pat.name"
        class="l2-card bg-slate-800/80 border border-slate-700 rounded-lg p-5 flex flex-col gap-4 shadow-sm"
      >
        <div class="l2-card-header flex justify-between items-start">
          <div>
            <span class="l2-category-tag bg-blue-500/20 text-blue-400 font-bold text-xs px-2 py-0.5 rounded">{{ pat.category }}</span>
            <h3 class="l2-title mt-2 font-semibold text-slate-100 text-base">{{ pat.name }}</h3>
          </div>
          <div class="l2-header-right flex items-center">
            <span class="priority-badge bg-slate-900 border border-slate-700 text-slate-400 text-xs px-2 py-0.5 rounded">優先級: {{ pat.priority }}</span>
            <button
              type="button"
              class="yaml-view-btn ml-2 bg-slate-800 hover:bg-sky-400 hover:text-slate-900 border border-slate-700 text-sky-400 text-xs px-2 py-1 rounded flex items-center transition-colors"
              @click="$emit('view-yaml', pat._filename, pat._raw_yaml)"
            >
              <i class="pi pi-file-code mr-1"></i>YAML
            </button>
          </div>
        </div>

        <div class="l2-signals-list flex flex-col gap-1.5">
          <span class="section-sublabel text-xs font-medium text-slate-400">訊號群組特徵:</span>
          <div class="signal-chips flex flex-wrap gap-1.5">
            <span v-for="sig in pat.signals" :key="sig.role" class="signal-chip bg-slate-900 border border-slate-700 text-slate-300 text-xs px-2 py-0.5 rounded">
              {{ sig.role }} <small v-if="sig.required" class="text-sky-400 font-normal">(必備)</small>
            </span>
          </div>
        </div>

        <div v-if="pat.role_overrides && pat.role_overrides.length > 0" class="role-overrides-box bg-slate-900 border border-slate-800 rounded p-3 flex flex-col gap-1.5">
          <span class="section-sublabel text-xs font-medium text-slate-400">動態角色覆寫 (Topology Overrides):</span>
          <ul class="overrides-list m-0 pl-4 text-xs text-slate-300 space-y-1 list-disc">
            <li v-for="(ov, idx) in pat.role_overrides" :key="idx">
              <code class="text-sky-400 font-mono">{{ ov.original_sub_category }}</code> 連接至 <code class="text-sky-400 font-mono">{{ ov.connected_to }}</code> ➔ 覆寫為 <strong class="text-emerald-400">{{ ov.new_role }}</strong>
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
