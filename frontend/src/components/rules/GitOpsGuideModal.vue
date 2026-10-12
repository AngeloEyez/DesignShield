<template>
  <div v-if="visible" class="yaml-modal-overlay fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4" @click.self="$emit('update:visible', false)">
    <div class="yaml-modal-container gitops-guide-container bg-[#1e1e1e] border border-[#333333] rounded-md w-[680px] max-w-[90vw] max-h-[85vh] flex flex-col shadow-2xl overflow-hidden">
      <div class="yaml-modal-header flex justify-between items-center px-4 py-3 border-b border-[#333333] bg-[#2d2d2d]">
        <div class="modal-title-box flex items-center">
          <i class="pi pi-book text-sky-400 mr-2"></i>
          <span class="modal-filename font-semibold text-white text-xs">GitOps 規則庫維護與貢獻指引 (Rule Governance SOP)</span>
        </div>
        <button type="button" class="modal-close-btn text-[#858585] hover:text-white p-1 text-base leading-none cursor-pointer" @click="$emit('update:visible', false)">
          <i class="pi pi-times"></i>
        </button>
      </div>
      <div class="yaml-modal-body guide-content p-4 overflow-y-auto flex-1 bg-[#1e1e1e]">
        <h3 class="text-sm font-semibold text-white mb-2 flex items-center">
          <i class="pi pi-shield mr-2 text-sky-400"></i>核心原則：Git 作為唯一真相來源
        </h3>
        <p class="text-xs text-[#cccccc] leading-relaxed mb-4">
          DesignShield 捨棄繁雜的資料庫 CRUD 介面，全面採用 <strong>File-based YAML (IaC)</strong> 存放於 <code class="text-sky-300 bg-[#252526] px-1 py-0.5 rounded border border-[#333333]">patterns/</code>。
          所有規則增刪改查皆在 IDE 程式碼編輯器中進行，享受 Git PR 審查與版本歷史。
        </p>

        <div class="guide-step-card bg-[#252526] border border-[#333333] rounded p-3 mb-3">
          <h4 class="text-xs font-semibold text-white mb-1.5 flex items-center gap-2">
            <span class="step-badge bg-sky-500/20 text-sky-400 px-2 py-0.5 rounded text-[11px]">步驟 1</span> 新增或修改規則 YAML
          </h4>
          <p class="text-xs text-[#858585] leading-normal m-0">
            於 <code class="text-sky-300">patterns/rules/&lt;domain&gt;/</code> 下建立 Level 3 規則 YAML，嚴格填寫 <code>name</code>, <code>tags</code>, <code>severity</code>, <code>trigger_conditions</code>, <code>check_logic</code>。
          </p>
        </div>

        <div class="guide-step-card bg-[#252526] border border-[#333333] rounded p-3 mb-3">
          <h4 class="text-xs font-semibold text-white mb-1.5 flex items-center gap-2">
            <span class="step-badge bg-sky-500/20 text-sky-400 px-2 py-0.5 rounded text-[11px]">步驟 2</span> 本地端執行統一校驗指令
          </h4>
          <p class="text-xs text-[#858585] leading-normal mb-2">提交 PR 前，必須在本地端執行 Python 統一校驗腳本：</p>
          <pre class="cmd-snippet bg-[#1e1e1e] border border-[#333333] rounded p-2.5 text-sky-300 font-mono text-xs m-0"><code>python scripts/validate_rules.py</code></pre>
        </div>

        <div class="guide-step-card bg-[#252526] border border-[#333333] rounded p-3 mb-3">
          <h4 class="text-xs font-semibold text-white mb-1.5 flex items-center gap-2">
            <span class="step-badge bg-sky-500/20 text-sky-400 px-2 py-0.5 rounded text-[11px]">步驟 3</span> 於 Web UI 即時熱載入
          </h4>
          <p class="text-xs text-[#858585] leading-normal m-0">
            編輯完成後，可於本頁面右上角點擊「<strong class="text-white">重新載入規則庫</strong>」按鈕，後端即時掃描磁碟並於介面呈現最新規則！
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
