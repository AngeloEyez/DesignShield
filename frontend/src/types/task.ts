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

export type LogLevel = 'INFO' | 'WARNING' | 'ERROR' | 'DEBUG'

export interface LogEntry {
  id: string
  task_id?: string
  timestamp: string
  display_time?: string
  step_name: string
  category?: string
  level?: LogLevel
  status?: StepState
  message: string
  details?: any
}

export interface TaskLogListResponse {
  total: number
  task_id: string
  logs: LogEntry[]
}


export interface TaskListItem {
  id: string
  project_name: string
  task_type: string
  status: string
  created_at: string
  updated_at: string
  pre_analysis_summary: TaskSummary
  selected_rules: string[]
}

export interface TaskListResponse {
  total: number
  tasks: TaskListItem[]
}

export interface ComponentDetail {
  ref_des: string
  category: string
  sub_category?: string
  functional_role?: string
  is_electrical?: boolean
  part_value?: string
  package?: string
  description?: string
  pins_count: number
  connected_nets: string[]
}

export interface NetDetail {
  net_name: string
  bus_type?: string
  is_power: boolean
  is_ground: boolean
  connected_components: string[]
}

export interface TaskGraphDetails {
  task_id: string
  components_count: number
  nets_count: number
  pins_count: number
  buses: string[]
  components: ComponentDetail[]
  nets: NetDetail[]
  key_ics?: string[]
  key_connectors?: string[]
  ic_directory_by_role?: Record<string, string[]>
  non_electrical_components?: string[]
  main_ics: string[]
  sub_ics: string[]
}

export interface ArchiveFileItem {
  filename: string
  relative_path: string
  size_bytes: number
  is_xml: boolean
  is_netlist: boolean
}

export interface TaskArchiveDetails {
  task_id: string
  original_filename?: string
  file_count: number
  total_bytes: number
  files: ArchiveFileItem[]
}

export type TaskArchiveFile = ArchiveFileItem

