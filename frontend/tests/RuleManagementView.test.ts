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
        pn: 'STM32F405',
        description: 'ARM Cortex-M4 微控制器',
        interfaces: {
          I2C: {
            forbid_gnd_capacitor: true,
            pullup_range_ohms: [2000, 10000],
            _meta: {
              evidence: 'STM32F405_Datasheet_Rev4.pdf',
              page: 45,
              excerpt: 'In Fast-mode Plus, avoid external ground capacitors.',
            },
          },
        },
        _filename: 'STM32F405.yaml',
        _raw_yaml: 'pn: STM32F405\ninterfaces:\n  I2C:\n    forbid_gnd_capacitor: true\n',
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

  it('支援切換至 PartDB 分頁並展示晶片特規與規格書溯源鐵證', async () => {
    const wrapper = mount(RuleManagementView, {
      global: {
        plugins: [PrimeVue],
      },
    })

    await vi.waitFor(() => {
      expect(wrapper.text()).toContain('I2C_Pull_Up_Existence')
    })

    // 點擊 PartDB 分頁按鈕
    const partdbTabBtn = wrapper.findAll('.tab-btn').find((b) => b.text().includes('PartDB'))
    expect(partdbTabBtn).toBeDefined()
    await partdbTabBtn?.trigger('click')

    const text = wrapper.text()
    expect(text).toContain('STM32F405')
    expect(text).toContain('嚴禁接地電容')
    expect(text).toContain('2000Ω ~ 10000Ω')
    expect(text).toContain('STM32F405_Datasheet_Rev4.pdf')
    expect(text).toContain('第 45 頁')
    expect(text).toContain('avoid external ground capacitors')
  })

  it('支援切換至 Level 2 與 Level 1 分頁', async () => {
    const wrapper = mount(RuleManagementView, {
      global: {
        plugins: [PrimeVue],
      },
    })

    await vi.waitFor(() => {
      expect(wrapper.text()).toContain('I2C_Pull_Up_Existence')
    })

    // 切換至 Level 2
    const l2Btn = wrapper.findAll('.tab-btn').find((b) => b.text().includes('Level 2'))
    await l2Btn?.trigger('click')
    expect(wrapper.text()).toContain('動態角色覆寫')
    expect(wrapper.text()).toContain('Pull_up')

    // 切換至 Level 1
    const l1Btn = wrapper.findAll('.tab-btn').find((b) => b.text().includes('Level 1'))
    await l1Btn?.trigger('click')
    expect(wrapper.text()).toContain('rule_ic_mcu')
    expect(wrapper.text()).toContain('Bus_Master')
    expect(wrapper.text()).toContain('95%')
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
})
