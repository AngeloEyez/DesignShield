/**
 * @file ArchitectureGuard.test.ts
 * @description 前端架構守門員測試 (Zero-Custom-CSS Policy & Component Guidelines)
 * 確保全專案所有 .vue 檔案均嚴格遵守 Tailwind CSS 與 PrimeVue 原生規範，禁止手寫 <style> 區塊
 */

import { describe, it, expect } from 'vitest'
import fs from 'fs'
import path from 'path'

function getVueFiles(dir: string): string[] {
  let results: string[] = []
  const list = fs.readdirSync(dir)
  list.forEach((file) => {
    const filePath = path.join(dir, file)
    const stat = fs.statSync(filePath)
    if (stat && stat.isDirectory()) {
      results = results.concat(getVueFiles(filePath))
    } else if (file.endsWith('.vue')) {
      results.push(filePath)
    }
  })
  return results
}

describe('前端架構守門員測試 (Architecture Guard)', () => {
  const srcDir = path.resolve(__dirname, '../src')
  const vueFiles = getVueFiles(srcDir)

  it('全專案應包含正確數量的 .vue 檔案', () => {
    expect(vueFiles.length).toBeGreaterThan(0)
  })

  it('確保全專案所有 .vue 檔案皆為 0 行自訂 CSS (Zero <style> Policy)', () => {
    const filesWithStyle: { file: string; line: number }[] = []

    vueFiles.forEach((file) => {
      const content = fs.readFileSync(file, 'utf-8')
      const lines = content.split('\n')
      lines.forEach((line, idx) => {
        if (/<style/i.test(line)) {
          filesWithStyle.push({
            file: path.relative(path.resolve(__dirname, '..'), file),
            line: idx + 1,
          })
        }
      })
    })

    const errorMessage = filesWithStyle.length
      ? `\n🚨 檢測到違反專案架構規範的 <style> 標籤！\n` +
        `本專案嚴格要求全面使用 Tailwind CSS 原子類與 PrimeVue v4 原生元件，禁止自訂 CSS。\n` +
        `違規檔案清單：\n` +
        filesWithStyle.map((f) => `  - ${f.file}:${f.line}`).join('\n') +
        `\n請移除 <style> 區塊並改以 Tailwind CSS 實現。\n`
      : ''

    expect(filesWithStyle, errorMessage).toEqual([])
  })
})
