<template>
  <div class="evidence-details-block border-t border-[#333333] bg-[#161616] p-2.5 flex flex-col gap-2 text-xs">
    <!-- 1. 規則意圖 (精練單行) -->
    <div class="rule-description-box p-2 rounded bg-[#1e1e1e] border border-[#2a2a2a] text-[#cccccc] flex items-start gap-2">
      <i class="pi pi-info-circle text-sky-400 mt-0.5 shrink-0 text-xs"></i>
      <div class="flex flex-col gap-0.5">
        <span class="text-[10px] font-semibold text-[#858585] uppercase tracking-wider">規則意圖</span>
        <span class="leading-relaxed">{{ item.description || item.rule_title }}</span>
      </div>
    </div>

    <!-- 2. 違規原因與改善建議 (若為 FAIL / WARN) -->
    <div v-if="item.error_message" class="error-msg-box p-2 rounded bg-red-500/10 border border-red-500/30 text-red-300 flex items-start gap-2">
      <i class="pi pi-exclamation-circle text-red-400 mt-0.5 shrink-0 text-xs"></i>
      <div class="flex flex-col gap-0.5">
        <span class="text-[10px] font-semibold text-red-400 uppercase tracking-wider">違規原因</span>
        <span class="leading-relaxed font-medium">{{ item.error_message }}</span>
      </div>
    </div>

    <div v-if="item.recommendation" class="recommendation-box p-2 rounded bg-amber-500/10 border border-amber-500/30 text-amber-300 flex items-start gap-2">
      <i class="pi pi-lightbulb text-amber-400 mt-0.5 shrink-0 text-xs"></i>
      <div class="flex flex-col gap-0.5">
        <span class="text-[10px] font-semibold text-amber-400 uppercase tracking-wider">工程建議</span>
        <span class="leading-relaxed">{{ item.recommendation }}</span>
      </div>
    </div>

    <!-- 狀態標記 (PASS / SKIPPED 緊湊提示) -->
    <div v-if="item.status === 'SKIPPED'" class="skipped-box p-1.5 px-2 rounded bg-[#1e1e1e] border border-[#333333] text-[#858585] flex items-center gap-1.5">
      <i class="pi pi-ban text-[#858585] text-xs"></i>
      <span>未發現符合觸發條件之目標，略過執行</span>
    </div>

    <div v-else-if="item.status === 'PASS' && !item.error_message && !item.recommendation" class="pass-box text-green-400/90 flex items-center gap-1.5 text-xs py-0.5">
      <i class="pi pi-check-circle text-green-400 text-xs"></i>
      <span>此受測標的已全數通過規範判定</span>
    </div>

    <!-- 3. 詳細受測節點資訊 -->
    <div class="target-nodes-section p-2 rounded bg-[#1e1e1e] border border-[#2a2a2a] flex flex-col gap-1">
      <span class="text-[10px] font-semibold text-[#858585] uppercase tracking-wider">受測節點</span>
      <div class="nodes-row flex items-center gap-2.5 flex-wrap">
        <div class="flex items-center gap-1">
          <span class="node-label text-[#858585] text-[11px]">受測元件:</span>
          <span v-if="item.target_nodes.components.length > 0" class="flex items-center gap-1 flex-wrap">
            <span
              v-for="c in item.target_nodes.components"
              :key="c"
              class="code-chip text-[10px] font-mono px-1.5 py-0.2 rounded bg-[#141414] border border-[#333333] text-sky-400"
            >
              {{ c }}
            </span>
          </span>
          <span v-else class="text-[#666666] text-[11px]">無特定元件</span>
        </div>

        <div class="flex items-center gap-1 ml-0 sm:ml-3">
          <span class="node-label text-[#858585] text-[11px]">受測網路:</span>
          <span v-if="item.target_nodes.nets.length > 0" class="flex items-center gap-1 flex-wrap">
            <span
              v-for="n in item.target_nodes.nets"
              :key="n"
              class="code-chip text-[10px] font-mono px-1.5 py-0.2 rounded bg-[#141414] border border-[#333333] text-teal-300"
            >
              {{ n }}
            </span>
          </span>
          <span v-else class="text-[#666666] text-[11px]">無特定網路</span>
        </div>
      </div>
    </div>

    <!-- 3.5 結構化審計量測總結 -->
    <div v-if="item.evidence_trail && item.evidence_trail.audit_summary" class="audit-summary-box p-2 rounded bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 flex items-start gap-2">
      <i class="pi pi-check-circle text-emerald-400 mt-0.5 shrink-0 text-xs"></i>
      <div class="flex flex-col gap-0.5">
        <span class="text-[10px] font-semibold text-emerald-400 uppercase tracking-wider">量測審計結論</span>
        <span class="leading-relaxed font-medium">{{ item.evidence_trail.audit_summary }}</span>
      </div>
    </div>

    <!-- 3.55 通用電路通道鏈路拓撲繪圖 (直接展示拓樸繪圖，無多餘外框與說明文字) -->
    <div
      v-if="hasCircuitTopology(item.evidence_trail)"
      class="channel-segments-box w-full"
    >
      <UniversalCircuitTopologySvg :evidence="item.evidence_trail" />
    </div>

    <!-- 3.6 實測電阻與參數卡片 -->
    <div v-if="item.evidence_trail && item.evidence_trail.resistors && item.evidence_trail.resistors.length > 0" class="resistors-table-box p-2 rounded bg-[#1e1e1e] border border-[#2a2a2a] flex flex-col gap-1">
      <span class="text-[10px] font-semibold text-[#858585] uppercase tracking-wider">配置電阻與量測值</span>
      <div class="flex flex-col gap-1">
        <div
          v-for="(r, rIdx) in item.evidence_trail.resistors"
          :key="rIdx"
          class="resistor-row flex items-center justify-between p-1 px-2 rounded bg-[#141414] border border-[#2a2a2a] text-xs flex-wrap gap-1.5"
        >
          <div class="flex items-center gap-2 flex-wrap">
            <span class="font-mono font-bold text-sky-400">{{ r.ref_des }}</span>
            <span class="text-[#858585]">標稱值:</span>
            <span class="font-mono text-emerald-300">{{ r.part_value || (r.resistance_ohm ? `${r.resistance_ohm}Ω` : '未知') }}</span>
            <span v-if="r.power_rail" class="text-[#858585]">供電軌:</span>
            <span v-if="r.power_rail" class="font-mono text-teal-300">{{ r.power_rail }}</span>
          </div>
          <span
            class="text-[9px] font-semibold px-1.5 py-0.2 rounded"
            :class="r.compliant !== false ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30' : 'bg-red-500/15 text-red-300 border border-red-500/30'"
          >
            {{ r.compliant !== false ? '規格合規' : '偏離門檻' }}
          </span>
        </div>
      </div>
    </div>

    <!-- 4. 詳細檢驗佐證歷程 JSON (Debug 訊息，預設收合，必須手動點擊展開) -->
    <div class="raw-evidence-section flex flex-col gap-1">
      <div
        class="flex justify-between items-center cursor-pointer select-none py-1 hover:opacity-90 transition-opacity"
        @click="isJsonExpanded = !isJsonExpanded"
      >
        <div class="flex items-center gap-1.5">
          <i
            class="pi text-[9px] text-[#858585] transition-transform"
            :class="isJsonExpanded ? 'pi-chevron-down' : 'pi-chevron-right'"
          ></i>
          <span class="evidence-title text-[10px] font-semibold text-[#858585] uppercase tracking-wider">
            佐證歷程 (JSON)
          </span>
          <span class="text-[9px] text-surface-500 font-normal">({{ isJsonExpanded ? '點擊收合' : 'Debug 資訊，點擊展開' }})</span>
        </div>
        <button
          class="copy-json-btn flex items-center gap-1 text-[10px] text-[#858585] hover:text-white cursor-pointer bg-transparent border-0 p-0.5 transition-colors"
          @click.stop="copyEvidenceJson"
        >
          <i :class="isCopied ? 'pi pi-check text-green-400' : 'pi pi-copy'"></i>
          <span>{{ isCopied ? '已複製' : '複製 JSON' }}</span>
        </button>
      </div>
      <pre
        v-if="isJsonExpanded"
        class="json-code m-0 font-mono text-[10px] text-[#d4d4d4] bg-[#121212] p-2 rounded max-h-48 overflow-y-auto border border-[#2a2a2a] leading-relaxed select-text"
      >{{ formatJson(item.evidence_trail) }}</pre>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * @file EvidenceDetailsBlock.vue
 * @description DRC 檢驗項目詳細佐證歷程展開面板
 * 支援端到端拓撲鏈路、量測審計數據、電阻參數卡片與 JSON 佐證歷程
 */

import { ref } from 'vue'
import type { ViolationItem } from './TaskReportDashboard.vue'
import { copyToClipboard } from '@/utils/clipboard'
import UniversalCircuitTopologySvg from './UniversalCircuitTopologySvg.vue'

interface Props {
  item: ViolationItem
}

const props = defineProps<Props>()
const isCopied = ref<boolean>(false)
const isJsonExpanded = ref<boolean>(false)

/**
 * 格式化 JSON 字串
 */
const formatJson = (data: any): string => {
  if (!data || Object.keys(data).length === 0) {
    return '{\n  "note": "此檢測項目無額外佐證歷程記錄"\n}'
  }
  return JSON.stringify(data, null, 2)
}

/**
 * 複製佐證歷程 JSON 到剪貼簿
 */
const copyEvidenceJson = async () => {
  const text = JSON.stringify(props.item.evidence_trail || {}, null, 2)
  const ok = await copyToClipboard(text)
  if (ok) {
    isCopied.value = true
    setTimeout(() => {
      isCopied.value = false
    }, 2000)
  }
}

/**
 * 檢查佐證歷程是否包含通用電路通道拓撲資料
 */
const hasCircuitTopology = (evidence: Record<string, any> | undefined): boolean => {
  if (!evidence) return false
  return Boolean(
    evidence.topology &&
    Array.isArray(evidence.topology.nodes) &&
    evidence.topology.nodes.length > 0
  )
}
</script>

