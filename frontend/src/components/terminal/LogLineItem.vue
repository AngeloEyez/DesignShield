<template>
  <div
    ref="itemRef"
    class="flex flex-col px-1.5 py-[2px] rounded font-mono text-xs leading-snug transition-colors hover:bg-surface-800/40 break-all"
  >
    <div
      class="flex items-baseline gap-1.5 flex-wrap"
      :class="{ 'cursor-pointer': hasDetails }"
      @click="toggleExpand"
    >
      <!-- 1. 時間戳記 (月日與時間) -->
      <span class="text-surface-500 text-[10px] shrink-0 tabular-nums">[{{ formattedTime }}]</span>

      <!-- 2. 第一標籤：Timeline 工作流主要步驟 -->
      <span
        class="text-[10px] font-medium px-1 py-0.2 rounded shrink-0 leading-none inline-flex items-center"
        :class="getStepTagClass(log.step_name)"
        :title="log.step_name"
      >
        [{{ formatStepTag(log.step_name) }}]
      </span>

      <!-- 3. 第二標籤：用途分類 (LLM, DB, VLM, PARSER, GRAPH, FILE, HEURISTIC 等) -->
      <span
        v-if="log.category"
        class="text-[10px] font-medium px-1 py-0.2 rounded shrink-0 leading-none inline-flex items-center"
        :class="getCategoryTagClass(log.category)"
        :title="`分類: ${log.category}`"
      >
        [{{ log.category }}]
      </span>

      <!-- 4. 日誌分級 (INFO, WARN, ERROR, DEBUG) -->
      <span
        class="text-[10px] font-bold px-1 py-0.2 rounded shrink-0 tracking-wide leading-none inline-flex items-center"
        :class="getLevelBadgeClass(normalizedLevel)"
      >
        {{ normalizedLevel }}
      </span>

      <!-- 5. 步驟狀態 (若有 status 欄位) -->
      <span
        v-if="log.status && !log.level"
        class="text-[10px] font-bold px-1 py-0.2 rounded shrink-0 text-surface-400 bg-surface-800/60 leading-none inline-flex items-center"
      >
        {{ log.status }}
      </span>

      <!-- 6. 日誌訊息內容 -->
      <span class="flex-1" :class="getMessageClass(normalizedLevel)">
        {{ log.message }}
      </span>

      <!-- 7. 展開詳細資訊按鈕 (移除文字，僅保留微型箭頭圖示) -->
      <button
        v-if="hasDetails"
        type="button"
        class="details-toggle-btn w-4 h-4 p-0 bg-[#1e1e1e] border border-[#333333] text-surface-400 hover:text-white rounded cursor-pointer inline-flex items-center justify-center hover:bg-[#2a2d2e] transition-colors shrink-0"
        :class="{ 'border-sky-500/50 text-sky-300': isExpanded }"
        :title="isExpanded ? '收合詳細資料' : '查看完整 LLM 查詢/錯誤細節'"
        @click.stop="toggleExpand"
      >
        <i :class="isExpanded ? 'pi pi-chevron-up' : 'pi pi-chevron-down'" class="text-[9px]"></i>
      </button>
    </div>

    <!-- 展開之結構化詳細資訊區塊 (VS Code 摺疊輸出風格) -->
    <div
      v-if="hasDetails && isExpanded"
      class="details-box mt-1.5 ml-6 bg-[#1e1e1e] border border-[#333333] border-l-2 border-l-sky-400 rounded p-2.5"
    >
      <div class="flex justify-between items-center mb-1.5 border-b border-[#333333] pb-1">
        <span class="text-xs text-[#858585] font-semibold flex items-center">
          <i class="pi pi-file-code mr-1"></i>
          結構化詳細內容 (Payload / Trace)
        </span>
        <button
          type="button"
          class="bg-[#252526] border border-[#333333] text-[#cccccc] text-[11px] px-1.5 py-0.5 rounded cursor-pointer hover:text-white hover:bg-[#2a2d2e] transition-colors inline-flex items-center"
          @click.stop="copyDetails"
          :title="copySuccess ? '已複製！' : '複製內容'"
        >
          <i :class="copySuccess ? 'pi pi-check' : 'pi pi-copy'" class="mr-1"></i>
          <span>{{ copySuccess ? '已複製' : '複製' }}</span>
        </button>
      </div>

      <!-- 若包含 prompt 與 response 則特別友善排版 -->
      <div v-if="detailsObj && (detailsObj.prompt || detailsObj.response)" class="flex flex-col gap-1.5">
        <div v-if="detailsObj.prompt" class="flex flex-col gap-1">
          <span class="text-[10px] font-semibold px-1 py-0.5 rounded w-fit bg-sky-500/20 text-sky-400">Prompt 提示詞</span>
          <pre class="m-0 text-xs text-surface-300 whitespace-pre-wrap break-all max-h-60 overflow-y-auto leading-relaxed">{{ detailsObj.prompt }}</pre>
        </div>
        <div v-if="detailsObj.response" class="flex flex-col gap-1">
          <span class="text-[10px] font-semibold px-1 py-0.5 rounded w-fit bg-pink-500/20 text-pink-400">LLM 回應</span>
          <pre class="m-0 text-xs text-surface-300 whitespace-pre-wrap break-all max-h-60 overflow-y-auto leading-relaxed">{{ formatPayload(detailsObj.response) }}</pre>
        </div>
      </div>
      <pre v-else class="m-0 text-xs text-surface-300 whitespace-pre-wrap break-all max-h-60 overflow-y-auto leading-relaxed">{{ formatPayload(log.details) }}</pre>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * @file LogLineItem.vue
 * @description VS Code 終端風格緊密日誌單行元件，支援月日時間格式、工作流與用途雙標籤、四級分級與展開/收合 details
 */

import { ref, computed, nextTick } from 'vue'
import type { LogEntry } from '@/types/task'

interface Props {
  log: LogEntry
}

const props = defineProps<Props>()

const itemRef = ref<HTMLElement | null>(null)
const isExpanded = ref(false)
const copySuccess = ref(false)

/**
 * 切換詳細資訊展開/收合狀態
 * 當展開時，若該行位於視窗底部或下方被遮擋，智慧平滑捲動確保展開內容可視
 */
const toggleExpand = () => {
  if (hasDetails.value) {
    isExpanded.value = !isExpanded.value
    if (isExpanded.value) {
      nextTick(() => {
        if (itemRef.value && typeof itemRef.value.scrollIntoView === 'function') {
          itemRef.value.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
        }
      })
    }
  }
}

/**
 * 格式化時間 (顯示月日與時間 MM-DD HH:mm:ss)
 */
const formattedTime = computed(() => {
  if (props.log.display_time) {
    return props.log.display_time
  }
  const raw = props.log.timestamp || ''
  if (!raw) return ''
  if (raw.includes('T') || raw.includes('-')) {
    try {
      const d = new Date(raw)
      if (!isNaN(d.getTime())) {
        const m = String(d.getMonth() + 1).padStart(2, '0')
        const day = String(d.getDate()).padStart(2, '0')
        const h = String(d.getHours()).padStart(2, '0')
        const min = String(d.getMinutes()).padStart(2, '0')
        const s = String(d.getSeconds()).padStart(2, '0')
        return `${m}-${day} ${h}:${min}:${s}`
      }
    } catch {
      // 降級使用原始字串
    }
  }
  return raw
})

/**
 * 正規化等級字串
 */
const normalizedLevel = computed(() => {
  if (props.log.level) {
    const lvl = props.log.level.toUpperCase()
    if (lvl === 'WARNING') return 'WARN'
    return lvl
  }
  if (props.log.status === 'FAILED') return 'ERROR'
  if (props.log.status === 'PROCESSING') return 'INFO'
  return 'INFO'
})

/**
 * 是否有結構化詳細資料
 */
const hasDetails = computed(() => {
  const d = props.log.details
  if (d === null || d === undefined) return false
  if (typeof d === 'object') {
    return Object.keys(d).length > 0
  }
  if (typeof d === 'string') {
    return d.trim().length > 0
  }
  return false
})

/**
 * 解析為物件格式 (若適用)
 */
const detailsObj = computed(() => {
  const d = props.log.details
  if (typeof d === 'object' && d !== null) {
    return d as Record<string, any>
  }
  return null
})

/**
 * 格式化輸出資料
 */
const formatPayload = (val: any): string => {
  if (typeof val === 'string') return val
  try {
    return JSON.stringify(val, null, 2)
  } catch {
    return String(val)
  }
}

/**
 * 複製詳細資料
 */
const copyDetails = async () => {
  const text = formatPayload(props.log.details)
  try {
    await navigator.clipboard.writeText(text)
    copySuccess.value = true
    setTimeout(() => {
      copySuccess.value = false
    }, 2000)
  } catch (err) {
    console.error('複製失敗:', err)
  }
}

/**
 * 第一標籤 (Timeline 步驟) 顯示
 */
const formatStepTag = (step?: string): string => {
  return step || 'TASK'
}

/**
 * 第一標籤 class 顏色 (低飽和暗色沉浸)
 */
const getStepTagClass = (step: string): string => {
  if (!step) return 'text-surface-400 bg-surface-800/40 border border-surface-700/40'
  if (step.includes('UNPACK')) return 'text-sky-300/70 bg-sky-950/30 border border-sky-800/30'
  if (step.includes('PARSE')) return 'text-violet-300/70 bg-violet-950/30 border border-violet-800/30'
  if (step.includes('RULE')) return 'text-amber-300/70 bg-amber-950/30 border border-amber-800/30'
  if (step.includes('HEURISTIC')) return 'text-amber-300/70 bg-amber-950/30 border border-amber-800/30'
  if (step.includes('LLM')) return 'text-purple-300/70 bg-purple-950/30 border border-purple-800/30'
  return 'text-emerald-300/70 bg-emerald-950/30 border border-emerald-800/30'
}

/**
 * 第二標籤 (用途分類) class 顏色 (低飽和暗色沉浸)
 */
const getCategoryTagClass = (cat: string): string => {
  const c = cat.toUpperCase()
  if (c === 'LLM') return 'text-purple-300/80 bg-purple-950/40 border border-purple-800/40'
  if (c === 'DB') return 'text-emerald-300/80 bg-emerald-950/40 border border-emerald-800/40'
  if (c === 'VLM') return 'text-purple-300/80 bg-purple-950/40 border border-purple-800/40'
  if (c === 'PARSER') return 'text-teal-300/80 bg-teal-950/40 border border-teal-800/40'
  if (c === 'GRAPH') return 'text-indigo-300/80 bg-indigo-950/40 border border-indigo-800/40'
  if (c === 'FILE') return 'text-sky-300/80 bg-sky-950/40 border border-sky-800/40'
  if (c === 'HEURISTIC') return 'text-amber-300/80 bg-amber-950/40 border border-amber-800/40'
  return 'text-surface-400 bg-surface-800/40 border border-surface-700/40'
}

const getLevelBadgeClass = (lvl: string): string => {
  if (lvl === 'ERROR') return 'text-rose-300/90 bg-rose-950/50 border border-rose-800/40'
  if (lvl === 'WARN') return 'text-amber-300/80 bg-amber-950/40 border border-amber-800/30'
  if (lvl === 'DEBUG') return 'text-zinc-400 bg-zinc-800/50 border border-zinc-700/40'
  return 'text-sky-300/80 bg-sky-950/40 border border-sky-800/30'
}

const getMessageClass = (lvl: string): string => {
  if (lvl === 'ERROR') return 'text-red-300 font-medium'
  if (lvl === 'WARN') return 'text-yellow-300'
  if (lvl === 'DEBUG') return 'text-surface-400'
  return 'text-surface-200'
}
</script>
