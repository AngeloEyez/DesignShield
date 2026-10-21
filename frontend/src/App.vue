<template>
  <div class="app-layout min-h-screen flex flex-row overflow-hidden bg-surface-ground text-vscode-textMain">
    <!-- 左側可收合導航抽屜 (預設 48px 圖示軌，展開時 168px) -->
    <aside
      class="sidebar flex flex-col shrink-0 z-50 border-r border-surface-border select-none transition-[width] duration-150 bg-surface-sidebar text-vscode-textMain"
      :class="isCollapsed ? 'w-12 is-collapsed' : 'w-[168px]'"
    >
      <!-- 頂端品牌識別 (單行 ~40px 高度，移除冗長副標) -->
      <div
        v-tooltip.right="isCollapsed ? 'DesignShield 線路設計規則檢查系統' : undefined"
        class="sidebar-brand h-10 flex items-center px-3 border-b border-surface-border gap-2 overflow-hidden whitespace-nowrap"
      >
        <div class="brand-logo-wrapper flex items-center justify-center min-w-[22px]">
          <i class="pi pi-shield brand-icon text-base text-primary"></i>
        </div>
        <div v-if="!isCollapsed" class="brand-text flex items-center overflow-hidden">
          <span class="brand-title text-xs font-semibold tracking-tight text-vscode-textHeading">DesignShield</span>
        </div>
      </div>

      <!-- 導航選單列表 -->
      <nav class="sidebar-nav flex-1 p-1.5 flex flex-col gap-0.5 overflow-y-auto">
        <router-link
          to="/"
          v-tooltip.right="isCollapsed ? '總覽儀表板 (Dashboard)' : undefined"
          class="nav-item flex items-center gap-2 px-2 py-1.5 text-vscode-textSecondary no-underline rounded text-xs font-medium transition-colors whitespace-nowrap relative hover:text-vscode-textHeading hover:bg-surface-hover"
          :class="[
            isCollapsed ? 'justify-center px-0' : '',
            currentRoutePath === '/'
              ? 'active text-vscode-textHeading bg-surface-active font-semibold before:content-[\'\'] before:absolute before:left-0 before:top-1 before:bottom-1 before:w-0.5 before:bg-primary before:rounded-r'
              : ''
          ]"
        >
          <i class="pi pi-th-large nav-icon text-sm min-w-[16px] text-center"></i>
          <span v-if="!isCollapsed" class="nav-label overflow-hidden text-ellipsis">總覽儀表板</span>
        </router-link>

        <router-link
          to="/drc"
          v-tooltip.right="isCollapsed ? '線路 DRC 檢測' : undefined"
          class="nav-item flex items-center gap-2 px-2 py-1.5 text-vscode-textSecondary no-underline rounded text-xs font-medium transition-colors whitespace-nowrap relative hover:text-vscode-textHeading hover:bg-surface-hover"
          :class="[
            isCollapsed ? 'justify-center px-0' : '',
            currentRoutePath.startsWith('/drc')
              ? 'active text-vscode-textHeading bg-surface-active font-semibold before:content-[\'\'] before:absolute before:left-0 before:top-1 before:bottom-1 before:w-0.5 before:bg-primary before:rounded-r'
              : ''
          ]"
        >
          <i class="pi pi-shield nav-icon text-sm min-w-[16px] text-center"></i>
          <span v-if="!isCollapsed" class="nav-label overflow-hidden text-ellipsis">線路 DRC 檢測</span>
        </router-link>

        <router-link
          to="/rules"
          v-tooltip.right="isCollapsed ? 'DRC 規則庫管理' : undefined"
          class="nav-item flex items-center gap-2 px-2 py-1.5 text-vscode-textSecondary no-underline rounded text-xs font-medium transition-colors whitespace-nowrap relative hover:text-vscode-textHeading hover:bg-surface-hover"
          :class="[
            isCollapsed ? 'justify-center px-0' : '',
            currentRoutePath.startsWith('/rules')
              ? 'active text-vscode-textHeading bg-surface-active font-semibold before:content-[\'\'] before:absolute before:left-0 before:top-1 before:bottom-1 before:w-0.5 before:bg-primary before:rounded-r'
              : ''
          ]"
        >
          <i class="pi pi-sliders-h nav-icon text-sm min-w-[16px] text-center"></i>
          <span v-if="!isCollapsed" class="nav-label overflow-hidden text-ellipsis">規則庫管理</span>
        </router-link>

        <router-link
          to="/settings"
          v-tooltip.right="isCollapsed ? '系統環境與參數設定' : undefined"
          class="nav-item flex items-center gap-2 px-2 py-1.5 text-vscode-textSecondary no-underline rounded text-xs font-medium transition-colors whitespace-nowrap relative hover:text-vscode-textHeading hover:bg-surface-hover"
          :class="[
            isCollapsed ? 'justify-center px-0' : '',
            currentRoutePath.startsWith('/settings')
              ? 'active text-vscode-textHeading bg-surface-active font-semibold before:content-[\'\'] before:absolute before:left-0 before:top-1 before:bottom-1 before:w-0.5 before:bg-primary before:rounded-r'
              : ''
          ]"
        >
          <i class="pi pi-cog nav-icon text-sm min-w-[16px] text-center"></i>
          <span v-if="!isCollapsed" class="nav-label overflow-hidden text-ellipsis">系統環境設定</span>
        </router-link>
      </nav>

      <!-- 側邊欄底部控制區 (主題切換與收合切換，統一圖示 + Tooltip) -->
      <div
        class="sidebar-footer border-t border-surface-border flex items-center overflow-hidden"
        :class="isCollapsed ? 'flex-col py-1.5 px-1 gap-1' : 'justify-between py-1.5 px-2.5 gap-1'"
      >
        <button
          v-tooltip.right="theme === 'dark' ? '切換為溫潤淺色模式 (Light)' : '切換為護眼深色模式 (Dark)'"
          class="theme-toggle-btn flex items-center justify-center gap-1.5 bg-transparent border-0 text-vscode-textMuted hover:text-vscode-textHeading hover:bg-surface-hover rounded px-1.5 py-1 text-xs cursor-pointer transition-colors"
          :title="theme === 'dark' ? '切換為淺色模式 (Light)' : '切換為深色模式 (Dark)'"
          @click="toggleTheme"
        >
          <i :class="theme === 'dark' ? 'pi pi-sun text-vscode-yellow' : 'pi pi-moon text-primary'" class="text-xs"></i>
          <span v-if="!isCollapsed" class="theme-label text-[11px] font-medium">
            {{ theme === 'dark' ? '淺色模式' : '深色模式' }}
          </span>
        </button>

        <button
          v-tooltip.right="isCollapsed ? '展開導航文字 (168px)' : '收合為圖示軌 (48px)'"
          class="collapse-toggle-btn bg-transparent border-0 text-vscode-textMuted rounded w-6 h-6 flex items-center justify-center cursor-pointer transition-colors text-xs hover:bg-surface-hover hover:text-vscode-textHeading"
          :title="isCollapsed ? '展開側邊欄' : '收合側邊欄'"
          @click="toggleSidebar"
        >
          <i :class="isCollapsed ? 'pi pi-chevron-right' : 'pi pi-chevron-left'" class="text-[11px]"></i>
        </button>
      </div>
    </aside>

    <!-- 主內容呈現區 -->
    <main class="main-content flex-1 min-w-0 h-screen overflow-y-auto bg-surface-ground">
      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts">
/**
 * @file App.vue
 * @description DesignShield 主版面佈局，預設收合 48px 圖示軌導航 (展開 168px)、雙主題切換與路由視圖
 */

import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useTheme } from '@/composables/useTheme'

const route = useRoute()
const currentRoutePath = computed(() => route.path)
const { theme, toggleTheme } = useTheme()

// 側邊欄收合狀態：預設為收合狀態 (true)，由 LocalStorage 記憶使用者習慣
const savedCollapsed = localStorage.getItem('designshield_sidebar_collapsed')
const isCollapsed = ref<boolean>(savedCollapsed !== null ? savedCollapsed === 'true' : true)

/**
 * 切換左側導航欄展開與收合狀態
 */
const toggleSidebar = () => {
  isCollapsed.value = !isCollapsed.value
  localStorage.setItem('designshield_sidebar_collapsed', String(isCollapsed.value))
}
</script>
