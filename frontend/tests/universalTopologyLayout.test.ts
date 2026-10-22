/**
 * @file universalTopologyLayout.test.ts
 * @description 通用電路拓撲排版演算法核心單元測試
 */

import { describe, it, expect } from 'vitest'
import {
  computeUniversalTopologyLayout,
  generateOrthogonalPath,
  type UniversalTopologyData,
  type UniversalPin,
} from '@/utils/universalTopologyLayout'

describe('universalTopologyLayout', () => {
  describe('generateOrthogonalPath', () => {
    it('水平直線路徑 (dy = 0)', () => {
      const path = generateOrthogonalPath({ x: 0, y: 50 }, { x: 100, y: 50 })
      expect(path).toBe('M 0 50 L 100 50')
    })

    it('曼哈頓階梯折線路徑 (具備微圓角半徑與指定轉折點)', () => {
      const path = generateOrthogonalPath({ x: 10, y: 20 }, { x: 100, y: 80 }, 4, 60)
      expect(path).toContain('M 10 20')
      expect(path).toContain('L 56 20')
      expect(path).toContain('Q 60 20 60 24')
      expect(path).toContain('L 60 76')
      expect(path).toContain('L 100 80')
    })
  })

  describe('computeUniversalTopologyLayout', () => {
    it('差分對稱通道排版 (TJ1 ↔ TC13/TC14 ↔ TU1)', () => {
      const diffData: UniversalTopologyData = {
        title: 'TJ1 ↔ TU1 (USB 差分通道)',
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
              { pin_number: 'B11', pin_name: 'SSRXP1' },
              { pin_number: 'B10', pin_name: 'SSRXN1' },
            ],
          },
          {
            id: 'TU1',
            ref_des: 'TU1',
            category: 'IC',
            role: 'terminal',
            pins: [
              { pin_number: 'N12', pin_name: 'TX_P' },
              { pin_number: 'N13', pin_name: 'TX_N' },
            ],
          },
          {
            id: 'TC13',
            ref_des: 'TC13',
            category: 'Capacitor',
            role: 'series',
            value: '0.1µF',
            pins: [
              { pin_number: '2', orientation: 'left' },
              { pin_number: '1', orientation: 'right' },
            ],
          },
          {
            id: 'TC14',
            ref_des: 'TC14',
            category: 'Capacitor',
            role: 'series',
            value: '0.1µF',
            pins: [
              { pin_number: '2', orientation: 'left' },
              { pin_number: '1', orientation: 'right' },
            ],
          },
        ],
        connections: [
          {
            net_name: 'USB_SSRX_P',
            rail_id: 'p_rail',
            from_node: 'TJ1',
            from_pin: 'B11',
            to_node: 'TC13',
            to_pin: '2',
          },
          {
            net_name: 'USB_SSRX_P_C',
            rail_id: 'p_rail',
            from_node: 'TC13',
            from_pin: '1',
            to_node: 'TU1',
            to_pin: 'N12',
          },
          {
            net_name: 'USB_SSRX_N',
            rail_id: 'n_rail',
            from_node: 'TJ1',
            from_pin: 'B10',
            to_node: 'TC14',
            to_pin: '2',
          },
          {
            net_name: 'USB_SSRX_N_C',
            rail_id: 'n_rail',
            from_node: 'TC14',
            from_pin: '1',
            to_node: 'TU1',
            to_pin: 'N13',
          },
        ],
      }

      const layout = computeUniversalTopologyLayout(diffData)
      expect(layout.nodes.length).toBe(4)
      expect(layout.edges.length).toBe(4)
      expect(layout.channelType).toBe('differential')

      // TJ1 應位於最左側 (X 最小)
      const tj1 = layout.nodes.find((n) => n.id === 'TJ1')!
      const tu1 = layout.nodes.find((n) => n.id === 'TU1')!
      const tc13 = layout.nodes.find((n) => n.id === 'TC13')!
      expect(tj1.x).toBeLessThan(tc13.x)
      expect(tc13.x).toBeLessThan(tu1.x)

      // 檢查差分標籤
      const netNames = layout.netLabels.map((l) => l.net)
      expect(netNames).toContain('USB_SSRX_P')
      expect(netNames).toContain('USB_SSRX_N')
    })

    it('單端信號上拉與接地分流排版 (U1 ↔ R1 (VCC) ↔ C1 (GND) ↔ U2)', () => {
      const singleData: UniversalTopologyData = {
        title: 'I2C SCL 匯流排鏈路',
        channel_type: 'single',
        rails: [{ id: 'main', name: 'I2C SCL' }],
        nodes: [
          {
            id: 'U1',
            ref_des: 'U1',
            category: 'IC',
            role: 'terminal',
            pins: [{ pin_number: '10', pin_name: 'SCL' }],
          },
          {
            id: 'U2',
            ref_des: 'U2',
            category: 'IC',
            role: 'terminal',
            pins: [{ pin_number: '5', pin_name: 'SCL' }],
          },
          {
            id: 'R1',
            ref_des: 'R1',
            category: 'Resistor',
            role: 'pull_up',
            value: '4.7kΩ',
            pins: [
              { pin_number: '1', orientation: 'bottom' },
              { pin_number: '2', pin_name: '+3.3V', orientation: 'top' },
            ],
          },
          {
            id: 'C1',
            ref_des: 'C1',
            category: 'Capacitor',
            role: 'shunt_ground',
            value: '10pF',
            pins: [
              { pin_number: '1', orientation: 'top' },
              { pin_number: '2', pin_name: 'GND', orientation: 'bottom' },
            ],
          },
        ],
        connections: [
          {
            net_name: 'I2C_SCL',
            rail_id: 'main',
            from_node: 'U1',
            from_pin: '10',
            to_node: 'U2',
            to_pin: '5',
          },
          {
            net_name: 'I2C_SCL',
            rail_id: 'main',
            from_node: 'U1',
            from_pin: '10',
            to_node: 'R1',
            to_pin: '1',
            is_branch: true,
          },
          {
            net_name: 'I2C_SCL',
            rail_id: 'main',
            from_node: 'U1',
            from_pin: '10',
            to_node: 'C1',
            to_pin: '1',
            is_branch: true,
          },
        ],
      }

      const layout = computeUniversalTopologyLayout(singleData)
      expect(layout.nodes.length).toBe(4)

      // 檢查 VCC 與 GND 電氣符號產生
      expect(layout.symbols.length).toBe(2)
      const vccSym = layout.symbols.find((s) => s.type === 'vcc')
      const gndSym = layout.symbols.find((s) => s.type === 'gnd')
      expect(vccSym).toBeDefined()
      expect(vccSym?.label).toBe('+3.3V')
      expect(gndSym).toBeDefined()
      expect(gndSym?.label).toBe('GND')

      // 檢查分支交會焊點產生
      expect(layout.junctionDots.length).toBe(2)
    })

    it('USB 4-port Type-C 連接器與並聯次要端點排版 (TJ1 4 ports, TL1 CMC, TU2 & P72 分支)', () => {
      const usbData: UniversalTopologyData = {
        title: 'TJ1 ↔ TL1 ↔ TU2 ↔ P72 (USB8_USB20 差分通道)',
        channel_type: 'differential',
        rails: [
          { id: 'p_rail', name: '正極軌道', polarity: 'P' },
          { id: 'n_rail', name: '負極軌道', polarity: 'N' },
        ],
        nodes: [
          {
            id: 'TJ1',
            ref_des: 'TJ1',
            category: 'Connector',
            role: 'terminal',
            pins: [
              { pin_number: 'B6', pin_name: 'DP2' },
              { pin_number: 'A7', pin_name: 'DN1' },
              { pin_number: 'B7', pin_name: 'DN2' },
              { pin_number: 'A6', pin_name: 'DP1' },
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
              { pin_number: '2', orientation: 'left' },
              { pin_number: '1', orientation: 'right' },
            ],
          },
          {
            id: 'TU2',
            ref_des: 'TU2',
            category: 'IC',
            role: 'terminal',
            pins: [
              { pin_number: '2', pin_name: 'D1P' },
              { pin_number: '7', pin_name: 'D2P' },
              { pin_number: '1', pin_name: 'D1M' },
              { pin_number: '8', pin_name: 'D2M' },
            ],
          },
          {
            id: 'P72',
            ref_des: 'P72',
            category: 'Connector',
            role: 'terminal',
            pins: [
              { pin_number: '39', pin_name: '39' },
              { pin_number: '37', pin_name: '37' },
            ],
          },
        ],
        connections: [
          {
            net_name: 'USB8_USB20_CMC_P',
            rail_id: 'p_rail',
            from_node: 'TJ1',
            from_pin: 'B6',
            to_node: 'TL1',
            to_pin: '3',
          },
          {
            net_name: 'USB8_USB20_CMC_P',
            rail_id: 'p_rail',
            from_node: 'TJ1',
            from_pin: 'A7',
            to_node: 'TL1',
            to_pin: '3',
          },
          {
            net_name: 'USB8_USB20_P',
            rail_id: 'p_rail',
            from_node: 'TL1',
            from_pin: '4',
            to_node: 'TU2',
            to_pin: '2',
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
            from_node: 'TL1',
            from_pin: '4',
            to_node: 'P72',
            to_pin: '39',
          },
          {
            net_name: 'USB8_USB20_CMC_N',
            rail_id: 'n_rail',
            from_node: 'TJ1',
            from_pin: 'B7',
            to_node: 'TL1',
            to_pin: '2',
          },
          {
            net_name: 'USB8_USB20_CMC_N',
            rail_id: 'n_rail',
            from_node: 'TJ1',
            from_pin: 'A6',
            to_node: 'TL1',
            to_pin: '2',
          },
          {
            net_name: 'USB8_USB20_N',
            rail_id: 'n_rail',
            from_node: 'TL1',
            from_pin: '1',
            to_node: 'TU2',
            to_pin: '1',
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
            from_node: 'TL1',
            from_pin: '1',
            to_node: 'P72',
            to_pin: '37',
          },
        ],
      }

      const layout = computeUniversalTopologyLayout(usbData)

      // 1. 斷言 TJ1 包含全部 4 個 ports (B6, A7, B7, A6)
      const tj1 = layout.nodes.find((n) => n.id === 'TJ1')!
      expect(tj1).toBeDefined()
      expect(tj1.ports.length).toBe(4)
      const tj1Pins = tj1.ports.map((p) => p.pinNumber)
      expect(tj1Pins).toContain('B6')
      expect(tj1Pins).toContain('A7')
      expect(tj1Pins).toContain('B7')
      expect(tj1Pins).toContain('A6')

      // 2. 斷言同軌多引腳匯流 (TJ1 右側打上 P/N 匯流焊點)
      expect(layout.junctionDots.some((d) => d.id === 'merge_dot_TJ1_p')).toBe(true)
      expect(layout.junctionDots.some((d) => d.id === 'merge_dot_TJ1_n')).toBe(true)

      // 3. 斷言 P72 正確擁有 pin 39 與 pin 37 且無掉線 (極性吻合)
      const p72 = layout.nodes.find((n) => n.id === 'P72')!
      expect(p72).toBeDefined()
      expect(p72.ports.length).toBe(2)
      const p72Pin37 = p72.ports.find((p) => p.pinNumber === '37')
      const p72Pin39 = p72.ports.find((p) => p.pinNumber === '39')
      expect(p72Pin37).toBeDefined()
      expect(p72Pin37?.polarity).toBe('n')
      expect(p72Pin39).toBeDefined()
      expect(p72Pin39?.polarity).toBe('p')

      // 4. 斷言 TU2 與 P72 位於同一 Stage 且外框完全分離，保持至少 14px 垂直安全淨間隙
      const tu2 = layout.nodes.find((n) => n.id === 'TU2')!
      expect(tu2).toBeDefined()
      expect(p72.y).toBeGreaterThanOrEqual(tu2.y + tu2.height + 14)

      // 5. 斷言連線精準連接到 P72 的 pin 37 與 pin 39
      const p72Edges = layout.edges.filter((e) => e.targetId === 'P72')
      expect(p72Edges.length).toBe(2)
      const p72NEdge = p72Edges.find((e) => e.polarity === 'n')
      const p72PEdge = p72Edges.find((e) => e.polarity === 'p')
      expect(p72NEdge).toBeDefined()
      expect(p72PEdge).toBeDefined()
      expect(p72NEdge?.end.y).toBe(p72Pin37?.y)
      expect(p72PEdge?.end.y).toBe(p72Pin39?.y)

      // 6. 斷言分叉到 P72 的垂直導線與焊點保持水平空間，X 座標絕不重疊且間隔寬裕 (相距至少 20px)
      const p72JunctionDots = layout.junctionDots.filter((d) => d.id.includes('P72'))
      expect(p72JunctionDots.length).toBe(2)
      const pDot = p72JunctionDots.find((d) => d.polarity === 'p')!
      const nDot = p72JunctionDots.find((d) => d.polarity === 'n')!
      expect(pDot).toBeDefined()
      expect(nDot).toBeDefined()
      expect(Math.abs(pDot.x - nDot.x)).toBeGreaterThanOrEqual(20)

      // 7. 斷言 P 軌分接焊點與 TU2 目標分流焊點之間保持至少 20px 的安全距離
      const tu2SplitDot = layout.junctionDots.find((d) => d.id === 'split_dot_TU2_p')
      if (tu2SplitDot) {
        expect(Math.abs(tu2SplitDot.x - pDot.x)).toBeGreaterThanOrEqual(20)
      }

      // 8. 斷言正負極軌道垂直基準高度緊湊適度 (組間差距縮小為 50px，避免元件過高空洞)
      const tj1PPort = tj1.ports.find((p) => p.pinNumber === 'B6')!
      const tj1NPort = tj1.ports.find((p) => p.pinNumber === 'B7')!
      expect(tj1NPort.y - tj1PPort.y).toBeLessThanOrEqual(60)

      // 9. 斷言最頂部 port 距離節點頂部保留至少 24px (避開上方零件編號 RefDes，防止文字重疊)
      const tu2TopPort = tu2.ports.find((p) => p.pinNumber === '2')!
      expect(tu2TopPort.relY).toBeGreaterThanOrEqual(24)
      const tl1 = layout.nodes.find((n) => n.id === 'TL1')!
      const tl1TopPort = tl1.ports[0]!
      expect(tl1TopPort.relY).toBeGreaterThanOrEqual(24)
    })

    it('空資料或不合法資料之優雅回退', () => {
      const layout = computeUniversalTopologyLayout(undefined)
      expect(layout.nodes).toEqual([])
      expect(layout.edges).toEqual([])
      expect(layout.width).toBeGreaterThan(0)
      expect(layout.height).toBeGreaterThan(0)
    })

    it('差分直連通道 (E33 ↔ E34 含 5INCH 網路名) 正負極分離與動態導線長度計算', () => {
      const topoData: UniversalTopologyData = {
        title: 'E33 -> E34 (L1_85_MS_5INCH_P_DL4 差分通道)',
        channel_type: 'differential',
        rails: [
          { id: 'p_rail', name: '正極軌道 (L1_85_MS_5INCH_P_DL4)', polarity: 'P' },
          { id: 'n_rail', name: '負極軌道 (L1_85_MS_5INCH_N_DL4)', polarity: 'N' },
        ],
        nodes: [
          {
            id: 'E33',
            ref_des: 'E33',
            category: 'NonElectrical',
            role: 'terminal',
            is_mounted: false,
            pins: [
              { pin_number: '2', pin_name: 'X-' },
              { pin_number: '1', pin_name: 'X+' },
            ],
            bom: 'X',
            part_number: 'test for SIM_7PIN',
          },
          {
            id: 'E34',
            ref_des: 'E34',
            category: 'NonElectrical',
            role: 'terminal',
            is_mounted: false,
            pins: [
              { pin_number: '1', pin_name: 'X+' },
              { pin_number: '2', pin_name: 'X-' },
            ],
            bom: 'X',
            part_number: 'test for SIM_7PIN',
          },
        ],
        connections: [
          {
            net_name: 'L1_85_MS_5INCH_P_DL4',
            rail_id: 'p_rail',
            from_node: 'E33',
            from_pin: '2',
            to_node: 'E34',
            to_pin: '1',
            is_branch: false,
          },
          {
            net_name: 'L1_85_MS_5INCH_N_DL4',
            rail_id: 'n_rail',
            from_node: 'E33',
            from_pin: '1',
            to_node: 'E34',
            to_pin: '2',
            is_branch: false,
          },
        ],
      }

      const layout = computeUniversalTopologyLayout(topoData)

      // 1. 斷言節點正確生成且未上件狀態保持
      expect(layout.nodes.length).toBe(2)
      const e33 = layout.nodes.find((n) => n.id === 'E33')!
      const e34 = layout.nodes.find((n) => n.id === 'E34')!
      expect(e33.isMounted).toBe(false)
      expect(e34.isMounted).toBe(false)

      // 2. 斷言差分正負極兩條平行導線獨立分開，不發生誤合併或重疊
      expect(layout.edges.length).toBe(2)
      const pEdge = layout.edges.find((e) => e.polarity === 'p')!
      const nEdge = layout.edges.find((e) => e.polarity === 'n')!
      expect(pEdge).toBeDefined()
      expect(nEdge).toBeDefined()
      expect(pEdge.netName).toBe('L1_85_MS_5INCH_P_DL4')
      expect(nEdge.netName).toBe('L1_85_MS_5INCH_N_DL4')

      // 正極導線走 P 軌 (Y=65)，負極導線走 N 軌 (Y=115)
      expect(pEdge.start.y).toBe(65)
      expect(pEdge.end.y).toBe(65)
      expect(nEdge.start.y).toBe(115)
      expect(nEdge.end.y).toBe(115)

      // 3. 直連通道不應有任何匯流或分流焊點
      expect(layout.junctionDots.length).toBe(0)

      // 4. 斷言導線長度真實依照 net_name 字元長度計算，不使用死板固定預留值
      const netLen = 'L1_85_MS_5INCH_P_DL4'.length // 20 字元
      const expectedWireLen = Math.ceil(netLen * 5.3) + 28 // 106 + 28 = 134
      const actualWireLen = pEdge.end.x - pEdge.start.x
      expect(actualWireLen).toBe(expectedWireLen)
      expect(actualWireLen).not.toBe(90) // 證明非舊有固定 90px

      // 5. 斷言實體 net 標籤水平精確置中於導線段中點
      expect(layout.netLabels.length).toBe(2)
      const pLabel = layout.netLabels.find((l) => l.polarity === 'p')!
      const nLabel = layout.netLabels.find((l) => l.polarity === 'n')!
      expect(pLabel.x).toBe(Math.round((pEdge.start.x + pEdge.end.x) / 2))
      expect(nLabel.x).toBe(Math.round((nEdge.start.x + nEdge.end.x) / 2))
    })

    it('多端點直連差分通道 (XU1 ↔ XMM1, XMM2) 1 對多發散扇出與垂直分支焊點', () => {
      const ddrData: UniversalTopologyData = {
        title: 'XU1 -> XMM1, XMM2 (M_B_DDR1_DQS0 差分通道)',
        channel_type: 'differential',
        rails: [
          { id: 'p_rail', name: '正極軌道 (M_B_DDR1_DQS0_DP)', polarity: 'P' },
          { id: 'n_rail', name: '負極軌道 (M_B_DDR1_DQS0_DN)', polarity: 'N' },
        ],
        nodes: [
          {
            id: 'XU1',
            ref_des: 'XU1',
            category: 'Connector',
            role: 'terminal',
            is_mounted: true,
            pins: [
              { pin_number: 'AL47', pin_name: 'AL47' },
              { pin_number: 'AK48', pin_name: 'AK48' },
            ],
            bom: 'I',
            part_number: 'Socket_LGA 1954_15u_Black',
          },
          {
            id: 'XMM1',
            ref_des: 'XMM1',
            category: 'Connector',
            role: 'terminal',
            is_mounted: true,
            pins: [
              { pin_number: '14', pin_name: '14' },
              { pin_number: '13', pin_name: '13' },
            ],
            bom: 'I',
            part_number: 'UDIMM_287P_15u_Black',
          },
          {
            id: 'XMM2',
            ref_des: 'XMM2',
            category: 'Connector',
            role: 'terminal',
            is_mounted: true,
            pins: [
              { pin_number: '14', pin_name: '14' },
              { pin_number: '13', pin_name: '13' },
            ],
            bom: 'I',
            part_number: 'UDIMM_287P_15u_Natural',
          },
        ],
        connections: [
          {
            net_name: 'M_B_DDR1_DQS0_DP',
            rail_id: 'p_rail',
            from_node: 'XU1',
            from_pin: 'AL47',
            to_node: 'XMM1',
            to_pin: '14',
            is_branch: false,
          },
          {
            net_name: 'M_B_DDR1_DQS0_DN',
            rail_id: 'n_rail',
            from_node: 'XU1',
            from_pin: 'AK48',
            to_node: 'XMM1',
            to_pin: '13',
            is_branch: false,
          },
          {
            net_name: 'M_B_DDR1_DQS0_DP',
            rail_id: 'p_rail',
            from_node: 'XU1',
            from_pin: 'AL47',
            to_node: 'XMM2',
            to_pin: '14',
            is_branch: false,
          },
          {
            net_name: 'M_B_DDR1_DQS0_DN',
            rail_id: 'n_rail',
            from_node: 'XU1',
            from_pin: 'AK48',
            to_node: 'XMM2',
            to_pin: '13',
            is_branch: false,
          },
        ],
      }

      const layout = computeUniversalTopologyLayout(ddrData)

      // 1. 斷言 3 個端點元件完整呈現
      expect(layout.nodes.length).toBe(3)
      const xu1 = layout.nodes.find((n) => n.id === 'XU1')!
      const xmm1 = layout.nodes.find((n) => n.id === 'XMM1')!
      const xmm2 = layout.nodes.find((n) => n.id === 'XMM2')!
      expect(xu1).toBeDefined()
      expect(xmm1).toBeDefined()
      expect(xmm2).toBeDefined()

      // XU1 位於左側源端 (X 最小)，XMM1 與 XMM2 位於右側
      expect(xu1.x).toBeLessThan(xmm1.x)
      expect(xu1.x).toBeLessThan(xmm2.x)

      // 2. 斷言 XMM2 作為次要端點向下垂直錯開，不發生方塊重疊
      expect(xmm2.y).toBeGreaterThan(xmm1.y)

      // 3. 斷言 4 條差分連線完整繪製 (XMM2 不再是孤島)
      expect(layout.edges.length).toBe(4)
      const xmm2Edges = layout.edges.filter((e) => e.targetId === 'XMM2')
      expect(xmm2Edges.length).toBe(2)
      expect(xmm2Edges.map((e) => e.polarity)).toContain('p')
      expect(xmm2Edges.map((e) => e.polarity)).toContain('n')

      // 4. 斷言產生實體分接焊點 (Junction Dots ●)，P 軌與 N 軌各 1 個，水平錯開防重疊
      const xmm2Dots = layout.junctionDots.filter((d) => d.id.includes('XMM2'))
      expect(xmm2Dots.length).toBe(2)
      const pDot = xmm2Dots.find((d) => d.polarity === 'p')!
      const nDot = xmm2Dots.find((d) => d.polarity === 'n')!
      expect(pDot).toBeDefined()
      expect(nDot).toBeDefined()
      expect(Math.abs(pDot.x - nDot.x)).toBeGreaterThanOrEqual(20)
    })

    it('後端網路圖拓撲 (U4 → {R63∥L19 缺 PartDB} → CON 網路 J90 tap → R2 → U78)：完整連線、tap 與並聯分支位於主幹下方、元件不重疊', () => {
      const mkPins = (list: [string, string?, UniversalPin['orientation']?][]): UniversalPin[] =>
        list.map(([pin_number, pin_name, orientation]) => ({ pin_number, pin_name, orientation }))
      const conn = (
        net_name: string, rail_id: string, from_node: string, from_pin: string,
        to_node: string, to_pin: string, is_branch = false,
      ) => ({ net_name, rail_id, from_node, from_pin, to_node, to_pin, is_branch })

      const topo: UniversalTopologyData = {
        title: 'U4 -> R63 -> R2 -> R1 -> R64 -> J90, U78 (USBC1_USB20 差分通道)',
        channel_type: 'differential',
        rails: [
          { id: 'p_rail', name: '正極軌道 (USBC1_USB20_P)', polarity: 'P' },
          { id: 'n_rail', name: '負極軌道 (USBC1_USB20_N)', polarity: 'N' },
        ],
        nodes: [
          { id: 'U4', ref_des: 'U4', category: 'IC', role: 'terminal', is_mounted: true, pins: mkPins([['C12', 'C12'], ['B12', 'B12']]) },
          { id: 'J90', ref_des: 'J90', category: 'Connector', role: 'terminal', is_mounted: true, lane: 'tap',
            pins: mkPins([['A6', 'Dp1'], ['B6', 'Dp2'], ['A7', 'Dn1'], ['B7', 'Dn2']]) },
          { id: 'U78', ref_des: 'U78', category: 'IC', role: 'terminal', is_mounted: true, pins: mkPins([['28', 'DP'], ['27', 'DM']]) },
          { id: 'R63', ref_des: 'R63', category: 'Resistor', role: 'series', is_mounted: true, pins: mkPins([['2', undefined, 'left'], ['1', undefined, 'right']]) },
          { id: 'R2', ref_des: 'R2', category: 'Resistor', role: 'series', is_mounted: true, pins: mkPins([['1', undefined, 'left'], ['2', undefined, 'right']]) },
          { id: 'L19', ref_des: 'L19', category: 'Common_Mode_Choke', role: 'series', is_mounted: false, bom: 'X', lane: 'branch', partdb_missing: true,
            pins: mkPins([['4', undefined, 'left'], ['3', undefined, 'right'], ['2', undefined, 'left'], ['1', undefined, 'right']]) },
          { id: 'R1', ref_des: 'R1', category: 'Resistor', role: 'series', is_mounted: true, pins: mkPins([['2', undefined, 'left'], ['1', undefined, 'right']]) },
          { id: 'R64', ref_des: 'R64', category: 'Resistor', role: 'series', is_mounted: true, pins: mkPins([['1', undefined, 'left'], ['2', undefined, 'right']]) },
        ],
        connections: [
          conn('USBC1_USB20_P', 'p_rail', 'U4', 'C12', 'R63', '2'),
          conn('USBC1_USB20_P', 'p_rail', 'U4', 'C12', 'L19', '4', true),
          conn('USBC1_USB20_CON_P', 'p_rail', 'R63', '1', 'R2', '1'),
          conn('USBC1_USB20_CON_P', 'p_rail', 'R63', '1', 'J90', 'A6'),
          conn('USBC1_USB20_CON_P', 'p_rail', 'R63', '1', 'J90', 'B6'),
          conn('USBC1_USB20_CON_P', 'p_rail', 'L19', '3', 'R2', '1', true),
          conn('USBC1_USB20_PD1_P', 'p_rail', 'R2', '2', 'U78', '28'),
          conn('USBC1_USB20_N', 'n_rail', 'U4', 'B12', 'R1', '2'),
          conn('USBC1_USB20_N', 'n_rail', 'U4', 'B12', 'L19', '2', true),
          conn('USBC1_USB20_CON_N', 'n_rail', 'R1', '1', 'R64', '1'),
          conn('USBC1_USB20_CON_N', 'n_rail', 'R1', '1', 'J90', 'A7'),
          conn('USBC1_USB20_CON_N', 'n_rail', 'R1', '1', 'J90', 'B7'),
          conn('USBC1_USB20_CON_N', 'n_rail', 'L19', '1', 'R64', '1', true),
          conn('USBC1_USB20_PD1_N', 'n_rail', 'R64', '2', 'U78', '27'),
        ],
      }

      const layout = computeUniversalTopologyLayout(topo)
      const node = (id: string) => layout.nodes.find((n) => n.id === id)!

      // 1. 8 個元件全部呈現，且 Stage 由左至右：U4 < {R63,R1,L19} < {R2,R64,J90} < U78
      expect(layout.nodes.length).toBe(8)
      expect(node('U4').x).toBeLessThan(node('R63').x)
      expect(node('R63').x).toBe(node('L19').x)
      expect(node('R63').x).toBe(node('R1').x)
      expect(node('R63').x).toBeLessThan(node('R2').x)
      expect(node('R2').x).toBe(node('J90').x)
      expect(node('R2').x).toBe(node('R64').x)
      expect(node('R2').x).toBeLessThan(node('U78').x)

      // 2. 主幹元件在 P/N 主軌，並聯 L19 與 tap 端點 J90 皆位於主幹 (N 軌 Y=115) 下方車道
      expect(node('R63').y).toBeLessThan(100)
      expect(node('L19').y).toBeGreaterThan(115)
      expect(node('J90').y).toBeGreaterThan(115)
      expect(node('L19').partdbMissing).toBe(true)

      // 3. 連線完整：每條 connection 皆產生導線，J90 的 P(A6/B6) 與 N(A7/B7) 四支引腳皆有導線抵達
      const j90Edges = layout.edges.filter((e) => e.targetId === 'J90')
      expect(j90Edges.map((e) => e.polarity)).toContain('p')
      expect(j90Edges.map((e) => e.polarity)).toContain('n')
      expect(layout.edges.some((e) => e.sourceId === 'L19' && e.targetId === 'R2')).toBe(true)
      expect(layout.edges.some((e) => e.sourceId === 'U4' && e.targetId === 'L19')).toBe(true)
      for (const e of layout.edges) {
        expect(e.pathD).not.toContain('NaN')
        expect(e.pathD.length).toBeGreaterThan(5)
      }

      // 4. 任意兩個元件方塊不得重疊 (AABB 檢查)
      for (let i = 0; i < layout.nodes.length; i++) {
        for (let j = i + 1; j < layout.nodes.length; j++) {
          const a = layout.nodes[i]
          const b = layout.nodes[j]
          const overlap =
            a.x < b.x + b.width && b.x < a.x + a.width && a.y < b.y + b.height && b.y < a.y + a.height
          expect(overlap, `${a.id} 與 ${b.id} 重疊`).toBe(false)
        }
      }
    })

    it('並聯穿透群與未上件共模扼流圈 (U4 ↔ UR810/UL810 [X] ↔ J81) 雙軌避讓與垂直線零重疊', () => {
      const parallelData: UniversalTopologyData = {
        title: 'U4 -> UR810 -> J81 (USB2_DP 差分通道)',
        channel_type: 'differential',
        rails: [
          { id: 'p_rail', name: '正極軌道 (USB2_DP)', polarity: 'P' },
          { id: 'n_rail', name: '負極軌道 (USB2_DN)', polarity: 'N' },
        ],
        nodes: [
          {
            id: 'U4',
            ref_des: 'U4',
            category: 'IC',
            role: 'terminal',
            pins: [
              { pin_number: '1', pin_name: 'DP', orientation: 'right' },
              { pin_number: '2', pin_name: 'DN', orientation: 'right' },
            ],
            is_mounted: true,
          },
          {
            id: 'UR810',
            ref_des: 'UR810',
            category: 'Passive',
            role: 'series',
            part_number: '0_OHM',
            pins: [
              { pin_number: '1', orientation: 'left' },
              { pin_number: '2', orientation: 'right' },
            ],
            is_mounted: true,
          },
          {
            id: 'UL810',
            ref_des: 'UL810',
            category: 'Passive',
            role: 'series',
            part_number: 'CMF_90_300mA',
            pins: [
              { pin_number: '1', orientation: 'left' },
              { pin_number: '2', orientation: 'right' },
              { pin_number: '3', orientation: 'left' },
              { pin_number: '4', orientation: 'right' },
            ],
            is_mounted: false,
            bom: 'NI',
          },
          {
            id: 'J81',
            ref_des: 'J81',
            category: 'Connector',
            role: 'terminal',
            pins: [
              { pin_number: 'A6', pin_name: 'DP', orientation: 'left' },
              { pin_number: 'A7', pin_name: 'DN', orientation: 'left' },
            ],
            is_mounted: true,
          },
        ],
        connections: [
          // 主幹 U4 -> UR810 -> J81
          {
            net_name: 'USB2_DP',
            rail_id: 'p_rail',
            from_node: 'U4',
            from_pin: '1',
            to_node: 'UR810',
            to_pin: '1',
            is_branch: false,
          },
          {
            net_name: 'USB_CON_DP',
            rail_id: 'p_rail',
            from_node: 'UR810',
            from_pin: '2',
            to_node: 'J81',
            to_pin: 'A6',
            is_branch: false,
          },
          // 並聯分支 U4 -> UL810 -> J81
          {
            net_name: 'USB2_DP',
            rail_id: 'p_rail',
            from_node: 'U4',
            from_pin: '1',
            to_node: 'UL810',
            to_pin: '1',
            is_branch: true,
          },
          {
            net_name: 'USB_CON_DP',
            rail_id: 'p_rail',
            from_node: 'UL810',
            from_pin: '2',
            to_node: 'J81',
            to_pin: 'A6',
            is_branch: true,
          },
          {
            net_name: 'USB2_DN',
            rail_id: 'n_rail',
            from_node: 'U4',
            from_pin: '2',
            to_node: 'UL810',
            to_pin: '3',
            is_branch: true,
          },
          {
            net_name: 'USB_CON_DN',
            rail_id: 'n_rail',
            from_node: 'UL810',
            from_pin: '4',
            to_node: 'J81',
            to_pin: 'A7',
            is_branch: true,
          },
        ],
      }

      const layout = computeUniversalTopologyLayout(parallelData)

      // 1. 斷言 4 個元件全部呈現
      expect(layout.nodes.length).toBe(4)
      const u4 = layout.nodes.find((n) => n.id === 'U4')!
      const ur810 = layout.nodes.find((n) => n.id === 'UR810')!
      const ul810 = layout.nodes.find((n) => n.id === 'UL810')!
      const j81 = layout.nodes.find((n) => n.id === 'J81')!

      expect(u4).toBeDefined()
      expect(ur810).toBeDefined()
      expect(ul810).toBeDefined()
      expect(j81).toBeDefined()

      // 2. 斷言流向：U4 在左 (Stage 0)，中間穿透群 (Stage 1)，J81 在右 (Stage 2)
      expect(u4.x).toBeLessThan(ur810.x)
      expect(ur810.x).toBeLessThan(j81.x)

      // 3. 斷言並聯元件垂直避讓：UR810 位於主軌 (Y ~ 65)，UL810 CMC 下移至避讓軌道 (Y > 140)
      expect(ur810.y).toBeLessThan(100)
      expect(ul810.y).toBeGreaterThanOrEqual(130)

      // 4. 斷言並聯元件入線與出線的垂直折線在 X 座標完全錯開 (零重疊)
      const ul810InEdges = layout.edges.filter((e) => e.targetId === 'UL810')
      const ul810OutEdges = layout.edges.filter((e) => e.sourceId === 'UL810')
      expect(ul810InEdges.length).toBeGreaterThanOrEqual(1)
      expect(ul810OutEdges.length).toBeGreaterThanOrEqual(1)

      const inDots = layout.junctionDots.filter((d) => d.id.includes('junc_tap_in') && d.id.includes('UL810'))
      const outDots = layout.junctionDots.filter((d) => d.id.includes('junc_tap_out') && d.id.includes('UL810'))

      expect(inDots.length).toBeGreaterThanOrEqual(1)
      expect(outDots.length).toBeGreaterThanOrEqual(1)

      // 入線焊點 (Tap In) 必須在 UL810 左側 (X < ul810.x)
      // 出線焊點 (Tap Out) 必須在 UL810 右側 (X > ul810.x + ul810.width)
      for (const inDot of inDots) {
        expect(inDot.x).toBeLessThan(ul810.x)
      }
      for (const outDot of outDots) {
        expect(outDot.x).toBeGreaterThan(ul810.x + ul810.width)
      }

      // 入線與出線垂直折線水平間距必須 >= 50px，確保完全無垂直重疊
      const minOutDotX = Math.min(...outDots.map((d) => d.x))
      const maxInDotX = Math.max(...inDots.map((d) => d.x))
      expect(minOutDotX - maxInDotX).toBeGreaterThanOrEqual(50)
    })

    it('中繼 Hub (KU100) 與 Bypass 電阻雙路徑匯流 + 並聯 CMC (FUSBA1_USB20_CON)：分層對齊、同車道水平直連、Net Name 緊貼水平線', () => {
      const mkPins = (list: [string, string?, UniversalPin['orientation']?][]): UniversalPin[] =>
        list.map(([pin_number, pin_name, orientation]) => ({ pin_number, pin_name, orientation }))
      const conn = (
        net_name: string, rail_id: string, from_node: string, from_pin: string,
        to_node: string, to_pin: string, is_branch = false,
      ) => ({ net_name, rail_id, from_node, from_pin, to_node, to_pin, is_branch })

      const fusba1Topo: UniversalTopologyData = {
        title: 'U4 -> KR135 -> UR800 -> J80 (FUSBA1_USB20_CON 差分通道)',
        channel_type: 'differential',
        rails: [
          { id: 'p_rail', name: '正極軌道 (USB2_P1_DP)', polarity: 'P' },
          { id: 'n_rail', name: '負極軌道 (USB2_P1_DN)', polarity: 'N' },
        ],
        nodes: [
          { id: 'U4', ref_des: 'U4', category: 'IC', role: 'terminal', is_mounted: true, pins: mkPins([['AE9', 'AE9'], ['AE11', 'AE11']]) },
          { id: 'KR135', ref_des: 'KR135', category: 'Passive', role: 'series', is_mounted: false, bom: 'X', pins: mkPins([['1', undefined, 'left'], ['2', undefined, 'right']]) },
          { id: 'KR136', ref_des: 'KR136', category: 'Passive', role: 'series', is_mounted: false, bom: 'X', pins: mkPins([['1', undefined, 'left'], ['2', undefined, 'right']]) },
          { id: 'KR104', ref_des: 'KR104', category: 'Passive', role: 'series', is_mounted: true, pins: mkPins([['1', undefined, 'left'], ['2', undefined, 'right']]) },
          { id: 'KR105', ref_des: 'KR105', category: 'Passive', role: 'series', is_mounted: true, pins: mkPins([['1', undefined, 'left'], ['2', undefined, 'right']]) },
          {
            id: 'KU100', ref_des: 'KU100', category: 'IC', role: 'series', is_mounted: true,
            pins: mkPins([
              ['47', 'UFP_DP', 'left'],
              ['49', 'DFP1_DP', 'right'],
              ['46', 'UFP_DM', 'left'],
              ['48', 'DFP1_DM', 'right'],
            ]),
          },
          { id: 'KR129', ref_des: 'KR129', category: 'Passive', role: 'series', is_mounted: true, pins: mkPins([['1', undefined, 'left'], ['2', undefined, 'right']]) },
          { id: 'KR130', ref_des: 'KR130', category: 'Passive', role: 'series', is_mounted: true, pins: mkPins([['1', undefined, 'left'], ['2', undefined, 'right']]) },
          { id: 'UR800', ref_des: 'UR800', category: 'Passive', role: 'series', is_mounted: true, pins: mkPins([['1', undefined, 'left'], ['2', undefined, 'right']]) },
          { id: 'UR801', ref_des: 'UR801', category: 'Passive', role: 'series', is_mounted: true, pins: mkPins([['1', undefined, 'left'], ['2', undefined, 'right']]) },
          {
            id: 'UL800', ref_des: 'UL800', category: 'Common_Mode_Choke', role: 'series', is_mounted: false, bom: 'X', lane: 'branch',
            pins: mkPins([['1', undefined, 'left'], ['2', undefined, 'right'], ['4', undefined, 'left'], ['3', undefined, 'right']]),
          },
          { id: 'J80', ref_des: 'J80', category: 'Connector', role: 'terminal', is_mounted: true, pins: mkPins([['3', 'D+'], ['2', 'D-']]) },
        ],
        connections: [
          // Bypass 2-hop 支路: U4 -> KR135/KR136 -> UR800/UR801 & UL800
          conn('USB2_P1_DP', 'p_rail', 'U4', 'AE9', 'KR135', '1'),
          conn('USB2_P1_DN', 'n_rail', 'U4', 'AE11', 'KR136', '1'),
          conn('FUSBA1_USB20_CON_DP', 'p_rail', 'KR135', '2', 'UR800', '1'),
          conn('FUSBA1_USB20_CON_DN', 'n_rail', 'KR136', '2', 'UR801', '1'),
          conn('FUSBA1_USB20_CON_DP', 'p_rail', 'KR135', '2', 'UL800', '1', true),
          conn('FUSBA1_USB20_CON_DN', 'n_rail', 'KR136', '2', 'UL800', '4', true),
          // Hub 3-hop 支路: U4 -> KR104/KR105 -> KU100 -> KR129/KR130 -> UR800/UR801
          conn('USB2_P1_DP', 'p_rail', 'U4', 'AE9', 'KR104', '1', true),
          conn('USB2_P1_DN', 'n_rail', 'U4', 'AE11', 'KR105', '1', true),
          conn('USB_HUB1_UP_DP', 'p_rail', 'KR104', '2', 'KU100', '47'),
          conn('USB_HUB1_UP_DN', 'n_rail', 'KR105', '2', 'KU100', '46'),
          conn('USB_HUB1_DN1_DP', 'p_rail', 'KU100', '49', 'KR129', '1'),
          conn('USB_HUB1_DN1_DN', 'n_rail', 'KU100', '48', 'KR130', '1'),
          conn('FUSBA1_USB20_CON_DP', 'p_rail', 'KR129', '2', 'UR800', '1', true),
          conn('FUSBA1_USB20_CON_DN', 'n_rail', 'KR130', '2', 'UR801', '1', true),
          // 匯流後至終點 J80
          conn('FUSBA1_USB20_DP', 'p_rail', 'UR800', '2', 'J80', '3'),
          conn('FUSBA1_USB20_DN', 'n_rail', 'UR801', '2', 'J80', '2'),
          conn('FUSBA1_USB20_DP', 'p_rail', 'UL800', '2', 'J80', '3', true),
          conn('FUSBA1_USB20_DN', 'n_rail', 'UL800', '3', 'J80', '2', true),
        ],
      }

      const layout = computeUniversalTopologyLayout(fusba1Topo)
      const node = (id: string) => layout.nodes.find((n) => n.id === id)!

      // 1. 最長路徑分層對齊：U4 (Col 0) < KR104 (Col 1) < KU100 (Col 2) < KR129 (Col 3) < UR800/UL800 (Col 4) < J80 (Col 5)
      expect(node('U4').x).toBeLessThan(node('KR104').x)
      expect(node('KR104').x).toBeLessThan(node('KU100').x)
      expect(node('KU100').x).toBeLessThan(node('KR129').x)
      expect(node('KR129').x).toBeLessThan(node('UR800').x)
      expect(node('UR800').x).toBe(node('UL800').x)
      expect(node('UR800').x).toBeLessThan(node('J80').x)

      // 2. 中繼 IC KU100 具備雙側具名引腳 (UFP_DP / DFP1_DP)，寬度自動擴展 (> 120px) 防止引腳名稱互撞
      expect(node('KU100').width).toBeGreaterThan(120)

      // 3. 次要路徑帶 (KR104 -> KU100 -> KR129) 內部為純水平直連 (start.y === end.y 且無轉折 Q)，絕不折回主幹 Band 0
      const kr104ToKu100 = layout.edges.find((e) => e.sourceId === 'KR104' && e.targetId === 'KU100')!
      const ku100ToKr129 = layout.edges.find((e) => e.sourceId === 'KU100' && e.targetId === 'KR129')!
      expect(kr104ToKu100.start.y).toBe(kr104ToKu100.end.y)
      expect(kr104ToKu100.pathD).not.toContain('Q ')
      expect(ku100ToKr129.start.y).toBe(ku100ToKr129.end.y)
      expect(ku100ToKr129.pathD).not.toContain('Q ')

      // 4. 任意兩個元件方塊絕不重疊
      for (let i = 0; i < layout.nodes.length; i++) {
        for (let j = i + 1; j < layout.nodes.length; j++) {
          const a = layout.nodes[i]
          const b = layout.nodes[j]
          const overlap =
            a.x < b.x + b.width && b.x < a.x + a.width && a.y < b.y + b.height && b.y < a.y + a.height
          expect(overlap, `${a.id} 與 ${b.id} 重疊`).toBe(false)
        }
      }

      // 5. 每個 Net Label 必須精確錨定於該網路某一條實際連線的水平高度正上方 (y === start.y - 3.5 或 end.y - 3.5)
      for (const label of layout.netLabels) {
        const netEdges = layout.edges.filter((e) => e.netName === label.net)
        const anchoredOnHorizontalSegment = netEdges.some(
          (edge) =>
            Math.abs(label.y - (edge.start.y - 3.5)) <= 1 || Math.abs(label.y - (edge.end.y - 3.5)) <= 1
        )
        expect(anchoredOnHorizontalSegment, `Net Label ${label.net} 未錨定在實際水平線段正上方`).toBe(true)
      }
    })

    it('1-to-2 串聯分叉選擇與單腳測試點緊湊掛載 (LAN2_CLK2_100M 含 TP56/TP57)：測點不佔主車道、向上/向下就近引出', () => {
      const mkPins = (list: [string, string?, UniversalPin['orientation']?][]): UniversalPin[] =>
        list.map(([pin_number, pin_name, orientation]) => ({ pin_number, pin_name, orientation }))
      const conn = (
        net_name: string, rail_id: string, from_node: string, from_pin: string,
        to_node: string, to_pin: string, is_branch = false,
      ) => ({ net_name, rail_id, from_node, from_pin, to_node, to_pin, is_branch })

      const lan2Topo: UniversalTopologyData = {
        title: 'XU1 -> LR136 -> LJ100, LU100 (LAN2_CLK2_100M 差分通道)',
        channel_type: 'differential',
        rails: [
          { id: 'p_rail', name: '正極軌道 (PE0_CLK3_100M_DP)', polarity: 'P' },
          { id: 'n_rail', name: '負極軌道 (PE0_CLK3_100M_DN)', polarity: 'N' },
        ],
        nodes: [
          { id: 'XU1', ref_des: 'XU1', category: 'IC', role: 'terminal', is_mounted: true, pins: mkPins([['C25', 'C25'], ['D25', 'D25']]) },
          { id: 'TP56', ref_des: 'TP56', category: 'TestPoint', role: 'terminal', is_mounted: false, bom: 'X', lane: 'tap', pins: mkPins([['1', '1']]) },
          { id: 'TP57', ref_des: 'TP57', category: 'TestPoint', role: 'terminal', is_mounted: false, bom: 'X', lane: 'tap', pins: mkPins([['1', '1']]) },
          { id: 'LR136', ref_des: 'LR136', category: 'Resistor', role: 'series', is_mounted: true, pins: mkPins([['1', undefined, 'left'], ['2', undefined, 'right']]) },
          { id: 'LR138', ref_des: 'LR138', category: 'Resistor', role: 'series', is_mounted: true, pins: mkPins([['1', undefined, 'left'], ['2', undefined, 'right']]) },
          { id: 'LR140', ref_des: 'LR140', category: 'Resistor', role: 'series', is_mounted: false, bom: 'X', pins: mkPins([['1', undefined, 'left'], ['2', undefined, 'right']]) },
          { id: 'LR142', ref_des: 'LR142', category: 'Resistor', role: 'series', is_mounted: false, bom: 'X', pins: mkPins([['1', undefined, 'left'], ['2', undefined, 'right']]) },
          { id: 'LJ100', ref_des: 'LJ100', category: 'Connector', role: 'terminal', is_mounted: true, pins: mkPins([['A13', 'REFCLK+'], ['A14', 'REFCLK-']]) },
          { id: 'LU100', ref_des: 'LU100', category: 'IC', role: 'terminal', is_mounted: true, pins: mkPins([['19', 'PE_CLKP'], ['20', 'PE_CLKN']]) },
        ],
        connections: [
          conn('PE0_CLK3_100M_DP', 'p_rail', 'XU1', 'C25', 'LR136', '1'),
          conn('PE0_CLK3_100M_DN', 'n_rail', 'XU1', 'D25', 'LR138', '1'),
          conn('PE0_CLK3_100M_DP', 'p_rail', 'XU1', 'C25', 'TP56', '1', true),
          conn('PE0_CLK3_100M_DN', 'n_rail', 'XU1', 'D25', 'TP57', '1', true),
          conn('PE0_CLK3_100M_DP', 'p_rail', 'XU1', 'C25', 'LR140', '1', true),
          conn('PE0_CLK3_100M_DN', 'n_rail', 'XU1', 'D25', 'LR142', '1', true),
          conn('OCP_CLK2_100M_DP', 'p_rail', 'LR136', '2', 'LJ100', 'A13'),
          conn('OCP_CLK2_100M_DN', 'n_rail', 'LR138', '2', 'LJ100', 'A14'),
          conn('LAN2_CLK2_100M_DP', 'p_rail', 'LR140', '2', 'LU100', '19'),
          conn('LAN2_CLK2_100M_DN', 'n_rail', 'LR142', '2', 'LU100', '20'),
        ],
      }

      const layout = computeUniversalTopologyLayout(lan2Topo)
      const node = (id: string) => layout.nodes.find((n) => n.id === id)!

      // 1. 斷言 TP56 與 TP57 正確識別為單腳測試點 (isTestPoint && isSinglePin)
      const tp56 = node('TP56')
      const tp57 = node('TP57')
      expect(tp56.isTestPoint).toBe(true)
      expect(tp56.isSinglePin).toBe(true)
      expect(tp57.isTestPoint).toBe(true)
      expect(tp57.isSinglePin).toBe(true)

      // 2. 斷言 TP56 從 P 軌向上就近引出 (y < P 軌 65)，TP57 從 N 軌向下就近引出 (y > N 軌 115)
      expect(tp56.ports[0].y).toBeLessThan(65)
      expect(tp57.ports[0].y).toBeGreaterThan(115)

      // 3. 斷言次要路徑帶 (LR140/LR142 -> LU100) 內部為水平直連，不會被拉回主幹 Band 0
      const lr140ToLu100 = layout.edges.find((e) => e.sourceId === 'LR140' && e.targetId === 'LU100')!
      const lr142ToLu100 = layout.edges.find((e) => e.sourceId === 'LR142' && e.targetId === 'LU100')!
      expect(lr140ToLu100.start.y).toBe(lr140ToLu100.end.y)
      expect(lr140ToLu100.pathD).not.toContain('Q ')
      expect(lr142ToLu100.start.y).toBe(lr142ToLu100.end.y)
      expect(lr142ToLu100.pathD).not.toContain('Q ')
    })

    it('中繼晶片與並聯 CMC/電阻回流 (KU100 ↔ UL830 [X] ∥ UR830/UR831 [X] ↔ J83) 垂直向上線與節點方塊零重疊', () => {
      const mkPins = (list: [string, string?, UniversalPin['orientation']?][]): UniversalPin[] =>
        list.map(([pin_number, pin_name, orientation]) => ({ pin_number, pin_name, orientation }))
      const conn = (
        net_name: string, rail_id: string, from_node: string, from_pin: string,
        to_node: string, to_pin: string, is_branch = false,
      ) => ({ net_name, rail_id, from_node, from_pin, to_node, to_pin, is_branch })

      const topo: UniversalTopologyData = {
        title: 'KU100 -> UL830 -> UR830 -> UR831 -> J83 (FUSBA4_USB20_CON)',
        channel_type: 'differential',
        rails: [
          { id: 'p_rail', name: 'P Rail', polarity: 'P' },
          { id: 'n_rail', name: 'N Rail', polarity: 'N' },
        ],
        nodes: [
          {
            id: 'KU100',
            ref_des: 'KU100',
            category: 'IC',
            role: 'terminal',
            is_mounted: false,
            pins: mkPins([['51', '51'], ['52', '52']]),
          },
          {
            id: 'UL830',
            ref_des: 'UL830',
            category: 'Common_Mode_Choke',
            role: 'series',
            value: 'CMF_90_300mA',
            is_mounted: false,
            pins: mkPins([
              ['4', undefined, 'left'],
              ['3', undefined, 'right'],
              ['1', undefined, 'left'],
              ['2', undefined, 'right'],
            ]),
          },
          {
            id: 'UR830',
            ref_des: 'UR830',
            category: 'Passive',
            role: 'series',
            value: '0_5%',
            is_mounted: false,
            pins: mkPins([
              ['2', undefined, 'left'],
              ['1', undefined, 'right'],
            ]),
          },
          {
            id: 'UR831',
            ref_des: 'UR831',
            category: 'Passive',
            role: 'series',
            value: '0_5%',
            is_mounted: false,
            pins: mkPins([
              ['2', undefined, 'left'],
              ['1', undefined, 'right'],
            ]),
          },
          {
            id: 'J83',
            ref_des: 'J83',
            category: 'Connector',
            role: 'terminal',
            is_mounted: false,
            pins: mkPins([
              ['3', 'D+'],
              ['2', 'D-'],
            ]),
          },
        ],
        connections: [
          conn('FUSBA4_USB20_P', 'p_rail', 'KU100', '51', 'UL830', '4'),
          conn('FUSBA4_USB20_N', 'n_rail', 'KU100', '52', 'UL830', '1'),
          conn('FUSBA4_USB20_CON_P', 'p_rail', 'UL830', '3', 'J83', '3'),
          conn('FUSBA4_USB20_CON_N', 'n_rail', 'UL830', '2', 'J83', '2'),

          conn('FUSBA4_USB20_P', 'p_rail', 'KU100', '51', 'UR830', '2', true),
          conn('FUSBA4_USB20_CON_P', 'p_rail', 'UR830', '1', 'J83', '3', true),

          conn('FUSBA4_USB20_N', 'n_rail', 'KU100', '52', 'UR831', '2', true),
          conn('FUSBA4_USB20_CON_N', 'n_rail', 'UR831', '1', 'J83', '2', true),
        ],
      }

      const layout = computeUniversalTopologyLayout(topo)
      const ul830 = layout.nodes.find((n) => n.id === 'UL830')!
      const ur830 = layout.nodes.find((n) => n.id === 'UR830')!
      const ur831 = layout.nodes.find((n) => n.id === 'UR831')!
      const ul830Right = ul830.x + ul830.width

      // 1. UL830 寬度 (88) 大於 UR830/UR831 (56)
      expect(ul830.width).toBeGreaterThan(ur830.width)

      // 2. 向上回流線段 (UR830/UR831 -> J83) 的出線焊點 (Tap Out) 必須嚴格在 UL830 右邊界之外
      const outDots = layout.junctionDots.filter((d) => d.id.includes('junc_tap_out'))
      expect(outDots.length).toBe(2)
      for (const dot of outDots) {
        expect(dot.x).toBeGreaterThan(ul830Right)
      }

      // 3. 向下分流線段 (KU100 -> UR830/UR831) 的入線焊點 (Tap In) 必須嚴格在 UL830 左邊界之左
      const inDots = layout.junctionDots.filter((d) => d.id.includes('junc_tap_in'))
      expect(inDots.length).toBe(2)
      for (const dot of inDots) {
        expect(dot.x).toBeLessThan(ul830.x)
      }

      // 4. 垂直線段絕不穿越 UL830 方塊矩形範圍 (X: [ul830.x, ul830Right], Y: [ul830.y, ul830.y + ul830.height])
      const ur830Edge = layout.edges.find((e) => e.sourceId === 'UR830' && e.targetId === 'J83')!
      const ur831Edge = layout.edges.find((e) => e.sourceId === 'UR831' && e.targetId === 'J83')!
      // 從路徑解析垂直段 X 座標
      const matchX = (pathD: string) => {
        const parts = pathD.match(/L (\d+) (\d+)/g) || []
        return parts.map((p) => Number(p.split(' ')[1]))
      }
      const xs = [...matchX(ur830Edge.pathD), ...matchX(ur831Edge.pathD)]
      for (const x of xs) {
        // 若 X 落於 UL830 水平寬度內，則不可與其垂直高度重合
        const insideX = x >= ul830.x && x <= ul830Right
        expect(insideX, `垂直導線 X=${x} 落於 UL830 節點水平範圍 [${ul830.x}, ${ul830Right}] 內產生重疊`).toBe(false)
      }
    })
  })
})
