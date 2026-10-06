import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import SettingsView from '../src/views/SettingsView.vue'
import Button from 'primevue/button'
import axios from 'axios'

vi.mock('axios')

// Mock vue-router
const pushMock = vi.fn()
vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: pushMock,
  }),
}))

describe('SettingsView.vue', () => {
  const mockEnvData = {
    env_file_path: '/app/.env',
    total_count: 5,
    categories: [
      { id: 'server', name: '網路與伺服器主機設定', icon: 'pi pi-globe' },
      { id: 'llm', name: '本地大語言模型推理 (Local LLM)', icon: 'pi pi-microchip-ai' },
      { id: 'langfuse', name: 'Langfuse 觀測與追蹤服務', icon: 'pi pi-chart-line' },
      { id: 'storage', name: '檔案儲存與生命週期管理', icon: 'pi pi-database' },
      { id: 'database', name: '核心資料庫連線配置', icon: 'pi pi-server' },
    ],
    items: [
      {
        key: 'SERVER_HOST',
        value: '192.168.1.16',
        category: 'server',
        category_name: '網路與伺服器主機設定',
        label: '伺服器主機 IP 或網域',
        description: '全系統集中主控之主機 IP 或網域名稱。',
        example: '192.168.1.16',
        default: '192.168.1.16',
        is_secret: false,
        requires_restart: true,
      },
      {
        key: 'LOCAL_LLM_URL',
        value: 'http://192.168.1.5:8000/v1',
        category: 'llm',
        category_name: '本地大語言模型推理 (Local LLM)',
        label: '本地 LLM 服務 API 端點',
        description: '本地大語言模型推理伺服器連線端點。',
        example: 'http://192.168.1.5:8000/v1',
        default: 'http://192.168.1.5:8000/v1',
        is_secret: false,
        requires_restart: true,
      },
      {
        key: 'LOCAL_LLM_API_KEY',
        value: 'EMPTY',
        category: 'llm',
        category_name: '本地大語言模型推理 (Local LLM)',
        label: '本地 LLM 存取金鑰',
        description: '呼叫本地模型推理服務所需的 API Key。',
        example: 'EMPTY',
        default: 'EMPTY',
        is_secret: true,
        requires_restart: true,
      },
      {
        key: 'LOCAL_LLM_MODEL',
        value: 'openai/qwen',
        category: 'llm',
        category_name: '本地大語言模型推理 (Local LLM)',
        label: 'LLM 推理模型名稱',
        description: '呼叫本地推理伺服器時指定的模型識別名稱。',
        example: 'openai/qwen',
        default: 'openai/qwen',
        is_secret: false,
        requires_restart: true,
      },
      {
        key: 'LANGFUSE_PUBLIC_KEY',
        value: 'pk-lf-1234567890abcdef',
        category: 'langfuse',
        category_name: 'Langfuse 觀測與追蹤服務',
        label: 'Langfuse 公開金鑰 (Public Key)',
        description: '用於後端 LiteLLM 自動上報 LLM 推理追蹤數據至 Langfuse 的公開金鑰。\n範例: LANGFUSE_PUBLIC_KEY=pk-lf-xxxxxxxxxxxxxxxx',
        example: 'pk-lf-xxxxxxxxxxxxxxxx',
        default: '',
        is_secret: false,
        requires_restart: true,
      },
      {
        key: 'LANGFUSE_SECRET_KEY',
        value: 'sk-lf-0987654321fedcba',
        category: 'langfuse',
        category_name: 'Langfuse 觀測與追蹤服務',
        label: 'Langfuse 私密金鑰 (Secret Key)',
        description: '用於後端 LiteLLM 安全驗證與寫入 Telemetry 紀錄的私密金鑰。\n範例: LANGFUSE_SECRET_KEY=sk-lf-xxxxxxxxxxxxxxxx',
        example: 'sk-lf-xxxxxxxxxxxxxxxx',
        default: '',
        is_secret: true,
        requires_restart: true,
      },
      {
        key: 'UPLOAD_RETENTION_DAYS',
        value: '7',
        category: 'storage',
        category_name: '檔案儲存與生命週期管理',
        label: '暫存檔案保留天數',
        description: '超過此天數之檔案將被垃圾清理機制自動回收以釋放磁碟空間。',
        example: '7',
        default: '7',
        is_secret: false,
        requires_restart: false,
      },
    ],
  }

  const mockStorageStats = {
    total_files: 8,
    total_bytes: 2097152,
    total_mb: 2.0,
    uploads: { file_count: 2, total_bytes: 1048576 },
    staging: { file_count: 5, total_bytes: 1048576 },
    reports: { file_count: 1, total_bytes: 0 },
  }

  beforeEach(() => {
    vi.clearAllMocks()
    ;(axios.get as any).mockImplementation((url: string) => {
      if (url === '/api/v1/settings/env') {
        return Promise.resolve({ data: mockEnvData })
      }
      if (url === '/api/v1/settings/storage-stats') {
        return Promise.resolve({ data: mockStorageStats })
      }
      if (url === '/api/v1/settings/llm/models') {
        return Promise.resolve({
          data: {
            success: true,
            api_base: 'http://192.168.1.5:8000/v1',
            models: ['Qwen3.8-27B', 'qwen', 'custom-model'],
            message: '成功自 LLM 伺服器取得 3 個可用模型',
          },
        })
      }
      if (url === '/health') {
        return Promise.resolve({ status: 200, data: { status: 'healthy' } })
      }
      return Promise.resolve({ data: {} })
    })
    ;(axios.put as any).mockImplementation((url: string, payload: any) => {
      if (url === '/api/v1/settings/env') {
        return Promise.resolve({
          data: {
            success: true,
            changed_keys: Object.keys(payload.settings),
            requires_restart: true,
            restart_reasons: ['LANGFUSE_PUBLIC_KEY'],
            message: '設定已成功寫入 .env 檔案！',
          },
        })
      }
      return Promise.resolve({ data: {} })
    })
    ;(axios.post as any).mockImplementation((url: string) => {
      if (url === '/api/v1/settings/restart') {
        return Promise.resolve({
          data: { success: true, mode: 'docker_socket', message: '已發送重啟訊號' },
        })
      }
      return Promise.resolve({ data: {} })
    })
  })

  it('renders settings page with Chinese descriptions and examples', async () => {
    const wrapper = mount(SettingsView, {
      global: {
        components: { Button },
      },
    })

    await wrapper.vm.$nextTick()
    await new Promise((resolve) => setTimeout(resolve, 50))

    expect(wrapper.text()).toContain('系統環境與參數設定')
    expect(wrapper.text()).toContain('SERVER_HOST')
    expect(wrapper.text()).toContain('LANGFUSE_PUBLIC_KEY')
    expect(wrapper.text()).toContain('LANGFUSE_SECRET_KEY')
    expect(wrapper.text()).toContain('LANGFUSE_PUBLIC_KEY=pk-lf-xxxxxxxxxxxxxxxx')
    expect(wrapper.text()).toContain('LANGFUSE_SECRET_KEY=sk-lf-xxxxxxxxxxxxxxxx')
    expect(wrapper.text()).toContain('重啟服務器')
  })

  it('saves settings and displays restart warning when restart-required key is changed', async () => {
    const wrapper = mount(SettingsView, {
      global: {
        components: { Button },
      },
    })

    await wrapper.vm.$nextTick()
    await new Promise((resolve) => setTimeout(resolve, 50))

    // 修改 LANGFUSE_PUBLIC_KEY 輸入框
    const input = wrapper.find('input[type="text"]')
    expect(input.exists()).toBe(true)
    await input.setValue('192.168.1.99')

    // 點擊儲存按鈕
    const buttons = wrapper.findAllComponents(Button)
    const saveBtn = buttons.find((b) => b.text().includes('儲存設定'))
    expect(saveBtn).toBeDefined()

    await saveBtn!.trigger('click')
    await wrapper.vm.$nextTick()
    await new Promise((resolve) => setTimeout(resolve, 50))

    expect(axios.put).toHaveBeenCalledWith(
      '/api/v1/settings/env',
      expect.objectContaining({
        settings: expect.any(Object),
      })
    )

    // 檢查重啟警告橫幅已顯示
    expect(wrapper.text()).toContain('系統提示：部分設定變更需要重新啟動伺服器才能完全生效')
  })

  it('triggers server restart when confirm restart is clicked', async () => {
    const wrapper = mount(SettingsView, {
      global: {
        components: { Button },
      },
    })

    await wrapper.vm.$nextTick()
    await new Promise((resolve) => setTimeout(resolve, 50))

    // 點擊頂部重啟服務器按鈕開啟對話框
    const restartBtns = wrapper.findAllComponents(Button).filter((b) => b.text().includes('重啟服務器'))
    expect(restartBtns.length).toBeGreaterThan(0)

    await restartBtns[0].trigger('click')
    await wrapper.vm.$nextTick()

    // 檢查彈出確認視窗
    expect(wrapper.text()).toContain('確認重啟伺服器？')

    // 點擊確認重啟
    const confirmBtn = wrapper.findAllComponents(Button).find((b) => b.text().includes('確定重啟'))
    expect(confirmBtn).toBeDefined()

    await confirmBtn!.trigger('click')
    await wrapper.vm.$nextTick()
    await new Promise((resolve) => setTimeout(resolve, 50))

    expect(axios.post).toHaveBeenCalledWith('/api/v1/settings/restart')
  })

  it('displays Local LLM settings in exact order: URL -> API_KEY -> MODEL', async () => {
    const wrapper = mount(SettingsView, {
      global: {
        components: { Button },
      },
    })

    await wrapper.vm.$nextTick()
    await new Promise((resolve) => setTimeout(resolve, 50))

    // 找到所有 .env-key-badge
    const badges = wrapper.findAll('.env-key-badge').map((el) => el.text())
    const llmBadges = badges.filter((b) => b.startsWith('LOCAL_LLM_'))

    expect(llmBadges).toEqual(['LOCAL_LLM_URL', 'LOCAL_LLM_API_KEY', 'LOCAL_LLM_MODEL'])
  })

  it('queries LLM models in real-time, supports dropdown selection and manual input', async () => {
    const wrapper = mount(SettingsView, {
      global: {
        components: { Button },
      },
    })

    await wrapper.vm.$nextTick()
    await new Promise((resolve) => setTimeout(resolve, 80))

    // 檢查即時模型端點是否被呼叫
    expect(axios.get).toHaveBeenCalledWith(
      '/api/v1/settings/llm/models',
      expect.objectContaining({
        params: expect.objectContaining({
          api_base: 'http://192.168.1.5:8000/v1',
        }),
      })
    )

    // 檢查下拉選單 options 是否渲染自查詢到的模型
    const select = wrapper.find('#llm-model-select')
    expect(select.exists()).toBe(true)
    const options = select.findAll('option').map((o) => o.text())
    expect(options).toContain('Qwen3.8-27B')
    expect(options).toContain('qwen')

    // 檢查快速選取晶片 (Chips) 是否包含模型名稱
    const chips = wrapper.findAll('.model-chip').map((c) => c.text())
    expect(chips.some((c) => c.includes('Qwen3.8-27B'))).toBe(true)

    // 測試從下拉選單選擇模型
    await select.setValue('Qwen3.8-27B')
    await select.trigger('change')
    await wrapper.vm.$nextTick()

    // 檢查 model input 的值已被更新為選取的模型
    const modelInput = wrapper.find('.model-input')
    expect(modelInput.exists()).toBe(true)
    expect((modelInput.element as HTMLInputElement).value).toBe('Qwen3.8-27B')

    // 測試點擊快速選取晶片
    const qwenChip = wrapper.findAll('.model-chip').find((c) => c.text().includes('qwen'))
    expect(qwenChip).toBeDefined()
    await qwenChip!.trigger('click')
    await wrapper.vm.$nextTick()
    expect((modelInput.element as HTMLInputElement).value).toBe('qwen')

    // 測試同時支援手動直接輸入
    await modelInput.setValue('my-custom-fine-tuned-model')
    await modelInput.trigger('input')
    await wrapper.vm.$nextTick()
    expect((modelInput.element as HTMLInputElement).value).toBe('my-custom-fine-tuned-model')
  })
})

