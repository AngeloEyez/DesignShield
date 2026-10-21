<template>
  <div class="drawer-step-content flex flex-col gap-3">
    <!-- 頂部解壓統計單行橫條 (Compact Metric Strip，高 ~38px) -->
    <div class="drawer-stat-banner grid grid-cols-3 divide-x divide-surface-border bg-surface-panel border border-surface-border rounded">
      <div class="banner-stat px-3 py-1.5 flex items-center justify-between">
        <span class="stat-name text-xs text-vscode-textSecondary">解壓檔案數</span>
        <span class="stat-num text-sm font-semibold text-vscode-textHeading font-mono">{{ archiveDetails?.file_count || 0 }}</span>
      </div>
      <div class="banner-stat px-3 py-1.5 flex items-center justify-between">
        <span class="stat-name text-xs text-vscode-textSecondary">解壓總容量</span>
        <span class="stat-num text-sm font-semibold text-vscode-textHeading font-mono">{{ formatBytes(archiveDetails?.total_bytes || 0) }}</span>
      </div>
      <div class="banner-stat px-3 py-1.5 flex items-center justify-between">
        <span class="stat-name text-xs text-vscode-textSecondary">OrCAD XML 格式</span>
        <span class="stat-num text-xs font-semibold text-vscode-green">{{ (archiveDetails?.file_count || 0) > 0 ? '通過' : '—' }}</span>
      </div>
    </div>

    <div class="file-list-section flex flex-col gap-2">
      <h4 class="content-subtitle text-xs font-medium text-vscode-textHeading m-0">解壓中繼目錄檔案列表</h4>

      <!-- 有檔案時展示 PrimeVue DataTable -->
      <div v-if="archiveFilesList && archiveFilesList.length > 0" class="overflow-x-auto border border-surface-border rounded bg-surface-panel">
        <DataTable
          :value="archiveFilesList"
          data-key="relative_path"
          size="small"
          class="drawer-table w-full text-xs [&_td]:!py-1.5 [&_td]:!px-3 [&_th]:!py-1.5 [&_th]:!px-3 [&_th]:!bg-surface-header [&_th]:!text-vscode-textSecondary [&_th]:!font-medium"
        >
          <Column header="檔案名稱">
            <template #body="{ data: f }">
              <div class="flex items-center gap-1.5 text-vscode-textHeading font-medium">
                <i class="pi pi-file text-primary text-xs"></i>
                <span>{{ f.filename }}</span>
              </div>
            </template>
          </Column>
          <Column header="相對路徑">
            <template #body="{ data: f }">
              <code class="font-mono text-primary text-xs">{{ f.relative_path }}</code>
            </template>
          </Column>
          <Column header="檔案大小">
            <template #body="{ data: f }">
              <span class="text-vscode-textMuted font-mono text-[11px]">{{ formatBytes(f.size_bytes) }}</span>
            </template>
          </Column>
          <Column header="格式類型">
            <template #body="{ data: f }">
              <span v-if="f.is_xml" class="badge-tag tag-green text-[10px] px-1.5 py-0.2 rounded border border-primary/30 bg-primary/10 text-primary">OrCAD XML</span>
              <span v-else-if="f.is_netlist" class="badge-tag tag-blue text-[10px] px-1.5 py-0.2 rounded border border-primary/30 bg-primary/10 text-primary">Netlist</span>
              <span v-else class="badge-tag text-[10px] px-1.5 py-0.2 rounded border border-surface-border bg-surface-ground text-vscode-textMuted">一般中繼</span>
            </template>
          </Column>
        </DataTable>
      </div>

      <!-- 無檔案時的 Empty State -->
      <div v-else class="archive-empty-state border border-surface-border rounded p-6 flex flex-col items-center justify-center gap-1.5 text-center bg-surface-panel">
        <i class="pi pi-folder-open text-xl text-vscode-textMuted"></i>
        <span class="text-xs text-vscode-textSecondary">目前尚無解壓中繼目錄檔案</span>
        <span class="text-[11px] text-vscode-textMuted">上傳並執行解壓後，此處將自動列出檔案結構與格式預檢明細</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * @file Step1ArchiveDrawer.vue
 * @description TaskMonitorView 抽屜 Step 1：解壓縮與格式預檢檔案清單 (單行數據橫條 + PrimeVue DataTable)
 */

import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
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
