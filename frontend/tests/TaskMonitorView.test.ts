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
    vi.mocked(api.fetchTaskStatus).mockResolvedValue({
      task_id: 'test-123',
      project_name: '測試專案',
      status: 'PROCESSING',
      pre_analysis_summary: {
        component_count: 10,
        net_count: 20,
        buses: ['I2C'],
        platforms: ['STM32'],
      },
      steps: [],
    })
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

  it('Step 2 抽屜展示元件表格，支援關鍵字搜尋、類別篩選與電氣性篩選', async () => {
    vi.mocked(api.fetchTaskGraphDetails).mockResolvedValue({
      task_id: 'task-step2-test',
      components_count: 3,
      nets_count: 3,
      pins_count: 102,
      buses: ['I2C'],
      components: [
        {
          ref_des: 'TU10',
          category: 'IC',
          sub_category: 'MCU',
          functional_role: 'Bus_Master',
          is_electrical: true,
          part_value: 'STM32F407',
          package: 'LQFP100',
          description: 'ARM Cortex-M4 MCU',
          pins_count: 100,
          connected_nets: ['I2C1_SCL', '+3.3V', 'GND'],
        },
        {
          ref_des: 'NUT1',
          category: 'NonElectrical',
          sub_category: 'Mechanical',
          functional_role: 'None',
          is_electrical: false,
          part_value: 'M3_NUT',
          package: 'NUT-M3',
          description: 'Screw nut',
          pins_count: 0,
          connected_nets: [],
        },
        {
          ref_des: 'PR101',
          category: 'Passive',
          sub_category: 'Resistor',
          functional_role: 'None',
          is_electrical: true,
          part_value: '10K',
          package: '0402',
          description: 'Pullup resistor',
          pins_count: 2,
          connected_nets: ['I2C1_SCL', '+3.3V'],
        },
      ],
      nets: [
        {
          net_name: 'I2C1_SCL',
          bus_type: 'I2C',
          is_power: false,
          is_ground: false,
          connected_components: ['TU10', 'PR101'],
        },
      ],
      main_ics: ['TU10'],
      sub_ics: [],
    })

    const wrapper = mount(TaskMonitorView, {
      global: { plugins: [PrimeVue] },
    })

    const vm = wrapper.vm as any
    vm.currentTaskId = 'task-step2-test'
    vm.activeDrawerStep = 'PARSE_AND_GRAPH'
    await vm.loadExistingTask('task-step2-test')
    await wrapper.vm.$nextTick()

    // 抽屜呈現
    expect(wrapper.find('.step-overlay-drawer').exists()).toBe(true)
    const text = wrapper.text()
    expect(text).toContain('元件清單 (Components)')
    expect(text).toContain('網路清單 (Nets)')
    expect(text).toContain('TU10')
    expect(text).toContain('NUT1')
    expect(text).toContain('PR101')
    expect(text).toContain('STM32F407')
    expect(text).toContain('LQFP100')
    expect(text).toContain('電氣件')
    expect(text).toContain('非電氣')

    // 測試搜尋篩選
    vm.compSearch = 'STM32'
    await wrapper.vm.$nextTick()
    let tbodyText = wrapper.find('.table-container tbody').text()
    expect(tbodyText).toContain('TU10')
    expect(tbodyText).not.toContain('NUT1')
    expect(tbodyText).not.toContain('PR101')

    // 清除搜尋
    vm.compSearch = ''
    await wrapper.vm.$nextTick()

    // 測試電氣性篩選 (僅非電氣件)
    vm.compElectricalFilter = 'non_electrical'
    await wrapper.vm.$nextTick()
    tbodyText = wrapper.find('.table-container tbody').text()
    expect(tbodyText).toContain('NUT1')
    expect(tbodyText).not.toContain('TU10')
    expect(tbodyText).not.toContain('PR101')
  })

  it('Step 2 抽屜切換至網路清單 (Nets) 子頁籤，呈現網路屬性與連接元件', async () => {
    vi.mocked(api.fetchTaskGraphDetails).mockResolvedValue({
      task_id: 'task-step2-nets-test',
      components_count: 2,
      nets_count: 2,
      pins_count: 4,
      buses: ['I2C'],
      components: [],
      nets: [
        {
          net_name: 'I2C1_SCL',
          bus_type: 'I2C',
          is_power: false,
          is_ground: false,
          connected_components: ['TU10', 'PR101'],
        },
        {
          net_name: '+3.3V',
          bus_type: undefined,
          is_power: true,
          is_ground: false,
          connected_components: ['TU10', 'PR101'],
        },
      ],
      main_ics: [],
      sub_ics: [],
    })

    const wrapper = mount(TaskMonitorView, {
      global: { plugins: [PrimeVue] },
    })

    const vm = wrapper.vm as any
    vm.currentTaskId = 'task-step2-nets-test'
    vm.activeDrawerStep = 'PARSE_AND_GRAPH'
    await vm.loadExistingTask('task-step2-nets-test')
    await wrapper.vm.$nextTick()

    // 切換至 Nets 子頁籤
    const netTabBtn = wrapper.findAll('.subtab-btn').find((b) => b.text().includes('網路清單'))
    expect(netTabBtn).toBeDefined()
    await netTabBtn?.trigger('click')
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain('I2C1_SCL')
    expect(wrapper.text()).toContain('+3.3V')
    expect(wrapper.text()).toContain('電源')
    expect(wrapper.text()).toContain('I2C')

    // 搜尋網路
    vm.netSearch = 'SCL'
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('I2C1_SCL')
    expect(wrapper.text()).not.toContain('+3.3V')
  })
})

