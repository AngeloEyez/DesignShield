<template>
  <div class="settings-page-container max-w-[1200px] mx-auto px-5 py-6 pb-20 flex flex-col gap-5 text-surface-200">
    <!-- 頂部頁頭導航與動作列 -->
    <div class="settings-header flex flex-col md:flex-row justify-between items-start gap-4 bg-surface-card p-4 md:p-6 rounded-lg border border-surface-border shadow-md">
      <div class="header-left flex items-start gap-4">
        <Button
          label="返回 DRC 檢測"
          icon="pi pi-arrow-left"
          severity="secondary"
          size="small"
          class="back-btn shrink-0"
          @click="goBack"
        />
        <div class="header-titles">
          <h1 class="page-title text-xl md:text-2xl font-bold m-0 mb-1 flex items-center text-surface-900 dark:text-surface-0">
            <i class="pi pi-cog text-primary mr-2"></i>
            系統環境與參數設定 (System Settings)
          </h1>
          <p class="page-subtitle text-surface-400 text-xs md:text-sm m-0">
            直接綁定至系統 <code class="bg-surface-ground px-1 py-0.5 rounded text-sky-400 font-mono">.env</code> 設定檔，支援網路主機、本地 LLM、Langfuse 觀測與磁碟垃圾清理管理。
          </p>
        </div>
      </div>

      <div class="header-actions flex flex-wrap gap-2.5">
        <Button
          label="重設未儲存變更"
          icon="pi pi-undo"
          severity="secondary"
          :disabled="!hasUnsavedChanges || isSaving"
          @click="resetChanges"
        />
        <Button
          label="儲存設定"
          icon="pi pi-save"
          severity="primary"
          :loading="isSaving"
          :disabled="!hasUnsavedChanges"
          @click="saveSettings"
        />
        <Button
          label="重啟服務器"
          icon="pi pi-power-off"
          severity="danger"
          :loading="isRestarting"
          @click="confirmRestartServer"
        />
      </div>
    </div>

    <!-- 需重啟伺服器之警示提示橫幅 -->
    <div v-if="restartPromptVisible" class="alert-banner warning-banner flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 p-4 rounded-lg bg-amber-500/15 border border-amber-500/30 text-amber-300">
      <div class="alert-content flex items-start gap-3">
        <i class="pi pi-exclamation-triangle alert-icon text-xl text-amber-400 mt-0.5"></i>
        <div>
          <div class="alert-title font-semibold text-sm">系統提示：部分設定變更需要重新啟動伺服器才能完全生效</div>
          <div class="alert-desc text-xs text-amber-200 mt-1 leading-relaxed">
            受影響的設定項目包含：<strong>{{ pendingRestartReasons.join(', ') }}</strong>。
            您可以點擊右側按鈕立即安全重啟後端服務。
          </div>
        </div>
      </div>
      <Button
        label="立即重啟服務器"
        icon="pi pi-refresh"
        severity="warn"
        size="small"
        :loading="isRestarting"
        @click="confirmRestartServer"
      />
    </div>

    <!-- 儲存成功通知橫幅 -->
    <div v-if="saveSuccessMessage" class="alert-banner success-banner flex items-center justify-between p-3.5 rounded-lg bg-green-500/15 border border-green-500/30 text-green-300 text-sm">
      <div class="alert-content flex items-center gap-2">
        <i class="pi pi-check-circle alert-icon text-green-400"></i>
        <span>{{ saveSuccessMessage }}</span>
      </div>
      <button class="banner-close bg-transparent border-0 text-inherit cursor-pointer p-1" @click="saveSuccessMessage = ''">
        <i class="pi pi-times"></i>
      </button>
    </div>

    <!-- 磁碟儲存空間監控與垃圾清理卡片 -->
    <div class="settings-card storage-card bg-surface-card border border-surface-border rounded-lg p-5 flex flex-col gap-4 shadow-sm">
      <div class="card-header flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
        <div class="card-title flex items-center text-primary text-base font-semibold m-0 text-surface-900 dark:text-surface-0">
          <i class="pi pi-database text-indigo-400 mr-2 text-lg"></i>
          <h3 class="m-0 text-base font-semibold text-surface-900 dark:text-surface-0">磁碟儲存空間監控與垃圾回收 (Storage & Garbage Collection)</h3>
        </div>
        <div class="cleanup-actions flex gap-2">
          <Button
            label="重新整理空間指標"
            icon="pi pi-refresh"
            severity="secondary"
            size="small"
            :loading="isLoadingStats"
            @click="loadStorageStats"
          />
          <Button
            label="立即清理過期任務與孤兒檔案"
            icon="pi pi-trash"
            severity="danger"
            size="small"
            :loading="isCleaning"
            @click="triggerCleanup"
          />
        </div>
      </div>

      <div class="storage-metrics-grid grid grid-cols-2 md:grid-cols-4 gap-3">
        <div class="metric-box bg-surface-ground border border-surface-border rounded p-3 flex flex-col items-center text-center">
          <span class="metric-label text-xs text-surface-400 mb-1">上傳原始封裝 (Uploads)</span>
          <span class="metric-value text-base font-bold text-surface-900 dark:text-surface-0">{{ storageStats.uploads.file_count }} 檔</span>
          <span class="metric-sub text-[11px] text-surface-400 mt-0.5">{{ formatBytes(storageStats.uploads.total_bytes) }}</span>
        </div>
        <div class="metric-box bg-surface-ground border border-surface-border rounded p-3 flex flex-col items-center text-center">
          <span class="metric-label text-xs text-surface-400 mb-1">解壓中繼暫存 (Staging)</span>
          <span class="metric-value text-base font-bold text-surface-900 dark:text-surface-0">{{ storageStats.staging.file_count }} 檔</span>
          <span class="metric-sub text-[11px] text-surface-400 mt-0.5">{{ formatBytes(storageStats.staging.total_bytes) }}</span>
        </div>
        <div class="metric-box bg-surface-ground border border-surface-border rounded p-3 flex flex-col items-center text-center">
          <span class="metric-label text-xs text-surface-400 mb-1">DRC 檢查報告 (Reports)</span>
          <span class="metric-value text-base font-bold text-surface-900 dark:text-surface-0">{{ storageStats.reports.file_count }} 檔</span>
          <span class="metric-sub text-[11px] text-surface-400 mt-0.5">{{ formatBytes(storageStats.reports.total_bytes) }}</span>
        </div>
        <div class="metric-box highlight bg-primary/10 border border-primary/30 rounded p-3 flex flex-col items-center text-center">
          <span class="metric-label text-xs text-surface-400 mb-1">總磁碟佔用</span>
          <span class="metric-value text-base font-bold text-primary">{{ storageStats.total_mb }} MB</span>
          <span class="metric-sub text-[11px] text-surface-400 mt-0.5">{{ storageStats.total_files }} 個檔案總計</span>
        </div>
      </div>

      <div v-if="cleanupMessage" class="cleanup-alert p-2.5 rounded bg-teal-500/15 border border-teal-500/30 text-teal-300 text-xs flex items-center gap-1.5">
        <i class="pi pi-info-circle mr-1"></i>
        <span>{{ cleanupMessage }}</span>
      </div>
    </div>

    <!-- 設定分類切換標籤 -->
    <div class="category-tabs flex gap-2 overflow-x-auto pb-2 border-b border-surface-border">
      <button
        class="tab-btn px-3.5 py-2 text-xs font-semibold rounded-md border border-surface-border bg-surface-card cursor-pointer transition-colors whitespace-nowrap"
        :class="selectedCategory === 'all' ? 'bg-primary/20 border-primary text-primary-contrast dark:text-primary-300' : 'text-surface-400 hover:text-surface-100 hover:bg-surface-hover'"
        @click="selectedCategory = 'all'"
      >
        <i class="pi pi-list mr-1"></i>
        全部設定 ({{ envItems.length }})
      </button>
      <button
        v-for="cat in categories"
        :key="cat.id"
        class="tab-btn px-3.5 py-2 text-xs font-semibold rounded-md border border-surface-border bg-surface-card cursor-pointer transition-colors whitespace-nowrap"
        :class="selectedCategory === cat.id ? 'bg-primary/20 border-primary text-primary-contrast dark:text-primary-300' : 'text-surface-400 hover:text-surface-100 hover:bg-surface-hover'"
        @click="selectedCategory = cat.id"
      >
        <i :class="cat.icon + ' mr-1'"></i>
        {{ cat.name }} ({{ getCategoryItems(cat.id).length }})
      </button>
    </div>

    <!-- 設定項目列表卡片 -->
    <div class="settings-content-grid flex flex-col gap-5">
      <div
        v-for="cat in displayCategories"
        :key="cat.id"
        class="category-group-card bg-surface-card border border-surface-border rounded-lg p-5 flex flex-col gap-4 shadow-sm"
      >
        <div class="group-header flex items-center gap-2.5 pb-3 border-b border-surface-border">
          <i :class="cat.icon" class="group-icon text-lg text-primary"></i>
          <h3 class="m-0 text-base font-semibold text-surface-900 dark:text-surface-0">{{ cat.name }}</h3>
          <span class="env-source-tag text-[11px] font-mono px-2 py-0.5 rounded bg-surface-ground text-surface-400 border border-surface-border ml-auto">綁定至 .env 檔案</span>
        </div>

        <!-- LiteLLM 服務提供商快捷切換橫幅 (Gemini / OpenRouter / 本地 / OpenAI 等) -->
        <div v-if="cat.id === 'llm'" class="provider-switch-banner p-3.5 rounded-md bg-surface-ground border border-surface-border flex flex-col gap-2.5">
          <div class="provider-switch-header flex flex-col sm:flex-row justify-between sm:items-center gap-1">
            <span class="provider-switch-title text-xs font-semibold text-surface-200 flex items-center">
              <i class="pi pi-sparkles text-primary mr-1"></i>
              切換 LiteLLM 服務提供者 (Provider)：
            </span>
            <span class="provider-switch-hint text-[11px] text-surface-400">點選後自動載入該服務推薦模型與預設端點設定</span>
          </div>
          <div class="provider-chips-grid grid grid-cols-2 sm:grid-cols-4 gap-2">
            <button
              v-for="p in supportedProviders"
              :key="p.id"
              type="button"
              class="provider-badge-btn p-2 rounded border cursor-pointer flex flex-col items-center text-center transition-colors"
              :class="currentProvider === p.id ? 'bg-primary/20 border-primary text-primary-contrast dark:text-primary-300 font-semibold shadow-sm' : 'bg-surface-card border-surface-border text-surface-400 hover:text-surface-100 hover:bg-surface-hover'"
              @click="selectProvider(p.id)"
            >
              <i :class="p.icon" class="text-sm mb-1"></i>
              <span class="provider-name text-xs">{{ p.name }}</span>
              <span class="provider-tag text-[10px] text-surface-400 mt-0.5">{{ p.tag }}</span>
            </button>
          </div>
        </div>

        <div class="settings-items-list flex flex-col gap-4">
          <div
            v-for="item in getCategoryItems(cat.id)"
            :key="item.key"
            class="setting-item-row p-4 rounded-md border bg-surface-ground/50 flex flex-col md:flex-row justify-between items-start md:items-center gap-4 transition-colors"
            :class="isItemChanged(item.key) ? 'border-amber-500/50 bg-amber-500/5' : 'border-surface-border'"
          >
            <!-- 左側標籤與說明 -->
            <div class="setting-item-meta flex-1 flex flex-col gap-1.5">
              <div class="meta-title-row flex items-center gap-2 flex-wrap">
                <span class="item-label font-semibold text-sm text-surface-900 dark:text-surface-0">{{ item.label }}</span>
                <code class="env-key-badge font-mono text-xs px-2 py-0.5 rounded bg-surface-ground border border-surface-border text-sky-400 font-bold">{{ item.key }}</code>
                <span v-if="item.requires_restart" class="badge-restart text-[10px] px-1.5 py-0.5 rounded bg-amber-500/15 border border-amber-500/30 text-amber-300 font-semibold flex items-center gap-1">
                  <i class="pi pi-refresh"></i> 需重啟生效
                </span>
                <span v-else class="badge-dynamic text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 font-semibold flex items-center gap-1">
                  <i class="pi pi-bolt"></i> 動態生效
                </span>
                <span v-if="isItemChanged(item.key)" class="badge-modified text-[10px] px-1.5 py-0.5 rounded bg-amber-400 text-slate-900 font-bold">
                  已修改
                </span>
              </div>
              <p class="item-description text-xs text-surface-400 m-0 leading-relaxed whitespace-pre-line">{{ item.description }}</p>
              <div v-if="item.example" class="item-example-box text-xs text-surface-400 flex items-center gap-1 font-mono">
                <span class="example-label text-surface-500">範例格式：</span>
                <code class="text-sky-300 bg-surface-ground px-1 py-0.5 rounded border border-surface-border">{{ item.example }}</code>
              </div>
            </div>

            <!-- 右側輸入控制項 -->
            <div class="setting-item-control w-full md:w-96 flex flex-col gap-2 shrink-0">
              <!-- 若為 LITELLM_PROVIDER，提供下拉切換選單 -->
              <div v-if="item.key === 'LITELLM_PROVIDER'" class="input-wrapper relative flex items-center w-full">
                <select
                  v-model="formValues[item.key]"
                  class="setting-input provider-select w-full px-3 py-1.5 rounded border border-surface-border bg-surface-ground text-surface-900 dark:text-surface-100 text-xs font-mono focus:outline-none focus:border-primary transition-colors cursor-pointer"
                  @change="selectProvider(formValues[item.key])"
                >
                  <option v-for="p in supportedProviders" :key="p.id" :value="p.id">
                    {{ p.name }} ({{ p.tag }}) - provider: {{ p.id }}
                  </option>
                </select>
              </div>

              <!-- 若為 LOCAL_LLM_MODEL，提供即時向伺服器查詢下拉選單並同時支援手動輸入 -->
              <div v-else-if="item.key === 'LOCAL_LLM_MODEL'" class="model-select-wrapper flex flex-col gap-2 w-full">
                <div class="input-wrapper relative flex items-center w-full">
                  <input
                    v-model="formValues[item.key]"
                    type="text"
                    class="setting-input model-input w-full px-3 py-1.5 rounded border border-surface-border bg-surface-ground text-surface-900 dark:text-surface-100 text-xs font-mono focus:outline-none focus:border-primary transition-colors"
                    list="llm-model-options"
                    :placeholder="item.default || item.example || '可直接輸入或自下拉選單選擇'"
                    @input="handleInput(item.key)"
                  />
                  <datalist id="llm-model-options">
                    <option v-for="m in availableLlmModels" :key="m" :value="m">{{ m }}</option>
                  </datalist>
                  <button
                    type="button"
                    class="btn-fetch-models px-2.5 py-1 text-xs rounded border border-surface-border bg-surface-card hover:bg-surface-hover text-surface-300 cursor-pointer ml-2 flex items-center gap-1 shrink-0 transition-colors"
                    :title="isFetchingModels ? '正在向伺服器查詢可用模型...' : '即時向伺服器查詢可用模型清單'"
                    :disabled="isFetchingModels"
                    @click="queryLlmModels(true)"
                  >
                    <i :class="isFetchingModels ? 'pi pi-spin pi-spinner' : 'pi pi-refresh'"></i>
                    <span>{{ isFetchingModels ? '查詢中...' : '重新整理' }}</span>
                  </button>
                </div>

                <!-- 下拉選單選擇器 -->
                <div class="model-dropdown-row flex items-center gap-2 text-xs">
                  <label class="model-dropdown-label text-surface-400 shrink-0" for="llm-model-select">
                    <i class="pi pi-list mr-1"></i>
                    下拉選單：
                  </label>
                  <select
                    id="llm-model-select"
                    class="model-select w-full px-2 py-1 rounded border border-surface-border bg-surface-ground text-surface-900 dark:text-surface-100 text-xs font-mono focus:outline-none focus:border-primary transition-colors cursor-pointer"
                    :disabled="isFetchingModels"
                    @change="onModelSelectChange($event)"
                  >
                    <option value="" disabled :selected="!availableLlmModels.includes(formValues[item.key])">
                      {{ availableLlmModels.length > 0 ? `-- 點擊展開可選模型 (共 ${availableLlmModels.length} 個) --` : '-- 尚無模型或點擊右上方重新整理查詢 --' }}
                    </option>
                    <option
                      v-for="m in availableLlmModels"
                      :key="m"
                      :value="m"
                      :selected="formValues[item.key] === m"
                    >
                      {{ m }}
                    </option>
                  </select>
                </div>

                <!-- 可用模型快速標籤 (Chips) -->
                <div v-if="availableLlmModels.length > 0" class="model-chips-list flex flex-wrap items-center gap-1.5 text-xs mt-1">
                  <span class="chips-label text-[11px] text-surface-400">可用模型：</span>
                  <span
                    v-for="m in availableLlmModels"
                    :key="m"
                    class="model-chip px-2 py-0.5 rounded border border-surface-border bg-surface-card text-surface-300 text-xs cursor-pointer hover:bg-surface-hover transition-colors font-mono"
                    :class="{ 'bg-primary/20 border-primary text-primary-contrast dark:text-primary-300 font-semibold': formValues[item.key] === m }"
                    @click="applyModel(m)"
                  >
                    {{ m }}
                    <i v-if="formValues[item.key] === m" class="pi pi-check ml-1"></i>
                  </span>
                </div>

                <!-- 查詢狀態提示 -->
                <div v-if="llmModelStatusMessage" class="model-status-hint text-xs flex items-center gap-1" :class="llmModelStatusSuccess ? 'text-teal-300' : 'text-surface-400'">
                  <i :class="llmModelStatusSuccess ? 'pi pi-check-circle text-teal-400' : 'pi pi-info-circle text-surface-400'" class="mr-1"></i>
                  <span>{{ llmModelStatusMessage }}</span>
                </div>
              </div>

              <!-- 一般設定項目輸入控制項 -->
              <div v-else class="input-wrapper relative flex items-center w-full">
                <input
                  v-if="!item.is_secret || visibleSecrets[item.key]"
                  v-model="formValues[item.key]"
                  type="text"
                  class="setting-input w-full px-3 py-1.5 rounded border border-surface-border bg-surface-ground text-surface-900 dark:text-surface-100 text-xs font-mono focus:outline-none focus:border-primary transition-colors"
                  :placeholder="item.default || item.example || '請輸入設定值'"
                  @input="handleInput(item.key)"
                  @blur="item.key === 'LOCAL_LLM_URL' ? queryLlmModels(false) : null"
                />
                <input
                  v-else
                  v-model="formValues[item.key]"
                  type="password"
                  class="setting-input w-full px-3 py-1.5 rounded border border-surface-border bg-surface-ground text-surface-900 dark:text-surface-100 text-xs font-mono focus:outline-none focus:border-primary transition-colors"
                  :placeholder="item.default || item.example || '請輸入設定值'"
                  @input="handleInput(item.key)"
                />
                <button
                  v-if="item.is_secret"
                  type="button"
                  class="btn-toggle-secret absolute right-2 text-surface-400 hover:text-surface-200 cursor-pointer bg-transparent border-0 text-sm"
                  :title="visibleSecrets[item.key] ? '隱藏金鑰' : '顯示金鑰'"
                  @click="toggleSecret(item.key)"
                >
                  <i :class="visibleSecrets[item.key] ? 'pi pi-eye-slash' : 'pi pi-eye'"></i>
                </button>
              </div>

              <div v-if="isItemChanged(item.key)" class="original-val-hint text-[11px] text-surface-400">
                原設定值：<code class="bg-surface-ground px-1 py-0.5 rounded text-amber-300 font-mono">{{ originalValues[item.key] || '(空值)' }}</code>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 底部固定儲存浮動列 (當有未儲存變更時浮現) -->
    <div v-if="hasUnsavedChanges" class="floating-save-bar fixed bottom-4 left-1/2 -translate-x-1/2 z-50 bg-surface-overlay/95 backdrop-blur border border-primary/40 rounded-xl px-6 py-3 shadow-2xl flex items-center gap-6 text-sm text-surface-100">
      <div class="save-bar-info flex items-center gap-2">
        <i class="pi pi-info-circle text-primary"></i>
        <span>您有 <strong>{{ changedKeysCount }}</strong> 個設定項目尚未儲存至 <code class="font-mono text-sky-300">.env</code></span>
      </div>
      <div class="save-bar-actions flex items-center gap-2.5">
        <Button label="放棄變更" severity="secondary" size="small" @click="resetChanges" />
        <Button
          label="立即儲存設定"
          icon="pi pi-check"
          severity="primary"
          size="small"
          :loading="isSaving"
          @click="saveSettings"
        />
      </div>
    </div>

    <!-- 重啟確認對話框 -->
    <div v-if="showRestartConfirm" class="modal-backdrop fixed inset-0 bg-black/70 backdrop-blur-sm z-[999] flex items-center justify-center p-4" @click.self="showRestartConfirm = false">
      <div class="modal-dialog bg-surface-card border border-surface-border rounded-lg max-w-md w-full p-6 flex flex-col gap-4 shadow-2xl text-surface-200">
        <div class="dialog-header flex items-center gap-2 text-red-400 text-lg font-bold">
          <i class="pi pi-power-off text-red-500"></i>
          <h3 class="m-0 text-lg font-bold text-surface-900 dark:text-surface-0">確認重啟伺服器？</h3>
        </div>
        <div class="dialog-body flex flex-col gap-2 text-sm text-surface-300">
          <p class="m-0 leading-relaxed">您即將發送指令重新啟動 DesignShield 後端伺服器服務。</p>
          <p class="text-surface-400 text-xs m-0 leading-relaxed">
            重啟期間 API 連線將暫時中斷約 5~10 秒，頁面會自動監測連線狀況並在服務恢復時自動重新連線。
          </p>
        </div>
        <div class="dialog-footer flex justify-end gap-2.5 pt-2 border-t border-surface-border">
          <Button label="取消" severity="secondary" @click="showRestartConfirm = false" />
          <Button
            label="確定重啟"
            icon="pi pi-check"
            severity="danger"
            :loading="isRestarting"
            @click="executeRestart"
          />
        </div>
      </div>
    </div>

    <!-- 重啟中連線輪詢等待覆蓋遮罩 -->
    <div v-if="isReconnecting" class="reconnect-overlay fixed inset-0 bg-black/80 backdrop-blur-md z-[1000] flex items-center justify-center p-4">
      <div class="reconnect-box bg-surface-card border border-surface-border rounded-xl p-8 max-w-md w-full text-center flex flex-col items-center gap-3 shadow-2xl">
        <div class="spinner-icon text-3xl text-primary animate-spin">
          <i class="pi pi-spin pi-spinner"></i>
        </div>
        <h3 class="m-0 text-lg font-bold text-surface-900 dark:text-surface-0">伺服器正在重新啟動中...</h3>
        <p class="reconnect-desc text-xs text-surface-400 m-0 leading-relaxed">
          已發送重啟訊號，正在偵測服務健康狀態 (已等待 {{ reconnectTimer }} 秒 / 最長等待 120 秒)...
        </p>
        <div class="ping-status text-xs text-surface-400 flex items-center gap-2 bg-surface-ground px-3 py-1.5 rounded-full border border-surface-border">
          <i class="pi pi-circle-fill text-[8px] text-amber-400 animate-pulse"></i>
          <span>正在探測端點：<code class="text-sky-300 font-mono">{{ healthCheckEndpointUrl }}</code></span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * @file SettingsView.vue
 * @description 系統環境與參數設定頁面，完整綁定 .env 檔案並提供重啟服務器功能
 */

import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import Button from 'primevue/button'
import {
  fetchEnvSettings,
  updateEnvSettings,
  restartServer,
  fetchStorageStats,
  triggerStorageCleanup,
  checkServerHealth,
  fetchAvailableLlmModels,
} from '@/services/api'
import type { EnvSettingItem, EnvCategory, StorageStats } from '@/types/settings'

const router = useRouter()

// 資料狀態
const envItems = ref<EnvSettingItem[]>([])
const categories = ref<EnvCategory[]>([])
const formValues = ref<Record<string, string>>({})
const originalValues = ref<Record<string, string>>({})
const visibleSecrets = ref<Record<string, boolean>>({})

// LLM 可用模型即時查詢狀態
const availableLlmModels = ref<string[]>([])
const isFetchingModels = ref<boolean>(false)
const llmModelStatusMessage = ref<string>('')
const llmModelStatusSuccess = ref<boolean>(true)

// 分類切換
const selectedCategory = ref<string>('all')

// 載入與動作狀態
const isLoading = ref<boolean>(false)
const isSaving = ref<boolean>(false)
const isRestarting = ref<boolean>(false)
const isReconnecting = ref<boolean>(false)
const reconnectTimer = ref<number>(0)
let reconnectInterval: any = null

const showRestartConfirm = ref<boolean>(false)
const saveSuccessMessage = ref<string>('')
const restartPromptVisible = ref<boolean>(false)
const pendingRestartReasons = ref<string[]>([])

// 磁碟空間狀態
const storageStats = ref<StorageStats>({
  total_files: 0,
  total_bytes: 0,
  total_mb: 0.0,
  uploads: { file_count: 0, total_bytes: 0 },
  staging: { file_count: 0, total_bytes: 0 },
  reports: { file_count: 0, total_bytes: 0 },
})
const isLoadingStats = ref<boolean>(false)
const isCleaning = ref<boolean>(false)
const cleanupMessage = ref<string>('')

// 計算屬性：是否有尚未儲存的變更
const hasUnsavedChanges = computed(() => {
  for (const k of Object.keys(formValues.value)) {
    if (formValues.value[k] !== originalValues.value[k]) {
      return true
    }
  }
  return false
})

const changedKeysCount = computed(() => {
  let count = 0
  for (const k of Object.keys(formValues.value)) {
    if (formValues.value[k] !== originalValues.value[k]) {
      count++
    }
  }
  return count
})

const isItemChanged = (key: string): boolean => {
  return formValues.value[key] !== originalValues.value[key]
}

const displayCategories = computed(() => {
  if (selectedCategory.value === 'all') {
    return categories.value
  }
  return categories.value.filter((c) => c.id === selectedCategory.value)
})

/**
 * 動態計算健康探測端點網址 (Health Check URL)
 * 依據表單中之 SERVER_HOST 與 FRONTEND_PORT，或當前瀏覽器 window.location 動態組裝，確保 UI 顯示與實際發送路徑一致。
 */
const healthCheckEndpointUrl = computed(() => {
  const host = formValues.value['SERVER_HOST'] || (typeof window !== 'undefined' ? window.location.hostname : '192.168.1.16')
  const port = formValues.value['FRONTEND_PORT'] || (typeof window !== 'undefined' && window.location.port ? window.location.port : '8080')
  const protocol = typeof window !== 'undefined' && window.location.protocol ? window.location.protocol : 'http:'
  return `${protocol}//${host}:${port}/api/v1/health`
})

const getCategoryItems = (catId: string): EnvSettingItem[] => {
  return envItems.value.filter((item) => item.category === catId)
}

const toggleSecret = (key: string) => {
  visibleSecrets.value[key] = !visibleSecrets.value[key]
}

const handleInput = (_key: string) => {
  // 自動追蹤變更
}

const formatBytes = (bytes: number): string => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

// 支援之 LiteLLM 服務提供者定義
interface LlmProviderOption {
  id: string
  name: string
  tag: string
  icon: string
  defaultUrl: string
  defaultModel: string
  keyHint: string
}

const supportedProviders: LlmProviderOption[] = [
  {
    id: 'local',
    name: '本地推理',
    tag: 'vLLM / Ollama',
    icon: 'pi pi-server',
    defaultUrl: 'http://192.168.1.5:8000/v1',
    defaultModel: 'openai/qwen',
    keyHint: '本地端點未啟用鑑權填 EMPTY 即可'
  },
  {
    id: 'gemini',
    name: 'Google Gemini',
    tag: 'AI Studio',
    icon: 'pi pi-bolt',
    defaultUrl: 'https://generativelanguage.googleapis.com',
    defaultModel: 'gemini/gemini-2.5-flash',
    keyHint: '請填入 Google AI Studio API Key (AIzaSy...)'
  },
  {
    id: 'openrouter',
    name: 'OpenRouter',
    tag: '聚合網關',
    icon: 'pi pi-globe',
    defaultUrl: 'https://openrouter.ai/api/v1',
    defaultModel: 'openrouter/google/gemini-2.5-flash',
    keyHint: '請填入 OpenRouter API Key (sk-or-v1-...)'
  },
  {
    id: 'openai',
    name: 'OpenAI 官方',
    tag: 'GPT-4o',
    icon: 'pi pi-microchip',
    defaultUrl: 'https://api.openai.com/v1',
    defaultModel: 'openai/gpt-4o',
    keyHint: '請填入 OpenAI API Key (sk-proj-...)'
  },
  {
    id: 'anthropic',
    name: 'Anthropic',
    tag: 'Claude 3.5',
    icon: 'pi pi-comments',
    defaultUrl: 'https://api.anthropic.com',
    defaultModel: 'anthropic/claude-3-5-sonnet-20241022',
    keyHint: '請填入 Anthropic API Key (sk-ant-...)'
  },
  {
    id: 'groq',
    name: 'Groq',
    tag: '極速推理',
    icon: 'pi pi-forward',
    defaultUrl: 'https://api.groq.com/openai/v1',
    defaultModel: 'groq/llama-3.3-70b-versatile',
    keyHint: '請填入 Groq API Key (gsk_...)'
  },
  {
    id: 'deepseek',
    name: 'DeepSeek',
    tag: '官方 API',
    icon: 'pi pi-search',
    defaultUrl: 'https://api.deepseek.com/v1',
    defaultModel: 'deepseek/deepseek-chat',
    keyHint: '請填入 DeepSeek API Key (sk-...)'
  },
]

const currentProvider = computed(() => {
  if (formValues.value['LITELLM_PROVIDER']) {
    return formValues.value['LITELLM_PROVIDER'].toLowerCase()
  }
  const model = (formValues.value['LOCAL_LLM_MODEL'] || '').toLowerCase()
  if (model.startsWith('gemini/')) return 'gemini'
  if (model.startsWith('openrouter/')) return 'openrouter'
  if (model.startsWith('anthropic/') || model.startsWith('claude')) return 'anthropic'
  if (model.startsWith('groq/')) return 'groq'
  if (model.startsWith('deepseek/')) return 'deepseek'
  return 'local'
})

const selectProvider = (providerId: string) => {
  if (!providerId) return
  formValues.value['LITELLM_PROVIDER'] = providerId
  handleInput('LITELLM_PROVIDER')

  const providerDef = supportedProviders.find((p) => p.id === providerId)
  if (providerDef) {
    const curUrl = formValues.value['LOCAL_LLM_URL'] || ''
    const isOtherDefault = supportedProviders.some((p) => p.defaultUrl === curUrl)
    if (!curUrl || isOtherDefault || (providerId === 'gemini' && curUrl.includes('192.168.1.5'))) {
      formValues.value['LOCAL_LLM_URL'] = providerDef.defaultUrl
      handleInput('LOCAL_LLM_URL')
    }

    const curModel = (formValues.value['LOCAL_LLM_MODEL'] || '').trim()
    // 僅在模型為空或明顯屬於其他特定 Provider 前綴時才置換為預設模型，保留使用者自訂模型 (如 Qwen3.8-27B)
    const isOtherProviderModel =
      (providerId === 'local' && (curModel.startsWith('gemini/') || curModel.startsWith('openrouter/') || curModel.startsWith('groq/') || curModel.startsWith('deepseek/') || curModel.startsWith('anthropic/'))) ||
      (providerId === 'gemini' && !curModel.startsWith('gemini/')) ||
      (providerId === 'openrouter' && !curModel.startsWith('openrouter/')) ||
      (providerId === 'groq' && !curModel.startsWith('groq/')) ||
      (providerId === 'deepseek' && !curModel.startsWith('deepseek/')) ||
      (providerId === 'anthropic' && !curModel.startsWith('anthropic/'))

    if (!curModel || isOtherProviderModel) {
      formValues.value['LOCAL_LLM_MODEL'] = providerDef.defaultModel
      handleInput('LOCAL_LLM_MODEL')
    }

    queryLlmModels(true, providerId)
  }
}

// 載入 .env 設定資料
const loadEnvSettings = async () => {
  isLoading.value = true
  try {
    const data = await fetchEnvSettings()
    envItems.value = data.items
    categories.value = data.categories

    const forms: Record<string, string> = {}
    const origs: Record<string, string> = {}
    for (const item of data.items) {
      forms[item.key] = item.value !== null && item.value !== undefined ? String(item.value) : ''
      origs[item.key] = forms[item.key]
    }
    formValues.value = forms
    originalValues.value = origs

    // 自動向 LiteLLM 服務查詢可用模型列表
    queryLlmModels(false)
  } catch (err) {
    console.error('Failed to load env settings:', err)
  } finally {
    isLoading.value = false
  }
}

// 即時向 LiteLLM 伺服器端點或 Provider 查詢可用模型
const queryLlmModels = async (manual = false, forceProvider?: string) => {
  const p = forceProvider || currentProvider.value
  const url = formValues.value['LOCAL_LLM_URL'] || ''
  let key = formValues.value['LOCAL_LLM_API_KEY'] || ''
  if (p === 'gemini' && formValues.value['GEMINI_API_KEY']) {
    key = formValues.value['GEMINI_API_KEY']
  } else if (p === 'openrouter' && formValues.value['OPENROUTER_API_KEY']) {
    key = formValues.value['OPENROUTER_API_KEY']
  }

  isFetchingModels.value = true
  if (manual) {
    const provName = supportedProviders.find((sp) => sp.id === p)?.name || p
    llmModelStatusMessage.value = `正在查詢 ${provName} 可用模型清單...`
  }

  try {
    const res = await fetchAvailableLlmModels(p, url, key)
    if (res && res.success && Array.isArray(res.models) && res.models.length > 0) {
      availableLlmModels.value = res.models
      llmModelStatusSuccess.value = true
      llmModelStatusMessage.value = res.message || `成功取得 ${res.models.length} 個可用模型`
    } else {
      llmModelStatusSuccess.value = false
      llmModelStatusMessage.value = res?.message || '未能取得模型清單，支援手動輸入模型名稱'
    }
  } catch (err: any) {
    llmModelStatusSuccess.value = false
    llmModelStatusMessage.value = '連線至模型伺服器端點失敗，支援手動輸入模型名稱'
  } finally {
    isFetchingModels.value = false
  }
}

const onModelSelectChange = (event: Event) => {
  const target = event.target as HTMLSelectElement
  if (target && target.value) {
    formValues.value['LOCAL_LLM_MODEL'] = target.value
    handleInput('LOCAL_LLM_MODEL')
  }
}

const applyModel = (modelName: string) => {
  formValues.value['LOCAL_LLM_MODEL'] = modelName
  handleInput('LOCAL_LLM_MODEL')
}

// 載入磁碟空間指標
const loadStorageStats = async () => {
  isLoadingStats.value = true
  try {
    const data = await fetchStorageStats()
    if (data) {
      storageStats.value = data
    }
  } catch (err) {
    console.error('Failed to load storage stats:', err)
  } finally {
    isLoadingStats.value = false
  }
}

// 觸發磁碟空間清理
const triggerCleanup = async () => {
  isCleaning.value = true
  cleanupMessage.value = ''
  try {
    const res = await triggerStorageCleanup()
    if (res) {
      const tasksCount = res.expired_tasks_count ?? 0
      const orphanCount = res.orphan_files_count ?? 0
      cleanupMessage.value = `清理成功！已釋放 ${res.freed_mb} MB 空間，清除 ${tasksCount} 個過期任務與 ${orphanCount} 個孤兒檔案。`
      await loadStorageStats()
    }
  } catch (err) {
    cleanupMessage.value = '清理失敗，請檢閱後端日誌。'
    console.error('Cleanup error:', err)
  } finally {
    isCleaning.value = false
  }
}

// 放棄變更並還原
const resetChanges = () => {
  formValues.value = { ...originalValues.value }
}

// 儲存設定至 .env
const saveSettings = async () => {
  isSaving.value = true
  saveSuccessMessage.value = ''

  try {
    const payload: Record<string, any> = {}
    for (const k of Object.keys(formValues.value)) {
      if (formValues.value[k] !== originalValues.value[k]) {
        payload[k] = formValues.value[k]
      }
    }

    if (Object.keys(payload).length === 0) {
      isSaving.value = false
      return
    }

    const res = await updateEnvSettings(payload)
    if (res.success) {
      originalValues.value = { ...formValues.value }
      saveSuccessMessage.value = res.message || '設定已成功儲存至 .env 檔案！'

      if (res.requires_restart) {
        restartPromptVisible.value = true
        pendingRestartReasons.value = res.restart_reasons || []
      } else {
        restartPromptVisible.value = false
      }
    }
  } catch (err) {
    console.error('Failed to save settings:', err)
  } finally {
    isSaving.value = false
  }
}

// 重啟伺服器確認與執行
const confirmRestartServer = () => {
  showRestartConfirm.value = true
}

const executeRestart = async () => {
  showRestartConfirm.value = false
  isRestarting.value = true
  isReconnecting.value = true
  reconnectTimer.value = 0

  try {
    await restartServer()
  } catch (err) {
    console.error('Trigger restart error (expected during process restart):', err)
  }

  // 開始計時與連線輪詢 (每秒累加 1 次，逾時上限擴增至 120 秒)
  let checkInFlight = false
  reconnectInterval = setInterval(async () => {
    reconnectTimer.value += 1

    // 預留前 3 秒緩衝讓後端容器有充足時間接收關閉信號並中斷舊連線
    if (reconnectTimer.value >= 3 && !checkInFlight) {
      checkInFlight = true
      try {
        const isAlive = await checkServerHealth()
        if (isAlive) {
          clearInterval(reconnectInterval)
          reconnectInterval = null
          isReconnecting.value = false
          isRestarting.value = false
          restartPromptVisible.value = false
          saveSuccessMessage.value = '✅ 伺服器已成功重啟完成並恢復連線！'
          await loadEnvSettings()
          await loadStorageStats()
          return
        }
      } catch {
        // 重啟過程中網路暫時中斷屬預期狀況，持續探測
      } finally {
        checkInFlight = false
      }
    }

    // 逾時保護 (擴展為 120 秒)
    if (reconnectTimer.value >= 120) {
      if (reconnectInterval) {
        clearInterval(reconnectInterval)
        reconnectInterval = null
      }
      isReconnecting.value = false
      isRestarting.value = false
      alert('伺服器重啟探測逾時 (已等待 120 秒)，請手動刷新頁面或確認容器執行狀態。')
    }
  }, 1000)
}

const goBack = () => {
  router.push('/')
}

onMounted(() => {
  loadEnvSettings()
  loadStorageStats()
})

onUnmounted(() => {
  if (reconnectInterval) {
    clearInterval(reconnectInterval)
  }
})
</script>
