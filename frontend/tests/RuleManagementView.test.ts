/**
 * @file RuleManagementView.test.ts
 * @description RuleManagementView 規則庫與知識庫中心單元測試
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import PrimeVue from 'primevue/config'
import RuleManagementView from '@/views/RuleManagementView.vue'
import * as api from '@/services/api'
import type { PatternTreeResponse } from '@/types/pattern'

vi.mock('@/services/api', () => ({
  fetchPatternTree: vi.fn(),
  reloadPatterns: vi.fn(),
  fetchPatternTags: vi.fn(),
  fetchRules: vi.fn(),
  createRule: vi.fn(),
  updateRule: vi.fn(),
  deleteRule: vi.fn(),
}))

const mockPatternTree: PatternTreeResponse = {
  level3: [
    {
      name: 'I2C_Pull_Up_Existence',
      description: 'I2C 匯流排上拉電阻存在性檢查',
      tags: ['I2C', 'Signal Integrity'],
      severity: 'Error',
      trigger_conditions: { graph_match: { attributes: { type: 'net', bus_type: 'I2C' } } },
      check_logic: [{ type: 'topology_check' }],
      _domain: 'interfaces',
      _filename: 'i2c_pullup_existence.yaml',
      _rel_path: 'rules/interfaces/i2c_pullup_existence.yaml',
      _raw_yaml: 'name: I2C_Pull_Up_Existence\nseverity: Error\n',
    },
    {
      name: 'Power_Ground_Short_Fatal',
      description: '電源-接地短路致命異常檢測',
      tags: ['Power Domain', 'Short Circuit', 'Fatal'],
      severity: 'Fatal',
      trigger_conditions: { graph_match: { attributes: { type: 'net', is_power: true, is_ground: true } } },
      check_logic: [{ type: 'topology_check' }],
      _domain: 'power',
      _filename: 'power_ground_short.yaml',
      _rel_path: 'rules/power/power_ground_short.yaml',
      _raw_yaml: 'name: Power_Ground_Short_Fatal\nseverity: Fatal\n',
    },
  ],
  partdb: {
    parts: [
      {
        pn: 'TPS66994',
        mfg: 'TI',
        mfg_pn: 'TPS66994',
        description: 'Dual Port USB Type-C & PD 控制晶片',
        interfaces: {
          I2C: {
            forbid_gnd_capacitor: false,
            pullup_range_ohms: [1000, 2400],
            _meta: {
              evidence: 'TI_TPS66994CBREPR.pdf',
              page: 21,
              excerpt: 'Cb: Capacitive load for each bus line (external), MAX 400 pF.',
            },
          },
        },
        _filename: 'TI_TPS66994.yaml',
        _raw_yaml: 'mfg: TI\npn: TPS66994\n',
      },
    ],
    schemas: {},
  },
  level2: [
    {
      name: 'I2C',
      category: 'Communication',
      priority: 700,
      signals: [{ role: 'SCL', required: true }, { role: 'SDA', required: true }],
      role_overrides: [
        { original_sub_category: 'Resistor', connected_to: 'PowerRail', new_role: 'Pull_up' },
      ],
      _domain: 'buses',
      _filename: '700_i2c.yaml',
      _raw_yaml: 'name: I2C\npriority: 700\n',
    },
  ],
  level1: [
    {
      name: 'rule_ic_mcu',
      description: '辨識主控晶片',
      priority: 900,
      matches: {},
      assigns: {
        category: 'IC',
        sub_category: 'Microcontroller',
        functional_role: 'Bus_Master',
        is_electrical: true,
        confidence: 0.95,
      },
      _filename: '850_ic_connector.yaml',
      _raw_yaml: 'name: rule_ic_mcu\npriority: 900\n',
    },
  ],
  tags: ['I2C', 'Signal Integrity', 'Power Domain', 'Short Circuit', 'Fatal'],
  summary: {
    level1_count: 1,
    level2_count: 1,
    level3_count: 2,
    partdb_parts_count: 1,
    tags_count: 5,
  },
}

describe('RuleManagementView.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.fetchPatternTree).mockResolvedValue(JSON.parse(JSON.stringify(mockPatternTree)))
    vi.mocked(api.reloadPatterns).mockResolvedValue({
      success: true,
      message: '規則庫重新載入成功',
      summary: mockPatternTree.summary,
    })
  })

  it('正確渲染規則庫中心頁面、四大統計卡片與 Level 3 規則清單', async () => {
    const wrapper = mount(RuleManagementView, {
      global: {
        plugins: [PrimeVue],
      },
    })

    await vi.waitFor(() => {
      expect(wrapper.text()).toContain('I2C_Pull_Up_Existence')
    })

    const text = wrapper.text()
    // 頁頭與標題
    expect(text).toContain('DRC 規則庫與知識庫中心')
    expect(text).toContain('GitOps')

    // 統計卡片
    expect(text).toContain('Level 3: DRC 驗證規範')
    expect(text).toContain('PartDB: 零件特規庫')
    expect(text).toContain('Level 2: 網路拓撲與匯流排')
    expect(text).toContain('Level 1: 元件辨識規範')

    // Level 3 規則列表內容
    expect(text).toContain('I2C_Pull_Up_Existence')
    expect(text).toContain('I2C 匯流排上拉電阻存在性檢查')
    expect(text).toContain('Power_Ground_Short_Fatal')
    expect(text).toContain('Fatal')
  })

  it('支援關鍵字搜尋過濾 Level 3 規則', async () => {
    const wrapper = mount(RuleManagementView, {
      global: {
        plugins: [PrimeVue],
      },
    })

    await vi.waitFor(() => {
      expect(wrapper.text()).toContain('I2C_Pull_Up_Existence')
    })

    const searchInput = wrapper.find('.filter-search-input')
    await searchInput.setValue('Fatal')

    const text = wrapper.text()
    expect(text).toContain('Power_Ground_Short_Fatal')
    expect(text).not.toContain('I2C_Pull_Up_Existence')
  })

  it('支援點擊統計卡片或 Filter 快速聯動目錄樹過濾層級', async () => {
    const wrapper = mount(RuleManagementView, {
      global: {
        plugins: [PrimeVue],
      },
    })


    await vi.waitFor(() => {
      expect(wrapper.text()).toContain('I2C_Pull_Up_Existence')
    })

    // 點擊 Level 1 統計卡片
    const l1Card = wrapper.findAll('.stat-card').find((c) => c.text().includes('Level 1'))
    expect(l1Card).toBeDefined()
    await l1Card?.trigger('click')

    // 驗證過濾後包含 Level 1 規則，且不包含 Level 3 規則
    await vi.waitFor(() => {
      expect(wrapper.text()).toContain('rule_ic_mcu')
      expect(wrapper.text()).not.toContain('I2C_Pull_Up_Existence')
    })

    // 點擊 Level 3 統計卡片恢復
    const l3Card = wrapper.findAll('.stat-card').find((c) => c.text().includes('Level 3'))
    await l3Card?.trigger('click')
    await vi.waitFor(() => {
      expect(wrapper.text()).toContain('I2C_Pull_Up_Existence')
      expect(wrapper.text()).not.toContain('rule_ic_mcu')
    })
  })


  it('支援點擊「重新載入規則庫」按鈕熱重載，並呈現編譯快取統計', async () => {
    vi.mocked(api.reloadPatterns).mockResolvedValue({
      success: true,
      message: '規則庫與編譯快取重新載入成功 (耗時 12.5ms)',
      summary: mockPatternTree.summary,
      compile_stats: {
        level1_rules: 10,
        level2_rules: 5,
        level3_rules: 20,
        partdb_parts: 4,
        regex_compiled: 45,
        compile_time_ms: 12.5,
      },
    })

    const wrapper = mount(RuleManagementView, {
      global: {
        plugins: [PrimeVue],
      },
    })

    await vi.waitFor(() => {
      expect(wrapper.text()).toContain('I2C_Pull_Up_Existence')
    })

    const reloadBtn = wrapper.findAll('button').find((b) => b.text().includes('重新載入規則庫'))
    expect(reloadBtn).toBeDefined()
    await reloadBtn?.trigger('click')

    expect(api.reloadPatterns).toHaveBeenCalledTimes(1)
    await vi.waitFor(() => {
      expect(wrapper.text()).toContain('規則庫與編譯快取重新載入成功')
      expect(wrapper.text()).toContain('Level 1: 10')
      expect(wrapper.text()).toContain('Regex 快取: 45')
    })
  })

  it('當 YAML 校驗失敗時，取消編譯並展示可展開之詳細錯誤清單', async () => {
    vi.mocked(api.reloadPatterns).mockResolvedValue({
      success: false,
      message: 'YAML 校驗失敗，已取消編譯 (發現 2 項錯誤)',
      errors: [
        '[Level 3] rules/interfaces/i2c.yaml: 缺少必填欄位 severity',
        '[Level 1] components/mcu.yaml: 正規表示式語法錯誤',
      ],
    })

    const wrapper = mount(RuleManagementView, {
      global: {
        plugins: [PrimeVue],
      },
    })

    await vi.waitFor(() => {
      expect(wrapper.text()).toContain('I2C_Pull_Up_Existence')
    })

    const reloadBtn = wrapper.findAll('button').find((b) => b.text().includes('重新載入規則庫'))
    await reloadBtn?.trigger('click')

    await vi.waitFor(() => {
      expect(wrapper.text()).toContain('YAML 校驗失敗，已取消編譯')
    })

    // 展開詳細錯誤按鈕
    const toggleBtn = wrapper.find('.detail-toggle-btn')
    expect(toggleBtn.exists()).toBe(true)
    expect(toggleBtn.text()).toContain('查看詳細錯誤 (2)')

    // 尚未展開時不應看見錯誤列表容器
    expect(wrapper.find('.error-details-list').exists()).toBe(false)

    // 點擊展開
    await toggleBtn.trigger('click')
    expect(wrapper.find('.error-details-list').exists()).toBe(true)
    expect(wrapper.text()).toContain('rules/interfaces/i2c.yaml: 缺少必填欄位 severity')
    expect(wrapper.text()).toContain('components/mcu.yaml: 正規表示式語法錯誤')
    expect(toggleBtn.text()).toContain('收起詳細錯誤')

    // 點擊收起
    await toggleBtn.trigger('click')
    expect(wrapper.find('.error-details-list').exists()).toBe(false)
  })

  it('支援開啟 GitOps 貢獻手冊與檢視 YAML 對話框', async () => {
    const wrapper = mount(RuleManagementView, {
      global: {
        plugins: [PrimeVue],
      },
    })

    await vi.waitFor(() => {
      expect(wrapper.text()).toContain('I2C_Pull_Up_Existence')
    })

    // 點擊 GitOps 貢獻手冊
    const guideBtn = wrapper.findAll('button').find((b) => b.text().includes('GitOps 貢獻手冊'))
    expect(guideBtn).toBeDefined()
    await guideBtn?.trigger('click')

    expect(wrapper.text()).toContain('GitOps 規則庫維護與貢獻指引')
    expect(wrapper.text()).toContain('python scripts/validate_rules.py')

    // 點擊關閉
    const closeBtn = wrapper.find('.modal-close-btn')
    await closeBtn.trigger('click')
    expect(wrapper.text()).not.toContain('GitOps 規則庫維護與貢獻指引')
  })

  it('支援呈現啟用與停用狀態，且支援在目錄樹工具列進行狀態篩選', async () => {
    const customTree: PatternTreeResponse = {
      ...mockPatternTree,
      level3: [
        {
          name: 'rule_l3_enabled',
          description: '已啟用的 L3 規則',
          tags: ['I2C'],
          severity: 'Error',
          enabled: true,
          trigger_conditions: {},
          check_logic: [{ type: 'topology_check' }],
          _domain: 'interfaces',
          _filename: 'l3_enabled.yaml',
          _rel_path: 'rules/interfaces/l3_enabled.yaml',
          _raw_yaml: 'name: rule_l3_enabled\n',
        },
        {
          name: 'rule_l3_disabled',
          description: '已停用的 L3 規則',
          tags: ['Power'],
          severity: 'Warning',
          enabled: false,
          trigger_conditions: {},
          check_logic: [{ type: 'topology_check' }],
          _domain: 'power',
          _filename: 'l3_disabled.yaml',
          _rel_path: 'rules/power/l3_disabled.yaml',
          _raw_yaml: 'name: rule_l3_disabled\n',
        },
      ],
      level2: [
        {
          name: 'rule_l2_disabled',
          category: 'Communication',
          priority: 500,
          enabled: false,
          _domain: 'buses',
          _filename: 'l2_disabled.yaml',
          _raw_yaml: 'name: rule_l2_disabled\n',
        },
      ],
      level1: [
        {
          name: 'rule_l1_disabled',
          description: '已停用元件規則',
          priority: 800,
          enabled: false,
          matches: {},
          assigns: {
            category: 'Passive',
            sub_category: 'Resistor',
            functional_role: 'Passive_Support',
            is_electrical: true,
            confidence: 0.9,
          },
          _filename: 'l1_disabled.yaml',
          _raw_yaml: 'name: rule_l1_disabled\n',
        },
      ],
    }

    vi.mocked(api.fetchPatternTree).mockResolvedValue(customTree)

    const wrapper = mount(RuleManagementView, {
      global: {
        plugins: [PrimeVue],
      },
    })

    await vi.waitFor(() => {
      expect(wrapper.text()).toContain('rule_l3_enabled')
      expect(wrapper.text()).toContain('rule_l3_disabled')
    })

    // 檢查停用規則列是否帶有 opacity-60
    const disabledRuleRow = wrapper.findAll('.rule-row').find((c) => c.text().includes('rule_l3_disabled'))
    expect(disabledRuleRow?.classes()).toContain('opacity-60')

    // 測試狀態篩選選單
    const statusSelect = wrapper.find<HTMLSelectElement>('.filter-status-select')
    expect(statusSelect.exists()).toBe(true)

    // 切換為「僅顯示已啟用」
    await statusSelect.setValue('enabled')
    expect(wrapper.text()).toContain('rule_l3_enabled')
    expect(wrapper.text()).not.toContain('rule_l3_disabled')

    // 切換為「僅顯示已停用」
    await statusSelect.setValue('disabled')
    expect(wrapper.text()).not.toContain('rule_l3_enabled')
    expect(wrapper.text()).toContain('rule_l3_disabled')
    expect(wrapper.text()).toContain('rule_l2_disabled')
    expect(wrapper.text()).toContain('rule_l1_disabled')
  })

  it('下拉式選單與上方統計卡片雙向連動，且標題說明文字已移除', async () => {
    const wrapper = mount(RuleManagementView, {
      global: {
        plugins: [PrimeVue],
      },
    })

    await vi.waitFor(() => {
      expect(wrapper.text()).toContain('DRC 規則庫與知識庫中心')
    })

    // 1. 驗證說明文字已被移除
    expect(wrapper.text()).not.toContain('全域硬體檢查規範集中檢視中心，支援 GitOps File-based YAML 檔案架構與即時熱載入。')

    // 2. 測試下拉選單變更 -> 上方卡片連動高亮
    const levelSelect = wrapper.find<HTMLSelectElement>('.filter-level-select')
    expect(levelSelect.exists()).toBe(true)

    // 切換下拉選單至 level2
    await levelSelect.setValue('level2')
    await vi.waitFor(() => {
      const l2Card = wrapper.findAll('.stat-card').find((c) => c.text().includes('Level 2'))
      expect(l2Card?.classes()).toContain('active')
    })

    // 3. 測試點擊上方卡片 -> 下拉選單連動
    const l1Card = wrapper.findAll('.stat-card').find((c) => c.text().includes('Level 1'))
    await l1Card?.trigger('click')
    await vi.waitFor(() => {
      expect((wrapper.find('.filter-level-select').element as HTMLSelectElement).value).toBe('level1')
    })
  })
})

