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

    it('空資料或不合法資料之優雅回退', () => {
      const layout = computeUniversalTopologyLayout(undefined)
      expect(layout.nodes).toEqual([])
      expect(layout.edges).toEqual([])
      expect(layout.width).toBeGreaterThan(0)
      expect(layout.height).toBeGreaterThan(0)
    })
  })
})
