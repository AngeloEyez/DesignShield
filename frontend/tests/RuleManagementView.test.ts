/**
 * @file RuleManagementView.test.ts
 * @description RuleManagementView 規則管理頁面單元測試
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import PrimeVue from 'primevue/config'
import RuleManagementView from '@/views/RuleManagementView.vue'
import * as api from '@/services/api'
import type { DrcRuleItem } from '@/types/rule'

vi.mock('@/services/api', () => ({
  fetchRules: vi.fn(),
  createRule: vi.fn(),
  updateRule: vi.fn(),
  deleteRule: vi.fn(),
}))

const mockInitialRules: DrcRuleItem[] = [
  {
    id: 'RULE-BUS-I2C-ADDR',
    name: 'I2C 匯流排地址唯一性檢查',
    category: 'Bus Integrity',
    check_type: 'HEURISTIC',
    is_active: true,
    parameters: {},
    prompt_template: null,
    context_extractor: 'extract_i2c_bus_context',
  },
  {
    id: 'RULE-LLM-SD-MODE',
    name: 'MicroSD 介面工作模式合理性確認',
    category: 'Interface Mode',
    check_type: 'LLM',
    is_active: true,
    parameters: { interface: 'SD_SPI' },
    prompt_template: '分析 MicroSD 上下文: {context}',
    context_extractor: 'extract_sd_interface_subgraph',
  },
  {
    id: 'RULE-PWR-CAP-DERATING',
    name: '電源濾波電容耐壓降額檢查',
    category: 'Power Domain',
    check_type: 'HEURISTIC',
    is_active: false,
    parameters: { derating_factor: 0.5 },
    prompt_template: null,
    context_extractor: 'extract_power_capacitors_context',
  },
]

describe('RuleManagementView.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.fetchRules).mockResolvedValue([...mockInitialRules])
  })

  it('正確渲染規則庫頁面、統計卡片與所有規則清單', async () => {
    const wrapper = mount(RuleManagementView, {
      global: {
        plugins: [PrimeVue],
      },
    })

    // 等待 onMounted API 載入完成
    await vi.waitFor(() => {
      expect(wrapper.text()).toContain('RULE-BUS-I2C-ADDR')
    })

    const text = wrapper.text()
    expect(text).toContain('RULE-BUS-I2C-ADDR')
    expect(text).toContain('I2C 匯流排地址唯一性檢查')
    expect(text).toContain('RULE-LLM-SD-MODE')
    expect(text).toContain('MicroSD 介面工作模式合理性確認')
    expect(text).toContain('RULE-PWR-CAP-DERATING')

    // 統計卡片數值 (總共 3 筆，HEURISTIC 2 筆，LLM 1 筆，啟用中 2 筆)
    expect(text).toContain('規則總筆數')
    expect(text).toContain('傳統演算法 (HEURISTIC)')
    expect(text).toContain('本地大模型 (LLM)')
    expect(text).toContain('啟用中規則')
  })

  it('支援關鍵字過濾規則清單', async () => {
    const wrapper = mount(RuleManagementView, {
      global: {
        plugins: [PrimeVue],
      },
    })

    await vi.waitFor(() => {
      expect(wrapper.text()).toContain('RULE-BUS-I2C-ADDR')
    })

    const searchInput = wrapper.find('.filter-search-input')
    await searchInput.setValue('MicroSD')

    expect(wrapper.text()).toContain('MicroSD 介面工作模式合理性確認')
    expect(wrapper.text()).not.toContain('I2C 匯流排地址唯一性檢查')
  })

  it('提供必要欄位 UI 填寫以新增規則', async () => {
    vi.mocked(api.createRule).mockResolvedValue({
      id: 'RULE-NEW-TEST',
      name: '全新電壓測試規則',
      category: 'Power Domain',
      check_type: 'HEURISTIC',
      is_active: true,
      parameters: {},
    })

    const wrapper = mount(RuleManagementView, {
      global: {
        plugins: [PrimeVue],
      },
    })

    await vi.waitFor(() => {
      expect(wrapper.text()).toContain('新增規則')
    })

    // 點擊新增按鈕開啟對話框
    const addBtn = wrapper.findAll('button').find((b) => b.text().includes('新增規則'))
    await addBtn?.trigger('click')

    expect(wrapper.find('.rule-edit-dialog').exists()).toBe(true)
    expect(wrapper.text()).toContain('新增 DRC 檢驗規則')

    // 檢查必要欄位存在
    const inputs = wrapper.findAll('.form-input')
    expect(inputs.length).toBeGreaterThanOrEqual(3)

    // 輸入必要欄位: ID, Name, Category
    await inputs[0].setValue('RULE-NEW-TEST')
    await inputs[1].setValue('全新電壓測試規則')
    await inputs[2].setValue('Power Domain')

    // 點擊確定建立按鈕
    const submitBtn = wrapper.findAll('button').find((b) => b.text().includes('確定建立'))
    expect(submitBtn?.attributes('disabled')).toBeUndefined()
    await submitBtn?.trigger('click')

    expect(api.createRule).toHaveBeenCalledWith(
      expect.objectContaining({
        id: 'RULE-NEW-TEST',
        name: '全新電壓測試規則',
        category: 'Power Domain',
        check_type: 'HEURISTIC',
      })
    )
  })

  it('支援修改現有規則且代碼 ID 不可修改', async () => {
    vi.mocked(api.updateRule).mockResolvedValue({
      id: 'RULE-BUS-I2C-ADDR',
      name: 'I2C 匯流排地址唯一性檢查 (已優化)',
      category: 'Bus Integrity',
      check_type: 'HEURISTIC',
      is_active: true,
      parameters: {},
    })

    const wrapper = mount(RuleManagementView, {
      global: {
        plugins: [PrimeVue],
      },
    })

    await vi.waitFor(() => {
      expect(wrapper.text()).toContain('RULE-BUS-I2C-ADDR')
    })

    // 點擊編輯按鈕
    const editBtns = wrapper.findAll('button').filter((b) => b.text().includes('編輯'))
    await editBtns[0].trigger('click')

    expect(wrapper.find('.rule-edit-dialog').exists()).toBe(true)
    expect(wrapper.text()).toContain('修改規則: RULE-BUS-I2C-ADDR')

    // 檢查 ID 輸入框為 disabled
    const idInput = wrapper.find('.form-input:disabled')
    expect(idInput.exists()).toBe(true)

    // 修改名稱
    const nameInput = wrapper.findAll('.form-input')[1]
    await nameInput.setValue('I2C 匯流排地址唯一性檢查 (已優化)')

    const saveBtn = wrapper.findAll('button').find((b) => b.text().includes('儲存修改'))
    await saveBtn?.trigger('click')

    expect(api.updateRule).toHaveBeenCalledWith(
      'RULE-BUS-I2C-ADDR',
      expect.objectContaining({
        name: 'I2C 匯流排地址唯一性檢查 (已優化)',
      })
    )
  })

  it('支援刪除規則並跳出確認對話框', async () => {
    vi.mocked(api.deleteRule).mockResolvedValue({
      success: true,
      message: 'deleted',
      id: 'RULE-BUS-I2C-ADDR',
    })

    const wrapper = mount(RuleManagementView, {
      global: {
        plugins: [PrimeVue],
      },
    })

    await vi.waitFor(() => {
      expect(wrapper.text()).toContain('RULE-BUS-I2C-ADDR')
    })

    // 點擊刪除按鈕
    const deleteBtns = wrapper.findAll('button').filter((b) => b.text().includes('刪除'))
    await deleteBtns[0].trigger('click')

    // 檢查彈出確認刪除對話框
    expect(wrapper.find('.delete-confirm-dialog').exists()).toBe(true)
    expect(wrapper.text()).toContain('確認刪除規則？')
    expect(wrapper.text()).toContain('RULE-BUS-I2C-ADDR')

    // 點擊對話框內的確認刪除
    const confirmBtn = wrapper.findAll('.dialog-footer button').find((b) => b.text().includes('確認刪除'))
    await confirmBtn?.trigger('click')

    expect(api.deleteRule).toHaveBeenCalledWith('RULE-BUS-I2C-ADDR')
  })

  it('進階 JSON 模式：動態檢查語法與缺少必要欄位，格式正確才能儲存', async () => {
    vi.mocked(api.createRule).mockResolvedValue({
      id: 'RULE-JSON-01',
      name: '進階模式建立規則',
      category: 'Power Domain',
      check_type: 'HEURISTIC',
      is_active: true,
      parameters: {},
    })

    const wrapper = mount(RuleManagementView, {
      global: {
        plugins: [PrimeVue],
      },
    })

    await vi.waitFor(() => {
      expect(wrapper.text()).toContain('新增規則')
    })

    const addBtn = wrapper.findAll('button').find((b) => b.text().includes('新增規則'))
    await addBtn?.trigger('click')

    // 切換至進階 JSON 模式
    const jsonTabBtn = wrapper.findAll('.mode-tab-btn').find((b) => b.text().includes('進階 JSON 模式'))
    await jsonTabBtn?.trigger('click')

    expect(wrapper.find('.advanced-json-textarea').exists()).toBe(true)
    const jsonTextarea = wrapper.find('.advanced-json-textarea')

    // 1. 測試非法語法 (語法錯誤)
    await jsonTextarea.setValue('{ invalid json')
    expect(wrapper.text()).toContain('動態檢驗未通過')
    expect(wrapper.text()).toContain('JSON 語法錯誤')
    const saveBtn = wrapper.findAll('button').find((b) => b.text().includes('確定建立'))
    expect(saveBtn?.attributes('disabled')).toBeDefined()

    // 2. 測試缺少必要欄位 (缺少 category)
    const missingCategoryJson = JSON.stringify({
      id: 'RULE-JSON-01',
      name: '測試名稱',
      check_type: 'HEURISTIC',
    })
    await jsonTextarea.setValue(missingCategoryJson)
    expect(wrapper.text()).toContain('缺少必要欄位 \'category\'')
    expect(saveBtn?.attributes('disabled')).toBeDefined()

    // 3. 測試 check_type 不合法
    const invalidCheckTypeJson = JSON.stringify({
      id: 'RULE-JSON-01',
      name: '測試名稱',
      category: 'Power Domain',
      check_type: 'INVALID_TYPE',
    })
    await jsonTextarea.setValue(invalidCheckTypeJson)
    expect(wrapper.text()).toContain("檢測方式必須為 'HEURISTIC' 或 'LLM'")
    expect(saveBtn?.attributes('disabled')).toBeDefined()

    // 4. 輸入完全合法之 JSON
    const validJson = JSON.stringify(
      {
        id: 'RULE-JSON-01',
        name: '進階模式建立規則',
        category: 'Power Domain',
        check_type: 'HEURISTIC',
        is_active: true,
        parameters: { threshold: 3.3 },
      },
      null,
      2
    )
    await jsonTextarea.setValue(validJson)

    // 檢驗通過，錯誤消失
    expect(wrapper.text()).toContain('動態檢驗通過')
    expect(wrapper.text()).toContain('JSON 格式正確且必要欄位完整')
    expect(saveBtn?.attributes('disabled')).toBeUndefined()

    // 點擊儲存
    await saveBtn?.trigger('click')
    expect(api.createRule).toHaveBeenCalledWith(
      expect.objectContaining({
        id: 'RULE-JSON-01',
        name: '進階模式建立規則',
        category: 'Power Domain',
        check_type: 'HEURISTIC',
      })
    )
  })
})
