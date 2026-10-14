/**
 * @file clipboard.ts
 * 安全且具備降級機制的剪貼簿複製工具 (相容 HTTP 非安全上下文與各類瀏覽器環境)
 */

/**
 * 將指定文字複製到使用者系統剪貼簿
 *
 * @param text 要複製的字串內容
 * @returns Promise<boolean> 是否成功寫入剪貼簿
 */
export async function copyToClipboard(text: string): Promise<boolean> {
  if (!text) return false

  // 1. 優先嘗試現代 Clipboard API (適用 HTTPS 或 localhost 安全上下文)
  if (typeof navigator !== 'undefined' && navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
    try {
      await navigator.clipboard.writeText(text)
      return true
    } catch (err) {
      console.warn('[Clipboard] navigator.clipboard.writeText 失敗，切換至 textarea 降級機制:', err)
    }
  }

  // 2. 降級使用 document.execCommand('copy') (相容 HTTP 區域網路或不支援 Clipboard API 的環境)
  if (typeof document !== 'undefined' && typeof document.createElement === 'function') {
    try {
      const textArea = document.createElement('textarea')
      textArea.value = text

      // 避免視窗捲動或觸發移動端鍵盤
      textArea.style.position = 'fixed'
      textArea.style.top = '0'
      textArea.style.left = '0'
      textArea.style.width = '2em'
      textArea.style.height = '2em'
      textArea.style.padding = '0'
      textArea.style.border = 'none'
      textArea.style.outline = 'none'
      textArea.style.boxShadow = 'none'
      textArea.style.background = 'transparent'
      textArea.style.opacity = '0'
      textArea.setAttribute('readonly', '')

      document.body.appendChild(textArea)
      textArea.focus()
      textArea.select()
      // 相容 iOS Safari 的選取邏輯
      textArea.setSelectionRange(0, text.length)

      const successful = document.execCommand('copy')
      document.body.removeChild(textArea)
      return successful
    } catch (err) {
      console.error('[Clipboard] document.execCommand 降級複製失敗:', err)
      return false
    }
  }

  return false
}
