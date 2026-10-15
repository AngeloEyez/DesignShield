/**
 * @file RuleDirectoryTree.test.ts
 * @description RuleDirectoryTree 目錄結構樹狀視圖單元測試
 */

import { describe, it, expect, vi } from 'vitest'
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
      pn: 'STM32F405',
      description: 'ARM Cortex-M4 微控制器',
      interfaces: {
        I2C: {
          forbid_gnd_capacitor: true,
        },
      },
      _domain: 'ics',
      _filename: 'ST_STM32F405.yaml',
      _rel_path: 'patterns/partdb/data/ics/ST_STM32F405.yaml',
      _raw_yaml: 'pn: STM32F405\n',
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

  it('PartDB 項目沒有 ToggleSwitch 開關，僅提供點擊查看 YAML Drawer', async () => {
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
    // 呼叫 viewRuleYaml
    vm.viewRuleYaml({
      name: 'STM32F405',
      level: 'partdb',
      category_path: 'patterns/partdb/data/ics',
      filename: 'ST_STM32F405.yaml',
      rawYaml: 'pn: STM32F405\n',
    })

    expect(vm.showDrawer).toBe(true)
    expect(vm.selectedRuleData.name).toBe('STM32F405')
    expect(vm.selectedRuleData.level).toBe('partdb')
  })
})
