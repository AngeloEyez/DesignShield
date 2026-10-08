<template>
  <div class="tab-content">
    <div class="partdb-banner">
      <div class="partdb-banner-info">
        <h3>
          <i class="pi pi-database text-indigo mr-2"></i>
          PartDB 零件特規與原廠規格書真相來源
        </h3>
        <p>
          集中維護真實 IC 型號之介面電氣限制 (如 I2C 阻值範圍、禁止接地電容)。所有特規皆強制綁定 <code>_meta</code> 規格書出處與頁碼，為 DRC 違規報告提供可查證鐵證。
        </p>
      </div>
    </div>

    <div class="partdb-grid">
      <div
        v-for="part in parts"
        :key="part.pn"
        class="part-card"
      >
        <div class="part-card-header">
          <div class="part-title-wrapper">
            <span class="part-icon"><i class="pi pi-microchip"></i></span>
            <div>
              <h3 class="part-pn">{{ part.pn }}</h3>
              <span class="part-file-label">{{ part._filename }}</span>
            </div>
          </div>
          <button
            type="button"
            class="yaml-view-btn"
            @click="$emit('view-yaml', part._filename, part._raw_yaml)"
          >
            <i class="pi pi-file-code mr-1"></i>YAML
          </button>
        </div>

        <p class="part-desc">{{ part.description || '無描述' }}</p>

        <div class="interfaces-section">
          <h4 class="iface-title">
            <i class="pi pi-sliders-v mr-1"></i>支援硬體介面特規 ({{ Object.keys(part.interfaces || {}).length }})
          </h4>

          <div
            v-for="(spec, ifName) in part.interfaces"
            :key="ifName"
            class="iface-box"
          >
            <div class="iface-header">
              <span class="iface-badge">{{ ifName }}</span>
            </div>

            <!-- 特規參數 -->
            <div class="iface-props">
              <div v-if="spec.pullup_range_ohms" class="prop-item">
                <span class="prop-name">上拉阻值範圍:</span>
                <span class="prop-val">{{ spec.pullup_range_ohms[0] }}Ω ~ {{ spec.pullup_range_ohms[1] }}Ω</span>
              </div>
              <div v-if="spec.forbid_gnd_capacitor !== undefined" class="prop-item">
                <span class="prop-name">嚴禁接地電容:</span>
                <span class="prop-val" :class="spec.forbid_gnd_capacitor ? 'text-red font-bold' : ''">
                  {{ spec.forbid_gnd_capacitor ? '是 (Forbid)' : '否' }}
                </span>
              </div>
              <div v-if="spec.requires_series_resistor !== undefined" class="prop-item">
                <span class="prop-name">強制串聯電阻:</span>
                <span class="prop-val">{{ spec.requires_series_resistor ? '是' : '否' }}</span>
              </div>
              <div v-if="spec.max_bus_capacitance_pf" class="prop-item">
                <span class="prop-name">最大寄生電容:</span>
                <span class="prop-val">{{ spec.max_bus_capacitance_pf }} pF</span>
              </div>
              <div v-if="spec.default_address" class="prop-item">
                <span class="prop-name">預設 7-bit 位址:</span>
                <span class="prop-val font-mono">{{ spec.default_address }}</span>
              </div>
            </div>

            <!-- 結構化溯源證據 _meta -->
            <div v-if="spec._meta" class="evidence-box">
              <div class="evidence-header">
                <i class="pi pi-bookmark text-primary mr-1"></i>
                <span>原廠規格書溯源鐵證 (Datasheet Evidence)</span>
              </div>
              <div class="evidence-body">
                <div class="evidence-source">
                  <span class="source-file"><i class="pi pi-file-pdf mr-1"></i>{{ spec._meta.evidence }}</span>
                  <span class="source-page">第 {{ spec._meta.page }} 頁</span>
                </div>
                <blockquote class="evidence-quote">
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

<style scoped>
.tab-content {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.partdb-banner {
  background-color: var(--surface-card, #1e293b);
  border: 1px solid #334155;
  border-left: 4px solid #818cf8;
  border-radius: 8px;
  padding: 1.25rem;
}

.partdb-banner-info h3 {
  margin: 0 0 0.5rem 0;
  font-size: 1.1rem;
  color: #f8fafc;
  display: flex;
  align-items: center;
}

.partdb-banner-info p {
  margin: 0;
  font-size: 0.875rem;
  color: #94a3b8;
  line-height: 1.5;
}

.partdb-banner-info code {
  background-color: #0f172a;
  padding: 0.15rem 0.4rem;
  border-radius: 4px;
  color: #38bdf8;
  font-family: monospace;
}

.partdb-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(420px, 1fr));
  gap: 1.25rem;
}

.part-card {
  background-color: var(--surface-card, #1e293b);
  border: 1px solid #334155;
  border-radius: 8px;
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.part-card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.part-title-wrapper {
  display: flex;
  gap: 0.75rem;
  align-items: center;
}

.part-icon {
  width: 40px;
  height: 40px;
  background-color: rgba(99, 102, 241, 0.15);
  color: #818cf8;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.25rem;
}

.part-pn {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 700;
  color: #f8fafc;
}

.part-file-label {
  font-size: 0.75rem;
  color: #64748b;
  font-family: monospace;
}

.part-desc {
  margin: 0;
  font-size: 0.875rem;
  color: #94a3b8;
  line-height: 1.4;
}

.interfaces-section {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  border-top: 1px dashed #334155;
  padding-top: 0.75rem;
}

.iface-title {
  margin: 0;
  font-size: 0.85rem;
  color: #cbd5e1;
  font-weight: 600;
  display: flex;
  align-items: center;
}

.iface-box {
  background-color: #0f172a;
  border: 1px solid #1e293b;
  border-radius: 6px;
  padding: 0.85rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.iface-header {
  display: flex;
  align-items: center;
}

.iface-badge {
  background-color: rgba(99, 102, 241, 0.2);
  color: #a5b4fc;
  font-size: 0.75rem;
  font-weight: 700;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
}

.iface-props {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.prop-item {
  display: flex;
  justify-content: space-between;
  font-size: 0.8rem;
}

.prop-name {
  color: #94a3b8;
}

.prop-val {
  color: #f8fafc;
  font-weight: 500;
}

.evidence-box {
  background-color: rgba(30, 41, 59, 0.6);
  border-left: 3px solid #38bdf8;
  border-radius: 4px;
  padding: 0.6rem 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.evidence-header {
  font-size: 0.75rem;
  font-weight: 600;
  color: #38bdf8;
  display: flex;
  align-items: center;
}

.evidence-body {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.evidence-source {
  display: flex;
  justify-content: space-between;
  font-size: 0.75rem;
  color: #cbd5e1;
}

.source-file {
  font-family: monospace;
  color: #67e8f9;
}

.source-page {
  font-weight: 600;
  color: #f1f5f9;
}

.evidence-quote {
  margin: 0;
  font-size: 0.75rem;
  font-style: italic;
  color: #94a3b8;
  line-height: 1.35;
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
