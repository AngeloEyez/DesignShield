import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import SettingsView from '../src/views/SettingsView.vue'
import Button from 'primevue/button'
import ToggleSwitch from 'primevue/toggleswitch'
import Select from 'primevue/select'
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
      { id: 'llm', name: 'LiteLLM 多模型服務串接 (LiteLLM)', icon: 'pi pi-microchip-ai' },
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
        key: 'LITELLM_PROVIDER',
        value: 'local',
        category: 'llm',
        category_name: 'LiteLLM 多模型服務串接 (LiteLLM)',
        label: 'LLM 服務提供者 (Provider)',
        description: '選擇使用的 LiteLLM 服務供應商或本地推論引擎。',
        example: 'local',
        default: 'local',
        is_secret: false,
        requires_restart: true,
      },
      {
        key: 'LLM_API_BASE',
        value: 'http://192.168.1.5:8000/v1',
        category: 'llm',
        category_name: 'LiteLLM 多模型服務串接 (LiteLLM)',
        label: 'LLM 服務 API 端點',
        description: '大語言模型推理伺服器連線端點。',
        example: 'http://192.168.1.5:8000/v1',
        default: 'http://192.168.1.5:8000/v1',
        is_secret: false,
        requires_restart: true,
      },
      {
        key: 'LLM_API_KEY',
        value: 'EMPTY',
        category: 'llm',
        category_name: 'LiteLLM 多模型服務串接 (LiteLLM)',
        label: 'LLM 存取金鑰',
        description: '呼叫模型推理服務所需的 API Key。',
        example: 'EMPTY',
        default: 'EMPTY',
        is_secret: true,
        requires_restart: true,
      },
      {
        key: 'LLM_MODEL',
        value: 'openai/qwen',
        category: 'llm',
        category_name: 'LiteLLM 多模型服務串接 (LiteLLM)',
        label: 'LLM 推理模型名稱',
        description: '呼叫推理伺服器時指定的模型識別名稱。',
        example: 'openai/qwen',
        default: 'openai/qwen',
        is_secret: false,
        requires_restart: true,
      },
      {
        key: 'GEMINI_API_KEY',
        value: '',
        category: 'llm',
        category_name: 'LiteLLM 多模型服務串接 (LiteLLM)',
        label: 'Google Gemini API 金鑰',
        description: 'Google AI Studio 或 Vertex AI Gemini API 金鑰。',
        example: 'AIzaSyxxxxxxxxxxxxxxxxx',
        default: '',
        is_secret: true,
        requires_restart: true,
      },
      {
        key: 'OPENROUTER_API_KEY',
        value: '',
        category: 'llm',
        category_name: 'LiteLLM 多模型服務串接 (LiteLLM)',
        label: 'OpenRouter API 金鑰',
        description: 'OpenRouter 聚合平台存取金鑰。',
        example: 'sk-or-v1-xxxxxxxxxxxxxxxxx',
        default: '',
        is_secret: true,
        requires_restart: true,
      },
      {
        key: 'ENABLE_LEVEL1_LLM_FALLBACK',
        value: 'true',
        category: 'llm',
        category_name: 'LiteLLM 多模型服務串接 (LiteLLM)',
        label: 'Level 1 零件分類 LLM 保底推論開關',
        description: '當 Level 1 元件未能命中任何 YAML 規則時，是否呼叫大語言模型進行語意保底推論。',
        example: 'true 或 false',
        default: 'true',
        item_type: 'boolean',
        is_secret: false,
        requires_restart: false,
      },
      {
        key: 'ENABLE_LEVEL2_LLM_FALLBACK',
        value: 'true',
        category: 'llm',
        category_name: 'LiteLLM 多模型服務串接 (LiteLLM)',
        label: 'Level 2 網路拓撲 LLM 保底推論開關',
        description: '當 Level 2 網路未能命中任何 YAML 拓撲規則且名稱模糊時，是否呼叫大語言模型進行語意保底推論。',
        example: 'true 或 false',
        default: 'true',
        item_type: 'boolean',
        is_secret: false,
        requires_restart: false,
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
    ;(axios.get as any).mockImplementation((url: string, config?: any) => {
      if (url === '/api/v1/settings' || url === '/api/v1/settings/env') {
        return Promise.resolve({ data: mockEnvData })
      }
      if (url === '/api/v1/settings/storage-stats') {
        return Promise.resolve({ data: mockStorageStats })
      }
      if (url === '/api/v1/settings/llm/models') {
        const provider = config?.params?.provider || 'local'
        if (provider === 'gemini') {
          return Promise.resolve({
            data: {
              success: true,
              provider: 'gemini',
              models: ['gemini/gemini-2.5-flash', 'gemini/gemini-2.5-pro', 'gemini/gemini-2.0-flash'],
              message: '成功自 Google Gemini API 取得模型清單',
            },
          })
        }
        return Promise.resolve({
          data: {
            success: true,
            provider: 'local',
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
      if (url === '/api/v1/settings/env' || url === '/api/v1/settings') {
        return Promise.resolve({
          data: {
            success: true,
            changed_keys: Object.keys(payload.settings),
            requires_restart: true,
            restart_reasons: ['LANGFUSE_PUBLIC_KEY'],
            message: '設定已成功儲存至資料庫並即時生效！',
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
      expect.stringMatching(/\/api\/v1\/settings/),
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

  it('displays LiteLLM settings in exact order: API_BASE -> API_KEY -> MODEL', async () => {
    const wrapper = mount(SettingsView, {
      global: {
        components: { Button, Select },
      },
    })

    await wrapper.vm.$nextTick()
    await new Promise((resolve) => setTimeout(resolve, 50))

    // 找到所有 .env-key-badge
    const badges = wrapper.findAll('.env-key-badge').map((el) => el.text())
    const llmBadges = badges.filter((b) => ['LLM_API_BASE', 'LLM_API_KEY', 'LLM_MODEL'].includes(b))

    expect(llmBadges).toEqual(['LLM_API_BASE', 'LLM_API_KEY', 'LLM_MODEL'])
  })

  it('queries LLM models in real-time, supports combo dropdown selection and manual input via PrimeVue Select', async () => {
    const wrapper = mount(SettingsView, {
      global: {
        components: { Button, Select },
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

    // 檢查 PrimeVue Select 整合型 combo 元件是否存在
    const select = wrapper.find('#llm-model-select')
    expect(select.exists()).toBe(true)

    const selectComponent = wrapper.findComponent<any>('#llm-model-select')
    expect(selectComponent.exists()).toBe(true)
    const selectProps = selectComponent.props() as any
    expect(selectProps.editable).toBe(true)
    expect(selectProps.options).toContain('Qwen3.8-27B')
    expect(selectProps.options).toContain('qwen')

    // 測試從下拉選單更新選取模型
    await selectComponent.vm.$emit('update:modelValue', 'Qwen3.8-27B')
    await selectComponent.vm.$emit('change', { value: 'Qwen3.8-27B' })
    await wrapper.vm.$nextTick()

    const vm = wrapper.vm as any
    expect(vm.formValues['LLM_MODEL']).toBe('Qwen3.8-27B')

    // 測試同時支援手動直接自訂輸入
    await selectComponent.vm.$emit('update:modelValue', 'my-custom-fine-tuned-model')
    await selectComponent.vm.$emit('input', { target: { value: 'my-custom-fine-tuned-model' } })
    await wrapper.vm.$nextTick()
    expect(vm.formValues['LLM_MODEL']).toBe('my-custom-fine-tuned-model')
  })

  it('allows switching LiteLLM provider to Gemini and updates model list', async () => {
    const wrapper = mount(SettingsView, {
      global: {
        components: { Button, Select },
      },
    })

    await wrapper.vm.$nextTick()
    await new Promise((resolve) => setTimeout(resolve, 80))

    // 驗證快捷切換按鈕已被移除，使用者透過 provider 選單或方法直接切換
    expect(wrapper.find('.provider-badge-btn').exists()).toBe(false)

    // 觸發切換至 Gemini
    const vm = wrapper.vm as any
    vm.selectProvider('gemini')
    await wrapper.vm.$nextTick()
    await new Promise((resolve) => setTimeout(resolve, 80))

    // 驗證是否向 /api/v1/settings/llm/models 發送了 provider: gemini 的請求
    expect(axios.get).toHaveBeenCalledWith(
      '/api/v1/settings/llm/models',
      expect.objectContaining({
        params: expect.objectContaining({
          provider: 'gemini',
        }),
      })
    )

    // 驗證模型已切換至 Gemini 預設模型
    expect(vm.formValues['LLM_MODEL']).toBe('gemini/gemini-2.5-flash')

    // 驗證可用模型選單包含 gemini 模型
    const selectComponent = wrapper.findComponent<any>('#llm-model-select')
    const geminiProps = selectComponent.props() as any
    expect(geminiProps.options.some((m: string) => m.includes('gemini-2.5-flash'))).toBe(true)
  })

  it('大標題已去除重複括號 (LiteLLM) 且子項目容器具有明顯縮排邊框', async () => {
    const wrapper = mount(SettingsView, {
      global: {
        components: { Button },
      },
    })

    await wrapper.vm.$nextTick()
    await new Promise((resolve) => setTimeout(resolve, 50))

    // 驗證不包含重複的 (LiteLLM) 括號
    expect(wrapper.text()).not.toContain('(LiteLLM)')
    expect(wrapper.text()).toContain('LiteLLM 多模型服務串接')

    // 驗證子項目容器包含縮排邊框
    const itemsList = wrapper.find('.settings-items-list')
    expect(itemsList.exists()).toBe(true)
    expect(itemsList.classes()).toContain('border-l-2')
  })

  it('能正確渲染布林 ToggleSwitch 開關，且點擊開關後可切換啟用與停用狀態並標記為已修改', async () => {
    const wrapper = mount(SettingsView, {
      global: {
        components: { Button, ToggleSwitch },
      },
    })

    await wrapper.vm.$nextTick()
    await new Promise((resolve) => setTimeout(resolve, 80))

    // 找到布林開關包裹器
    const switchWrappers = wrapper.findAll('.boolean-switch-wrapper')
    expect(switchWrappers.length).toBeGreaterThanOrEqual(2)

    // 驗證初始顯示「已啟用」
    expect(switchWrappers[0].text()).toContain('已啟用 (Enabled)')

    // 取得 ToggleSwitch 元件並模擬切換為 false
    const toggleSwitches = wrapper.findAllComponents(ToggleSwitch)
    expect(toggleSwitches.length).toBeGreaterThanOrEqual(2)

    await toggleSwitches[0].vm.$emit('update:modelValue', false)
    await wrapper.vm.$nextTick()

    // 驗證狀態文字變為「已停用」
    expect(switchWrappers[0].text()).toContain('已停用 (Disabled)')
    expect(switchWrappers[0].text()).toContain('DB: false')

    // 驗證頁面標記有未儲存變更
    const vm = wrapper.vm as any
    expect(vm.hasUnsavedChanges).toBe(true)
  })

  it('已徹底移除動態生效標籤，僅保留需重啟生效標籤', async () => {
    const wrapper = mount(SettingsView, {
      global: {
        components: { Button },
      },
    })

    await wrapper.vm.$nextTick()
    await new Promise((resolve) => setTimeout(resolve, 50))

    // 驗證不包含動態生效標籤與文字
    expect(wrapper.find('.badge-dynamic').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('動態生效')

    // 驗證需重啟生效標籤依然存在
    expect(wrapper.findAll('.badge-restart').length).toBeGreaterThan(0)
    expect(wrapper.text()).toContain('需重啟生效')
  })

  it('具備 VS Code 風格左右雙欄佈局與即時搜尋功能，且儲存空間橫條已移除', async () => {
    const wrapper = mount(SettingsView, {
      global: {
        components: { Button },
      },
    })

    await wrapper.vm.$nextTick()
    await new Promise((resolve) => setTimeout(resolve, 50))

    // 驗證左側大綱導航欄存在
    expect(wrapper.find('.settings-outline-sidebar').exists()).toBe(true)
    expect(wrapper.text()).toContain('設定大綱 (Outline)')

    // 驗證原本頂部的磁碟儲存空間指標橫條已被移除 (已遷移至 DashboardView)
    expect(wrapper.find('.storage-card').exists()).toBe(false)

    // 驗證搜尋功能
    const searchInput = wrapper.find('.settings-search-input')
    expect(searchInput.exists()).toBe(true)

    // 輸入關鍵字過濾
    await searchInput.setValue('UPLOAD_RETENTION_DAYS')
    await wrapper.vm.$nextTick()

    // 應該看到 UPLOAD_RETENTION_DAYS，但不應看到未命中的 SERVER_HOST
    expect(wrapper.text()).toContain('UPLOAD_RETENTION_DAYS')
    expect(wrapper.text()).not.toContain('SERVER_HOST')

    // 清除搜尋
    await searchInput.setValue('')
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('SERVER_HOST')
  })
})


