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

  it('點選清空按鈕觸發 clear 事件', async () => {
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

    const clearBtn = wrapper.findAll('.terminal-btn').find((b) => b.text().includes('清空'))
    expect(clearBtn).toBeDefined()
    await clearBtn?.trigger('click')
    expect(wrapper.emitted('clear')).toBeTruthy()
  })
})
