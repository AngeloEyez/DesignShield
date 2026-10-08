<template>
  <div class="drawer-step-content flex flex-col gap-4">
    <div class="drawer-stat-banner flex justify-around text-center p-3.5 rounded-md bg-surface-card border border-surface-border">
      <div class="banner-stat flex flex-col gap-1">
        <span class="stat-num text-xl font-bold text-surface-900 dark:text-surface-0">{{ archiveDetails?.file_count || 0 }}</span>
        <span class="stat-name text-xs text-surface-400">解壓檔案數</span>
      </div>
      <div class="banner-stat flex flex-col gap-1">
        <span class="stat-num text-xl font-bold text-surface-900 dark:text-surface-0">{{ formatBytes(archiveDetails?.total_bytes || 0) }}</span>
        <span class="stat-name text-xs text-surface-400">解壓總容量</span>
      </div>
      <div class="banner-stat flex flex-col gap-1">
        <span class="stat-num text-xl font-bold text-green-400">通過</span>
        <span class="stat-name text-xs text-surface-400">OrCAD XML 格式</span>
      </div>
    </div>

    <h4 class="content-subtitle text-sm font-bold text-surface-900 dark:text-surface-0 m-0">解壓中繼目錄檔案列表</h4>
    <div class="overflow-x-auto border border-surface-border rounded-md">
      <table class="drawer-table w-full border-collapse text-xs text-left">
        <thead>
          <tr class="bg-surface-ground border-b border-surface-border">
            <th class="p-2.5 font-semibold text-surface-400">檔案名稱</th>
            <th class="p-2.5 font-semibold text-surface-400">相對路徑</th>
            <th class="p-2.5 font-semibold text-surface-400">檔案大小</th>
            <th class="p-2.5 font-semibold text-surface-400">格式類型</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="f in archiveFilesList" :key="f.relative_path" class="border-b border-surface-border/50 hover:bg-surface-hover/30 transition-colors">
            <td class="p-2.5 text-surface-200">
              <i class="pi pi-file text-sky-400 mr-1.5"></i>
              <strong>{{ f.filename }}</strong>
            </td>
            <td class="p-2.5"><code class="font-mono text-sky-300 text-xs">{{ f.relative_path }}</code></td>
            <td class="p-2.5 text-surface-300">{{ formatBytes(f.size_bytes) }}</td>
            <td class="p-2.5">
              <span v-if="f.is_xml" class="badge-tag tag-green text-[10px] px-1.5 py-0.5 rounded border border-green-400/30 bg-green-500/10 text-green-400">OrCAD XML</span>
              <span v-else-if="f.is_netlist" class="badge-tag tag-blue text-[10px] px-1.5 py-0.5 rounded border border-blue-400/30 bg-blue-500/10 text-blue-400">Netlist</span>
              <span v-else class="badge-tag text-[10px] px-1.5 py-0.5 rounded border border-surface-border bg-surface-ground text-surface-400">一般中繼</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
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
