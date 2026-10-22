/**
 * @file RuleDirectoryTree.test.ts
 * @description RuleDirectoryTree 目錄結構樹狀視圖單元測試
 */

import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import PrimeVue from 'primevue/config'
import RuleDirectoryTree from '@/components/rules/RuleDirectoryTree.vue'

describe('RuleDirectoryTree.vue', () => {
  const mockLevel1 = [
    {
      name: 'rule_passive_resistor',
      priority: 800,
      description: '通用電阻元件識別規則',
      enabled: true,
      _filename: '800_passive_discrete.yaml',
      _raw_yaml: 'name: rule_passive_resistor\npriority: 800\n',
    },
  ]

  const mockLevel2 = [
    {
      name: 'i2c_bus',
      category: 'I2C',
      priority: 700,
      enabled: true,
      _domain: 'buses',
      _filename: '700_i2c.yaml',
      _raw_yaml: 'name: i2c_bus\ncategory: I2C\n',
    },
  ]

  const mockLevel3 = [
    {
      name: 'i2c_pull_up_existence',
      description: 'I2C 匯流排上拉電阻存在性檢查',
      severity: 'Error',
      tags: ['I2C'],
      enabled: true,
      _domain: 'interfaces',
      _filename: 'i2c_pullup_existence.yaml',
      _raw_yaml: 'name: i2c_pull_up_existence\nseverity: Error\n',
    },
    {
      name: 'power_ground_short_fatal',
      description: '電源接地短路致命檢查',
      severity: 'Fatal',
      tags: ['Power Domain'],
      enabled: false,
      _domain: 'power',
      _filename: 'power_ground_short.yaml',
      _raw_yaml: 'name: power_ground_short_fatal\nseverity: Fatal\n',
    },
  ]

  it('正確渲染根目錄與各層級規則數量', () => {
    const wrapper = mount(RuleDirectoryTree, {
      global: {
        plugins: [PrimeVue],
      },
      props: {
        level1Rules: mockLevel1 as any,
        level2Rules: mockLevel2 as any,
        level3Rules: mockLevel3 as any,
      },
    })

    expect(wrapper.text()).toContain('patterns/ (規則庫根目錄)')
    expect(wrapper.text()).toContain('4') // 1 + 1 + 2 = 4
    expect(wrapper.text()).toContain('components (Level 1 元件分類)')
    expect(wrapper.text()).toContain('rules (Level 3 DRC 設計規則)')
  })

  it('支援關鍵字搜尋過濾節點', async () => {
    const wrapper = mount(RuleDirectoryTree, {
      global: {
        plugins: [PrimeVue],
      },
      props: {
        level1Rules: mockLevel1 as any,
        level2Rules: mockLevel2 as any,
        level3Rules: mockLevel3 as any,
      },
    })

    const input = wrapper.find('input[type="text"]')
    expect(input.exists()).toBe(true)

    await input.setValue('power_ground')
    expect(wrapper.text()).toContain('power_ground_short_fatal')
    expect(wrapper.text()).not.toContain('i2c_pull_up_existence')
  })

  it('點擊 ToggleSwitch 觸發 toggle-rule 事件', async () => {
    const wrapper = mount(RuleDirectoryTree, {
      global: {
        plugins: [PrimeVue],
      },
      props: {
        level1Rules: mockLevel1 as any,
        level2Rules: mockLevel2 as any,
        level3Rules: mockLevel3 as any,
      },
    })

    // 呼叫內部 handleToggleSwitch
    const vm = wrapper.vm as any
    vm.handleToggleSwitch(
      {
        name: 'i2c_pull_up_existence',
        enabled: true,
      },
      false
    )

    expect(wrapper.emitted('toggle-rule')).toBeTruthy()
    expect(wrapper.emitted('toggle-rule')![0]).toEqual([
      {
        ruleName: 'i2c_pull_up_existence',
        enabled: false,
      },
    ])
  })

  const mockPartdb = [
    {
      pn: 'TPS66994',
      mfg: 'TI',
      mfg_pn: 'TPS66994',
      description: 'Dual Port USB Type-C & PD 控制晶片',
      interfaces: {
        I2C: {
          pullup_range_ohms: [1000, 2400],
        },
      },
      _domain: 'ics',
      _filename: 'TI_TPS66994.yaml',
      _rel_path: 'patterns/partdb/data/ics/TI_TPS66994.yaml',
      _raw_yaml: 'mfg: TI\npn: TPS66994\n',
    },
  ]

  it('僅第一層目錄名稱包含 Level 說明，更深層子目錄為純目錄名', () => {
    const wrapper = mount(RuleDirectoryTree, {
      global: {
        plugins: [PrimeVue],
      },
      props: {
        level1Rules: mockLevel1 as any,
        level2Rules: mockLevel2 as any,
        level3Rules: mockLevel3 as any,
        partdbParts: mockPartdb as any,
      },
    })

    // 第一層目錄包含 Level 標記
    expect(wrapper.text()).toContain('rules (Level 3 DRC 設計規則)')
    expect(wrapper.text()).toContain('buses (Level 2 網路拓撲)')
    expect(wrapper.text()).toContain('components (Level 1 元件分類)')
    expect(wrapper.text()).toContain('partdb (PartDB 零件規格庫)')

    // rules 底下的子目錄只呈現純目錄名，不包含 (Level 3 DRC)
    expect(wrapper.text()).toContain('interfaces')
    expect(wrapper.text()).not.toContain('interfaces (Level 3 DRC)')
    expect(wrapper.text()).not.toContain('power (Level 3 DRC)')
  })

  it('樹狀目錄結構嚴格按照 Level 3 -> Level 2 -> Level 1 -> PartDB 排序', () => {
    const wrapper = mount(RuleDirectoryTree, {
      global: {
        plugins: [PrimeVue],
      },
      props: {
        level1Rules: mockLevel1 as any,
        level2Rules: mockLevel2 as any,
        level3Rules: mockLevel3 as any,
        partdbParts: mockPartdb as any,
      },
    })

    const vm = wrapper.vm as any
    const rootChildren = vm.fullTreeNodes[0].children
    // 包含: rules(L3), buses(L2), power(L2), signals(L2), components(L1), partdb(PartDB)
    expect(rootChildren.length).toBe(6)
    // 1. Level 3
    expect(rootChildren[0].key).toBe('folder_rules')
    // 2. Level 2 (buses, power, signals)
    expect(rootChildren[1].key).toBe('folder_l2_buses')
    expect(rootChildren[2].key).toBe('folder_l2_power')
    expect(rootChildren[3].key).toBe('folder_l2_signals')
    // 3. Level 1
    expect(rootChildren[4].key).toBe('folder_components')
    // 4. PartDB
    expect(rootChildren[5].key).toBe('folder_partdb')
  })

  it('PartDB 項目沒有 ToggleSwitch 開關，展示廠商與料號並提供點擊查看 YAML Drawer', async () => {
    const wrapper = mount(RuleDirectoryTree, {
      global: {
        plugins: [PrimeVue],
      },
      props: {
        level1Rules: mockLevel1 as any,
        level2Rules: mockLevel2 as any,
        level3Rules: mockLevel3 as any,
        partdbParts: mockPartdb as any,
      },
    })

    // 驗證 TreeTable 中顯示了廠商與料號
    expect(wrapper.find('.partdb-mfg-tag').exists()).toBe(true)
    expect(wrapper.find('.partdb-mfg-tag').text()).toBe('TI')
    expect(wrapper.find('.partdb-pn').text()).toBe('TPS66994')

    const vm = wrapper.vm as any
    // 呼叫 viewRuleYaml
    vm.viewRuleYaml({
      name: 'TPS66994',
      mfg: 'TI',
      mfg_pn: 'TPS66994',
      level: 'partdb',
      category_path: 'patterns/partdb/data/ics',
      filename: 'TI_TPS66994.yaml',
      rawYaml: 'mfg: TI\npn: TPS66994\n',
    })

    expect(vm.showDrawer).toBe(true)
    expect(vm.selectedRuleData.name).toBe('TPS66994')
    expect(vm.selectedRuleData.mfg).toBe('TI')
    expect(vm.selectedRuleData.mfg_pn).toBe('TPS66994')
    expect(vm.selectedRuleData.level).toBe('partdb')
  })

  it('TreeTable 游標懸停樣式正確套用於單一行而不是整個表格容器', () => {
    const wrapper = mount(RuleDirectoryTree, {
      global: {
        plugins: [PrimeVue],
      },
      props: {
        level1Rules: mockLevel1 as any,
        level2Rules: mockLevel2 as any,
        level3Rules: mockLevel3 as any,
        partdbParts: mockPartdb as any,
      },
    })

    const treetable = wrapper.findComponent({ name: 'TreeTable' })
    expect(treetable.exists()).toBe(true)
    const classes = treetable.attributes('class') || ''
    // 確認包含單行 hover 偽類選擇器，且無容器級別 hover 污染
    expect(classes).toContain('[&_.p-treetable-tbody>tr:hover]:!bg-surface-hover')
    expect(classes).not.toContain('[&_.p-treetable-tbody>tr]:hover:!bg-surface-hover')
  })

  it('表格欄位共用：Level 3 顯示 severity，Level 1 與 Level 2 純文字顯示 priority (不使用 tag)，PartDB 顯示 -', () => {
    const wrapper = mount(RuleDirectoryTree, {
      global: {
        plugins: [PrimeVue],
      },
      props: {
        level1Rules: mockLevel1 as any,
        level2Rules: mockLevel2 as any,
        level3Rules: mockLevel3 as any,
        partdbParts: mockPartdb as any,
      },
    })

    const text = wrapper.text()
    // 欄位標題共用
    expect(text).toContain('嚴重等級 / 優先級')

    // Level 3 顯示 severity (Error, Fatal)
    expect(text).toContain('Error')
    expect(text).toContain('Fatal')

    // Level 1 與 Level 2 顯示 priority (800, 700)
    expect(text).toContain('800')
    expect(text).toContain('700')

    // 驗證 priority 為純文字顯示 (非 tag 膠囊)
    const prioritySpans = wrapper.findAll('.priority-text')
    expect(prioritySpans.length).toBeGreaterThanOrEqual(2)
    const priorityTexts = prioritySpans.map((b) => b.text())
    expect(priorityTexts).toContain('800')
    expect(priorityTexts).toContain('700')

    // 確保 priority 沒有 tag 的 border 或 rounded 樣式
    for (const span of prioritySpans) {
      const cls = span.attributes('class') || ''
      expect(cls).not.toContain('rounded')
      expect(cls).not.toContain('border-')
      expect(cls).not.toContain('bg-')
    }

    // 驗證 severity badge
    const severityBadges = wrapper.findAll('.severity-badge')
    expect(severityBadges.length).toBeGreaterThanOrEqual(2)
    const severityTexts = severityBadges.map((b) => b.text())
    expect(severityTexts).toContain('Error')
    expect(severityTexts).toContain('Fatal')
  })

  it('規則層級 Level 1 與 Level 2 分兩種不同顏色顯示 (Level 1 為 Purple，Level 2 為 Teal，Level 3 為 Primary)', () => {
    const wrapper = mount(RuleDirectoryTree, {
      global: {
        plugins: [PrimeVue],
      },
      props: {
        level1Rules: mockLevel1 as any,
        level2Rules: mockLevel2 as any,
        level3Rules: mockLevel3 as any,
        partdbParts: mockPartdb as any,
      },
    })

    const levelBadges = wrapper.findAll('.level-badge')
    expect(levelBadges.length).toBeGreaterThan(0)

    const level1Badge = levelBadges.find((b) => b.text() === 'Level 1')
    const level2Badge = levelBadges.find((b) => b.text() === 'Level 2')
    const level3Badge = levelBadges.find((b) => b.text() === 'Level 3')

    expect(level1Badge).toBeDefined()
    expect(level2Badge).toBeDefined()
    expect(level3Badge).toBeDefined()

    const l1Class = level1Badge?.attributes('class') || ''
    const l2Class = level2Badge?.attributes('class') || ''
    const l3Class = level3Badge?.attributes('class') || ''

    // Level 1 與 Level 2 顏色必須不同
    expect(l1Class).not.toEqual(l2Class)

    // Level 1 採用 Purple 語義色
    expect(l1Class).toContain('purple')
    // Level 2 採用 Teal 語義色
    expect(l2Class).toContain('teal')
    // Level 3 採用 Primary 藍色
    expect(l3Class).toContain('primary')
  })

  it('搜尋優先級數值 (Priority) 能正確過濾對應之 Level 1 / Level 2 規則', async () => {
    const wrapper = mount(RuleDirectoryTree, {
      global: {
        plugins: [PrimeVue],
      },
      props: {
        level1Rules: mockLevel1 as any,
        level2Rules: mockLevel2 as any,
        level3Rules: mockLevel3 as any,
        partdbParts: mockPartdb as any,
      },
    })

    const input = wrapper.find('input[type="text"]')
    // 搜尋 priority 800
    await input.setValue('800')
    expect(wrapper.text()).toContain('rule_passive_resistor')
    expect(wrapper.text()).toContain('800')
    expect(wrapper.text()).not.toContain('i2c_pull_up_existence')
    expect(wrapper.text()).not.toContain('i2c_bus')

    // 搜尋 priority 700
    await input.setValue('700')
    expect(wrapper.text()).toContain('i2c_bus')
    expect(wrapper.text()).toContain('700')
    expect(wrapper.text()).not.toContain('rule_passive_resistor')
  })

  it('點擊規則開啟 Drawer 時，正確展示對應之嚴重等級或優先級中繼資訊', async () => {
    const wrapper = mount(RuleDirectoryTree, {
      global: {
        plugins: [PrimeVue],
      },
      props: {
        level1Rules: mockLevel1 as any,
        level2Rules: mockLevel2 as any,
        level3Rules: mockLevel3 as any,
        partdbParts: mockPartdb as any,
      },
    })

    const vm = wrapper.vm as any

    // 1. 檢視 Level 1 規則 (含 priority: 800)
    vm.viewRuleYaml({
      name: 'rule_passive_resistor',
      level: 'level1',
      category_path: 'patterns/components',
      filename: '800_passive_discrete.yaml',
      priority: 800,
      enabled: true,
      rawYaml: 'name: rule_passive_resistor\npriority: 800\n',
    })
    await wrapper.vm.$nextTick()
    expect(vm.showDrawer).toBe(true)
    expect(vm.selectedRuleData.priority).toBe(800)
    expect(document.body.textContent).toContain('優先級:')
    expect(document.body.textContent).toContain('800')

    // 2. 檢視 Level 3 規則 (含 severity: Error)
    vm.viewRuleYaml({
      name: 'i2c_pull_up_existence',
      level: 'level3',
      category_path: 'patterns/rules/interfaces',
      filename: 'i2c_pullup_existence.yaml',
      severity: 'Error',
      enabled: true,
      rawYaml: 'name: i2c_pull_up_existence\nseverity: Error\n',
    })
    await wrapper.vm.$nextTick()
    expect(vm.selectedRuleData.severity).toBe('Error')
    expect(document.body.textContent).toContain('嚴重等級:')
    expect(document.body.textContent).toContain('Error')
  })
})
