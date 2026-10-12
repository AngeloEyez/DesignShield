/**
 * @file useTheme.ts
 * @description DesignShield 深淺色主題狀態管理 Composable，支援 localStorage 持久化與 PrimeVue Aura / Tailwind 暗色適配
 */

import { ref } from 'vue'

export type ThemeMode = 'dark' | 'light'

const THEME_STORAGE_KEY = 'designshield-theme'

// 全域共享響應式主題狀態
const currentTheme = ref<ThemeMode>('dark')

/**
 * 套用主題至 HTML 根節點
 */
const applyThemeToDOM = (theme: ThemeMode) => {
  const root = document.documentElement
  if (theme === 'dark') {
    root.classList.add('dark-mode')
    root.classList.add('dark')
  } else {
    root.classList.remove('dark-mode')
    root.classList.remove('dark')
  }
}

/**
 * 初始化主題偏好
 */
export const initTheme = () => {
  const saved = localStorage.getItem(THEME_STORAGE_KEY) as ThemeMode | null
  if (saved === 'dark' || saved === 'light') {
    currentTheme.value = saved
  } else {
    // 預設採用 dark，亦可依系統偏好偵測
    const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches
    currentTheme.value = prefersDark ? 'dark' : 'dark' // 專案預設保持一致深色
  }
  applyThemeToDOM(currentTheme.value)
}

/**
 * 主題控制 Composable
 */
export function useTheme() {
  const setTheme = (theme: ThemeMode) => {
    currentTheme.value = theme
    localStorage.setItem(THEME_STORAGE_KEY, theme)
    applyThemeToDOM(theme)
  }

  const toggleTheme = () => {
    const nextTheme: ThemeMode = currentTheme.value === 'dark' ? 'light' : 'dark'
    setTheme(nextTheme)
  }

  return {
    theme: currentTheme,
    setTheme,
    toggleTheme,
  }
}
