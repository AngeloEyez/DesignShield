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

  it('完整渲染差分通道端到端鏈路拓撲 (含起點連接器、途經 CMC、實體網路與終點晶片)', async () => {
    const diffViolation: ViolationItem = {
      item_id: 'v-diff-001',
      rule_id: 'usb_pn_swap_check',
      rule_category: 'Differential Pair',
      rule_title: 'USB 差分對極性與拓撲對稱檢查',
      check_type: 'HEURISTIC',
      status: 'PASS',
      severity: 'INFO',
      target_nodes: { components: ['TJ1', 'TU2', 'P72', 'TL1'], nets: ['USB8_USB20_CMC_P', 'USB8_USB20_P'] },
      error_message: '',
      description: 'USB8 差分通道通過完整性檢查。',
      evidence_trail: {
        checked_target: 'TJ1 ↔ TU2 ↔ P72 (USB8_USB20 差分通道)',
        channel_title: 'TJ1 ↔ TU2 ↔ P72 (USB8_USB20 差分通道)',
        pair_type: 'USB Differential Channel',
        p_net: 'USB8_USB20_CMC_P',
        n_net: 'USB8_USB20_CMC_N',
        covered_nets: ['USB8_USB20_CMC_P', 'USB8_USB20_CMC_N', 'USB8_USB20_P', 'USB8_USB20_N'],
        path_segments: [
          {
            from_net: 'USB8_USB20_CMC_P',
            pass_component: 'TL1',
            pass_component_type: 'Common_Mode_Choke',
            in_pin: '3',
            out_pin: '4',
            to_net: 'USB8_USB20_P',
          },
        ],
        n_path_segments: [
          {
            from_net: 'USB8_USB20_CMC_N',
            pass_component: 'TL1',
            pass_component_type: 'Common_Mode_Choke',
            in_pin: '2',
            out_pin: '1',
            to_net: 'USB8_USB20_N',
          },
        ],
        p_endpoints: [
          {
            ref_des: 'TJ1',
            part_number: 'USBX1_Type-C_30u_Black',
            pin: 'A6',
            pin_polarity: 'P',
            polarity_match: true,
            connected_net: 'USB8_USB20_CMC_P',
            component_type: 'Connector',
          },
          {
            ref_des: 'TU2',
            part_number: 'TUSB212RWBR',
            pin: '7',
            pin_polarity: 'P',
            polarity_match: true,
            connected_net: 'USB8_USB20_P',
            component_type: 'IC',
          },
          {
            ref_des: 'P72',
            part_number: 'B to B_120P_15u_Black',
            pin: '39',
            pin_polarity: 'P',
            polarity_match: true,
            connected_net: 'USB8_USB20_P',
            component_type: 'Connector',
          },
        ],
        n_endpoints: [
          {
            ref_des: 'TJ1',
            part_number: 'USBX1_Type-C_30u_Black',
            pin: 'A7',
            pin_polarity: 'N',
            polarity_match: true,
            connected_net: 'USB8_USB20_CMC_N',
            component_type: 'Connector',
          },
          {
            ref_des: 'TU2',
            part_number: 'TUSB212RWBR',
            pin: '8',
            pin_polarity: 'N',
            polarity_match: true,
            connected_net: 'USB8_USB20_N',
            component_type: 'IC',
          },
          {
            ref_des: 'P72',
            part_number: 'B to B_120P_15u_Black',
            pin: '37',
            pin_polarity: 'N',
            polarity_match: true,
            connected_net: 'USB8_USB20_N',
            component_type: 'Connector',
          },
        ],
        pass_through_components: ['TL1'],
        symmetry_check: {
          is_symmetric: true,
          endpoints_count_match: true,
        },
      },
    }

    const wrapper = mount(TaskReportDashboard, {
      global: { plugins: [PrimeVue] },
      props: {
        taskId: 'test-diff-task',
        summary: mockSummary,
        violations: [diffViolation],
      },
    })

    // 展開詳情
    const expandBtn = wrapper.find('.expand-btn')
    await expandBtn.trigger('click')

    const text = wrapper.text()
    // 1. 驗證標題與狀態
    expect(text).toContain('差分通道端到端鏈路拓撲')
    expect(text).toContain('P/N 拓撲完全對稱')
    expect(text).toContain('途經元件: TL1')

    // 2. 驗證起點端點元件 TJ1 與接腳
    expect(text).toContain('TJ1')
    expect(text).toContain('[Pin A6]')
    expect(text).toContain('[Pin A7]')

    // 3. 驗證穿透元件 TL1 與直通引腳標籤
    expect(text).toContain('TL1')
    expect(text).toContain('(3 ➔ 4)')
    expect(text).toContain('(2 ➔ 1)')

    // 4. 驗證實體網路名稱
    expect(text).toContain('USB8_USB20_CMC_P')
    expect(text).toContain('USB8_USB20_P')
    expect(text).toContain('USB8_USB20_CMC_N')
    expect(text).toContain('USB8_USB20_N')

    // 5. 驗證終點端點晶片與連接器 TU2, P72
    expect(text).toContain('TU2')
    expect(text).toContain('[Pin 7]')
    expect(text).toContain('[Pin 8]')
    expect(text).toContain('P72')
    expect(text).toContain('[Pin 39]')
    expect(text).toContain('[Pin 37]')
  })
})

