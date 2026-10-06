<template>
  <div class="app-layout">
    <!-- 左側 VS Code 風格可收合導航抽屜 -->
    <aside class="sidebar" :class="{ 'is-collapsed': isCollapsed }">
      <!-- 頂端品牌識別 -->
      <div class="sidebar-brand" :title="isCollapsed ? 'DesignShield' : ''">
        <div class="brand-logo-wrapper">
          <i class="pi pi-shield brand-icon"></i>
        </div>
        <div v-if="!isCollapsed" class="brand-text">
          <div class="brand-title">DesignShield</div>
          <div class="brand-subtitle">線路設計規則檢查系統</div>
        </div>
      </div>

      <!-- 導航選單列表 -->
      <nav class="sidebar-nav">
        <router-link
          to="/"
          class="nav-item"
          :class="{ active: currentRoutePath === '/' }"
          :title="isCollapsed ? '總覽儀表板 (Dashboard)' : ''"
        >
          <i class="pi pi-th-large nav-icon"></i>
          <span v-if="!isCollapsed" class="nav-label">總覽儀表板</span>
        </router-link>

        <router-link
          to="/drc"
          class="nav-item"
          :class="{ active: currentRoutePath.startsWith('/drc') }"
          :title="isCollapsed ? '線路 DRC 任務檢測' : ''"
        >
          <i class="pi pi-shield nav-icon"></i>
          <span v-if="!isCollapsed" class="nav-label">線路 DRC 檢測</span>
        </router-link>

        <router-link
          to="/rules"
          class="nav-item"
          :class="{ active: currentRoutePath.startsWith('/rules') }"
          :title="isCollapsed ? 'DRC 規則庫管理' : ''"
        >
          <i class="pi pi-sliders-h nav-icon"></i>
          <span v-if="!isCollapsed" class="nav-label">規則庫管理</span>
        </router-link>

        <router-link
          to="/settings"
          class="nav-item"
          :class="{ active: currentRoutePath.startsWith('/settings') }"
          :title="isCollapsed ? '系統環境與參數設定' : ''"
        >
          <i class="pi pi-cog nav-icon"></i>
          <span v-if="!isCollapsed" class="nav-label">系統環境設定</span>
        </router-link>
      </nav>

      <!-- 側邊欄底部控制區 -->
      <div class="sidebar-footer">
        <div class="engine-status" :title="isCollapsed ? 'DBOS Engine: 就緒' : ''">
          <span class="status-dot"></span>
          <span v-if="!isCollapsed" class="status-label">DBOS Engine: 就緒</span>
        </div>

        <button
          class="collapse-toggle-btn"
          :title="isCollapsed ? '展開側邊欄' : '收合側邊欄'"
          @click="toggleSidebar"
        >
          <i :class="isCollapsed ? 'pi pi-chevron-right' : 'pi pi-chevron-left'"></i>
        </button>
      </div>
    </aside>

    <!-- 主內容呈現區 -->
    <main class="main-content">
      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts">
/**
 * @file App.vue
 * @description DesignShield 主版面佈局，VS Code 風格左側可收合抽屜導航與路由視圖
 */

import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const currentRoutePath = computed(() => route.path)

// 側邊欄收合狀態 (由 LocalStorage 記憶使用者習慣)
const isCollapsed = ref<boolean>(
  localStorage.getItem('designshield_sidebar_collapsed') === 'true'
)

const toggleSidebar = () => {
  isCollapsed.value = !isCollapsed.value
  localStorage.setItem('designshield_sidebar_collapsed', String(isCollapsed.value))
}
</script>

<style>
/* VS Code 深色調色盤與全域 CSS 變數 */
:root, .dark-mode {
  --vscode-bg-base: #1e1e1e;
  --vscode-bg-sidebar: #252526;
  --vscode-bg-panel: #252526;
  --vscode-bg-header: #2d2d2d;
  --vscode-bg-card: #252526;
  --vscode-bg-input: #1e1e1e;
  --vscode-bg-hover: #2a2d2e;
  --vscode-bg-active: #37373d;
  --vscode-border: #333333;
  --vscode-border-light: #3c3c3c;
  --vscode-text-main: #cccccc;
  --vscode-text-heading: #ffffff;
  --vscode-text-muted: #858585;
  --vscode-text-secondary: #999999;
  --vscode-blue: #007acc;
  --vscode-cyan: #4ec9b0;
  --vscode-green: #89d185;
  --vscode-yellow: #dcdcaa;
  --vscode-purple: #c586c0;
  --vscode-danger: #f14c4c;
}

/* 全域基本樣式重設 */
body {
  margin: 0;
  padding: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  background-color: var(--vscode-bg-base);
  color: var(--vscode-text-main);
  font-size: 13px;
  line-height: 1.45;
}

* {
  box-sizing: border-box;
}

/* 滾動條 VS Code 風格 */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}
::-webkit-scrollbar-track {
  background: #1e1e1e;
}
::-webkit-scrollbar-thumb {
  background: #424242;
  border-radius: 4px;
}
::-webkit-scrollbar-thumb:hover {
  background: #4f4f4f;
}

.app-layout {
  min-height: 100vh;
  display: flex;
  flex-direction: row;
  overflow: hidden;
  background-color: var(--vscode-bg-base);
}

/* VS Code 風格深色側邊欄 */
.sidebar {
  width: 220px;
  background-color: var(--vscode-bg-sidebar);
  color: var(--vscode-text-main);
  display: flex;
  flex-direction: column;
  transition: width 0.22s cubic-bezier(0.4, 0, 0.2, 1);
  flex-shrink: 0;
  z-index: 100;
  border-right: 1px solid var(--vscode-border);
  user-select: none;
}

.sidebar.is-collapsed {
  width: 60px;
}

.sidebar-brand {
  height: 48px;
  display: flex;
  align-items: center;
  padding: 0 0.85rem;
  border-bottom: 1px solid var(--vscode-border);
  gap: 0.65rem;
  overflow: hidden;
  white-space: nowrap;
}

.brand-logo-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 26px;
}

.brand-icon {
  font-size: 1.25rem;
  color: #38bdf8;
}

.brand-text {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.brand-title {
  font-size: 0.9rem;
  font-weight: 700;
  letter-spacing: -0.01em;
  color: #ffffff;
}

.brand-subtitle {
  font-size: 0.65rem;
  color: var(--vscode-text-muted);
}

/* 導航選單清單 */
.sidebar-nav {
  flex: 1;
  padding: 0.65rem 0.45rem;
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  overflow-y: auto;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  padding: 0.45rem 0.65rem;
  color: #999999;
  text-decoration: none;
  border-radius: 4px;
  font-size: 0.82rem;
  font-weight: 500;
  transition: all 0.15s ease;
  white-space: nowrap;
  position: relative;
}

.sidebar.is-collapsed .nav-item {
  justify-content: center;
  padding: 0.5rem 0;
}

.nav-icon {
  font-size: 1rem;
  min-width: 18px;
  text-align: center;
}

.nav-label {
  overflow: hidden;
  text-overflow: ellipsis;
}

.nav-item:hover {
  color: #ffffff;
  background-color: var(--vscode-bg-hover);
}

.nav-item.active {
  color: #ffffff;
  background-color: #37373d;
  font-weight: 600;
}

.nav-item.active::before {
  content: "";
  position: absolute;
  left: 0;
  top: 4px;
  bottom: 4px;
  width: 2px;
  background-color: #007acc;
  border-radius: 0 2px 2px 0;
}

/* 側邊欄底部狀態與收合按鈕 */
.sidebar-footer {
  padding: 0.55rem 0.75rem;
  border-top: 1px solid var(--vscode-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  overflow: hidden;
}

.sidebar.is-collapsed .sidebar-footer {
  flex-direction: column;
  padding: 0.55rem 0.25rem;
  gap: 0.55rem;
}

.engine-status {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  font-size: 0.72rem;
  color: var(--vscode-text-muted);
  white-space: nowrap;
}

.status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background-color: #10b981;
  box-shadow: 0 0 6px #10b981;
  display: inline-block;
  flex-shrink: 0;
}

.collapse-toggle-btn {
  background: transparent;
  border: 1px solid #3c3c3c;
  color: #999999;
  border-radius: 3px;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.15s ease;
  font-size: 0.72rem;
}

.collapse-toggle-btn:hover {
  background-color: #333333;
  color: #ffffff;
  border-color: #555555;
}

/* 主內容呈現視窗 */
.main-content {
  flex: 1;
  min-width: 0;
  height: 100vh;
  overflow-y: auto;
  background-color: var(--vscode-bg-base);
}
</style>
