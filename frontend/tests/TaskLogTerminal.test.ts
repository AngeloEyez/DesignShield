/**
 * @file TaskLogTerminal.test.ts
 * @description TaskLogTerminal 元件單元測試
 */

import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import TaskLogTerminal from '@/components/TaskLogTerminal.vue'
import type { LogEntry } from '@/types/task'

describe('TaskLogTerminal.vue', () => {
  it('正確渲染日誌項目與資訊', () => {
    const mockLogs: LogEntry[] = [
      {
        id: 'log-1',
        timestamp: '12:00:01',
        step_name: 'PARSE_AND_GRAPH',
        status: 'PROCESSING',
        message: '開始解析圖譜',
      },
      {
        id: 'log-2',
        timestamp: '12:00:02',
        step_name: 'PARSE_AND_GRAPH',
        status: 'COMPLETED',
        message: '圖譜構建完成',
      },
    ]

    const wrapper = mount(TaskLogTerminal, {
      props: {
        logs: mockLogs,
      },
    })

    const text = wrapper.text()
    expect(text).toContain('PARSE_AND_GRAPH')
    expect(text).toContain('開始解析圖譜')
    expect(text).toContain('圖譜構建完成')
    expect(text).toContain('2 則日誌')
  })

  it('空日誌時顯示提示文字', () => {
    const wrapper = mount(TaskLogTerminal, {
      props: {
        logs: [],
      },
    })

    expect(wrapper.text()).toContain('等待 SSE 即時日誌連線中...')
  })

  it('已移除清空按鈕且支援 hideToolbar 隱藏工具列', () => {
    const wrapper = mount(TaskLogTerminal, {
      props: {
        logs: [
          {
            id: 'log-1',
            timestamp: '12:00:01',
            step_name: 'TEST',
            status: 'PROCESSING',
            message: '測試',
          },
        ],
      },
    })

    // 驗證已移除清空按鈕
    const clearBtn = wrapper.findAll('.terminal-btn').find((b) => b.text().includes('清空'))
    expect(clearBtn).toBeUndefined()

    // 驗證 hideToolbar 時不渲染內置 LogToolbar
    const hideWrapper = mount(TaskLogTerminal, {
      props: {
        logs: [],
        hideToolbar: true,
      },
    })
    expect(hideWrapper.findComponent({ name: 'LogToolbar' }).exists()).toBe(false)
  })

  it('預設隱藏 DEBUG 等級日誌，切換 Debug 開關後顯示', async () => {
    const mockLogs: LogEntry[] = [
      {
        id: 'log-info',
        timestamp: '12:00:01',
        display_time: '10-06 12:00:01',
        step_name: 'PARSE_AND_GRAPH',
        category: 'PARSER',
        level: 'INFO',
        message: '一般進度訊息',
      },
      {
        id: 'log-debug',
        timestamp: '12:00:02',
        display_time: '10-06 12:00:02',
        step_name: 'PARSE_AND_GRAPH',
        category: 'LLM',
        level: 'DEBUG',
        message: 'LLM 詳細查詢除錯訊息',
      },
    ]

    const wrapper = mount(TaskLogTerminal, {
      props: {
        logs: mockLogs,
      },
    })

    // 預設 showDebug 為 false，應只看見 INFO，看不到 DEBUG
    expect(wrapper.text()).toContain('一般進度訊息')
    expect(wrapper.text()).not.toContain('LLM 詳細查詢除錯訊息')

    // 切換 Debug 開關
    const debugBtn = wrapper.find('.debug-toggle-btn')
    expect(debugBtn.exists()).toBe(true)
    await debugBtn.trigger('click')

    // 切換後應看見 DEBUG 訊息
    expect(wrapper.text()).toContain('一般進度訊息')
    expect(wrapper.text()).toContain('LLM 詳細查詢除錯訊息')
  })

  it('正確渲染時間戳記與雙標籤（工作流步驟與用途分類）', () => {
    const mockLogs: LogEntry[] = [
      {
        id: 'log-tags',
        timestamp: '2026-10-06T12:00:00Z',
        display_time: '10-06 12:00:00',
        step_name: 'RULE_SELECTION',
        category: 'LLM',
        level: 'INFO',
        message: '推薦規則完成',
      },
    ]

    const wrapper = mount(TaskLogTerminal, {
      props: {
        logs: mockLogs,
      },
    })

    const text = wrapper.text()
    expect(text).toContain('[10-06 12:00:00]')
    expect(text).toContain('[RULE_SELECTION]')
    expect(text).toContain('[LLM]')
    expect(text).toContain('INFO')
    expect(text).toContain('推薦規則完成')
  })

  it('含有結構化 details 時支援展開檢視提示詞與回應', async () => {
    const mockLogs: LogEntry[] = [
      {
        id: 'log-llm-query',
        timestamp: '12:00:05',
        step_name: 'PARSE_AND_GRAPH',
        category: 'LLM',
        level: 'INFO',
        message: '發起組件分類查詢',
        details: {
          prompt: '請判斷以下元件類別: C1 10uF 0805',
          response: { category: 'Capacitor', confidence: 0.98 },
        },
      },
    ]

    const wrapper = mount(TaskLogTerminal, {
      props: {
        logs: mockLogs,
      },
    })

    // 初始狀態尚未展開
    expect(wrapper.find('.details-box').exists()).toBe(false)

    // 點擊詳情按鈕
    const toggleBtn = wrapper.find('.details-toggle-btn')
    expect(toggleBtn.exists()).toBe(true)
    await toggleBtn.trigger('click')

    // 展開後應包含 details 區塊與 prompt/response
    expect(wrapper.find('.details-box').exists()).toBe(true)
    expect(wrapper.text()).toContain('請判斷以下元件類別: C1 10uF 0805')
    expect(wrapper.text()).toContain('Capacitor')
  })

  it('暴露 scrollToBottom 方法並正確設定 scrollTop 為 scrollHeight', async () => {
    const mockLogs: LogEntry[] = [
      { id: '1', timestamp: '12:00:01', step_name: 'TEST', message: '訊息 1' },
      { id: '2', timestamp: '12:00:02', step_name: 'TEST', message: '訊息 2' },
    ]

    const wrapper = mount(TaskLogTerminal, {
      props: { logs: mockLogs },
    })

    const vm = wrapper.vm as any
    expect(typeof vm.scrollToBottom).toBe('function')

    const terminalEl = wrapper.find('.terminal-body').element as HTMLElement
    Object.defineProperty(terminalEl, 'scrollHeight', { value: 600, configurable: true, writable: true })
    Object.defineProperty(terminalEl, 'clientHeight', { value: 200, configurable: true, writable: true })
    terminalEl.scrollTop = 0

    vm.scrollToBottom()
    await wrapper.vm.$nextTick()
    await wrapper.vm.$nextTick()

    expect(terminalEl.scrollTop).toBe(600)
  })

  it('使用者向上捲動離底超過 30px 時發出 update:autoScroll(false) 暫停自動捲動', async () => {
    const mockLogs: LogEntry[] = [
      { id: '1', timestamp: '12:00:01', step_name: 'TEST', message: '測試日誌' },
    ]

    const wrapper = mount(TaskLogTerminal, {
      props: { logs: mockLogs, autoScroll: true },
    })

    const terminalEl = wrapper.find('.terminal-body').element as HTMLElement
    Object.defineProperty(terminalEl, 'scrollHeight', { value: 1000, configurable: true })
    Object.defineProperty(terminalEl, 'clientHeight', { value: 300, configurable: true })

    // 使用者往上滑動到 scrollTop = 200 (距離底部 1000 - 200 - 300 = 500px > 30px)
    terminalEl.scrollTop = 200
    terminalEl.dispatchEvent(new Event('scroll'))
    await wrapper.vm.$nextTick()

    expect(wrapper.emitted('update:autoScroll')).toBeTruthy()
    expect(wrapper.emitted('update:autoScroll')?.[0]).toEqual([false])
  })

  it('使用者滾動回最底部時自動恢復 update:autoScroll(true)', async () => {
    const mockLogs: LogEntry[] = [
      { id: '1', timestamp: '12:00:01', step_name: 'TEST', message: '測試日誌' },
    ]

    const wrapper = mount(TaskLogTerminal, {
      props: { logs: mockLogs, autoScroll: false },
    })

    const terminalEl = wrapper.find('.terminal-body').element as HTMLElement
    Object.defineProperty(terminalEl, 'scrollHeight', { value: 1000, configurable: true })
    Object.defineProperty(terminalEl, 'clientHeight', { value: 300, configurable: true })

    // 使用者滾回最底部 (scrollTop = 700，距離底部 1000 - 700 - 300 = 0 <= 10px)
    terminalEl.scrollTop = 700
    terminalEl.dispatchEvent(new Event('scroll'))
    await wrapper.vm.$nextTick()

    expect(wrapper.emitted('update:autoScroll')).toBeTruthy()
    expect(wrapper.emitted('update:autoScroll')?.[0]).toEqual([true])
  })

  it('當 autoScroll 由 false 變更為 true 時立即觸發 scrollToBottom', async () => {
    const mockLogs: LogEntry[] = [
      { id: '1', timestamp: '12:00:01', step_name: 'TEST', message: '日誌項目' },
    ]

    const wrapper = mount(TaskLogTerminal, {
      props: { logs: mockLogs, autoScroll: false },
    })

    const terminalEl = wrapper.find('.terminal-body').element as HTMLElement
    Object.defineProperty(terminalEl, 'scrollHeight', { value: 800, configurable: true, writable: true })
    Object.defineProperty(terminalEl, 'clientHeight', { value: 200, configurable: true, writable: true })
    terminalEl.scrollTop = 50

    await wrapper.setProps({ autoScroll: true })
    await wrapper.vm.$nextTick()
    await wrapper.vm.$nextTick()

    expect(terminalEl.scrollTop).toBe(800)
  })
})

