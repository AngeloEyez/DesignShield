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
  fetchPatternTree: vi.fn(),
  fetchTaskStatus: vi.fn(),
  fetchTaskLogs: vi.fn(),
  stopTask: vi.fn(),
  fetchTaskGraphDetails: vi.fn(),
  fetchTaskArchiveDetails: vi.fn(),
}))

describe('TaskMonitorView.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.fetchTaskLogs).mockResolvedValue({
      total: 0,
      task_id: 'test-123',
      logs: [],
    })
    vi.mocked(api.fetchPatternTree).mockResolvedValue({
      level1: [],
      level2: [],
      level3: [],
      partdb: { parts: [], schemas: {} },
      tags: [],
      summary: { level1_count: 0, level2_count: 0, level3_count: 0, partdb_parts_count: 0, tags_count: 0 },
    })
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

  it('確認規則後主工作台切換至 Step 4 演算法檢測並自動展開日誌終端', async () => {
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

    // 在主工作台 Step 3 中觸發 RuleTreeSelector 的 run 事件
    const selector = wrapper.findComponent({ name: 'RuleTreeSelector' })
    expect(selector.exists()).toBe(true)
    await selector.vm.$emit('run', ['RULE-01'])

    await new Promise((r) => setTimeout(r, 50))
    // 主工作台自動轉入 Step 4，Console 依新規範維持預設單行
    const vm = wrapper.vm as any
    expect(vm.activeDrawerStep).toBe('HEURISTIC_CHECK')
    expect(vm.isConsoleExpanded).toBe(false)
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

  it('非同步預先分析流程：上傳後立即顯示 Step 1 PROCESSING，收到 task_status 後彈出選取抽屜，點擊關閉按鈕關閉視窗以檢視底層 Log', async () => {
    let capturedOnTaskStatus: ((data: any) => void) | undefined
    vi.mocked(api.subscribeTaskEvents).mockImplementation((_id, _onStep, _onEnd, _onError, _onLog, onStatus) => {
      capturedOnTaskStatus = onStatus
      return { close: vi.fn() } as any
    })

    vi.mocked(api.uploadSchematic).mockResolvedValue({
      task_id: 'async-task-uuid-999',
      project_name: '非同步分析專案',
      status: 'PRE_ANALYZING',
      pre_analysis_summary: { component_count: 0, net_count: 0, buses: [], platforms: [] },
      recommended_rules: [],
    })

    const wrapper = mount(TaskMonitorView, {
      global: { plugins: [PrimeVue] },
    })

    const uploadComponent = wrapper.findComponent({ name: 'TaskUpload' })
    await uploadComponent.vm.$emit('upload', {
      file: new File([''], 'async.zip'),
      projectName: '非同步分析專案',
    })
    await new Promise((r) => setTimeout(r, 50))

    // 1. 上傳卡片隱藏，處於 PRE_ANALYZING 狀態
    expect(wrapper.find('.upload-section-card').exists()).toBe(false)
    const vm = wrapper.vm as any
    expect(vm.taskStatus).toBe('PRE_ANALYZING')
    // 預先分析進行中，抽屜尚未遮蔽日誌
    expect(wrapper.find('.step-overlay-drawer').exists()).toBe(false)

    // Step 1 處於 PROCESSING
    expect(vm.steps[0].status).toBe('PROCESSING')

    // 2. 模擬後端透過 SSE task_status 事件推播分析完成
    expect(capturedOnTaskStatus).toBeDefined()
    capturedOnTaskStatus!({
      task_id: 'async-task-uuid-999',
      status: 'READY_FOR_RUN',
      pre_analysis_summary: { component_count: 8, net_count: 16, buses: ['I2C'], platforms: ['STM32'] },
      recommended_rules: [{ id: 'RULE-ASYNC-1', name: '異步推薦規則', category: 'Bus' }],
    })
    await wrapper.vm.$nextTick()

    // 抽屜自動彈出
    expect(vm.taskStatus).toBe('READY_FOR_RUN')
    expect(vm.activeDrawerStep).toBe('RULE_SELECTION')
    expect(wrapper.find('.step-overlay-drawer').exists()).toBe(true)

    // 3. 測試右上角關閉按鈕 (.drawer-close-btn)
    const closeBtn = wrapper.find('.drawer-close-btn')
    expect(closeBtn.exists()).toBe(true)
    await closeBtn.trigger('click')
    await wrapper.vm.$nextTick()

    // 抽屜已直接關閉，activeDrawerStep 變為 null，底層 Log 完整可見
    expect(vm.activeDrawerStep).toBeNull()
    expect(wrapper.find('.step-overlay-drawer').exists()).toBe(false)
    expect(wrapper.find('.drawer-backdrop').exists()).toBe(false)
  })

  it('點擊 Timeline 卡片能直接切換右側 Detail 抽屜視窗，關閉後點擊卡片可再次開啟', async () => {
    vi.mocked(api.fetchTaskStatus).mockResolvedValue({
      task_id: 'task-timeline-click-test',
      project_name: '點擊測試專案',
      status: 'READY_FOR_RUN',
      pre_analysis_summary: {
        component_count: 10,
        net_count: 20,
        buses: ['I2C'],
        platforms: ['TI Power'],
      },
      recommended_rules: [
        { id: 'rule-1', name: '規則 1', category: 'I2C' },
      ],
      steps: [
        { step_name: 'UNPACK_AND_VALIDATE', status: 'COMPLETED', log_message: '解壓完成' },
        { step_name: 'PARSE_AND_GRAPH', status: 'COMPLETED', log_message: '圖譜構建完成' },
        { step_name: 'RULE_SELECTION', status: 'PROCESSING', log_message: '等待選取規則' },
        { step_name: 'HEURISTIC_CHECK', status: 'PENDING', log_message: '等待演算法' },
        { step_name: 'LLM_REASONING', status: 'PENDING', log_message: '等待 LLM' },
        { step_name: 'GENERATE_REPORT', status: 'PENDING', log_message: '等待報告' },
      ],
    })

    const wrapper = mount(TaskMonitorView, {
      global: { plugins: [PrimeVue] },
    })

    const vm = wrapper.vm as any
    await vm.loadExistingTask('task-timeline-click-test')
    await wrapper.vm.$nextTick()

    // 初始 READY_FOR_RUN 狀態：抽屜開啟在 RULE_SELECTION
    expect(vm.activeDrawerStep).toBe('RULE_SELECTION')
    expect(wrapper.find('.step-overlay-drawer').exists()).toBe(true)

    // 取得所有時間軸卡片
    const stepCards = wrapper.findAll('.step-item-card')
    expect(stepCards.length).toBe(6)

    // 1. 點擊 Step 1 卡片 (UNPACK_AND_VALIDATE) -> 直接切換
    await stepCards[0].trigger('click')
    await wrapper.vm.$nextTick()
    expect(vm.activeDrawerStep).toBe('UNPACK_AND_VALIDATE')
    expect(wrapper.findComponent({ name: 'Step1ArchiveDrawer' }).exists()).toBe(true)

    // 2. 點擊 Step 2 卡片 (PARSE_AND_GRAPH) -> 直接切換
    await stepCards[1].trigger('click')
    await wrapper.vm.$nextTick()
    expect(vm.activeDrawerStep).toBe('PARSE_AND_GRAPH')
    expect(wrapper.findComponent({ name: 'Step2TopologyDrawer' }).exists()).toBe(true)

    // 3. 點擊右上角關閉按鈕關閉視窗以檢視底層 Log
    const closeBtn = wrapper.find('.drawer-close-btn')
    expect(closeBtn.exists()).toBe(true)
    await closeBtn.trigger('click')
    await wrapper.vm.$nextTick()
    expect(vm.activeDrawerStep).toBeNull()
    expect(wrapper.find('.step-overlay-drawer').exists()).toBe(false)

    // 4. 點擊 Step 3 卡片 (RULE_SELECTION) -> 重新開啟抽屜
    await stepCards[2].trigger('click')
    await wrapper.vm.$nextTick()
    expect(vm.activeDrawerStep).toBe('RULE_SELECTION')
    expect(wrapper.findComponent({ name: 'RuleTreeSelector' }).exists()).toBe(true)

    // 5. 點擊待執行之 Step 4 卡片 (HEURISTIC_CHECK) -> 直接切換
    await stepCards[3].trigger('click')
    await wrapper.vm.$nextTick()
    expect(vm.activeDrawerStep).toBe('HEURISTIC_CHECK')
    expect(wrapper.findComponent({ name: 'StepCheckStatusDrawer' }).exists()).toBe(true)

    // 6. 點擊待執行之 Step 6 卡片 (GENERATE_REPORT) -> 直接切換
    await stepCards[5].trigger('click')
    await wrapper.vm.$nextTick()
    expect(vm.activeDrawerStep).toBe('GENERATE_REPORT')
    expect(wrapper.findComponent({ name: 'Step6ReportSummaryDrawer' }).exists()).toBe(true)
    expect(wrapper.find('.report-empty-state').exists()).toBe(true)

    // 7. 測試鍵盤 ESC 鍵關閉抽屜
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    await wrapper.vm.$nextTick()
    expect(vm.activeDrawerStep).toBeNull()
    expect(wrapper.find('.step-overlay-drawer').exists()).toBe(false)
  })

  it('底部全寬 Console 終端機面板支援三段式高度切換 (單擊 32/200px、雙擊 32/max、按鈕純圖標與時間戳)', async () => {
    const wrapper = mount(TaskMonitorView, {
      global: { plugins: [PrimeVue] },
    })
    const vm = wrapper.vm as any

    // 初始狀態為收合 (collapsed / 32px)
    expect(vm.consoleHeightMode).toBe('collapsed')
    expect(vm.isConsoleExpanded).toBe(false)
    const statusBar = wrapper.find('.console-status-bar')
    expect(statusBar.exists()).toBe(true)

    // 驗證按鈕群已移除冗贅文字，僅保留圖標
    const debugBtn = wrapper.find('.debug-toggle-btn')
    expect(debugBtn.text()).not.toContain('Debug 模式')
    expect(debugBtn.find('i.pi-code').exists()).toBe(true)

    const scrollBtn = wrapper.find('.autoscroll-toggle-btn')
    expect(scrollBtn.text()).not.toContain('自動捲動')
    expect(scrollBtn.find('i.pi-arrow-down').exists()).toBe(true)

    // 驗證標題列已移除「即時日誌」標題
    expect(statusBar.text()).not.toContain('即時日誌')

    // 驗證日誌計數標籤存在於右側按鈕區左側
    const rightArea = wrapper.find('.console-status-right')
    const countBadge = rightArea.find('.log-count-badge')
    expect(countBadge.exists()).toBe(true)

    // 模擬注入一筆日誌並確認單行模式下呈現時間戳
    vm.logs = [
      {
        id: 'test-log-1',
        display_time: '17:15:30',
        timestamp: '2026-10-12T17:15:30Z',
        step_name: 'UNPACK_AND_VALIDATE',
        level: 'INFO',
        message: '上傳檔案解壓縮成功',
      },
    ]
    await wrapper.vm.$nextTick()
    const timestampEl = wrapper.find('.log-timestamp')
    expect(timestampEl.exists()).toBe(true)
    expect(timestampEl.text()).toContain('17:15:30')

    // 1. 單擊狀態列 -> 經 250ms 防抖後展開為預設高度 (expanded / 200px)
    await statusBar.trigger('click')
    await new Promise((r) => setTimeout(r, 260))
    expect(vm.consoleHeightMode).toBe('expanded')
    expect(vm.isConsoleExpanded).toBe(true)
    const dock = wrapper.find('.bottom-console-dock')
    expect(dock.classes()).toContain('h-[200px]')

    // 2. 再次單擊狀態列 -> 經 250ms 防抖後收合為 32px (collapsed)
    await statusBar.trigger('click')
    await new Promise((r) => setTimeout(r, 260))
    expect(vm.consoleHeightMode).toBe('collapsed')
    expect(vm.isConsoleExpanded).toBe(false)
    expect(dock.classes()).toContain('h-8')

    // 3. 雙擊狀態列 -> 立即全屏最大化 (maximized)
    await statusBar.trigger('dblclick')
    expect(vm.consoleHeightMode).toBe('maximized')
    expect(dock.classes()).toContain('flex-1')
    expect(dock.classes()).toContain('h-full')
    expect(wrapper.find('.workspace-main-area').attributes('style')).toContain('display: none')

    // 4. 再次雙擊狀態列 -> 立即收合為 32px (collapsed)
    await statusBar.trigger('dblclick')
    expect(vm.consoleHeightMode).toBe('collapsed')
    expect(dock.classes()).toContain('h-8')

    // 5. 點擊最大化按鈕 -> 最大化與還原
    const maxBtn = wrapper.find('.console-maximize-btn')
    await maxBtn.trigger('click')
    expect(vm.consoleHeightMode).toBe('maximized')
    await maxBtn.trigger('click')
    expect(vm.consoleHeightMode).toBe('expanded')

    // 6. 點擊收合按鈕 -> 收合
    const toggleBtn = wrapper.find('.console-toggle-btn')
    await toggleBtn.trigger('click')
    expect(vm.consoleHeightMode).toBe('collapsed')
  })

  it('任務完成 (COMPLETED) 時主工作台自動切換至 Step 6 且嵌入 TaskReportDashboard', async () => {
    vi.mocked(api.fetchTaskStatus).mockResolvedValue({
      task_id: 'task-completed-test',
      project_name: '已完成專案',
      status: 'COMPLETED',
      pre_analysis_summary: { component_count: 5, net_count: 5, buses: [], platforms: [] },
      recommended_rules: [],
      steps: [
        { step_name: 'GENERATE_REPORT', status: 'COMPLETED', log_message: '報告產出完成' },
      ],
    })
    vi.mocked(api.fetchTaskReport).mockResolvedValue({
      task_id: 'task-completed-test',
      summary: { total_violations: 2, error_count: 1, warning_count: 1, info_count: 0 },
      violations: [],
    })

    const wrapper = mount(TaskMonitorView, {
      global: { plugins: [PrimeVue] },
    })
    const vm = wrapper.vm as any

    await vm.loadExistingTask('task-completed-test')
    await wrapper.vm.$nextTick()

    expect(vm.taskStatus).toBe('COMPLETED')
    expect(vm.activeDrawerStep).toBe('GENERATE_REPORT')
    // 主工作區內直接呈現 TaskReportDashboard
    expect(wrapper.findComponent({ name: 'TaskReportDashboard' }).exists()).toBe(true)
  })
})


