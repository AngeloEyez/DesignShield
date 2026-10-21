<template>
  <div
    ref="itemRef"
    class="flex flex-col px-1.5 py-[2px] rounded font-mono text-xs leading-snug transition-colors hover:bg-surface-hover/50 break-all"
  >
    <div
      class="flex items-baseline gap-1.5 flex-wrap"
      :class="{ 'cursor-pointer': hasDetails }"
      @click="toggleExpand"
    >
      <!-- 1. 時間戳記 (月日與時間) -->
      <span class="text-vscode-textMuted text-[10px] shrink-0 tabular-nums">[{{ formattedTime }}]</span>

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
        class="text-[10px] font-semibold px-1 py-0.2 rounded shrink-0 tracking-wide leading-none inline-flex items-center"
        :class="getLevelBadgeClass(normalizedLevel)"
      >
        {{ normalizedLevel }}
      </span>

      <!-- 5. 步驟狀態 (若有 status 欄位) -->
      <span
        v-if="log.status && !log.level"
        class="text-[10px] font-semibold px-1 py-0.2 rounded shrink-0 text-vscode-textMuted bg-surface-hover border border-surface-border leading-none inline-flex items-center"
      >
        {{ log.status }}
      </span>

      <!-- 6. 日誌訊息內容 -->
      <span class="flex-1" :class="getMessageClass(normalizedLevel)">
        {{ log.message }}
      </span>

      <!-- 7. 展開詳細資訊按鈕 (僅保留微型箭頭圖示 + Tooltip) -->
      <button
        v-if="hasDetails"
        type="button"
        v-tooltip.left="isExpanded ? '收合詳細資料' : '查看完整 LLM 查詢/錯誤細節'"
        class="details-toggle-btn w-4 h-4 p-0 bg-surface-panel border border-surface-border text-vscode-textMuted hover:text-vscode-textHeading rounded cursor-pointer inline-flex items-center justify-center hover:bg-surface-hover transition-colors shrink-0"
        :class="{ 'border-primary/50 text-primary': isExpanded }"
        @click.stop="toggleExpand"
      >
        <i :class="isExpanded ? 'pi pi-chevron-up' : 'pi pi-chevron-down'" class="text-[9px]"></i>
      </button>
    </div>

    <!-- 展開之結構化詳細資訊區塊 -->
    <div
      v-if="hasDetails && isExpanded"
      class="details-box mt-1.5 ml-6 bg-surface-panel border border-surface-border border-l-2 border-l-primary rounded p-2"
    >
      <div class="flex justify-between items-center mb-1.5 border-b border-surface-border pb-1">
        <span class="text-[11px] text-vscode-textMuted font-semibold flex items-center">
          <i class="pi pi-file-code mr-1 text-primary"></i>
          結構化詳細內容 (Payload / Trace)
        </span>
        <button
          type="button"
          v-tooltip.left="copySuccess ? '已複製！' : '複製內容'"
          class="bg-surface-card border border-surface-border text-vscode-textSecondary text-[10px] px-1.5 py-0.5 rounded cursor-pointer hover:text-vscode-textHeading hover:bg-surface-hover transition-colors inline-flex items-center gap-1"
          @click.stop="copyDetails"
        >
          <i :class="copySuccess ? 'pi pi-check text-emerald-500' : 'pi pi-copy'"></i>
          <span>{{ copySuccess ? '已複製' : '複製' }}</span>
        </button>
      </div>

      <!-- 若包含 prompt 與 response 則特別友善排版 -->
      <div v-if="detailsObj && (detailsObj.prompt || detailsObj.response)" class="flex flex-col gap-1.5">
        <div v-if="detailsObj.prompt" class="flex flex-col gap-1">
          <span class="text-[10px] font-semibold px-1.5 py-0.2 rounded w-fit bg-primary/10 text-primary">Prompt 提示詞</span>
          <pre class="m-0 text-xs text-vscode-textMain whitespace-pre-wrap break-all max-h-60 overflow-y-auto leading-relaxed">{{ detailsObj.prompt }}</pre>
        </div>
        <div v-if="detailsObj.response" class="flex flex-col gap-1">
          <span class="text-[10px] font-semibold px-1.5 py-0.2 rounded w-fit bg-surface-card text-vscode-textSecondary border border-surface-border">LLM 回應</span>
          <pre class="m-0 text-xs text-vscode-textMain whitespace-pre-wrap break-all max-h-60 overflow-y-auto leading-relaxed">{{ formatPayload(detailsObj.response) }}</pre>
        </div>
      </div>
      <pre v-else class="m-0 text-xs text-vscode-textMain whitespace-pre-wrap break-all max-h-60 overflow-y-auto leading-relaxed">{{ formatPayload(log.details) }}</pre>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * @file LogLineItem.vue
 * @description 終端緊密日誌單行元件 (2026 雙主題 2色低飽和版)，支援月日時間格式、工作流與用途雙標籤、四級分級與展開/收合 details
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
 * 第一標籤 class 顏色 (中性石色標籤，雙主題高對比度)
 */
const getStepTagClass = (_step: string): string => {
  return 'text-vscode-textSecondary bg-surface-hover/80 border border-surface-border'
}

/**
 * 第二標籤 (用途分類) class 顏色 (AI/圖譜核心為 Primary Slate-Blue，其餘為中性石色)
 */
const getCategoryTagClass = (cat: string): string => {
  const c = cat.toUpperCase()
  if (c === 'LLM' || c === 'VLM' || c === 'GRAPH') {
    return 'text-primary font-medium bg-primary/10 border border-primary/25'
  }
  return 'text-vscode-textSecondary bg-surface-hover/80 border border-surface-border'
}

const getLevelBadgeClass = (lvl: string): string => {
  if (lvl === 'ERROR') return 'text-red-600 dark:text-red-400 font-semibold bg-red-500/15 border border-red-500/30'
  if (lvl === 'WARN') return 'text-amber-600 dark:text-amber-400 font-semibold bg-amber-500/15 border border-amber-500/30'
  if (lvl === 'DEBUG') return 'text-vscode-textMuted bg-surface-hover/80 border border-surface-border'
  return 'text-primary font-semibold bg-primary/10 border border-primary/25'
}

const getMessageClass = (lvl: string): string => {
  if (lvl === 'ERROR') return 'text-red-600 dark:text-red-400 font-medium'
  if (lvl === 'WARN') return 'text-amber-600 dark:text-amber-400 font-medium'
  if (lvl === 'DEBUG') return 'text-vscode-textMuted'
  return 'text-vscode-textMain'
}
</script>
