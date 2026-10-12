/**
 * @file RuleTreeSelector.test.ts
 * @description RuleTreeSelector 元件單元測試
 */

import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import PrimeVue from 'primevue/config'
import RuleTreeSelector from '@/components/RuleTreeSelector.vue'

describe('RuleTreeSelector.vue', () => {
  it('正確渲染特徵摘要與推薦規則列表', () => {
    const mockSummary = {
      buses: ['I2C', 'SPI'],
      platforms: ['STM32'],
      component_count: 84,
      net_count: 156,
    }
    const mockRules = [
      {
        id: 'RULE-BUS-I2C-ADDR',
        name: 'I2C 匯流排地址唯一性檢查',
        category: 'Bus Integrity',
      },
      {
        id: 'RULE-PWR-CAP-DERATING',
        name: '電源濾波電容耐壓降額檢查',
        category: 'Power Domain',
      },
    ]

    const wrapper = mount(RuleTreeSelector, {
      global: {
        plugins: [PrimeVue],
      },
      props: {
        summary: mockSummary,
        recommendedRules: mockRules,
      },
    })

    const text = wrapper.text()
    expect(text).toContain('元件總數:84')
    expect(text).toContain('網路總數:156')
    expect(text).toContain('I2C, SPI')
    expect(text).toContain('STM32')
    expect(text).toContain('Bus Integrity')
    expect(text).toContain('Power Domain')
    expect(text).toContain('I2C 匯流排地址唯一性檢查')
  })

  it('支援點選全選按鈕切換勾選狀態', async () => {
    const mockRules = [
      {
        id: 'RULE-1',
        name: '規則一',
        category: 'TestCat',
      },
      {
        id: 'RULE-2',
        name: '規則二',
        category: 'TestCat',
      },
    ]

    const wrapper = mount(RuleTreeSelector, {
      global: {
        plugins: [PrimeVue],
      },
      props: {
        summary: { buses: [], platforms: [], component_count: 2, net_count: 2 },
        recommendedRules: mockRules,
      },
    })

    // 初始預設全選
    expect(wrapper.text()).toContain('已選取 2 條規則')

    // 點擊切換全選/取消全選
    const toggleBtn = wrapper.findAll('button').find((b) => b.text().includes('取消全選'))
    expect(toggleBtn).toBeDefined()
    await toggleBtn?.trigger('click')

    expect(wrapper.text()).toContain('已選取 0 條規則')
  })

  it('樹狀結構列出所有規則並允許勾選未被推薦之規則', async () => {
    const mockRecommended = [
      {
        id: 'RULE-REC-01',
        name: '推薦規則A',
        category: 'Power Domain',
      },
    ]

    const mockAllRules = [
      {
        id: 'RULE-REC-01',
        name: '推薦規則A',
        category: 'Power Domain',
        check_type: 'HEURISTIC' as const,
        is_active: true,
        parameters: {},
      },
      {
        id: 'RULE-UNREC-02',
        name: '未推薦自選規則B',
        category: 'Power Domain',
        check_type: 'HEURISTIC' as const,
        is_active: true,
        parameters: {},
      },
      {
        id: 'RULE-UNREC-03',
        name: '訊號完整性自選規則C',
        category: 'Signal Integrity',
        check_type: 'LLM' as const,
        is_active: true,
        parameters: {},
      },
    ]

    const wrapper = mount(RuleTreeSelector, {
      global: {
        plugins: [PrimeVue],
      },
      props: {
        summary: { buses: ['I2C'], platforms: ['STM32'], component_count: 10, net_count: 20 },
        recommendedRules: mockRecommended,
        allRules: mockAllRules,
      },
    })

    const text = wrapper.text()
    // 檢查樹狀結構與分類節點
    expect(text).toContain('Power Domain')
    expect(text).toContain('Signal Integrity')
    // 推薦規則與標籤
    expect(text).toContain('推薦規則A')
    expect(text).toContain('推薦')
    // 未推薦規則存在並可見
    expect(text).toContain('未推薦自選規則B')
    expect(text).toContain('未推薦 (可自選)')
    expect(text).toContain('訊號完整性自選規則C')

    // 初始預設僅勾選推薦規則 1 條
    expect(text).toContain('已選取 1 條規則')

    // 找到未推薦規則 B 的 checkbox 並勾選
    const checkboxes = wrapper.findAll<HTMLInputElement>('input[type="checkbox"]')
    const unrecCheckbox = checkboxes.find((cb) => cb.element.value === 'RULE-UNREC-02')
    expect(unrecCheckbox).toBeDefined()
    await unrecCheckbox?.setValue(true)

    // 已選取數量更新為 2 條
    expect(wrapper.text()).toContain('已選取 2 條規則')
    expect(wrapper.text()).toContain('1 條額外選取規則')
  })

  it('當無任何規則存在時，呈現無規則可選且確認按鈕禁用', () => {
    const wrapper = mount(RuleTreeSelector, {
      global: {
        plugins: [PrimeVue],
      },
      props: {
        summary: { buses: [], platforms: [], component_count: 0, net_count: 0 },
        recommendedRules: [],
        allRules: [],
      },
    })

    const text = wrapper.text()
    expect(text).toContain('無規則可選')
    expect(text).toContain('已選取 0 條規則')

    const confirmBtn = wrapper.find('button.confirm-run-btn')
    expect(confirmBtn.exists()).toBe(true)
    expect(confirmBtn.attributes('disabled')).toBeDefined()
  })

  it('支援視圖密度切換 (緊湊/詳細) 與單項細節展開/收合', async () => {
    const mockRules = [
      {
        id: 'RULE-DENSITY-1',
        name: '緊湊視圖測試規則',
        category: 'Power',
        description: '這是長篇詳細描述說明',
      },
    ]

    const wrapper = mount(RuleTreeSelector, {
      global: { plugins: [PrimeVue] },
      props: {
        summary: { buses: [], platforms: [], component_count: 1, net_count: 1 },
        recommendedRules: mockRules,
      },
    })

    // 預設為緊湊視圖，長篇描述不顯示在主行
    expect(wrapper.find('.density-toggle-btn').text()).toContain('緊湊視圖')
    expect(wrapper.find('.rule-expanded-details').exists()).toBe(false)

    // 點擊單項展開按鈕
    const expandBtn = wrapper.find('.expand-rule-btn')
    expect(expandBtn.exists()).toBe(true)
    await expandBtn.trigger('click')
    await wrapper.vm.$nextTick()

    // 展開細節出現
    expect(wrapper.find('.rule-expanded-details').exists()).toBe(true)
    expect(wrapper.text()).toContain('這是長篇詳細描述說明')

    // 切換全域為詳細視圖
    const densityBtn = wrapper.find('.density-toggle-btn')
    await densityBtn.trigger('click')
    await wrapper.vm.$nextTick()
    expect(wrapper.find('.density-toggle-btn').text()).toContain('詳細視圖')
    expect(wrapper.find('.rule-expanded-details').exists()).toBe(true)
  })

  it('色彩降噪驗證：不顯示拓撲斷言標籤，LLM 規則正確顯示 LLM 標籤', async () => {
    const mockRules = [
      {
        id: 'RULE-TOPO',
        name: '拓撲規則',
        category: 'Power',
        check_type: 'topology_check',
      },
      {
        id: 'RULE-LLM',
        name: '推理規則',
        category: 'Power',
        check_type: 'llm_agent',
      },
    ]

    const wrapper = mount(RuleTreeSelector, {
      global: { plugins: [PrimeVue] },
      props: {
        summary: { buses: [], platforms: [], component_count: 1, net_count: 1 },
        recommendedRules: mockRules,
      },
    })

    const text = wrapper.text()
    // 拓撲斷言標籤已被移除，不應出現在介面上
    expect(text).not.toContain('拓撲斷言')
    // LLM 規則應顯示 LLM 標籤
    expect(wrapper.find('.llm-tag').exists()).toBe(true)
    expect(wrapper.find('.llm-tag').text()).toBe('LLM')
  })
})

