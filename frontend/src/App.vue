<template>
  <div class="app-layout">
    <!-- 頂部導航列 -->
    <header class="navbar">
      <div class="brand">
        <i class="pi pi-shield brand-icon"></i>
        <span class="brand-title">DesignShield</span>
        <span class="brand-subtitle">線路設計規則檢查系統</span>
      </div>

      <!-- 主選單切換導航 -->
      <nav class="nav-menu">
        <router-link to="/" class="nav-link" active-class="active">
          <i class="pi pi-shield mr-1"></i>
          <span>線路 DRC 檢測</span>
        </router-link>
        <router-link to="/settings" class="nav-link" active-class="active">
          <i class="pi pi-cog mr-1"></i>
          <span>系統環境設定</span>
        </router-link>
      </nav>

      <div class="nav-links">
        <span class="badge-status">
          <i class="pi pi-check-circle mr-1"></i> DBOS Engine: 就緒
        </span>
      </div>
    </header>

    <!-- 主內容區 -->
    <main class="main-content">
      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts">
/**
 * @file App.vue
 * @description DesignShield 主版面佈局，整合路由視圖與全域頂部選單
 */
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

.nav-menu {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.nav-link {
  display: flex;
  align-items: center;
  color: #94a3b8;
  text-decoration: none;
  font-size: 0.9rem;
  font-weight: 500;
  padding: 0.45rem 0.9rem;
  border-radius: 6px;
  transition: all 0.2s ease;
}

.nav-link:hover {
  color: #ffffff;
  background-color: rgba(255, 255, 255, 0.08);
}

.nav-link.active {
  color: #38bdf8;
  background-color: rgba(56, 189, 248, 0.12);
  font-weight: 600;
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
