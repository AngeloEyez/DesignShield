<template>
  <div class="app-layout min-h-screen flex flex-row overflow-hidden bg-[var(--vscode-bg-base,#1e1e1e)]">
    <!-- 左側 VS Code 風格可收合導航抽屜 -->
    <aside
      class="sidebar flex flex-col shrink-0 z-50 border-r border-[var(--vscode-border,#333)] select-none transition-[width] duration-200 bg-[var(--vscode-bg-sidebar,#252526)] text-[var(--vscode-text-main,#ccc)]"
      :class="isCollapsed ? 'w-[60px] is-collapsed' : 'w-[220px]'"
    >
      <!-- 頂端品牌識別 -->
      <div
        class="sidebar-brand h-12 flex items-center px-3.5 border-b border-[var(--vscode-border,#333)] gap-2.5 overflow-hidden whitespace-nowrap"
        :title="isCollapsed ? 'DesignShield' : ''"
      >
        <div class="brand-logo-wrapper flex items-center justify-center min-w-[26px]">
          <i class="pi pi-shield brand-icon text-xl text-sky-400"></i>
        </div>
        <div v-if="!isCollapsed" class="brand-text flex flex-col overflow-hidden">
          <div class="brand-title text-sm font-bold tracking-tight text-white">DesignShield</div>
          <div class="brand-subtitle text-[0.65rem] text-[var(--vscode-text-muted,#858585)]">線路設計規則檢查系統</div>
        </div>
      </div>

      <!-- 導航選單列表 -->
      <nav class="sidebar-nav flex-1 p-2 flex flex-col gap-1 overflow-y-auto">
        <router-link
          to="/"
          class="nav-item flex items-center gap-2.5 px-2.5 py-2 text-[var(--vscode-text-secondary,#999)] no-underline rounded text-xs font-medium transition-all whitespace-nowrap relative hover:text-white hover:bg-[var(--vscode-bg-hover,#2a2d2e)]"
          :class="[
            isCollapsed ? 'justify-center px-0 py-2' : '',
            currentRoutePath === '/'
              ? 'active text-white bg-[var(--vscode-bg-active,#37373d)] font-semibold before:content-[\'\'] before:absolute before:left-0 before:top-1 before:bottom-1 before:w-0.5 before:bg-[#007acc] before:rounded-r'
              : ''
          ]"
          :title="isCollapsed ? '總覽儀表板 (Dashboard)' : ''"
        >
          <i class="pi pi-th-large nav-icon text-base min-w-[18px] text-center"></i>
          <span v-if="!isCollapsed" class="nav-label overflow-hidden text-ellipsis">總覽儀表板</span>
        </router-link>

        <router-link
          to="/drc"
          class="nav-item flex items-center gap-2.5 px-2.5 py-2 text-[var(--vscode-text-secondary,#999)] no-underline rounded text-xs font-medium transition-all whitespace-nowrap relative hover:text-white hover:bg-[var(--vscode-bg-hover,#2a2d2e)]"
          :class="[
            isCollapsed ? 'justify-center px-0 py-2' : '',
            currentRoutePath.startsWith('/drc')
              ? 'active text-white bg-[var(--vscode-bg-active,#37373d)] font-semibold before:content-[\'\'] before:absolute before:left-0 before:top-1 before:bottom-1 before:w-0.5 before:bg-[#007acc] before:rounded-r'
              : ''
          ]"
          :title="isCollapsed ? '線路 DRC 任務檢測' : ''"
        >
          <i class="pi pi-shield nav-icon text-base min-w-[18px] text-center"></i>
          <span v-if="!isCollapsed" class="nav-label overflow-hidden text-ellipsis">線路 DRC 檢測</span>
        </router-link>

        <router-link
          to="/rules"
          class="nav-item flex items-center gap-2.5 px-2.5 py-2 text-[var(--vscode-text-secondary,#999)] no-underline rounded text-xs font-medium transition-all whitespace-nowrap relative hover:text-white hover:bg-[var(--vscode-bg-hover,#2a2d2e)]"
          :class="[
            isCollapsed ? 'justify-center px-0 py-2' : '',
            currentRoutePath.startsWith('/rules')
              ? 'active text-white bg-[var(--vscode-bg-active,#37373d)] font-semibold before:content-[\'\'] before:absolute before:left-0 before:top-1 before:bottom-1 before:w-0.5 before:bg-[#007acc] before:rounded-r'
              : ''
          ]"
          :title="isCollapsed ? 'DRC 規則庫管理' : ''"
        >
          <i class="pi pi-sliders-h nav-icon text-base min-w-[18px] text-center"></i>
          <span v-if="!isCollapsed" class="nav-label overflow-hidden text-ellipsis">規則庫管理</span>
        </router-link>

        <router-link
          to="/settings"
          class="nav-item flex items-center gap-2.5 px-2.5 py-2 text-[var(--vscode-text-secondary,#999)] no-underline rounded text-xs font-medium transition-all whitespace-nowrap relative hover:text-white hover:bg-[var(--vscode-bg-hover,#2a2d2e)]"
          :class="[
            isCollapsed ? 'justify-center px-0 py-2' : '',
            currentRoutePath.startsWith('/settings')
              ? 'active text-white bg-[var(--vscode-bg-active,#37373d)] font-semibold before:content-[\'\'] before:absolute before:left-0 before:top-1 before:bottom-1 before:w-0.5 before:bg-[#007acc] before:rounded-r'
              : ''
          ]"
          :title="isCollapsed ? '系統環境與參數設定' : ''"
        >
          <i class="pi pi-cog nav-icon text-base min-w-[18px] text-center"></i>
          <span v-if="!isCollapsed" class="nav-label overflow-hidden text-ellipsis">系統環境設定</span>
        </router-link>
      </nav>

      <!-- 側邊欄底部控制區 -->
      <div
        class="sidebar-footer border-t border-[var(--vscode-border,#333)] flex items-center overflow-hidden"
        :class="isCollapsed ? 'flex-col p-2 px-1 gap-2' : 'justify-between p-2 px-3 gap-2'"
      >
        <div class="engine-status flex items-center gap-2 text-[0.72rem] text-[var(--vscode-text-muted,#858585)] whitespace-nowrap" :title="isCollapsed ? 'DBOS Engine: 就緒' : ''">
          <span class="status-dot w-[7px] h-[7px] rounded-full bg-emerald-500 shadow-[0_0_6px_#10b981] inline-block shrink-0"></span>
          <span v-if="!isCollapsed" class="status-label overflow-hidden text-ellipsis">DBOS Engine: 就緒</span>
        </div>

        <button
          class="collapse-toggle-btn bg-transparent border border-[#3c3c3c] text-[#999999] rounded w-6 h-6 flex items-center justify-center cursor-pointer transition-all text-xs hover:bg-[#333333] hover:text-white hover:border-[#555555]"
          :title="isCollapsed ? '展開側邊欄' : '收合側邊欄'"
          @click="toggleSidebar"
        >
          <i :class="isCollapsed ? 'pi pi-chevron-right' : 'pi pi-chevron-left'"></i>
        </button>
      </div>
    </aside>

    <!-- 主內容呈現區 -->
    <main class="main-content flex-1 min-w-0 h-screen overflow-y-auto bg-[var(--vscode-bg-base,#1e1e1e)]">
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
