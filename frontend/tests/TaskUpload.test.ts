/**
 * @file TaskUpload.test.ts
 * @description TaskUpload 元件單元測試
 */

import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import PrimeVue from 'primevue/config'
import TaskUpload from '@/components/TaskUpload.vue'

describe('TaskUpload.vue', () => {
  it('正確渲染專案名稱輸入框與上傳按鈕', () => {
    const wrapper = mount(TaskUpload, {
      global: {
        plugins: [PrimeVue],
      },
    })

    expect(wrapper.find('.text-input').exists()).toBe(true)
    expect(wrapper.text()).toContain('上傳線路圖檔')
    expect(wrapper.text()).toContain('專案名稱')
  })

  it('在未選擇檔案時，上傳按鈕應為禁用狀態', () => {
    const wrapper = mount(TaskUpload, {
      global: {
        plugins: [PrimeVue],
      },
    })

    const button = wrapper.find('.submit-upload-btn')
    expect(button.attributes('disabled')).toBeDefined()
  })

  it('支援裝配階段模式切換 (NPI/MP)，並在上傳時正確發出 payload', async () => {
    const wrapper = mount(TaskUpload, {
      global: {
        plugins: [PrimeVue],
      },
    })

    // 檢查預設包含 NPI 與 MP 選項
    expect(wrapper.text()).toContain('裝配階段模式')
    expect(wrapper.text()).toContain('NPI')
    expect(wrapper.text()).toContain('MP')

    // 模擬選定檔案
    const file = new File(['dummy xml content'], 'schematic.xml', { type: 'text/xml' })
    const fileInput = wrapper.find('input[type="file"]')
    Object.defineProperty(fileInput.element, 'files', {
      value: [file],
      writable: false,
    })
    await fileInput.trigger('change')

    // 提交上傳 (預設 NPI: isMpMode = false)
    const uploadBtn = wrapper.findAll('button').find((b) => b.text().includes('預先分析'))
    await uploadBtn?.trigger('click')

    const emitted = wrapper.emitted('upload')
    expect(emitted).toBeDefined()
    expect(emitted?.[0]?.[0]).toMatchObject({
      projectName: 'My_Carrier_Board',
      isMpMode: false,
    })
  })
})
