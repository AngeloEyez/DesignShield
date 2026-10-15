/**
 * @file dagreTopologyLayout.test.ts
 * @description dagreTopologyLayout 工具單元測試
 */

import { describe, it, expect } from 'vitest'
import {
  formatDeviceDisplay,
  generateOrthogonalPath,
  computeTopologyLayout,
} from '@/utils/dagreTopologyLayout'

describe('dagreTopologyLayout.ts', () => {
  it('正確格式化元件引腳顯示字串', () => {
    // 實體 pin_number + pin_name
    expect(
      formatDeviceDisplay({
        ref_des: 'TJ1',
        pin: 'A6',
        pin_number: 'A6',
        pin_name: 'DP1',
      })
    ).toEqual({
      refPin: 'TJ1.A6',
      pinName: 'DP1',
      pinNum: 'A6',
    })

    // 只有 pin 且為實體腳位
    expect(
      formatDeviceDisplay({
        ref_des: 'TU2',
        pin: '7',
      })
    ).toEqual({
      refPin: 'TU2.7',
      pinName: undefined,
      pinNum: '7',
    })

    // pin 為非實體腳位名稱 (例如 DP)
    expect(
      formatDeviceDisplay({
        ref_des: 'TU1',
        pin: 'DP',
      })
    ).toEqual({
      refPin: 'TU1',
      pinName: 'DP',
    })
  })

  it('產生具備 4px 導角之曼哈頓直角階梯連線路徑', () => {
    // 水平同高直線
    const straight = generateOrthogonalPath({ x: 10, y: 50 }, { x: 100, y: 50 })
    expect(straight).toBe('M 10 50 L 100 50')

    // 向下折彎
    const downPath = generateOrthogonalPath({ x: 0, y: 0 }, { x: 100, y: 100 }, 4)
    expect(downPath).toContain('M 0 0')
    expect(downPath).toContain('Q 50 0 50 4')
    expect(downPath).toContain('Q 50 100 54 100')
    expect(downPath).toContain('L 100 100')

    // 向上折彎
    const upPath = generateOrthogonalPath({ x: 0, y: 100 }, { x: 100, y: 0 }, 4)
    expect(upPath).toContain('M 0 100')
    expect(upPath).toContain('Q 50 100 50 96')
    expect(upPath).toContain('Q 50 0 54 0')
    expect(upPath).toContain('L 100 0')
  })

  it('能正確計算差分通道 (TJ1 ↔ TL1 ↔ TU2, P72) 之排版結構、分叉連線與焊點', () => {
    const mockEvidence = {
      p_net: 'USB8_USB20_CMC_P',
      n_net: 'USB8_USB20_CMC_N',
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

    const layout = computeTopologyLayout(mockEvidence)

    // 寬高正常大於 0
    expect(layout.width).toBeGreaterThan(300)
    expect(layout.height).toBeGreaterThan(100)

    // 包含 4 個實體元件節點: TJ1, TL1, TU2, P72
    expect(layout.nodes.length).toBe(4)
    const refDesList = layout.nodes.map((n) => n.refDes)
    expect(refDesList).toContain('TJ1')
    expect(refDesList).toContain('TL1')
    expect(refDesList).toContain('TU2')
    expect(refDesList).toContain('P72')

    // 驗證 TL1 穿透引腳標籤
    const tl1Node = layout.nodes.find((n) => n.refDes === 'TL1')
    expect(tl1Node).toBeDefined()
    expect(tl1Node?.isPassThrough).toBe(true)
    expect(tl1Node?.pInfo?.throughPin).toBe('(3 ➔ 4)')
    expect(tl1Node?.nInfo?.throughPin).toBe('(2 ➔ 1)')

    // 驗證連線與分叉
    expect(layout.edges.length).toBeGreaterThanOrEqual(6)
    // 驗證焊點 (因為 TL1 連接到 TU2 與 P72 兩個端點，應產生分支電氣焊點)
    expect(layout.junctionDots.length).toBeGreaterThan(0)

    // 驗證 Net 標籤
    const netNames = layout.netLabels.map((l) => l.net)
    expect(netNames).toContain('USB8_USB20_CMC_P')
    expect(netNames).toContain('USB8_USB20_P')
  })
})
