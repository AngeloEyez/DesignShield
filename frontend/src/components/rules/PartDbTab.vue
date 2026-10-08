<template>
  <div class="flex flex-col gap-5">
    <div class="p-5 rounded-lg border border-surface-border bg-surface-card border-l-4 border-l-indigo-400">
      <div>
        <h3 class="m-0 mb-2 text-lg text-surface-900 dark:text-surface-0 flex items-center font-bold">
          <i class="pi pi-database text-indigo-500 mr-2"></i>
          PartDB 零件特規與原廠規格書真相來源
        </h3>
        <p class="m-0 text-sm text-surface-400 leading-relaxed">
          集中維護真實 IC 型號之介面電氣限制 (如 I2C 阻值範圍、禁止接地電容)。所有特規皆強制綁定 <code class="bg-surface-ground px-1.5 py-0.5 rounded text-sky-400 font-mono">_meta</code> 規格書出處與頁碼，為 DRC 違規報告提供可查證鐵證。
        </p>
      </div>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
      <div
        v-for="part in parts"
        :key="part.pn"
        class="bg-surface-card border border-surface-border rounded-lg p-5 flex flex-col gap-4"
      >
        <div class="flex justify-between items-start">
          <div class="flex gap-3 items-center">
            <span class="w-10 h-10 bg-indigo-500/15 text-indigo-400 rounded-lg flex items-center justify-center text-xl">
              <i class="pi pi-microchip"></i>
            </span>
            <div>
              <h3 class="m-0 text-lg font-bold text-surface-900 dark:text-surface-0">{{ part.pn }}</h3>
              <span class="text-xs text-surface-400 font-mono">{{ part._filename }}</span>
            </div>
          </div>
          <button
            type="button"
            class="yaml-view-btn flex items-center px-2 py-1 text-xs rounded border border-surface-border bg-surface-ground text-primary hover:bg-primary hover:text-surface-900 transition-colors cursor-pointer"
            @click="$emit('view-yaml', part._filename, part._raw_yaml)"
          >
            <i class="pi pi-file-code mr-1"></i>YAML
          </button>
        </div>

        <p class="m-0 text-sm text-surface-400 leading-normal">{{ part.description || '無描述' }}</p>

        <div class="flex flex-col gap-3 border-t border-dashed border-surface-border pt-3">
          <h4 class="m-0 text-sm text-surface-300 font-semibold flex items-center">
            <i class="pi pi-sliders-v mr-1"></i>支援硬體介面特規 ({{ Object.keys(part.interfaces || {}).length }})
          </h4>

          <div
            v-for="(spec, ifName) in part.interfaces"
            :key="ifName"
            class="bg-surface-ground border border-surface-border rounded-md p-3.5 flex flex-col gap-3"
          >
            <div class="flex items-center">
              <span class="bg-indigo-500/20 text-indigo-300 text-xs font-bold px-2 py-0.5 rounded">{{ ifName }}</span>
            </div>

            <!-- 特規參數 -->
            <div class="flex flex-col gap-1.5 text-xs">
              <div v-if="spec.pullup_range_ohms" class="flex justify-between">
                <span class="text-surface-400">上拉阻值範圍:</span>
                <span class="text-surface-900 dark:text-surface-0 font-medium">{{ spec.pullup_range_ohms[0] }}Ω ~ {{ spec.pullup_range_ohms[1] }}Ω</span>
              </div>
              <div v-if="spec.forbid_gnd_capacitor !== undefined" class="flex justify-between">
                <span class="text-surface-400">嚴禁接地電容:</span>
                <span :class="spec.forbid_gnd_capacitor ? 'text-red-400 font-bold' : 'text-surface-900 dark:text-surface-0 font-medium'">
                  {{ spec.forbid_gnd_capacitor ? '是 (Forbid)' : '否' }}
                </span>
              </div>
              <div v-if="spec.requires_series_resistor !== undefined" class="flex justify-between">
                <span class="text-surface-400">強制串聯電阻:</span>
                <span class="text-surface-900 dark:text-surface-0 font-medium">{{ spec.requires_series_resistor ? '是' : '否' }}</span>
              </div>
              <div v-if="spec.max_bus_capacitance_pf" class="flex justify-between">
                <span class="text-surface-400">最大寄生電容:</span>
                <span class="text-surface-900 dark:text-surface-0 font-medium">{{ spec.max_bus_capacitance_pf }} pF</span>
              </div>
              <div v-if="spec.default_address" class="flex justify-between">
                <span class="text-surface-400">預設 7-bit 位址:</span>
                <span class="text-surface-900 dark:text-surface-0 font-medium font-mono">{{ spec.default_address }}</span>
              </div>
            </div>

            <!-- 結構化溯源證據 _meta -->
            <div v-if="spec._meta" class="bg-surface-card/60 border-l-2 border-l-sky-400 rounded-r p-2.5 flex flex-col gap-1.5">
              <div class="text-xs font-semibold text-sky-400 flex items-center">
                <i class="pi pi-bookmark text-primary mr-1"></i>
                <span>原廠規格書溯源鐵證 (Datasheet Evidence)</span>
              </div>
              <div class="flex flex-col gap-1 text-xs">
                <div class="flex justify-between text-surface-300">
                  <span class="font-mono text-cyan-300"><i class="pi pi-file-pdf mr-1"></i>{{ spec._meta.evidence }}</span>
                  <span class="font-semibold text-surface-100">第 {{ spec._meta.page }} 頁</span>
                </div>
                <blockquote class="m-0 text-xs italic text-surface-400 leading-normal">
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
import type { PartDBItem } from '@/types/pattern'

defineProps<{
  parts: PartDBItem[]
}>()

defineEmits<{
  (e: 'view-yaml', filename: string, rawYaml: string): void
}>()
</script>
