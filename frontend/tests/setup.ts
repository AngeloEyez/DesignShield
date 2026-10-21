/**
 * @file setup.ts
 * @description Vitest 測試環境全域初始化設定
 * 提供 jsdom 缺失之 window.matchMedia polyfill，並預設註冊 PrimeVue 與 v-tooltip 指令
 */

import { config } from '@vue/test-utils'
import PrimeVue from 'primevue/config'
import Tooltip from 'primevue/tooltip'

if (typeof window !== 'undefined' && !window.matchMedia) {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: (query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    }),
  })
}

config.global.plugins = [PrimeVue]
config.global.directives = {
  tooltip: Tooltip,
}
