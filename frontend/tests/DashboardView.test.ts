/**
 * @file DashboardView.test.ts
 * @description DashboardView 元件單元與流程測試
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import PrimeVue from 'primevue/config'
import DashboardView from '@/views/DashboardView.vue'
import * as api from '@/services/api'

// Mock 路由
const mockPush = vi.fn()
vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: mockPush,
  }),
  useRoute: () => ({
    path: '/',
    query: {},
  }),
}))

// Mock API
vi.mock('@/services/api', () => ({
  fetchTasks: vi.fn(),
  checkServerHealth: vi.fn(),
  fetchServerHealthDetails: vi.fn(),
  fetchStorageStats: vi.fn(),
  fetchRules: vi.fn(),
  stopTask: vi.fn(),
  deleteTask: vi.fn(),
}))

describe('DashboardView.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.checkServerHealth).mockResolvedValue(true)
    vi.mocked(api.fetchServerHealthDetails).mockResolvedValue({
      status: 'healthy',
      service: 'DesignShield',
      version: '0.1.0',
      components: {
        api: { status: 'healthy', label: 'FASTAPI / DBOS', message: '工作流引擎就緒' },
        database: { status: 'healthy', label: 'Database', message: '連線正常' },
        llm: { status: 'healthy', label: 'LLM 推理', message: '模型就緒' },
      },
    })
    vi.mocked(api.fetchStorageStats).mockResolvedValue({
      storage_root: './storage',
      uploads: { file_count: 3, total_bytes: 3000 },
      staging: { file_count: 2, total_bytes: 2000 },
      reports: { file_count: 1, total_bytes: 1000 },
      total_files: 6,
      total_bytes: 6000,
      total_mb: 5.86,
      disk_total_bytes: 30000000000,
      disk_used_bytes: 10000000000,
      disk_free_bytes: 20000000000,
      disk_total_gb: 27.94,
      disk_used_gb: 9.31,
      disk_free_gb: 18.63,
      disk_used_percent: 33.3,
    })
    vi.mocked(api.fetchRules).mockResolvedValue([
      { id: 'R1', name: '規則 1', category: 'Bus', check_type: 'HEURISTIC', is_active: true } as any,
      { id: 'R2', name: '規則 2', category: 'LLM', check_type: 'LLM', is_active: true } as any,
    ])
    vi.mocked(api.fetchTasks).mockResolvedValue({
      total: 3,
      tasks: [
        {
          id: 'task-run-01',
          project_name: '專案 A',
          task_type: 'DRC',
          status: 'PROCESSING',
          created_at: '2026-10-06T10:00:00Z',
          updated_at: '2026-10-06T10:00:00Z',
          pre_analysis_summary: { component_count: 15, net_count: 25, buses: ['I2C'], platforms: [] },
          selected_rules: ['R1'],
        },
        {
          id: 'task-sched-02',
          project_name: '專案 B',
          task_type: 'DRC',
          status: 'READY_FOR_RUN',
          created_at: '2026-10-06T09:00:00Z',
          updated_at: '2026-10-06T09:00:00Z',
          pre_analysis_summary: { component_count: 5, net_count: 8, buses: [], platforms: [] },
          selected_rules: [],
        },
        {
          id: 'task-done-03',
          project_name: '專案 C',
          task_type: 'DRC',
          status: 'COMPLETED',
          created_at: '2026-10-06T08:00:00Z',
          updated_at: '2026-10-06T08:00:00Z',
          pre_analysis_summary: { component_count: 30, net_count: 50, buses: ['SPI'], platforms: [] },
          selected_rules: ['R1', 'R2'],
        },
      ],
    })
  })

  it('正確渲染頂部標題、指標卡片與伺服器健康狀態', async () => {
    const wrapper = mount(DashboardView, {
      global: { plugins: [PrimeVue] },
    })

    await new Promise((r) => setTimeout(r, 50))
    const text = wrapper.text()
    expect(text).toContain('系統任務總覽儀表板')
    expect(text).toContain('健康運作')
    expect(text).toContain('FastAPI/DBOS')
    expect(text).toContain('Database')
    expect(text).toContain('LLM')
    expect(text).toContain('5.86 MB')
    expect(text).toContain('18.63 GB')
    expect(text).toContain('2 條') // 規則總數
    expect(wrapper.find('.health-lights-row').exists()).toBe(true)
    expect(wrapper.find('.mini-bar-track').exists()).toBe(true)
  })

  it('點擊新增任務按鈕會導航至 /drc', async () => {
    const wrapper = mount(DashboardView, {
      global: { plugins: [PrimeVue] },
    })

    await new Promise((r) => setTimeout(r, 50))
    const newBtn = wrapper.findAll('button').find((b) => b.text().includes('新增 DRC 任務'))
    expect(newBtn).toBeDefined()
    await newBtn?.trigger('click')
    expect(mockPush).toHaveBeenCalledWith('/drc')
  })

  it('支援分頁標籤切換與點擊任務卡片導航', async () => {
    const wrapper = mount(DashboardView, {
      global: { plugins: [PrimeVue] },
    })

    await new Promise((r) => setTimeout(r, 50))
    // 切換至等待與排程標籤
    const schedTab = wrapper.findAll('.tab-btn').find((b) => b.text().includes('等待與排程'))
    expect(schedTab).toBeDefined()
    await schedTab?.trigger('click')

    expect(wrapper.text()).toContain('專案 B')

    // 點擊該任務列
    const row = wrapper.find('.task-row')
    await row.trigger('click')
    expect(mockPush).toHaveBeenCalledWith({
      path: '/drc',
      query: { taskId: 'task-sched-02' },
    })
  })
})
