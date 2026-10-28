<template>
  <div class="settings-page-container flex flex-col bg-surface-ground min-h-screen text-vscode-textMain pb-16">
    <!-- 頂部緊湊頁頭導航與動作列 (VS Code 風格：含搜尋列與主要操作) -->
    <header class="settings-header flex flex-wrap justify-between items-center gap-3 bg-surface-card px-4 py-2 border-b border-surface-border sticky top-0 z-30">
      <!-- 左側：標題 (純中文) -->
      <div class="header-left flex items-center gap-2 min-w-0">
        <i class="pi pi-cog text-primary text-sm shrink-0"></i>
        <h1 class="page-title text-sm font-semibold m-0 text-vscode-textHeading truncate">
          系統環境與參數設定
        </h1>
      </div>

      <!-- 中間：VS Code 風格即時搜尋輸入框 -->
      <div class="header-search flex-1 max-w-xs sm:max-w-sm mx-2">
        <div class="search-box relative flex items-center w-full">
          <i class="pi pi-search absolute left-2.5 text-xs text-vscode-textMuted pointer-events-none"></i>
          <input
            v-model="searchKeyword"
            type="search"
            placeholder="搜尋設定 (名稱、Key 或說明)..."
            class="settings-search-input w-full !pl-8 !pr-7 !py-1 text-xs font-sans bg-surface-ground border border-surface-border text-vscode-textHeading rounded focus:outline-none focus:border-primary transition-colors"
          />
          <button
            v-if="searchKeyword"
            type="button"
            class="clear-search-btn absolute right-2 text-vscode-textMuted hover:text-vscode-textHeading bg-transparent border-0 cursor-pointer p-0 text-xs"
            @click="searchKeyword = ''"
          >
            <i class="pi pi-times"></i>
            <span class="sr-only">清除搜尋</span>
          </button>
        </div>
      </div>

      <!-- 右側動作按鈕 -->
      <div class="header-actions flex items-center gap-1.5 shrink-0">
        <Button
          v-tooltip.bottom="'重設未儲存變更'"
          icon="pi pi-undo"
          severity="secondary"
          size="small"
          outlined
          class="!w-7 !h-7 !p-0"
          :disabled="!hasUnsavedChanges || isSaving"
          @click="resetChanges"
        >
          <i class="pi pi-undo text-xs"></i>
          <span class="sr-only">重設未儲存變更</span>
        </Button>
        <Button
          label="儲存設定"
          icon="pi pi-save"
          severity="primary"
          size="small"
          class="!py-1 !px-2.5 !text-xs"
          :loading="isSaving"
          :disabled="!hasUnsavedChanges"
          @click="saveSettings"
        />
        <Button
          v-tooltip.bottom="'重新啟動後端伺服器'"
          icon="pi pi-power-off"
          severity="danger"
          size="small"
          outlined
          class="!w-7 !h-7 !p-0"
          :loading="isRestarting"
          @click="confirmRestartServer"
        >
          <i class="pi pi-power-off text-xs"></i>
          <span class="sr-only">重啟服務器</span>
        </Button>
      </div>
    </header>

    <!-- 需重啟伺服器之警示提示橫幅 -->
    <div
      v-if="restartPromptVisible"
      class="alert-banner warning-banner flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 px-4 py-2 bg-amber-500/10 border-b border-amber-500/30 text-amber-600 dark:text-amber-400 text-xs"
    >
      <div class="alert-content flex items-center gap-2">
        <i class="pi pi-exclamation-triangle alert-icon text-sm text-amber-500 shrink-0"></i>
        <div>
          <span class="alert-title font-semibold">系統提示：部分設定變更需要重新啟動伺服器才能完全生效</span>
          <span class="alert-desc text-vscode-textSecondary ml-2">
            受影響項目：<strong>{{ pendingRestartReasons.join(', ') }}</strong>
          </span>
        </div>
      </div>
      <Button
        label="立即重啟服務器"
        icon="pi pi-refresh"
        severity="warn"
        size="small"
        class="!py-1 !px-2.5 !text-xs shrink-0"
        :loading="isRestarting"
        @click="confirmRestartServer"
      />
    </div>

    <!-- 儲存成功通知橫幅 -->
    <div
      v-if="saveSuccessMessage"
      class="alert-banner success-banner flex items-center justify-between px-4 py-1.5 bg-emerald-500/10 border-b border-emerald-500/30 text-emerald-600 dark:text-emerald-400 text-xs"
    >
      <div class="alert-content flex items-center gap-2">
        <i class="pi pi-check-circle alert-icon text-emerald-500"></i>
        <span>{{ saveSuccessMessage }}</span>
      </div>
      <button
        type="button"
        class="banner-close bg-transparent border-0 text-inherit cursor-pointer p-0.5"
        @click="saveSuccessMessage = ''"
      >
        <i class="pi pi-times text-xs"></i>
      </button>
    </div>

    <!-- 行動/窄螢幕橫向滾動分類導航列 (RWD: md:hidden) -->
    <div class="category-tabs flex md:hidden gap-1.5 overflow-x-auto px-4 py-2 bg-surface-card border-b border-surface-border">
      <button
        v-for="cat in categories"
        :key="cat.id"
        type="button"
        class="tab-btn px-2.5 py-1 text-xs font-medium rounded border cursor-pointer transition-colors whitespace-nowrap flex items-center gap-1.5"
        :class="activeCategory === cat.id
          ? 'bg-primary-500 text-white border-primary-500'
          : 'bg-surface-panel border-surface-border text-vscode-textSecondary hover:text-vscode-textHeading hover:bg-surface-hover'"
        @click="scrollToCategory(cat.id)"
      >
        <i :class="cat.icon" class="text-[11px]"></i>
        <span>{{ cleanCategoryName(cat.name) }} ({{ getCategoryItems(cat.id).length }})</span>
      </button>
    </div>

    <!-- 左右雙欄主佈局 (VS Code 設定風格：左欄大綱導航 + 右欄長頁面設定) -->
    <div class="settings-main-split flex flex-1 w-full max-w-[1600px] mx-auto">
      <!-- 左側大綱導航 (Sticky Outline Sidebar，桌機版 md:flex) -->
      <aside class="settings-outline-sidebar w-64 lg:w-72 shrink-0 border-r border-surface-border bg-surface-card p-3 hidden md:flex flex-col gap-1 sticky top-12 self-start max-h-[calc(100vh-3rem)] overflow-y-auto">
        <div class="outline-header px-2 py-1 text-[11px] font-semibold uppercase tracking-wider text-vscode-textMuted flex items-center justify-between">
          <span class="flex items-center gap-1.5">
            <i class="pi pi-compass text-[11px] text-primary"></i>
            <span>設定大綱 (Outline)</span>
          </span>
          <span class="text-[10px] font-mono text-vscode-textMuted">共 {{ envItems.length }} 項</span>
        </div>

        <nav class="outline-nav flex flex-col gap-0.5 mt-1">
          <!-- 個別分類大綱項目 -->
          <button
            v-for="cat in categories"
            :key="cat.id"
            type="button"
            class="tab-btn outline-item-btn w-full text-left px-2.5 py-1.5 rounded text-xs font-medium cursor-pointer transition-colors flex items-center justify-between group"
            :class="activeCategory === cat.id
              ? 'bg-primary/10 text-primary font-semibold border-l-2 border-primary'
              : 'text-vscode-textSecondary hover:text-vscode-textHeading hover:bg-surface-hover border-l-2 border-transparent'"
            @click="scrollToCategory(cat.id)"
          >
            <span class="flex items-center gap-2 truncate">
              <i :class="cat.icon" class="text-xs shrink-0"></i>
              <span class="truncate">{{ cleanCategoryName(cat.name) }}</span>
            </span>
            <div class="flex items-center gap-1 shrink-0">
              <!-- 未儲存變更提示圓點 -->
              <span
                v-if="getCategoryModifiedCount(cat.id) > 0"
                v-tooltip.top="`${getCategoryModifiedCount(cat.id)} 個項目已修改`"
                class="w-2 h-2 rounded-full bg-amber-500 inline-block shrink-0"
              ></span>
              <Tag
                :value="getCategoryItems(cat.id).length"
                severity="secondary"
                class="!text-[10px] !py-0 !px-1.5 !font-mono"
              />
            </div>
          </button>
        </nav>
      </aside>

      <!-- 右側長頁面設定內容區 (Continuous Scroll Panel) -->
      <main class="settings-content-pane flex-1 min-w-0 flex flex-col divide-y divide-surface-border">
        <!-- 搜尋無結果提示 -->
        <div
          v-if="displayCategories.length === 0"
          class="empty-search-state p-12 text-center text-vscode-textMuted text-xs flex flex-col items-center gap-2 bg-surface-panel"
        >
          <i class="pi pi-search text-2xl text-vscode-textMuted"></i>
          <span>未找到與「<strong class="text-vscode-textHeading">{{ searchKeyword }}</strong>」相符的設定項目</span>
          <Button
            label="清除搜尋關鍵字"
            size="small"
            severity="secondary"
            outlined
            class="!text-xs !py-1 !px-2 mt-2"
            @click="searchKeyword = ''"
          />
        </div>

        <!-- 各設定分組區塊 (長頁面連續向下滾動，支援錨點) -->
        <section
          v-for="cat in displayCategories"
          :id="`section-${cat.id}`"
          :key="cat.id"
          class="category-group-card bg-surface-panel flex flex-col scroll-mt-14 pb-4"
        >
          <!-- 分組大標題列 (清晰視覺階層：底色襯托、加大字體、圖示徽章) -->
          <div class="group-header flex items-center justify-between gap-3 px-4 sm:px-6 py-3 bg-surface-card border-y border-surface-border">
            <div class="flex items-center gap-2.5 min-w-0">
              <div class="w-6 h-6 rounded flex items-center justify-center bg-primary/10 text-primary shrink-0">
                <i :class="cat.icon" class="group-icon text-xs"></i>
              </div>
              <h2 class="m-0 text-sm sm:text-base font-bold text-vscode-textHeading tracking-tight truncate">
                {{ cleanCategoryName(cat.name) }}
              </h2>
            </div>
            <Tag
              :value="`${getFilteredCategoryItems(cat.id).length} 項`"
              severity="secondary"
              class="!text-[11px] !py-0.5 !px-2 !font-mono shrink-0"
            />
          </div>

          <!-- 子項目縮排區塊 (清晰層級：明顯縮排 + 左側微導引線) -->
          <div class="settings-items-list divide-y divide-surface-border/60 pl-4 sm:pl-8 pr-4 sm:pr-6 ml-3 sm:ml-5 border-l-2 border-surface-border/60 my-2">
            <div
              v-for="item in getFilteredCategoryItems(cat.id)"
              :key="item.key"
              :id="`setting-item-${item.key}`"
              class="setting-item-row px-3 sm:px-4 py-3.5 grid grid-cols-1 lg:grid-cols-2 gap-4 items-start transition-colors hover:bg-surface-hover/30 rounded"
              :class="isItemChanged(item.key) ? 'bg-amber-500/5 border-l-2 border-l-amber-500' : ''"
            >
              <!-- 左側欄：第 1 行主說明 + 主 key + tag；第 2 行輸入元件 / toggle button -->
              <div class="setting-item-left flex flex-col gap-1.5 min-w-0">
                <!-- 第 1 行：主說明 (item.label) + 主 key (.env-key-badge) + 狀態 tag (需重啟/已修改) -->
                <div class="meta-title-row flex items-center gap-1.5 flex-wrap">
                  <span class="item-label font-semibold text-xs text-vscode-textHeading">{{ item.label }}</span>
                  <code class="env-key-badge font-mono text-[11px] px-1.5 py-0.2 rounded bg-surface-card border border-surface-border text-primary font-medium">{{ item.key }}</code>

                  <!-- 僅在 requires_restart 時顯示需重啟生效標籤，已移除動態生效標籤 -->
                  <Tag
                    v-if="item.requires_restart"
                    severity="warn"
                    class="badge-restart text-[10px] !py-0 !px-1.5 font-medium inline-flex items-center gap-1"
                  >
                    <i class="pi pi-refresh text-[9px]"></i> 需重啟生效
                  </Tag>

                  <!-- 已修改標籤 -->
                  <Tag
                    v-if="isItemChanged(item.key)"
                    severity="danger"
                    class="badge-modified text-[10px] !py-0 !px-1.5 font-semibold"
                  >
                    已修改
                  </Tag>
                </div>

                <!-- 第 2 行：輸入控制元件 (InputText / Provider select / Model select / ToggleSwitch) -->
                <div class="setting-item-control w-full flex flex-col gap-1.5">
                  <!-- LITELLM_PROVIDER 下拉切換選單 -->
                  <div v-if="item.key === 'LITELLM_PROVIDER'" class="input-wrapper relative flex items-center w-full">
                    <Select
                      v-model="formValues[item.key]"
                      :options="supportedProviders"
                      optionLabel="name"
                      optionValue="id"
                      size="small"
                      class="setting-input provider-select w-full text-xs font-mono"
                      @change="selectProvider(formValues[item.key])"
                    >
                      <template #value="slotProps">
                        <span v-if="slotProps.value" class="text-xs font-mono">
                          {{ getProviderDisplay(slotProps.value) }}
                        </span>
                      </template>
                      <template #option="slotProps">
                        <div class="flex items-center gap-1.5 text-xs font-mono">
                          <i :class="slotProps.option.icon" class="text-[11px]"></i>
                          <span>{{ slotProps.option.name }} ({{ slotProps.option.tag }}) - provider: {{ slotProps.option.id }}</span>
                        </div>
                      </template>
                    </Select>
                  </div>

                  <!-- LLM_MODEL 整合型 Combo 輸入下拉選單 (PrimeVue Select editable 原生元件) -->
                  <div v-else-if="item.key === 'LLM_MODEL'" class="model-select-wrapper flex flex-col gap-1.5 w-full">
                    <div class="input-wrapper relative flex items-center w-full gap-1.5">
                      <Select
                        id="llm-model-select"
                        v-model="formValues[item.key]"
                        :options="availableLlmModels"
                        editable
                        size="small"
                        class="setting-input model-input w-full text-xs font-mono"
                        :placeholder="item.default || item.example || '可直接輸入或自下拉選單選擇'"
                        @change="handleInput(item.key)"
                        @input="handleInput(item.key)"
                      />
                      <Button
                        v-tooltip.top="isFetchingModels ? '正在向伺服器查詢可用模型...' : '即時向伺服器查詢可用模型清單'"
                        icon="pi pi-refresh"
                        severity="secondary"
                        size="small"
                        outlined
                        class="btn-fetch-models !h-7 !px-2 !py-1 text-xs shrink-0"
                        :loading="isFetchingModels"
                        @click="queryLlmModels(true)"
                      >
                        <i :class="isFetchingModels ? 'pi pi-spin pi-spinner' : 'pi pi-refresh'" class="text-xs"></i>
                        <span class="sr-only">{{ isFetchingModels ? '查詢中...' : '重新整理' }}</span>
                      </Button>
                    </div>

                    <!-- 查詢狀態提示 -->
                    <div v-if="llmModelStatusMessage" class="model-status-hint text-[11px] flex items-center gap-1" :class="llmModelStatusSuccess ? 'text-emerald-500' : 'text-vscode-textMuted'">
                      <i :class="llmModelStatusSuccess ? 'pi pi-check-circle text-emerald-500' : 'pi pi-info-circle text-vscode-textMuted'" class="text-[10px]"></i>
                      <span>{{ llmModelStatusMessage }}</span>
                    </div>
                  </div>

                  <!-- 布林開關 (item_type === 'boolean') -->
                  <div v-else-if="item.item_type === 'boolean'" class="boolean-switch-wrapper flex items-center justify-between px-2.5 py-1 rounded border border-surface-border bg-surface-ground w-full">
                    <div class="flex items-center gap-2">
                      <span
                        class="status-text text-[11px] font-medium px-1.5 py-0.2 rounded border flex items-center gap-1"
                        :class="isBooleanActive(item.key)
                          ? 'bg-emerald-500/15 border-emerald-500/30 text-emerald-600 dark:text-emerald-400'
                          : 'bg-surface-card border-surface-border text-vscode-textMuted'"
                      >
                        <i :class="isBooleanActive(item.key) ? 'pi pi-check-circle text-emerald-500' : 'pi pi-ban text-vscode-textMuted'" class="text-[10px]"></i>
                        {{ isBooleanActive(item.key) ? '已啟用 (Enabled)' : '已停用 (Disabled)' }}
                      </span>
                      <span class="text-[11px] font-mono text-vscode-textMuted">
                        DB: <code class="text-primary font-semibold">{{ formValues[item.key] }}</code>
                      </span>
                    </div>
                    <ToggleSwitch
                      :model-value="isBooleanActive(item.key)"
                      class="setting-boolean-switch scale-75 origin-right"
                      @update:model-value="setBooleanValue(item.key, $event)"
                    />
                  </div>

                  <!-- 一般文字/密鑰輸入框 -->
                  <div v-else class="input-wrapper relative flex items-center w-full">
                    <InputText
                      v-if="!item.is_secret || visibleSecrets[item.key]"
                      v-model="formValues[item.key]"
                      type="text"
                      size="small"
                      class="setting-input w-full !py-1 !px-2.5 text-xs font-mono bg-surface-ground border-surface-border text-vscode-textHeading"
                      :placeholder="item.default || item.example || '請輸入設定值'"
                      @input="handleInput(item.key)"
                      @blur="item.key === 'LLM_API_BASE' ? queryLlmModels(false) : null"
                    />
                    <InputText
                      v-else
                      v-model="formValues[item.key]"
                      type="password"
                      size="small"
                      class="setting-input w-full !py-1 !px-2.5 !pr-7 text-xs font-mono bg-surface-ground border-surface-border text-vscode-textHeading"
                      :placeholder="item.default || item.example || '請輸入設定值'"
                      @input="handleInput(item.key)"
                    />
                    <button
                      v-if="item.is_secret"
                      type="button"
                      v-tooltip.left="visibleSecrets[item.key] ? '隱藏金鑰' : '顯示金鑰'"
                      class="btn-toggle-secret absolute right-2 text-vscode-textMuted hover:text-vscode-textHeading cursor-pointer bg-transparent border-0 text-xs"
                      @click="toggleSecret(item.key)"
                    >
                      <i :class="visibleSecrets[item.key] ? 'pi pi-eye-slash' : 'pi pi-eye'"></i>
                    </button>
                  </div>

                  <!-- 若有修改顯示原值 -->
                  <div v-if="isItemChanged(item.key)" class="original-val-hint text-[10px] text-vscode-textMuted">
                    原設定值：<code class="bg-surface-card px-1 py-0.2 rounded text-amber-600 dark:text-amber-400 font-mono border border-surface-border">{{ originalValues[item.key] || '(空值)' }}</code>
                  </div>
                </div>
              </div>

              <!-- 右側欄：佔用與左側相同高度，放說明文字與範例格式 -->
              <div
                v-tooltip.bottom="formatItemTooltip(item)"
                class="setting-item-doc flex flex-col justify-start gap-1.5 text-xs py-0.5 min-w-0"
              >
                <p class="item-description text-xs text-vscode-textMain m-0 leading-relaxed whitespace-pre-wrap">
                  {{ item.description }}
                </p>
                <div
                  v-if="item.example && !item.description?.includes(item.example)"
                  class="item-example-box text-[11px] text-vscode-textMuted font-mono flex items-center gap-1.5 mt-0.5"
                >
                  <span class="shrink-0">範例格式：</span>
                  <code class="px-1.5 py-0.2 rounded bg-surface-ground border border-surface-border text-vscode-textSecondary break-all">{{ item.example }}</code>
                </div>
              </div>
            </div>
          </div>
        </section>
      </main>
    </div>

    <!-- 底部固定儲存浮動列 (當有未儲存變更時浮現) -->
    <div
      v-if="hasUnsavedChanges"
      class="floating-save-bar fixed bottom-4 left-1/2 -translate-x-1/2 z-50 bg-surface-panel border border-primary/60 rounded-lg px-4 py-2 shadow-xl flex items-center gap-4 text-xs text-vscode-textMain"
    >
      <div class="save-bar-info flex items-center gap-1.5">
        <i class="pi pi-info-circle text-primary"></i>
        <span>您有 <strong class="text-vscode-textHeading">{{ changedKeysCount }}</strong> 個設定項目尚未儲存至 <code class="font-mono text-primary">資料庫</code></span>
      </div>
      <div class="save-bar-actions flex items-center gap-2">
        <Button label="放棄變更" severity="secondary" size="small" outlined class="!py-1 !px-2 !text-xs" @click="resetChanges" />
        <Button
          label="立即儲存設定"
          icon="pi pi-check"
          severity="primary"
          size="small"
          class="!py-1 !px-2.5 !text-xs"
          :loading="isSaving"
          @click="saveSettings"
        />
      </div>
    </div>

    <!-- 重啟確認對話框 (採用 PrimeVue Dialog 原生元件，appendTo='self' 確保測試與渲染相容) -->
    <Dialog
      v-model:visible="showRestartConfirm"
      modal
      header="確認重啟伺服器？"
      :style="{ width: '28rem' }"
      :appendTo="'self'"
      :pt="{
        root: { class: 'bg-surface-panel border border-surface-border rounded-lg shadow-xl text-vscode-textMain' },
        header: { class: 'border-b border-surface-border px-4 py-3 text-sm font-semibold text-red-500' },
        content: { class: 'p-4 text-xs text-vscode-textSecondary' },
        footer: { class: 'border-t border-surface-border px-4 py-2.5 flex justify-end gap-2' },
      }"
    >
      <div class="dialog-body flex flex-col gap-1.5">
        <p class="m-0 leading-relaxed text-vscode-textMain">您即將發送指令重新啟動 DesignShield 後端伺服器服務。</p>
        <p class="text-vscode-textMuted text-xs m-0 leading-relaxed">
          重啟期間 API 連線將暫時中斷約 5~10 秒，頁面會自動監測連線狀況並在服務恢復時自動重新連線。
        </p>
      </div>
      <template #footer>
        <Button label="取消" severity="secondary" size="small" outlined @click="showRestartConfirm = false" />
        <Button
          label="確定重啟"
          icon="pi pi-check"
          severity="danger"
          size="small"
          :loading="isRestarting"
          @click="executeRestart"
        />
      </template>
    </Dialog>

    <!-- 重啟中連線輪詢等待覆蓋遮罩 -->
    <div v-if="isReconnecting" class="reconnect-overlay fixed inset-0 bg-black/60 backdrop-blur-md z-[1000] flex items-center justify-center p-4">
      <div class="reconnect-box bg-surface-panel border border-surface-border rounded-lg p-6 max-w-md w-full text-center flex flex-col items-center gap-2.5 shadow-xl">
        <div class="spinner-icon text-2xl text-primary animate-spin">
          <i class="pi pi-spin pi-spinner"></i>
        </div>
        <h3 class="m-0 text-sm font-semibold text-vscode-textHeading">伺服器正在重新啟動中...</h3>
        <p class="reconnect-desc text-xs text-vscode-textMuted m-0 leading-relaxed">
          已發送重啟訊號，正在偵測服務健康狀態 (已等待 {{ reconnectTimer }} 秒 / 最長等待 120 秒)...
        </p>
        <div class="ping-status text-xs text-vscode-textSecondary flex items-center gap-2 bg-surface-card px-3 py-1 rounded-full border border-surface-border">
          <i class="pi pi-circle-fill text-[8px] text-amber-500 animate-pulse"></i>
          <span>正在探測端點：<code class="text-primary font-mono">{{ healthCheckEndpointUrl }}</code></span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * @file SettingsView.vue
 * @description 系統環境與參數設定頁面 (VS Code 雙欄大綱導航 + 長頁面設定版，Zero-Custom-CSS)
 */

import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import Button from 'primevue/button'
import ToggleSwitch from 'primevue/toggleswitch'
import InputText from 'primevue/inputtext'
import Tag from 'primevue/tag'
import Select from 'primevue/select'
import Dialog from 'primevue/dialog'
import {
  fetchEnvSettings,
  updateEnvSettings,
  restartServer,
  checkServerHealth,
  fetchAvailableLlmModels,
} from '@/services/api'
import type { EnvSettingItem, EnvCategory } from '@/types/settings'

// 資料狀態
const envItems = ref<EnvSettingItem[]>([])
const categories = ref<EnvCategory[]>([])
const formValues = ref<Record<string, string>>({})
const originalValues = ref<Record<string, string>>({})
const visibleSecrets = ref<Record<string, boolean>>({})

// 搜尋關鍵字
const searchKeyword = ref<string>('')

// LLM 可用模型即時查詢狀態
const availableLlmModels = ref<string[]>([])
const isFetchingModels = ref<boolean>(false)
const llmModelStatusMessage = ref<string>('')
const llmModelStatusSuccess = ref<boolean>(true)

// 大綱導航選中與滾動活躍項目 (Scrollspy)
const activeCategory = ref<string>('')
let scrollObserver: IntersectionObserver | null = null

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

/**
 * 組合設定項目完整說明與範例格式供 Tooltip 呈現
 */
const formatItemTooltip = (item: EnvSettingItem): string => {
  if (item.example) {
    return `${item.description}\n範例格式：${item.example}`
  }
  return item.description || item.label
}

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

/**
 * 清理分類標題中的冗餘字串 (如去除重複的 " (LiteLLM)")
 */
const cleanCategoryName = (name: string): string => {
  return (name || '').replace(/\s*\(LiteLLM\)/gi, '').trim()
}

/**
 * 取得特定分類下的設定項目
 */
const getCategoryItems = (catId: string): EnvSettingItem[] => {
  return envItems.value.filter((item) => item.category === catId)
}

/**
 * 取得特定分類下符合搜尋條件的設定項目
 */
const getFilteredCategoryItems = (catId: string): EnvSettingItem[] => {
  const items = getCategoryItems(catId)
  if (!searchKeyword.value.trim()) {
    return items
  }
  const kw = searchKeyword.value.trim().toLowerCase()
  return items.filter((item) => {
    return (
      item.key.toLowerCase().includes(kw) ||
      (item.label && item.label.toLowerCase().includes(kw)) ||
      (item.description && item.description.toLowerCase().includes(kw)) ||
      (item.value && String(item.value).toLowerCase().includes(kw))
    )
  })
}

/**
 * 取得特定分類下已修改的設定項目數量
 */
const getCategoryModifiedCount = (catId: string): number => {
  const items = getCategoryItems(catId)
  return items.filter((item) => isItemChanged(item.key)).length
}

/**
 * 動態計算呈現的分類清單 (根據搜尋過濾)
 */
const displayCategories = computed(() => {
  if (!searchKeyword.value.trim()) {
    return categories.value
  }
  return categories.value.filter((cat) => getFilteredCategoryItems(cat.id).length > 0)
})

/**
 * 動態計算健康探測端點網址 (Health Check URL)
 */
const healthCheckEndpointUrl = computed(() => {
  const host = formValues.value['SERVER_HOST'] || (typeof window !== 'undefined' ? window.location.hostname : '192.168.1.16')
  const port = formValues.value['FRONTEND_PORT'] || (typeof window !== 'undefined' && window.location.port ? window.location.port : '8080')
  const protocol = typeof window !== 'undefined' && window.location.protocol ? window.location.protocol : 'http:'
  return `${protocol}//${host}:${port}/api/v1/health`
})

/**
 * 平滑滾動至指定分類區塊
 */
const scrollToCategory = (catId: string) => {
  activeCategory.value = catId
  if (catId === 'all') {
    const mainEl = typeof document !== 'undefined' ? (document.querySelector('.main-content') as HTMLElement | null) : null
    if (mainEl) {
      mainEl.scrollTo({ top: 0, behavior: 'smooth' })
    } else if (typeof window !== 'undefined') {
      window.scrollTo({ top: 0, behavior: 'smooth' })
    }
    return
  }

  // 若目前有搜尋關鍵字導致該分類未被渲染，先清空關鍵字
  if (searchKeyword.value) {
    searchKeyword.value = ''
  }

  nextTick(() => {
    if (typeof document === 'undefined') return
    const el = document.getElementById(`section-${catId}`)
    const mainEl = document.querySelector('.main-content') as HTMLElement | null
    if (mainEl && el) {
      const containerRect = mainEl.getBoundingClientRect()
      const elRect = el.getBoundingClientRect()
      // 52px 補償頂部緊湊黏性頁頭 (sticky header)
      const targetScrollTop = mainEl.scrollTop + (elRect.top - containerRect.top) - 52
      mainEl.scrollTo({
        top: Math.max(0, targetScrollTop),
        behavior: 'smooth',
      })
    } else if (el) {
      if (typeof el.scrollIntoView === 'function') {
        el.scrollIntoView({ behavior: 'smooth', block: 'start' })
      } else if (typeof window !== 'undefined') {
        window.scrollTo({ top: el.offsetTop - 52, behavior: 'smooth' })
      }
    }
  })
}

/**
 * 監聽滾動容器滑動至頂端時自動將第一項設為活躍項
 */
const handleContainerScroll = () => {
  if (typeof document === 'undefined') return
  const mainEl = document.querySelector('.main-content')
  if (mainEl && mainEl.scrollTop < 40 && categories.value.length > 0) {
    activeCategory.value = categories.value[0].id
  }
}

/**
 * 建立雙向滾動監聽 (Scrollspy)
 */
const setupScrollspy = () => {
  if (typeof window === 'undefined' || !('IntersectionObserver' in window)) return
  if (scrollObserver) {
    scrollObserver.disconnect()
  }

  const scrollContainer = document.querySelector('.main-content') || null

  scrollObserver = new IntersectionObserver(
    (entries) => {
      // 若滾動容器接近最頂端且有分類，直接將第一項設為 activeCategory
      if (scrollContainer && scrollContainer.scrollTop < 40 && categories.value.length > 0) {
        activeCategory.value = categories.value[0].id
        return
      }
      const visible = entries.filter((e) => e.isIntersecting)
      if (visible.length > 0) {
        const topEntry = visible.reduce((prev, curr) =>
          prev.boundingClientRect.top < curr.boundingClientRect.top ? prev : curr
        )
        const catId = topEntry.target.id.replace('section-', '')
        if (catId) {
          activeCategory.value = catId
        }
      }
    },
    {
      root: scrollContainer,
      rootMargin: '-52px 0px -60% 0px',
      threshold: 0,
    }
  )

  categories.value.forEach((cat) => {
    const el = document.getElementById(`section-${cat.id}`)
    if (el) {
      scrollObserver?.observe(el)
    }
  })
}

const toggleSecret = (key: string) => {
  visibleSecrets.value[key] = !visibleSecrets.value[key]
}

const handleInput = (_key: string) => {
  // 自動追蹤變更
}

const isBooleanActive = (key: string): boolean => {
  const val = String(formValues.value[key] ?? '').toLowerCase().trim()
  return val === 'true' || val === '1' || val === 'yes'
}

const setBooleanValue = (key: string, enabled: boolean) => {
  formValues.value[key] = enabled ? 'true' : 'false'
  handleInput(key)
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
    keyHint: '本地端點未啟用鑑權填 EMPTY 即可',
  },
  {
    id: 'gemini',
    name: 'Google Gemini',
    tag: 'AI Studio',
    icon: 'pi pi-bolt',
    defaultUrl: 'https://generativelanguage.googleapis.com',
    defaultModel: 'gemini/gemini-2.5-flash',
    keyHint: '請填入 Google AI Studio API Key (AIzaSy...)',
  },
  {
    id: 'openrouter',
    name: 'OpenRouter',
    tag: '聚合網關',
    icon: 'pi pi-globe',
    defaultUrl: 'https://openrouter.ai/api/v1',
    defaultModel: 'openrouter/google/gemini-2.5-flash',
    keyHint: '請填入 OpenRouter API Key (sk-or-v1-...)',
  },
  {
    id: 'openai',
    name: 'OpenAI 官方',
    tag: 'GPT-4o',
    icon: 'pi pi-microchip',
    defaultUrl: 'https://api.openai.com/v1',
    defaultModel: 'openai/gpt-4o',
    keyHint: '請填入 OpenAI API Key (sk-proj-...)',
  },
  {
    id: 'anthropic',
    name: 'Anthropic',
    tag: 'Claude 3.5',
    icon: 'pi pi-comments',
    defaultUrl: 'https://api.anthropic.com',
    defaultModel: 'anthropic/claude-3-5-sonnet-20241022',
    keyHint: '請填入 Anthropic API Key (sk-ant-...)',
  },
  {
    id: 'groq',
    name: 'Groq',
    tag: '極速推理',
    icon: 'pi pi-forward',
    defaultUrl: 'https://api.groq.com/openai/v1',
    defaultModel: 'groq/llama-3.3-70b-versatile',
    keyHint: '請填入 Groq API Key (gsk_...)',
  },
  {
    id: 'deepseek',
    name: 'DeepSeek',
    tag: '官方 API',
    icon: 'pi pi-search',
    defaultUrl: 'https://api.deepseek.com/v1',
    defaultModel: 'deepseek/deepseek-chat',
    keyHint: '請填入 DeepSeek API Key (sk-...)',
  },
]

const getProviderDisplay = (providerId: string): string => {
  const p = supportedProviders.find((sp) => sp.id === providerId)
  return p ? `${p.name} (${p.tag})` : providerId
}

const currentProvider = computed(() => {
  if (formValues.value['LITELLM_PROVIDER']) {
    return formValues.value['LITELLM_PROVIDER'].toLowerCase()
  }
  const model = (formValues.value['LLM_MODEL'] || '').toLowerCase()
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
    const curUrl = formValues.value['LLM_API_BASE'] || ''
    const isOtherDefault = supportedProviders.some((p) => p.defaultUrl === curUrl)
    if (!curUrl || isOtherDefault || (providerId === 'gemini' && curUrl.includes('192.168.1.5'))) {
      formValues.value['LLM_API_BASE'] = providerDef.defaultUrl
      handleInput('LLM_API_BASE')
    }

    const curModel = (formValues.value['LLM_MODEL'] || '').trim()
    const isOtherProviderModel =
      (providerId === 'local' && (curModel.startsWith('gemini/') || curModel.startsWith('openrouter/') || curModel.startsWith('groq/') || curModel.startsWith('deepseek/') || curModel.startsWith('anthropic/'))) ||
      (providerId === 'gemini' && !curModel.startsWith('gemini/')) ||
      (providerId === 'openrouter' && !curModel.startsWith('openrouter/')) ||
      (providerId === 'groq' && !curModel.startsWith('groq/')) ||
      (providerId === 'deepseek' && !curModel.startsWith('deepseek/')) ||
      (providerId === 'anthropic' && !curModel.startsWith('anthropic/'))

    if (!curModel || isOtherProviderModel) {
      formValues.value['LLM_MODEL'] = providerDef.defaultModel
      handleInput('LLM_MODEL')
    }

    queryLlmModels(true, providerId)
  }
}

// 載入 .env 設定資料
const loadEnvSettings = async () => {
  isLoading.value = true
  try {
    const data = await fetchEnvSettings()
    envItems.value = data?.items || []
    categories.value = data?.categories || []
    if (categories.value.length > 0 && !activeCategory.value) {
      activeCategory.value = categories.value[0].id
    }

    const forms: Record<string, string> = {}
    const origs: Record<string, string> = {}
    for (const item of (data?.items || [])) {
      forms[item.key] = item.value !== null && item.value !== undefined ? String(item.value) : ''
      origs[item.key] = forms[item.key]
    }
    formValues.value = forms
    originalValues.value = origs

    queryLlmModels(false)
    nextTick(() => {
      setupScrollspy()
    })
  } catch (err) {
    console.error('Failed to load env settings:', err)
  } finally {
    isLoading.value = false
  }
}

// 即時向 LiteLLM 伺服器端點或 Provider 查詢可用模型
const queryLlmModels = async (manual = false, forceProvider?: string) => {
  const p = forceProvider || currentProvider.value
  const url = formValues.value['LLM_API_BASE'] || ''
  let key = formValues.value['LLM_API_KEY'] || ''
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
      availableLlmModels.value = []
      llmModelStatusSuccess.value = false
      llmModelStatusMessage.value = res?.message || '未能取得模型清單，支援手動輸入模型名稱'
    }
  } catch (err: any) {
    availableLlmModels.value = []
    llmModelStatusSuccess.value = false
    llmModelStatusMessage.value = '連線至模型伺服器端點失敗，支援手動輸入模型名稱'
  } finally {
    isFetchingModels.value = false
  }
}

// 放棄變更並還原
const resetChanges = () => {
  formValues.value = { ...originalValues.value }
}

// 儲存設定至資料庫
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
      saveSuccessMessage.value = res.message || '設定已成功儲存至資料庫並即時生效！'

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

  let checkInFlight = false
  reconnectInterval = setInterval(async () => {
    reconnectTimer.value += 1

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
          return
        }
      } catch {
        // 重啟過程中網路暫時中斷屬預期狀況，持續探測
      } finally {
        checkInFlight = false
      }
    }

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

onMounted(() => {
  loadEnvSettings()
  if (typeof document !== 'undefined') {
    const mainEl = document.querySelector('.main-content')
    if (mainEl) {
      mainEl.addEventListener('scroll', handleContainerScroll, { passive: true })
    }
  }
})

onUnmounted(() => {
  if (reconnectInterval) {
    clearInterval(reconnectInterval)
  }
  if (scrollObserver) {
    scrollObserver.disconnect()
  }
  if (typeof document !== 'undefined') {
    const mainEl = document.querySelector('.main-content')
    if (mainEl) {
      mainEl.removeEventListener('scroll', handleContainerScroll)
    }
  }
})
</script>