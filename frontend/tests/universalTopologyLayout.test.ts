/**
 * @file universalTopologyLayout.test.ts
 * @description 通用電路拓撲排版演算法核心單元測試
 */

import { describe, it, expect } from 'vitest'
import {
  computeUniversalTopologyLayout,
  generateOrthogonalPath,
  type UniversalTopologyData,
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

      // 4. 斷言 TU2 與 P72 位於同一 Stage 但垂直錯開不重疊
      const tu2 = layout.nodes.find((n) => n.id === 'TU2')!
      expect(tu2).toBeDefined()
      expect(p72.y).toBeGreaterThan(tu2.y + tu2.height / 2)

      // 5. 斷言連線精準連接到 P72 的 pin 37 與 pin 39
      const p72Edges = layout.edges.filter((e) => e.targetId === 'P72')
      expect(p72Edges.length).toBe(2)
      const p72NEdge = p72Edges.find((e) => e.polarity === 'n')
      const p72PEdge = p72Edges.find((e) => e.polarity === 'p')
      expect(p72NEdge).toBeDefined()
      expect(p72PEdge).toBeDefined()
      expect(p72NEdge?.end.y).toBe(p72Pin37?.y)
      expect(p72PEdge?.end.y).toBe(p72Pin39?.y)

      // 6. 斷言分叉到 P72 的垂直導線與焊點保持水平空間，X 座標絕不重疊 (相距至少 14px)
      const p72JunctionDots = layout.junctionDots.filter((d) => d.id.includes('P72'))
      expect(p72JunctionDots.length).toBe(2)
      const pDot = p72JunctionDots.find((d) => d.polarity === 'p')!
      const nDot = p72JunctionDots.find((d) => d.polarity === 'n')!
      expect(pDot).toBeDefined()
      expect(nDot).toBeDefined()
      expect(Math.abs(pDot.x - nDot.x)).toBeGreaterThanOrEqual(14)
    })

    it('空資料或不合法資料之優雅回退', () => {
      const layout = computeUniversalTopologyLayout(undefined)
      expect(layout.nodes).toEqual([])
      expect(layout.edges).toEqual([])
      expect(layout.width).toBeGreaterThan(0)
      expect(layout.height).toBeGreaterThan(0)
    })
  })
})
