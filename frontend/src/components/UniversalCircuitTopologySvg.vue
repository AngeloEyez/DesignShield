<template>
  <div class="universal-circuit-topology-svg-container w-full overflow-x-auto select-none py-1">
    <svg
      :viewBox="`0 0 ${layout.width} ${layout.height}`"
      :style="{ minWidth: `${layout.width}px`, height: `${layout.height}px` }"
      class="w-full bg-transparent overflow-visible select-none block"
    >
      <!-- 1. 曼哈頓階梯折線 (Edges，直接連接至節點 Port 邊界，無多餘箭頭) -->
      <g class="topology-edges">
        <path
          v-for="edge in layout.edges"
          :key="edge.id"
          :d="edge.pathD"
          :class="edge.polarity === 'p' ? 'stroke-emerald-500 dark:stroke-emerald-400' : 'stroke-teal-500 dark:stroke-teal-400'"
          class="fill-none stroke-2 transition-all opacity-85 hover:opacity-100"
        />
      </g>

      <!-- 2. 分支/匯流電氣焊點圓點 (Junction Dots ●，僅在分支導線與主幹交會處打點) -->
      <g class="topology-junction-dots">
        <circle
          v-for="dot in layout.junctionDots"
          :key="dot.id"
          :cx="dot.x"
          :cy="dot.y"
          r="3"
          :class="dot.polarity === 'p' ? 'fill-emerald-500 dark:fill-emerald-400 stroke-surface-50 dark:stroke-[#141414]' : 'fill-teal-500 dark:fill-teal-400 stroke-surface-50 dark:stroke-[#141414]'"
          class="stroke-1"
        />
      </g>

      <!-- 3. 電氣電源/接地符號 (VCC / GND Symbols) -->
      <g class="topology-symbols">
        <template v-for="sym in layout.symbols" :key="sym.id">
          <!-- VCC 電源符號 (箭頭朝上 ▲ + 電壓文字) -->
          <g v-if="sym.type === 'vcc'" :transform="`translate(${sym.x}, ${sym.y})`">
            <line x1="0" y1="10" x2="0" y2="0" class="stroke-rose-500 dark:stroke-rose-400 stroke-1" />
            <polygon points="-4,2 0,-4 4,2" class="fill-rose-500 dark:fill-rose-400" />
            <text x="7" y="1" class="text-[9px] font-mono font-semibold fill-rose-600 dark:fill-rose-400 select-none">
              {{ sym.label }}
            </text>
          </g>

          <!-- GND 接地符號 (⏚ 接地三橫線) -->
          <g v-else-if="sym.type === 'gnd'" :transform="`translate(${sym.x}, ${sym.y})`">
            <line x1="0" y1="-10" x2="0" y2="0" class="stroke-surface-500 dark:stroke-surface-400 stroke-1" />
            <line x1="-6" y1="0" x2="6" y2="0" class="stroke-surface-500 dark:stroke-surface-400 stroke-1.5" />
            <line x1="-4" y1="3" x2="4" y2="3" class="stroke-surface-500 dark:stroke-surface-400 stroke-1.5" />
            <line x1="-2" y1="6" x2="2" y2="6" class="stroke-surface-500 dark:stroke-surface-400 stroke-1.5" />
            <text x="9" y="5" class="text-[8.5px] font-mono fill-surface-500 dark:fill-surface-400 select-none">
              {{ sym.label }}
            </text>
          </g>
        </template>
      </g>

      <!-- 4. 實體網路名稱純文字標籤 (無 tag 外框，纖細微型字體，置中對齊導線防遮擋) -->
      <g class="topology-net-labels">
        <text
          v-for="lbl in layout.netLabels"
          :key="lbl.id"
          :x="lbl.x"
          :y="lbl.y"
          text-anchor="middle"
          class="text-[8.5px] font-mono font-normal tracking-tight select-none pointer-events-none"
          :class="lbl.polarity === 'p' ? 'fill-emerald-600 dark:fill-emerald-400/90' : 'fill-teal-600 dark:fill-teal-400/90'"
        >
          {{ lbl.net }}
        </text>
      </g>

      <!-- 5. 元件卡片節點 (Nodes，外框顏色依類別區分，未上件時透明度 65%、虛線外框並標註 [X]/[P]/[M]) -->
      <g class="topology-nodes">
        <g
          v-for="node in layout.nodes"
          :key="node.id"
          :transform="`translate(${node.x}, ${node.y})`"
          class="topology-node-group cursor-default transition-opacity"
          :class="{ 'opacity-65': node.isMounted === false }"
        >
          <!-- 節點底卡 (外框色彩代表元件類型；未上件時採用 3,3 虛線邊框) -->
          <rect
            :width="node.width"
            :height="node.height"
            rx="4"
            :stroke-dasharray="node.isMounted === false ? '3,3' : undefined"
            :class="getNodeBorderClass(node.category, node.refDes)"
            class="fill-surface-0 dark:fill-[#161616] stroke-[1.5] shadow-sm transition-colors"
          />

          <!-- 節點 Header：RefDes 識別字 (置頂靠左) + 未上件標註 [X]/[P]/[M] (淡灰色) -->
          <text
            x="7"
            y="13"
            class="text-[10px] font-mono font-bold select-none"
            :class="getNodeRefDesColor(node.category, node.refDes)"
          >
            {{ node.refDes }}
            <tspan
              v-if="node.isMounted === false"
              class="unmounted-x-tag fill-surface-400 dark:fill-surface-500 font-medium text-[9px]"
              dx="2"
            >[{{ node.bom && ['P', 'M'].includes(node.bom) ? node.bom : 'X' }}]</tspan>
          </text>

          <!-- 節點 Value 或 Part Number (次要規格資訊) -->
          <text
            v-if="node.value"
            x="7"
            :y="node.height - 6"
            class="text-[8.5px] font-mono fill-surface-500 dark:fill-surface-400 select-none"
          >
            {{ node.value }}
          </text>

          <!-- 引腳微型 Port 符號 (4x4 方塊) 與引腳編號/名稱標示 -->
          <g
            v-for="port in node.ports"
            :key="port.id"
            :transform="`translate(${port.relX}, ${port.relY})`"
          >
            <!-- Port 4x4 方塊 -->
            <rect
              x="-2"
              y="-2"
              width="4"
              height="4"
              rx="0.5"
              :class="port.polarity === 'n' || (port.pinName && /n|dn|-/i.test(port.pinName)) ? 'stroke-teal-500 dark:stroke-teal-400' : 'stroke-emerald-500 dark:stroke-emerald-400'"
              class="fill-surface-0 dark:fill-[#161616] stroke-[1.2]"
            />

            <!-- 引腳標示 (水平輸入端：文字靠左) -->
            <text
              v-if="port.orientation === 'left'"
              x="6"
              y="3"
              text-anchor="start"
              class="text-[9px] font-mono select-none"
              :class="port.polarity === 'n' || (port.pinName && /n|dn|-/i.test(port.pinName)) ? 'fill-teal-600 dark:fill-teal-400' : 'fill-emerald-600 dark:fill-emerald-400'"
            >
              <tspan class="font-semibold">{{ port.pinNumber }}</tspan>
              <tspan
                v-if="port.pinName && port.pinName !== port.pinNumber"
                class="fill-surface-500 dark:fill-surface-400 font-normal opacity-80"
                dx="4"
              >{{ port.pinName }}</tspan>
            </text>

            <!-- 引腳標示 (水平輸出端：文字靠右) -->
            <text
              v-else-if="port.orientation === 'right'"
              x="-6"
              y="3"
              text-anchor="end"
              class="text-[9px] font-mono select-none"
              :class="port.polarity === 'n' || (port.pinName && /n|dn|-/i.test(port.pinName)) ? 'fill-teal-600 dark:fill-teal-400' : 'fill-emerald-600 dark:fill-emerald-400'"
            >
              <tspan
                v-if="port.pinName && port.pinName !== port.pinNumber"
                class="fill-surface-500 dark:fill-surface-400 font-normal opacity-80"
              >{{ port.pinName }}</tspan>
              <tspan
                class="font-semibold"
                :dx="port.pinName && port.pinName !== port.pinNumber ? '4' : '0'"
              >{{ port.pinNumber }}</tspan>
            </text>

            <!-- 引腳標示 (垂直頂部/底部) -->
            <text
              v-else-if="port.orientation === 'top' || port.orientation === 'bottom'"
              x="0"
              :y="port.orientation === 'top' ? 10 : -6"
              text-anchor="middle"
              class="text-[8px] font-mono fill-surface-500 dark:fill-surface-400 select-none"
            >
              {{ port.pinNumber }}
            </text>
          </g>
        </g>
      </g>
    </svg>
  </div>
</template>

<script setup lang="ts">
/**
 * @file UniversalCircuitTopologySvg.vue
 * @description 通用電路通道鏈路拓撲 SVG 圖形渲染組件
 * 採用通用圖論座標與曼哈頓直角階梯折線 (4px 微圓角、分支電氣焊點與 VCC/GND 符號)
 * 嚴格遵循 Zero-Custom-CSS 規範，全依賴 Tailwind CSS 與 PrimeVue Aura 設計令牌
 */

import { computed } from 'vue'
import { computeUniversalTopologyLayout } from '@/utils/universalTopologyLayout'

interface Props {
  evidence: Record<string, any> | undefined
}

const props = defineProps<Props>()

/**
 * 依據傳入之 evidence_trail 響應式計算通用 SVG 佈局幾何屬性
 */
const layout = computed(() => {
  return computeUniversalTopologyLayout(props.evidence)
})

/**
 * 依據元件類別取得節點外框色彩樣式
 */
const getNodeBorderClass = (category?: string, refDes?: string): string => {
  const c = (category || '').toLowerCase()
  const r = (refDes || '').toUpperCase()
  if (c.includes('connector') || r.startsWith('J') || r.startsWith('P') || r.startsWith('CN')) {
    return 'stroke-amber-500/80 dark:stroke-amber-400/80'
  }
  if (c.includes('ic') || r.startsWith('U')) {
    return 'stroke-purple-500/80 dark:stroke-purple-400/80'
  }
  if (c.includes('choke') || c.includes('cmc') || c.includes('inductor') || r.startsWith('TL') || r.startsWith('L')) {
    return 'stroke-sky-500/80 dark:stroke-sky-400/80'
  }
  if (c.includes('resistor') || c.includes('capacitor') || c.includes('passive') || r.startsWith('C') || r.startsWith('R')) {
    return 'stroke-emerald-500/80 dark:stroke-emerald-400/80'
  }
  return 'stroke-surface-400 dark:stroke-surface-600'
}

/**
 * 依據元件類別取得 RefDes 標題文字色彩樣式
 */
const getNodeRefDesColor = (category?: string, refDes?: string): string => {
  const c = (category || '').toLowerCase()
  const r = (refDes || '').toUpperCase()
  if (c.includes('connector') || r.startsWith('J') || r.startsWith('P') || r.startsWith('CN')) {
    return 'fill-amber-600 dark:fill-amber-400'
  }
  if (c.includes('ic') || r.startsWith('U')) {
    return 'fill-purple-600 dark:fill-purple-400'
  }
  if (c.includes('choke') || c.includes('cmc') || c.includes('inductor') || r.startsWith('TL') || r.startsWith('L')) {
    return 'fill-sky-600 dark:fill-sky-400'
  }
  return 'fill-sky-600 dark:fill-sky-400'
}
</script>
