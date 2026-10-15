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

    <!-- 3.55 差分通道鏈路拓撲歷程 -->
    <div
      v-if="hasTopologyFlow(item.evidence_trail)"
      class="channel-segments-box p-2.5 rounded bg-[#1e1e1e] border border-[#2a2a2a] flex flex-col gap-2"
    >
      <div class="flex items-center justify-between flex-wrap gap-1.5">
        <div class="flex items-center gap-1.5">
          <i class="pi pi-sitemap text-teal-400 text-xs"></i>
          <span class="text-[10px] font-semibold text-[#a0a0a0] uppercase tracking-wider">
            差分通道端到端鏈路拓撲
          </span>
        </div>
        <div class="flex items-center gap-1.5 flex-wrap">
          <span
            v-if="item.evidence_trail.pass_through_components && item.evidence_trail.pass_through_components.length > 0"
            class="text-[10px] px-1.5 py-0.2 rounded bg-sky-500/10 border border-sky-500/25 text-sky-300 font-mono"
          >
            途經元件: {{ item.evidence_trail.pass_through_components.join(', ') }}
          </span>
          <span
            v-if="item.evidence_trail.symmetry_check"
            class="text-[10px] px-1.5 py-0.2 rounded font-mono font-semibold"
            :class="item.evidence_trail.symmetry_check.is_symmetric ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30' : 'bg-red-500/15 text-red-300 border border-red-500/30'"
          >
            {{ item.evidence_trail.symmetry_check.is_symmetric ? 'P/N 拓撲完全對稱' : 'P/N 拓撲不對稱' }}
          </span>
        </div>
      </div>

      <!-- 正極 (P) 鏈路拓撲 -->
      <div class="channel-p-flow flex flex-col gap-1">
        <div class="flex items-center gap-1.5 text-[10px] font-mono text-emerald-400 font-semibold">
          <span class="px-1.5 py-0.2 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">P+ 正極鏈路</span>
          <span class="text-[#858585] font-normal">({{ item.evidence_trail.p_net || '正極網路' }})</span>
        </div>
        <div class="path-segments-flow flex items-center gap-1.5 flex-wrap p-2 rounded bg-[#141414] border border-[#2a2a2a] text-xs">
          <template v-for="(stage, stIdx) in getTopologyFlow(item.evidence_trail, 'p')" :key="'p-' + stIdx">
            <template v-if="stage.stage === 'endpoints'">
              <div class="flex items-center gap-1.5 flex-wrap">
                <template v-if="stIdx === 0">
                  <div v-if="stage.devices && stage.devices.length > 0" class="flex items-center gap-1 flex-wrap">
                    <div
                      v-for="(dev, dIdx) in stage.devices"
                      :key="dIdx"
                      :class="getDeviceBadgeClass(dev.type, dev.ref_des)"
                      class="device-chip flex items-center gap-1 px-1.5 py-0.2 rounded border font-mono text-[10px]"
                      :title="dev.part_number ? `料號: ${dev.part_number}` : ''"
                    >
                      <i :class="getDeviceIcon(dev.type, dev.ref_des)" class="text-[9px]"></i>
                      <span class="font-bold">{{ formatDeviceDisplay(dev).refPin }}</span>
                      <span v-if="formatDeviceDisplay(dev).pinName" class="opacity-80">
                        [{{ formatDeviceDisplay(dev).pinName }}]
                      </span>
                    </div>
                  </div>
                  <i v-if="stage.devices && stage.devices.length > 0" class="pi pi-arrow-right text-[9px] text-teal-400/60"></i>
                  <span class="net-name-chip font-mono px-1.5 py-0.2 rounded bg-teal-500/10 border border-teal-500/30 text-teal-300 font-semibold text-[11px]">
                    {{ stage.net }}
                  </span>
                </template>
                <template v-else>
                  <span class="net-name-chip font-mono px-1.5 py-0.2 rounded bg-teal-500/10 border border-teal-500/30 text-teal-300 font-semibold text-[11px]">
                    {{ stage.net }}
                  </span>
                  <i v-if="stage.devices && stage.devices.length > 0" class="pi pi-arrow-right text-[9px] text-teal-400/60"></i>
                  <div v-if="stage.devices && stage.devices.length > 0" class="flex items-center gap-1 flex-wrap">
                    <div
                      v-for="(dev, dIdx) in stage.devices"
                      :key="dIdx"
                      :class="getDeviceBadgeClass(dev.type, dev.ref_des)"
                      class="device-chip flex items-center gap-1 px-1.5 py-0.2 rounded border font-mono text-[10px]"
                      :title="dev.part_number ? `料號: ${dev.part_number}` : ''"
                    >
                      <i :class="getDeviceIcon(dev.type, dev.ref_des)" class="text-[9px]"></i>
                      <span class="font-bold">{{ formatDeviceDisplay(dev).refPin }}</span>
                      <span v-if="formatDeviceDisplay(dev).pinName" class="opacity-80">
                        [{{ formatDeviceDisplay(dev).pinName }}]
                      </span>
                    </div>
                  </div>
                </template>
              </div>
            </template>

            <template v-else-if="stage.stage === 'pass_through'">
              <i class="pi pi-arrow-right text-[9px] text-[#666666]"></i>
              <div class="pass-comp-pill flex items-center gap-1 px-1.5 py-0.2 rounded bg-sky-500/15 border border-sky-500/35 text-sky-300 font-mono text-[10px]">
                <i class="pi pi-compass text-[9px] text-sky-400"></i>
                <span class="font-bold">{{ stage.component }}</span>
                <span v-if="stage.type" class="text-[9px] px-1 py-0.2 rounded bg-sky-400/20 text-sky-200 uppercase">
                  {{ stage.type }}
                </span>
                <span v-if="stage.in_pin && stage.out_pin" class="text-[10px] font-semibold text-sky-400">
                  ({{ stage.in_pin }} ➔ {{ stage.out_pin }})
                </span>
              </div>
              <i class="pi pi-arrow-right text-[9px] text-[#666666]"></i>
            </template>
          </template>
        </div>
      </div>

      <!-- 負極 (N) 鏈路拓撲 -->
      <div v-if="item.evidence_trail.n_net || (item.evidence_trail.n_endpoints && item.evidence_trail.n_endpoints.length > 0)" class="channel-n-flow flex flex-col gap-1">
        <div class="flex items-center gap-1.5 text-[10px] font-mono text-teal-400 font-semibold">
          <span class="px-1.5 py-0.2 rounded bg-teal-500/20 text-teal-300 border border-teal-500/30">N- 負極鏈路</span>
          <span class="text-[#858585] font-normal">({{ item.evidence_trail.n_net || '負極網路' }})</span>
        </div>
        <div class="path-segments-flow flex items-center gap-1.5 flex-wrap p-2 rounded bg-[#141414] border border-[#2a2a2a] text-xs">
          <template v-for="(stage, stIdx) in getTopologyFlow(item.evidence_trail, 'n')" :key="'n-' + stIdx">
            <template v-if="stage.stage === 'endpoints'">
              <div class="flex items-center gap-1.5 flex-wrap">
                <template v-if="stIdx === 0">
                  <div v-if="stage.devices && stage.devices.length > 0" class="flex items-center gap-1 flex-wrap">
                    <div
                      v-for="(dev, dIdx) in stage.devices"
                      :key="dIdx"
                      :class="getDeviceBadgeClass(dev.type, dev.ref_des)"
                      class="device-chip flex items-center gap-1 px-1.5 py-0.2 rounded border font-mono text-[10px]"
                      :title="dev.part_number ? `料號: ${dev.part_number}` : ''"
                    >
                      <i :class="getDeviceIcon(dev.type, dev.ref_des)" class="text-[9px]"></i>
                      <span class="font-bold">{{ formatDeviceDisplay(dev).refPin }}</span>
                      <span v-if="formatDeviceDisplay(dev).pinName" class="opacity-80">
                        [{{ formatDeviceDisplay(dev).pinName }}]
                      </span>
                    </div>
                  </div>
                  <i v-if="stage.devices && stage.devices.length > 0" class="pi pi-arrow-right text-[9px] text-teal-400/60"></i>
                  <span class="net-name-chip font-mono px-1.5 py-0.2 rounded bg-teal-500/10 border border-teal-500/30 text-teal-300 font-semibold text-[11px]">
                    {{ stage.net }}
                  </span>
                </template>
                <template v-else>
                  <span class="net-name-chip font-mono px-1.5 py-0.2 rounded bg-teal-500/10 border border-teal-500/30 text-teal-300 font-semibold text-[11px]">
                    {{ stage.net }}
                  </span>
                  <i v-if="stage.devices && stage.devices.length > 0" class="pi pi-arrow-right text-[9px] text-teal-400/60"></i>
                  <div v-if="stage.devices && stage.devices.length > 0" class="flex items-center gap-1 flex-wrap">
                    <div
                      v-for="(dev, dIdx) in stage.devices"
                      :key="dIdx"
                      :class="getDeviceBadgeClass(dev.type, dev.ref_des)"
                      class="device-chip flex items-center gap-1 px-1.5 py-0.2 rounded border font-mono text-[10px]"
                      :title="dev.part_number ? `料號: ${dev.part_number}` : ''"
                    >
                      <i :class="getDeviceIcon(dev.type, dev.ref_des)" class="text-[9px]"></i>
                      <span class="font-bold">{{ formatDeviceDisplay(dev).refPin }}</span>
                      <span v-if="formatDeviceDisplay(dev).pinName" class="opacity-80">
                        [{{ formatDeviceDisplay(dev).pinName }}]
                      </span>
                    </div>
                  </div>
                </template>
              </div>
            </template>

            <template v-else-if="stage.stage === 'pass_through'">
              <i class="pi pi-arrow-right text-[9px] text-[#666666]"></i>
              <div class="pass-comp-pill flex items-center gap-1 px-1.5 py-0.2 rounded bg-sky-500/15 border border-sky-500/35 text-sky-300 font-mono text-[10px]">
                <i class="pi pi-compass text-[9px] text-sky-400"></i>
                <span class="font-bold">{{ stage.component }}</span>
                <span v-if="stage.type" class="text-[9px] px-1 py-0.2 rounded bg-sky-400/20 text-sky-200 uppercase">
                  {{ stage.type }}
                </span>
                <span v-if="stage.in_pin && stage.out_pin" class="text-[10px] font-semibold text-sky-400">
                  ({{ stage.in_pin }} ➔ {{ stage.out_pin }})
                </span>
              </div>
              <i class="pi pi-arrow-right text-[9px] text-[#666666]"></i>
            </template>
          </template>
        </div>
      </div>
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

    <!-- 4. 詳細檢驗佐證歷程 JSON -->
    <div class="raw-evidence-section flex flex-col gap-1">
      <div class="flex justify-between items-center">
        <span class="evidence-title text-[10px] font-semibold text-[#858585] uppercase tracking-wider">
          佐證歷程 (JSON)
        </span>
        <button
          class="copy-json-btn flex items-center gap-1 text-[10px] text-[#858585] hover:text-white cursor-pointer bg-transparent border-0 p-0.5 transition-colors"
          @click.stop="copyEvidenceJson"
        >
          <i :class="isCopied ? 'pi pi-check text-green-400' : 'pi pi-copy'"></i>
          <span>{{ isCopied ? '已複製' : '複製 JSON' }}</span>
        </button>
      </div>
      <pre class="json-code m-0 font-mono text-[10px] text-[#d4d4d4] bg-[#121212] p-2 rounded max-h-48 overflow-y-auto border border-[#2a2a2a] leading-relaxed select-text">{{ formatJson(item.evidence_trail) }}</pre>
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
import type { ViolationItem, TopologyFlowStage, FlowDevice } from './TaskReportDashboard.vue'
import { copyToClipboard } from '@/utils/clipboard'

interface Props {
  item: ViolationItem
}

const props = defineProps<Props>()
const isCopied = ref<boolean>(false)

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
 * 檢查佐證歷程是否包含差分通道拓撲鏈路資料
 */
const hasTopologyFlow = (evidence: Record<string, any> | undefined): boolean => {
  if (!evidence) return false
  return Boolean(
    (Array.isArray(evidence.topology_flow) && evidence.topology_flow.length > 0) ||
    (Array.isArray(evidence.path_segments) && evidence.path_segments.length > 0) ||
    (Array.isArray(evidence.p_endpoints) && evidence.p_endpoints.length > 0 && evidence.p_net)
  )
}

/**
 * 取得差分通道端到端完整鏈路拓撲流程
 */
const getTopologyFlow = (
  evidence: Record<string, any> | undefined,
  polarity: 'p' | 'n' = 'p'
): TopologyFlowStage[] => {
  if (!evidence) return []

  const flowKey = polarity === 'p' ? 'topology_flow' : 'n_topology_flow'
  if (Array.isArray(evidence[flowKey]) && evidence[flowKey].length > 0) {
    return evidence[flowKey]
  }

  const segs = polarity === 'p' ? (evidence.path_segments || []) : (evidence.n_path_segments || [])
  const endpoints = polarity === 'p' ? (evidence.p_endpoints || []) : (evidence.n_endpoints || [])
  const startNet = polarity === 'p' ? (evidence.p_net || '') : (evidence.n_net || '')

  const seenSegs = new Set<string>()
  const uniqueSegs: any[] = []
  for (const s of segs) {
    const k = `${s.from_net}|${s.pass_component}|${s.in_pin}|${s.out_pin}|${s.to_net}`
    if (!seenSegs.has(k)) {
      seenSegs.add(k)
      uniqueSegs.push(s)
    }
  }

  if (uniqueSegs.length === 0) {
    if (endpoints.length > 0) {
      return [
        {
          stage: 'endpoints',
          net: startNet,
          devices: endpoints.map((ep: any) => ({
            ref_des: ep.ref_des,
            pin: ep.pin || '',
            pin_name: ep.pin_name || (ep.pin && ep.pin !== ep.pin_number ? ep.pin : ''),
            pin_number: ep.pin_number || '',
            part_number: ep.part_number || '',
            type: ep.component_type || '',
          })),
        },
      ]
    }
    return []
  }

  const endpointsByNet: Record<string, FlowDevice[]> = {}
  for (const ep of endpoints) {
    const net = ep.connected_net || (endpoints.indexOf(ep) === 0 ? uniqueSegs[0].from_net : uniqueSegs[uniqueSegs.length - 1].to_net)
    if (!endpointsByNet[net]) {
      endpointsByNet[net] = []
    }
    endpointsByNet[net].push({
      ref_des: ep.ref_des,
      pin: ep.pin || '',
      pin_name: ep.pin_name || (ep.pin && ep.pin !== ep.pin_number ? ep.pin : ''),
      pin_number: ep.pin_number || '',
      part_number: ep.part_number || '',
      type: ep.component_type || '',
    })
  }

  const flow: TopologyFlowStage[] = []
  const visitedNets = new Set<string>()

  uniqueSegs.forEach((seg, idx) => {
    const fromNet = seg.from_net
    const toNet = seg.to_net

    if (!visitedNets.has(fromNet)) {
      visitedNets.add(fromNet)
      flow.push({
        stage: 'endpoints',
        net: fromNet,
        devices: endpointsByNet[fromNet] || [],
      })
    }

    flow.push({
      stage: 'pass_through',
      component: seg.pass_component,
      type: seg.pass_component_type || 'Passive',
      in_pin: seg.in_pin || '',
      out_pin: seg.out_pin || '',
      from_net: fromNet,
      to_net: toNet,
    })

    if (!visitedNets.has(toNet) && (idx === uniqueSegs.length - 1 || uniqueSegs[idx + 1].from_net !== toNet)) {
      visitedNets.add(toNet)
      flow.push({
        stage: 'endpoints',
        net: toNet,
        devices: endpointsByNet[toNet] || [],
      })
    }
  })

  return flow
}

/**
 * 依據元件類型與 RefDes 取得 PrimeIcons 圖標名稱
 */
const getDeviceIcon = (type?: string, refDes?: string): string => {
  const t = (type || '').toLowerCase()
  const r = (refDes || '').toUpperCase()
  if (t.includes('connector') || r.startsWith('J') || r.startsWith('P') || r.startsWith('CN')) {
    return 'pi pi-link'
  }
  if (t.includes('ic') || r.startsWith('U')) {
    return 'pi pi-server'
  }
  return 'pi pi-box'
}

/**
 * 依據元件類型取得徽章色彩樣式
 */
const getDeviceBadgeClass = (type?: string, refDes?: string): string => {
  const t = (type || '').toLowerCase()
  const r = (refDes || '').toUpperCase()
  if (t.includes('connector') || r.startsWith('J') || r.startsWith('P') || r.startsWith('CN')) {
    return 'bg-amber-500/15 border-amber-500/35 text-amber-300'
  }
  if (t.includes('ic') || r.startsWith('U')) {
    return 'bg-purple-500/15 border-purple-500/35 text-purple-300'
  }
  return 'bg-slate-700/40 border-slate-600 text-slate-300'
}

/**
 * 格式化零件與引腳在拓撲鏈路中的展示字串
 * 格式規範: {part_reference}.{pin_number} [{pin_name}]
 * 例如: TJ1.A6 [DP2]
 */
const formatDeviceDisplay = (dev: FlowDevice): { refPin: string; pinName?: string } => {
  const pinNum = dev.pin_number || ''
  const pinNm = dev.pin_name || (dev.pin && dev.pin !== pinNum ? dev.pin : '')

  if (pinNum) {
    return {
      refPin: `${dev.ref_des}.${pinNum}`,
      pinName: pinNm || undefined,
    }
  }

  // 若未傳遞獨立 pin_number 但有 pin 欄位
  if (dev.pin) {
    // 若 pin 格式為實體腳位 (如 A6, B7, 1, 2)
    if (/^[A-Z]?\d+$/i.test(dev.pin)) {
      return {
        refPin: `${dev.ref_des}.${dev.pin}`,
        pinName: pinNm && pinNm !== dev.pin ? pinNm : undefined,
      }
    }
    // 否則 pin 為引腳名稱 (如 DP, DN, SCL)
    return {
      refPin: dev.ref_des,
      pinName: dev.pin,
    }
  }

  return {
    refPin: dev.ref_des,
  }
}
</script>
