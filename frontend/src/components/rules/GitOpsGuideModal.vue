<template>
  <div v-if="visible" class="yaml-modal-overlay fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4" @click.self="$emit('update:visible', false)">
    <div class="yaml-modal-container gitops-guide-container bg-slate-900 border border-slate-700 rounded-lg w-[680px] max-w-[90vw] max-h-[85vh] flex flex-col shadow-2xl overflow-hidden">
      <div class="yaml-modal-header flex justify-between items-center px-5 py-4 border-b border-slate-700 bg-slate-800">
        <div class="modal-title-box flex items-center">
          <i class="pi pi-book text-sky-400 mr-2"></i>
          <span class="modal-filename font-semibold text-slate-100 text-sm">GitOps 規則庫維護與貢獻指引 (Rule Governance SOP)</span>
        </div>
        <button type="button" class="modal-close-btn text-slate-400 hover:text-slate-100 p-1 text-lg leading-none cursor-pointer" @click="$emit('update:visible', false)">
          <i class="pi pi-times"></i>
        </button>
      </div>
      <div class="yaml-modal-body guide-content p-5 overflow-y-auto flex-1">
        <h3 class="text-base font-semibold text-slate-100 mb-3 flex items-center">
          <i class="pi pi-shield mr-2 text-sky-400"></i>核心原則：Git 作為唯一真相來源
        </h3>
        <p class="text-sm text-slate-400 leading-relaxed mb-5">
          DesignShield 捨棄繁雜的資料庫 CRUD 介面，全面採用 <strong>File-based YAML (IaC)</strong> 存放於 <code>patterns/</code>。
          所有規則增刪改查皆在 IDE 程式碼編輯器中進行，享受 Git PR 審查與版本歷史。
        </p>

        <div class="guide-step-card bg-slate-800/80 border border-slate-700 rounded-md p-4 mb-4">
          <h4 class="text-sm font-medium text-slate-100 mb-2 flex items-center gap-2">
            <span class="step-badge bg-sky-500/20 text-sky-400 px-2 py-0.5 rounded text-xs">步驟 1</span> 新增或修改規則 YAML
          </h4>
          <p class="text-xs text-slate-400 leading-normal">
            於 <code>patterns/rules/&lt;domain&gt;/</code> 下建立 Level 3 規則 YAML，嚴格填寫 <code>name</code>, <code>tags</code>, <code>severity</code>, <code>trigger_conditions</code>, <code>check_logic</code>。
          </p>
        </div>

        <div class="guide-step-card bg-slate-800/80 border border-slate-700 rounded-md p-4 mb-4">
          <h4 class="text-sm font-medium text-slate-100 mb-2 flex items-center gap-2">
            <span class="step-badge bg-sky-500/20 text-sky-400 px-2 py-0.5 rounded text-xs">步驟 2</span> 本地端執行統一校驗指令
          </h4>
          <p class="text-xs text-slate-400 leading-normal mb-2">提交 PR 前，必須在本地端執行 Python 統一校驗腳本：</p>
          <pre class="cmd-snippet bg-slate-950 border border-slate-800 rounded p-3 text-sky-400 font-mono text-xs"><code>python scripts/validate_rules.py</code></pre>
        </div>

        <div class="guide-step-card bg-slate-800/80 border border-slate-700 rounded-md p-4 mb-4">
          <h4 class="text-sm font-medium text-slate-100 mb-2 flex items-center gap-2">
            <span class="step-badge bg-sky-500/20 text-sky-400 px-2 py-0.5 rounded text-xs">步驟 3</span> 於 Web UI 即時熱載入
          </h4>
          <p class="text-xs text-slate-400 leading-normal">
            編輯完成後，可於本頁面右上角點擊「<strong>重新載入規則庫</strong>」按鈕，後端即時掃描磁碟並於介面呈現最新規則！
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  visible: boolean
}>()

defineEmits<{
  (e: 'update:visible', val: boolean): void
}>()
</script>
