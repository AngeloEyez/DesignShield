<template>
  <div class="universal-circuit-topology-svg-container w-full overflow-x-auto select-none py-1">
    <svg
      :viewBox="`0 0 ${layout.width} ${layout.height}`"
      :style="{ minWidth: `${layout.width}px`, height: `${layout.height}px` }"
      class="w-full bg-transparent overflow-visible select-none block"
    >
      <!-- 1. 曼哈頓階梯折線 (Edges，直接連接至節點 Port 邊界；單腳測試點引線採灰色虛線) -->
      <g class="topology-edges">
        <path
          v-for="edge in layout.edges"
          :key="edge.id"
          :d="edge.pathD"
          :stroke-dasharray="edge.isTestPointStub ? '2,2' : undefined"
          :class="
            edge.isTestPointStub
              ? 'stroke-slate-400 dark:stroke-slate-500 stroke-[1.5]'
              : edge.polarity === 'p'
                ? 'stroke-primary-500 stroke-2'
                : 'stroke-emerald-500 stroke-2'
          "
          class="fill-none transition-all opacity-85 hover:opacity-100"
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
          :class="dot.polarity === 'p' ? 'fill-primary-500 stroke-surface-panel' : 'fill-emerald-500 stroke-surface-panel'"
          class="stroke-1"
        />
      </g>

      <!-- 3. 電氣電源/接地符號 (VCC / GND Symbols) -->
      <g class="topology-symbols">
        <template v-for="sym in layout.symbols" :key="sym.id">
          <!-- VCC 電源符號 (箭頭朝上 ▲ + 電壓文字) -->
          <g v-if="sym.type === 'vcc'" :transform="`translate(${sym.x}, ${sym.y})`">
            <line x1="0" y1="10" x2="0" y2="0" class="stroke-amber-500 stroke-1" />
            <polygon points="-4,2 0,-4 4,2" class="fill-amber-500" />
            <text x="7" y="1" class="text-[9px] font-mono font-semibold fill-amber-500 select-none">
              {{ sym.label }}
            </text>
          </g>

          <!-- GND 接地符號 (⏚ 接地三橫線) -->
          <g v-else-if="sym.type === 'gnd'" :transform="`translate(${sym.x}, ${sym.y})`">
            <line x1="0" y1="-10" x2="0" y2="0" class="stroke-surface-400 dark:stroke-surface-500 stroke-1" />
            <line x1="-6" y1="0" x2="6" y2="0" class="stroke-surface-400 dark:stroke-surface-500 stroke-1.5" />
            <line x1="-4" y1="3" x2="4" y2="3" class="stroke-surface-400 dark:stroke-surface-500 stroke-1.5" />
            <line x1="-2" y1="6" x2="2" y2="6" class="stroke-surface-400 dark:stroke-surface-500 stroke-1.5" />
            <text x="9" y="5" class="text-[8.5px] font-mono fill-vscode-textSecondary dark:fill-vscode-textMuted select-none">
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
          :class="lbl.polarity === 'p' ? 'fill-primary dark:fill-primary-400 font-medium' : 'fill-emerald-600 dark:fill-emerald-400 font-medium'"
        >
          {{ lbl.net }}
        </text>
      </g>

      <!-- 5. 元件卡片節點與單腳測試點符號 -->
      <g class="topology-nodes">
        <g
          v-for="node in layout.nodes"
          :key="node.id"
          :transform="`translate(${node.x}, ${node.y})`"
          class="topology-node-group cursor-default transition-opacity"
          :class="{ 'opacity-65': node.isMounted === false }"
        >
          <!-- 5A. 單腳測試點專用電子線路符號 (空心測試環 ○ + 位號，無矩形方框、無腳位名稱、統一灰色) -->
          <template v-if="node.isTestPoint && node.isSinglePin">
            <circle
              :cx="Math.round(node.width / 2)"
              :cy="node.tpDirection === 'up' ? 14 : 4"
              r="3.5"
              class="test-point-symbol fill-surface-panel stroke-slate-400 dark:stroke-slate-500 stroke-[1.5]"
            />
            <text
              :x="Math.round(node.width / 2)"
              :y="node.tpDirection === 'up' ? 7 : 18"
              text-anchor="middle"
              class="text-[9px] font-mono font-medium fill-slate-500 dark:fill-slate-400 select-none"
            >
              {{ node.refDes }}
            </text>
          </template>

          <!-- 5B. 一般多引腳元件卡片 (IC / Connector / 被動元件 / CMC) -->
          <template v-else>
            <!-- 節點底卡 (外框色彩代表元件層級；未上件或缺失 PartDB 時採用 3,3 虛線邊框) -->
            <rect
              :width="node.width"
              :height="node.height"
              rx="4"
              :stroke-dasharray="node.isMounted === false || node.partdbMissing ? '3,3' : undefined"
              :class="getNodeBorderClass(node.category, node.refDes, node.isTestPoint)"
              class="fill-surface-panel stroke-[1.5] transition-colors"
            />

            <!-- 節點 Header：RefDes 識別字 (置頂靠左) + 未上件標註 [X]/[P]/[M] (淡灰色) -->
            <text
              x="7"
              y="13"
              class="text-[10px] font-mono font-semibold select-none"
              :class="getNodeRefDesColor(node.category, node.refDes, node.isTestPoint)"
            >
              {{ node.refDes }}
              <tspan
                v-if="node.isMounted === false && node.bom !== 'NOBOM'"
                class="unmounted-x-tag fill-vscode-textSecondary dark:fill-vscode-textMuted font-medium text-[9px]"
                dx="2"
              >[{{ node.bom && ['P', 'M'].includes(node.bom) ? node.bom : 'X' }}]</tspan>
            </text>

            <!-- PartDB 缺失標註 (虛線方塊下方；此元件穿透引腳配對未知，僅顯示、不參與導通判定) -->
            <text
              v-if="node.partdbMissing"
              x="0"
              :y="node.height + 11"
              class="partdb-missing-tag text-[8.5px] font-mono font-medium fill-amber-600 dark:fill-amber-400 select-none"
            >
              PartDB 缺失
            </text>

            <!-- 節點 Value 或 Part Number (次要規格資訊) -->
            <text
              v-if="node.value"
              x="7"
              :y="node.height - 6"
              class="text-[8.5px] font-mono fill-vscode-textSecondary dark:fill-vscode-textMuted select-none"
            >
              {{ node.value }}
            </text>

            <!-- 引腳微型 Port 符號 (4x4 方塊) 與引腳編號/名稱標示 (單引腳零件不標註引腳號碼/名稱) -->
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
                :class="port.polarity === 'n' || (port.pinName && /n|dn|-/i.test(port.pinName)) ? 'stroke-emerald-600 dark:stroke-emerald-500' : 'stroke-primary dark:stroke-primary-500'"
                class="fill-surface-panel stroke-[1.2]"
              />

              <template v-if="!node.isSinglePin">
                <!-- 引腳標示 (水平輸入端：文字靠左) -->
                <text
                  v-if="port.orientation === 'left'"
                  x="6"
                  y="3"
                  text-anchor="start"
                  class="text-[9px] font-mono select-none"
                  :class="port.polarity === 'n' || (port.pinName && /n|dn|-/i.test(port.pinName)) ? 'fill-emerald-600 dark:fill-emerald-400' : 'fill-primary dark:fill-primary-400'"
                >
                  <tspan class="font-semibold">{{ port.pinNumber }}</tspan>
                  <tspan
                    v-if="port.pinName && port.pinName !== port.pinNumber"
                    class="fill-vscode-textSecondary dark:fill-vscode-textMuted font-normal"
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
                  :class="port.polarity === 'n' || (port.pinName && /n|dn|-/i.test(port.pinName)) ? 'fill-emerald-600 dark:fill-emerald-400' : 'fill-primary dark:stroke-primary-400 fill-primary-400'"
                >
                  <tspan
                    v-if="port.pinName && port.pinName !== port.pinNumber"
                    class="fill-vscode-textSecondary dark:fill-vscode-textMuted font-normal"
                    dx="-4"
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
                  class="text-[8px] font-mono fill-vscode-textSecondary dark:fill-vscode-textMuted select-none"
                >
                  {{ port.pinNumber }}
                </text>
              </template>
            </g>
          </template>
        </g>
      </g>
    </svg>
  </div>
</template>

<script setup lang="ts">
/**
 * @file UniversalCircuitTopologySvg.vue
 * @description 通用電路通道鏈路拓撲 SVG 圖形渲染組件 (2026 雙主題低飽和版)
 * 採用通用分層路徑帶座標與曼哈頓直角階梯折線，支援單腳測試點符號渲染，遵循 Zero-Custom-CSS 原則
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
 * 依據元件類別取得節點外框色彩樣式 (2 色低飽和：主晶片/連接器用 Slate-Blue，被動元件與測試點用中性石色)
 */
const getNodeBorderClass = (category?: string, refDes?: string, isTestPoint?: boolean): string => {
  if (isTestPoint) {
    return 'stroke-slate-400 dark:stroke-slate-500'
  }
  const c = (category || '').toLowerCase()
  const r = (refDes || '').toUpperCase()
  if (c.includes('ic') || c.includes('connector') || r.startsWith('U') || r.startsWith('J') || r.startsWith('P') || r.startsWith('CN')) {
    return 'stroke-slate-700/85 dark:stroke-primary-400/80'
  }
  return 'stroke-surface-400 dark:stroke-surface-500'
}

/**
 * 依據元件類別取得 RefDes 標題文字色彩樣式
 */
const getNodeRefDesColor = (category?: string, refDes?: string, isTestPoint?: boolean): string => {
  if (isTestPoint) {
    return 'fill-slate-500 dark:fill-slate-400'
  }
  const c = (category || '').toLowerCase()
  const r = (refDes || '').toUpperCase()
  if (c.includes('ic') || c.includes('connector') || r.startsWith('U') || r.startsWith('J') || r.startsWith('P') || r.startsWith('CN')) {
    return 'fill-slate-800 dark:fill-primary-400'
  }
  return 'fill-vscode-textHeading'
}
</script>
