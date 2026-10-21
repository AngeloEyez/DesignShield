<template>
  <div class="tab-content flex flex-col gap-3">
    <div class="level2-grid grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
      <div
        v-for="pat in patterns"
        :key="pat.name"
        class="l2-card bg-surface-panel border border-surface-border rounded p-3 flex flex-col gap-2.5 transition-opacity"
        :class="{ 'opacity-60': pat.enabled === false }"
      >
        <div class="l2-card-header flex justify-between items-start gap-2">
          <div>
            <div class="flex items-center gap-1.5">
              <span class="l2-category-tag bg-primary-500/15 text-primary-400 font-medium text-[11px] px-1.5 py-0.2 rounded">{{ pat.category }}</span>
              <Tag
                :value="pat.enabled === false ? '已停用' : '啟用'"
                :severity="pat.enabled === false ? 'secondary' : 'success'"
                class="status-tag text-[10px] px-1.5 py-0.2 rounded font-normal"
              />
            </div>
            <h3 class="l2-title mt-1.5 mb-0 font-semibold text-surface-0 text-sm font-mono">{{ pat.name }}</h3>
          </div>
          <div class="l2-header-right flex items-center gap-1.5">
            <span class="priority-badge bg-surface-card border border-surface-border text-surface-400 text-[11px] px-1.5 py-0.2 rounded font-mono">P:{{ pat.priority }}</span>
            <button
              type="button"
              v-tooltip.left="'檢視 YAML'"
              class="yaml-view-btn bg-surface-card hover:bg-surface-hover border border-surface-border text-primary-400 text-xs p-1 rounded flex items-center transition-colors cursor-pointer"
              @click="$emit('view-yaml', pat._filename, pat._raw_yaml)"
            >
              <i class="pi pi-file-code text-xs"></i>
              <span class="sr-only">YAML</span>
            </button>
          </div>
        </div>

        <div class="l2-signals-list flex flex-col gap-1">
          <span class="section-sublabel text-[11px] font-medium text-surface-400">訊號群組特徵:</span>
          <div class="signal-chips flex flex-wrap gap-1">
            <span v-for="sig in pat.signals" :key="sig.role" class="signal-chip bg-surface-card border border-surface-border text-surface-200 text-xs px-1.5 py-0.2 rounded font-mono">
              {{ sig.role }} <small v-if="sig.required" class="text-primary-400 font-normal">(必備)</small>
            </span>
          </div>
        </div>

        <div v-if="(pat.component_role_overrides && pat.component_role_overrides.length > 0) || (pat.role_overrides && pat.role_overrides.length > 0)" class="role-overrides-box pt-2 border-t border-surface-border flex flex-col gap-1">
          <span class="section-sublabel text-[11px] font-medium text-surface-400">元件角色拓撲覆寫:</span>
          <ul class="overrides-list m-0 pl-4 text-xs text-surface-200 space-y-0.5 list-disc">
            <li v-for="(ov, idx) in (pat.component_role_overrides || pat.role_overrides)" :key="idx">
              <code class="text-primary-400 font-mono">{{ ov.original_sub_category }}</code> 連接至 <code class="text-primary-400 font-mono">{{ ov.connected_to }}</code> ➔ 覆寫為 <strong class="text-surface-0">{{ ov.new_role }}</strong>
            </li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * @file Level2TopologyTab.vue
 * @description Level 2 網路拓撲與匯流排規範頁籤 (2026 雙主題版)
 */

import Tag from 'primevue/tag'
import type { Level2PatternItem } from '@/types/pattern'

defineProps<{
  patterns: Level2PatternItem[]
}>()

defineEmits<{
  (e: 'view-yaml', filename: string, rawYaml: string): void
}>()
</script>
