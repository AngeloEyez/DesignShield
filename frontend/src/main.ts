import { createApp } from 'vue'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import { definePreset } from '@primevue/themes'
import Aura from '@primevue/themes/aura'
import Tooltip from 'primevue/tooltip'
import 'primeicons/primeicons.css'
import './assets/main.css'

import App from './App.vue'
import router from './router'
import { initTheme } from './composables/useTheme'

initTheme()

/**
 * 2026 DesignShield 專屬低飽和度主題 Preset
 * 結合溫潤紙感 Stone 表面與低飽和深海藍灰 (Muted Slate-Blue) 主強調色
 */
const DesignShieldPreset = definePreset(Aura, {
  semantic: {
    primary: {
      50: '#f0f9ff',
      100: '#e0f2fe',
      200: '#bae6fd',
      300: '#7dd3fc',
      400: '#38bdf8',
      500: '#0ea5e9',
      600: '#0284c7',
      700: '#0369a1',
      800: '#075985',
      900: '#0c4a6e',
      950: '#082f49',
    },
    colorScheme: {
      light: {
        surface: {
          0: '#ffffff',
          50: '#f7f6f2',
          100: '#efece6',
          200: '#e4e2dd',
          300: '#d5d2cb',
          400: '#9e9b93',
          500: '#78756e',
          600: '#57554f',
          700: '#3a3a35',
          800: '#292925',
          900: '#1c1c1a',
          950: '#161615',
        },
      },
      dark: {
        surface: {
          0: '#eceae4',
          50: '#f7f6f2',
          100: '#d6d3cd',
          200: '#b8b4ac',
          300: '#9e9b93',
          400: '#75726b',
          500: '#57554f',
          600: '#3a3a35',
          700: '#2e2e2a',
          800: '#21211e',
          900: '#1c1c1a',
          950: '#161615',
        },
      },
    },
  },
})

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(PrimeVue, {
  theme: {
    preset: DesignShieldPreset,
    options: {
      darkModeSelector: '.dark-mode',
    },
  },
})
app.directive('tooltip', Tooltip)

app.mount('#app')
