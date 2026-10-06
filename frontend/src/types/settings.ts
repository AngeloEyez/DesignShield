/**
 * 系統設定與環境變數相關型別定義 (System Settings Types)
 */

export interface EnvSettingItem {
  key: string
  value: any
  category: string
  category_name: string
  label: string
  description: string
  example: string
  default?: string
  is_secret?: boolean
  requires_restart?: boolean
}

export interface EnvCategory {
  id: string
  name: string
  icon: string
}

export interface EnvSettingsResponse {
  env_file_path: string
  items: EnvSettingItem[]
  categories: EnvCategory[]
  total_count: number
}

export interface EnvSettingsUpdateResponse {
  success: boolean
  changed_keys: string[]
  requires_restart: boolean
  restart_reasons: string[]
  message: string
}

export interface RestartResponse {
  success: boolean
  mode: string
  message: string
}

export interface StorageStats {
  storage_root?: string
  total_files: number
  total_bytes: number
  total_mb: number
  uploads: { file_count: number; total_bytes: number }
  staging: { file_count: number; total_bytes: number }
  reports: { file_count: number; total_bytes: number }
}
