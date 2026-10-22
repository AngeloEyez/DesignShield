/**
 * @file elkTopologyLayout.test.ts
 * @description ELKjs 現代化電路拓撲排版引擎 (漸進式 POC) 單元測試
 */

import { describe, it, expect } from 'vitest'
import {
  computeElkTopologyLayout,
  pointsToSmoothOrthogonalPath,
} from '@/utils/elkTopologyLayout'
import type { UniversalTopologyData, UniversalPin } from '@/utils/universalTopologyLayout'

describe('elkTopologyLayout', () => {
  describe('pointsToSmoothOrthogonalPath', () => {
    it('二點直線生成 (dy = 0)', () => {
      const path = pointsToSmoothOrthogonalPath([
        { x: 10, y: 50 },
        { x: 100, y: 50 },
      ])
      expect(path).toBe('M 10 50 L 100 50')
    })

    it('多折點平滑圓角生成 (帶 Q 二階貝茲曲線)', () => {
      const path = pointsToSmoothOrthogonalPath([
        { x: 10, y: 20 },
        { x: 60, y: 20 },
        { x: 60, y: 80 },
        { x: 120, y: 80 },
      ], 4)
      expect(path).toContain('M 10 20')
      expect(path).toContain('Q 60 20')
      expect(path).toContain('Q 60 80')
      expect(path).toContain('L 120 80')
    })
  })

  describe('computeElkTopologyLayout', () => {
    const mkPins = (list: [string, string?, UniversalPin['orientation']?][]): UniversalPin[] =>
      list.map(([pin_number, pin_name, orientation]) => ({ pin_number, pin_name, orientation }))
    const conn = (
      net_name: string,
      rail_id: string,
      from_node: string,
      from_pin: string,
      to_node: string,
      to_pin: string,
      is_branch = false
    ) => ({ net_name, rail_id, from_node, from_pin, to_node, to_pin, is_branch })

    it('差分對稱通道排版 (TJ1 ↔ TC13/TC14 ↔ TU1)，P 軌在上、N 軌在下', async () => {
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
            pins: mkPins([['B11', 'SSRXP1', 'right'], ['B10', 'SSRXN1', 'right']]),
          },
          {
            id: 'TU1',
            ref_des: 'TU1',
            category: 'IC',
            role: 'terminal',
            pins: mkPins([['N12', 'TX_P', 'left'], ['N13', 'TX_N', 'left']]),
          },
          {
            id: 'TC13',
            ref_des: 'TC13',
            category: 'Capacitor',
            role: 'series',
            value: '0.1µF',
            pins: mkPins([['2', undefined, 'left'], ['1', undefined, 'right']]),
          },
          {
            id: 'TC14',
            ref_des: 'TC14',
            category: 'Capacitor',
            role: 'series',
            value: '0.1µF',
            pins: mkPins([['2', undefined, 'left'], ['1', undefined, 'right']]),
          },
        ],
        connections: [
          conn('USB_SSRX_P', 'p_rail', 'TJ1', 'B11', 'TC13', '2'),
          conn('USB_SSRX_P_C', 'p_rail', 'TC13', '1', 'TU1', 'N12'),
          conn('USB_SSRX_N', 'n_rail', 'TJ1', 'B10', 'TC14', '2'),
          conn('USB_SSRX_N_C', 'n_rail', 'TC14', '1', 'TU1', 'N13'),
        ],
      }

      const layout = await computeElkTopologyLayout(diffData)
      expect(layout.nodes.length).toBe(4)
      expect(layout.edges.length).toBe(4)
      expect(layout.channelType).toBe('differential')

      // TJ1 在最左側，TC13/TC14 在中間，TU1 在右側
      const tj1 = layout.nodes.find((n) => n.id === 'TJ1')!
      const tu1 = layout.nodes.find((n) => n.id === 'TU1')!
      const tc13 = layout.nodes.find((n) => n.id === 'TC13')!
      const tc14 = layout.nodes.find((n) => n.id === 'TC14')!

      expect(tj1.x).toBeLessThan(tc13.x)
      expect(tc13.x).toBeLessThan(tu1.x)

      // 差分對稱性：TC13 (P 軌) 的 Y 座標應小於 TC14 (N 軌) 的 Y 座標
      expect(tc13.y).toBeLessThan(tc14.y)

      // 導線包含平滑 SVG path
      for (const e of layout.edges) {
        expect(e.pathD).toMatch(/^M \d+/)
      }
    })

    it('單端信號上拉 VCC 與接地 GND 符號生成 (U1 ↔ R1 ↔ C1 ↔ U2)', async () => {
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
            pins: mkPins([['10', 'SCL', 'right']]),
          },
          {
            id: 'U2',
            ref_des: 'U2',
            category: 'IC',
            role: 'terminal',
            pins: mkPins([['5', 'SCL', 'left']]),
          },
          {
            id: 'R1',
            ref_des: 'R1',
            category: 'Resistor',
            role: 'pull_up',
            value: '4.7kΩ',
            pins: mkPins([['1', undefined, 'bottom'], ['2', '+3.3V', 'top']]),
          },
          {
            id: 'C1',
            ref_des: 'C1',
            category: 'Capacitor',
            role: 'shunt_ground',
            value: '10pF',
            pins: mkPins([['1', undefined, 'top'], ['2', 'GND', 'bottom']]),
          },
        ],
        connections: [
          conn('I2C_SCL', 'main', 'U1', '10', 'U2', '5'),
          conn('I2C_SCL', 'main', 'U1', '10', 'R1', '1', true),
          conn('I2C_SCL', 'main', 'U1', '10', 'C1', '1', true),
        ],
      }

      const layout = await computeElkTopologyLayout(singleData)
      expect(layout.nodes.length).toBe(4)

      // 檢查 VCC 與 GND 電氣符號產生
      expect(layout.symbols.length).toBe(2)
      const vcc = layout.symbols.find((s) => s.type === 'vcc')
      const gnd = layout.symbols.find((s) => s.type === 'gnd')
      expect(vcc).toBeDefined()
      expect(gnd).toBeDefined()
      expect(vcc?.label).toBe('+3.3V')
      expect(gnd?.label).toBe('GND')

      // 檢查分支交會焊點產生
      expect(layout.junctionDots.length).toBeGreaterThanOrEqual(1)
    })

    it('並聯回流電路 (KU100 ↔ UL830 ∥ UR830/UR831 ↔ J83) 節點與導線排版正確', async () => {
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
            pins: mkPins([['51', '51', 'right'], ['52', '52', 'right']]),
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
            pins: mkPins([['2', undefined, 'left'], ['1', undefined, 'right']]),
          },
          {
            id: 'UR831',
            ref_des: 'UR831',
            category: 'Passive',
            role: 'series',
            value: '0_5%',
            is_mounted: false,
            pins: mkPins([['2', undefined, 'left'], ['1', undefined, 'right']]),
          },
          {
            id: 'J83',
            ref_des: 'J83',
            category: 'Connector',
            role: 'terminal',
            is_mounted: false,
            pins: mkPins([['3', 'D+', 'left'], ['2', 'D-', 'left']]),
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

      const layout = await computeElkTopologyLayout(topo)
      expect(layout.nodes.length).toBe(5)
      // 1-to-2 分流經純前端圖改寫器 (Dummy Junction) 收斂後，改寫為 Source->Junc 與 Junc->Targets，共 10 條邊段
      expect(layout.edges.length).toBe(10)
      expect(layout.junctionDots.length).toBe(2)

      const ku100 = layout.nodes.find((n) => n.id === 'KU100')!
      const j83 = layout.nodes.find((n) => n.id === 'J83')!
      expect(ku100.x).toBeLessThan(j83.x)
    })

    it('單腳測試點 (TP56/TP57) 就近緊湊垂直引出且 Net Name 浮於導線正上方', async () => {
      const topo: UniversalTopologyData = {
        title: 'U4 ↔ TP56/57 ↔ LR37/38 (差分驅動端與測點)',
        channel_type: 'differential',
        rails: [
          { id: 'p_rail', name: '正極軌道', polarity: 'P' },
          { id: 'n_rail', name: '負極軌道', polarity: 'N' },
        ],
        nodes: [
          {
            id: 'U4',
            ref_des: 'U4',
            category: 'IC',
            role: 'terminal',
            pins: mkPins([['1', 'TX_DP', 'right'], ['2', 'TX_DN', 'right']]),
          },
          {
            id: 'TP56',
            ref_des: 'TP56',
            category: 'Test_Point',
            role: 'terminal',
            is_test_point: true,
            lane: 'tap',
            pins: mkPins([['1', 'TP', 'top']]),
          },
          {
            id: 'TP57',
            ref_des: 'TP57',
            category: 'Test_Point',
            role: 'terminal',
            is_test_point: true,
            lane: 'tap',
            pins: mkPins([['1', 'TP', 'bottom']]),
          },
          {
            id: 'LR37',
            ref_des: 'LR37',
            category: 'Resistor',
            role: 'series',
            value: '0Ω',
            pins: mkPins([['1', undefined, 'left'], ['2', undefined, 'right']]),
          },
          {
            id: 'LR38',
            ref_des: 'LR38',
            category: 'Resistor',
            role: 'series',
            value: '0Ω',
            pins: mkPins([['1', undefined, 'left'], ['2', undefined, 'right']]),
          },
        ],
        connections: [
          // P 軌：U4.1 -> LR37.1 (主幹) 與 U4.1 -> TP56.1 (單腳測試點)
          conn('TX_DP_MAIN', 'p_rail', 'U4', '1', 'LR37', '1'),
          conn('TX_DP_MAIN', 'p_rail', 'U4', '1', 'TP56', '1', true),

          // N 軌：U4.2 -> LR38.1 (主幹) 與 U4.2 -> TP57.1 (單腳測試點)
          conn('TX_DN_MAIN', 'n_rail', 'U4', '2', 'LR38', '1'),
          conn('TX_DN_MAIN', 'n_rail', 'U4', '2', 'TP57', '1', true),
        ],
      }

      const layout = await computeElkTopologyLayout(topo)

      // 1. 元件節點數量正確 (Dummy Junction 不進入可見 layoutNodes)
      expect(layout.nodes.length).toBe(5)

      // 2. 自動在分流處生成電氣焊點 (Junction Dots)
      expect(layout.junctionDots.length).toBe(2)

      const u4 = layout.nodes.find((n) => n.id === 'U4')!
      const tp56 = layout.nodes.find((n) => n.id === 'TP56')!
      const tp57 = layout.nodes.find((n) => n.id === 'TP57')!
      const lr37 = layout.nodes.find((n) => n.id === 'LR37')!
      const lr38 = layout.nodes.find((n) => n.id === 'LR38')!

      // 3. Test Point 就近緊湊放置：TP 的 X 座標不會被推到 LR37/38 的後續獨立欄位
      expect(tp56.x).toBeGreaterThan(u4.x)
      expect(tp56.x).toBeLessThanOrEqual(lr37.x + lr37.width)
      expect(tp57.x).toBeGreaterThan(u4.x)
      expect(tp57.x).toBeLessThanOrEqual(lr38.x + lr38.width)

      // 4. 極性方向正確：正極 TP 在上方 (Y 較小)、負極 TP 在下方 (Y 較大)
      expect(tp56.y).toBeLessThan(lr37.y)
      expect(tp57.y).toBeGreaterThan(lr38.y)

      // 5. Net Name 文字標籤雙重保障：Y 座標精準浮於導線正上方 4px (不切線、不遮擋)
      expect(layout.netLabels.length).toBeGreaterThanOrEqual(1)
      for (const lbl of layout.netLabels) {
        expect(lbl.net).toBeTruthy()
        // 驗證標籤 Y 座標確實浮於其連接之主要導線水平段上方
        const relatedEdge = layout.edges.find((e) => e.netName === lbl.net && !e.isTestPointStub)
        if (relatedEdge) {
          // 導線之 Y 座標
          const edgeY = relatedEdge.start.y
          expect(lbl.y).toBeLessThan(edgeY)
        }
      }
    })

    it('雙節點直通差分通道排版 (XU1 ↔ P72)', async () => {
      const topo: UniversalTopologyData = {
        title: 'XU1 -> P72 (FLEX1_TCP_TX1)',
        channel_type: 'differential',
        rails: [
          { id: 'p_rail', name: 'P Rail', polarity: 'P' },
          { id: 'n_rail', name: 'N Rail', polarity: 'N' },
        ],
        nodes: [
          {
            id: 'XU1',
            ref_des: 'XU1',
            category: 'IC',
            role: 'terminal',
            pins: mkPins([['F33', 'FLEX1_TCP_TXRX1_P', 'right'], ['E33', 'FLEX1_TCP_TXRX1_N', 'right']]),
          },
          {
            id: 'P72',
            ref_des: 'P72',
            category: 'Connector',
            role: 'terminal',
            pins: mkPins([['27', '27', 'left'], ['25', '25', 'left']]),
          },
        ],
        connections: [
          conn('FLEX1_TCP_TXRX1_P', 'p_rail', 'XU1', 'F33', 'P72', '27'),
          conn('FLEX1_TCP_TXRX1_N', 'n_rail', 'XU1', 'E33', 'P72', '25'),
        ],
      }

      const layout = await computeElkTopologyLayout(topo)
      expect(layout.nodes.length).toBe(2)
      expect(layout.edges.length).toBe(2)

      const xu1 = layout.nodes.find((n) => n.id === 'XU1')!
      const p72 = layout.nodes.find((n) => n.id === 'P72')!
      const distance = p72.x - (xu1.x + xu1.width)

      // 1. 驗證節點間距緊湊合理，不發生重複累加而過長 (> 250px)
      expect(distance).toBeGreaterThanOrEqual(80)
      expect(distance).toBeLessThanOrEqual(160)

      // 2. 驗證左側 port 小方塊 100% 精確錨定在導線上 (0 像素錯位)
      const p72Pin27 = p72.ports.find((p) => p.pinNumber === '27')!
      const edge0 = layout.edges.find((e) => e.targetId === 'P72' && e.polarity === 'p')!

      expect(p72Pin27.relX).toBe(0) // 半嵌於元件左邊框上
      expect(p72Pin27.x).toBe(edge0.end.x) // X 座標精確吻合導線終點
      expect(p72Pin27.y).toBe(edge0.end.y) // Y 座標精確吻合導線終點
    })
  })
})
