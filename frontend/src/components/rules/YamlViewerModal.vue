<template>
  <div v-if="visible" class="yaml-modal-overlay fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" @click.self="$emit('update:visible', false)">
    <div class="yaml-modal-container bg-surface-panel border border-surface-border rounded-md w-[720px] max-w-[90vw] max-h-[85vh] flex flex-col shadow-xl overflow-hidden text-vscode-textMain">
      <div class="yaml-modal-header flex justify-between items-center px-4 py-2.5 border-b border-surface-border bg-surface-card">
        <div class="modal-title-box flex items-center gap-2">
          <i class="pi pi-file-code text-primary text-xs"></i>
          <span class="modal-filename font-semibold text-vscode-textHeading text-xs font-mono">{{ filename }}</span>
        </div>
        <div class="modal-header-actions flex items-center gap-2">
          <button
            type="button"
            v-tooltip.left="isCopied ? '已複製!' : '複製 YAML 原始碼'"
            class="copy-code-btn bg-surface-panel hover:bg-surface-hover border border-surface-border text-vscode-textSecondary hover:text-vscode-textHeading px-2 py-1 rounded text-xs flex items-center gap-1 transition-colors cursor-pointer"
            @click="copyYamlToClipboard"
          >
            <i :class="isCopied ? 'pi pi-check text-emerald-500' : 'pi pi-copy'" class="text-xs"></i>
            <span>{{ isCopied ? '已複製!' : '複製 YAML' }}</span>
          </button>
          <button
            type="button"
            v-tooltip.bottom="'關閉視窗'"
            class="modal-close-btn text-vscode-textMuted hover:text-vscode-textHeading p-1 text-sm leading-none cursor-pointer bg-transparent border-0"
            @click="$emit('update:visible', false)"
          >
            <i class="pi pi-times"></i>
          </button>
        </div>
      </div>
      <div class="yaml-modal-body p-4 overflow-y-auto flex-1 bg-surface-ground">
        <pre class="yaml-code-view m-0 font-mono text-xs text-vscode-textMain leading-relaxed whitespace-pre-wrap break-all"><code>{{ code }}</code></pre>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * @file YamlViewerModal.vue
 * @description YAML 原始碼檢視對話框 (2026 雙主題版)
 */

import { ref } from 'vue'
import { copyToClipboard } from '@/utils/clipboard'

const props = defineProps<{
  visible: boolean
  filename: string
  code: string
}>()

defineEmits<{
  (e: 'update:visible', val: boolean): void
}>()

const isCopied = ref<boolean>(false)

const copyYamlToClipboard = async () => {
  const ok = await copyToClipboard(props.code)
  if (ok) {
    isCopied.value = true
    setTimeout(() => {
      isCopied.value = false
    }, 2000)
  }
}
</script>
