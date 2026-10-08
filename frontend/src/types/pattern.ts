/**
 * Pattern 規則與 PartDB 知識庫型別定義 (Pattern & PartDB Types)
 */

export type RuleSeverity = 'Fatal' | 'Error' | 'Warning' | 'Info'

export interface Level3RuleItem {
  name: string
  description?: string
  tags: string[]
  severity: RuleSeverity
  trigger_conditions: Record<string, any>
  check_logic: Array<{
    type: string
    asserts?: Array<{
      condition: string
      node?: string
      error_message?: string
      [key: string]: any
    }>
    script_path?: string
    params?: Record<string, any>
    agent_prompt?: string
  }>
  _domain: string
  _filename: string
  _rel_path: string
  _raw_yaml: string
}

export interface Level2PatternItem {
  name: string
  category: string
  priority: number
  signals?: Array<{
    role: string
    required?: boolean
    group_key?: boolean
    matches?: any
  }>
  role_overrides?: Array<{
    original_sub_category: string
    connected_to: string
    new_role: string
  }>
  extra_fields?: Record<string, any>
  _domain: string
  _filename: string
  _raw_yaml: string
}

export interface Level1PatternItem {
  name: string
  description?: string
  priority: number
  matches: Record<string, any>
  assigns: {
    category: string
    sub_category: string
    functional_role: string
    is_electrical: boolean
    confidence: number
  }
  _filename: string
  _raw_yaml: string
}

export interface PartDBItem {
  pn: string
  description?: string
  interfaces: Record<string, {
    requires_series_resistor?: boolean
    forbid_gnd_capacitor?: boolean
    pullup_range_ohms?: [number, number]
    _meta?: {
      evidence: string
      page: number
      excerpt: string
    }
    [key: string]: any
  }>
  _filename: string
  _raw_yaml: string
}

export interface PatternTreeResponse {
  level1: Level1PatternItem[]
  level2: Level2PatternItem[]
  level3: Level3RuleItem[]
  partdb: {
    parts: PartDBItem[]
    schemas: Record<string, any>
  }
  tags: string[]
  summary: {
    level1_count: number
    level2_count: number
    level3_count: number
    partdb_parts_count: number
    tags_count: number
  }
}
