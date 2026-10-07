<template>
  <div class="drawer-step-content">
    <div class="drawer-stat-banner">
      <div class="banner-stat">
        <span class="stat-num">{{ archiveDetails?.file_count || 0 }}</span>
        <span class="stat-name">解壓檔案數</span>
      </div>
      <div class="banner-stat">
        <span class="stat-num">{{ formatBytes(archiveDetails?.total_bytes || 0) }}</span>
        <span class="stat-name">解壓總容量</span>
      </div>
      <div class="banner-stat">
        <span class="stat-num text-green">通過</span>
        <span class="stat-name">OrCAD XML 格式</span>
      </div>
    </div>

    <h4 class="content-subtitle">解壓中繼目錄檔案列表</h4>
    <table class="drawer-table">
      <thead>
        <tr>
          <th>檔案名稱</th>
          <th>相對路徑</th>
          <th>檔案大小</th>
          <th>格式類型</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="f in archiveFilesList" :key="f.relative_path">
          <td>
            <i class="pi pi-file text-cyan mr-1"></i>
            <strong>{{ f.filename }}</strong>
          </td>
          <td><code>{{ f.relative_path }}</code></td>
          <td>{{ formatBytes(f.size_bytes) }}</td>
          <td>
            <span v-if="f.is_xml" class="badge-tag tag-green">OrCAD XML</span>
            <span v-else-if="f.is_netlist" class="badge-tag tag-blue">Netlist</span>
            <span v-else class="badge-tag">一般中繼</span>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup lang="ts">
/**
 * @file Step1ArchiveDrawer.vue
 * @description TaskMonitorView 抽屜 Step 1：解壓縮與格式預檢檔案清單
 */

import type { TaskArchiveDetails, TaskArchiveFile } from '@/types/task'

interface Props {
  archiveDetails: TaskArchiveDetails | null
  archiveFilesList: TaskArchiveFile[]
}

defineProps<Props>()

const formatBytes = (bytes: number): string => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}
</script>

<style scoped>
.drawer-step-content {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.drawer-stat-banner {
  display: flex;
  background-color: var(--vscode-bg-panel, #252526);
  border-radius: 6px;
  padding: 1rem;
  border: 1px solid var(--vscode-border, #333333);
  justify-content: space-around;
  text-align: center;
}

.banner-stat {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.stat-num {
  font-size: 1.45rem;
  font-weight: 700;
  color: var(--vscode-text-heading, #ffffff);
}

.stat-name {
  font-size: 0.75rem;
  color: var(--vscode-text-muted, #858585);
}

.text-green {
  color: var(--vscode-green, #89d185);
}

.text-cyan {
  color: var(--vscode-cyan, #4ec9b0);
}

.mr-1 {
  margin-right: 0.25rem;
}

.content-subtitle {
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--vscode-text-heading, #ffffff);
  margin: 0 0 0.5rem 0;
}

.drawer-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.8rem;
  text-align: left;
}

.drawer-table thead th {
  background-color: var(--vscode-bg-header, #2d2d2d);
  color: var(--vscode-text-secondary, #999999);
  padding: 0.6rem 0.85rem;
  border-bottom: 1px solid var(--vscode-border, #333333);
  font-weight: 600;
}

.drawer-table tbody td {
  padding: 0.65rem 0.85rem;
  border-bottom: 1px solid var(--vscode-border, #333333);
  vertical-align: middle;
}

.badge-tag {
  display: inline-block;
  font-size: 0.7rem;
  padding: 0.15rem 0.45rem;
  border-radius: 3px;
  background-color: var(--vscode-bg-header, #2d2d2d);
  color: var(--vscode-text-secondary, #999999);
  border: 1px solid var(--vscode-border, #333333);
}

.tag-green {
  background-color: rgba(137, 209, 133, 0.15);
  color: #89d185;
  border-color: rgba(137, 209, 133, 0.3);
}

.tag-blue {
  background-color: rgba(0, 122, 204, 0.15);
  color: #38bdf8;
  border-color: rgba(0, 122, 204, 0.3);
}
</style>
