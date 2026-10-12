/**
 * @file useTheme.test.ts
 * @description useTheme Composable 單元測試
 */

import { describe, it, expect, beforeEach } from 'vitest'
import { useTheme, initTheme } from '@/composables/useTheme'

describe('useTheme.ts', () => {
  beforeEach(() => {
    localStorage.clear()
    document.documentElement.className = ''
  })

  it('initTheme 預設初始化為深色並在根節點加上 dark-mode 與 dark class', () => {
    initTheme()
    const { theme } = useTheme()
    expect(theme.value).toBe('dark')
    expect(document.documentElement.classList.contains('dark-mode')).toBe(true)
    expect(document.documentElement.classList.contains('dark')).toBe(true)
  })

  it('toggleTheme 能在深色與淺色之間切換，並同步更新 localStorage 與 DOM class', () => {
    initTheme()
    const { theme, toggleTheme } = useTheme()
    expect(theme.value).toBe('dark')

    // 切換為淺色
    toggleTheme()
    expect(theme.value).toBe('light')
    expect(localStorage.getItem('designshield-theme')).toBe('light')
    expect(document.documentElement.classList.contains('dark-mode')).toBe(false)
    expect(document.documentElement.classList.contains('dark')).toBe(false)

    // 切換回深色
    toggleTheme()
    expect(theme.value).toBe('dark')
    expect(localStorage.getItem('designshield-theme')).toBe('dark')
    expect(document.documentElement.classList.contains('dark-mode')).toBe(true)
    expect(document.documentElement.classList.contains('dark')).toBe(true)
  })

  it('setTheme 能直接指定特定主題', () => {
    const { theme, setTheme } = useTheme()
    setTheme('light')
    expect(theme.value).toBe('light')
    expect(localStorage.getItem('designshield-theme')).toBe('light')
    expect(document.documentElement.classList.contains('dark-mode')).toBe(false)

    setTheme('dark')
    expect(theme.value).toBe('dark')
    expect(localStorage.getItem('designshield-theme')).toBe('dark')
    expect(document.documentElement.classList.contains('dark-mode')).toBe(true)
  })
})
