/**
 * API 與 SSE 服務模組 (DesignShield API & SSE Client)
 */

import axios from 'axios'
import type {
  TaskInfo,
  StepItem,
  TaskListResponse,
  TaskGraphDetails,
  TaskArchiveDetails,
  LogEntry,
  TaskLogListResponse,
} from '@/types/task'
import type { ServerHealthDetails } from '@/types/settings'
import type { PatternTreeResponse } from '@/types/pattern'

const API_BASE = '/api/v1'

/**
 * 取得任務清單 (支援依狀態、類型過濾與分頁)
 */
export async function fetchTasks(params?: {
  status?: string
  task_type?: string
  limit?: number
  skip?: number
}): Promise<TaskListResponse> {
  const response = await axios.get<TaskListResponse>(`${API_BASE}/tasks`, { params })
  return response.data
}

/**
 * 取得指定任務之日誌清單 (支援 level, step_name, category 過濾)
 */
export async function fetchTaskLogs(
  taskId: string,
  params?: { level?: string; step_name?: string; category?: string }
): Promise<TaskLogListResponse> {
  const response = await axios.get<TaskLogListResponse>(`${API_BASE}/tasks/${taskId}/logs`, { params })
  return response.data
}



/**
 * 手動停止/中斷指定任務
 */
export async function stopTask(taskId: string): Promise<any> {
  const response = await axios.post(`${API_BASE}/tasks/${taskId}/stop`)
  return response.data
}

/**
 * 刪除指定任務與其綁定之磁碟檔案
 */
export async function deleteTask(taskId: string): Promise<any> {
  const response = await axios.delete(`${API_BASE}/tasks/${taskId}`)
  return response.data
}

/**
 * 取得任務之電路圖譜拓撲詳細資訊 (Step 2)
 */
export async function fetchTaskGraphDetails(taskId: string): Promise<TaskGraphDetails> {
  const response = await axios.get<TaskGraphDetails>(`${API_BASE}/tasks/${taskId}/graph-details`)
  return response.data
}

/**
 * 取得任務之解壓縮與格式驗證檔案詳細資訊 (Step 1)
 */
export async function fetchTaskArchiveDetails(taskId: string): Promise<TaskArchiveDetails> {
  const response = await axios.get<TaskArchiveDetails>(`${API_BASE}/tasks/${taskId}/archive-details`)
  return response.data
}

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
  onError?: (err: Event) => void,
  onLog?: (log: LogEntry) => void,
  onTaskStatus?: (statusData: any) => void
): EventSource {
  const eventSource = new EventSource(`${API_BASE}/tasks/${taskId}/events`)

  eventSource.addEventListener('log', (event) => {
    try {
      const data = JSON.parse(event.data)
      if (onLog) onLog(data)
    } catch (e) {
      console.error('Failed to parse SSE log:', e)
    }
  })

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

  eventSource.addEventListener('task_status', (event) => {
    try {
      const data = JSON.parse(event.data)
      if (onTaskStatus) onTaskStatus(data)
    } catch (e) {
      console.error('Failed to parse SSE task_status:', e)
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

import type {
  EnvSettingsResponse,
  EnvSettingsUpdateResponse,
  RestartResponse,
  StorageStats,
} from '@/types/settings'

/**
 * 取得所有 .env 系統環境變數配置與中繼資料
 */
export async function fetchEnvSettings(): Promise<EnvSettingsResponse> {
  const response = await axios.get<EnvSettingsResponse>(`${API_BASE}/settings/env`)
  return response.data
}

/**
 * 更新 .env 系統設定值
 */
export async function updateEnvSettings(
  settings: Record<string, any>
): Promise<EnvSettingsUpdateResponse> {
  const response = await axios.put<EnvSettingsUpdateResponse>(`${API_BASE}/settings/env`, {
    settings,
  })
  return response.data
}

/**
 * 發送伺服器重啟請求
 */
export async function restartServer(): Promise<RestartResponse> {
  const response = await axios.post<RestartResponse>(`${API_BASE}/settings/restart`)
  return response.data
}

/**
 * 取得儲存空間統計指標
 */
export async function fetchStorageStats(): Promise<StorageStats> {
  const response = await axios.get<StorageStats>(`${API_BASE}/settings/storage-stats`)
  return response.data
}

/**
 * 觸發過期暫存垃圾回收
 */
export async function triggerStorageCleanup(retentionDays?: number): Promise<any> {
  const url = retentionDays !== undefined
    ? `${API_BASE}/settings/cleanup?retention_days=${retentionDays}`
    : `${API_BASE}/settings/cleanup`
  const response = await axios.post(url)
  return response.data
}

/**
 * 檢查伺服器健康狀態 (用於重啟時輪詢連線)
 * 優先透過反向代理端點 /api/v1/health 探測，完全相容於 Nginx 生產部署與 Vite 開發環境。
 * 
 * @returns {Promise<boolean>} 伺服器健康恢復正常時回傳 true，否則回傳 false
 */
export async function checkServerHealth(): Promise<boolean> {
  try {
    const res = await axios.get(`${API_BASE}/health`, { timeout: 2000 })
    return res.status === 200 && (res.data?.status === 'healthy' || res.data?.status === 'degraded')
  } catch {
    try {
      // 容錯機制：嘗試連線根目錄 /health
      const fallbackRes = await axios.get('/health', { timeout: 1500 })
      return fallbackRes.status === 200 && (fallbackRes.data?.status === 'healthy' || fallbackRes.data?.status === 'degraded')
    } catch {
      return false
    }
  }
}

/**
 * 取得詳細伺服器健康度與各元件 (FastAPI/DBOS, Database, LLM) 燈號狀態
 */
export async function fetchServerHealthDetails(): Promise<ServerHealthDetails> {
  try {
    const res = await axios.get<ServerHealthDetails>(`${API_BASE}/health`, { timeout: 2500 })
    if (res.status === 200 && res.data) {
      return res.data
    }
  } catch {
    try {
      const fallbackRes = await axios.get<ServerHealthDetails>('/health', { timeout: 2000 })
      if (fallbackRes.status === 200 && fallbackRes.data) {
        return fallbackRes.data
      }
    } catch {
      // 網路或服務離線
    }
  }

  return {
    status: 'unhealthy',
    service: 'DesignShield',
    version: '0.1.0',
    components: {
      api: { status: 'error', label: 'FASTAPI / DBOS', message: '伺服器未連線' },
      database: { status: 'error', label: 'Database', message: '無法連線' },
      llm: { status: 'offline', label: 'LLM 推理', message: '未連線' },
    },
  }
}

/**
 * 即時自指定 Provider 或端點查詢可用模型清單 (支援 Gemini, OpenRouter, Local 等)
 */
export async function fetchAvailableLlmModels(provider?: string, apiBase?: string, apiKey?: string): Promise<{
  success: boolean
  provider?: string
  api_base: string
  models: string[]
  message: string
}> {
  const params: Record<string, string> = {}
  if (provider) params.provider = provider
  if (apiBase) params.api_base = apiBase
  if (apiKey) params.api_key = apiKey
  const response = await axios.get(`${API_BASE}/settings/llm/models`, { params })
  return response.data
}

import type {
  DrcRuleItem,
  RuleCreatePayload,
  RuleUpdatePayload,
} from '@/types/rule'

/**
 * 取得所有 DRC 規則清單
 */
export async function fetchRules(params?: {
  category?: string
  check_type?: string
  is_active?: boolean
}): Promise<DrcRuleItem[]> {
  const response = await axios.get<DrcRuleItem[]>(`${API_BASE}/rules`, { params })
  return response.data
}

/**
 * 取得單一 DRC 規則詳情
 */
export async function fetchRule(ruleId: string): Promise<DrcRuleItem> {
  const response = await axios.get<DrcRuleItem>(`${API_BASE}/rules/${ruleId}`)
  return response.data
}

/**
 * 新增 DRC 規則
 */
export async function createRule(payload: RuleCreatePayload): Promise<DrcRuleItem> {
  const response = await axios.post<DrcRuleItem>(`${API_BASE}/rules`, payload)
  return response.data
}

/**
 * 修改 DRC 規則
 */
export async function updateRule(
  ruleId: string,
  payload: RuleUpdatePayload
): Promise<DrcRuleItem> {
  const response = await axios.put<DrcRuleItem>(`${API_BASE}/rules/${ruleId}`, payload)
  return response.data
}

/**
 * 刪除 DRC 規則
 */
export async function deleteRule(
  ruleId: string
): Promise<{ success: boolean; message: string; id: string }> {
  const response = await axios.delete<{ success: boolean; message: string; id: string }>(
    `${API_BASE}/rules/${ruleId}`
  )
  return response.data
}

/**
 * 取得完整 Pattern 規則庫與 PartDB 目錄樹 (File-based YAML)
 */
export async function fetchPatternTree(): Promise<PatternTreeResponse> {
  const response = await axios.get<PatternTreeResponse>(`${API_BASE}/patterns/tree`)
  return response.data
}

export interface ReloadPatternsResponse {
  success: boolean
  message: string
  summary?: any
  compile_stats?: {
    level1_rules: number
    level2_rules: number
    level3_rules: number
    partdb_parts: number
    regex_compiled: number
    compile_time_ms: number
  }
  errors?: string[]
}

/**
 * 重新載入磁碟上的 Pattern YAML 與 PartDB，並重新編譯引擎快取
 */
export async function reloadPatterns(): Promise<ReloadPatternsResponse> {
  const response = await axios.post<ReloadPatternsResponse>(
    `${API_BASE}/patterns/reload`
  )
  return response.data
}

/**
 * 取得全域合法 DRC 標籤白名單
 */
export async function fetchPatternTags(): Promise<string[]> {
  const response = await axios.get<string[]>(`${API_BASE}/patterns/tags`)
  return response.data
}



