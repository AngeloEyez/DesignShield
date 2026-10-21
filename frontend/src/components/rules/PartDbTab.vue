<template>
  <div class="flex flex-col gap-3">
    <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
      <div
        v-for="part in parts"
        :key="part.pn"
        class="bg-surface-panel border border-surface-border rounded p-3 flex flex-col gap-2.5"
      >
        <div class="flex justify-between items-start gap-2">
          <div class="flex gap-2.5 items-center">
            <span class="w-8 h-8 bg-primary-500/15 text-primary-400 rounded flex items-center justify-center text-sm shrink-0">
              <i class="pi pi-microchip"></i>
            </span>
            <div>
              <div class="flex items-center gap-1.5 flex-wrap">
                <span
                  v-if="part.mfg"
                  class="text-[10px] px-1.5 py-0.2 rounded font-mono bg-surface-card border border-surface-border text-surface-300 font-semibold uppercase"
                >
                  {{ part.mfg }}
                </span>
                <h3 class="m-0 text-sm font-semibold text-surface-0 font-mono">{{ part.mfg_pn || part.pn }}</h3>
              </div>
              <div class="flex items-center gap-2 mt-0.5 text-[11px] text-surface-400 font-mono">
                <span v-if="part.mfg">廠商: {{ part.mfg }}</span>
                <span v-if="part.mfg">|</span>
                <span>廠商料號: {{ part.mfg_pn || part.pn }}</span>
                <span>({{ part._filename }})</span>
              </div>
            </div>
          </div>
          <button
            type="button"
            v-tooltip.left="'檢視 YAML'"
            class="yaml-view-btn flex items-center p-1 text-xs rounded border border-surface-border bg-surface-card text-primary-400 hover:bg-surface-hover transition-colors cursor-pointer"
            @click="$emit('view-yaml', part._filename || '', part._raw_yaml || '')"
          >
            <i class="pi pi-file-code text-xs"></i>
            <span class="sr-only">YAML</span>
          </button>
        </div>

        <p class="m-0 text-xs text-surface-200 leading-normal">{{ part.description || '無描述' }}</p>

        <div class="flex flex-col gap-2 border-t border-surface-border pt-2">
          <h4 class="m-0 text-[11px] text-surface-400 font-semibold flex items-center gap-1 uppercase tracking-wider">
            <i class="pi pi-sliders-v text-[10px]"></i>
            <span>支援硬體介面特規 ({{ Object.keys(part.interfaces || {}).length }})</span>
          </h4>

          <div
            v-for="(spec, ifName) in part.interfaces"
            :key="ifName"
            class="bg-surface-card border border-surface-border rounded p-2.5 flex flex-col gap-2"
          >
            <div class="flex items-center">
              <span class="bg-primary-500/15 text-primary-400 text-[11px] font-semibold px-1.5 py-0.2 rounded font-mono">{{ ifName }}</span>
            </div>

            <!-- 特規參數 -->
            <div class="flex flex-col gap-1 text-xs">
              <div v-if="spec.pullup_range_ohms" class="flex justify-between">
                <span class="text-surface-400">上拉阻值範圍:</span>
                <span class="text-surface-0 font-medium font-mono">{{ spec.pullup_range_ohms[0] }}Ω ~ {{ spec.pullup_range_ohms[1] }}Ω</span>
              </div>
              <div v-if="spec.forbid_gnd_capacitor !== undefined" class="flex justify-between">
                <span class="text-surface-400">嚴禁接地電容:</span>
                <span :class="spec.forbid_gnd_capacitor ? 'text-red-500 font-semibold' : 'text-surface-0 font-medium'">
                  {{ spec.forbid_gnd_capacitor ? '是 (Forbid)' : '否' }}
                </span>
              </div>
              <div v-if="spec.requires_series_resistor !== undefined" class="flex justify-between">
                <span class="text-surface-400">強制串聯電阻:</span>
                <span class="text-surface-0 font-medium">{{ spec.requires_series_resistor ? '是' : '否' }}</span>
              </div>
              <div v-if="spec.max_bus_capacitance_pf" class="flex justify-between">
                <span class="text-surface-400">最大寄生電容:</span>
                <span class="text-surface-0 font-medium font-mono">{{ spec.max_bus_capacitance_pf }} pF</span>
              </div>
              <div v-if="spec.default_address" class="flex justify-between">
                <span class="text-surface-400">預設 7-bit 位址:</span>
                <span class="text-surface-0 font-medium font-mono">{{ spec.default_address }}</span>
              </div>
            </div>

            <!-- 結構化溯源證據 _meta -->
            <div v-if="spec._meta" class="border-l-2 border-l-primary-500 pl-2.5 py-1 flex flex-col gap-1">
              <div class="text-[11px] font-semibold text-primary-400 flex items-center gap-1">
                <i class="pi pi-bookmark text-[10px]"></i>
                <span>原廠規格書溯源鐵證</span>
              </div>
              <div class="flex flex-col gap-0.5 text-xs">
                <div class="flex justify-between text-surface-200">
                  <span class="font-mono text-primary-400"><i class="pi pi-file-pdf mr-1"></i>{{ spec._meta.evidence }}</span>
                  <span class="font-semibold text-surface-0 font-mono">第 {{ spec._meta.page }} 頁</span>
                </div>
                <blockquote class="m-0 text-[11px] italic text-surface-400 leading-normal">
                  "{{ spec._meta.excerpt }}"
                </blockquote>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * @file PartDbTab.vue
 * @description PartDB 零件特規庫頁籤 (2026 雙主題版)
 */

import type { PartDBItem } from '@/types/pattern'

defineProps<{
  parts: PartDBItem[]
}>()

defineEmits<{
  (e: 'view-yaml', filename: string, rawYaml: string): void
}>()
</script>
