<template>
  <div class="rule-tree-card">
    <div class="tree-header">
      <div>
        <h3 class="card-title">
          <i class="pi pi-check-square mr-2"></i> 預先分析特徵與推薦規則庫 (Recommended DRC Rules)
        </h3>
        <p class="card-desc">系統依據圖譜特徵自動標註建議規則，請勾選欲執行的檢查項目</p>
      </div>
      <div class="header-actions">
        <Button
          :label="isAllSelected ? '取消全選' : '全選所有推薦'"
          icon="pi pi-filter"
          text
          size="small"
          @click="toggleSelectAll"
        />
      </div>
    </div>

    <!-- 預先分析特徵摘要標籤 -->
    <div class="summary-chips">
      <div class="chip-item">
        <span class="chip-label">元件總數:</span>
        <span class="chip-value">{{ summary.component_count }}</span>
      </div>
      <div class="chip-item">
        <span class="chip-label">網路總數:</span>
        <span class="chip-value">{{ summary.net_count }}</span>
      </div>
      <div class="chip-item">
        <span class="chip-label">偵測匯流排:</span>
        <span class="chip-value">{{ summary.buses.join(', ') || '未偵測' }}</span>
      </div>
      <div class="chip-item">
        <span class="chip-label">主控平台:</span>
        <span class="chip-value">{{ summary.platforms.join(', ') || '通用' }}</span>
      </div>
    </div>

    <!-- 規則分類樹狀列表 -->
    <div class="rule-categories-list">
      <div
        v-for="(group, category) in groupedRules"
        :key="category"
        class="category-group"
      >
        <div class="category-header">
          <span class="category-name">
            <i class="pi pi-folder mr-1 text-primary"></i> {{ category }}
          </span>
          <span class="category-count">{{ group.length }} 條規則</span>
        </div>

        <div class="rules-list">
          <label
            v-for="rule in group"
            :key="rule.id"
            class="rule-item"
            :class="{ selected: selectedRuleIds.includes(rule.id) }"
          >
            <input
              type="checkbox"
              :value="rule.id"
              v-model="selectedRuleIds"
              class="rule-checkbox"
            />
            <div class="rule-info">
              <div class="rule-title-row">
                <span class="rule-name">{{ rule.name }}</span>
                <span class="rule-id-badge">{{ rule.id }}</span>
              </div>
            </div>
            <Tag value="推薦" severity="success" class="recommended-tag" />
          </label>
        </div>
      </div>
    </div>

    <div class="tree-footer">
      <span class="selected-count-text">
        已選取 <strong>{{ selectedRuleIds.length }}</strong> 條規則
      </span>
      <Button
        label="確認並啟動正式 DRC"
        icon="pi pi-play"
        severity="success"
        :loading="isSubmitting"
        :disabled="selectedRuleIds.length === 0"
        @click="confirmAndRun"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * @file RuleTreeSelector.vue
 * @description 預先分析摘要展示與規則庫樹狀勾選元件
 */

import { ref, computed, watch } from 'vue'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import type { TaskSummary, RecommendedRuleItem } from '@/types/task'

interface Props {
  summary: TaskSummary
  recommendedRules: RecommendedRuleItem[]
  isSubmitting?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  summary: () => ({ buses: [], platforms: [], component_count: 0, net_count: 0 }),
  recommendedRules: () => [],
  isSubmitting: false,
})

const emit = defineEmits<{
  (e: 'run', selectedIds: string[]): void
}>()

// 已選取的 Rule IDs
const selectedRuleIds = ref<string[]>([])

// 初始化預設勾選所有推薦規則
watch(
  () => props.recommendedRules,
  (newRules) => {
    selectedRuleIds.value = newRules.map((r) => r.id)
  },
  { immediate: true }
)

/**
 * 依分類群組化規則
 */
const groupedRules = computed(() => {
  const groups: Record<string, RecommendedRuleItem[]> = {}
  props.recommendedRules.forEach((rule) => {
    if (!groups[rule.category]) {
      groups[rule.category] = []
    }
    groups[rule.category].push(rule)
  })
  return groups
})

/**
 * 判斷是否已全選
 */
const isAllSelected = computed(() => {
  return (
    props.recommendedRules.length > 0 &&
    selectedRuleIds.value.length === props.recommendedRules.length
  )
})

/**
 * 切換全選狀態
 */
const toggleSelectAll = () => {
  if (isAllSelected.value) {
    selectedRuleIds.value = []
  } else {
    selectedRuleIds.value = props.recommendedRules.map((r) => r.id)
  }
}

/**
 * 確認選取並啟動
 */
const confirmAndRun = () => {
  emit('run', selectedRuleIds.value)
}
</script>

<style scoped>
.rule-tree-card {
  background: #ffffff;
  border-radius: 8px;
  padding: 1.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  border: 1px solid #e2e8f0;
}

.tree-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.25rem;
}

.card-title {
  margin: 0;
  font-size: 1.2rem;
  color: #0f172a;
  display: flex;
  align-items: center;
}

.card-desc {
  margin: 0.25rem 0 0 0;
  font-size: 0.85rem;
  color: #64748b;
}

.summary-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  background: #f8fafc;
  padding: 0.85rem 1rem;
  border-radius: 6px;
  margin-bottom: 1.25rem;
  border: 1px solid #e2e8f0;
}

.chip-item {
  display: inline-flex;
  gap: 0.4rem;
  font-size: 0.85rem;
}

.chip-label {
  color: #64748b;
}

.chip-value {
  font-weight: 600;
  color: #1e293b;
}

.rule-categories-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.category-group {
  border: 1px solid #f1f5f9;
  border-radius: 6px;
  overflow: hidden;
}

.category-header {
  background: #f8fafc;
  padding: 0.6rem 0.85rem;
  display: flex;
  justify-content: space-between;
  font-size: 0.9rem;
  font-weight: 600;
  border-bottom: 1px solid #f1f5f9;
  color: #334155;
}

.category-count {
  font-size: 0.75rem;
  color: #94a3b8;
}

.rules-list {
  display: flex;
  flex-direction: column;
}

.rule-item {
  display: flex;
  align-items: center;
  padding: 0.65rem 0.85rem;
  border-bottom: 1px solid #f8fafc;
  cursor: pointer;
  transition: background-color 0.15s;
}

.rule-item:last-child {
  border-bottom: none;
}

.rule-item:hover {
  background-color: #f1f5f9;
}

.rule-item.selected {
  background-color: #f0fdf4;
}

.rule-checkbox {
  margin-right: 0.75rem;
  cursor: pointer;
  width: 16px;
  height: 16px;
}

.rule-info {
  flex: 1;
}

.rule-title-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.rule-name {
  font-size: 0.9rem;
  font-weight: 500;
  color: #1e293b;
}

.rule-id-badge {
  font-size: 0.75rem;
  background: #e2e8f0;
  color: #475569;
  padding: 0.1rem 0.4rem;
  border-radius: 4px;
  font-family: monospace;
}

.recommended-tag {
  font-size: 0.7rem;
}

.tree-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-top: 1px solid #e2e8f0;
  padding-top: 1.25rem;
}

.selected-count-text {
  font-size: 0.9rem;
  color: #475569;
}

.text-primary {
  color: #3b82f6;
}
</style>
