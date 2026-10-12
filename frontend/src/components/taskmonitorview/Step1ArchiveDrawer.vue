<template>
  <div class="drawer-step-content flex flex-col gap-4">
    <!-- 頂部解壓統計指標列 -->
    <div class="drawer-stat-banner flex justify-around text-center p-3.5 rounded-md bg-[#252526] border border-[#333333]">
      <div class="banner-stat flex flex-col gap-1">
        <span class="stat-num text-xl font-bold text-white">{{ archiveDetails?.file_count || 0 }}</span>
        <span class="stat-name text-xs text-[#858585]">解壓檔案數</span>
      </div>
      <div class="banner-stat flex flex-col gap-1">
        <span class="stat-num text-xl font-bold text-white">{{ formatBytes(archiveDetails?.total_bytes || 0) }}</span>
        <span class="stat-name text-xs text-[#858585]">解壓總容量</span>
      </div>
      <div class="banner-stat flex flex-col gap-1">
        <span class="stat-num text-xl font-bold text-emerald-400">{{ (archiveDetails?.file_count || 0) > 0 ? '通過' : '—' }}</span>
        <span class="stat-name text-xs text-[#858585]">OrCAD XML 格式</span>
      </div>
    </div>

    <div class="file-list-section flex flex-col gap-2">
      <h4 class="content-subtitle text-xs font-bold text-white m-0">解壓中繼目錄檔案列表</h4>
      
      <!-- 有檔案時展示資料表格 -->
      <div v-if="archiveFilesList && archiveFilesList.length > 0" class="overflow-x-auto border border-[#333333] rounded-md bg-[#252526]">
        <table class="drawer-table w-full border-collapse text-xs text-left">
          <thead>
            <tr class="bg-[#2d2d2d] border-b border-[#333333]">
              <th class="p-2.5 font-semibold text-[#999999]">檔案名稱</th>
              <th class="p-2.5 font-semibold text-[#999999]">相對路徑</th>
              <th class="p-2.5 font-semibold text-[#999999]">檔案大小</th>
              <th class="p-2.5 font-semibold text-[#999999]">格式類型</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="f in archiveFilesList" :key="f.relative_path" class="border-b border-[#333333]/50 hover:bg-[#2a2d2e] transition-colors">
              <td class="p-2.5 text-[#cccccc]">
                <i class="pi pi-file text-sky-400 mr-1.5"></i>
                <strong>{{ f.filename }}</strong>
              </td>
              <td class="p-2.5"><code class="font-mono text-sky-300 text-xs">{{ f.relative_path }}</code></td>
              <td class="p-2.5 text-[#999999]">{{ formatBytes(f.size_bytes) }}</td>
              <td class="p-2.5">
                <span v-if="f.is_xml" class="badge-tag tag-green text-[10px] px-1.5 py-0.5 rounded border border-emerald-500/30 bg-emerald-500/10 text-emerald-400">OrCAD XML</span>
                <span v-else-if="f.is_netlist" class="badge-tag tag-blue text-[10px] px-1.5 py-0.5 rounded border border-sky-400/30 bg-sky-500/10 text-sky-400">Netlist</span>
                <span v-else class="badge-tag text-[10px] px-1.5 py-0.5 rounded border border-[#3c3c3c] bg-[#1e1e1e] text-[#858585]">一般中繼</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 無檔案時的 Empty State -->
      <div v-else class="archive-empty-state border border-[#333333] rounded-md p-8 flex flex-col items-center justify-center gap-2 text-center bg-[#252526]">
        <i class="pi pi-folder-open text-3xl text-[#555555]"></i>
        <span class="text-xs text-[#858585]">目前尚無解壓中繼目錄檔案</span>
        <span class="text-[11px] text-[#666666]">上傳並執行解壓後，此處將自動列出檔案結構與格式預檢明細</span>
      </div>
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
