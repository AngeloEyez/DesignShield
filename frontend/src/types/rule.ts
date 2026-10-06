/**
 * DRC 規則庫資料型別定義 (DRC Rule Types)
 */

export type RuleCheckType = 'HEURISTIC' | 'LLM'

export interface DrcRuleItem {
  id: string
  name: string
  category: string
  check_type: RuleCheckType
  is_active: boolean
  parameters: Record<string, any>
  prompt_template?: string | null
  context_extractor?: string | null
  created_at?: string | null
}

export interface RuleCreatePayload {
  id: string
  name: string
  category: string
  check_type: RuleCheckType
  is_active: boolean
  parameters: Record<string, any>
  prompt_template?: string | null
  context_extractor?: string | null
}

export interface RuleUpdatePayload {
  name?: string
  category?: string
  check_type?: RuleCheckType
  is_active?: boolean
  parameters?: Record<string, any>
  prompt_template?: string | null
  context_extractor?: string | null
}
