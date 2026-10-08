<template>
  <div class="rule-management-view">
    <!-- 頂部頁頭導航與 GitOps 動作列 -->
    <div class="rules-header">
      <div class="header-left">
        <h1 class="page-title">
          <i class="pi pi-sliders-h text-primary mr-2"></i>
          DRC 規則庫與知識庫中心 (Rule & Knowledge Base Center)
        </h1>
        <p class="page-subtitle">
          依據 GitOps 架構維護之檔案式 YAML 規則庫 (Level 1~3) 與 PartDB 零件特規庫，無狀態高效能載入與版本控制。
        </p>
      </div>

      <div class="header-actions">
        <Button
          label="重新載入規則庫"
          icon="pi pi-refresh"
          severity="secondary"
          size="small"
          :loading="isLoading"
          @click="handleReloadPatterns"
        />
        <Button
          label="GitOps 貢獻手冊"
          icon="pi pi-book"
          severity="primary"
          size="small"
          @click="showGitOpsGuide = true"
        />
      </div>
    </div>

    <!-- 訊息提示橫幅 -->
    <div v-if="successMessage" class="alert-banner success-banner">
      <div class="alert-content">
        <i class="pi pi-check-circle alert-icon"></i>
        <span>{{ successMessage }}</span>
      </div>
      <button class="banner-close" @click="successMessage = ''">
        <i class="pi pi-times"></i>
      </button>
    </div>

    <div v-if="errorMessage" class="alert-banner error-banner">
      <div class="alert-content">
        <i class="pi pi-exclamation-circle alert-icon"></i>
        <span>{{ errorMessage }}</span>
      </div>
      <button class="banner-close" @click="errorMessage = ''">
        <i class="pi pi-times"></i>
      </button>
    </div>

    <!-- 統計指標卡片 -->
    <div class="stats-grid">
      <div class="stat-card" :class="{ active: activeTab === 'level3' }" @click="activeTab = 'level3'">
        <div class="stat-icon-wrapper bg-red-light">
          <i class="pi pi-shield text-red"></i>
        </div>
        <div class="stat-info">
          <span class="stat-label">Level 3: DRC 驗證規範</span>
          <span class="stat-value">{{ level3Rules.length }} <small class="unit">條規則</small></span>
        </div>
      </div>

      <div class="stat-card" :class="{ active: activeTab === 'partdb' }" @click="activeTab = 'partdb'">
        <div class="stat-icon-wrapper bg-indigo-light">
          <i class="pi pi-microchip text-indigo"></i>
        </div>
        <div class="stat-info">
          <span class="stat-label">PartDB: 零件特規庫</span>
          <span class="stat-value">{{ partdbParts.length }} <small class="unit">顆晶片</small></span>
        </div>
      </div>

      <div class="stat-card" :class="{ active: activeTab === 'level2' }" @click="activeTab = 'level2'">
        <div class="stat-icon-wrapper bg-blue-light">
          <i class="pi pi-sitemap text-blue"></i>
        </div>
        <div class="stat-info">
          <span class="stat-label">Level 2: 網路拓撲與匯流排</span>
          <span class="stat-value">{{ level2Patterns.length }} <small class="unit">項規範</small></span>
        </div>
      </div>

      <div class="stat-card" :class="{ active: activeTab === 'level1' }" @click="activeTab = 'level1'">
        <div class="stat-icon-wrapper bg-green-light">
          <i class="pi pi-th-large text-green"></i>
        </div>
        <div class="stat-info">
          <span class="stat-label">Level 1: 元件辨識規範</span>
          <span class="stat-value">{{ level1Patterns.length }} <small class="unit">項規範</small></span>
        </div>
      </div>
    </div>

    <!-- 分頁切換選單 (Navigation Tabs) -->
    <div class="tabs-nav">
      <button
        type="button"
        class="tab-btn"
        :class="{ active: activeTab === 'level3' }"
        @click="activeTab = 'level3'"
      >
        <i class="pi pi-shield mr-2"></i>
        Level 3: DRC 驗證規範 ({{ level3Rules.length }})
      </button>
      <button
        type="button"
        class="tab-btn"
        :class="{ active: activeTab === 'partdb' }"
        @click="activeTab = 'partdb'"
      >
        <i class="pi pi-microchip mr-2"></i>
        PartDB: 零件特規庫 ({{ partdbParts.length }})
      </button>
      <button
        type="button"
        class="tab-btn"
        :class="{ active: activeTab === 'level2' }"
        @click="activeTab = 'level2'"
      >
        <i class="pi pi-sitemap mr-2"></i>
        Level 2: 網路拓撲與匯流排 ({{ level2Patterns.length }})
      </button>
      <button
        type="button"
        class="tab-btn"
        :class="{ active: activeTab === 'level1' }"
        @click="activeTab = 'level1'"
      >
        <i class="pi pi-th-large mr-2"></i>
        Level 1: 元件辨識規範 ({{ level1Patterns.length }})
      </button>
    </div>

    <!-- TAB 1: Level 3 DRC 驗證規範 -->
    <div v-show="activeTab === 'level3'" class="tab-content">
      <!-- 搜尋與篩選工具列 -->
      <div class="filter-card">
        <div class="filter-controls">
          <div class="search-input-wrapper">
            <i class="pi pi-search search-icon"></i>
            <input
              v-model="searchQuery"
              type="text"
              placeholder="搜尋 Level 3 規則名稱、說明、標籤或網域..."
              class="filter-search-input"
            />
            <button
              v-if="searchQuery"
              type="button"
              class="clear-btn"
              @click="searchQuery = ''"
            >
              <i class="pi pi-times"></i>
            </button>
          </div>

          <div class="filter-select-group">
            <select v-model="selectedDomain" class="filter-select">
              <option value="">全部網域 (All Domains)</option>
              <option v-for="d in level3Domains" :key="d" :value="d">
                {{ d }}
              </option>
            </select>

            <select v-model="selectedSeverity" class="filter-select">
              <option value="">全部嚴重等級 (All Severities)</option>
              <option value="Fatal">Fatal (致命異常)</option>
              <option value="Error">Error (嚴重違規)</option>
              <option value="Warning">Warning (潛在警告)</option>
              <option value="Info">Info (提示資訊)</option>
            </select>

            <select v-model="selectedTag" class="filter-select">
              <option value="">全部標籤 (All Tags)</option>
              <option v-for="t in allTags" :key="t" :value="t">
                {{ t }}
              </option>
            </select>
          </div>
        </div>

        <div class="filter-summary">
          <span>顯示 <strong>{{ filteredLevel3Rules.length }}</strong> / {{ level3Rules.length }} 條 DRC 規則</span>
        </div>
      </div>

      <!-- Level 3 規則卡片列表 -->
      <div class="rules-grid">
        <div v-if="filteredLevel3Rules.length === 0" class="empty-placeholder">
          <i class="pi pi-inbox text-4xl mb-3 text-muted"></i>
          <p>無符合條件之 Level 3 DRC 規則項目</p>
        </div>

        <div
          v-for="rule in filteredLevel3Rules"
          :key="rule.name"
          class="rule-card"
          :class="`border-${getSeverityClass(rule.severity)}`"
        >
          <div class="rule-card-header">
            <div class="header-badges">
              <span class="severity-badge" :class="getSeverityClass(rule.severity)">
                <i :class="getSeverityIcon(rule.severity)" class="mr-1"></i>
                {{ rule.severity }}
              </span>
              <span class="domain-badge">
                <i class="pi pi-folder mr-1"></i>{{ rule._domain }}
              </span>
            </div>
            <button
              type="button"
              class="yaml-view-btn"
              title="查看原始 YAML 檔"
              @click="openYamlModal(rule._filename, rule._raw_yaml)"
            >
              <i class="pi pi-file-code mr-1"></i>YAML
            </button>
          </div>

          <div class="rule-card-body">
            <h3 class="rule-title">{{ rule.name }}</h3>
            <p class="rule-desc">{{ rule.description || '無詳細說明' }}</p>

            <div class="rule-meta-section">
              <div class="meta-item">
                <span class="meta-label">檢查機制:</span>
                <span class="meta-value check-type-pill">
                  <i class="pi pi-cog mr-1"></i>
                  {{ formatCheckLogicType(rule.check_logic) }}
                </span>
              </div>
              <div class="meta-item">
                <span class="meta-label">關聯標籤:</span>
                <div class="tags-container">
                  <span v-for="tag in rule.tags" :key="tag" class="rule-tag-chip">
                    {{ tag }}
                  </span>
                </div>
              </div>
            </div>

            <!-- 觸發條件預覽 -->
            <div class="rule-condition-box">
              <span class="cond-title">
                <i class="pi pi-bolt text-amber mr-1"></i>觸發特徵:
              </span>
              <code class="cond-code">
                {{ formatTriggerSummary(rule.trigger_conditions) }}
              </code>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- TAB 2: PartDB 零件特規庫 -->
    <div v-show="activeTab === 'partdb'" class="tab-content">
      <div class="partdb-banner">
        <div class="partdb-banner-info">
          <h3>
            <i class="pi pi-database text-indigo mr-2"></i>
            PartDB 零件特規與原廠規格書真相來源
          </h3>
          <p>
            集中維護真實 IC 型號之介面電氣限制 (如 I2C 阻值範圍、禁止接地電容)。所有特規皆強制綁定 <code>_meta</code> 規格書出處與頁碼，為 DRC 違規報告提供可查證鐵證。
          </p>
        </div>
      </div>

      <div class="partdb-grid">
        <div
          v-for="part in partdbParts"
          :key="part.pn"
          class="part-card"
        >
          <div class="part-card-header">
            <div class="part-title-wrapper">
              <span class="part-icon"><i class="pi pi-microchip"></i></span>
              <div>
                <h3 class="part-pn">{{ part.pn }}</h3>
                <span class="part-file-label">{{ part._filename }}</span>
              </div>
            </div>
            <button
              type="button"
              class="yaml-view-btn"
              @click="openYamlModal(part._filename, part._raw_yaml)"
            >
              <i class="pi pi-file-code mr-1"></i>YAML
            </button>
          </div>

          <p class="part-desc">{{ part.description || '無描述' }}</p>

          <div class="interfaces-section">
            <h4 class="iface-title">
              <i class="pi pi-sliders-v mr-1"></i>支援硬體介面特規 ({{ Object.keys(part.interfaces || {}).length }})
            </h4>

            <div
              v-for="(spec, ifName) in part.interfaces"
              :key="ifName"
              class="iface-box"
            >
              <div class="iface-header">
                <span class="iface-badge">{{ ifName }}</span>
              </div>

              <!-- 特規參數 -->
              <div class="iface-props">
                <div v-if="spec.pullup_range_ohms" class="prop-item">
                  <span class="prop-name">上拉阻值範圍:</span>
                  <span class="prop-val">{{ spec.pullup_range_ohms[0] }}Ω ~ {{ spec.pullup_range_ohms[1] }}Ω</span>
                </div>
                <div v-if="spec.forbid_gnd_capacitor !== undefined" class="prop-item">
                  <span class="prop-name">嚴禁接地電容:</span>
                  <span class="prop-val" :class="spec.forbid_gnd_capacitor ? 'text-red font-bold' : ''">
                    {{ spec.forbid_gnd_capacitor ? '是 (Forbid)' : '否' }}
                  </span>
                </div>
                <div v-if="spec.requires_series_resistor !== undefined" class="prop-item">
                  <span class="prop-name">強制串聯電阻:</span>
                  <span class="prop-val">{{ spec.requires_series_resistor ? '是' : '否' }}</span>
                </div>
                <div v-if="spec.max_bus_capacitance_pf" class="prop-item">
                  <span class="prop-name">最大寄生電容:</span>
                  <span class="prop-val">{{ spec.max_bus_capacitance_pf }} pF</span>
                </div>
                <div v-if="spec.default_address" class="prop-item">
                  <span class="prop-name">預設 7-bit 位址:</span>
                  <span class="prop-val font-mono">{{ spec.default_address }}</span>
                </div>
              </div>

              <!-- 結構化溯源證據 _meta -->
              <div v-if="spec._meta" class="evidence-box">
                <div class="evidence-header">
                  <i class="pi pi-bookmark text-primary mr-1"></i>
                  <span>原廠規格書溯源鐵證 (Datasheet Evidence)</span>
                </div>
                <div class="evidence-body">
                  <div class="evidence-source">
                    <span class="source-file"><i class="pi pi-file-pdf mr-1"></i>{{ spec._meta.evidence }}</span>
                    <span class="source-page">第 {{ spec._meta.page }} 頁</span>
                  </div>
                  <blockquote class="evidence-quote">
                    "{{ spec._meta.excerpt }}"
                  </blockquote>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- TAB 3: Level 2 網路拓撲與匯流排 -->
    <div v-show="activeTab === 'level2'" class="tab-content">
      <div class="level2-grid">
        <div
          v-for="pat in level2Patterns"
          :key="pat.name"
          class="l2-card"
        >
          <div class="l2-card-header">
            <div>
              <span class="l2-category-tag">{{ pat.category }}</span>
              <h3 class="l2-title">{{ pat.name }}</h3>
            </div>
            <div class="l2-header-right">
              <span class="priority-badge">優先級: {{ pat.priority }}</span>
              <button
                type="button"
                class="yaml-view-btn ml-2"
                @click="openYamlModal(pat._filename, pat._raw_yaml)"
              >
                <i class="pi pi-file-code mr-1"></i>YAML
              </button>
            </div>
          </div>

          <div class="l2-signals-list">
            <span class="section-sublabel">訊號群組特徵:</span>
            <div class="signal-chips">
              <span v-for="sig in pat.signals" :key="sig.role" class="signal-chip">
                {{ sig.role }} <small v-if="sig.required">(必備)</small>
              </span>
            </div>
          </div>

          <div v-if="pat.role_overrides && pat.role_overrides.length > 0" class="role-overrides-box">
            <span class="section-sublabel">動態角色覆寫 (Topology Overrides):</span>
            <ul class="overrides-list">
              <li v-for="(ov, idx) in pat.role_overrides" :key="idx">
                <code>{{ ov.original_sub_category }}</code> 連接至 <code>{{ ov.connected_to }}</code> ➔ 覆寫為 <strong>{{ ov.new_role }}</strong>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>

    <!-- TAB 4: Level 1 元件辨識規範 -->
    <div v-show="activeTab === 'level1'" class="tab-content">
      <div class="level1-table-wrapper">
        <table class="level1-table">
          <thead>
            <tr>
              <th style="width: 110px;">優先級</th>
              <th style="width: 240px;">規則名稱 (Rule Name)</th>
              <th style="width: 140px;">主分類 (Category)</th>
              <th style="width: 160px;">次分類 (Sub-Category)</th>
              <th style="width: 160px;">預設功能角色</th>
              <th style="width: 100px;">信心度</th>
              <th style="width: 90px; text-align: center;">YAML</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="rule in sortedLevel1Patterns" :key="rule.name">
              <td>
                <span class="priority-num">{{ rule.priority }}</span>
              </td>
              <td>
                <span class="rule-name-text">{{ rule.name }}</span>
                <p v-if="rule.description" class="rule-desc-text">{{ rule.description }}</p>
              </td>
              <td>
                <span class="cat-pill">{{ rule.assigns?.category }}</span>
              </td>
              <td>
                <span class="subcat-text">{{ rule.assigns?.sub_category }}</span>
              </td>
              <td>
                <span class="role-badge">{{ rule.assigns?.functional_role }}</span>
              </td>
              <td>
                <span class="confidence-text">{{ (rule.assigns?.confidence * 100).toFixed(0) }}%</span>
              </td>
              <td style="text-align: center;">
                <button
                  type="button"
                  class="icon-code-btn"
                  title="檢視 YAML"
                  @click="openYamlModal(rule._filename, rule._raw_yaml)"
                >
                  <i class="pi pi-file-code"></i>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- YAML 原始檔檢視對話框 (Modal) -->
    <div v-if="showYamlModal" class="yaml-modal-overlay" @click.self="showYamlModal = false">
      <div class="yaml-modal-container">
        <div class="yaml-modal-header">
          <div class="modal-title-box">
            <i class="pi pi-file-code text-primary mr-2"></i>
            <span class="modal-filename">{{ currentYamlFilename }}</span>
          </div>
          <div class="modal-header-actions">
            <button type="button" class="copy-code-btn" @click="copyYamlToClipboard">
              <i class="pi pi-copy mr-1"></i>{{ isCopied ? '已複製!' : '複製 YAML' }}
            </button>
            <button type="button" class="modal-close-btn" @click="showYamlModal = false">
              <i class="pi pi-times"></i>
            </button>
          </div>
        </div>
        <div class="yaml-modal-body">
          <pre class="yaml-code-view"><code>{{ currentYamlCode }}</code></pre>
        </div>
      </div>
    </div>

    <!-- GitOps 貢獻指引對話框 (Modal) -->
    <div v-if="showGitOpsGuide" class="yaml-modal-overlay" @click.self="showGitOpsGuide = false">
      <div class="yaml-modal-container gitops-guide-container">
        <div class="yaml-modal-header">
          <div class="modal-title-box">
            <i class="pi pi-book text-primary mr-2"></i>
            <span class="modal-filename">GitOps 規則庫維護與貢獻指引 (Rule Governance SOP)</span>
          </div>
          <button type="button" class="modal-close-btn" @click="showGitOpsGuide = false">
            <i class="pi pi-times"></i>
          </button>
        </div>
        <div class="yaml-modal-body guide-content">
          <h3><i class="pi pi-shield mr-2"></i>核心原則：Git 作為唯一真相來源</h3>
          <p>
            DesignShield 捨棄繁雜的資料庫 CRUD 介面，全面採用 <strong>File-based YAML (IaC)</strong> 存放於 <code>patterns/</code>。
            所有規則增刪改查皆在 IDE 程式碼編輯器中進行，享受 Git PR 審查與版本歷史。
          </p>

          <div class="guide-step-card">
            <h4><span class="step-badge">步驟 1</span> 新增或修改規則 YAML</h4>
            <p>於 <code>patterns/rules/&lt;domain&gt;/</code> 下建立 Level 3 規則 YAML，嚴格填寫 <code>name</code>, <code>tags</code>, <code>severity</code>, <code>trigger_conditions</code>, <code>check_logic</code>。</p>
          </div>

          <div class="guide-step-card">
            <h4><span class="step-badge">步驟 2</span> 本地端執行統一校驗指令</h4>
            <p>提交 PR 前，必須在本地端執行 Python 統一校驗腳本：</p>
            <pre class="cmd-snippet"><code>python scripts/validate_rules.py</code></pre>
          </div>

          <div class="guide-step-card">
            <h4><span class="step-badge">步驟 3</span> 於 Web UI 即時熱載入</h4>
            <p>編輯完成後，可於本頁面右上角點擊「<strong>重新載入規則庫</strong>」按鈕，後端即時掃描磁碟並於介面呈現最新規則！</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * @file RuleManagementView.vue
 * @description DRC 規則庫與知識庫中心，支援 Level 1~3 檔案式 YAML 與 PartDB 視覺化檢視
 */

import { ref, computed, onMounted } from 'vue'
import Button from 'primevue/button'
import { fetchPatternTree, reloadPatterns } from '@/services/api'
import type {
  Level3RuleItem,
  Level2PatternItem,
  Level1PatternItem,
  PartDBItem,
  PatternTreeResponse,
} from '@/types/pattern'

// 狀態控制
const activeTab = ref<'level3' | 'partdb' | 'level2' | 'level1'>('level3')
const isLoading = ref<boolean>(false)
const successMessage = ref<string>('')
const errorMessage = ref<string>('')

// 規則資料結構
const level3Rules = ref<Level3RuleItem[]>([])
const level2Patterns = ref<Level2PatternItem[]>([])
const level1Patterns = ref<Level1PatternItem[]>([])
const partdbParts = ref<PartDBItem[]>([])
const allTags = ref<string[]>([])

// 篩選條件
const searchQuery = ref<string>('')
const selectedDomain = ref<string>('')
const selectedSeverity = ref<string>('')
const selectedTag = ref<string>('')

// YAML 彈跳檢視視窗
const showYamlModal = ref<boolean>(false)
const currentYamlFilename = ref<string>('')
const currentYamlCode = ref<string>('')
const isCopied = ref<boolean>(false)

// GitOps 說明彈窗
const showGitOpsGuide = ref<boolean>(false)

// 載入資料
const loadPatternData = async () => {
  isLoading.value = true
  try {
    const data: PatternTreeResponse = await fetchPatternTree()
    level1Patterns.value = data.level1 || []
    level2Patterns.value = data.level2 || []
    level3Rules.value = data.level3 || []
    partdbParts.value = data.partdb?.parts || []
    allTags.value = data.tags || []
  } catch (err: any) {
    errorMessage.value = `載入規則庫失敗: ${err.message || err}`
  } finally {
    isLoading.value = false
  }
}

// 重新載入規則 (Reload)
const handleReloadPatterns = async () => {
  isLoading.value = true
  successMessage.value = ''
  errorMessage.value = ''
  try {
    const res = await reloadPatterns()
    await loadPatternData()
    successMessage.value = `${res.message} (共載入 Level 3: ${level3Rules.value.length} 條, PartDB: ${partdbParts.value.length} 顆晶片)`
  } catch (err: any) {
    errorMessage.value = `重新載入失敗: ${err.message || err}`
  } finally {
    isLoading.value = false
  }
}

// 計算 Level 3 所有可用網域
const level3Domains = computed(() => {
  const set = new Set<string>()
  level3Rules.value.forEach((r) => {
    if (r._domain) set.add(r._domain)
  })
  return Array.from(set).sort()
})

// Level 3 篩選結果
const filteredLevel3Rules = computed(() => {
  return level3Rules.value.filter((rule) => {
    // 關鍵字
    if (searchQuery.value) {
      const q = searchQuery.value.toLowerCase()
      const matchName = rule.name.toLowerCase().includes(q)
      const matchDesc = (rule.description || '').toLowerCase().includes(q)
      const matchDomain = (rule._domain || '').toLowerCase().includes(q)
      const matchTag = (rule.tags || []).some((t) => t.toLowerCase().includes(q))
      if (!matchName && !matchDesc && !matchDomain && !matchTag) return false
    }
    // 網域
    if (selectedDomain.value && rule._domain !== selectedDomain.value) {
      return false
    }
    // 嚴重度
    if (selectedSeverity.value && rule.severity !== selectedSeverity.value) {
      return false
    }
    // 標籤
    if (selectedTag.value && !rule.tags.includes(selectedTag.value)) {
      return false
    }
    return true
  })
})

// Level 1 依優先級降冪排序
const sortedLevel1Patterns = computed(() => {
  return [...level1Patterns.value].sort((a, b) => b.priority - a.priority)
})

// 開啟 YAML 預覽視窗
const openYamlModal = (filename: string, rawYaml: string) => {
  currentYamlFilename.value = filename
  currentYamlCode.value = rawYaml
  isCopied.value = false
  showYamlModal.value = true
}

// 複製 YAML
const copyYamlToClipboard = async () => {
  try {
    await navigator.clipboard.writeText(currentYamlCode.value)
    isCopied.value = true
    setTimeout(() => {
      isCopied.value = false
    }, 2000)
  } catch {
    // ignore
  }
}

// 輔助函式: 嚴重度樣式
const getSeverityClass = (sev: string): string => {
  switch (sev) {
    case 'Fatal':
      return 'fatal'
    case 'Error':
      return 'error'
    case 'Warning':
      return 'warning'
    default:
      return 'info'
  }
}

const getSeverityIcon = (sev: string): string => {
  switch (sev) {
    case 'Fatal':
      return 'pi pi-bolt'
    case 'Error':
      return 'pi pi-times-circle'
    case 'Warning':
      return 'pi pi-exclamation-triangle'
    default:
      return 'pi pi-info-circle'
  }
}

const formatCheckLogicType = (logic: any[]): string => {
  if (!logic || logic.length === 0) return '拓撲斷言'
  const types = logic.map((l) => {
    if (l.type === 'topology_check') return '拓撲斷言 (Topology Check)'
    if (l.type === 'python_script') return 'PartDB 查表 (Python Script)'
    if (l.type === 'llm_agent') return '大模型推理 (LLM Agent)'
    return l.type
  })
  return types.join(' + ')
}

const formatTriggerSummary = (tc: Record<string, any>): string => {
  if (!tc) return '無特定條件'
  const gm = tc.graph_match?.attributes
  if (gm) {
    const parts = []
    if (gm.type) parts.push(`type: ${gm.type}`)
    if (gm.bus_type) parts.push(`bus: ${gm.bus_type}`)
    if (gm.sub_category) parts.push(`sub_cat: ${gm.sub_category}`)
    if (gm.is_power && gm.is_ground) parts.push(`power & ground`)
    return `{ ${parts.join(', ')} }`
  }
  return JSON.stringify(tc)
}

onMounted(() => {
  loadPatternData()
})
</script>

<style scoped>
.rule-management-view {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  padding: 1.5rem;
  background-color: var(--surface-ground, #0f172a);
  color: var(--text-color, #f8fafc);
  min-height: 100vh;
}

/* 頁頭 */
.rules-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.page-title {
  font-size: 1.5rem;
  font-weight: 700;
  margin: 0 0 0.5rem 0;
  display: flex;
  align-items: center;
}

.page-subtitle {
  color: #94a3b8;
  font-size: 0.875rem;
  margin: 0;
}

.header-actions {
  display: flex;
  gap: 0.75rem;
}

/* 提示橫幅 */
.alert-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1rem;
  border-radius: 6px;
  font-size: 0.875rem;
}

.success-banner {
  background-color: rgba(34, 197, 94, 0.15);
  border: 1px solid rgba(34, 197, 94, 0.3);
  color: #4ade80;
}

.error-banner {
  background-color: rgba(239, 68, 68, 0.15);
  border: 1px solid rgba(239, 68, 68, 0.3);
  color: #f87171;
}

.banner-close {
  background: none;
  border: none;
  color: inherit;
  cursor: pointer;
}

/* 統計指標卡片 */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1rem;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem 1.25rem;
  background-color: var(--surface-card, #1e293b);
  border: 1px solid #334155;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.stat-card:hover, .stat-card.active {
  border-color: #38bdf8;
  background-color: #1e293b;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(56, 189, 248, 0.1);
}

.stat-icon-wrapper {
  width: 44px;
  height: 44px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.25rem;
}

.bg-red-light { background-color: rgba(239, 68, 68, 0.15); }
.text-red { color: #f87171; }
.bg-indigo-light { background-color: rgba(99, 102, 241, 0.15); }
.text-indigo { color: #818cf8; }
.bg-blue-light { background-color: rgba(56, 189, 248, 0.15); }
.text-blue { color: #38bdf8; }
.bg-green-light { background-color: rgba(34, 197, 94, 0.15); }
.text-green { color: #4ade80; }

.stat-info {
  display: flex;
  flex-direction: column;
}

.stat-label {
  font-size: 0.75rem;
  color: #94a3b8;
}

.stat-value {
  font-size: 1.35rem;
  font-weight: 700;
  color: #f8fafc;
}

.unit {
  font-size: 0.75rem;
  font-weight: 400;
  color: #64748b;
}

/* 分頁按鈕 */
.tabs-nav {
  display: flex;
  gap: 0.5rem;
  border-bottom: 1px solid #334155;
  padding-bottom: 0.25rem;
}

.tab-btn {
  padding: 0.6rem 1.2rem;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  color: #94a3b8;
  font-weight: 600;
  font-size: 0.875rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  transition: all 0.2s;
}

.tab-btn:hover {
  color: #f8fafc;
}

.tab-btn.active {
  color: #38bdf8;
  border-bottom-color: #38bdf8;
}

/* 篩選卡片 */
.filter-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.85rem 1.25rem;
  background-color: var(--surface-card, #1e293b);
  border: 1px solid #334155;
  border-radius: 8px;
}

.filter-controls {
  display: flex;
  gap: 0.75rem;
  flex: 1;
}

.search-input-wrapper {
  position: relative;
  width: 320px;
}

.search-icon {
  position: absolute;
  left: 0.75rem;
  top: 50%;
  transform: translateY(-50%);
  color: #64748b;
}

.filter-search-input {
  width: 100%;
  padding: 0.5rem 2rem 0.5rem 2.25rem;
  background-color: #0f172a;
  border: 1px solid #334155;
  border-radius: 6px;
  color: #f8fafc;
  font-size: 0.875rem;
}

.clear-btn {
  position: absolute;
  right: 0.5rem;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  color: #64748b;
  cursor: pointer;
}

.filter-select-group {
  display: flex;
  gap: 0.5rem;
}

.filter-select {
  padding: 0.5rem 0.75rem;
  background-color: #0f172a;
  border: 1px solid #334155;
  border-radius: 6px;
  color: #f8fafc;
  font-size: 0.875rem;
}

.filter-summary {
  font-size: 0.85rem;
  color: #94a3b8;
}

/* 規則卡片 Grid */
.rules-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: 1rem;
  margin-top: 1rem;
}

.rule-card {
  background-color: var(--surface-card, #1e293b);
  border: 1px solid #334155;
  border-radius: 8px;
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  transition: transform 0.2s, box-shadow 0.2s;
}

.rule-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
}

.border-fatal { border-left: 4px solid #ef4444; }
.border-error { border-left: 4px solid #f97316; }
.border-warning { border-left: 4px solid #eab308; }
.border-info { border-left: 4px solid #38bdf8; }

.rule-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-badges {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.severity-badge {
  font-size: 0.75rem;
  font-weight: 700;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
}

.severity-badge.fatal { background-color: rgba(239, 68, 68, 0.2); color: #f87171; }
.severity-badge.error { background-color: rgba(249, 115, 22, 0.2); color: #fb923c; }
.severity-badge.warning { background-color: rgba(234, 179, 8, 0.2); color: #facc15; }
.severity-badge.info { background-color: rgba(56, 189, 248, 0.2); color: #38bdf8; }

.domain-badge {
  font-size: 0.75rem;
  color: #94a3b8;
  background-color: #0f172a;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
}

.yaml-view-btn {
  background-color: #0f172a;
  border: 1px solid #334155;
  color: #38bdf8;
  padding: 0.25rem 0.6rem;
  border-radius: 4px;
  font-size: 0.75rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  transition: all 0.2s;
}

.yaml-view-btn:hover {
  background-color: #38bdf8;
  color: #0f172a;
}

.rule-title {
  font-size: 1.05rem;
  font-weight: 600;
  margin: 0 0 0.35rem 0;
  color: #f8fafc;
}

.rule-desc {
  font-size: 0.85rem;
  color: #94a3b8;
  line-height: 1.4;
  margin: 0 0 0.75rem 0;
}

.rule-meta-section {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  font-size: 0.8rem;
  background-color: #0f172a;
  padding: 0.6rem;
  border-radius: 6px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.meta-label {
  color: #64748b;
  min-width: 60px;
}

.check-type-pill {
  color: #e2e8f0;
  font-weight: 500;
}

.tags-container {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
}

.rule-tag-chip {
  background-color: #1e293b;
  color: #38bdf8;
  padding: 0.15rem 0.4rem;
  border-radius: 3px;
  font-size: 0.7rem;
  border: 1px solid #334155;
}

.rule-condition-box {
  margin-top: 0.5rem;
  font-size: 0.75rem;
}

.cond-title {
  color: #94a3b8;
  font-weight: 600;
}

.cond-code {
  font-family: monospace;
  background-color: #090d16;
  color: #f1f5f9;
  padding: 0.2rem 0.4rem;
  border-radius: 4px;
}

/* PartDB 樣式 */
.partdb-banner {
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.15), rgba(56, 189, 248, 0.15));
  border: 1px solid rgba(99, 102, 241, 0.3);
  border-radius: 8px;
  padding: 1.25rem;
  margin-bottom: 1.25rem;
}

.partdb-banner-info h3 {
  margin: 0 0 0.35rem 0;
  font-size: 1.15rem;
  color: #f8fafc;
}

.partdb-banner-info p {
  margin: 0;
  font-size: 0.85rem;
  color: #cbd5e1;
  line-height: 1.5;
}

.partdb-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(420px, 1fr));
  gap: 1.25rem;
}

.part-card {
  background-color: var(--surface-card, #1e293b);
  border: 1px solid #334155;
  border-radius: 8px;
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
}

.part-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.part-title-wrapper {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.part-icon {
  width: 38px;
  height: 38px;
  border-radius: 6px;
  background-color: rgba(99, 102, 241, 0.2);
  color: #818cf8;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.25rem;
}

.part-pn {
  margin: 0;
  font-size: 1.15rem;
  font-weight: 700;
  color: #f8fafc;
}

.part-file-label {
  font-size: 0.75rem;
  color: #64748b;
}

.part-desc {
  font-size: 0.85rem;
  color: #94a3b8;
  margin: 0;
}

.interfaces-section {
  margin-top: 0.5rem;
}

.iface-title {
  font-size: 0.85rem;
  color: #cbd5e1;
  margin: 0 0 0.5rem 0;
}

.iface-box {
  background-color: #0f172a;
  border: 1px solid #334155;
  border-radius: 6px;
  padding: 0.85rem;
  margin-bottom: 0.75rem;
}

.iface-badge {
  background-color: #4f46e5;
  color: #ffffff;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
}

.iface-props {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.5rem;
  margin: 0.75rem 0;
  font-size: 0.8rem;
}

.prop-item {
  display: flex;
  flex-direction: column;
}

.prop-name {
  color: #64748b;
  font-size: 0.75rem;
}

.prop-val {
  color: #f8fafc;
  font-weight: 600;
}

.evidence-box {
  background-color: #1e293b;
  border-left: 3px solid #38bdf8;
  padding: 0.6rem;
  border-radius: 4px;
  margin-top: 0.5rem;
}

.evidence-header {
  font-size: 0.75rem;
  font-weight: 600;
  color: #38bdf8;
  margin-bottom: 0.35rem;
}

.evidence-source {
  display: flex;
  justify-content: space-between;
  font-size: 0.75rem;
  color: #cbd5e1;
}

.evidence-quote {
  margin: 0.35rem 0 0 0;
  font-size: 0.75rem;
  color: #94a3b8;
  font-style: italic;
  line-height: 1.35;
}

/* Level 2 樣式 */
.level2-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: 1rem;
}

.l2-card {
  background-color: var(--surface-card, #1e293b);
  border: 1px solid #334155;
  border-radius: 8px;
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.l2-card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.l2-category-tag {
  font-size: 0.75rem;
  background-color: rgba(56, 189, 248, 0.2);
  color: #38bdf8;
  padding: 0.15rem 0.4rem;
  border-radius: 4px;
}

.l2-title {
  margin: 0.25rem 0 0 0;
  font-size: 1.1rem;
  font-weight: 600;
}

.priority-badge {
  font-size: 0.75rem;
  background-color: #0f172a;
  color: #94a3b8;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
}

.section-sublabel {
  font-size: 0.75rem;
  color: #64748b;
  display: block;
  margin-bottom: 0.25rem;
}

.signal-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
}

.signal-chip {
  background-color: #0f172a;
  border: 1px solid #334155;
  padding: 0.2rem 0.45rem;
  border-radius: 4px;
  font-size: 0.75rem;
}

.overrides-list {
  margin: 0;
  padding-left: 1.25rem;
  font-size: 0.75rem;
  color: #cbd5e1;
}

/* Level 1 表格樣式 */
.level1-table-wrapper {
  background-color: var(--surface-card, #1e293b);
  border: 1px solid #334155;
  border-radius: 8px;
  overflow-x: auto;
}

.level1-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.875rem;
}

.level1-table th, .level1-table td {
  padding: 0.85rem 1rem;
  text-align: left;
  border-bottom: 1px solid #334155;
}

.level1-table th {
  background-color: #0f172a;
  color: #94a3b8;
  font-weight: 600;
  font-size: 0.8rem;
}

.priority-num {
  font-weight: 700;
  color: #38bdf8;
}

.rule-name-text {
  font-weight: 600;
  color: #f8fafc;
}

.rule-desc-text {
  margin: 0.2rem 0 0 0;
  font-size: 0.75rem;
  color: #94a3b8;
}

.cat-pill {
  background-color: rgba(34, 197, 94, 0.2);
  color: #4ade80;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
}

.icon-code-btn {
  background: none;
  border: none;
  color: #38bdf8;
  font-size: 1.1rem;
  cursor: pointer;
}

/* YAML Modal */
.yaml-modal-overlay {
  position: fixed;
  inset: 0;
  background-color: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 999;
}

.yaml-modal-container {
  background-color: #0f172a;
  border: 1px solid #334155;
  border-radius: 8px;
  width: 720px;
  max-width: 90vw;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
}

.gitops-guide-container {
  width: 640px;
}

.yaml-modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid #334155;
}

.modal-title-box {
  display: flex;
  align-items: center;
  font-weight: 600;
  color: #f8fafc;
}

.modal-header-actions {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.copy-code-btn {
  background-color: #1e293b;
  border: 1px solid #334155;
  color: #38bdf8;
  padding: 0.35rem 0.75rem;
  border-radius: 4px;
  font-size: 0.8rem;
  cursor: pointer;
}

.modal-close-btn {
  background: none;
  border: none;
  color: #94a3b8;
  cursor: pointer;
  font-size: 1.1rem;
}

.yaml-modal-body {
  padding: 1.25rem;
  overflow-y: auto;
}

.yaml-code-view {
  margin: 0;
  background-color: #050811;
  color: #f8fafc;
  padding: 1rem;
  border-radius: 6px;
  font-family: 'Fira Code', monospace;
  font-size: 0.85rem;
  line-height: 1.45;
  overflow-x: auto;
}

/* Guide 樣式 */
.guide-content h3 {
  margin: 0 0 0.5rem 0;
  font-size: 1.1rem;
  color: #38bdf8;
}

.guide-content p {
  color: #cbd5e1;
  font-size: 0.875rem;
  line-height: 1.5;
}

.guide-step-card {
  background-color: #1e293b;
  border: 1px solid #334155;
  border-radius: 6px;
  padding: 0.85rem 1rem;
  margin-top: 0.75rem;
}

.guide-step-card h4 {
  margin: 0 0 0.35rem 0;
  font-size: 0.95rem;
  display: flex;
  align-items: center;
}

.step-badge {
  background-color: #38bdf8;
  color: #0f172a;
  font-size: 0.75rem;
  font-weight: 700;
  padding: 0.15rem 0.4rem;
  border-radius: 4px;
  margin-right: 0.5rem;
}

.cmd-snippet {
  background-color: #090d16;
  color: #4ade80;
  padding: 0.5rem 0.75rem;
  border-radius: 4px;
  font-family: monospace;
  font-size: 0.85rem;
  margin: 0.5rem 0 0 0;
}
</style>
