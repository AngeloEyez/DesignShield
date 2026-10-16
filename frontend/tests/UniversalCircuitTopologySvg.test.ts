/**
 * @file UniversalCircuitTopologySvg.test.ts
 * @description UniversalCircuitTopologySvg 元件單元測試
 */

import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import PrimeVue from 'primevue/config'
import UniversalCircuitTopologySvg from '@/components/UniversalCircuitTopologySvg.vue'

describe('UniversalCircuitTopologySvg.vue', () => {
  const mockEvidence = {
    topology: {
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
            { pin_number: '1', orientation: 'left' },
            { pin_number: '2', orientation: 'right' },
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
      ],
      connections: [
        {
          net_name: 'USB8_USB20_P',
          rail_id: 'p_rail',
          from_node: 'TJ1',
          from_pin: 'A6',
          to_node: 'TL1',
          to_pin: '1',
        },
        {
          net_name: 'USB8_USB20_CMC_P',
          rail_id: 'p_rail',
          from_node: 'TL1',
          from_pin: '2',
          to_node: 'TU2',
          to_pin: '7',
        },
      ],
    },
  }

  it('依精簡規範直接展示 SVG 拓撲繪圖，不包含額外文字與外框', () => {
    const wrapper = mount(UniversalCircuitTopologySvg, {
      global: { plugins: [PrimeVue] },
      props: {
        evidence: mockEvidence,
      },
    })

    const text = wrapper.text()
    // 精簡規範：移除頂部標題、說明與圖例
    expect(text).not.toContain('差分通道端到端鏈路拓撲')
    expect(text).not.toContain('P+ 正極軌道')
    expect(text).not.toContain('N- 負極軌道')

    // 直接渲染 SVG 畫布
    expect(wrapper.find('svg').exists()).toBe(true)

    // 驗證包含核心拓撲群組
    expect(wrapper.find('.topology-edges').exists()).toBe(true)
    expect(wrapper.find('.topology-nodes').exists()).toBe(true)
    expect(wrapper.find('.topology-net-labels').exists()).toBe(true)

    // 驗證節點 RefDes 成功渲染
    expect(wrapper.text()).toContain('TJ1')
    expect(wrapper.text()).toContain('TL1')
    expect(wrapper.text()).toContain('TU2')
  })

  it('支援單端上拉與電氣符號渲染', () => {
    const pullupEvidence = {
      topology: {
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
        ],
        connections: [
          {
            net_name: 'I2C_SCL',
            rail_id: 'main',
            from_node: 'U1',
            from_pin: '10',
            to_node: 'R1',
            to_pin: '1',
            is_branch: true,
          },
        ],
      },
    }

    const wrapper = mount(UniversalCircuitTopologySvg, {
      global: { plugins: [PrimeVue] },
      props: {
        evidence: pullupEvidence,
      },
    })

    expect(wrapper.find('.topology-symbols').exists()).toBe(true)
    expect(wrapper.text()).toContain('+3.3V')
    expect(wrapper.text()).toContain('4.7kΩ')
  })

  it('未上件節點 (is_mounted: false) 渲染為透明度 30%、虛線外框並標註 [X]', () => {
    const unmountedEvidence = {
      topology: {
        title: 'USB 差分通道 (含未上件端點)',
        channel_type: 'differential',
        rails: [{ id: 'p_rail', name: '正極軌道', polarity: 'P' }],
        nodes: [
          {
            id: 'TJ1',
            ref_des: 'TJ1',
            category: 'Connector',
            role: 'terminal',
            is_mounted: true,
            pins: [{ pin_number: 'A6', pin_name: 'DP' }],
          },
          {
            id: 'TU2',
            ref_des: 'TU2',
            category: 'IC',
            role: 'terminal',
            is_mounted: false,
            pins: [{ pin_number: '7', pin_name: 'DM' }],
          },
        ],
        connections: [
          {
            net_name: 'USB_DP',
            rail_id: 'p_rail',
            from_node: 'TJ1',
            from_pin: 'A6',
            to_node: 'TU2',
            to_pin: '7',
          },
        ],
      },
    }

    const wrapper = mount(UniversalCircuitTopologySvg, {
      global: { plugins: [PrimeVue] },
      props: {
        evidence: unmountedEvidence,
      },
    })

    const nodeGroups = wrapper.findAll('.topology-node-group')
    expect(nodeGroups.length).toBe(2)

    // 已上件節點 TJ1: 無 opacity-65，無虛線，無 [X]
    const tj1Group = nodeGroups.find((g) => g.text().includes('TJ1'))
    expect(tj1Group?.classes()).not.toContain('opacity-65')
    expect(tj1Group?.find('rect').attributes('stroke-dasharray')).toBeUndefined()
    expect(tj1Group?.find('.unmounted-x-tag').exists()).toBe(false)

    // 未上件節點 TU2: 具有 opacity-65，虛線邊框 3,3，且顯示 [X]
    const tu2Group = nodeGroups.find((g) => g.text().includes('TU2'))
    expect(tu2Group).toBeDefined()
    expect(tu2Group?.classes()).toContain('opacity-65')
    expect(tu2Group?.find('rect').attributes('stroke-dasharray')).toBe('3,3')
    expect(tu2Group?.find('.unmounted-x-tag').exists()).toBe(true)
    expect(tu2Group?.text()).toContain('[X]')
  })
})

