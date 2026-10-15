<template>
  <div class="differential-topology-svg-container flex flex-col gap-2 w-full">
    <!-- 拓撲狀態與對稱性摘要列 -->
    <div class="topology-header-row flex items-center justify-between flex-wrap gap-2 text-xs">
      <div class="flex items-center gap-2">
        <i class="pi pi-sitemap text-teal-400 text-xs"></i>
        <span class="text-[10px] font-semibold text-[#a0a0a0] dark:text-[#a0a0a0] uppercase tracking-wider">
          差分通道端到端鏈路拓撲
        </span>
      </div>

      <div class="flex items-center gap-1.5 flex-wrap">
        <span
          v-if="evidence?.pass_through_components && evidence.pass_through_components.length > 0"
          class="text-[10px] px-1.5 py-0.5 rounded bg-sky-500/10 border border-sky-500/25 text-sky-400 dark:text-sky-300 font-mono"
        >
          途經元件: {{ evidence.pass_through_components.join(', ') }}
        </span>
        <span
          v-if="evidence?.symmetry_check"
          class="text-[10px] px-1.5 py-0.5 rounded font-mono font-semibold"
          :class="evidence.symmetry_check.is_symmetric ? 'bg-emerald-500/15 text-emerald-500 dark:text-emerald-300 border border-emerald-500/30' : 'bg-red-500/15 text-red-500 dark:text-red-300 border border-red-500/30'"
        >
          {{ evidence.symmetry_check.is_symmetric ? 'P/N 拓撲完全對稱' : 'P/N 拓撲不對稱' }}
        </span>
      </div>
    </div>

    <!-- 拓撲軌道圖例 (P+ / N- 指示) -->
    <div class="track-legend-row flex items-center gap-3 text-[10px] font-mono">
      <div class="flex items-center gap-1.5">
        <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
        <span class="font-semibold text-emerald-600 dark:text-emerald-400">P+ 正極軌道</span>
        <span class="text-surface-500 dark:text-surface-400 font-normal">({{ evidence?.p_net || '正極網路' }})</span>
      </div>
      <div v-if="evidence?.n_net || (evidence?.n_endpoints && evidence.n_endpoints.length > 0)" class="flex items-center gap-1.5">
        <span class="w-2 h-2 rounded-full bg-teal-500"></span>
        <span class="font-semibold text-teal-600 dark:text-teal-400">N- 負極軌道</span>
        <span class="text-surface-500 dark:text-surface-400 font-normal">({{ evidence?.n_net || '負極網路' }})</span>
      </div>
    </div>

    <!-- SVG 拓撲畫布與水平捲動保護層 -->
    <div class="topology-canvas-viewport w-full overflow-x-auto rounded border border-surface-200 dark:border-[#2a2a2a] bg-surface-50/50 dark:bg-[#141414] p-2 transition-colors">
      <svg
        :viewBox="`0 0 ${layout.width} ${layout.height}`"
        :style="{ minWidth: `${layout.width}px`, height: `${layout.height}px` }"
        class="w-full bg-transparent overflow-visible select-none block"
      >
        <defs>
          <!-- P 軌箭頭標記 -->
          <marker
            id="arrow-p"
            viewBox="0 0 10 10"
            refX="7"
            refY="5"
            markerWidth="6"
            markerHeight="6"
            orient="auto-start-reverse"
          >
            <path d="M 0 1.5 L 8 5 L 0 8.5 z" class="fill-emerald-500 dark:fill-emerald-400" />
          </marker>

          <!-- N 軌箭頭標記 -->
          <marker
            id="arrow-n"
            viewBox="0 0 10 10"
            refX="7"
            refY="5"
            markerWidth="6"
            markerHeight="6"
            orient="auto-start-reverse"
          >
            <path d="M 0 1.5 L 8 5 L 0 8.5 z" class="fill-teal-500 dark:fill-teal-400" />
          </marker>
        </defs>

        <!-- 1. 曼哈頓階梯折線 (Edges) -->
        <g class="topology-edges">
          <path
            v-for="edge in layout.edges"
            :key="edge.id"
            :d="edge.pathD"
            :class="edge.polarity === 'p' ? 'stroke-emerald-500 dark:stroke-emerald-400' : 'stroke-teal-500 dark:stroke-teal-400'"
            :marker-end="edge.polarity === 'p' ? 'url(#arrow-p)' : 'url(#arrow-n)'"
            class="fill-none stroke-2 transition-all opacity-85 hover:opacity-100"
          />
        </g>

        <!-- 2. 分支電氣焊點圓點 (Junction Dots ●) -->
        <g class="topology-junction-dots">
          <circle
            v-for="dot in layout.junctionDots"
            :key="dot.id"
            :cx="dot.x"
            :cy="dot.y"
            r="3.5"
            :class="dot.polarity === 'p' ? 'fill-emerald-500 dark:fill-emerald-400 stroke-surface-50 dark:stroke-[#141414]' : 'fill-teal-500 dark:fill-teal-400 stroke-surface-50 dark:stroke-[#141414]'"
            class="stroke-1"
          />
        </g>

        <!-- 3. 實體網路名稱標籤膠囊 (Net Label Pills) -->
        <g class="topology-net-labels">
          <g
            v-for="lbl in layout.netLabels"
            :key="lbl.id"
            :transform="`translate(${lbl.x - lbl.width / 2}, ${lbl.y - lbl.height / 2})`"
            class="net-label-group cursor-default"
          >
            <rect
              :width="lbl.width"
              :height="lbl.height"
              rx="4"
              class="fill-surface-0 dark:fill-[#181818] stroke-surface-300 dark:stroke-[#333333] stroke-1 shadow-sm"
            />
            <text
              :x="lbl.width / 2"
              :y="lbl.height / 2 + 3.5"
              text-anchor="middle"
              class="text-[9px] font-mono font-semibold"
              :class="lbl.polarity === 'p' ? 'fill-emerald-600 dark:fill-teal-300' : 'fill-teal-600 dark:fill-teal-300'"
            >
              {{ lbl.net }}
            </text>
          </g>
        </g>

        <!-- 4. 元件卡片節點 (Nodes) -->
        <g class="topology-nodes">
          <g
            v-for="node in layout.nodes"
            :key="node.id"
            :transform="`translate(${node.x}, ${node.y})`"
            class="topology-node-group cursor-default"
          >
            <!-- 節點底卡 (帶圓角與主題樣式) -->
            <rect
              :width="node.width"
              :height="node.height"
              rx="6"
              class="fill-surface-0 dark:fill-[#1c1c1c] stroke-surface-300 dark:stroke-[#2e2e2e] stroke-1 shadow-sm transition-colors"
            />

            <!-- 節點頂部標題列 (RefDes 與 元件類型徽章) -->
            <rect
              x="0"
              y="0"
              :width="node.width"
              height="22"
              rx="6"
              class="fill-surface-100 dark:fill-[#252526] stroke-none"
            />
            <!-- 覆蓋底部圓角以維持直角連接 -->
            <rect
              x="0"
              y="16"
              :width="node.width"
              height="6"
              class="fill-surface-100 dark:fill-[#252526] stroke-none"
            />

            <!-- 元件類型圖標/徽章 -->
            <rect
              x="6"
              y="3"
              width="36"
              height="15"
              rx="3"
              :class="getNodeBadgeClass(node.type, node.refDes)"
              class="stroke-none"
            />
            <text
              x="24"
              y="14"
              text-anchor="middle"
              class="text-[8px] font-mono font-bold uppercase fill-current"
              :class="getNodeBadgeTextClass(node.type, node.refDes)"
            >
              {{ getNodeBadgeLabel(node.type, node.refDes) }}
            </text>

            <!-- RefDes 識別字 -->
            <text
              x="48"
              y="15"
              class="text-[11px] font-mono font-bold fill-sky-600 dark:fill-sky-400"
            >
              {{ node.refDes }}
            </text>

            <!-- 雙軌排版情況：P 軌資訊行 -->
            <g v-if="node.hasP" transform="translate(8, 38)">
              <!-- 穿透元件直通引腳標記 (如 TL1 (3 ➔ 4)) -->
              <text
                v-if="node.isPassThrough"
                x="0"
                y="0"
                class="text-[10px] font-mono fill-emerald-600 dark:fill-emerald-400 font-semibold"
              >
                P+ <tspan class="font-normal">{{ node.pInfo?.throughPin }}</tspan>
              </text>
              <!-- 端點元件引腳標記 (如 TJ1.A6 [DP1] 或 TU2.7) -->
              <text
                v-else
                x="0"
                y="0"
                class="text-[10px] font-mono fill-emerald-600 dark:fill-emerald-400 font-bold"
              >
                {{ node.pInfo?.refPin }}
                <tspan v-if="node.pInfo?.pinName" class="fill-surface-500 dark:fill-surface-400 font-normal">
                  [{{ node.pInfo.pinName }}]
                </tspan>
              </text>
            </g>

            <!-- 雙軌排版情況：N 軌資訊行 -->
            <g v-if="node.hasN" transform="translate(8, 64)">
              <!-- 穿透元件直通引腳標記 (如 TL1 (2 ➔ 1)) -->
              <text
                v-if="node.isPassThrough"
                x="0"
                y="0"
                class="text-[10px] font-mono fill-teal-600 dark:fill-teal-400 font-semibold"
              >
                N- <tspan class="font-normal">{{ node.nInfo?.throughPin }}</tspan>
              </text>
              <!-- 端點元件引腳標記 (如 TJ1.A7 [DN1] 或 TU2.8) -->
              <text
                v-else
                x="0"
                y="0"
                class="text-[10px] font-mono fill-teal-600 dark:fill-teal-400 font-bold"
              >
                {{ node.nInfo?.refPin }}
                <tspan v-if="node.nInfo?.pinName" class="fill-surface-500 dark:fill-surface-400 font-normal">
                  [{{ node.nInfo.pinName }}]
                </tspan>
              </text>
            </g>
          </g>
        </g>
      </svg>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * @file DifferentialTopologySvg.vue
 * @description 差分通道端到端鏈路拓撲 SVG 圖形渲染組件
 * 採用 Dagre 佈局座標與曼哈頓直角階梯折線 (4px 微圓角與電氣焊點)
 * 嚴格遵循 Zero-Custom-CSS 規範，全依賴 Tailwind CSS 與 PrimeVue Aura 設計令牌
 */

import { computed } from 'vue'
import { computeTopologyLayout } from '@/utils/dagreTopologyLayout'

interface Props {
  evidence: Record<string, any> | undefined
}

const props = defineProps<Props>()

/**
 * 依據傳入之 evidence_trail 響應式計算 SVG 佈局幾何屬性
 */
const layout = computed(() => {
  return computeTopologyLayout(props.evidence)
})

/**
 * 取得節點類別縮寫標籤
 */
const getNodeBadgeLabel = (type?: string, refDes?: string): string => {
  const t = (type || '').toLowerCase()
  const r = (refDes || '').toUpperCase()
  if (t.includes('choke') || t.includes('cmc') || r.startsWith('TL') || r.startsWith('L')) return 'CMC'
  if (t.includes('connector') || r.startsWith('J') || r.startsWith('P') || r.startsWith('CN')) return 'CONN'
  if (t.includes('ic') || r.startsWith('U')) return 'IC'
  if (r.startsWith('C')) return 'CAP'
  if (r.startsWith('R')) return 'RES'
  return 'DEV'
}

/**
 * 取得節點徽章背景樣式
 */
const getNodeBadgeClass = (type?: string, refDes?: string): string => {
  const t = (type || '').toLowerCase()
  const r = (refDes || '').toUpperCase()
  if (t.includes('connector') || r.startsWith('J') || r.startsWith('P') || r.startsWith('CN')) {
    return 'fill-amber-500/15'
  }
  if (t.includes('ic') || r.startsWith('U')) {
    return 'fill-purple-500/15'
  }
  if (t.includes('choke') || t.includes('cmc') || r.startsWith('TL') || r.startsWith('L')) {
    return 'fill-sky-500/15'
  }
  return 'fill-surface-500/15'
}

/**
 * 取得節點徽章文字樣式
 */
const getNodeBadgeTextClass = (type?: string, refDes?: string): string => {
  const t = (type || '').toLowerCase()
  const r = (refDes || '').toUpperCase()
  if (t.includes('connector') || r.startsWith('J') || r.startsWith('P') || r.startsWith('CN')) {
    return 'fill-amber-600 dark:fill-amber-400'
  }
  if (t.includes('ic') || r.startsWith('U')) {
    return 'fill-purple-600 dark:fill-purple-400'
  }
  if (t.includes('choke') || t.includes('cmc') || r.startsWith('TL') || r.startsWith('L')) {
    return 'fill-sky-600 dark:fill-sky-400'
  }
  return 'fill-surface-600 dark:fill-surface-400'
}
</script>
