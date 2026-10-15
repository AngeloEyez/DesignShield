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
  it('能正確計算一對多分支主幹與 T-tap 分流，主幹直達 TU2 且無多餘分叉，P 軌垂直分支穿過 N 軌水平線時不誤打焊點', () => {
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
          pin: 'DP2',
          pin_number: 'B6',
          pin_name: 'DP2',
          connected_net: 'USB8_USB20_CMC_P',
          component_type: 'Connector',
        },
        {
          ref_des: 'TJ1',
          pin: 'DN1',
          pin_number: 'A7',
          pin_name: 'DN1',
          connected_net: 'USB8_USB20_CMC_P',
          component_type: 'Connector',
        },
        {
          ref_des: 'TU2',
          pin: '2',
          pin_number: '2',
          pin_name: 'D1P',
          connected_net: 'USB8_USB20_P',
          component_type: 'IC',
        },
        {
          ref_des: 'TU2',
          pin: '7',
          pin_number: '7',
          pin_name: 'D2P',
          connected_net: 'USB8_USB20_P',
          component_type: 'IC',
        },
        {
          ref_des: 'P72',
          pin: '39',
          pin_number: '39',
          connected_net: 'USB8_USB20_P',
          component_type: 'Connector',
        },
      ],
      n_endpoints: [
        {
          ref_des: 'TJ1',
          pin: 'DN2',
          pin_number: 'B7',
          pin_name: 'DN2',
          connected_net: 'USB8_USB20_CMC_N',
          component_type: 'Connector',
        },
        {
          ref_des: 'TJ1',
          pin: 'DP1',
          pin_number: 'A6',
          pin_name: 'DP1',
          connected_net: 'USB8_USB20_CMC_N',
          component_type: 'Connector',
        },
        {
          ref_des: 'TU2',
          pin: '1',
          pin_number: '1',
          pin_name: 'D1M',
          connected_net: 'USB8_USB20_N',
          component_type: 'IC',
        },
        {
          ref_des: 'TU2',
          pin: '8',
          pin_number: '8',
          pin_name: 'D2M',
          connected_net: 'USB8_USB20_N',
          component_type: 'IC',
        },
        {
          ref_des: 'P72',
          pin: '37',
          pin_number: '37',
          connected_net: 'USB8_USB20_N',
          component_type: 'Connector',
        },
      ],
    }
    const layout = computeTopologyLayout(mockEvidence)

    const pTrunkToTU2 = layout.edges.filter((e) => e.targetId === 'node_2_TU2' && e.polarity === 'p' && !e.id.includes('split_'))
    const nTrunkToTU2 = layout.edges.filter((e) => e.targetId === 'node_2_TU2' && e.polarity === 'n' && !e.id.includes('split_'))
    expect(pTrunkToTU2.length).toBe(1)
    expect(nTrunkToTU2.length).toBe(1)
    expect(pTrunkToTU2[0].isBranch).toBe(false)
    expect(nTrunkToTU2[0].isBranch).toBe(false)

    // 斷言 2: TU2 門口沒有虛假的分叉焊點，分流焊點精確定位於主幹線與分流引腳交會處 (444, 51)
    const tu2SplitDotsP = layout.junctionDots.filter((j) => j.id.includes('split_junc_p_node_2_TU2'))
    expect(tu2SplitDotsP.length).toBe(1)
    expect(tu2SplitDotsP[0].x).toBe(444)
    expect(tu2SplitDotsP[0].y).toBe(51)
    // 主幹線終點精確抵達分流焊點
    expect(pTrunkToTU2[0].end).toEqual({ x: 444, y: 51 })
    // 分流引腳連線起點精確自分流焊點出發
    const tu2SplitEdgesP = layout.edges.filter((e) => e.id.includes('split_p_node_2_TU2'))
    expect(tu2SplitEdgesP.length).toBe(2)
    tu2SplitEdgesP.forEach((edge) => {
      expect(edge.start).toEqual({ x: 444, y: 51 })
    })

    // 斷言 2.1: TJ1 來源端多引腳匯流焊點精確定位於引腳匯流與主幹線起點交會處 (100, 51)
    const tj1MergeDotP = layout.junctionDots.find((j) => j.id.includes('merge_junc_p_node_0_TJ1'))
    expect(tj1MergeDotP).toBeDefined()
    expect(tj1MergeDotP?.x).toBe(100)
    expect(tj1MergeDotP?.y).toBe(51)
    const tj1MergeEdgesP = layout.edges.filter((e) => e.id.includes('merge_p_node_0_TJ1'))
    expect(tj1MergeEdgesP.length).toBe(2)
    tj1MergeEdgesP.forEach((edge) => {
      expect(edge.end).toEqual({ x: 100, y: 51 })
    })
    const tj1TrunkEdgeP = layout.edges.find((e) => e.id.includes('edge_p_node_0_TJ1_node_1_TL1'))
    expect(tj1TrunkEdgeP?.start).toEqual({ x: 100, y: 51 })

    // 斷言 3: 分支 P72 採用 T-tap 探出，起點在主幹上且帶有分叉焊點
    const pBranchToP72 = layout.edges.find((e) => e.targetId === 'node_2_P72' && e.polarity === 'p')
    const nBranchToP72 = layout.edges.find((e) => e.targetId === 'node_2_P72' && e.polarity === 'n')
    expect(pBranchToP72).toBeDefined()
    expect(nBranchToP72).toBeDefined()
    expect(pBranchToP72?.isBranch).toBe(true)
    expect(nBranchToP72?.isBranch).toBe(true)

    const pJuncDot = layout.junctionDots.find((j) => j.id.includes('junc_p_node_1_TL1_node_2_P72'))
    const nJuncDot = layout.junctionDots.find((j) => j.id.includes('junc_n_node_1_TL1_node_2_P72'))
    expect(pJuncDot).toBeDefined()
    expect(nJuncDot).toBeDefined()
    // T-tap 焊點必須與分支連線起點 100% 精準吻合
    expect(pJuncDot).toEqual({ id: pJuncDot!.id, polarity: 'p', x: pBranchToP72!.start.x, y: pBranchToP72!.start.y })
    expect(nJuncDot).toEqual({ id: nJuncDot!.id, polarity: 'n', x: nBranchToP72!.start.x, y: nBranchToP72!.start.y })

    // 斷言 4: P 軌與 N 軌的分叉 X 座標相互避開 (至少 16px 以上安全間隔)，且與 TU2 分流點保持安全距離
    expect(pJuncDot!.x).not.toBe(nJuncDot!.x)
    expect(Math.abs(pJuncDot!.x - nJuncDot!.x)).toBeGreaterThanOrEqual(16)
    expect(tu2SplitDotsP[0].x - pJuncDot!.x).toBeGreaterThanOrEqual(20)

    // 斷言 5: P 軌垂直分支穿過 N 軌水平主幹高度 (Y=74) 時，在交會處絕不打上任何焊點
    const dotAtCrossing = layout.junctionDots.find((j) => Math.abs(j.x - pJuncDot!.x) < 2 && Math.abs(j.y - 74) < 2)
    expect(dotAtCrossing).toBeUndefined()
  })
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

    // 驗證 1：節點尺寸緊湊化 (TL1 寬度大幅小於原本的 88px/154px，杜絕空白)
    expect(tl1Node?.width).toBeLessThanOrEqual(72)
    expect(tl1Node?.height).toBe(52)

    // 驗證 2：Net 標籤防遮擋 (x 座標緊貼來源節點右側 6px)
    const pNetLabel = layout.netLabels.find((l) => l.net === 'USB8_USB20_P' && l.polarity === 'p')
    expect(pNetLabel).toBeDefined()
    expect(pNetLabel?.x).toBe(tl1Node!.pOutPort!.x + 6)

    // 驗證 3：分岔連線在 X 軸避開重疊 (TL1 分岔至 P72 時，P 軌與 N 軌折轉點 X 座標錯開，互不黏連)
    const pEdgeToP72 = layout.edges.find((e) => e.targetId === 'node_2_P72' && e.polarity === 'p')
    const nEdgeToP72 = layout.edges.find((e) => e.targetId === 'node_2_P72' && e.polarity === 'n')
    expect(pEdgeToP72).toBeDefined()
    expect(nEdgeToP72).toBeDefined()

    // 焊點圓點 X 軸座標亦各自獨立錯開，絕不重疊在同一 X 上
    const pJunc = layout.junctionDots.find((j) => j.polarity === 'p')
    const nJunc = layout.junctionDots.find((j) => j.polarity === 'n')
    expect(pJunc).toBeDefined()
    expect(nJunc).toBeDefined()
    expect(pJunc!.x).not.toBe(nJunc!.x)
  })

  it('虛擬 Endpoint 節點寬度與高度應緊湊一致，不產生多餘留白與排版扭曲', () => {
    const virtualEvidence = {
      p_net: 'RT_SSRX0_P_C',
      n_net: 'RT_SSRX0_N_C',
      path_segments: [
        {
          from_net: 'RT_SSRX0_P_C',
          pass_component: 'TC13',
          in_pin: '2',
          out_pin: '1',
          to_net: 'ENDPOINT_NET_P',
        },
      ],
      n_path_segments: [
        {
          from_net: 'RT_SSRX0_N_C',
          pass_component: 'TC13',
          in_pin: '2',
          out_pin: '1',
          to_net: 'ENDPOINT_NET_N',
        },
      ],
      p_endpoints: [],
      n_endpoints: [],
    }

    const layout = computeTopologyLayout(virtualEvidence)
    const endpointNode = layout.nodes.find((n) => n.refDes === 'Endpoint')
    expect(endpointNode).toBeDefined()
    expect(endpointNode!.width).toBeLessThanOrEqual(72)
    expect(endpointNode!.height).toBe(52)
  })

  it('當端點元件 (如 Type-C TJ1) 連接複數 Pin 時，完整保留所有引腳並產生匯流走線', () => {
    const multiPinEvidence = {
      p_net: 'USB8_USB20_CMC_P',
      n_net: 'USB8_USB20_CMC_N',
      path_segments: [
        {
          from_net: 'USB8_USB20_P',
          pass_component: 'TL1',
          in_pin: '4',
          out_pin: '3',
          to_net: 'USB8_USB20_CMC_P',
        },
      ],
      n_path_segments: [
        {
          from_net: 'USB8_USB20_N',
          pass_component: 'TL1',
          in_pin: '1',
          out_pin: '2',
          to_net: 'USB8_USB20_CMC_N',
        },
      ],
      p_endpoints: [
        {
          ref_des: 'TJ1',
          pin: 'DP2',
          pin_number: 'B6',
          pin_name: 'DP2',
          connected_net: 'USB8_USB20_CMC_P',
          component_type: 'Connector',
        },
        {
          ref_des: 'TJ1',
          pin: 'DN1',
          pin_number: 'A7',
          pin_name: 'DN1',
          connected_net: 'USB8_USB20_CMC_P',
          component_type: 'Connector',
        },
      ],
      n_endpoints: [
        {
          ref_des: 'TJ1',
          pin: 'DN2',
          pin_number: 'B7',
          pin_name: 'DN2',
          connected_net: 'USB8_USB20_CMC_N',
          component_type: 'Connector',
        },
        {
          ref_des: 'TJ1',
          pin: 'DP1',
          pin_number: 'A6',
          pin_name: 'DP1',
          connected_net: 'USB8_USB20_CMC_N',
          component_type: 'Connector',
        },
      ],
    }

    const layout = computeTopologyLayout(multiPinEvidence)
    const tj1 = layout.nodes.find((n) => n.refDes === 'TJ1')
    expect(tj1).toBeDefined()

    // 驗證 1：TJ1 保留全部 4 個引腳，不再被覆蓋丟失
    expect(tj1!.pPins.length).toBe(2)
    expect(tj1!.nPins.length).toBe(2)
    const pPinNums = tj1!.pPins.map((p) => p.pinNum)
    const nPinNums = tj1!.nPins.map((p) => p.pinNum)
    expect(pPinNums).toContain('B6')
    expect(pPinNums).toContain('A7')
    expect(nPinNums).toContain('B7')
    expect(nPinNums).toContain('A6')

    // 驗證 2：TJ1 高度動態適應 4 個引腳
    expect(tj1!.height).toBeGreaterThanOrEqual(80)

    // 驗證 3：產生了複數引腳分流/匯流電氣焊點與分流走線
    const multiPinDots = layout.junctionDots.filter((j) => j.id.includes('split_junc_') || j.id.includes('merge_junc_'))
    expect(multiPinDots.length).toBeGreaterThanOrEqual(2)
    const multiPinEdges = layout.edges.filter((e) => e.id.includes('split_') || e.id.includes('merge_'))
    expect(multiPinEdges.length).toBeGreaterThanOrEqual(4)
  })

  it('能正確支援 P/N 軌分立元件 (TC13/TC14 與 TR8/TR9)，不產生中繼虛擬 Endpoint，且維持緊湊間距', () => {
    const discreteEvidence = {
      channel_title: 'TJ1 ↔ TU1 (TCP0_RT_SSRX0 差分通道)',
      pair_type: 'USB Differential Channel',
      p_net: 'TCP0_RT_SSRX0_P',
      n_net: 'TCP0_RT_SSRX0_N',
      path_segments: [
        {
          from_net: 'TCP0_RT_SSRX0_P',
          pass_component: 'TC13',
          pass_component_type: 'Capacitor',
          in_pin: '2',
          out_pin: '1',
          to_net: 'TCP0_RT_SSRX0_P_C',
        },
        {
          from_net: 'TCP0_RT_SSRX0_P_C',
          pass_component: 'TR8',
          pass_component_type: 'Resistor',
          in_pin: '2',
          out_pin: '1',
          to_net: 'TCP0_RT_SSRX0_P_R',
        },
      ],
      n_path_segments: [
        {
          from_net: 'TCP0_RT_SSRX0_N',
          pass_component: 'TC14',
          pass_component_type: 'Capacitor',
          in_pin: '2',
          out_pin: '1',
          to_net: 'TCP0_RT_SSRX0_N_C',
        },
        {
          from_net: 'TCP0_RT_SSRX0_N_C',
          pass_component: 'TR9',
          pass_component_type: 'Resistor',
          in_pin: '2',
          out_pin: '1',
          to_net: 'TCP0_RT_SSRX0_N_R',
        },
      ],
      topology_flow: [
        {
          stage: 'endpoints',
          net: 'TCP0_RT_SSRX0_P',
          devices: [
            {
              ref_des: 'TJ1',
              pin: 'SSRXP1',
              pin_name: 'SSRXP1',
              pin_number: 'B11',
              type: 'Connector',
            },
          ],
        },
        {
          stage: 'pass_through',
          component: 'TC13',
          type: 'Capacitor',
          in_pin: '2',
          out_pin: '1',
          from_net: 'TCP0_RT_SSRX0_P',
          to_net: 'TCP0_RT_SSRX0_P_C',
        },
        {
          stage: 'endpoints',
          net: 'TCP0_RT_SSRX0_P_C',
          devices: [],
        },
        {
          stage: 'pass_through',
          component: 'TR8',
          type: 'Resistor',
          in_pin: '2',
          out_pin: '1',
          from_net: 'TCP0_RT_SSRX0_P_C',
          to_net: 'TCP0_RT_SSRX0_P_R',
        },
        {
          stage: 'endpoints',
          net: 'TCP0_RT_SSRX0_P_R',
          devices: [
            {
              ref_des: 'TU1',
              pin: 'PB_TX1_DRX1_P',
              pin_name: 'PB_TX1_DRX1_P',
              pin_number: 'N12',
              type: 'IC',
            },
          ],
        },
      ],
      n_topology_flow: [
        {
          stage: 'endpoints',
          net: 'TCP0_RT_SSRX0_N',
          devices: [
            {
              ref_des: 'TJ1',
              pin: 'SSRXN1',
              pin_name: 'SSRXN1',
              pin_number: 'B10',
              type: 'Connector',
            },
          ],
        },
        {
          stage: 'pass_through',
          component: 'TC14',
          type: 'Capacitor',
          in_pin: '2',
          out_pin: '1',
          from_net: 'TCP0_RT_SSRX0_N',
          to_net: 'TCP0_RT_SSRX0_N_C',
        },
        {
          stage: 'endpoints',
          net: 'TCP0_RT_SSRX0_N_C',
          devices: [],
        },
        {
          stage: 'pass_through',
          component: 'TR9',
          type: 'Resistor',
          in_pin: '2',
          out_pin: '1',
          from_net: 'TCP0_RT_SSRX0_N_C',
          to_net: 'TCP0_RT_SSRX0_N_R',
        },
        {
          stage: 'endpoints',
          net: 'TCP0_RT_SSRX0_N_R',
          devices: [
            {
              ref_des: 'TU1',
              pin: 'PB_TX1_DRX1_N',
              pin_name: 'PB_TX1_DRX1_N',
              pin_number: 'N13',
              type: 'IC',
            },
          ],
        },
      ],
    }

    const layout = computeTopologyLayout(discreteEvidence)
    const nodeRefs = layout.nodes.map((n) => n.refDes)

    // 斷言 1: 絕無虛假中繼 Endpoint 節點
    expect(nodeRefs).not.toContain('Endpoint')

    // 斷言 2: P 軌電容 TC13 與 N 軌電容 TC14 各自獨立存在，不互相吞併
    expect(nodeRefs).toContain('TC13')
    expect(nodeRefs).toContain('TC14')
    const tc13 = layout.nodes.find((n) => n.refDes === 'TC13')
    const tc14 = layout.nodes.find((n) => n.refDes === 'TC14')
    expect(tc13).toBeDefined()
    expect(tc14).toBeDefined()
    expect(tc13?.hasP).toBe(true)
    expect(tc13?.hasN).toBe(false)
    expect(tc14?.hasP).toBe(false)
    expect(tc14?.hasN).toBe(true)

    // 斷言 3: P 軌電阻 TR8 與 N 軌電阻 TR9 各自獨立存在
    expect(nodeRefs).toContain('TR8')
    expect(nodeRefs).toContain('TR9')
    const tr8 = layout.nodes.find((n) => n.refDes === 'TR8')
    const tr9 = layout.nodes.find((n) => n.refDes === 'TR9')
    expect(tr8?.hasP).toBe(true)
    expect(tr8?.hasN).toBe(false)
    expect(tr9?.hasP).toBe(false)
    expect(tr9?.hasN).toBe(true)

    // 斷言 4: 階層寬度緊湊 (純直行鏈路無多餘留白)
    // 總階層只有 4 階 (TJ1, TC13/TC14, TR8/TR9, TU1)
    expect(layout.nodes.length).toBe(6) // TJ1, TC13, TC14, TR8, TR9, TU1
  })

  it('能正確處理分立元件拓撲 (TJ1 -> TC9/TC10 -> TR4/TR5 -> TU1)，P 軌與 N 軌完全獨立路由，100% 繪製連線且無斷線與孤立圓點', () => {
    const ssrx1Evidence = {
      channel_title: 'TJ1 ↔ TU1 (TCP0_RT_SSRX1 差分通道)',
      p_net: 'TCP0_RT_SSRX1_P',
      n_net: 'TCP0_RT_SSRX1_N',
      topology_flow: [
        {
          stage: 'endpoints',
          net: 'TCP0_RT_SSRX1_P',
          devices: [
            {
              ref_des: 'TJ1',
              pin: 'SSRXP2',
              pin_name: 'SSRXP2',
              pin_number: 'A11',
              type: 'Connector',
            },
          ],
        },
        {
          stage: 'pass_through',
          component: 'TC9',
          type: 'Capacitor',
          in_pin: '2',
          out_pin: '1',
          from_net: 'TCP0_RT_SSRX1_P',
          to_net: 'TCP0_RT_SSRX1_P_C',
        },
        {
          stage: 'endpoints',
          net: 'TCP0_RT_SSRX1_P_C',
          devices: [],
        },
        {
          stage: 'pass_through',
          component: 'TR4',
          type: 'Resistor',
          in_pin: '2',
          out_pin: '1',
          from_net: 'TCP0_RT_SSRX1_P_C',
          to_net: 'TCP0_RT_SSRX1_P_R',
        },
        {
          stage: 'endpoints',
          net: 'TCP0_RT_SSRX1_P_R',
          devices: [
            {
              ref_des: 'TU1',
              pin: 'PB_TX2_DRX2_P',
              pin_name: 'PB_TX2_DRX2_P',
              pin_number: 'G12',
              type: 'IC',
            },
          ],
        },
      ],
      n_topology_flow: [
        {
          stage: 'endpoints',
          net: 'TCP0_RT_SSRX1_N',
          devices: [
            {
              ref_des: 'TJ1',
              pin: 'SSRXN2',
              pin_name: 'SSRXN2',
              pin_number: 'A10',
              type: 'Connector',
            },
          ],
        },
        {
          stage: 'pass_through',
          component: 'TC10',
          type: 'Capacitor',
          in_pin: '2',
          out_pin: '1',
          from_net: 'TCP0_RT_SSRX1_N',
          to_net: 'TCP0_RT_SSRX1_N_C',
        },
        {
          stage: 'endpoints',
          net: 'TCP0_RT_SSRX1_N_C',
          devices: [],
        },
        {
          stage: 'pass_through',
          component: 'TR5',
          type: 'Resistor',
          in_pin: '2',
          out_pin: '1',
          from_net: 'TCP0_RT_SSRX1_N_C',
          to_net: 'TCP0_RT_SSRX1_N_R',
        },
        {
          stage: 'endpoints',
          net: 'TCP0_RT_SSRX1_N_R',
          devices: [
            {
              ref_des: 'TU1',
              pin: 'PB_TX2_DRX2_N',
              pin_name: 'PB_TX2_DRX2_N',
              pin_number: 'G13',
              type: 'IC',
            },
          ],
        },
      ],
    }

    const layout = computeTopologyLayout(ssrx1Evidence)
    const nodeRefs = layout.nodes.map((n) => n.refDes)

    // 斷言 1: 節點包含 TJ1, TC9, TC10, TR4, TR5, TU1，絕無虛擬 Endpoint 節點
    expect(nodeRefs).not.toContain('Endpoint')
    expect(nodeRefs).toContain('TJ1')
    expect(nodeRefs).toContain('TC9')
    expect(nodeRefs).toContain('TC10')
    expect(nodeRefs).toContain('TR4')
    expect(nodeRefs).toContain('TR5')
    expect(nodeRefs).toContain('TU1')

    // 斷言 2: 連線完整性 — P 軌與 N 軌連線數量對稱且各段皆完整繪製
    const pEdges = layout.edges.filter((e) => e.polarity === 'p')
    const nEdges = layout.edges.filter((e) => e.polarity === 'n')

    // 3 個間隔 (TJ1 -> TC, TC -> TR, TR -> TU1)，P 軌 3 條，N 軌 3 條
    expect(pEdges.length).toBe(3)
    expect(nEdges.length).toBe(3)

    // 斷言 3: P 軌主幹只連 P 軌元件，N 軌主幹只連 N 軌元件，絕無跨軌連線
    const tj1ToTc9 = pEdges.find((e) => e.targetId.includes('TC9'))
    const tj1ToTc10 = nEdges.find((e) => e.targetId.includes('TC10'))
    expect(tj1ToTc9).toBeDefined()
    expect(tj1ToTc10).toBeDefined()

    const tc9ToTr4 = pEdges.find((e) => e.sourceId.includes('TC9') && e.targetId.includes('TR4'))
    const tc10ToTr5 = nEdges.find((e) => e.sourceId.includes('TC10') && e.targetId.includes('TR5'))
    expect(tc9ToTr4).toBeDefined()
    expect(tc10ToTr5).toBeDefined()

    const tr4ToTu1 = pEdges.find((e) => e.sourceId.includes('TR4') && e.targetId.includes('TU1'))
    const tr5ToTu1 = nEdges.find((e) => e.sourceId.includes('TR5') && e.targetId.includes('TU1'))
    expect(tr4ToTu1).toBeDefined()
    expect(tr5ToTu1).toBeDefined()

    // 斷言 4: 純直行雙軌無分流，junctionDots 為 0 (杜絕孤立懸空焊點)
    expect(layout.junctionDots.length).toBe(0)
  })

  it('若輸入之 topology_flow 首端包含無設備中繼 stage，防禦性過濾機制生效，絕不渲染虛擬 Endpoint 節點', () => {
    const rawFlowWithEmptyStart = {
      channel_title: 'TJ1 ↔ TU1 (測試鏈路)',
      p_net: 'TEST_P',
      n_net: 'TEST_N',
      topology_flow: [
        {
          stage: 'endpoints',
          net: 'TEST_P_C',
          devices: [], // 首端無設備
        },
        {
          stage: 'pass_through',
          component: 'TC1',
          type: 'Capacitor',
          in_pin: '1',
          out_pin: '2',
          from_net: 'TEST_P_C',
          to_net: 'TEST_P',
        },
        {
          stage: 'endpoints',
          net: 'TEST_P',
          devices: [
            {
              ref_des: 'TU1',
              pin: '1',
              type: 'IC',
            },
          ],
        },
      ],
    }

    const layout = computeTopologyLayout(rawFlowWithEmptyStart)
    const nodeRefs = layout.nodes.map((n) => n.refDes)
    // 因鏈路內含有實體設備 TU1，首端 devices 為空之 endpoints stage 被過濾，不繪製 Endpoint
    expect(nodeRefs).not.toContain('Endpoint')
    expect(nodeRefs).toContain('TC1')
    expect(nodeRefs).toContain('TU1')
  })
})
