/**
 * @file useTheme.ts
 * @description DesignShield 深淺色主題狀態管理 Composable，支援 localStorage 持久化與 PrimeVue Aura / Tailwind 雙主題適配
 */

import { ref } from 'vue'

export type ThemeMode = 'dark' | 'light'

const THEME_STORAGE_KEY = 'designshield-theme'

// 全域共享響應式主題狀態 (預設為溫潤紙感淺色模式 Light Theme)
const currentTheme = ref<ThemeMode>('light')

/**
 * 套用主題至 HTML 根節點
 * @param {ThemeMode} theme 目標主題模式 ('light' | 'dark')
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
 * 若 localStorage 尚無紀錄，預設開啟溫潤紙感淺色模式 ('light')
 */
export const initTheme = () => {
  const saved = localStorage.getItem(THEME_STORAGE_KEY) as ThemeMode | null
  if (saved === 'dark' || saved === 'light') {
    currentTheme.value = saved
  } else {
    currentTheme.value = 'light'
  }
  applyThemeToDOM(currentTheme.value)
}

/**
 * 主題控制 Composable
 */
export function useTheme() {
  /**
   * 直接指定特定主題並持久化至 localStorage
   * @param {ThemeMode} theme 目標主題模式
   */
  const setTheme = (theme: ThemeMode) => {
    currentTheme.value = theme
    localStorage.setItem(THEME_STORAGE_KEY, theme)
    applyThemeToDOM(theme)
  }

  /**
   * 在淺色與深色主題間切換
   */
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
