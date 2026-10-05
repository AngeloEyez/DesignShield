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

    const button = wrapper.find('button')
    expect(button.attributes('disabled')).toBeDefined()
  })
})
