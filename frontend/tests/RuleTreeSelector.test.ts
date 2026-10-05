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
})
