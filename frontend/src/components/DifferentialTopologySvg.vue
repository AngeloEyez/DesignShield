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
        <!-- 1. 曼哈頓階梯折線 (Edges，直接連接至節點 Port 邊界，無箭頭) -->
        <g class="topology-edges">
          <path
            v-for="edge in layout.edges"
            :key="edge.id"
            :d="edge.pathD"
            :class="edge.polarity === 'p' ? 'stroke-emerald-500 dark:stroke-emerald-400' : 'stroke-teal-500 dark:stroke-teal-400'"
            class="fill-none stroke-2 transition-all opacity-85 hover:opacity-100"
          />
        </g>

        <!-- 2. 分支/匯流電氣焊點圓點 (Junction Dots ●，僅在 Net 與 Net 交叉互聯處產生) -->
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

        <!-- 3. 實體網路名稱純文字標籤 (無 tag 外框，纖細微型字體，左對齊防遮擋) -->
        <g class="topology-net-labels">
          <text
            v-for="lbl in layout.netLabels"
            :key="lbl.id"
            :x="lbl.x"
            :y="lbl.y"
            text-anchor="start"
            class="text-[8.5px] font-mono font-normal tracking-tight select-none pointer-events-none"
            :class="lbl.polarity === 'p' ? 'fill-emerald-600 dark:fill-emerald-400/90' : 'fill-teal-600 dark:fill-teal-400/90'"
          >
            {{ lbl.net }}
          </text>
        </g>

        <!-- 4. 元件卡片節點 (Nodes，外框顏色依類別區分，無額外 TAG，邊界具備精緻微型 Port 符號) -->
        <g class="topology-nodes">
          <g
            v-for="node in layout.nodes"
            :key="node.id"
            :transform="`translate(${node.x}, ${node.y})`"
            class="topology-node-group cursor-default"
          >
            <!-- 節點底卡 (外框色彩代表元件類型：Amber 為連接器、Purple 為晶片、Sky 為濾波電感等) -->
            <rect
              :width="node.width"
              :height="node.height"
              rx="4"
              :class="getNodeBorderClass(node.type, node.refDes)"
              class="fill-surface-0 dark:fill-[#161616] stroke-[1.5] shadow-sm transition-colors"
            />

            <!-- 節點 Header：RefDes 識別字 (無額外 TAG 晶片，置頂居中/靠左) -->
            <text
              x="7"
              y="13"
              class="text-[10px] font-mono font-bold"
              :class="getNodeRefDesColor(node.type, node.refDes)"
            >
              {{ node.refDes }}
            </text>

            <!-- A. 穿透元件引腳直通標記 (左右兩側皆有 Port 符號，In/Out Pin 緊貼兩側 Port，中間無多餘標示) -->
            <template v-if="node.isPassThrough">
              <!-- P 軌直通引腳 (依 pin.yOffset 動態定位) -->
              <g v-if="node.hasP" :transform="`translate(0, ${node.pPins[0]?.yOffset || 24})`">
                <!-- 左側輸入 Port 方塊 (4x4) -->
                <rect
                  x="-2"
                  y="-3"
                  width="4"
                  height="4"
                  rx="0.5"
                  class="fill-surface-0 dark:fill-[#161616] stroke-emerald-500 dark:stroke-emerald-400 stroke-[1.2]"
                />
                <!-- 右側輸出 Port 方塊 (4x4) -->
                <rect
                  :x="node.width - 2"
                  y="-3"
                  width="4"
                  height="4"
                  rx="0.5"
                  class="fill-surface-0 dark:fill-[#161616] stroke-emerald-500 dark:stroke-emerald-400 stroke-[1.2]"
                />
                <!-- 左側輸入 pin number (緊鄰左側 Port) -->
                <text x="6" y="3" text-anchor="start" class="text-[9px] font-mono font-semibold fill-emerald-600 dark:fill-emerald-400">
                  {{ node.pPins[0]?.inPin }}
                </text>
                <!-- 右側輸出 pin number (緊鄰右側 Port) -->
                <text :x="node.width - 6" y="3" text-anchor="end" class="text-[9px] font-mono font-semibold fill-emerald-600 dark:fill-emerald-400">
                  {{ node.pPins[0]?.outPin }}
                </text>
              </g>

              <!-- N 軌直通引腳 (依 pin.yOffset 動態定位) -->
              <g v-if="node.hasN" :transform="`translate(0, ${node.nPins[0]?.yOffset || 40})`">
                <!-- 左側輸入 Port 方塊 (4x4) -->
                <rect
                  x="-2"
                  y="-3"
                  width="4"
                  height="4"
                  rx="0.5"
                  class="fill-surface-0 dark:fill-[#161616] stroke-teal-500 dark:stroke-teal-400 stroke-[1.2]"
                />
                <!-- 右側輸出 Port 方塊 (4x4) -->
                <rect
                  :x="node.width - 2"
                  y="-3"
                  width="4"
                  height="4"
                  rx="0.5"
                  class="fill-surface-0 dark:fill-[#161616] stroke-teal-500 dark:stroke-teal-400 stroke-[1.2]"
                />
                <!-- 左側輸入 pin number (緊鄰左側 Port) -->
                <text x="6" y="3" text-anchor="start" class="text-[9px] font-mono font-semibold fill-teal-600 dark:fill-teal-400">
                  {{ node.nPins[0]?.inPin }}
                </text>
                <!-- 右側輸出 pin number (緊鄰右側 Port) -->
                <text :x="node.width - 6" y="3" text-anchor="end" class="text-[9px] font-mono font-semibold fill-teal-600 dark:fill-teal-400">
                  {{ node.nPins[0]?.outPin }}
                </text>
              </g>
            </template>

            <!-- B. 端點元件引腳標記 (支援多 Pin 逐行渲染，port number 緊鄰邊緣 Port 符號，不重複顯示 refDes，已具色彩區別無中括號) -->
            <template v-else>
              <!-- P 軌引腳列表 -->
              <g
                v-for="(pin, pIdx) in (node.pPins && node.pPins.length > 0 ? node.pPins : (node.pInfo ? [node.pInfo] : []))"
                :key="`p_pin_${pIdx}`"
                :transform="`translate(0, ${(pin as any).yOffset || 24})`"
              >
                <!-- 邊緣微型 Port 方塊 (4x4) -->
                <rect
                  :x="node.portDirection === 'out' ? node.width - 2 : -2"
                  y="-3"
                  width="4"
                  height="4"
                  rx="0.5"
                  class="fill-surface-0 dark:fill-[#161616] stroke-emerald-500 dark:stroke-emerald-400 stroke-[1.2]"
                />

                <!-- 情境 1: 輸出端口 (Port 在右側) -> 文字靠右，port number 緊鄰右側 Port，左側接續 port name (保留間距) -->
                <text
                  v-if="node.portDirection === 'out'"
                  :x="node.width - 6"
                  y="3"
                  text-anchor="end"
                  class="text-[9px] font-mono fill-emerald-600 dark:fill-emerald-400 select-none"
                >
                  <tspan
                    v-if="pin.pinName && pin.pinName !== (pin.pinNum || pin.refPin)"
                    class="fill-surface-500 dark:fill-surface-400 font-normal opacity-80"
                  >{{ pin.pinName }}</tspan>
                  <tspan
                    class="font-semibold"
                    :dx="pin.pinName && pin.pinName !== (pin.pinNum || pin.refPin) ? '5' : '0'"
                  >{{ pin.pinNum || pin.refPin }}</tspan>
                </text>

                <!-- 情境 2: 輸入端口 (Port 在左側) -> 文字靠左，port number 緊鄰左側 Port，右側接續 port name (保留間距) -->
                <text
                  v-else
                  x="6"
                  y="3"
                  text-anchor="start"
                  class="text-[9px] font-mono fill-emerald-600 dark:fill-emerald-400 select-none"
                >
                  <tspan class="font-semibold">{{ pin.pinNum || pin.refPin }}</tspan>
                  <tspan
                    v-if="pin.pinName && pin.pinName !== (pin.pinNum || pin.refPin)"
                    class="fill-surface-500 dark:fill-surface-400 font-normal opacity-80"
                    dx="5"
                  >{{ pin.pinName }}</tspan>
                </text>
              </g>

              <!-- N 軌引腳列表 -->
              <g
                v-for="(pin, nIdx) in (node.nPins && node.nPins.length > 0 ? node.nPins : (node.nInfo ? [node.nInfo] : []))"
                :key="`n_pin_${nIdx}`"
                :transform="`translate(0, ${(pin as any).yOffset || 40})`"
              >
                <!-- 邊緣微型 Port 方塊 (4x4) -->
                <rect
                  :x="node.portDirection === 'out' ? node.width - 2 : -2"
                  y="-3"
                  width="4"
                  height="4"
                  rx="0.5"
                  class="fill-surface-0 dark:fill-[#161616] stroke-teal-500 dark:stroke-teal-400 stroke-[1.2]"
                />

                <!-- 情境 1: 輸出端口 (Port 在右側) -> 文字靠右，port number 緊鄰右側 Port，左側接續 port name (保留間距) -->
                <text
                  v-if="node.portDirection === 'out'"
                  :x="node.width - 6"
                  y="3"
                  text-anchor="end"
                  class="text-[9px] font-mono fill-teal-600 dark:fill-teal-400 select-none"
                >
                  <tspan
                    v-if="pin.pinName && pin.pinName !== (pin.pinNum || pin.refPin)"
                    class="fill-surface-500 dark:fill-surface-400 font-normal opacity-80"
                  >{{ pin.pinName }}</tspan>
                  <tspan
                    class="font-semibold"
                    :dx="pin.pinName && pin.pinName !== (pin.pinNum || pin.refPin) ? '5' : '0'"
                  >{{ pin.pinNum || pin.refPin }}</tspan>
                </text>

                <!-- 情境 2: 輸入端口 (Port 在左側) -> 文字靠左，port number 緊鄰左側 Port，右側接續 port name (保留間距) -->
                <text
                  v-else
                  x="6"
                  y="3"
                  text-anchor="start"
                  class="text-[9px] font-mono fill-teal-600 dark:fill-teal-400 select-none"
                >
                  <tspan class="font-semibold">{{ pin.pinNum || pin.refPin }}</tspan>
                  <tspan
                    v-if="pin.pinName && pin.pinName !== (pin.pinNum || pin.refPin)"
                    class="fill-surface-500 dark:fill-surface-400 font-normal opacity-80"
                    dx="5"
                  >{{ pin.pinName }}</tspan>
                </text>
              </g>
            </template>
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
 * 依據元件類型取得節點外框色彩樣式 (外框色彩代表元件類型)
 */
const getNodeBorderClass = (type?: string, refDes?: string): string => {
  const t = (type || '').toLowerCase()
  const r = (refDes || '').toUpperCase()
  if (t.includes('connector') || r.startsWith('J') || r.startsWith('P') || r.startsWith('CN')) {
    return 'stroke-amber-500/80 dark:stroke-amber-400/80'
  }
  if (t.includes('ic') || r.startsWith('U')) {
    return 'stroke-purple-500/80 dark:stroke-purple-400/80'
  }
  if (t.includes('choke') || t.includes('cmc') || r.startsWith('TL') || r.startsWith('L')) {
    return 'stroke-sky-500/80 dark:stroke-sky-400/80'
  }
  if (r.startsWith('C') || r.startsWith('R') || t.includes('passive')) {
    return 'stroke-emerald-500/80 dark:stroke-emerald-400/80'
  }
  return 'stroke-surface-400 dark:stroke-surface-600'
}

/**
 * 依據元件類型取得 RefDes 標題文字顏色樣式
 */
const getNodeRefDesColor = (type?: string, refDes?: string): string => {
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
  return 'fill-sky-600 dark:fill-sky-400'
}
</script>
