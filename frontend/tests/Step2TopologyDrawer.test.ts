/**
 * @file Step2TopologyDrawer.test.ts
 * @description Step 2 拓撲線路圖與元件/網路清單表格單元測試
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import PrimeVue from 'primevue/config'
import Step2TopologyDrawer from '@/components/taskmonitorview/Step2TopologyDrawer.vue'
import type { TaskGraphDetails } from '@/types/task'

describe('Step2TopologyDrawer.vue', () => {
  const mockGraphDetails: TaskGraphDetails = {
    task_id: 'task-test-step2',
    components_count: 3,
    nets_count: 2,
    pins_count: 10,
    buses: ['I2C'],
    main_ics: ['U1'],
    sub_ics: [],
    key_ics: ['U1'],
    components: [
      {
        ref_des: 'U1',
        category: 'IC',
        sub_category: 'MCU',
        functional_role: 'Controller',
        is_electrical: true,
        part_value: 'STM32F407',
        package: 'LQFP100',
        pins_count: 100,
        connected_nets: ['NET_VCC', 'NET_I2C'],
        description: 'Main Controller',
      },
      {
        ref_des: 'NUT1',
        category: 'NonElectrical',
        sub_category: 'Mechanical',
        is_electrical: false,
        pins_count: 0,
        connected_nets: [],
        description: 'Mounting Nut',
      },
    ],
    nets: [
      {
        net_name: 'NET_VCC',
        bus_type: undefined,
        is_power: true,
        is_ground: false,
        connected_components: ['U1', 'R1', 'R2', 'R3', 'C1', 'C2', 'C3', 'C4', 'C5', 'C6', 'C7', 'C8', 'D1', 'D2', 'D3'],
      },
      {
        net_name: 'NET_GND',
        bus_type: undefined,
        is_power: false,
        is_ground: true,
        connected_components: ['U1', 'GND_PAD'],
      },
    ],
  }

  beforeEach(() => {
    vi.clearAllMocks()
    vi.useRealTimers()
  })

  it('表格標籤移除圖形符號 (無 ⚡, ⚪, ⏚, 🚌, 〰️)', () => {
    const wrapper = mount(Step2TopologyDrawer, {
      props: {
        graphDetails: mockGraphDetails,
        activeTab: 'components',
      },
      global: { plugins: [PrimeVue] },
    })

    const text = wrapper.text()
    expect(text).toContain('電氣件')
    expect(text).toContain('非電氣')
    expect(text).not.toContain('⚡ 電氣件')
    expect(text).not.toContain('⚪ 非電氣')
  })

  it('網路表格標籤移除圖形符號', async () => {
    const wrapper = mount(Step2TopologyDrawer, {
      props: {
        graphDetails: mockGraphDetails,
        activeTab: 'nets',
      },
      global: { plugins: [PrimeVue] },
    })

    const text = wrapper.text()
    expect(text).toContain('電源')
    expect(text).toContain('接地')
    expect(text).not.toContain('⚡ 電源')
    expect(text).not.toContain('⏚ 接地')
  })

  it('當滑鼠 overlay 在 +N more 標籤上時，彈出浮動小窗口並列出全部相連元件', async () => {
    const wrapper = mount(Step2TopologyDrawer, {
      props: {
        graphDetails: mockGraphDetails,
        activeTab: 'nets',
      },
      global: { plugins: [PrimeVue] },
      attachTo: document.body,
    })

    // 尋找 +9 more 標籤 (15 - 6 = 9)
    const moreTag = wrapper.find('.net-tag-more')
    expect(moreTag.exists()).toBe(true)
    expect(moreTag.text()).toContain('+9 more')

    // 觸發 mouseenter (overlay)
    await moreTag.trigger('mouseenter')
    await wrapper.vm.$nextTick()

    // 檢查浮動小窗口是否出現於 body
    const floatingWindow = document.querySelector('.net-components-floating-window')
    expect(floatingWindow).not.toBeNull()
    expect(floatingWindow?.textContent).toContain('NET_VCC')
    expect(floatingWindow?.textContent).toContain('全數 15 顆')

    // 檢查所有 15 顆元件是否皆列出在浮動小窗口中
    const allExpectedComps = ['U1', 'R1', 'R2', 'R3', 'C1', 'C2', 'C3', 'C4', 'C5', 'C6', 'C7', 'C8', 'D1', 'D2', 'D3']
    allExpectedComps.forEach((comp) => {
      expect(floatingWindow?.textContent).toContain(comp)
    })

    wrapper.unmount()
  })

  it('當滑鼠移開時，浮動小窗口自動隱藏', async () => {
    vi.useFakeTimers()
    const wrapper = mount(Step2TopologyDrawer, {
      props: {
        graphDetails: mockGraphDetails,
        activeTab: 'nets',
      },
      global: { plugins: [PrimeVue] },
      attachTo: document.body,
    })

    const moreTag = wrapper.find('.net-tag-more')
    await moreTag.trigger('mouseenter')
    await wrapper.vm.$nextTick()

    expect(document.querySelector('.net-components-floating-window')).not.toBeNull()

    // 觸發 mouseleave
    await moreTag.trigger('mouseleave')
    vi.advanceTimersByTime(350)
    await wrapper.vm.$nextTick()

    expect(document.querySelector('.net-components-floating-window')).toBeNull()

    wrapper.unmount()
    vi.useRealTimers()
  })

  it('在浮動小窗口內部捲動時不會觸發關閉，點擊關閉按鈕可立即關閉', async () => {
    const wrapper = mount(Step2TopologyDrawer, {
      props: {
        graphDetails: mockGraphDetails,
        activeTab: 'nets',
      },
      global: { plugins: [PrimeVue] },
      attachTo: document.body,
    })

    const moreTag = wrapper.find('.net-tag-more')
    await moreTag.trigger('mouseenter')
    await wrapper.vm.$nextTick()

    const popupBody = document.querySelector('.popup-body')
    expect(popupBody).not.toBeNull()

    // 模擬在 popup-body 內部滾動，小窗口依然存在
    popupBody?.dispatchEvent(new Event('scroll', { bubbles: false }))
    await wrapper.vm.$nextTick()
    expect(document.querySelector('.net-components-floating-window')).not.toBeNull()

    // 點擊關閉按鈕立即關閉
    const closeBtn = document.querySelector('.popup-close-btn') as HTMLElement
    expect(closeBtn).not.toBeNull()
    closeBtn.click()
    await wrapper.vm.$nextTick()
    expect(document.querySelector('.net-components-floating-window')).toBeNull()

    wrapper.unmount()
  })
})
