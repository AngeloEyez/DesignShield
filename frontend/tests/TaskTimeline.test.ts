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

    // 驗證卡片已移除文字狀態標籤，計時器與標題同一行
    expect(wrapper.find('.step-status-tag').exists()).toBe(false)
    const firstCardTitleRow = wrapper.find('.step-title-row')
    expect(firstCardTitleRow.find('.step-title').text()).toBe('1. 解壓縮與檔案格式預檢')
    expect(firstCardTitleRow.find('.step-timer-text').text()).toBe('0.35s')
  })

  it('頂部標題列移除工作狀態標籤，僅保留標題與任務總耗時計時器在同一列', () => {
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

    // 僅保留標題與計時器在同一列，無狀態標籤
    expect(header.find('.section-title').text()).toBe('工作流執行歷程')
    expect(header.find('.overall-status-tag').exists()).toBe(false)
    expect(header.find('.step-timer-text').text()).toContain('10.0s')
  })

  it('支援從 log_message 動態解析規則執行進度並正確展示進度條與標籤', () => {
    const mockSteps: StepItem[] = [
      {
        step_name: 'LLM_REASONING',
        status: 'PROCESSING',
        log_message: '[1/3] 正在呼叫本地 LLM 進行「MicroSD 介面工作模式合理性確認」語意推理...',
        started_at: new Date(Date.now() - 5000).toISOString(),
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
    expect(text).toContain('進行中: 第 1/3 項 (33%)')
    const fill = wrapper.find('.progress-bar-fill')
    expect(fill.exists()).toBe(true)
    expect(fill.attributes('style')).toContain('width: 33%')
  })

  it('歷史舊任務步驟若完全無時間記錄時展示佔位符「—」', () => {
    const mockSteps: StepItem[] = [
      {
        step_name: 'UNPACK_AND_VALIDATE',
        status: 'COMPLETED',
        log_message: '舊任務解壓完成',
      },
    ]

    const wrapper = mount(TaskTimeline, {
      global: { plugins: [PrimeVue] },
      props: {
        steps: mockSteps,
        overallStatus: 'COMPLETED',
      },
    })

    const text = wrapper.text()
    expect(text).toContain('—')
  })

  it('點擊未執行的 PENDING 步驟與已完成/進行中步驟皆正常觸發 select-step，以利開啟對應步驟之空狀態或詳情視窗', async () => {
    const mockSteps: StepItem[] = [
      {
        step_name: 'UNPACK_AND_VALIDATE',
        status: 'COMPLETED',
        log_message: '完成',
      },
      {
        step_name: 'PARSE_AND_GRAPH',
        status: 'PENDING',
        log_message: '等待中',
      },
    ]

    const wrapper = mount(TaskTimeline, {
      global: { plugins: [PrimeVue] },
      props: {
        steps: mockSteps,
        overallStatus: 'PROCESSING',
      },
    })

    const stepCards = wrapper.findAll('.step-item-card')
    expect(stepCards.length).toBe(2)

    // 點擊 COMPLETED 步驟
    await stepCards[0].trigger('click')
    expect(wrapper.emitted('select-step')).toBeTruthy()
    expect(wrapper.emitted('select-step')?.[0]).toEqual(['UNPACK_AND_VALIDATE'])

    // 點擊 PENDING 步驟
    await stepCards[1].trigger('click')
    expect(wrapper.emitted('select-step')?.[1]).toEqual(['PARSE_AND_GRAPH'])
  })
})
