/**
 * @file DifferentialTopologySvg.test.ts
 * @description DifferentialTopologySvg 元件單元測試
 */

import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import PrimeVue from 'primevue/config'
import DifferentialTopologySvg from '@/components/DifferentialTopologySvg.vue'

describe('DifferentialTopologySvg.vue', () => {
  const mockEvidence = {
    p_net: 'USB8_USB20_CMC_P',
    n_net: 'USB8_USB20_CMC_N',
    pass_through_components: ['TL1'],
    symmetry_check: {
      is_symmetric: true,
      endpoints_count_match: true,
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
        pin: 'A6',
        pin_number: 'A6',
        pin_name: 'DP1',
        connected_net: 'USB8_USB20_CMC_P',
        component_type: 'Connector',
      },
      {
        ref_des: 'TU2',
        pin: '7',
        connected_net: 'USB8_USB20_P',
        component_type: 'IC',
      },
      {
        ref_des: 'P72',
        pin: '39',
        connected_net: 'USB8_USB20_P',
        component_type: 'Connector',
      },
    ],
    n_endpoints: [
      {
        ref_des: 'TJ1',
        pin: 'A7',
        pin_number: 'A7',
        pin_name: 'DN1',
        connected_net: 'USB8_USB20_CMC_N',
        component_type: 'Connector',
      },
      {
        ref_des: 'TU2',
        pin: '8',
        connected_net: 'USB8_USB20_N',
        component_type: 'IC',
      },
      {
        ref_des: 'P72',
        pin: '37',
        connected_net: 'USB8_USB20_N',
        component_type: 'Connector',
      },
    ],
  }

  it('完整渲染差分拓撲標題、對稱性與 P/N 軌道圖例', () => {
    const wrapper = mount(DifferentialTopologySvg, {
      global: { plugins: [PrimeVue] },
      props: {
        evidence: mockEvidence,
      },
    })

    const text = wrapper.text()
    expect(text).toContain('差分通道端到端鏈路拓撲')
    expect(text).toContain('P/N 拓撲完全對稱')
    expect(text).toContain('途經元件: TL1')
    expect(text).toContain('P+ 正極軌道')
    expect(text).toContain('N- 負極軌道')
  })

  it('在 SVG 中精確繪製元件節點、引腳、穿透標籤與網路線段', () => {
    const wrapper = mount(DifferentialTopologySvg, {
      global: { plugins: [PrimeVue] },
      props: {
        evidence: mockEvidence,
      },
    })

    const text = wrapper.text()
    // 驗證起點引腳 (節點內顯示 port number 與 port name，已具顏色區別故無中括號)
    expect(text).toContain('TJ1')
    expect(text).toContain('A6')
    expect(text).toContain('DP1')
    expect(text).not.toContain('[DP1]')
    expect(text).toContain('A7')
    expect(text).toContain('DN1')
    expect(text).not.toContain('[DN1]')

    // 驗證穿透 CMC 元件直通引腳標籤 (左右顯示 inPin / outPin，中間無多餘 PN 箭頭)
    expect(text).toContain('TL1')
    expect(text).toContain('3')
    expect(text).toContain('4')
    expect(text).not.toContain('P+ ➔')
    expect(text).toContain('2')
    expect(text).toContain('1')
    expect(text).not.toContain('N- ➔')

    // 驗證終點元件與引腳 (port number 緊鄰 Port 符號)
    expect(text).toContain('TU2')
    expect(text).toContain('7')
    expect(text).toContain('8')
    expect(text).toContain('P72')
    expect(text).toContain('39')
    expect(text).toContain('37')

    // 驗證實體網路名稱標籤
    expect(text).toContain('USB8_USB20_CMC_P')
    expect(text).toContain('USB8_USB20_P')

    // 驗證 SVG 標籤存在且包含折線路徑、焊點與節點矩形
    expect(wrapper.find('svg').exists()).toBe(true)
    const edgePaths = wrapper.findAll('.topology-edges path')
    expect(edgePaths.length).toBeGreaterThan(0)
    // 驗證 1：連線直接接在邊界 Port 上，無箭頭 marker
    expect(edgePaths.every((p) => !p.attributes('marker-end'))).toBe(true)

    // 驗證 2：電氣焊點圓點僅在分岔處存在
    expect(wrapper.findAll('.topology-junction-dots circle').length).toBeGreaterThan(0)
    expect(wrapper.findAll('.topology-nodes g').length).toBeGreaterThan(0)

    // 驗證 3：節點邊緣具備微型 4x4 Port 方形端點符號
    const portRects = wrapper.findAll('.topology-nodes rect[width="4"][height="4"]')
    expect(portRects.length).toBeGreaterThanOrEqual(6)
  })
})
