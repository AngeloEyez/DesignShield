/**
 * @file TaskTimeline.test.ts
 * @description TaskTimeline 元件單元測試
 */

import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import PrimeVue from 'primevue/config'
import TaskTimeline from '@/components/TaskTimeline.vue'
import type { StepItem } from '@/types/task'

describe('TaskTimeline.vue', () => {
  it('正確渲染步驟名稱與狀態標籤', () => {
    const mockSteps: StepItem[] = [
      {
        step_name: 'UNPACK_AND_VALIDATE',
        status: 'COMPLETED',
        log_message: '解壓縮完成',
        started_at: '2026-10-05T12:00:00Z',
      },
      {
        step_name: 'PARSE_AND_GRAPH',
        status: 'PROCESSING',
        log_message: '構建圖譜中',
        started_at: '2026-10-05T12:00:05Z',
      },
    ]

    const wrapper = mount(TaskTimeline, {
      global: {
        plugins: [PrimeVue],
      },
      props: {
        steps: mockSteps,
        overallStatus: 'PROCESSING',
      },
    })

    const text = wrapper.text()
    expect(text).toContain('1. 解壓縮與檔案格式預檢')
    expect(text).toContain('2. 圖譜構建與線路解析')
    expect(text).toContain('解壓縮完成')
    expect(text).toContain('構建圖譜中')
  })

  it('支援空步驟時安全渲染', () => {
    const wrapper = mount(TaskTimeline, {
      global: {
        plugins: [PrimeVue],
      },
      props: {
        steps: [],
        overallStatus: 'PENDING',
      },
    })

    expect(wrapper.find('.task-timeline-container').exists()).toBe(true)
    expect(wrapper.text()).toContain('DBOS 工作流執行歷程')
  })
})
