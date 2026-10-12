<template>
  <div v-if="visible" class="yaml-modal-overlay fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4" @click.self="$emit('update:visible', false)">
    <div class="yaml-modal-container bg-[#1e1e1e] border border-[#333333] rounded-md w-[720px] max-w-[90vw] max-h-[85vh] flex flex-col shadow-2xl overflow-hidden">
      <div class="yaml-modal-header flex justify-between items-center px-4 py-3 border-b border-[#333333] bg-[#2d2d2d]">
        <div class="modal-title-box flex items-center">
          <i class="pi pi-file-code text-sky-400 mr-2"></i>
          <span class="modal-filename font-semibold text-white text-xs font-mono">{{ filename }}</span>
        </div>
        <div class="modal-header-actions flex items-center gap-2">
          <button type="button" class="copy-code-btn bg-[#252526] hover:bg-[#333333] border border-[#333333] text-[#cccccc] hover:text-white px-2.5 py-1 rounded text-xs flex items-center transition-colors cursor-pointer" @click="copyYamlToClipboard">
            <i class="pi pi-copy mr-1"></i>{{ isCopied ? '已複製!' : '複製 YAML' }}
          </button>
          <button type="button" class="modal-close-btn text-[#858585] hover:text-white p-1 text-base leading-none cursor-pointer" @click="$emit('update:visible', false)">
            <i class="pi pi-times"></i>
          </button>
        </div>
      </div>
      <div class="yaml-modal-body p-4 overflow-y-auto flex-1 bg-[#1e1e1e]">
        <pre class="yaml-code-view m-0 font-mono text-xs text-[#cccccc] leading-relaxed whitespace-pre-wrap break-all"><code>{{ code }}</code></pre>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

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
  try {
    await navigator.clipboard.writeText(props.code)
    isCopied.value = true
    setTimeout(() => {
      isCopied.value = false
    }, 2000)
  } catch {
    // 忽略剪貼簿例外
  }
}
</script>
