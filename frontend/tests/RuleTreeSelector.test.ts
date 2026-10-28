/**
 * @file RuleTreeSelector.test.ts
 * @description RuleTreeSelector 元件單元測試
 */

import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import PrimeVue from 'primevue/config'
import RuleTreeSelector from '@/components/RuleTreeSelector.vue'

describe('RuleTreeSelector.vue', () => {
  it('正確渲染特徵摘要與推薦規則列表', () => {
    const mockSummary = {
      buses: ['I2C', 'SPI'],
      platforms: ['STM32'],
      component_count: 84,
      net_count: 156,
    }
    const mockRules = [
      {
        id: 'RULE-BUS-I2C-ADDR',
        name: 'I2C 匯流排地址唯一性檢查',
        category: 'Bus Integrity',
      },
      {
        id: 'RULE-PWR-CAP-DERATING',
        name: '電源濾波電容耐壓降額檢查',
        category: 'Power Domain',
      },
    ]

    const wrapper = mount(RuleTreeSelector, {
      global: {
        plugins: [PrimeVue],
      },
      props: {
        summary: mockSummary,
        recommendedRules: mockRules,
      },
    })

    const text = wrapper.text()
    expect(text).toContain('元件總數:84')
    expect(text).toContain('網路總數:156')
    expect(text).toContain('I2C, SPI')
    expect(text).toContain('STM32')
    expect(text).toContain('Bus Integrity')
    expect(text).toContain('Power Domain')
    expect(text).toContain('I2C 匯流排地址唯一性檢查')
  })

  it('支援點選全選按鈕切換勾選狀態', async () => {
    const mockRules = [
      {
        id: 'RULE-1',
        name: '規則一',
        category: 'TestCat',
      },
      {
        id: 'RULE-2',
        name: '規則二',
        category: 'TestCat',
      },
    ]

    const wrapper = mount(RuleTreeSelector, {
      global: {
        plugins: [PrimeVue],
      },
      props: {
        summary: { buses: [], platforms: [], component_count: 2, net_count: 2 },
        recommendedRules: mockRules,
      },
    })

    // 初始預設全選
    expect(wrapper.text()).toContain('已選取 2 條規則')

    // 點擊切換全選/取消全選
    const toggleBtn = wrapper.findAll('button').find((b) => b.text().includes('取消全選'))
    expect(toggleBtn).toBeDefined()
    await toggleBtn?.trigger('click')

    expect(wrapper.text()).toContain('已選取 0 條規則')
  })

  it('樹狀結構列出所有規則並允許勾選未被推薦之規則', async () => {
    const mockRecommended = [
      {
        id: 'RULE-REC-01',
        name: '推薦規則A',
        category: 'Power Domain',
      },
    ]

    const mockAllRules = [
      {
        id: 'RULE-REC-01',
        name: '推薦規則A',
        category: 'Power Domain',
        check_type: 'HEURISTIC' as const,
        is_active: true,
        parameters: {},
      },
      {
        id: 'RULE-UNREC-02',
        name: '未推薦自選規則B',
        category: 'Power Domain',
        check_type: 'HEURISTIC' as const,
        is_active: true,
        parameters: {},
      },
      {
        id: 'RULE-UNREC-03',
        name: '訊號完整性自選規則C',
        category: 'Signal Integrity',
        check_type: 'LLM' as const,
        is_active: true,
        parameters: {},
      },
    ]

    const wrapper = mount(RuleTreeSelector, {
      global: {
        plugins: [PrimeVue],
      },
      props: {
        summary: { buses: ['I2C'], platforms: ['STM32'], component_count: 10, net_count: 20 },
        recommendedRules: mockRecommended,
        allRules: mockAllRules,
      },
    })

    const text = wrapper.text()
    // 檢查樹狀結構與分類節點
    expect(text).toContain('Power Domain')
    expect(text).toContain('Signal Integrity')
    // 推薦規則與標籤
    expect(text).toContain('推薦規則A')
    expect(text).toContain('推薦')
    // 未推薦規則存在並可見，且無冗餘之未推薦標籤干擾
    expect(text).toContain('未推薦自選規則B')
    expect(text).not.toContain('未推薦 (可自選)')
    expect(text).toContain('訊號完整性自選規則C')

    // 初始預設僅勾選推薦規則 1 條
    expect(text).toContain('已選取 1 條規則')

    // 找到未推薦規則 B 的 checkbox 並勾選
    const checkboxes = wrapper.findAll<HTMLInputElement>('input[type="checkbox"]')
    const unrecCheckbox = checkboxes.find((cb) => cb.element.value === 'RULE-UNREC-02')
    expect(unrecCheckbox).toBeDefined()
    await unrecCheckbox?.setValue(true)

    // 已選取數量更新為 2 條
    expect(wrapper.text()).toContain('已選取 2 條規則')
    expect(wrapper.text()).toContain('1 條額外選取規則')
  })

  it('當無任何規則存在時，呈現無規則可選且確認按鈕禁用', () => {
    const wrapper = mount(RuleTreeSelector, {
      global: {
        plugins: [PrimeVue],
      },
      props: {
        summary: { buses: [], platforms: [], component_count: 0, net_count: 0 },
        recommendedRules: [],
        allRules: [],
      },
    })

    const text = wrapper.text()
    expect(text).toContain('無規則可選')
    expect(text).toContain('已選取 0 條規則')

    const confirmBtn = wrapper.find('button.confirm-run-btn')
    expect(confirmBtn.exists()).toBe(true)
    expect(confirmBtn.attributes('disabled')).toBeDefined()
  })

  it('支援視圖密度切換 (緊湊/詳細) 與單項細節展開/收合', async () => {
    const mockRules = [
      {
        id: 'RULE-DENSITY-1',
        name: '緊湊視圖測試規則',
        category: 'Power',
        description: '這是長篇詳細描述說明',
      },
    ]

    const wrapper = mount(RuleTreeSelector, {
      global: { plugins: [PrimeVue] },
      props: {
        summary: { buses: [], platforms: [], component_count: 1, net_count: 1 },
        recommendedRules: mockRules,
      },
    })

    // 預設為緊湊視圖，長篇描述不顯示在主行
    expect(wrapper.find('.density-toggle-btn').text()).toContain('緊湊視圖')
    expect(wrapper.find('.rule-expanded-details').exists()).toBe(false)

    // 點擊單項展開按鈕
    const expandBtn = wrapper.find('.expand-rule-btn')
    expect(expandBtn.exists()).toBe(true)
    await expandBtn.trigger('click')
    await wrapper.vm.$nextTick()

    // 展開細節出現
    expect(wrapper.find('.rule-expanded-details').exists()).toBe(true)
    expect(wrapper.text()).toContain('這是長篇詳細描述說明')

    // 切換全域為詳細視圖
    const densityBtn = wrapper.find('.density-toggle-btn')
    await densityBtn.trigger('click')
    await wrapper.vm.$nextTick()
    expect(wrapper.find('.density-toggle-btn').text()).toContain('詳細視圖')
    expect(wrapper.find('.rule-expanded-details').exists()).toBe(true)
  })

  it('色彩降噪驗證：不顯示拓撲斷言標籤，LLM 規則正確顯示 LLM 標籤', async () => {
    const mockRules = [
      {
        id: 'RULE-TOPO',
        name: '拓撲規則',
        category: 'Power',
        check_type: 'topology_check',
      },
      {
        id: 'RULE-LLM',
        name: '推理規則',
        category: 'Power',
        check_type: 'llm_agent',
      },
    ]

    const wrapper = mount(RuleTreeSelector, {
      global: { plugins: [PrimeVue] },
      props: {
        summary: { buses: [], platforms: [], component_count: 1, net_count: 1 },
        recommendedRules: mockRules,
      },
    })

    const text = wrapper.text()
    // 拓撲斷言標籤已被移除，不應出現在介面上
    expect(text).not.toContain('拓撲斷言')
    // LLM 規則應顯示 LLM 標籤
    expect(wrapper.find('.llm-tag').exists()).toBe(true)
    expect(wrapper.find('.llm-tag').text()).toBe('LLM')
  })

  it('支援 enabled: false 之停用規則：以反灰及已停用標籤呈現、禁用 Checkbox 且不被全選包含', async () => {
    const mockAllRules = [
      {
        id: 'RULE-ACTIVE-1',
        name: '啟用規則',
        category: 'Power Domain',
        enabled: true,
      },
      {
        id: 'RULE-DISABLED-2',
        name: '已停用規則',
        category: 'Power Domain',
        enabled: false,
      },
    ]

    const wrapper = mount(RuleTreeSelector, {
      global: { plugins: [PrimeVue] },
      props: {
        summary: { buses: [], platforms: [], component_count: 2, net_count: 2 },
        recommendedRules: [],
        allRules: mockAllRules,
      },
    })

    // 檢查停用標籤與反灰效果
    expect(wrapper.text()).toContain('已停用規則')
    const disabledTag = wrapper.find('.disabled-tag')
    expect(disabledTag.exists()).toBe(true)
    expect(disabledTag.text()).toBe('已停用')

    // 檢查 checkbox 是否禁用
    const checkboxes = wrapper.findAll<HTMLInputElement>('input[type="checkbox"]')
    const disabledCheckbox = checkboxes.find((cb) => cb.element.value === 'RULE-DISABLED-2')
    expect(disabledCheckbox).toBeDefined()
    expect(disabledCheckbox?.attributes('disabled')).toBeDefined()

    // 點擊停用規則行不應將其勾選
    const disabledItem = wrapper.findAll('.tree-rule-item').find((item) => item.text().includes('已停用規則'))
    expect(disabledItem?.classes()).toContain('opacity-50')
    expect(disabledItem?.classes()).toContain('cursor-not-allowed')
    await disabledItem?.trigger('click')
    expect(wrapper.text()).toContain('已選取 0 條規則')

    // 點擊全選所有規則按鈕，只應勾選啟用的規則，跳過停用規則
    const selectAllBtn = wrapper.findAll('button').find((b) => b.text().includes('全選所有規則'))
    expect(selectAllBtn).toBeDefined()
    await selectAllBtn?.trigger('click')
    expect(wrapper.text()).toContain('已選取 1 條規則')
  })

  it('支援多 BOM Config 選擇，並在點擊確認時發出設定物件', async () => {
    const mockRules = [
      {
        id: 'RULE-1',
        name: '規則一',
        category: 'TestCat',
      },
    ]

    const wrapper = mount(RuleTreeSelector, {
      global: { plugins: [PrimeVue] },
      props: {
        summary: {
          buses: [],
          platforms: [],
          component_count: 5,
          net_count: 5,
          is_multi_config: true,
          config_count: 3,
          config_names: ['Config 1', 'Config 2', 'Config 3'],
        },
        recommendedRules: mockRules,
      },
    })

    const text = wrapper.text()
    // 工具列應顯示多 Config 標題與選項
    expect(text).toContain('BOM Config:')
    expect(text).toContain('將執行 3 組 Config')
    expect(text).toContain('Config 1')
    expect(text).toContain('Config 2')
    expect(text).toContain('Config 3')

    // 點擊確認並執行
    const confirmBtn = wrapper.find('.confirm-run-btn')
    await confirmBtn.trigger('click')

    const emitted = wrapper.emitted('run')
    expect(emitted).toBeDefined()
    expect(emitted?.[0]?.[0]).toEqual({
      ruleIds: ['RULE-1'],
      selectedConfigs: ['Config 1', 'Config 2', 'Config 3'],
    })
  })

  it('VS Code 設定佈局驗證：左側大綱導航欄正確渲染各領域大綱、計數標籤與雙獨立滾動捲軸結構', async () => {
    const mockRules = [
      { id: 'R-PWR-1', name: '電源規則1', category: 'Power Domain' },
      { id: 'R-PWR-2', name: '電源規則2', category: 'Power Domain' },
      { id: 'R-BUS-1', name: '匯流排規則1', category: 'Bus Integrity' },
    ]

    const wrapper = mount(RuleTreeSelector, {
      global: { plugins: [PrimeVue] },
      props: {
        summary: { buses: ['I2C'], platforms: ['STM32'], component_count: 10, net_count: 20 },
        recommendedRules: [mockRules[0]],
        allRules: mockRules,
      },
    })

    // 檢查左右雙欄容器結構
    const splitContainer = wrapper.find('.rule-split-container')
    expect(splitContainer.exists()).toBe(true)

    // 檢查左側大綱導航欄
    const sidebar = wrapper.find('.rule-outline-sidebar')
    expect(sidebar.exists()).toBe(true)
    expect(sidebar.classes()).toContain('overflow-y-auto')
    expect(sidebar.text()).toContain('規則大綱 (Outline)')
    expect(sidebar.text()).toContain('共 3 條')

    // 檢查大綱項目按鈕
    const outlineButtons = sidebar.findAll('.outline-item-btn')
    expect(outlineButtons.length).toBe(2) // Power Domain, Bus Integrity
    expect(outlineButtons[0].text()).toContain('Power Domain')
    expect(outlineButtons[0].text()).toContain('1/2') // 1 條已勾選推薦 / 總共 2 條
    expect(outlineButtons[1].text()).toContain('Bus Integrity')
    expect(outlineButtons[1].text()).toContain('0/1')

    // 檢查右側長頁面獨立滾動區與錨點標記
    const contentPane = wrapper.find('.rule-content-pane')
    expect(contentPane.exists()).toBe(true)
    expect(contentPane.classes()).toContain('overflow-y-auto')
    expect(contentPane.find('#rule-cat-Power_Domain').exists()).toBe(true)
    expect(contentPane.find('#rule-cat-Bus_Integrity').exists()).toBe(true)

    // 點擊左側大綱導航切換 activeCategory
    await outlineButtons[1].trigger('click')
    expect((wrapper.vm as any).activeCategory).toBe('Bus Integrity')
  })

  it('頁面按鈕 xs size 規格驗證：篩選、批次操作與分類按鈕緊湊化以增加顯示面積', () => {
    const mockRules = [
      { id: 'R-1', name: '規則1', category: 'Power' },
    ]

    const wrapper = mount(RuleTreeSelector, {
      global: { plugins: [PrimeVue] },
      props: {
        summary: { buses: [], platforms: [], component_count: 5, net_count: 5 },
        recommendedRules: mockRules,
      },
    })

    // 檢查篩選按鈕皆帶有 !h-6 與 !text-[11px] 的 xs size 樣式
    const filterPills = wrapper.findAll('.filter-pill-btn')
    expect(filterPills.length).toBeGreaterThanOrEqual(3)
    filterPills.forEach((btn) => {
      expect(btn.classes()).toContain('!h-6')
      expect(btn.classes()).toContain('!text-[11px]')
    })

    // 檢查批次操作按鈕為 24px (!w-6 !h-6)
    const compactActionBtns = wrapper.findAll('.compact-action-btn')
    expect(compactActionBtns.length).toBeGreaterThanOrEqual(3)
    compactActionBtns.forEach((btn) => {
      expect(btn.classes()).toContain('!w-6')
      expect(btn.classes()).toContain('!h-6')
    })

    // 檢查類別全選按鈕為 !h-6
    const catActionBtn = wrapper.find('.cat-action-btn')
    expect(catActionBtn.exists()).toBe(true)
    expect(catActionBtn.classes()).toContain('!h-6')

    // 檢查主要執行按鈕仍維持標準 small 高度
    const confirmBtn = wrapper.find('.confirm-run-btn')
    expect(confirmBtn.classes()).toContain('!h-7')
  })

  it('RWD 響應式適配：支援行動版橫向滾動分類頁籤列', async () => {
    const mockRules = [
      { id: 'R-1', name: '規則1', category: 'Power' },
      { id: 'R-2', name: '規則2', category: 'Signal' },
    ]

    const wrapper = mount(RuleTreeSelector, {
      global: { plugins: [PrimeVue] },
      props: {
        summary: { buses: [], platforms: [], component_count: 2, net_count: 2 },
        recommendedRules: mockRules,
      },
    })

    const tabsContainer = wrapper.find('.category-tabs')
    expect(tabsContainer.exists()).toBe(true)
    expect(tabsContainer.classes()).toContain('overflow-x-auto')
    expect(tabsContainer.classes()).toContain('md:hidden')

    const tabButtons = tabsContainer.findAll('.tab-btn')
    expect(tabButtons.length).toBe(2)
    expect(tabButtons[0].text()).toContain('Power')
    expect(tabButtons[1].text()).toContain('Signal')

    // 點擊頁籤更新 activeCategory
    await tabButtons[1].trigger('click')
    expect((wrapper.vm as any).activeCategory).toBe('Signal')
  })

  it('正確渲染 interfaces 領域中所有規則，包含兩條皆已選取之推薦規則 (differential_channel_continuity_check 與 pn_swap_check)', async () => {
    const mockAllRules = [
      { id: 'ic_decoupling_capacitor_existence', name: '確認所有具備電氣功能之 IC 晶片在電源網路接腳旁是否正確配置去耦/旁路電容', category: 'power', enabled: false },
      { id: 'power_capacitor_derating', name: '檢查跨接於電源軌之濾波電容其額定耐壓是否滿足工作電壓降額要求', category: 'power', enabled: false },
      { id: 'power_ground_short_fatal', name: '檢查線路中是否存在同時標註電源與接地屬性之網路節點', category: 'power', enabled: false },
      { id: 'power_sequence_compatibility', name: '晶片上下電時序與復位電路邏輯確認', category: 'power', enabled: false },
      { id: 'differential_channel_continuity_check', name: '差分通道兩端端點同時上件時，檢查中間所有串聯元件皆確實上件導通', category: 'interfaces', enabled: true },
      { id: 'i2c_pull_up_existence', name: '檢查所有 I2C 通訊匯流排是否均具備必備的上拉電阻', category: 'interfaces', enabled: false },
      { id: 'i2c_stm32_dynamic', name: '結合 PartDB 零件規格庫針對主控晶片進行驗證', category: 'interfaces', enabled: false },
      { id: 'level_shift_logic_validation', name: '跨電壓域電平轉換邏輯合理性確認', category: 'interfaces', enabled: false },
      { id: 'pn_swap_check', name: '高速差分對端到端反接/拓撲不對稱/懸空檢查', category: 'interfaces', enabled: true },
      { id: 'sd_interface_mode_reasoning', name: 'MicroSD 介面工作模式合理性確認', category: 'interfaces', enabled: false },
    ]

    const wrapper = mount(RuleTreeSelector, {
      global: { plugins: [PrimeVue] },
      props: {
        summary: { buses: ['USB2', 'USB3'], platforms: [], component_count: 3523, net_count: 2400 },
        recommendedRules: [
          { id: 'differential_channel_continuity_check', name: '差分通道兩端端點同時上件時...', category: 'Differential Pair' },
          { id: 'pn_swap_check', name: '高速差分對端到端反接...', category: 'Differential Pair' },
        ],
        allRules: mockAllRules,
      },
    })

    await wrapper.vm.$nextTick()

    // 驗證 10 條規則全數渲染於 DOM 中
    const items = wrapper.findAll('.tree-rule-item')
    expect(items.length).toBe(10)

    // 驗證 interfaces 分類下包含 6 條規則
    const interfacesNode = wrapper.find('#rule-cat-interfaces')
    expect(interfacesNode.exists()).toBe(true)
    const interfacesItems = interfacesNode.findAll('.tree-rule-item')
    expect(interfacesItems.length).toBe(6)

    // 驗證兩條推薦規則皆成功呈現且處於勾選狀態
    const diffContinuityItem = interfacesItems.find((i) => i.text().includes('差分通道兩端端點同時上件時'))
    expect(diffContinuityItem).toBeDefined()
    expect(diffContinuityItem?.text()).toContain('推薦')
    const diffContinuityCheckbox = diffContinuityItem?.find<HTMLInputElement>('input[type="checkbox"]')
    expect(diffContinuityCheckbox?.element.checked).toBe(true)

    const pnSwapItem = interfacesItems.find((i) => i.text().includes('高速差分對端到端反接'))
    expect(pnSwapItem).toBeDefined()
    expect(pnSwapItem?.text()).toContain('推薦')
    const pnSwapCheckbox = pnSwapItem?.find<HTMLInputElement>('input[type="checkbox"]')
    expect(pnSwapCheckbox?.element.checked).toBe(true)

    // 驗證 power 分類首條規則正常渲染
    const powerNode = wrapper.find('#rule-cat-power')
    expect(powerNode.exists()).toBe(true)
    const powerItems = powerNode.findAll('.tree-rule-item')
    expect(powerItems.length).toBe(4)
    expect(powerItems[0].text()).toContain('確認所有具備電氣功能之 IC 晶片在電源網路接腳旁是否正確配置去耦')

    // 驗證分類標頭不包含 sticky top-8，避免首項被遮蔽
    const header = wrapper.find('.category-node-header')
    expect(header.classes()).not.toContain('sticky')
  })

  it('導航跳轉對齊群組標題、無規則標題圖示且無嚴重程度標籤 (驗證 VS Code 簡潔樣式)', async () => {
    const mockRules = [
      { id: 'rule_1', name: '規則一', category: 'Power', severity: 'Error', enabled: true },
      { id: 'rule_2', name: '規則二', category: 'Power', severity: 'Fatal', enabled: false },
      { id: 'rule_3', name: '規則三', category: 'Interface', severity: 'Warning', enabled: true },
    ]

    const wrapper = mount(RuleTreeSelector, {
      global: { plugins: [PrimeVue] },
      props: {
        summary: { buses: [], platforms: [], component_count: 10, net_count: 5 },
        recommendedRules: [],
        allRules: mockRules,
      },
    })

    await wrapper.vm.$nextTick()

    // 1. 驗證規則群組節點具備 scroll-mt-12 以免被頂部釘選工具列遮蔽
    const categoryNodes = wrapper.findAll('.category-node')
    expect(categoryNodes.length).toBe(2)
    categoryNodes.forEach((node) => {
      expect(node.classes()).toContain('scroll-mt-12')
    })

    // 2. 驗證規則標題無圖標 (大綱導航欄按鈕與右側群組標題皆無 folder-icon / 類別圖標)
    const outlineButtons = wrapper.findAll('.outline-item-btn')
    expect(outlineButtons.length).toBe(2)
    outlineButtons.forEach((btn) => {
      // 確保按鈕內沒有額外的類別圖示 <i>
      expect(btn.find('i').exists()).toBe(false)
    })
    expect(wrapper.find('.folder-icon').exists()).toBe(false)

    // 3. 驗證規則項目中不再渲染任何嚴重程度標籤 (.severity-tag)
    const severityTags = wrapper.findAll('.severity-tag')
    expect(severityTags.length).toBe(0)
    expect(wrapper.text()).not.toContain('Error')
    expect(wrapper.text()).not.toContain('Fatal')
    expect(wrapper.text()).not.toContain('Warning')

    // 4. 驗證規則狀態標籤：僅保留 PrimeVue 原生之「已停用」與「推薦」標籤，不渲染「未推薦」標籤
    const disabledTag = wrapper.find('.disabled-tag')
    expect(disabledTag.exists()).toBe(true)
    expect(disabledTag.classes()).toContain('p-tag')
    expect(disabledTag.text()).toBe('已停用')

    // 確認無未推薦標籤干擾
    expect(wrapper.find('.unrecommended-tag').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('未推薦')
  })
})



