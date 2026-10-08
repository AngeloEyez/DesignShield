<template>
  <div v-if="visible" class="yaml-modal-overlay" @click.self="$emit('update:visible', false)">
    <div class="yaml-modal-container gitops-guide-container">
      <div class="yaml-modal-header">
        <div class="modal-title-box">
          <i class="pi pi-book text-primary mr-2"></i>
          <span class="modal-filename">GitOps 規則庫維護與貢獻指引 (Rule Governance SOP)</span>
        </div>
        <button type="button" class="modal-close-btn" @click="$emit('update:visible', false)">
          <i class="pi pi-times"></i>
        </button>
      </div>
      <div class="yaml-modal-body guide-content">
        <h3><i class="pi pi-shield mr-2"></i>核心原則：Git 作為唯一真相來源</h3>
        <p>
          DesignShield 捨棄繁雜的資料庫 CRUD 介面，全面採用 <strong>File-based YAML (IaC)</strong> 存放於 <code>patterns/</code>。
          所有規則增刪改查皆在 IDE 程式碼編輯器中進行，享受 Git PR 審查與版本歷史。
        </p>

        <div class="guide-step-card">
          <h4><span class="step-badge">步驟 1</span> 新增或修改規則 YAML</h4>
          <p>於 <code>patterns/rules/&lt;domain&gt;/</code> 下建立 Level 3 規則 YAML，嚴格填寫 <code>name</code>, <code>tags</code>, <code>severity</code>, <code>trigger_conditions</code>, <code>check_logic</code>。</p>
        </div>

        <div class="guide-step-card">
          <h4><span class="step-badge">步驟 2</span> 本地端執行統一校驗指令</h4>
          <p>提交 PR 前，必須在本地端執行 Python 統一校驗腳本：</p>
          <pre class="cmd-snippet"><code>python scripts/validate_rules.py</code></pre>
        </div>

        <div class="guide-step-card">
          <h4><span class="step-badge">步驟 3</span> 於 Web UI 即時熱載入</h4>
          <p>編輯完成後，可於本頁面右上角點擊「<strong>重新載入規則庫</strong>」按鈕，後端即時掃描磁碟並於介面呈現最新規則！</p>
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

.gitops-guide-container {
  width: 680px;
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
  padding: 1.25rem;
  overflow-y: auto;
  flex: 1;
}

.guide-content h3 {
  margin: 0 0 0.75rem 0;
  color: #f8fafc;
  font-size: 1.05rem;
  display: flex;
  align-items: center;
}

.guide-content p {
  color: #94a3b8;
  font-size: 0.875rem;
  line-height: 1.5;
  margin-bottom: 1.25rem;
}

.guide-step-card {
  background-color: #1e293b;
  border: 1px solid #334155;
  border-radius: 6px;
  padding: 1rem;
  margin-bottom: 1rem;
}

.guide-step-card h4 {
  margin: 0 0 0.5rem 0;
  font-size: 0.9rem;
  color: #f8fafc;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.step-badge {
  background-color: rgba(56, 189, 248, 0.2);
  color: #38bdf8;
  padding: 0.15rem 0.45rem;
  border-radius: 4px;
  font-size: 0.75rem;
}

.guide-step-card p {
  margin: 0;
  font-size: 0.825rem;
}

.cmd-snippet {
  background-color: #0f172a;
  border: 1px solid #334155;
  border-radius: 4px;
  padding: 0.5rem 0.75rem;
  margin-top: 0.5rem;
  color: #38bdf8;
  font-family: 'Fira Code', monospace;
  font-size: 0.85rem;
}
</style>
