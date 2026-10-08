<template>
  <div v-if="visible" class="yaml-modal-overlay fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4" @click.self="$emit('update:visible', false)">
    <div class="yaml-modal-container bg-slate-900 border border-slate-700 rounded-lg w-[720px] max-w-[90vw] max-h-[85vh] flex flex-col shadow-2xl overflow-hidden">
      <div class="yaml-modal-header flex justify-between items-center px-5 py-4 border-b border-slate-700 bg-slate-800">
        <div class="modal-title-box flex items-center">
          <i class="pi pi-file-code text-sky-400 mr-2"></i>
          <span class="modal-filename font-semibold text-slate-100 text-sm">{{ filename }}</span>
        </div>
        <div class="modal-header-actions flex items-center gap-2">
          <button type="button" class="copy-code-btn bg-slate-700 hover:bg-slate-600 text-slate-100 px-2.5 py-1.5 rounded text-xs flex items-center transition-colors" @click="copyYamlToClipboard">
            <i class="pi pi-copy mr-1"></i>{{ isCopied ? '已複製!' : '複製 YAML' }}
          </button>
          <button type="button" class="modal-close-btn text-slate-400 hover:text-slate-100 p-1 text-lg leading-none cursor-pointer" @click="$emit('update:visible', false)">
            <i class="pi pi-times"></i>
          </button>
        </div>
      </div>
      <div class="yaml-modal-body p-4 overflow-y-auto flex-1">
        <pre class="yaml-code-view m-0 font-mono text-xs text-slate-200 leading-relaxed whitespace-pre-wrap break-all"><code>{{ code }}</code></pre>
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
