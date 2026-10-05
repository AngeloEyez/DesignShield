<template>
  <div class="app-layout">
    <!-- 頂部導航列 -->
    <header class="navbar">
      <div class="brand">
        <i class="pi pi-shield brand-icon"></i>
        <span class="brand-title">DesignShield</span>
        <span class="brand-subtitle">線路設計規則檢查系統</span>
      </div>
      <div class="nav-links">
        <span class="badge-status">
          <i class="pi pi-check-circle mr-1"></i> DBOS Engine: 就緒
        </span>
      </div>
    </header>

    <!-- 主內容區 -->
    <main class="main-content">
      <TaskMonitorView />
    </main>
  </div>
</template>

<script setup lang="ts">
/**
 * @file App.vue
 * @description DesignShield 主版面佈局
 */

import TaskMonitorView from '@/views/TaskMonitorView.vue'
</script>

<style>
/* 全域基本樣式重設 */
body {
  margin: 0;
  padding: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  background-color: #f8fafc;
  color: #334155;
}

* {
  box-sizing: border-box;
}

.app-layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.navbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background-color: #0f172a;
  color: #ffffff;
  padding: 0.85rem 2rem;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.brand {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.brand-icon {
  font-size: 1.5rem;
  color: #38bdf8;
}

.brand-title {
  font-size: 1.25rem;
  font-weight: 700;
  letter-spacing: -0.025em;
  color: #ffffff;
}

.brand-subtitle {
  font-size: 0.875rem;
  color: #94a3b8;
  margin-left: 0.5rem;
  border-left: 1px solid #334155;
  padding-left: 0.75rem;
}

.badge-status {
  font-size: 0.8rem;
  color: #34d399;
  background-color: rgba(52, 211, 153, 0.15);
  padding: 0.3rem 0.6rem;
  border-radius: 9999px;
  display: inline-flex;
  align-items: center;
}

.main-content {
  flex: 1;
}

.mr-1 {
  margin-right: 0.25rem;
}

.mr-2 {
  margin-right: 0.5rem;
}
</style>
