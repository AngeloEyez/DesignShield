/**
 * @file TaskMonitorView.test.ts
 * @description TaskMonitorView 元件與 DRC 6 步驟工作流程整合測試
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import PrimeVue from 'primevue/config'
import TaskMonitorView from '@/views/TaskMonitorView.vue'
import * as api from '@/services/api'

// Mock 路由
const mockReplace = vi.fn()
vi.mock('vue-router', () => ({
  useRouter: () => ({
    replace: mockReplace,
    push: vi.fn(),
  }),
  useRoute: () => ({
    path: '/drc',
    query: {},
  }),
}))

// Mock API
vi.mock('@/services/api', () => ({
  uploadSchematic: vi.fn(),
  startTaskRun: vi.fn(),
  subscribeTaskEvents: vi.fn(() => ({ close: vi.fn() })),
  fetchTaskReport: vi.fn(),
  fetchRules: vi.fn(),
  fetchTaskStatus: vi.fn(),
  stopTask: vi.fn(),
  fetchTaskGraphDetails: vi.fn(),
  fetchTaskArchiveDetails: vi.fn(),
}))

describe('TaskMonitorView.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.fetchRules).mockResolvedValue([
      { id: 'RULE-01', name: '規則 A', category: 'Bus', check_type: 'HEURISTIC', is_active: true } as any,
    ])
    vi.mocked(api.fetchTaskGraphDetails).mockResolvedValue({
      task_id: 'test-123',
      components_count: 10,
      nets_count: 20,
      pins_count: 30,
      buses: ['I2C'],
      components: [],
      nets: [],
      main_ics: ['U1'],
      sub_ics: ['U2'],
    })
    vi.mocked(api.fetchTaskArchiveDetails).mockResolvedValue({
      task_id: 'test-123',
      file_count: 2,
      total_bytes: 1000,
      files: [],
    })
  })

  it('新任務初始狀態下呈現上傳區塊與 6 大步驟時間軸', () => {
    const wrapper = mount(TaskMonitorView, {
      global: { plugins: [PrimeVue] },
    })

    expect(wrapper.find('.upload-section-card').exists()).toBe(true)
    const text = wrapper.text()
    expect(text).toContain('1. 解壓縮與檔案格式預檢')
    expect(text).toContain('2. 圖譜構建與線路解析')
    expect(text).toContain('3. 規則推薦與選取')
    expect(text).toContain('4. 傳統演算法規則比對')
    expect(text).toContain('5. 本地大模型語意推理')
    expect(text).toContain('6. 報告彙整與資源落地')
  })

  it('完成上傳後上傳區塊隱藏，自動彈出 Step 3 規則選取抽屜', async () => {
    vi.mocked(api.uploadSchematic).mockResolvedValue({
      task_id: 'new-task-uuid-888',
      project_name: '測試線路專案',
      status: 'READY_FOR_RUN',
      pre_analysis_summary: {
        component_count: 12,
        net_count: 24,
        buses: ['I2C', 'SPI'],
        platforms: ['STM32'],
      },
      recommended_rules: [
        { id: 'RULE-01', name: '規則 A', category: 'Bus' },
      ],
    })

    const wrapper = mount(TaskMonitorView, {
      global: { plugins: [PrimeVue] },
    })

    // 觸發 TaskUpload 元件的 upload 事件
    const uploadComponent = wrapper.findComponent({ name: 'TaskUpload' })
    expect(uploadComponent.exists()).toBe(true)

    const dummyFile = new File(['dummy'], 'schematic.zip', { type: 'application/zip' })
    await uploadComponent.vm.$emit('upload', {
      file: dummyFile,
      projectName: '測試線路專案',
    })

    await new Promise((r) => setTimeout(r, 60))

    // 上傳卡片隱藏
    expect(wrapper.find('.upload-section-card').exists()).toBe(false)
    // 抽屜自動彈出
    expect(wrapper.find('.step-overlay-drawer').exists()).toBe(true)
    expect(wrapper.find('.mandatory-badge').exists()).toBe(true) // 強制選取提示
  })

  it('確認規則後抽屜收合並正式啟動檢測', async () => {
    vi.mocked(api.uploadSchematic).mockResolvedValue({
      task_id: 'new-task-uuid-888',
      project_name: '測試專案',
      status: 'READY_FOR_RUN',
      pre_analysis_summary: { component_count: 5, net_count: 10, buses: [], platforms: [] },
      recommended_rules: [],
    })
    vi.mocked(api.startTaskRun).mockResolvedValue({
      task_id: 'new-task-uuid-888',
      status: 'PROCESSING',
      message: '已啟動',
    })

    const wrapper = mount(TaskMonitorView, {
      global: { plugins: [PrimeVue] },
    })

    const uploadComponent = wrapper.findComponent({ name: 'TaskUpload' })
    await uploadComponent.vm.$emit('upload', {
      file: new File([''], 'test.zip'),
      projectName: '測試專案',
    })
    await new Promise((r) => setTimeout(r, 50))

    // 在抽屜中觸發 RuleTreeSelector 的 run 事件
    const selector = wrapper.findComponent({ name: 'RuleTreeSelector' })
    expect(selector.exists()).toBe(true)
    await selector.vm.$emit('run', ['RULE-01'])

    await new Promise((r) => setTimeout(r, 50))
    expect(api.startTaskRun).toHaveBeenCalledWith('new-task-uuid-888', ['RULE-01'])
    // 抽屜已收合
    expect(wrapper.find('.step-overlay-drawer').exists()).toBe(false)
  })

  it('點擊停止任務按鈕呼叫後端 stopTask API', async () => {
    vi.mocked(api.stopTask).mockResolvedValue({
      task_id: 'task-stopping',
      status: 'CANCELLED',
      message: '成功停止',
    })

    const wrapper = mount(TaskMonitorView, {
      global: { plugins: [PrimeVue] },
    })

    // 手動設定任務為 PROCESSING 狀態以展示停止按鈕
    const vm = wrapper.vm as any
    vm.currentTaskId = 'task-stopping'
    vm.taskStatus = 'PROCESSING'
    await wrapper.vm.$nextTick()

    const stopBtn = wrapper.findAll('button').find((b) => b.text().includes('停止任務'))
    expect(stopBtn).toBeDefined()
    await stopBtn?.trigger('click')

    expect(api.stopTask).toHaveBeenCalledWith('task-stopping')
  })
})
