<template>
  <div v-if="visible" class="yaml-modal-overlay fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" @click.self="$emit('update:visible', false)">
    <div class="yaml-modal-container gitops-guide-container bg-surface-panel border border-surface-border rounded-md w-[640px] max-w-[90vw] max-h-[85vh] flex flex-col shadow-xl overflow-hidden text-vscode-textMain">
      <div class="yaml-modal-header flex justify-between items-center px-4 py-2.5 border-b border-surface-border bg-surface-card">
        <div class="modal-title-box flex items-center gap-2">
          <i class="pi pi-book text-primary text-xs"></i>
          <span class="modal-filename font-semibold text-vscode-textHeading text-xs">GitOps 規則庫維護與貢獻指引 (Rule Governance SOP)</span>
        </div>
        <button
          type="button"
          v-tooltip.bottom="'關閉視窗'"
          class="modal-close-btn text-vscode-textMuted hover:text-vscode-textHeading p-1 text-sm leading-none cursor-pointer bg-transparent border-0"
          @click="$emit('update:visible', false)"
        >
          <i class="pi pi-times"></i>
        </button>
      </div>
      <div class="yaml-modal-body guide-content p-4 overflow-y-auto flex-1 bg-surface-panel flex flex-col gap-3">
        <div>
          <h3 class="text-xs font-semibold text-vscode-textHeading mb-1 flex items-center gap-1.5">
            <i class="pi pi-shield text-primary text-xs"></i>
            <span>核心原則：Git 作為唯一真相來源</span>
          </h3>
          <p class="text-xs text-vscode-textMain leading-relaxed m-0">
            DesignShield 捨棄繁雜的資料庫 CRUD 介面，全面採用 <strong>File-based YAML (IaC)</strong> 存放於 <code class="text-primary bg-surface-card px-1 py-0.5 rounded border border-surface-border font-mono">patterns/</code>。
            所有規則增刪改查皆在 IDE 程式碼編輯器中進行，享受 Git PR 審查與版本歷史。
          </p>
        </div>

        <div class="divide-y divide-surface-border border border-surface-border rounded bg-surface-card">
          <div class="guide-step-card p-3">
            <h4 class="text-xs font-semibold text-vscode-textHeading mb-1 flex items-center gap-2">
              <span class="step-badge bg-primary-500/15 text-primary-600 dark:text-primary-400 px-1.5 py-0.2 rounded text-[11px] font-mono">步驟 1</span>
              <span>新增或修改規則 YAML</span>
            </h4>
            <p class="text-xs text-vscode-textSecondary leading-normal m-0">
              於 <code class="text-primary font-mono">patterns/rules/&lt;domain&gt;/</code> 下建立 Level 3 規則 YAML，嚴格填寫 <code>name</code>, <code>tags</code>, <code>severity</code>, <code>trigger_conditions</code>, <code>check_logic</code>。
            </p>
          </div>

          <div class="guide-step-card p-3">
            <h4 class="text-xs font-semibold text-vscode-textHeading mb-1 flex items-center gap-2">
              <span class="step-badge bg-primary-500/15 text-primary-600 dark:text-primary-400 px-1.5 py-0.2 rounded text-[11px] font-mono">步驟 2</span>
              <span>本地端執行統一校驗指令</span>
            </h4>
            <p class="text-xs text-vscode-textSecondary leading-normal mb-1.5">提交 PR 前，必須在本地端執行 Python 統一校驗腳本：</p>
            <pre class="cmd-snippet bg-surface-ground border border-surface-border rounded px-2.5 py-1.5 text-primary font-mono text-xs m-0"><code>python scripts/validate_rules.py</code></pre>
          </div>

          <div class="guide-step-card p-3">
            <h4 class="text-xs font-semibold text-vscode-textHeading mb-1 flex items-center gap-2">
              <span class="step-badge bg-primary-500/15 text-primary-600 dark:text-primary-400 px-1.5 py-0.2 rounded text-[11px] font-mono">步驟 3</span>
              <span>於 Web UI 即時熱載入</span>
            </h4>
            <p class="text-xs text-vscode-textSecondary leading-normal m-0">
              編輯完成後，可於本頁面右上角點擊「<strong class="text-vscode-textHeading">重新載入規則庫</strong>」按鈕，後端即時掃描磁碟並於介面呈現最新規則！
            </p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * @file GitOpsGuideModal.vue
 * @description GitOps 規則庫維護與貢獻指引對話框 (2026 雙主題 1px 分隔版)
 */

defineProps<{
  visible: boolean
}>()

defineEmits<{
  (e: 'update:visible', val: boolean): void
}>()
</script>
