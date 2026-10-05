/**
 * API 與 SSE 服務模組 (DesignShield API & SSE Client)
 */

import axios from 'axios'
import type { TaskInfo, StepItem } from '@/types/task'

const API_BASE = '/api/v1'

/**
 * 上傳線路圖並取得輕量預先分析結果
 * @param {File} file 線路設計檔案 (.zip, .7z, .xml)
 * @param {string} projectName 專案名稱
 * @returns {Promise<TaskInfo>} 任務基本資訊與推薦規則
 */
export async function uploadSchematic(file: File, projectName: string): Promise<TaskInfo> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('project_name', projectName)

  const response = await axios.post<TaskInfo>(`${API_BASE}/tasks`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return response.data
}

/**
 * 啟動正式 DRC 分析任務
 * @param {string} taskId 任務 UUID
 * @param {string[]} selectedRuleIds 選定的檢驗規則代碼清單
 * @returns {Promise<any>} 啟動狀態
 */
export async function startTaskRun(taskId: string, selectedRuleIds: string[]): Promise<any> {
  const response = await axios.post(`${API_BASE}/tasks/${taskId}/run`, {
    selected_rule_ids: selectedRuleIds,
  })
  return response.data
}

/**
 * 查詢指定任務狀態與步驟執行紀錄
 * @param {string} taskId 任務 UUID
 * @returns {Promise<TaskInfo>} 任務完整狀態
 */
export async function fetchTaskStatus(taskId: string): Promise<TaskInfo> {
  const response = await axios.get<TaskInfo>(`${API_BASE}/tasks/${taskId}/status`)
  return response.data
}

/**
 * 查詢指定任務之最終完整分析報告
 * @param {string} taskId 任務 UUID
 * @returns {Promise<any>} 包含 summary 與 violations 的報告資料
 */
export async function fetchTaskReport(taskId: string): Promise<any> {
  const response = await axios.get(`${API_BASE}/tasks/${taskId}/report`)
  return response.data
}

/**
 * 訂閱 Server-Sent Events (SSE) 即時進度更新
 * @param {string} taskId 任務 UUID
 * @param {(step: StepItem) => void} onStepUpdate 步驟更新回呼函式
 * @param {(data: any) => void} onTaskEnd 任務結束回呼函式
 * @param {(err: Event) => void} onError 錯誤回呼函式
 * @returns {EventSource} 原生 EventSource 實例
 */
export function subscribeTaskEvents(
  taskId: string,
  onStepUpdate: (step: StepItem) => void,
  onTaskEnd?: (data: any) => void,
  onError?: (err: Event) => void
): EventSource {
  const eventSource = new EventSource(`${API_BASE}/tasks/${taskId}/events`)

  eventSource.addEventListener('step_update', (event) => {
    try {
      const data = JSON.parse(event.data)
      onStepUpdate({
        step_name: data.step_name,
        status: data.status,
        log_message: data.log_message,
        started_at: data.timestamp,
        completed_at: data.status === 'COMPLETED' ? data.timestamp : undefined,
      })
    } catch (e) {
      console.error('Failed to parse SSE step_update:', e)
    }
  })

  eventSource.addEventListener('task_end', (event) => {
    try {
      const data = JSON.parse(event.data)
      if (onTaskEnd) onTaskEnd(data)
    } catch (e) {
      console.error('Failed to parse SSE task_end:', e)
    }
    eventSource.close()
  })

  eventSource.onerror = (err) => {
    if (onError) onError(err)
  }

  return eventSource
}
