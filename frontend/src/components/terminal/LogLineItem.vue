<template>
  <div
    class="log-line"
    :class="[`level-${normalizedLevel.toLowerCase()}`, { 'has-details': hasDetails, 'is-expanded': isExpanded }]"
  >
    <div class="line-header" @click="toggleExpand">
      <!-- 1. 時間戳記 (月日與時間) -->
      <span class="log-timestamp">[{{ formattedTime }}]</span>

      <!-- 2. 第一標籤：Timeline 工作流主要步驟 -->
      <span class="log-step" :class="getStepTagClass(log.step_name)" :title="log.step_name">
        [{{ formatStepTag(log.step_name) }}]
      </span>

      <!-- 3. 第二標籤：用途分類 (LLM, DB, VLM, PARSER, GRAPH, FILE, HEURISTIC 等) -->
      <span v-if="log.category" class="log-category" :class="getCategoryTagClass(log.category)" :title="`分類: ${log.category}`">
        [{{ log.category }}]
      </span>

      <!-- 4. 日誌分級 (INFO, WARN, ERROR, DEBUG) -->
      <span class="log-level-badge" :class="`badge-${normalizedLevel.toLowerCase()}`">
        {{ normalizedLevel }}
      </span>

      <!-- 5. 步驟狀態 (若有 status 欄位) -->
      <span v-if="log.status && !log.level" class="log-status" :class="`status-${log.status.toLowerCase()}`">
        {{ log.status }}
      </span>

      <!-- 6. 日誌訊息內容 -->
      <span class="log-message">{{ log.message }}</span>

      <!-- 7. 展開詳細資訊按鈕 (若存在 details 結構化資料) -->
      <button
        v-if="hasDetails"
        type="button"
        class="details-toggle-btn"
        :class="{ expanded: isExpanded }"
        :title="isExpanded ? '收合詳細資料' : '查看完整 LLM 查詢/錯誤細節'"
        @click.stop="toggleExpand"
      >
        <i :class="isExpanded ? 'pi pi-chevron-up' : 'pi pi-chevron-down'" class="mr-1"></i>
        <span>{{ isExpanded ? '收合' : '詳情' }}</span>
      </button>
    </div>

    <!-- 展開之結構化詳細資訊區塊 (VS Code 摺疊輸出風格) -->
    <div v-if="hasDetails && isExpanded" class="details-box">
      <div class="details-top">
        <span class="details-label">
          <i class="pi pi-file-code mr-1"></i>
          結構化詳細內容 (Payload / Trace)
        </span>
        <button type="button" class="copy-btn" @click.stop="copyDetails" :title="copySuccess ? '已複製！' : '複製內容'">
          <i :class="copySuccess ? 'pi pi-check' : 'pi pi-copy'" class="mr-1"></i>
          <span>{{ copySuccess ? '已複製' : '複製' }}</span>
        </button>
      </div>

      <!-- 若包含 prompt 與 response 則特別友善排版 -->
      <div v-if="detailsObj && (detailsObj.prompt || detailsObj.response)" class="llm-details-view">
        <div v-if="detailsObj.prompt" class="detail-section">
          <span class="section-badge badge-prompt">Prompt 提示詞</span>
          <pre class="code-pre">{{ detailsObj.prompt }}</pre>
        </div>
        <div v-if="detailsObj.response" class="detail-section">
          <span class="section-badge badge-response">LLM 回應</span>
          <pre class="code-pre">{{ formatPayload(detailsObj.response) }}</pre>
        </div>
      </div>
      <pre v-else class="code-pre">{{ formatPayload(log.details) }}</pre>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * @file LogLineItem.vue
 * @description VS Code 終端風格緊密日誌單行元件，支援月日時間格式、工作流與用途雙標籤、四級分級與展開/收合 details
 */

import { ref, computed } from 'vue'
import type { LogEntry } from '@/types/task'

interface Props {
  log: LogEntry
}

const props = defineProps<Props>()

const isExpanded = ref(false)
const copySuccess = ref(false)

const toggleExpand = () => {
  if (hasDetails.value) {
    isExpanded.value = !isExpanded.value
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
  // 若為 ISO 字串，嘗試轉換為 MM-DD HH:mm:ss
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
 * 第一標籤 class 顏色
 */
const getStepTagClass = (step: string): string => {
  if (!step) return 'step-default'
  if (step.includes('UNPACK')) return 'step-unpack'
  if (step.includes('PARSE')) return 'step-parse'
  if (step.includes('RULE')) return 'step-rule'
  if (step.includes('HEURISTIC')) return 'step-heuristic'
  if (step.includes('LLM')) return 'step-llm'
  return 'step-report'
}

/**
 * 第二標籤 (用途分類) class 顏色
 */
const getCategoryTagClass = (cat: string): string => {
  const c = cat.toUpperCase()
  if (c === 'LLM') return 'cat-llm'
  if (c === 'DB') return 'cat-db'
  if (c === 'VLM') return 'cat-vlm'
  if (c === 'PARSER') return 'cat-parser'
  if (c === 'GRAPH') return 'cat-graph'
  if (c === 'FILE') return 'cat-file'
  if (c === 'HEURISTIC') return 'cat-heuristic'
  return 'cat-system'
}
</script>

<style scoped>
.log-line {
  display: flex;
  flex-direction: column;
  padding: 0.16rem 0.4rem;
  border-radius: 3px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
  font-size: 0.77rem;
  line-height: 1.45;
  transition: background-color 0.12s ease;
  word-break: break-all;
}

.log-line:hover {
  background-color: #2a2d2e;
}

.line-header {
  display: flex;
  align-items: baseline;
  gap: 0.4rem;
  flex-wrap: wrap;
}

.log-line.has-details .line-header {
  cursor: pointer;
}

/* 時間戳記 */
.log-timestamp {
  color: #6e7681;
  font-size: 0.73rem;
  flex-shrink: 0;
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.02em;
}

/* 第一標籤: Timeline 步驟 */
.log-step {
  font-size: 0.71rem;
  font-weight: 600;
  padding: 0.05rem 0.25rem;
  border-radius: 3px;
  flex-shrink: 0;
}

.step-unpack {
  color: #38bdf8;
  background: rgba(56, 189, 248, 0.12);
}

.step-parse {
  color: #a78bfa;
  background: rgba(167, 139, 250, 0.12);
}

.step-rule {
  color: #fb923c;
  background: rgba(251, 146, 60, 0.12);
}

.step-heuristic {
  color: #fbbf24;
  background: rgba(251, 191, 36, 0.12);
}

.step-llm {
  color: #f472b6;
  background: rgba(244, 114, 182, 0.12);
}

.step-report {
  color: #34d399;
  background: rgba(52, 211, 153, 0.12);
}

.step-default {
  color: #94a3b8;
  background: rgba(148, 163, 184, 0.12);
}

/* 第二標籤: 用途分類 */
.log-category {
  font-size: 0.71rem;
  font-weight: 600;
  padding: 0.05rem 0.25rem;
  border-radius: 3px;
  flex-shrink: 0;
}

.cat-llm {
  color: #ec4899;
  background: rgba(236, 72, 153, 0.15);
  border: 1px solid rgba(236, 72, 153, 0.3);
}

.cat-db {
  color: #10b981;
  background: rgba(16, 185, 129, 0.15);
  border: 1px solid rgba(16, 185, 129, 0.3);
}

.cat-vlm {
  color: #c084fc;
  background: rgba(192, 132, 252, 0.15);
  border: 1px solid rgba(192, 132, 252, 0.3);
}

.cat-parser {
  color: #2dd4bf;
  background: rgba(45, 212, 191, 0.15);
  border: 1px solid rgba(45, 212, 191, 0.3);
}

.cat-graph {
  color: #818cf8;
  background: rgba(129, 140, 248, 0.15);
  border: 1px solid rgba(129, 140, 248, 0.3);
}

.cat-file {
  color: #38bdf8;
  background: rgba(56, 189, 248, 0.15);
  border: 1px solid rgba(56, 189, 248, 0.3);
}

.cat-heuristic {
  color: #f59e0b;
  background: rgba(245, 158, 11, 0.15);
  border: 1px solid rgba(245, 158, 11, 0.3);
}

.cat-system {
  color: #94a3b8;
  background: rgba(148, 163, 184, 0.15);
  border: 1px solid rgba(148, 163, 184, 0.3);
}

/* 分級標籤 (INFO, WARN, ERROR, DEBUG) */
.log-level-badge {
  font-size: 0.69rem;
  font-weight: 700;
  padding: 0.05rem 0.25rem;
  border-radius: 3px;
  flex-shrink: 0;
  letter-spacing: 0.03em;
}

.badge-info {
  color: #38bdf8;
  background: rgba(56, 189, 248, 0.15);
}

.badge-warn {
  color: #fbbf24;
  background: rgba(251, 191, 36, 0.18);
}

.badge-error {
  color: #f87171;
  background: rgba(248, 113, 113, 0.2);
}

.badge-debug {
  color: #94a3b8;
  background: rgba(148, 163, 184, 0.12);
}

/* 訊息本文 */
.log-message {
  color: #d4d4d4;
  font-weight: 400;
  flex: 1;
}

.level-error .log-message {
  color: #fca5a5;
  font-weight: 500;
}

.level-warn .log-message {
  color: #fde047;
}

.level-debug .log-message {
  color: #94a3b8;
}

/* 展開按鈕 */
.details-toggle-btn {
  background: #252526;
  border: 1px solid #3c3c3c;
  color: #38bdf8;
  font-size: 0.68rem;
  padding: 0.08rem 0.35rem;
  border-radius: 3px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  transition: all 0.15s;
}

.details-toggle-btn:hover {
  background: #333333;
  color: #ffffff;
}

.details-toggle-btn.expanded {
  background: #1e3a5f;
  border-color: #38bdf8;
}

/* 展開詳細資料面板 */
.details-box {
  margin-top: 0.35rem;
  margin-left: 1.5rem;
  background: #181818;
  border: 1px solid #333333;
  border-left: 3px solid #38bdf8;
  border-radius: 4px;
  padding: 0.5rem 0.75rem;
}

.details-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.35rem;
  border-bottom: 1px solid #282828;
  padding-bottom: 0.25rem;
}

.details-label {
  font-size: 0.7rem;
  color: #888888;
  font-weight: 600;
}

.copy-btn {
  background: #252526;
  border: 1px solid #3c3c3c;
  color: #cccccc;
  font-size: 0.68rem;
  padding: 0.1rem 0.35rem;
  border-radius: 3px;
  cursor: pointer;
}

.copy-btn:hover {
  color: #ffffff;
  background: #333333;
}

.code-pre {
  margin: 0;
  font-size: 0.73rem;
  color: #a6accd;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 240px;
  overflow-y: auto;
  line-height: 1.4;
}

.llm-details-view {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.detail-section {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.section-badge {
  font-size: 0.65rem;
  font-weight: 600;
  padding: 0.05rem 0.25rem;
  border-radius: 2px;
  width: fit-content;
}

.badge-prompt {
  background: rgba(56, 189, 248, 0.2);
  color: #38bdf8;
}

.badge-response {
  background: rgba(244, 114, 182, 0.2);
  color: #f472b6;
}

.mr-1 {
  margin-right: 0.25rem;
}
</style>
