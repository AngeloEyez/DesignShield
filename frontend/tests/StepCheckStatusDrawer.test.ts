/**
 * @file StepCheckStatusDrawer.test.ts
 * @description StepCheckStatusDrawer 元件單元測試，驗證 Step 4/5 執行中進度儀表板與完成後隱藏機制
 */

import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import PrimeVue from 'primevue/config'
import StepCheckStatusDrawer from '@/components/taskmonitorview/StepCheckStatusDrawer.vue'
import type { StepItem } from '@/types/task'

describe('StepCheckStatusDrawer.vue', () => {
  it('在 PROCESSING 狀態下正確顯示進度儀表板、PrimeVue ProgressBar、項目計數與目前確認中規則', () => {
    const mockStep: StepItem = {
      step_name: 'HEURISTIC_CHECK',
      status: 'PROCESSING',
      log_message: '[Config 1][3/12] 正在比對傳統演算法規則「I2C 7-bit 地址唯一性檢驗」...',
      started_at: new Date().toISOString(),
    }

    const wrapper = mount(StepCheckStatusDrawer, {
      global: {
        plugins: [PrimeVue],
      },
      props: {
        stepName: 'HEURISTIC_CHECK',
        stepItem: mockStep,
      },
    })

    // 驗證進度儀表板存在
    const dashboard = wrapper.find('.step-progress-dashboard')
    expect(dashboard.exists()).toBe(true)

    // 驗證標題與計數文字
    expect(dashboard.text()).toContain('傳統演算法比對進度')
    expect(dashboard.text()).toContain('第 3 / 12 項 (25%)')

    // 驗證當前確認中規則
    expect(dashboard.find('.current-rule-title').text()).toBe('I2C 7-bit 地址唯一性檢驗')

    // 驗證 PrimeVue ProgressBar 存在
    expect(wrapper.findComponent({ name: 'ProgressBar' }).exists()).toBe(true)
  })

  it('在 LLM_REASONING 步驟 PROCESSING 狀態下正確顯示大模型推理進度與規則名稱', () => {
    const mockStep: StepItem = {
      step_name: 'LLM_REASONING',
      status: 'PROCESSING',
      log_message: '[Config 1][2/5] 正在呼叫本地 LLM 進行「MicroSD 介面工作模式合理性確認」語意推理...',
      started_at: new Date().toISOString(),
    }

    const wrapper = mount(StepCheckStatusDrawer, {
      global: {
        plugins: [PrimeVue],
      },
      props: {
        stepName: 'LLM_REASONING',
        stepItem: mockStep,
      },
    })

    const dashboard = wrapper.find('.step-progress-dashboard')
    expect(dashboard.exists()).toBe(true)
    expect(dashboard.text()).toContain('LLM 語意推理進度')
    expect(dashboard.text()).toContain('第 2 / 5 項 (40%)')
    expect(dashboard.find('.current-rule-title').text()).toBe('MicroSD 介面工作模式合理性確認')
  })

  it('在 COMPLETED 狀態下自動隱藏進度儀表板區塊，僅顯示該步驟結果詳情與狀態標籤', () => {
    const mockStep: StepItem = {
      step_name: 'HEURISTIC_CHECK',
      status: 'COMPLETED',
      log_message: '傳統演算法規則比對完成，產出 12 項比對結果 (1 組 Config)',
      started_at: '2026-10-05T12:00:00Z',
      completed_at: '2026-10-05T12:00:05Z',
    }

    const wrapper = mount(StepCheckStatusDrawer, {
      global: {
        plugins: [PrimeVue],
      },
      props: {
        stepName: 'HEURISTIC_CHECK',
        stepItem: mockStep,
      },
    })

    // 驗證進度儀表板已隱藏
    expect(wrapper.find('.step-progress-dashboard').exists()).toBe(false)

    // 驗證保留步驟說明與狀態摘要卡片
    expect(wrapper.find('.heuristic-box').exists()).toBe(true)
    expect(wrapper.find('.status-summary-card').exists()).toBe(true)
    expect(wrapper.text()).toContain('傳統圖論演算法檢查包含')
    expect(wrapper.text()).toContain('傳統演算法規則比對完成，產出 12 項比對結果')
  })

  it('在 PENDING 狀態下隱藏進度區塊，展示等待比對狀態', () => {
    const mockStep: StepItem = {
      step_name: 'HEURISTIC_CHECK',
      status: 'PENDING',
    }

    const wrapper = mount(StepCheckStatusDrawer, {
      global: {
        plugins: [PrimeVue],
      },
      props: {
        stepName: 'HEURISTIC_CHECK',
        stepItem: mockStep,
      },
    })

    expect(wrapper.find('.step-progress-dashboard').exists()).toBe(false)
    expect(wrapper.text()).toContain('等待演算法規則比對...')
  })
})
