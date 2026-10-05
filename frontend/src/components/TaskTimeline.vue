<template>
  <div class="task-timeline-container">
    <div class="timeline-header">
      <h3 class="section-title">
        <i class="pi pi-compass mr-2"></i>
        DBOS 工作流執行歷程 (Durable Execution Timeline)
      </h3>
      <span class="timeline-status-badge">
        <Tag :value="overallStatus" :severity="getOverallSeverity(overallStatus)" />
      </span>
    </div>

    <!-- 步驟時間軸 -->
    <Timeline :value="steps" align="alternate" class="custom-timeline">
      <template #marker="slotProps">
        <span
          class="custom-marker"
          :class="getMarkerClass(slotProps.item.status)"
        >
          <i :class="getStepIcon(slotProps.item.status)"></i>
        </span>
      </template>

      <template #content="slotProps">
        <Card class="step-card">
          <template #title>
            <div class="step-title-row">
              <span class="step-name">{{ formatStepName(slotProps.item.step_name) }}</span>
              <Tag
                :value="slotProps.item.status"
                :severity="getStatusSeverity(slotProps.item.status)"
              />
            </div>
          </template>

          <template #subtitle>
            <span class="step-time">
              <i class="pi pi-clock mr-1"></i>
              {{ formatTimestamp(slotProps.item.started_at) }}
            </span>
          </template>

          <template #content>
            <p class="step-log-message">
              {{ slotProps.item.log_message || '等待步驟執行中...' }}
            </p>
          </template>
        </Card>
      </template>
    </Timeline>
  </div>
</template>

<script setup lang="ts">
/**
 * @file TaskTimeline.vue
 * @description DBOS 步驟進度視覺化時間軸元件，即時展示 step_status 變化
 */

import Timeline from 'primevue/timeline'
import Card from 'primevue/card'
import Tag from 'primevue/tag'
import type { StepItem, StepState } from '@/types/task'

interface Props {
  /** 步驟狀態列表 */
  steps: StepItem[]
  /** 整體任務狀態 */
  overallStatus?: string
}

withDefaults(defineProps<Props>(), {
  steps: () => [],
  overallStatus: 'PENDING',
})

/**
 * 格式化步驟名稱為人類易讀繁體中文
 * @param {string} stepName 原始步驟名稱
 * @returns {string} 格式化後的中文字串
 */
const formatStepName = (stepName: string): string => {
  const mapping: Record<string, string> = {
    UNPACK_AND_VALIDATE: '1. 解壓縮與檔案格式預檢',
    PARSE_AND_GRAPH: '2. 圖譜構建與線路解析',
    HEURISTIC_CHECK: '3. 傳統演算法規則比對',
    LLM_REASONING: '4. 本地大模型語意推理',
    GENERATE_REPORT: '5. 報告彙整與資源落地',
  }
  return mapping[stepName] || stepName
}

/**
 * 取得步驟狀態對應的 PrimeVue Tag 嚴重度
 * @param {StepState} status 步驟狀態
 * @returns {'success' | 'info' | 'warn' | 'danger' | 'secondary'} 嚴重等級
 */
const getStatusSeverity = (status: StepState) => {
  switch (status) {
    case 'COMPLETED':
      return 'success'
    case 'PROCESSING':
      return 'info'
    case 'FAILED':
      return 'danger'
    case 'SKIPPED':
      return 'warn'
    default:
      return 'secondary'
  }
}

/**
 * 取得總體任務狀態的 Tag 嚴重度
 * @param {string} status 總體任務狀態
 * @returns {'success' | 'info' | 'warn' | 'danger' | 'secondary'} 嚴重等級
 */
const getOverallSeverity = (status: string) => {
  switch (status) {
    case 'COMPLETED':
      return 'success'
    case 'PROCESSING':
      return 'info'
    case 'FAILED':
      return 'danger'
    case 'READY_FOR_RUN':
      return 'warn'
    default:
      return 'secondary'
  }
}

/**
 * 根據步驟狀態取得對應 PrimeIcon
 * @param {StepState} status 步驟狀態
 * @returns {string} 圖示 class
 */
const getStepIcon = (status: StepState): string => {
  switch (status) {
    case 'COMPLETED':
      return 'pi pi-check'
    case 'PROCESSING':
      return 'pi pi-spin pi-spinner'
    case 'FAILED':
      return 'pi pi-times'
    default:
      return 'pi pi-circle'
  }
}

/**
 * 取得圓圈 Marker 的 CSS 類別
 * @param {StepState} status 步驟狀態
 * @returns {string} class 名稱
 */
const getMarkerClass = (status: StepState): string => {
  return `marker-${status.toLowerCase()}`
}

/**
 * 格式化時間戳記為本地時間
 * @param {string} [timestamp] ISO 時間字串
 * @returns {string} 易讀時間字串
 */
const formatTimestamp = (timestamp?: string): string => {
  if (!timestamp) return '尚未開始'
  try {
    const d = new Date(timestamp)
    return d.toLocaleTimeString('zh-TW', { hour12: false })
  } catch {
    return timestamp
  }
}
</script>

<style scoped>
.task-timeline-container {
  background: #ffffff;
  border-radius: 8px;
  padding: 1.5rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.timeline-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  border-bottom: 1px solid #f1f5f9;
  padding-bottom: 0.75rem;
}

.section-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: #1e293b;
  margin: 0;
  display: flex;
  align-items: center;
}

.custom-marker {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  border-radius: 50%;
  color: #ffffff;
}

.marker-completed {
  background-color: #10b981;
}

.marker-processing {
  background-color: #3b82f6;
  box-shadow: 0 0 10px rgba(59, 130, 246, 0.5);
}

.marker-failed {
  background-color: #ef4444;
}

.marker-pending {
  background-color: #94a3b8;
}

.step-card {
  margin-bottom: 1rem;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
  border: 1px solid #e2e8f0;
}

.step-title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 1rem;
  font-weight: 600;
}

.step-name {
  color: #334155;
}

.step-time {
  font-size: 0.825rem;
  color: #64748b;
}

.step-log-message {
  margin: 0.5rem 0 0 0;
  font-size: 0.875rem;
  color: #475569;
  line-height: 1.5;
}
</style>
