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
})
