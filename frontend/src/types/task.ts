/**
 * 任務與步驟型別定義 (Task & Step Status Types)
 */

export type StepState = 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED' | 'SKIPPED'

export interface StepItem {
  id?: string
  step_name: string
  status: StepState
  log_message?: string
  started_at?: string
  completed_at?: string
}

export interface TaskSummary {
  buses: string[]
  platforms: string[]
  component_count: number
  net_count: number
}

export interface RecommendedRuleItem {
  id: string
  name: string
  category: string
}

export interface TaskInfo {
  task_id: string
  project_name: string
  status: string
  pre_analysis_summary: TaskSummary
  recommended_rules?: RecommendedRuleItem[]
  selected_rules?: string[]
  created_at?: string
  steps?: StepItem[]
}

export interface LogEntry {
  id: string
  timestamp: string
  step_name: string
  status: StepState
  message: string
}
