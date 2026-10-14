/**
 * @file TaskReportDashboard.test.ts
 * @description TaskReportDashboard 元件單元測試
 */

import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import PrimeVue from 'primevue/config'
import TaskReportDashboard from '@/components/TaskReportDashboard.vue'
import type { ReportSummary, ViolationItem } from '@/components/TaskReportDashboard.vue'

describe('TaskReportDashboard.vue', () => {
  const mockSummary: ReportSummary = {
    total_rules_checked: 2,
    pass_count: 1,
    fail_count: 1,
    warning_count: 0,
    skip_count: 0,
    pass_rate_percentage: 50.0,
    by_category: {
      'Bus Integrity': { pass: 1, fail: 0, warning: 0 },
      'Power Domain': { pass: 0, fail: 1, warning: 0 },
    },
  }

  const mockViolations: ViolationItem[] = [
    {
      item_id: 'v-001',
      rule_id: 'RULE-BUS-I2C-ADDR',
      rule_category: 'Bus Integrity',
      rule_title: 'I2C 匯流排地址唯一性檢查',
      check_type: 'HEURISTIC',
      status: 'PASS',
      severity: 'INFO',
      target_nodes: { components: ['U1', 'U2'], nets: ['I2C_SDA'] },
      description: '未發現地址衝突。',
      comment: '地址配置正常。',
      evidence_trail: { bus: 'I2C_1' },
    },
    {
      item_id: 'v-002',
      rule_id: 'RULE-PWR-CAP-DERATING',
      rule_category: 'Power Domain',
      rule_title: '電源濾波電容耐壓降額檢查',
      check_type: 'HEURISTIC',
      status: 'FAIL',
      severity: 'HIGH',
      target_nodes: { components: ['C1'], nets: ['VBUS'] },
      description: '電容 C1 耐壓過低。',
      comment: '建議換用 10V 以上耐壓電容。',
      evidence_trail: { operating: 5.0, rated: 6.3 },
    },
  ]

  it('正確渲染評分卡與摘要數據', () => {
    const wrapper = mount(TaskReportDashboard, {
      global: { plugins: [PrimeVue] },
      props: {
        taskId: 'test-task-123',
        summary: mockSummary,
        violations: mockViolations,
      },
    })

    const text = wrapper.text()
    expect(text).toContain('總檢查規則')
    expect(text).toContain('通過項目 (PASS)')
    expect(text).toContain('違規項目 (FAIL)')
    expect(text).toContain('50%')
    expect(text).toContain('Bus Integrity')
    expect(text).toContain('Power Domain')
  })

  it('支援過濾按鈕切換展示列表', async () => {
    const wrapper = mount(TaskReportDashboard, {
      global: { plugins: [PrimeVue] },
      props: {
        taskId: 'test-task-123',
        summary: mockSummary,
        violations: mockViolations,
      },
    })

    // 初始展示所有 2 項
    expect(wrapper.findAll('.violation-item').length).toBe(2)

    // 點擊只看違規 FAIL
    const failBtn = wrapper.findAll('.filter-pill-btn').find((b) => b.text().includes('FAIL'))
    expect(failBtn).toBeDefined()
    await failBtn?.trigger('click')

    const itemsAfterFilter = wrapper.findAll('.violation-item')
    expect(itemsAfterFilter.length).toBe(1)
    expect(itemsAfterFilter[0].text()).toContain('電源濾波電容耐壓降額檢查')
  })

  it('點擊查看詳情能展開佐證資訊', async () => {
    const wrapper = mount(TaskReportDashboard, {
      global: { plugins: [PrimeVue] },
      props: {
        taskId: 'test-task-123',
        summary: mockSummary,
        violations: mockViolations,
      },
    })

    expect(wrapper.find('.evidence-details-block').exists()).toBe(false)
    const expandBtn = wrapper.find('.expand-btn')
    await expandBtn.trigger('click')
    expect(wrapper.find('.evidence-details-block').exists()).toBe(true)
  })

  it('支援異常優先置頂排序 (FAIL 項目排在 PASS 前面)', () => {
    const wrapper = mount(TaskReportDashboard, {
      global: { plugins: [PrimeVue] },
      props: {
        taskId: 'test-task-123',
        summary: mockSummary,
        violations: mockViolations,
      },
    })

    const items = wrapper.findAll('.violation-item')
    expect(items.length).toBe(2)
    // 第一項應為 FAIL 項目
    expect(items[0].text()).toContain('電源濾波電容耐壓降額檢查')
    expect(items[0].text()).toContain('FAIL')
    // 第二項應為 PASS 項目
    expect(items[1].text()).toContain('I2C 匯流排地址唯一性檢查')
    expect(items[1].text()).toContain('PASS')
  })

  it('支援點擊頂部指標卡進行連動過濾', async () => {
    const wrapper = mount(TaskReportDashboard, {
      global: { plugins: [PrimeVue] },
      props: {
        taskId: 'test-task-123',
        summary: mockSummary,
        violations: mockViolations,
      },
    })

    // 點擊 FAIL 指標卡
    const failCard = wrapper.find('.card-fail')
    await failCard.trigger('click')
    expect(wrapper.findAll('.violation-item').length).toBe(1)
    expect(wrapper.findAll('.violation-item')[0].text()).toContain('電源濾波電容耐壓降額檢查')

    // 點擊 PASS 指標卡
    const passCard = wrapper.find('.card-pass')
    await passCard.trigger('click')
    expect(wrapper.findAll('.violation-item').length).toBe(1)
    expect(wrapper.findAll('.violation-item')[0].text()).toContain('I2C 匯流排地址唯一性檢查')

    // 點擊 總檢查 指標卡回退至全部
    const totalCard = wrapper.find('.card-total')
    await totalCard.trigger('click')
    expect(wrapper.findAll('.violation-item').length).toBe(2)
  })

  it('支援點擊複製 JSON 按鈕並切換已複製狀態', async () => {
    const wrapper = mount(TaskReportDashboard, {
      global: { plugins: [PrimeVue] },
      props: {
        taskId: 'test-task-123',
        summary: mockSummary,
        violations: mockViolations,
      },
    })

    // 展開第一項詳情
    const expandBtn = wrapper.find('.expand-btn')
    await expandBtn.trigger('click')

    // 找到複製按鈕
    const copyBtn = wrapper.find('.copy-json-btn')
    expect(copyBtn.exists()).toBe(true)
    expect(copyBtn.text()).toContain('複製 JSON')

    await copyBtn.trigger('click')
    // 驗證按鈕狀態
    expect(copyBtn.exists()).toBe(true)
  })
})

