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
/* 全域基本樣式重設 */
body {
  margin: 0;
  padding: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  background-color: #f8fafc;
  color: #334155;
  font-size: 14px;
}

* {
  box-sizing: border-box;
}

.app-layout {
  min-height: 100vh;
  display: flex;
  flex-direction: row;
  overflow: hidden;
}

/* VS Code 風格深色側邊欄 */
.sidebar {
  width: 220px;
  background-color: #111827;
  color: #e2e8f0;
  display: flex;
  flex-direction: column;
  transition: width 0.22s cubic-bezier(0.4, 0, 0.2, 1);
  flex-shrink: 0;
  z-index: 100;
  border-right: 1px solid #1f2937;
  user-select: none;
}

.sidebar.is-collapsed {
  width: 60px;
}

.sidebar-brand {
  height: 56px;
  display: flex;
  align-items: center;
  padding: 0 1rem;
  border-bottom: 1px solid #1f2937;
  gap: 0.75rem;
  overflow: hidden;
  white-space: nowrap;
}

.brand-logo-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 28px;
}

.brand-icon {
  font-size: 1.35rem;
  color: #38bdf8;
}

.brand-text {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.brand-title {
  font-size: 0.95rem;
  font-weight: 700;
  letter-spacing: -0.025em;
  color: #ffffff;
}

.brand-subtitle {
  font-size: 0.68rem;
  color: #94a3b8;
  letter-spacing: -0.01em;
}

/* 導航選單清單 */
.sidebar-nav {
  flex: 1;
  padding: 0.75rem 0.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  overflow-y: auto;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.55rem 0.75rem;
  color: #9ca3af;
  text-decoration: none;
  border-radius: 6px;
  font-size: 0.875rem;
  font-weight: 500;
  transition: all 0.15s ease;
  white-space: nowrap;
  position: relative;
}

.sidebar.is-collapsed .nav-item {
  justify-content: center;
  padding: 0.6rem 0;
}

.nav-icon {
  font-size: 1.1rem;
  min-width: 20px;
  text-align: center;
}

.nav-label {
  overflow: hidden;
  text-overflow: ellipsis;
}

.nav-item:hover {
  color: #f9fafb;
  background-color: #1f2937;
}

.nav-item.active {
  color: #38bdf8;
  background-color: rgba(56, 189, 248, 0.12);
  font-weight: 600;
}

.nav-item.active::before {
  content: "";
  position: absolute;
  left: 0;
  top: 6px;
  bottom: 6px;
  width: 3px;
  background-color: #38bdf8;
  border-radius: 0 2px 2px 0;
}

/* 側邊欄底部狀態與收合按鈕 */
.sidebar-footer {
  padding: 0.65rem 0.75rem;
  border-top: 1px solid #1f2937;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  overflow: hidden;
}

.sidebar.is-collapsed .sidebar-footer {
  flex-direction: column;
  padding: 0.65rem 0.25rem;
  gap: 0.65rem;
}

.engine-status {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  font-size: 0.72rem;
  color: #94a3b8;
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
  border: 1px solid #374151;
  color: #9ca3af;
  border-radius: 4px;
  width: 26px;
  height: 26px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.15s ease;
  font-size: 0.75rem;
}

.collapse-toggle-btn:hover {
  background-color: #1f2937;
  color: #f3f4f6;
  border-color: #4b5563;
}

/* 主內容呈現視窗 */
.main-content {
  flex: 1;
  min-width: 0;
  height: 100vh;
  overflow-y: auto;
  background-color: #f8fafc;
}
</style>
