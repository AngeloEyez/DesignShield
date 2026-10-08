<template>
  <div v-if="visible" class="yaml-modal-overlay" @click.self="$emit('update:visible', false)">
    <div class="yaml-modal-container">
      <div class="yaml-modal-header">
        <div class="modal-title-box">
          <i class="pi pi-file-code text-primary mr-2"></i>
          <span class="modal-filename">{{ filename }}</span>
        </div>
        <div class="modal-header-actions">
          <button type="button" class="copy-code-btn" @click="copyYamlToClipboard">
            <i class="pi pi-copy mr-1"></i>{{ isCopied ? '已複製!' : '複製 YAML' }}
          </button>
          <button type="button" class="modal-close-btn" @click="$emit('update:visible', false)">
            <i class="pi pi-times"></i>
          </button>
        </div>
      </div>
      <div class="yaml-modal-body">
        <pre class="yaml-code-view"><code>{{ code }}</code></pre>
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

<style scoped>
.yaml-modal-overlay {
  position: fixed;
  inset: 0;
  background-color: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 999;
}

.yaml-modal-container {
  background-color: #0f172a;
  border: 1px solid #334155;
  border-radius: 8px;
  width: 720px;
  max-width: 90vw;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
}

.yaml-modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid #334155;
  background-color: #1e293b;
  border-top-left-radius: 8px;
  border-top-right-radius: 8px;
}

.modal-title-box {
  display: flex;
  align-items: center;
}

.modal-filename {
  font-weight: 600;
  color: #f8fafc;
  font-size: 0.95rem;
}

.modal-header-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.copy-code-btn {
  background-color: #334155;
  border: none;
  color: #f8fafc;
  padding: 0.35rem 0.65rem;
  border-radius: 4px;
  font-size: 0.8rem;
  cursor: pointer;
  display: flex;
  align-items: center;
}

.copy-code-btn:hover {
  background-color: #475569;
}

.modal-close-btn {
  background: none;
  border: none;
  color: #94a3b8;
  font-size: 1.1rem;
  cursor: pointer;
  padding: 0.2rem;
}

.modal-close-btn:hover {
  color: #f8fafc;
}

.yaml-modal-body {
  padding: 1rem;
  overflow-y: auto;
  flex: 1;
}

.yaml-code-view {
  margin: 0;
  font-family: 'Fira Code', monospace;
  font-size: 0.825rem;
  line-height: 1.5;
  color: #e2e8f0;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
