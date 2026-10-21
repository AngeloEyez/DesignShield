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

    const ruleCards = wrapper.findAll('.rule-group-card')
    expect(ruleCards.length).toBe(1)
    expect(ruleCards[0].text()).toContain('電源濾波電容耐壓降額檢查')
    expect(wrapper.findAll('.violation-item').length).toBe(1)
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

    const ruleCards = wrapper.findAll('.rule-group-card')
    expect(ruleCards.length).toBe(2)
    // 第一項應為 FAIL 規則卡片 (以左側紅色邊框標示)
    expect(ruleCards[0].text()).toContain('電源濾波電容耐壓降額檢查')
    expect(ruleCards[0].classes()).toContain('border-l-red-500')
    // 第二項應為 PASS 規則卡片 (以左側綠色邊框標示)
    expect(ruleCards[1].text()).toContain('I2C 匯流排地址唯一性檢查')
    expect(ruleCards[1].classes()).toContain('border-l-green-500')
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
    expect(wrapper.findAll('.rule-group-card').length).toBe(1)
    expect(wrapper.findAll('.rule-group-card')[0].text()).toContain('電源濾波電容耐壓降額檢查')

    // 點擊 PASS 指標卡
    const passCard = wrapper.find('.card-pass')
    await passCard.trigger('click')
    expect(wrapper.findAll('.rule-group-card').length).toBe(1)
    expect(wrapper.findAll('.rule-group-card')[0].text()).toContain('I2C 匯流排地址唯一性檢查')

    // 點擊 總檢查 指標卡回退至全部
    const totalCard = wrapper.find('.card-total')
    await totalCard.trigger('click')
    expect(wrapper.findAll('.rule-group-card').length).toBe(2)
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
        topology: {
          title: 'TJ1 ↔ TU2 ↔ P72 (USB8_USB20 差分通道)',
          channel_type: 'differential',
          rails: [
            { id: 'p_rail', name: '正極軌道 (P)', polarity: 'P' },
            { id: 'n_rail', name: '負極軌道 (N)', polarity: 'N' },
          ],
          nodes: [
            {
              id: 'TJ1',
              ref_des: 'TJ1',
              category: 'Connector',
              role: 'terminal',
              pins: [
                { pin_number: 'A6', pin_name: 'DP1' },
                { pin_number: 'A7', pin_name: 'DN1' },
              ],
            },
            {
              id: 'TL1',
              ref_des: 'TL1',
              category: 'Common_Mode_Choke',
              role: 'series',
              pins: [
                { pin_number: '3', orientation: 'left' },
                { pin_number: '4', orientation: 'right' },
              ],
            },
            {
              id: 'TU2',
              ref_des: 'TU2',
              category: 'IC',
              role: 'terminal',
              pins: [
                { pin_number: '7', pin_name: 'DP' },
                { pin_number: '8', pin_name: 'DN' },
              ],
            },
            {
              id: 'P72',
              ref_des: 'P72',
              category: 'Connector',
              role: 'terminal',
              pins: [
                { pin_number: '39', pin_name: 'DP' },
                { pin_number: '37', pin_name: 'DN' },
              ],
            },
          ],
          connections: [
            {
              net_name: 'USB8_USB20_CMC_P',
              rail_id: 'p_rail',
              from_node: 'TJ1',
              from_pin: 'A6',
              to_node: 'TL1',
              to_pin: '3',
            },
            {
              net_name: 'USB8_USB20_P',
              rail_id: 'p_rail',
              from_node: 'TL1',
              from_pin: '4',
              to_node: 'TU2',
              to_pin: '7',
            },
            {
              net_name: 'USB8_USB20_P',
              rail_id: 'p_rail',
              from_node: 'TU2',
              from_pin: '7',
              to_node: 'P72',
              to_pin: '39',
            },
            {
              net_name: 'USB8_USB20_CMC_N',
              rail_id: 'n_rail',
              from_node: 'TJ1',
              from_pin: 'A7',
              to_node: 'TL1',
              to_pin: '2',
            },
            {
              net_name: 'USB8_USB20_N',
              rail_id: 'n_rail',
              from_node: 'TL1',
              from_pin: '1',
              to_node: 'TU2',
              to_pin: '8',
            },
            {
              net_name: 'USB8_USB20_N',
              rail_id: 'n_rail',
              from_node: 'TU2',
              from_pin: '8',
              to_node: 'P72',
              to_pin: '37',
            },
          ],
        },
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
            pin_number: 'A6',
            pin_name: 'DP1',
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
            pin_number: 'A7',
            pin_name: 'DN1',
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
    // 1. 驗證直接展示 SVG 拓撲繪圖，無額外標題說明文字
    expect(text).not.toContain('差分通道端到端鏈路拓撲')
    expect(wrapper.find('svg').exists()).toBe(true)

    // 1.1 驗證佐證歷程 (JSON) 預設收合 (Debug 訊息手動展開機制)
    expect(wrapper.find('.json-code').exists()).toBe(false)
    await wrapper.find('.raw-evidence-section .cursor-pointer').trigger('click')
    expect(wrapper.find('.json-code').exists()).toBe(true)

    // 2. 驗證起點端點元件 TJ1 與接腳 (格式: 不重複顯示 refDes，port number 緊鄰 Port 符號，已具顏色區別無中括號)
    expect(text).toContain('TJ1')
    expect(text).toContain('A6')
    expect(text).toContain('DP1')
    expect(text).not.toContain('[DP1]')
    expect(text).toContain('A7')
    expect(text).toContain('DN1')
    expect(text).not.toContain('[DN1]')

    // 3. 驗證穿透元件 TL1 與直通引腳標籤 (左右顯示 inPin / outPin，中間無多餘 PN 箭頭)
    expect(text).toContain('TL1')
    expect(text).toContain('3')
    expect(text).toContain('4')
    expect(text).not.toContain('P+ ➔')
    expect(text).toContain('2')
    expect(text).toContain('1')
    expect(text).not.toContain('N- ➔')

    // 4. 驗證實體網路名稱
    expect(text).toContain('USB8_USB20_CMC_P')
    expect(text).toContain('USB8_USB20_P')
    expect(text).toContain('USB8_USB20_CMC_N')
    expect(text).toContain('USB8_USB20_N')

    // 5. 驗證終點端點晶片與連接器 TU2, P72 (格式: port number 緊鄰 Port 符號)
    expect(text).toContain('TU2')
    expect(text).toContain('7')
    expect(text).toContain('8')
    expect(text).toContain('P72')
    expect(text).toContain('39')
    expect(text).toContain('37')
  })

  it('支援同規則多受測通道歸類為單一規則卡片，並落實最壞情況判定與計數徽章', async () => {
    // 模擬 8 個通道在同一規則 usb_pn_swap_check 下，其中 1 個 FAIL，7 個 PASS
    const multiChannelViolations: ViolationItem[] = Array.from({ length: 8 }, (_, idx) => ({
      item_id: `usb-ch-${idx + 1}`,
      rule_id: 'usb_pn_swap_check',
      rule_category: 'USB',
      rule_title: '追蹤 USB 差分對端到端連線，嚴格檢測晶片引腳極性反接',
      check_type: 'HEURISTIC',
      status: idx === 0 ? 'FAIL' : 'PASS',
      severity: idx === 0 ? 'CRITICAL' : 'INFO',
      target_nodes: { components: ['TJ1', 'TU1'], nets: [`TCP0_RT_SSRX${idx}`] },
      error_message: idx === 0 ? '通道極性反接' : '',
      evidence_trail: { channel_title: `TJ1 ↔ TU1 (TCP0_RT_SSRX${idx} 差分通道)` },
    }))

    const wrapper = mount(TaskReportDashboard, {
      global: { plugins: [PrimeVue] },
      props: {
        taskId: 'usb-batch-task',
        summary: {
          total_rules_checked: 8,
          pass_count: 7,
          fail_count: 1,
          warning_count: 0,
          skip_count: 0,
          pass_rate_percentage: 87.5,
          by_category: { USB: { pass: 7, fail: 1, warning: 0 } },
        },
        violations: multiChannelViolations,
      },
    })

    // 1. 預設規則分組模式下，外層僅有 1 個規則卡片
    const ruleCards = wrapper.findAll('.rule-group-card')
    expect(ruleCards.length).toBe(1)

    // 2. 驗證最壞情況判定 (1 FAIL 導致整條規則顯示 FAIL)
    const header = wrapper.find('.rule-group-header')
    expect(header.text()).toContain('FAIL')
    expect(header.text()).toContain('1 FAIL')
    expect(header.text()).toContain('7 PASS')
    expect(header.text()).toContain('共 8 組受測')

    // 3. 內層涵蓋 8 個受測通道
    const items = wrapper.findAll('.violation-item')
    expect(items.length).toBe(8)
    expect(items[0].text()).toContain('通道極性反接')

    // 4. 驗證信號通道為純文字、移除雙向箭頭圖標、並使用 DIFF Tag
    expect(wrapper.find('.channel-title').text()).toContain('TJ1 ↔ TU1 (TCP0_RT_SSRX0)')
    expect(wrapper.find('.channel-title').text()).not.toContain('差分通道')
    expect(wrapper.find('.tag-diff').exists()).toBe(true)
    expect(wrapper.find('.tag-diff').text()).toBe('DIFF')
    expect(wrapper.find('.pi-arrows-h').exists()).toBe(false)

    // 5. 驗證子卡片不重複顯示規則 title (僅由上層規則卡片展示)
    expect(items[0].find('.item-title').exists()).toBe(false)
  })

  it('支援檢視模式切換 (規則分組 vs 平面清單)', async () => {
    const wrapper = mount(TaskReportDashboard, {
      global: { plugins: [PrimeVue] },
      props: {
        taskId: 'view-mode-task',
        summary: mockSummary,
        violations: mockViolations,
      },
    })

    // 預設為 grouped 模式
    expect(wrapper.find('.rules-grouped-list').exists()).toBe(true)
    expect(wrapper.find('.items-list').exists()).toBe(false)

    // 切換至平面清單 flat
    const flatBtn = wrapper.find('.view-mode-btn-flat')
    await flatBtn.trigger('click')
    expect(wrapper.find('.rules-grouped-list').exists()).toBe(false)
    expect(wrapper.find('.items-list').exists()).toBe(true)

    // 切換回規則分組 grouped
    const groupedBtn = wrapper.find('.view-mode-btn-grouped')
    await groupedBtn.trigger('click')
    expect(wrapper.find('.rules-grouped-list').exists()).toBe(true)
    expect(wrapper.find('.items-list').exists()).toBe(false)
  })

  it('支援批次展開全部與收合全部規則卡片', async () => {
    const wrapper = mount(TaskReportDashboard, {
      global: { plugins: [PrimeVue] },
      props: {
        taskId: 'batch-task',
        summary: mockSummary,
        violations: mockViolations,
      },
    })

    // 點擊收合全部
    const collapseBtn = wrapper.find('.btn-collapse-all')
    await collapseBtn.trigger('click')
    const ruleBodies = wrapper.findAll('.rule-group-body')
    ruleBodies.forEach((body) => {
      expect(body.attributes('style')).toContain('display: none')
    })

    // 點擊展開全部
    const expandBtn = wrapper.find('.btn-expand-all')
    await expandBtn.trigger('click')
    ruleBodies.forEach((body) => {
      const style = body.attributes('style') || ''
      expect(style).not.toContain('display: none')
    })
  })

  it('支援多 BOM Config 切換，若該 Config 有 FAIL 則按鈕固定為紅底，切換時全頁數據卡連動', async () => {
    const multiSummary: ReportSummary = {
      total_rules_checked: 3,
      pass_count: 2,
      fail_count: 1,
      warning_count: 0,
      skip_count: 0,
      pass_rate_percentage: 66.7,
      by_category: {},
      configs: {
        'Config 1': {
          total_rules_checked: 2,
          pass_count: 1,
          fail_count: 1,
          warning_count: 0,
          skip_count: 0,
          pass_rate_percentage: 50.0,
          by_category: { 'Power Domain': { pass: 1, fail: 1, warning: 0 } },
        },
        'Config 2': {
          total_rules_checked: 2,
          pass_count: 2,
          fail_count: 0,
          warning_count: 0,
          skip_count: 0,
          pass_rate_percentage: 100.0,
          by_category: { 'Power Domain': { pass: 2, fail: 0, warning: 0 } },
        },
      },
    }

    const multiViolations: ViolationItem[] = [
      {
        item_id: 'v-cfg1-01',
        rule_id: 'RULE-PWR-01',
        rule_category: 'Power Domain',
        rule_title: '電源規則1',
        check_type: 'HEURISTIC',
        status: 'FAIL',
        severity: 'HIGH',
        target_nodes: { components: ['C1'], nets: ['VCC'] },
        description: 'Config 1 下電容超額。',
        evidence_trail: {},
        bom_config: 'Config 1',
      },
      {
        item_id: 'v-cfg1-02',
        rule_id: 'RULE-PWR-02',
        rule_category: 'Power Domain',
        rule_title: '電源規則2',
        check_type: 'HEURISTIC',
        status: 'PASS',
        severity: 'INFO',
        target_nodes: { components: ['R1'], nets: ['GND'] },
        description: 'Config 1 下通過。',
        evidence_trail: {},
        bom_config: 'Config 1',
      },
      {
        item_id: 'v-cfg2-01',
        rule_id: 'RULE-PWR-01',
        rule_category: 'Power Domain',
        rule_title: '電源規則1',
        check_type: 'HEURISTIC',
        status: 'PASS',
        severity: 'INFO',
        target_nodes: { components: ['C1'], nets: ['VCC'] },
        description: 'Config 2 下未上件，檢查通過。',
        evidence_trail: {},
        bom_config: 'Config 2',
      },
      {
        item_id: 'v-cfg2-02',
        rule_id: 'RULE-PWR-02',
        rule_category: 'Power Domain',
        rule_title: '電源規則2',
        check_type: 'HEURISTIC',
        status: 'PASS',
        severity: 'INFO',
        target_nodes: { components: ['R1'], nets: ['GND'] },
        description: 'Config 2 下通過。',
        evidence_trail: {},
        bom_config: 'Config 2',
      },
    ]

    const wrapper = mount(TaskReportDashboard, {
      global: { plugins: [PrimeVue] },
      props: {
        taskId: 'multi-cfg-task',
        summary: multiSummary,
        violations: multiViolations,
      },
    })

    // 檢查 BOM filter 按鈕群
    const filterGroup = wrapper.find('.bom-config-filter-group')
    expect(filterGroup.exists()).toBe(true)

    const buttons = wrapper.findAll('.bom-config-filter-btn')
    expect(buttons.length).toBe(2)

    // Config 1 有 FAIL，按鈕必須固定為紅底 (包含 bg-red-600) 並顯示 FAIL 標記
    const cfg1Btn = buttons.find((b) => b.text().includes('Config 1'))
    expect(cfg1Btn).toBeDefined()
    expect(cfg1Btn?.classes()).toContain('bg-red-600')
    expect(cfg1Btn?.find('.fail-badge-indicator').exists()).toBe(true)

    // Config 2 全 PASS，按鈕不可為紅底
    const cfg2Btn = buttons.find((b) => b.text().includes('Config 2'))
    expect(cfg2Btn).toBeDefined()
    expect(cfg2Btn?.classes()).not.toContain('bg-red-600')
    expect(cfg2Btn?.find('.fail-badge-indicator').exists()).toBe(false)

    // 預設選中 Config 1 時，違規卡片顯示 1，違規清單包含 Config 1 的項目
    expect(wrapper.find('.card-fail .card-number').text()).toBe('1')
    expect(wrapper.find('.card-pass .card-number').text()).toBe('1')
    expect(wrapper.text()).toContain('Config 1 下電容超額。')

    // 點擊切換至 Config 2
    await cfg2Btn?.trigger('click')

    // 切換後全頁數據卡連動：違規卡片變為 0，通過卡片變為 2
    expect(wrapper.find('.card-fail .card-number').text()).toBe('0')
    expect(wrapper.find('.card-pass .card-number').text()).toBe('2')
    expect(wrapper.text()).toContain('Config 2 下未上件，檢查通過。')
    expect(wrapper.text()).not.toContain('Config 1 下電容超額。')
  })

  it('違規項目中未上件元件 RefDes 標註 [X] 並帶有醒目標籤', () => {
    const unmountedViolations: ViolationItem[] = [
      {
        item_id: 'v-unmounted-01',
        rule_id: 'differential_channel_continuity_check',
        rule_category: 'Signal Integrity',
        rule_title: '差分通道導通與串聯元件完整性檢查',
        check_type: 'HEURISTIC',
        status: 'FAIL',
        severity: 'HIGH',
        target_nodes: { components: ['C1'], nets: ['USB_DP'] },
        description: '差分通道兩端已上件，但中間串聯元件 C1 [X] 標註為未上件，導致訊號開路！',
        evidence_trail: {
          faulty_component: 'C1',
          is_mounted: false,
        },
      },
    ]

    const wrapper = mount(TaskReportDashboard, {
      global: { plugins: [PrimeVue] },
      props: {
        taskId: 'unmounted-report-task',
        summary: mockSummary,
        violations: unmountedViolations,
      },
    })

    const text = wrapper.text()
    expect(text).toContain('C1 [X]')
    // 檢查節點標籤樣式是否包含未上件淡灰色標註類
    const nodeChips = wrapper.findAll('.node-chip')
    const c1Chip = nodeChips.find((chip) => chip.text().includes('C1 [X]'))
    expect(c1Chip).toBeDefined()
    expect(c1Chip?.classes()).toContain('text-surface-400')
  })

  it('規則展示列表排版優化：移除 pass/fail tag，以粗體與分隔線展示規則，展開按鈕純圖標化', () => {
    const wrapper = mount(TaskReportDashboard, {
      global: { plugins: [PrimeVue] },
      props: {
        taskId: 'ui-refine-task',
        summary: mockSummary,
        violations: mockViolations,
      },
    })

    const ruleHeaders = wrapper.findAll('.rule-group-header')
    expect(ruleHeaders.length).toBe(2)

    // 1. 規則標題列不應包含最壞狀態 tag (移除 status-badge)
    expect(ruleHeaders[0].find('.status-badge').exists()).toBe(false)
    expect(ruleHeaders[1].find('.status-badge').exists()).toBe(false)

    // 2. rule-id 應採用 font-bold 且包含 "|" 分隔符號
    const ruleId = ruleHeaders[0].find('.rule-id')
    expect(ruleId.classes()).toContain('font-bold')
    expect(ruleHeaders[0].text()).toContain('|')

    // 3. 展開按鈕應移除「檢視佐證」與「收合詳情」純文字，僅保留箭頭
    const expandBtns = wrapper.findAll('.expand-btn')
    expect(expandBtns.length).toBeGreaterThan(0)
    for (const btn of expandBtns) {
      expect(btn.text()).not.toContain('檢視佐證')
      expect(btn.text()).not.toContain('收合詳情')
      expect(btn.find('i.pi').exists()).toBe(true)
    }
  })

  it('分組展開後，子受測項目依各自 status (PASS/FAIL/SKIPPED) 呈現獨立左側邊條', () => {
    // 構造同一規則下包含 FAIL、PASS、SKIPPED 項目的情境
    const mixedViolations: ViolationItem[] = [
      {
        item_id: 'item-fail',
        rule_id: 'diff_check',
        rule_category: 'Signal_Integrity',
        rule_title: '差分通道導通性檢查',
        check_type: 'DETERMINISTIC',
        status: 'FAIL',
        severity: 'HIGH',
        target_nodes: { components: ['U4', 'U78'], nets: ['USB_P', 'USB_N'] },
        error_message: '通道中斷',
      },
      {
        item_id: 'item-pass',
        rule_id: 'diff_check',
        rule_category: 'Signal_Integrity',
        rule_title: '差分通道導通性檢查',
        check_type: 'DETERMINISTIC',
        status: 'PASS',
        severity: 'INFO',
        target_nodes: { components: ['XU1', 'U4'], nets: ['CLK_P', 'CLK_N'] },
      },
      {
        item_id: 'item-skip',
        rule_id: 'diff_check',
        rule_category: 'Signal_Integrity',
        rule_title: '差分通道導通性檢查',
        check_type: 'DETERMINISTIC',
        status: 'SKIPPED',
        severity: 'INFO',
        target_nodes: { components: ['U10', 'U11'], nets: ['NET_P', 'NET_N'] },
      },
    ]

    const wrapper = mount(TaskReportDashboard, {
      global: { plugins: [PrimeVue] },
      props: {
        taskId: 'mixed-status-task',
        summary: mockSummary,
        violations: mixedViolations,
      },
    })

    const ruleCards = wrapper.findAll('.rule-group-card')
    expect(ruleCards.length).toBe(1)
    // 規則卡片整體標題列應為 FAIL 的紅色邊條
    const header = ruleCards[0].find('.rule-group-header')
    expect(header.classes()).toContain('border-l-red-500')

    // 展開後的子項目應各具自己的狀態邊條
    const items = ruleCards[0].findAll('.violation-item')
    expect(items.length).toBe(3)
    // FAIL 項目：紅色邊條
    expect(items[0].classes()).toContain('border-l-red-500')
    // PASS 項目：綠色邊條
    expect(items[1].classes()).toContain('border-l-green-500')
    // SKIPPED 項目：灰色邊條
    expect(items[2].classes()).toContain('border-l-surface-400')

    // 驗證 rule-group-body 不得包含 divide-y 或 divide-surface-border，以避免覆蓋子項目各自的 border-l 顏色
    const body = ruleCards[0].find('.rule-group-body')
    expect(body.classes()).not.toContain('divide-y')
    expect(body.classes()).not.toContain('divide-surface-border')
    // 驗證子項目具備獨立的 border-b 分隔線 class
    expect(items[0].classes()).toContain('border-b')
    expect(items[0].classes()).toContain('border-b-surface-border')
  })

  it('當檢驗結果包含 missing_partdb 時，正確呈現 PartDB 規格庫缺失待補清單 Section', () => {
    const partdbMissingViolations: ViolationItem[] = [
      {
        item_id: 'item-missing-1',
        rule_id: 'diff_check',
        rule_category: 'Signal_Integrity',
        rule_title: '差分通道導通性檢查',
        check_type: 'DETERMINISTIC',
        status: 'FAIL',
        severity: 'HIGH',
        target_nodes: { components: ['U4', 'U78'], nets: ['USB_P', 'USB_N'] },
        evidence_trail: {
          missing_partdb: [
            { ref_des: 'L19', mfg: 'GENERIC', pn: 'CMF_90_300mA', is_mounted: false },
            { ref_des: 'L20', mfg: 'GENERIC', pn: 'CMF_90_300mA', is_mounted: true },
          ],
        },
      },
    ]

    const wrapper = mount(TaskReportDashboard, {
      global: { plugins: [PrimeVue] },
      props: {
        taskId: 'partdb-missing-task',
        summary: mockSummary,
        violations: partdbMissingViolations,
      },
    })

    // 驗證 Section 是否存在
    const section = wrapper.find('.missing-partdb-section')
    expect(section.exists()).toBe(true)
    expect(section.text()).toContain('PartDB 規格庫缺失待補清單')
    expect(section.text()).toContain('GENERIC_CMF_90_300mA')

    // 驗證受影響元件清單與上件狀態 (L19 未上件應標註 [X], L20 已上件)
    expect(section.text()).toContain('L19 [X]')
    expect(section.text()).toContain('L20')
  })
})



