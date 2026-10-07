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
    expect(wrapper.text()).toContain('工作流執行歷程')
    expect(wrapper.text()).not.toContain('點擊步驟可於右側檢視詳細拓撲數據與分析進度')
  })

  it('支援時間依耗時精準格式化（<1s 兩位小數、<1m 一位小數、>1m 分秒格式）', () => {
    const mockSteps: StepItem[] = [
      {
        step_name: 'UNPACK_AND_VALIDATE',
        status: 'COMPLETED',
        started_at: '2026-10-05T12:00:00.000Z',
        completed_at: '2026-10-05T12:00:00.350Z', // 0.35s (< 1s)
      },
      {
        step_name: 'PARSE_AND_GRAPH',
        status: 'COMPLETED',
        started_at: '2026-10-05T12:00:00.000Z',
        completed_at: '2026-10-05T12:00:15.200Z', // 15.2s (< 1m)
      },
      {
        step_name: 'RULE_SELECTION',
        status: 'COMPLETED',
        started_at: '2026-10-05T12:00:00.000Z',
        completed_at: '2026-10-05T12:01:25.000Z', // 85s (> 1m -> 1m 25s)
      },
      {
        step_name: 'HEURISTIC_CHECK',
        status: 'PENDING',
      },
    ]

    const wrapper = mount(TaskTimeline, {
      global: { plugins: [PrimeVue] },
      props: {
        steps: mockSteps,
        overallStatus: 'PROCESSING',
      },
    })

    const text = wrapper.text()
    expect(text).toContain('0.35s')
    expect(text).toContain('15.2s')
    expect(text).toContain('1m 25s')
    expect(text).toContain('0.00s') // PENDING

    // 驗證標籤存在且等待中套用灰色標記
    const pendingTag = wrapper.find('.tag-pending')
    expect(pendingTag.exists()).toBe(true)
    expect(pendingTag.text()).toBe('等待中')
  })

  it('頂部標題列正確展示右側狀態標籤與任務總耗時計時器', () => {
    const mockSteps: StepItem[] = [
      {
        step_name: 'UNPACK_AND_VALIDATE',
        status: 'COMPLETED',
        started_at: '2026-10-05T12:00:00.000Z',
        completed_at: '2026-10-05T12:00:02.500Z',
      },
      {
        step_name: 'PARSE_AND_GRAPH',
        status: 'COMPLETED',
        started_at: '2026-10-05T12:00:02.500Z',
        completed_at: '2026-10-05T12:00:10.000Z',
      },
    ]

    const wrapper = mount(TaskTimeline, {
      global: { plugins: [PrimeVue] },
      props: {
        steps: mockSteps,
        overallStatus: 'COMPLETED',
      },
    })

    const header = wrapper.find('.timeline-header')
    expect(header.exists()).toBe(true)

    // 第 1 行：標題與狀態標籤
    const titleRow = header.find('.header-title-row')
    expect(titleRow.find('.section-title').text()).toBe('工作流執行歷程')
    expect(titleRow.find('.overall-status-tag').text()).toBe('任務已完成')

    // 第 2 行：任務總執行時間
    const timerRow = header.find('.header-timer-row')
    expect(timerRow.exists()).toBe(true)
    expect(timerRow.find('.step-timer-text').text()).toContain('10.0s')
  })
})
